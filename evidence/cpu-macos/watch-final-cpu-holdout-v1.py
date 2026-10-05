import json, os, pathlib, subprocess, time
root=pathlib.Path(__file__).resolve().parent
watch=root/'final-cpu-holdout-watch-v1'
watch.mkdir(exist_ok=False)
study=root/'final-cpu-studies-v1'
results=study/'results/holdout/full-v1'
command=['/usr/bin/python3','-B',str(study/'run.py'),'--run','--mode','holdout','--medium-screen',str(study/'results/medium-screen/full-v1/manifest.json'),'--ul-screen',str(study/'results/ul-screen/full-v1/manifest.json'),'--results',str(results)]
status=-99
started=time.perf_counter_ns()
try:
 with (watch/'stdout.log').open('xb') as out,(watch/'stderr.log').open('xb') as err:
  child=subprocess.Popen(command,stdout=out,stderr=err)
  (watch/'started.json').write_text(json.dumps({'watcherPid':os.getpid(),'runnerPid':child.pid,'command':command})+'\n')
  status=child.wait()
finally:
 (watch/'terminal.json').write_text(json.dumps({'exitCode':status,'studyWallNs':time.perf_counter_ns()-started,'note':'Study duration includes untimed source bindings and every-frame quality; use original per-export deliveredWallNs for performance.'})+'\n')
message='Fresh CPU matched three-engine holdout finished (exit '+str(status)+'). Inspect '+str(watch/'terminal.json')+' and '+str(results/'manifest.json')+' plus original per-export process/component receipts and selected-profile manifest bindings. Verify three balanced timed rounds per engine/preset, all-frame own-reference fidelity, exact cadence, strict CPU stages, actual encoder settings and original delivered nanosecond timers. Preserve warmups, failures and fframes original/repaired artifacts; do not rerun completed historical exports. Do not mix screening medians into holdout superiority statistics. Report native rasterizer limits and hardware scope honestly, then run final proportionate checks, merge proven gains and finalize motion-graphics handoff. Continue the CPU-only local and scheduler goal; Amp project unresolved and Wrangler completion separate; no new R2 or production authorization inferred.'
fd=os.open(str(watch/'notification-attempted.json'),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as f:f.write(json.dumps({'threadId':'01a0e813-a2b5-78e0-978e-6a278c8e331e','singleAttempt':True})+'\n')
queue=['/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex','queue','--thread','01a0e813-a2b5-78e0-978e-6a278c8e331e','--message',message]
try:
 p=subprocess.run(queue,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=45)
 receipt={'exitCode':p.returncode,'delivered':p.returncode==0}
except subprocess.TimeoutExpired:receipt={'delivered':'unknown','error':'queue-timeout-no-retry'}
(watch/'notification-result.json').write_text(json.dumps(receipt)+'\n')
