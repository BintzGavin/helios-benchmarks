import ctypes,hashlib,json,os,pathlib,shutil
r=pathlib.Path('comparison/fframes-concurrent-nv12-20261004/circles300');plan=json.loads((r/'FAILED-REFERENCE-STORAGE-PLAN.json').read_text());old=pathlib.Path(plan['old']);base=pathlib.Path(plan['new']);temp=r/'reference-failed-preserved-clone.tmp'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
assert not temp.exists() and not plan['applied'];expected=json.loads((r/'REFERENCE-ATTEMPT-01-EXCLUDED.json').read_text())['referenceSha256'];assert sha(old)==expected
bs=sha(base);st=old.stat();free=shutil.disk_usage(r).free;lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True);lib.clonefile.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int]
assert lib.clonefile(os.fsencode(base),os.fsencode(temp),0)==0,ctypes.get_errno()
try:
 with old.open('rb') as f,temp.open('r+b') as g:
  g.truncate(plan['oldBytes'])
  for b in plan['differentBlocks']:
   f.seek(b['offset']);raw=f.read(b['bytes']);assert hashlib.sha256(raw).hexdigest()==b['oldSha256'];g.seek(b['offset']);g.write(raw)
 os.chmod(temp,st.st_mode);os.utime(temp,ns=(st.st_atime_ns,st.st_mtime_ns));assert sha(temp)==expected and sha(base)==bs
 # Preserve original extended attributes as bytes; clonefile inherited base attributes.
 lib.listxattr.argtypes=[ctypes.c_char_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int]
 lib.getxattr.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint32,ctypes.c_int]
 lib.setxattr.argtypes=lib.getxattr.argtypes
 lib.removexattr.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int]
 def attrs(p):
  size=lib.listxattr(os.fsencode(p),None,0,0);assert size>=0;buf=ctypes.create_string_buffer(size);assert lib.listxattr(os.fsencode(p),buf,size,0)==size;values={}
  for name in buf.raw.split(b'\0'):
   if not name:continue
   n=lib.getxattr(os.fsencode(p),name,None,0,0,0);assert n>=0;v=ctypes.create_string_buffer(n);assert lib.getxattr(os.fsencode(p),name,v,n,0,0)==n;values[name]=v.raw
  return values
 original_attrs=attrs(old)
 for name in attrs(temp):
  if name not in original_attrs:assert lib.removexattr(os.fsencode(temp),name,0)==0
 for name,value in original_attrs.items():assert lib.setxattr(os.fsencode(temp),name,value,len(value),0,0)==0
 assert attrs(temp)==original_attrs
 os.replace(temp,old);assert sha(old)==expected and sha(base)==bs
 plan.update(applied=True,oldSha256=expected,baseSha256=bs,oldInode=st.st_ino,newInode=old.stat().st_ino,mtimePreserved=old.stat().st_mtime_ns==st.st_mtime_ns,bytesPreserved=True,freeBefore=free,freeAfter=shutil.disk_usage(r).free,storageMethod='APFS clone of correct reference, truncate, restore differing32KiB; invalid bytes retained exactly; inode/birthtime changed')
 (r/'FAILED-REFERENCE-STORAGE-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(plan))
finally:
 if temp.exists():temp.unlink()
