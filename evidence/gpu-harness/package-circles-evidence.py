"""Package validated sources and raw receipts after the timing window closes."""
from pathlib import Path
import zipfile,hashlib,json,stat,os
root=Path(__file__).resolve().parent.parent;output=root/'deliverables/helios-gpu-4k-source-receipts-20261003.zip'
child=Path('/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94/binary-transport-evidence');selected={}
def add(path,name):
 path=Path(path)
 if path.is_file() or path.is_symlink():selected[name]=path
# Only task-owned circle/common receipts; omit candidate/reference media and host-private inventory.
for p in (root/'comparison').iterdir():
 if not(p.name.startswith(('circles','common','binary-transport','bitrate-budget','encoder-pool','implementation-pr'))):continue
 if p.is_file() and p.suffix in ['.json','.jsonl','.md','.log','.txt']:add(p,'comparison/'+p.name)
 elif p.is_dir():
  for f in p.rglob('*'):
   capture='actual-metal.gputrace' in f.parts
   if f.is_file() and (capture or f.suffix in ['.json','.jsonl','.md','.log','.txt','.md5']):add(f,str(f.relative_to(root)))
   elif capture and f.is_symlink():
    target=(f.parent/os.readlink(f)).resolve();assert root in target.parents;add(f,str(f.relative_to(root)))
for p in (root/'checkpoint').iterdir():
 if p.is_file() and (any(x in p.name for x in ['circles','circle','common','mux','identical-video','comparison_schedule']) or p.name=='UPSTREAM-GPU-CLAIM.md'):add(p,'checkpoint/'+p.name)
 elif p.is_dir() and any(x in p.name for x in ['fframes-circles','fframes-common']):
  for f in p.rglob('*'):
   if f.is_file():add(f,str(f.relative_to(root)))
for name in ['run_matrix.py','validate_video.py','DM-Sans.ttf']:
 p=root/'preparation/unpacked/helios-gpu-comparison-prep'/name;add(p,'harness/'+name)
for p in (root/'preparation/unpacked/helios-gpu-comparison-prep').iterdir():
 if p.is_file() and any(x in p.name.lower() for x in ['license','ofl','notice']):add(p,'harness/'+p.name)
for p in (root/'sources/fframes-common-gpu').iterdir():
 if p.is_file():add(p,'sources/fframes-common-gpu/'+p.name)
source=root/'sources/fframes-circles-claim'
for name in ['Cargo.toml','Cargo.lock','render-bench/vs-remotion/Cargo.toml','render-bench/vs-remotion/src/main.rs','render-bench/vs-remotion/src/bin/circles-adapter.rs','render-bench/vs-remotion/src/bin/circles-high-quality-adapter.rs','render-bench/vs-remotion/src/bin/circles-common-gpu-adapter.rs']:
 add(source/name,'sources/fframes-circles-claim/'+name)
for p in (root/'sources/fframes-current/fframes-skia-renderer').rglob('*.rs'):add(p,'sources/fframes-skia-renderer/'+str(p.relative_to(root/'sources/fframes-current/fframes-skia-renderer')))
for p in (root/'sources/fframes-current').iterdir():
 if p.is_file() and 'license' in p.name.lower():add(p,'sources/fframes/'+p.name)
add(root/'build/fframes-current/release/circles-common-gpu-adapter','frozen/circles-common-gpu-adapter')
for p in child.iterdir():
 if p.is_file():add(p,'helios-binary-transport-evidence/'+p.name)
for folder in ['smoke-02','mutations']:
 p=child/folder
 if p.exists():
  for f in p.rglob('*'):
   if f.is_file() and f.suffix in ['.json','.jsonl','.log','.txt']:add(f,'helios-binary-transport-evidence/'+str(f.relative_to(child)))
for name in ['REPRODUCE-CIRCLES.md','helios-gpu-comparison-results-20261003.md','LIBRARY-BLOCKER.json']:
 add(root/'deliverables'/name,name)
entries=[]
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name,p in sorted(selected.items()):
  if p.is_symlink():
   target=os.readlink(p);info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,target);entries.append({'name':name,'kind':'relative-symlink','target':target})
  else:
   z.write(p,name);entries.append({'name':name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()})
 z.writestr('PACKAGE-MANIFEST.json',json.dumps({'scope':'reproducible source/runtime package and original receipts; large videos/references retained separately on host','entries':entries},indent=2))
with zipfile.ZipFile(output) as z:assert z.testzip() is None;members=len(z.infolist())
receipt={'path':str(output),'bytes':output.stat().st_size,'sha256':hashlib.file_digest(output.open('rb'),'sha256').hexdigest(),'members':members,'zipCrcPassed':True,'sourceAndReceiptCount':len(entries),'librarySaved':False}
(root/'deliverables/circles-package-validation.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
