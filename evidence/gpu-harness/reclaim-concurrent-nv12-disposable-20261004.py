import pathlib,hashlib,json,shutil,time
root=pathlib.Path(__file__).resolve().parent.parent
cache=root/'build/fframes-current/release/deps';receipt=root/'checkpoint/CONCURRENT-NV12-DISPOSABLE-CACHE-RECLAMATION-20261004.json'
assert not receipt.exists()
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
build=json.loads((root/'comparison/fframes-concurrent-nv12-20261004/BUILD-READY.json').read_text())
protected=[pathlib.Path(x[k]) for x in build['helpers'] for k in ['path','immutableCopy']]
runtime=json.loads((root/'comparison/fframes-concurrent-nv12-20261004/EXACT-RUNTIME-PINS.json').read_text());protected += [pathlib.Path(x['resolvedPath']) for h in runtime['runtime'] for x in h['libraries'] if x['readableBytes']]
pins={str(p):digest(p) for p in protected}
paths=sorted(p for p in cache.iterdir() if p.suffix in {'.rlib','.rmeta'} and p.is_file() and not p.is_symlink());assert all(p.parent==cache and p not in protected for p in paths)
files=[{'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p),'kind':'inactive task-owned Cargo compiler rlib/rmeta; rebuildable; not loaded by frozen render helpers'} for p in paths]
before=shutil.disk_usage(root).free
r={'status':'prepared','createdUnix':time.time(),'scope':'exact build/fframes-current/release/deps .rlib/.rmeta files only','files':files,'freeBefore':before,'protectedRuntimePins':pins,'frozenEvidenceChanged':False,'timingWindowOpen':False}
receipt.write_text(json.dumps(r,indent=2)+'\n')
for p,x in zip(paths,files):
 assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256'];p.unlink();x['removed']=True
for p,hash_ in pins.items():assert digest(pathlib.Path(p))==hash_
after=shutil.disk_usage(root).free;r.update(status='completed',freeAfter=after,observedFreeGain=after-before,nominalRemovedBytes=sum(x['bytes'] for x in files),filesRemoved=len(files),protectedRuntimeRehashed=True,sourcesAndRegistryAndPrebuiltCachesUnchanged=True)
receipt.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['files','protectedRuntimePins']}))
