"""Preserve every video path and byte via hardlinks after exact SHA256 equality."""
import pathlib,hashlib,os,json
root=pathlib.Path(__file__).resolve().parent.parent;seen={};checks=[];saved=0
for folder in ['comparison','deliverables']:
 for p in sorted((root/folder).rglob('*.mp4')):
  if not p.is_file() or p.is_symlink():continue
  before=p.stat();sha=hashlib.file_digest(p.open('rb'),'sha256').hexdigest();key=(before.st_size,sha)
  if key not in seen:seen[key]=p;continue
  canonical=seen[key];c=canonical.stat()
  if (before.st_dev,before.st_ino)==(c.st_dev,c.st_ino):continue
  temp=p.with_name(p.name+'.identical-link');os.link(canonical,temp);os.replace(temp,p)
  assert hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==sha
  if before.st_nlink==1:saved+=before.st_size
  checks.append({'path':str(p),'canonical':str(canonical),'sha256':sha,'bytes':before.st_size,'beforeInode':before.st_ino,'beforeMtimeNs':before.st_mtime_ns,'afterInode':p.stat().st_ino,'hardlinked':True,'bytesUnchanged':True})
 (root/'checkpoint/identical-video-hardlinks.json').write_text(json.dumps({'allPathsAndBytesRetained':True,'oldFilesystemMtimesRecorded':True,'checks':checks,'estimatedFreedBytes':saved},indent=2))
print(json.dumps({'hardlinked':len(checks),'estimatedFreedBytes':saved}))
