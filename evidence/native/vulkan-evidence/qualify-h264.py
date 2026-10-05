from pathlib import Path
import subprocess,json,hashlib,re,collections
r=Path(__file__).parent;d=r/'qualification-02';w=Path('/Users/gavinbintz/.codex/worktrees/gpu-vulkan-interop/helios/packages/portable');helper=r/'helper-candidate-03';log=d/'h264-profile.jsonl';assert not log.exists()
rows=[]
def run(name,args,data=None,output=None):
 with (output or d/('h264-'+name+'.stdout')).open('wb') as out,(d/('h264-'+name+'.stderr')).open('wb') as err:p=subprocess.run(args,input=data,stdout=out,stderr=err,timeout=90)
 rows.append({'name':name,'exit':p.returncode,'args':[str(x) for x in args]});(d/'h264-executions.json').write_text(json.dumps(rows,indent=2))
 assert p.returncode==0,(name,p.returncode)
ffmpeg='/opt/homebrew/bin/ffmpeg';ffprobe='/opt/homebrew/bin/ffprobe';lib=d/'h264-profile.dylib'
run('compile',['/usr/bin/env','TMPDIR=/private/tmp','/usr/bin/xcrun','clang++','-std=c++17','-dynamiclib','-fobjc-arc','-DHELIOS_PROFILE_VULKAN','-DHELIOS_PROFILE_PATH="'+str(log)+'"','-I','/private/tmp/helios-vulkan-runtime-01a101cb/MoltenVK/MoltenVK/include',str(w/'benchmarks/profile-gpu.mm'),'-L','/private/tmp/helios-vulkan-runtime-01a101cb/MoltenVK/MoltenVK/dynamic/dylib/macOS','-lMoltenVK','-Wl,-rpath,/private/tmp/helios-vulkan-runtime-01a101cb/MoltenVK/MoltenVK/dynamic/dylib/macOS','-framework','Foundation','-framework','Metal','-framework','CoreVideo','-framework','IOSurface','-o',str(lib)])
wrapper=d/'h264-profiled-helper';wrapper.write_text('#!/bin/sh\nexec /usr/bin/env DYLD_INSERT_LIBRARIES='+str(lib)+' '+str(helper)+' "$@"\n');wrapper.chmod(0o755)
run('api',['/opt/homebrew/bin/node',str(r/'prepare-qualification.mjs'),'encode-h264'])
run('direct-reference',[str(helper),'reference-binary','256','128','30000','1001','20000000','/unused',str(d/'h264-reference-trace.jsonl'),'','30','3','h264'],(d/'frames-300.bin').read_bytes(),d/'h264-reference.nv12')
assert (d/'h264-reference.nv12').read_bytes()==(d/'reference.nv12').read_bytes()
run('cadence',[ffprobe,'-v','error','-threads','1','-select_streams','v:0','-show_streams','-show_frames','-show_entries','frame=best_effort_timestamp,key_frame:stream=codec_name,width,height,pix_fmt,color_range,color_space,color_transfer,color_primaries,avg_frame_rate,time_base','-of','json',str(d/'h264-video.mp4')],output=d/'h264-cadence.json')
a=json.loads((d/'h264-cadence.json').read_text());s=a['streams'][0];assert len(a['frames'])==300 and s['codec_name']=='h264' and s['avg_frame_rate']=='30000/1001' and s['width']==256 and s['height']==128 and s['pix_fmt']=='yuv420p' and s['color_range']=='tv'
assert all(s[k]=='bt709' for k in ['color_space','color_transfer','color_primaries']);n,de=map(int,s['time_base'].split('/'))
for i,f in enumerate(a['frames']):assert f['best_effort_timestamp']*n*30000==i*1001*de
keyframes=[i for i,f in enumerate(a['frames']) if f['key_frame']];assert keyframes[0]==0 and max(b-a for a,b in zip(keyframes,keyframes[1:]))<=30
graph='[0:v]settb=1001/30000,setpts=N,split=2[a][b];[1:v]settb=1001/30000,setpts=N,split=2[c][d];[a][c]ssim=shortest=1:repeatlast=0:stats_file='+str(d/'h264-ssim.txt')+'[s];[b][d]psnr=shortest=1:repeatlast=0:stats_file='+str(d/'h264-psnr.txt')+'[p]'
run('quality',[ffmpeg,'-v','error','-filter_complex_threads','1','-threads','1','-i',str(d/'h264-video.mp4'),'-threads','1','-i',str(d/'reference.mkv'),'-filter_complex',graph,'-map','[s]','-map','[p]','-f','null','-'])
def stats(p):return [{k:float(v) for k,v in re.findall(r'([A-Za-z_]+):([\d.e+\-]+|inf)',line)} for line in p.read_text().splitlines()]
ss,ps=stats(d/'h264-ssim.txt'),stats(d/'h264-psnr.txt');assert len(ss)==len(ps)==300
for i,(a,b) in enumerate(zip(ss,ps)):assert a['n']==b['n']==i+1 and a['Y']>=.995 and b['psnr_y']>=40 and b['psnr_u']>=35 and b['psnr_v']>=35
vk=[json.loads(x) for x in (d/'h264-hardware-trace.jsonl.vulkan.jsonl').read_text().splitlines()];assert len(vk)==301 and [x['frame'] for x in vk[1:]]==list(range(300)) and all(vk[0][k] for k in ['sameImportedTexture','sameGpuRegistryId','metalObjects'])
trace=[json.loads(x) for x in (d/'h264-hardware-trace.jsonl').read_text().splitlines()];assert trace[0]['hardwareUsed'] and trace[0]['codec']=='h264' and trace[-1]['allCallbacksComplete'] and trace[-1]['frames']==300
counts=dict(collections.Counter(json.loads(x)['event'] for x in log.read_text().splitlines()));assert counts['VulkanQueueSubmitCommands']==counts['VulkanQueueSubmitFence']==300 and counts['VulkanFenceWaitComplete']>=300
transfers=['CVPixelBufferLockBaseAddress','IOSurfaceLock','MTLTextureGetBytes','MTLBlitTextureToBuffer','VulkanCopyImageToBuffer','VulkanCopyImageToBuffer2','VulkanCopyImageToBuffer2KHR'];assert sum(counts.get(k,0) for k in transfers)==0
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'status':'all300 Vulkan/H264 functional qualification passed; not a benchmark','helperSha256':sha(helper),'frames':300,'allDirectNv12FramesEqualByteBoundLosslessReference':True,'decodedCadenceColorGopPassed':True,'everyFrameUnchangedFloorsPassed':True,'minimumSsimY':min(x['Y'] for x in ss),'minimumPsnrY':min(x['psnr_y'] for x in ps),'minimumPsnrU':min(x['psnr_u'] for x in ps),'minimumPsnrV':min(x['psnr_v'] for x in ps),'hardwareUsed':True,'vulkanSubmissionAndFenceCounts':300,'profileEvents':counts,'hookedRawDownloadCalls':0,'profileSha256':sha(log),'interposerSha256':sha(lib),'profileSourceSha256':sha(w/'benchmarks/profile-gpu.mm'),'nv12Sha256':sha(d/'h264-reference.nv12'),'losslessReferenceSha256':sha(d/'reference.mkv'),'videoSha256':sha(d/'h264-video.mp4'),'zeroCopyProved':False,'opaqueDriverEncoderTransfers':'unknown','pointerAndMappedMemoryAccessIntent':'unknown','positiveControlsReceipt':'REPORT.json','clockClaim':None}
(d/'H264-REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
