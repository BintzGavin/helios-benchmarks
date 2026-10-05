from pathlib import Path
import hashlib,json,subprocess,re,sys
pattern=re.compile(b"\x00{2,}\x01")
def nals(handle):
 buffer=b'';prefix=None
 while True:
  chunk=handle.read(1024*1024)
  if chunk:buffer+=chunk
  matches=list(pattern.finditer(buffer))
  if prefix is None and matches:
   first=matches[0];assert first.start()==0,'leading bytes not handled';prefix=first.group();buffer=buffer[first.end():];matches=list(pattern.finditer(buffer))
  for match in reversed(matches):
   pass
  while True:
   match=pattern.search(buffer)
   if not match:break
   payload=buffer[:match.start()];yield prefix,payload
   prefix=match.group();buffer=buffer[match.end():]
  if not chunk:
   if prefix is not None:yield prefix,buffer
   return
bitstream=Path(sys.argv[1]);video=Path(sys.argv[2]);receipt=Path(sys.argv[3])
original=hashlib.file_digest(bitstream.open('rb'),'sha256').hexdigest();metadata=[]
with bitstream.open('rb') as f:
 for prefix,payload in nals(f):metadata.append({'prefixHex':prefix.hex(),'payloadBytes':len(payload),'payloadSha256':hashlib.sha256(payload).hexdigest()})
args=['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(video),'-map','0:v:0','-c:v','copy','-f','h264','-']
p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE);reconstructed=hashlib.sha256();mismatches=[];count=0
for prefix,payload in nals(p.stdout):
 if count>=len(metadata):mismatches.append({'nal':count,'reason':'extra NAL'})
 else:
  m=metadata[count]
  if len(payload)!=m['payloadBytes'] or hashlib.sha256(payload).hexdigest()!=m['payloadSha256']:mismatches.append({'nal':count,'reason':'payload changed'})
  reconstructed.update(bytes.fromhex(m['prefixHex']));reconstructed.update(payload)
 count+=1
stderr=p.stderr.read().decode();code=p.wait()
if count!=len(metadata):mismatches.append({'reason':'NAL count differs'})
equal=code==0 and not stderr and not mismatches and reconstructed.hexdigest()==original
meta=bitstream.with_suffix('.h264-reconstruction.json');meta.write_text(json.dumps({'originalSha256':original,'nalMetadata':metadata,'recipe':'demux retained MP4 with saved command; substitute each original prefixHex before identical NAL payload; ordered SHA256 verifies exact original bytes','command':args,'retainedVideo':str(video),'provedReconstructedSha256':reconstructed.hexdigest(),'byteExactReconstruction':equal,'mismatches':mismatches},indent=2))
row={'intermediate':str(bitstream),'retainedVideo':str(video),'bytes':bitstream.stat().st_size,'intermediateSha256':original,'metadata':str(meta),'metadataSha256':hashlib.file_digest(meta.open('rb'),'sha256').hexdigest(),'nals':count,'byteExactReconstruction':equal,'removed':False}
if equal:bitstream.unlink();row['removed']=True
receipt.write_text(json.dumps(row,indent=2));print(json.dumps({"removed":row["removed"],"bytes":row["bytes"],"byteExactReconstruction":row["byteExactReconstruction"]}))
