import hashlib, json, os, pathlib, signal, subprocess, sys, time
root = pathlib.Path(__file__).resolve().parent.parent
evidence = root / 'comparison/fframes-original-handoff-20261004'
lane = sys.argv[1]
assert lane in ('controls', 'circles300')
out = evidence / lane
out.mkdir(exist_ok=False)
capture = out / 'capture'
if lane == 'controls':
    binary = evidence / 'handoff-color-controls'
    argv = [str(binary), str(out/'video.mp4'), str(capture)]
else:
    binary = evidence / 'circles-handoff-capture'
    argv = [str(binary), 'hardware', str(out/'video.mp4'), str(root/'comparison/font'), '300', '500000000']
pins = json.loads((evidence/'BUILD-PINS.json').read_text())
binary_sha = hashlib.sha256(binary.read_bytes()).hexdigest()
assert next(p['sha256'] for p in pins['helpers'] if p['path'] == str(binary)) == binary_sha
env = {**os.environ, 'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin', 'FFRAMES_HANDOFF_CAPTURE':str(capture)}
receipt = {'status':'running','lane':lane,'argv':argv,'resourceCommand':['/usr/bin/time','-l',*argv],
           'binarySha256':binary_sha,'buildPinsSha256':hashlib.sha256((evidence/'BUILD-PINS.json').read_bytes()).hexdigest(),
           'captureDirectory':str(capture),'benchmarkTiming':False,'timingWindowOpen':False,'startedUnix':time.time()}
path = out/'process.json'
with (out/'stdout.log').open('w') as stdout, (out/'stderr-time-l.log').open('w') as stderr:
    p = subprocess.Popen(['/usr/bin/time','-l',*argv],env=env,cwd=root,stdout=stdout,stderr=stderr,start_new_session=True)
    receipt['pid']=p.pid;path.write_text(json.dumps(receipt,indent=2)+'\n')
    try:
        receipt['returncode']=p.wait(timeout=1200)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
        receipt.update(returncode=p.returncode,timeout=True)
receipt.update(status='completed' if receipt['returncode']==0 else 'failed',finishedUnix=time.time())
if (out/'video.mp4').exists():receipt['videoSha256']=hashlib.sha256((out/'video.mp4').read_bytes()).hexdigest()
path.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
sys.exit(receipt['returncode']!=0)
