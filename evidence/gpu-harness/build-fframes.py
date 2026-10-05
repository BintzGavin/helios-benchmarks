import json, os, pathlib, signal, subprocess, time
root=pathlib.Path(__file__).resolve().parent.parent
argv=['cargo','build','--release','--locked','-p','vs-remotion-bench','--target-dir',str(root/'build/fframes')]
env=dict(os.environ,CARGO_HOME=str(root/'build/cargo-home'))
(root/'build/cargo-home').mkdir(parents=True,exist_ok=True)
out=(root/'checkpoint/fframes-build.stdout.log').open('w')
err=(root/'checkpoint/fframes-build.stderr.log').open('w')
proc=subprocess.Popen(argv,cwd=root/'sources/fframes',env=env,stdout=out,stderr=err,start_new_session=True)
receipt={'argv':argv,'pid':proc.pid,'cwd':str(root/'sources/fframes'),'cargo_home':env['CARGO_HOME'],'kind':'release-build','benchmark_timing':False,'status':'running'}
path=root/'checkpoint/fframes-build-process.json'
path.write_text(json.dumps(receipt,indent=2))
try:
    receipt['returncode']=proc.wait(timeout=1800)
    receipt['status']='completed' if receipt['returncode']==0 else 'failed'
except subprocess.TimeoutExpired:
    os.killpg(proc.pid,signal.SIGTERM)
    try: proc.wait(timeout=5)
    except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    receipt.update(status='stopped_at_checkpoint_limit',returncode=proc.returncode)
finally:
    out.close();err.close()
    path.write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
