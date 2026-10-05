"""CPU FFV1 process control; never invokes a hardware encoder."""
import json,signal,subprocess,sys,time
mode=sys.argv[1];argv=json.loads(sys.argv[2])
if mode=='broken-encoder':sys.stdin.buffer.read(1);raise SystemExit(8)
p=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=sys.stderr)
try:
    while b:=sys.stdin.buffer.read(4096):p.stdin.write(b);p.stdin.flush();time.sleep(.002)
    p.stdin.close();raise SystemExit(p.wait(timeout=20))
finally:
    if p.poll() is None:p.terminate();p.wait(timeout=2)
