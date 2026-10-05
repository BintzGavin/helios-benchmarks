"""Bind final-reference decoded bytes to the same direct NV12 production stream.
Also quantify independent-render differences from the retained prior oracle.
"""
import pathlib,subprocess,json,hashlib,time,numpy as np
root=pathlib.Path(__file__).resolve().parent.parent;out=root/'comparison/circles-common-reference-f-v2';out.mkdir(exist_ok=False)
ref=out/'reference.mkv';old=root/'comparison/circles-common-reference-f/reference.mkv';binary=root/'build/fframes-current/release/circles-common-gpu-adapter';y=3840*2160;size=y*3//2
produce=[str(binary),'reference',str(out/'source.mkv'),str(root/'comparison/font'),'300','500000000']
oldargs=['/opt/homebrew/bin/ffmpeg','-v','error','-threads','2','-i',str(old),'-pix_fmt','yuv420p','-f','rawvideo','-']
encode=['/opt/homebrew/bin/ffmpeg','-v','error','-y','-filter_threads','1','-f','rawvideo','-pix_fmt','nv12','-s','3840x2160','-r','30','-i','pipe:0','-vf','setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709,format=yuv420p','-c:v','ffv1','-level','3','-threads','2','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-color_range','tv','-frames:v','300',str(ref)]
def exact(pipe):
 pieces=[];n=0
 while n<size:
  b=pipe.read(size-n)
  if not b:raise RuntimeError('partial/missing raw frame')
  pieces.append(b);n+=len(b)
 return b''.join(pieces)
hashes=[];differences=[];start=time.monotonic()
with (out/'producer.stderr.log').open('wb') as pe,(out/'encode.stderr.log').open('wb') as ee,(out/'old-decode.stderr.log').open('wb') as de:
 p=subprocess.Popen(produce,cwd=root,stdout=subprocess.PIPE,stderr=pe);e=subprocess.Popen(encode,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=ee);d=subprocess.Popen(oldargs,stdout=subprocess.PIPE,stderr=de)
 try:
  for index in range(300):
   nv12=exact(p.stdout);uv=nv12[y:];planar=nv12[:y]+uv[0::2]+uv[1::2];hashes.append(hashlib.md5(planar).hexdigest());previous=exact(d.stdout)
   if planar!=previous:
    a=np.frombuffer(planar,dtype=np.uint8).astype(np.int16);b=np.frombuffer(previous,dtype=np.uint8).astype(np.int16);delta=np.abs(a-b);nonzero=np.flatnonzero(delta)
    differences.append({'frame':index,'sourceFrame':index+3,'differentBytes':int(len(nonzero)),'maximumDelta':int(delta.max()),'firstByteOffsets':nonzero[:12].tolist(),'oldMd5':hashlib.md5(previous).hexdigest(),'newMd5':hashes[-1]})
   e.stdin.write(nv12)
  assert not p.stdout.read(1) and not d.stdout.read(1),'extra raw bytes';e.stdin.close();codes=[p.wait(),e.wait(),d.wait()];assert codes==[0,0,0],codes
 except BaseException:
  for process in [p,e,d]:process.kill();process.wait()
  raise
md5args=['/opt/homebrew/bin/ffmpeg','-v','error','-threads','2','-i',str(ref),'-pix_fmt','yuv420p','-f','framemd5','-'];md5=subprocess.run(md5args,check=True,capture_output=True).stdout.decode();(out/'frames.md5').write_text(md5)
expected=[l.split(',')[-1].strip() for l in md5.splitlines() if l and not l.startswith('#')];mismatch=[i for i,(a,b) in enumerate(zip(hashes,expected)) if a!=b];assert len(expected)==300
sha=lambda path:hashlib.file_digest(pathlib.Path(path).open('rb'),'sha256').hexdigest()
receipt={'status':'passed' if not mismatch else 'failed','reference':str(ref),'referenceSha256':sha(ref),'executableSha256':sha(binary),'converterSha256':sha(root/'sources/fframes-common-gpu/common-converter.dylib'),'frames':300,'sourceStart':3,'directFrameMd5':hashes,'referenceFrameMd5':expected,'mismatches':mismatch,'referenceOnlyRawDownload':True,'rawNv12Bytes':300*size,'algorithm':'same direct GPU NV12 stream: copy Y bytes and split even/odd UV to planar without arithmetic; independently hash decoded FFV1 output','commands':[produce,encode,oldargs,md5args],'returncodes':codes,'oldReference':str(old),'oldReferenceSha256':sha(old),'independentRenderDifferences':differences,'excludedElapsedSeconds':time.monotonic()-start,'oldReferenceAndCandidateClocksRetained':True}
(out/'direct-byte-binding.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({'status':receipt['status'],'frames':300,'mismatches':len(mismatch),'independentRenderDifferentFrames':len(differences),'differentBytes':sum(x['differentBytes'] for x in differences),'maxDelta':max([x['maximumDelta'] for x in differences],default=0)}));assert not mismatch
