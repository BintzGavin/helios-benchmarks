"""Cross-renderer visual diagnostic, not an encoding-fidelity qualification."""
from pathlib import Path
import subprocess,json,numpy as np,hashlib
root=Path(__file__).resolve().parent.parent;refs=[root/'comparison/circles-reference-h/reference.mkv',root/'comparison/circles-common-reference-f-v2/reference.mkv'];out=root/'comparison/circles-cross-renderer-diagnostic';out.mkdir(exist_ok=True);frames=[];commands=[]
for engine,ref in zip(['H','F'],refs):
 args=['/opt/homebrew/bin/ffmpeg','-v','error','-threads','2','-i',str(ref),'-frames:v','1','-pix_fmt','yuv420p','-f','rawvideo','-'];commands.append(args);frames.append(subprocess.run(args,capture_output=True,check=True).stdout)
 args=['/opt/homebrew/bin/ffmpeg','-v','error','-y','-threads','2','-i',str(ref),'-frames:v','1',str(out/(engine+'-source-frame-3.png'))];commands.append(args);subprocess.run(args,check=True)
assert len(frames[0])==len(frames[1])==3840*2160*3//2
count=3840*2160;offset=0;planes=[]
for name,size in [('Y',count),('U',count//4),('V',count//4)]:
 a=np.frombuffer(frames[0],dtype=np.uint8,count=size,offset=offset).astype(np.int16);b=np.frombuffer(frames[1],dtype=np.uint8,count=size,offset=offset).astype(np.int16);delta=np.abs(a-b);planes.append({'plane':name,'meanAbsoluteDelta':float(delta.mean()),'differentBytes':int(np.count_nonzero(delta)),'greaterThan4Bytes':int(np.count_nonzero(delta>4)),'maximumDelta':int(delta.max())});offset+=size
(out/'diagnostic.json').write_text(json.dumps({'scope':'same scene/source-frame3, two lossless renderer references; Skia versions/AA/text may differ; not an encoding quality gate or pixel identity assertion','planes':planes,'commands':commands},indent=2));print(json.dumps(planes))
