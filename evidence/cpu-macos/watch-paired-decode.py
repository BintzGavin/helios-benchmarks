import json,os,pathlib,subprocess,time
root=pathlib.Path(__file__).resolve().parent
run=root/'paired-decode-watch-v1'
run.mkdir(exist_ok=False)
font=root/'source/fframes/render-bench/vs-remotion/fframes/media/DMSans-Regular.ttf'
command=['/usr/bin/python3', '-B', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/paired-decode-export-v1/run.py', '--decode-threads', '8', '--results', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/paired-decode-export-v1/results/full-v1']
with (run/'stdout.log').open('wb') as out,(run/'stderr.log').open('wb') as err:
 started=time.perf_counter_ns()
 child=subprocess.Popen(command,stdout=out,stderr=err)
 (run/'started.json').write_text(json.dumps({'watcherPid':os.getpid(),'runnerPid':child.pid,'command':command,'study':'fresh-paired-decode-v1'})+'\n')
 status=child.wait()
 (run/'terminal.json').write_text(json.dumps({'exitCode':status,'studyWallNs':time.perf_counter_ns()-started,'note':'study duration includes setup and hashing; individual original render timers remain authoritative'})+'\n')
message='Paired CPU full-export decoder improvement benchmark finished (exit '+str(status)+'). Inspect '+str(root/'paired-decode-watch-v1/terminal.json')+' and '+str(root/'paired-decode-export-v1/results/full-v1/manifest.json')+' plus original pair records, component stats, source bindings and output hashes. Verify all three fresh pairs per preset and retain original timers. This benchmarks actual compiled availableParallelism cap8 source change against frozen one-thread baseline; no fframes/Remotion superiority follows yet. Continue local/scheduler/Remotion CPU performance, defer broad tests until performance work ends; merge proven gains when done, then create motion-graphics handoff. Wrangler browser sign-in was opened; inspect opaque login status only when user says complete.'
claim=run/'notification-attempted.json'
fd=os.open(str(claim),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as file:file.write(json.dumps({'threadId':'01a0e813-a2b5-78e0-978e-6a278c8e331e','singleAttempt':True})+'\n')
queue=['/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex','queue','--thread','01a0e813-a2b5-78e0-978e-6a278c8e331e','--message',message]
try:
 result=subprocess.run(queue,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=45)
 receipt={'exitCode':result.returncode,'delivered':result.returncode==0}
except subprocess.TimeoutExpired:receipt={'delivered':'unknown','error':'queue-timeout-no-retry'}
(run/'notification-result.json').write_text(json.dumps(receipt)+'\n')
