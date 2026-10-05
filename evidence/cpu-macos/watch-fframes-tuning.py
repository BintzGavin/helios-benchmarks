import json,os,pathlib,subprocess,time,select
root=pathlib.Path(__file__).resolve().parent
run=root/'fframes-worker-watch-v1'
run.mkdir(exist_ok=False)
gate=root/'encoder-thread-watch-v1/terminal.json'
previous=json.loads((root/'encoder-thread-watch-v1/waiting.json').read_text())
(run/'waiting.json').write_text(json.dumps({'watcherPid':os.getpid(),'waitingForWatcherPid':previous['watcherPid'],'terminalGate':str(gate)})+'\n')
if not gate.exists():
 queue=select.kqueue()
 event=select.kevent(previous['watcherPid'],filter=select.KQ_FILTER_PROC,flags=select.KQ_EV_ADD|select.KQ_EV_ONESHOT,fflags=select.KQ_NOTE_EXIT)
 try:queue.control([event],1,None)
 except ProcessLookupError:pass
 finally:queue.close()
if not gate.exists() or json.loads(gate.read_text()).get('exitCode')!=0:
 (run/'terminal.json').write_text(json.dumps({'exitCode':None,'skipped':True,'reason':'preceding benchmark success gate not satisfied; no follow-on exports launched'})+'\n')
 raise SystemExit(0)
command=['/usr/bin/python3', '-B', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/fframes-worker-study-v1/run.py', '--run', '--results', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/fframes-worker-study-v1/results/full-v1']
with (run/'stdout.log').open('wb') as out,(run/'stderr.log').open('wb') as err:
 started=time.perf_counter_ns()
 child=subprocess.Popen(command,stdout=out,stderr=err)
 (run/'started.json').write_text(json.dumps({'watcherPid':os.getpid(),'runnerPid':child.pid,'command':command,'study':'fframes-worker-study-v1'})+'\n')
 status=child.wait()
 (run/'terminal.json').write_text(json.dumps({'exitCode':status,'studyWallNs':time.perf_counter_ns()-started,'note':'study duration includes setup and hashing; individual original render timers remain authoritative'})+'\n')
message='CPU fframes medium worker-count benchmark finished (exit '+str(status)+'); inspect /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/fframes-worker-watch-v1/terminal.json and /Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/fframes-worker-study-v1/results/full-v1/manifest.json with original per-run nanosecond timers, component receipts, source/output bindings and failed attempts. Preserve completed exports; no historical reruns. Settings/quality/cadence remain provisional; do not infer superiority from screening. Continue local and scheduler CPU goal, merge proven gains after final checks, then create motion-graphics handoff. Amp CLI sign-in is now verified; project availability was being resolved. Wrangler completion remains separate.'
claim=run/'notification-attempted.json'
fd=os.open(str(claim),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as file:file.write(json.dumps({'threadId':'01a0e813-a2b5-78e0-978e-6a278c8e331e','singleAttempt':True})+'\n')
queue=['/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex','queue','--thread','01a0e813-a2b5-78e0-978e-6a278c8e331e','--message',message]
try:
 result=subprocess.run(queue,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=45)
 receipt={'exitCode':result.returncode,'delivered':result.returncode==0}
except subprocess.TimeoutExpired:receipt={'delivered':'unknown','error':'queue-timeout-no-retry'}
(run/'notification-result.json').write_text(json.dumps(receipt)+'\n')
