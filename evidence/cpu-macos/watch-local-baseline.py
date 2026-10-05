import json,os,pathlib,subprocess,time
root=pathlib.Path(__file__).resolve().parent
run=root/'local-baseline-v1'
run.mkdir(exist_ok=False)
font=root/'source/fframes/render-bench/vs-remotion/fframes/media/DMSans-Regular.ttf'
command=['/usr/bin/python3','-B',str(root/'local-driver/run.py'),'--font',str(font),'--warmups','1','--timed','2','--results',str(root/'local-driver/results/baseline-v1')]
with (run/'stdout.log').open('wb') as out,(run/'stderr.log').open('wb') as err:
 started=time.perf_counter_ns()
 child=subprocess.Popen(command,stdout=out,stderr=err)
 (run/'started.json').write_text(json.dumps({'watcherPid':os.getpid(),'runnerPid':child.pid,'command':command,'study':'fresh-local-baseline-v1'})+'\n')
 status=child.wait()
 (run/'terminal.json').write_text(json.dumps({'exitCode':status,'studyWallNs':time.perf_counter_ns()-started,'note':'study duration includes setup and hashing; individual original render timers remain authoritative'})+'\n')
message='Fresh Helios CPU baseline finished (exit '+str(status)+'). Inspect '+str(run)+'/terminal.json and '+str(root/'local-driver/results/baseline-v1/manifest.json')+'. Use original external process timers and component stats to choose a measured improvement, then continue the local/scheduler/Remotion CPU goal. This is a fresh study; historical local temporary evidence is unavailable. No superiority claim follows from Helios-only timings. Defer broad tests until performance work ends; merge proven gains when done, then prepare the motion-graphics handoff.'
claim=run/'notification-attempted.json'
fd=os.open(str(claim),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as file:file.write(json.dumps({'threadId':'01a0e813-a2b5-78e0-978e-6a278c8e331e','singleAttempt':True})+'\n')
queue=['/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex','queue','--thread','01a0e813-a2b5-78e0-978e-6a278c8e331e','--message',message]
try:
 result=subprocess.run(queue,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=45)
 receipt={'exitCode':result.returncode,'delivered':result.returncode==0}
except subprocess.TimeoutExpired:receipt={'delivered':'unknown','error':'queue-timeout-no-retry'}
(run/'notification-result.json').write_text(json.dumps(receipt)+'\n')
