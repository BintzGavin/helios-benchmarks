"""Remove only task-owned mux intermediates exactly reconstructable from saved MP4."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parent.parent;rows=[]
for bitstream in sorted((root/'comparison').rglob('*.h264')):
 if bitstream.stat().st_size<10_000_000:continue
 video=bitstream.parent/('output.mp4' if (bitstream.parent/'output.mp4').exists() else 'video.mp4')
 if not video.is_file():continue
 original=hashlib.file_digest(bitstream.open('rb'),'sha256').hexdigest()
 args=['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(video),'-map','0:v:0','-c:v','copy','-f','h264','-']
 p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE);digest=hashlib.sha256();n=0
 while True:
  b=p.stdout.read(1024*1024)
  if not b:break
  digest.update(b);n+=len(b)
 stderr=p.stderr.read().decode();code=p.wait();equal=code==0 and not stderr and n==bitstream.stat().st_size and digest.hexdigest()==original
 row={'intermediate':str(bitstream),'retainedVideo':str(video),'bytes':bitstream.stat().st_size,'intermediateSha256':original,'demuxSha256':digest.hexdigest(),'demuxBytes':n,'command':args,'returncode':code,'stderr':stderr,'byteExactReconstruction':equal,'removed':False}
 if equal:bitstream.unlink();row['removed']=True
 rows.append(row)
 (root/'checkpoint/mux-intermediate-reclamation.json').write_text(json.dumps({'scope':'task-owned duplicate elementary streams only; candidate MP4 and original clocks/receipts remain unchanged','checks':rows,'removedBytes':sum(x['bytes'] for x in rows if x['removed'])},indent=2))
print(json.dumps({'checked':len(rows),'removed':sum(x['removed'] for x in rows),'removedBytes':sum(x['bytes'] for x in rows if x['removed'])}))
