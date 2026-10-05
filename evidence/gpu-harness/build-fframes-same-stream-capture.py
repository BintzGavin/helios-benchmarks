import hashlib, json, os, pathlib, signal, subprocess, time

root = pathlib.Path(__file__).resolve().parent.parent
source = root / 'sources/fframes-same-stream-capture'
logs = root / 'checkpoint/fframes-same-stream-capture'
logs.mkdir(exist_ok=True)
env = dict(os.environ, PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin', CARGO_HOME=str(root/'build/cargo-home'))
argv = ['/opt/homebrew/bin/cargo', 'build', '--release', '--locked', '-p', 'vs-remotion-bench', '--bin', 'circles-handoff-capture', '--bin', 'handoff-color-controls', '--target-dir', str(root/'build/fframes-current')]
receipt = {'sourceCommit': 'f89cbd572524b70a709ba3569fa23b0bbc8a0d9c', 'argv': argv, 'cwd': str(source), 'optimizedUsvgr': '1c2a088217eb3365e965fd8dbd62acf265a07d33', 'exactOriginalClaimSource': False, 'benchmarkTiming': False, 'status': 'running', 'startedUnix': time.time()}
path = logs / 'build-process.json'
with (logs/'build.stdout.log').open('w') as out, (logs/'build.stderr.log').open('w') as err:
    proc = subprocess.Popen(argv, cwd=source, env=env, stdout=out, stderr=err, start_new_session=True)
    receipt['pid'] = proc.pid
    path.write_text(json.dumps(receipt, indent=2)+'\n')
    try:
        receipt['returncode'] = proc.wait(timeout=1800)
        receipt['status'] = 'completed' if receipt['returncode'] == 0 else 'failed'
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL); proc.wait()
        receipt.update(status='stopped_at_build_limit', returncode=proc.returncode)
    receipt['finishedUnix'] = time.time()
    receipt['wallSeconds'] = receipt['finishedUnix']-receipt['startedUnix']
    path.write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt))
