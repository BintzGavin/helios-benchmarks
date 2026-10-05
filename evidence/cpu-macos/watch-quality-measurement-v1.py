import json, os, pathlib, subprocess, time
root=pathlib.Path(__file__).resolve().parent
watch=root/'quality-watch-v1'
watch.mkdir(exist_ok=False)
results=root/'quality-measurement-v1/results/full-v1'
command=['/usr/bin/python3','-B',str(root/'quality-measurement-v1/run.py'),'--run','--results',str(results)]
status=-99
started=time.perf_counter_ns()
try:
 with (watch/'stdout.log').open('wb') as out,(watch/'stderr.log').open('wb') as err:
  child=subprocess.Popen(command,stdout=out,stderr=err)
  (watch/'started.json').write_text(json.dumps({'watcherPid':os.getpid(),'runnerPid':child.pid,'command':command})+'\n')
  status=child.wait()
finally:
 (watch/'terminal.json').write_text(json.dumps({'exitCode':status,'measurementWallNs':time.perf_counter_ns()-started,'note':'Untimed saved-output quality measurement; this duration is not render performance.'})+'\n')
message='Saved-output CPU quality measurement finished (exit '+str(status)+'). Inspect '+str(watch/'terminal.json')+' and '+str(results/'manifest.json')+'. Verify all-frame PSNR/SSIM, exact cadence, own-reference/source bindings and original saved timer references. Preserve completed exports and failed attempts; do not rerun historical exports. Measurements are quality evidence, not performance results; JPEG quality and native rasterizer differences require disclosure before superiority claims. Continue local/scheduler CPU goal, final proportionate checks, merge proven gains and motion-graphics handoff. Amp is authenticated but no project resolved; Wrangler completion remains separate.'
fd=os.open(str(watch/'notification-attempted.json'),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as f:f.write(json.dumps({'threadId':'01a0e813-a2b5-78e0-978e-6a278c8e331e','singleAttempt':True})+'\n')
queue=['/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex','queue','--thread','01a0e813-a2b5-78e0-978e-6a278c8e331e','--message',message]
try:
 p=subprocess.run(queue,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=45)
 receipt={'exitCode':p.returncode,'delivered':p.returncode==0}
except subprocess.TimeoutExpired:receipt={'delivered':'unknown','error':'queue-timeout-no-retry'}
(watch/'notification-result.json').write_text(json.dumps(receipt)+'\n')
