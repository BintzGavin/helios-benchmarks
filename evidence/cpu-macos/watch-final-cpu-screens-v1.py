import json, os, pathlib, subprocess, time
root=pathlib.Path(__file__).resolve().parent
watch=root/'final-cpu-screens-watch-v1'
watch.mkdir(exist_ok=False)
records=[]
status=-99
try:
 for mode in ['medium-screen','ul-screen']:
  results=root/'final-cpu-studies-v1/results'/mode/'full-v1'
  command=['/usr/bin/python3','-B',str(root/'final-cpu-studies-v1/run.py'),'--run','--mode',mode,'--results',str(results)]
  started=time.perf_counter_ns()
  with (watch/(mode+'.stdout.log')).open('xb') as out,(watch/(mode+'.stderr.log')).open('xb') as err:
   child=subprocess.Popen(command,stdout=out,stderr=err)
   (watch/'started.json').write_text(json.dumps({'watcherPid':os.getpid(),'runnerPid':child.pid,'mode':mode,'command':command})+'\n')
   status=child.wait()
  record={'mode':mode,'exitCode':status,'studyWallNs':time.perf_counter_ns()-started,'manifest':str(results/'manifest.json'),'note':'Study duration includes untimed binding and quality checks; use original per-export deliveredWallNs for performance.'}
  records.append(record)
  (watch/(mode+'.terminal.json')).write_text(json.dumps(record)+'\n')
  if status!=0:break
finally:
 (watch/'terminal.json').write_text(json.dumps({'exitCode':status,'studies':records,'historicalExportsRerun':False})+'\n')
message='Fresh CPU final resource screens finished (exit '+str(status)+'). Inspect '+str(watch/'terminal.json')+' and '+str(root/'final-cpu-studies-v1/results')+' manifests and original per-export process/component receipts. Preserve original delivered nanosecond timers, failures and every saved output path. Verify all-frame own-reference fidelity, exact cadence and CPU stages; select only fully eligible settings, then launch the separately prepared matched three-engine holdout. Screening and measurement durations are not superiority results. Do not rerun completed historical exports. Continue local/scheduler CPU goal, final proportionate checks, merge proven gains, then motion-graphics handoff. Amp project remains unresolved; Wrangler completion is separate; no R2 or production authorization inferred.'
fd=os.open(str(watch/'notification-attempted.json'),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as f:f.write(json.dumps({'threadId':'01a0e813-a2b5-78e0-978e-6a278c8e331e','singleAttempt':True})+'\n')
queue=['/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex','queue','--thread','01a0e813-a2b5-78e0-978e-6a278c8e331e','--message',message]
try:
 p=subprocess.run(queue,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=45)
 receipt={'exitCode':p.returncode,'delivered':p.returncode==0}
except subprocess.TimeoutExpired:receipt={'delivered':'unknown','error':'queue-timeout-no-retry'}
(watch/'notification-result.json').write_text(json.dumps(receipt)+'\n')
