"""All-frame pixel provenance, reference-only raw download, no color arithmetic."""
import json, hashlib, pathlib, subprocess, time
root=pathlib.Path(__file__).resolve().parent.parent
out=root/'comparison/circles-common-reference-f';ref=out/'reference.mkv'
binary=root/'build/fframes-current/release/circles-common-gpu-adapter'
md5args=['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(ref),'-pix_fmt','yuv420p','-f','framemd5','-']
decoded=subprocess.run(md5args,check=True,capture_output=True).stdout.decode();(out/'frames-v2.md5').write_text(decoded)
expected=[line.split(',')[-1].strip() for line in decoded.splitlines() if line and not line.startswith('#')];assert len(expected)==300
args=[str(binary),'reference',str(out/'direct-v2.mkv'),str(root/'comparison/font'),'300','500000000']
y=3840*2160;size=y*3//2;hashes=[];start=time.monotonic()
with (out/'direct-v2.stderr.log').open('wb') as stderr:
 process=subprocess.Popen(args,cwd=root,stdout=subprocess.PIPE,stderr=stderr)
 try:
  while True:
   chunks=[];count=0
   while count<size:
    chunk=process.stdout.read(size-count)
    if not chunk: break
    chunks.append(chunk);count+=len(chunk)
   if not count:break
   if count!=size:raise RuntimeError('partial NV12 frame')
   frame=b''.join(chunks);uv=frame[y:];digest=hashlib.md5();digest.update(frame[:y]);digest.update(uv[0::2]);digest.update(uv[1::2]);hashes.append(digest.hexdigest())
  code=process.wait()
 except BaseException:
  process.kill();process.wait();raise
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
mismatches=[{'frame':i,'sourceFrame':i+3,'direct':h,'reference':expected[i] if i<len(expected) else None} for i,h in enumerate(hashes) if i>=len(expected) or h!=expected[i]]
receipt={'status':'passed' if code==0 and len(hashes)==300 and not mismatches else 'failed','reference':str(ref),'referenceSha256':sha(ref),'executable':str(binary),'executableSha256':sha(binary),'converterSha256':sha(root/'sources/fframes-common-gpu/common-converter.dylib'),'referenceOriginallyCreatedUsingConverterV1':True,'bindingUsesFinalConverterV2':True,'sourceStart':3,'frames':len(hashes),'rawNv12Bytes':len(hashes)*size,'algorithm':'direct NV12 Y bytes then split even/odd UV bytes to planar U/V; MD5 of Y+U+V; no color arithmetic','commands':[md5args,args],'mismatches':mismatches,'directFrameMd5':hashes,'referenceFrameMd5':expected,'referenceOnlyRawDownload':True,'returncode':code,'excludedElapsedSeconds':time.monotonic()-start}
(out/'direct-byte-binding-v2.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({'status':receipt['status'],'frames':len(hashes),'mismatches':len(mismatches)}));assert receipt['status']=='passed'
