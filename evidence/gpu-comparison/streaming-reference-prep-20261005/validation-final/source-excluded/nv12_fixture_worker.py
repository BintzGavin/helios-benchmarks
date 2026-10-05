"""CPU test subprocess only, with explicit fault controls and bounded input."""
import hashlib,json,os,pathlib,subprocess,sys,time

if sys.argv[1]=='producer':
    s=json.loads(pathlib.Path(sys.argv[2]).read_text());p=pathlib.Path(s['source']);size=s['width']*s['height']*3//2;n=s['frames'];fault=s.get('testControl','')
    ids=[];chunk_sizes=s.get('producerChunkSizes',[1,17,65521]);
    if not chunk_sizes or any(type(x)!=int or not 1<=x<=65536 for x in chunk_sizes):raise SystemExit(6)
    with p.open('rb') as f:
        for i in range(n):
            raw=f.read(size);ids.append({'index':i,'sourceIndex':i+s['sourceStart']})
            if fault=='short-boundary' and i==n-1:break
            if fault=='short-midframe' and i==n-1:raw=raw[:-1]
            if fault=='bad-source-byte' and i==0:raw=bytes([raw[0]^1])+raw[1:]
            offset=0;k=0
            while offset<len(raw):
                b=raw[offset:offset+chunk_sizes[k%len(chunk_sizes)]];sys.stdout.buffer.write(b);sys.stdout.buffer.flush();offset+=len(b);k+=1
        if fault=='extra-byte':sys.stdout.buffer.write(b'x');sys.stdout.buffer.flush()
        if fault=='extra-frame':sys.stdout.buffer.write(b'\0'*size);sys.stdout.buffer.flush()
    if fault=='duplicate-index':ids[-1]=ids[-2]
    if fault=='source-order':ids.reverse()
    sha=hashlib.sha256(p.read_bytes()).hexdigest()
    if fault=='producer-source-hash':sha='0'*64
    print(json.dumps({'kind':'copied-fixture-CPU-producer','frames':n,'sourceSha256':sha,'frameIdentities':ids}),file=sys.stderr,flush=True)
    if fault=='producer-failure':raise SystemExit(7)
elif sys.argv[1]=='encoder':
    fault=sys.argv[2];cmd=json.loads(sys.argv[3])
    if fault in ['broken-pipe','encoder-failure']:
        sys.stdin.buffer.read(1 if fault=='broken-pipe' else 65536);raise SystemExit(8)
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=sys.stderr)
    try:
        while b:=sys.stdin.buffer.read(4096):
            p.stdin.write(b);p.stdin.flush();time.sleep(.002)
        p.stdin.close();raise SystemExit(p.wait(timeout=10))
    except BaseException:
        if p.poll() is None:p.terminate();p.wait(timeout=3)
        raise
else:raise SystemExit(9)
