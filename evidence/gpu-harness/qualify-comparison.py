import json, os, pathlib, subprocess, time
root=pathlib.Path(__file__).resolve().parent.parent
validator=root/'preparation/unpacked/helios-gpu-comparison-prep/validate_video.py'
env=dict(os.environ,PATH='/opt/homebrew/bin:/usr/bin:/bin')
pairs=[('f-software','F'),('f-hardware','F'),('r-software','R')]
receipts=[]
for name,engine in pairs:
 output=root/'comparison'/f'screen-{name}/video.mp4';ref=root/'comparison'/f'reference-{name}/reference.mkv';result=output.parent/'quality.json'
 argv=['/opt/homebrew/bin/python3',str(validator),str(output),'--reference',str(ref),'--engine',engine,'--reference-engine',engine,'--ssim-y','0.995','--psnr-y','40','--psnr-uv','35','--output',str(result)]
 start=time.time()
 with (output.parent/'quality-process.log').open('w') as log:
  p=subprocess.run(argv,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 receipts.append({'name':name,'argv':argv,'returncode':p.returncode,'startedUnix':start,'finishedUnix':time.time(),'benchmarkTiming':False})
 (root/'comparison/quality-process.json').write_text(json.dumps(receipts,indent=2)+'\n')
 print(json.dumps({'name':name,'returncode':p.returncode}),flush=True)
