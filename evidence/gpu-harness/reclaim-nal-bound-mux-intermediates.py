"""Retain exact Annex-B reconstruction metadata and prove its hash before reclaim."""
from pathlib import Path
import hashlib,json,subprocess,re
root=Path(__file__).resolve().parent.parent
pattern=re.compile(b'\x00{2,}\x01')
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
rows=[]
for bitstream in sorted((root/'comparison').rglob('*.h264')):
 if bitstream.stat().st_size<10_000_000:continue
 video=bitstream.parent/('output.mp4' if (bitstream.parent/'output.mp4').exists() else 'video.mp4')
 if not video.is_file():continue
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
 rows.append(row)
 (root/'checkpoint/mux-nal-intermediate-reclamation.json').write_text(json.dumps({'scope':'only task-owned duplicate elementary streams; complete exact-reconstruction metadata retained; candidate MP4 and original clocks unchanged','checks':rows,'removedBytes':sum(x['bytes'] for x in rows if x['removed'])},indent=2))
print(json.dumps({'checked':len(rows),'removed':sum(x['removed'] for x in rows),'removedBytes':sum(x['bytes'] for x in rows if x['removed'])}))
