import pathlib,subprocess,os,json,hashlib
root=pathlib.Path.cwd();out=root/'comparison/circles-f-chroma-diagnostic-02';out.mkdir(exist_ok=False)
producer=[str(root/'build/fframes-circles-claim/release/circles-adapter'),'raw-hardware',str(out/'unused.mp4'),str(root/'comparison/font'),'3','8000000']
encoder=['/opt/homebrew/bin/ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgra','-s','3840x2160','-r','30','-i','pipe:0','-c:v','ffv1','-level','3','-pix_fmt','bgr0','-frames:v','3',str(out/'raster-bgr0.mkv')]
with (out/'producer.stderr.log').open('w') as pe,(out/'reference.stderr.log').open('w') as ee:
 p=subprocess.Popen(producer,stdout=subprocess.PIPE,stderr=pe,env={**os.environ,'PATH':'/opt/homebrew/bin:/usr/bin:/bin'});e=subprocess.Popen(encoder,stdin=p.stdout,stderr=ee);p.stdout.close();ec=e.wait();pc=p.wait()
assert pc==ec==0
report={'scope':'excluded3-frame conversion diagnostic; not a replacement oracle and not a qualification; BGR channels retained, opaque alpha discarded','sourceFrames':[3,5],'producer':producer,'referenceCommand':encoder,'variants':[],'original500MbpsCandidateUnchanged':True}
for flags in ['bicubic','bilinear','area','neighbor']:
 for location in ['auto','left','center']:
  tag=flags+'-'+location
  scaler=f'scale=out_color_matrix=bt601:out_range=tv:flags={flags}:out_chroma_loc={location},format=yuv420p'
  graph=f'[0:v]trim=end_frame=3,setpts=N/30/TB,format=yuv420p[c];[1:v]{scaler},setpts=N/30/TB[r];[c][r]psnr=stats_file={tag}.psnr:stats_version=2'
  cmd=['/opt/homebrew/bin/ffmpeg','-v','error','-xerror','-i',str(root/'comparison/circles-screen-f-500/video.mp4'),'-i',str(out/'raster-bgr0.mkv'),'-filter_complex_threads','1','-filter_complex',graph,'-frames:v','3','-an','-f','null','-']
  r=subprocess.run(cmd,cwd=out,capture_output=True,text=True);(out/(tag+'.stderr.log')).write_text(r.stderr);log=out/(tag+'.psnr');rows=[]
  if log.exists():
   for line in log.read_text().splitlines():
    data=dict(item.split(':',1) for item in line.split() if ':' in item)
    if 'n' in data:rows.append({k:float(data[k]) for k in ['psnr_y','psnr_u','psnr_v']})
  report['variants'].append({'flags':flags,'location':location,'command':cmd,'returncode':r.returncode,'frames':rows,'minimum':{k:min(x[k] for x in rows) for k in ['psnr_y','psnr_u','psnr_v']} if rows else None})
(out/'diagnostic.json').write_text(json.dumps(report,indent=2));print(json.dumps([{'flags':r['flags'],'location':r['location'],'minimum':r['minimum']} for r in report['variants']]))
