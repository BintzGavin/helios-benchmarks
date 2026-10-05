"""Sequential, retained prerequisites; exports here are excluded from comparison timings."""
import json, os, pathlib, subprocess, sys, time
root=pathlib.Path(__file__).resolve().parent.parent
env=dict(os.environ,PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin')
cli=['/opt/homebrew/bin/node','/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios/node_modules/tsx/dist/cli.mjs']
steps=[
 ('smoke-f-software',cli+[str(root/'checkpoint/export-comparison.mts'),'F','software',str(root/'comparison/smoke-f-software/video.mp4'),'3']),
 ('smoke-h-software',cli+[str(root/'checkpoint/export-comparison.mts'),'H','software',str(root/'comparison/smoke-h-software/video.mp4'),'3']),
 ('smoke-h-hardware',cli+[str(root/'checkpoint/export-comparison.mts'),'H','hardware',str(root/'comparison/smoke-h-hardware/video.mp4'),'3']),
 ('reference-f-software',cli+[str(root/'checkpoint/export-comparison.mts'),'F','reference-software',str(root/'comparison/reference-f-software/reference.mkv')]),
 ('reference-f-hardware',cli+[str(root/'checkpoint/export-comparison.mts'),'F','reference-hardware',str(root/'comparison/reference-f-hardware/reference.mkv')]),
 ('reference-r-software',cli+[str(root/'checkpoint/export-remotion.mts'),'reference-software',str(root/'comparison/reference-r-software/reference.mkv')]),
 ('screen-f-software',cli+[str(root/'checkpoint/export-comparison.mts'),'F','software',str(root/'comparison/screen-f-software/video.mp4')]),
 ('screen-f-hardware',cli+[str(root/'checkpoint/export-comparison.mts'),'F','hardware',str(root/'comparison/screen-f-hardware/video.mp4')]),
 ('screen-r-software',cli+[str(root/'checkpoint/export-remotion.mts'),'software',str(root/'comparison/screen-r-software/video.mp4')]),
]
journal=root/'comparison/setup.jsonl'
if journal.exists(): raise SystemExit('Setup already started; inspect receipts before resuming')
for name,argv in steps:
 log=root/'comparison'/f'{name}.log'; receipt={'step':name,'argv':argv,'benchmarkTiming':False,'startedUnix':time.time(),'status':'running'}
 with log.open('w') as stream:
  proc=subprocess.Popen(argv,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
  receipt['pid']=proc.pid
  (root/'comparison/setup-current.json').write_text(json.dumps(receipt,indent=2)+'\n')
  try: code=proc.wait(timeout=600)
  except subprocess.TimeoutExpired:
   import signal
   os.killpg(proc.pid,signal.SIGTERM); code=proc.wait(timeout=10)
  receipt.update(status='complete' if code==0 else 'failed',returncode=code,finishedUnix=time.time())
 with journal.open('a') as stream: stream.write(json.dumps(receipt)+'\n')
 (root/'comparison/setup-current.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'step':name,'status':receipt['status']}),flush=True)
 if code: raise SystemExit(code)
