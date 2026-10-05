"""Decoded GOP/color and actual transfer-ledger checks, outside render clocks."""
import pathlib,subprocess,json,sys

def inspect(probe,events,bitrate,frames=300):
 errors=[];streams=probe.get('streams',[]);decoded=probe.get('frames',[])
 if len(streams)!=1:errors.append('video stream count')
 stream=streams[0] if streams else {}
 for key,value in {'pix_fmt':'yuv420p','color_range':'tv','color_space':'bt709','color_transfer':'bt709','color_primaries':'bt709'}.items():
  if stream.get(key)!=value:errors.append('decoded '+key+' differs')
 keys=[i for i,f in enumerate(decoded) if f.get('key_frame')==1]
 if len(decoded)!=frames or not keys or keys[0]!=0:errors.append('frame count/first keyframe')
 spacing=[b-a for a,b in zip(keys,keys[1:])]+([frames-keys[-1]] if keys else [])
 if not spacing or max(spacing)>30:errors.append('actual GOP exceeds30')
 config=[e for e in events if e['event']=='surface-create']
 if len(config)!=1 or any(config[0].get(k)!=v for k,v in {'protocol':4,'bitrate':bitrate,'configuredBitrate':bitrate,'gop':30,'poolCapacity':3,'format':'nv12-video-range','rawCpuMapCallsInBridge':0}.items()):errors.append('actual surface configuration')
 finishes=[e for e in events if e['event']=='encoder-finish']
 if len(finishes)!=1 or finishes[0].get('frames')!=frames or not finishes[0].get('allCallbacksComplete'):errors.append('incomplete drain')
 for index in range(frames):
  per=[e for e in events if e.get('frame')==index];names=[e['event'] for e in per]
  required=['raster-submitted','conversion-complete','encoder-submit','encoder-callback']
  if any(names.count(n)!=1 for n in required):errors.append('frame event missing/duplicate '+str(index));continue
  if [names.index(n) for n in required]!=sorted(names.index(n) for n in required):errors.append('frame event order '+str(index))
  conv=per[names.index('conversion-complete')];submit=per[names.index('encoder-submit')];callback=per[names.index('encoder-callback')]
  if not conv.get('sameIOSurfacePlanes') or not(conv['surfaceId']==submit['surfaceId']==callback['surfaceId']):errors.append('surface ownership '+str(index))
  if callback.get('status')!=0 or callback.get('dropped') is not False:errors.append('callback failure/drop '+str(index))
  if 'import-bgra-complete' in names and not(names.index('import-bgra-complete')<names.index('conversion-complete')):errors.append('GPU import order '+str(index))
 return {'passed':not errors,'errors':errors,'frames':len(decoded),'keyframeIndices':keys,'maximumDecodedSpacing':max(spacing) if spacing else None,'requestedGop':30,'surfaceConfiguration':config,'encoderFinish':finishes,'zeroCopyProved':False}

if __name__=='__main__':
 video=pathlib.Path(sys.argv[1]);transfer=pathlib.Path(sys.argv[2]);bitrate=int(sys.argv[3]);output=pathlib.Path(sys.argv[4])
 args=['/opt/homebrew/bin/ffprobe','-v','error','-select_streams','v:0','-show_streams','-show_frames','-show_entries','stream=pix_fmt,color_range,color_space,color_transfer,color_primaries:frame=key_frame','-of','json',str(video)]
 raw=subprocess.run(args,check=True,capture_output=True);output.with_suffix('.ffprobe.json').write_bytes(raw.stdout)
 result=inspect(json.loads(raw.stdout),[json.loads(l) for l in transfer.read_text().splitlines()],bitrate);result['command']=args;output.write_text(json.dumps(result,indent=2));print(json.dumps({'passed':result['passed'],'errors':result['errors'],'maxGop':result['maximumDecodedSpacing']}));raise SystemExit(0 if result['passed'] else 1)
