from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).parent
d=root/'vulkan-faults-03';d.mkdir(exist_ok=True)
helper=root/'helper-candidate-03'
rows=[]
def run(name,args,expected=0):
 p=subprocess.run(args,capture_output=True,timeout=45)
 (d/(name+'.stdout')).write_bytes(p.stdout);(d/(name+'.stderr')).write_bytes(p.stderr)
 assert p.returncode==expected,(name,p.returncode)
 return p
run('baseline-probe',[str(helper),'probe','hevc'])
run('baseline-api',['/opt/homebrew/bin/node',str(root/'check-fault-api.mjs'),str(helper),str(d/'baseline.mp4'),'pass'])
for kind in ['CPU','IMAGE','EXTENSION','FENCE']:
 lib=d/(kind.lower()+'.dylib')
 run('compile-'+kind,['/usr/bin/env','TMPDIR=/private/tmp','/usr/bin/xcrun','clang++','-std=c++17','-dynamiclib','-DFAIL_'+kind,'-I','/private/tmp/helios-vulkan-runtime-01a101cb/MoltenVK/MoltenVK/include',str(root/'fault-vulkan.mm'),'-L','/private/tmp/helios-vulkan-runtime-01a101cb/MoltenVK/MoltenVK/dynamic/dylib/macOS','-lMoltenVK','-Wl,-rpath,/private/tmp/helios-vulkan-runtime-01a101cb/MoltenVK/MoltenVK/dynamic/dylib/macOS','-o',str(lib)])
 wrapper=d/(kind.lower()+'-helper');wrapper.write_text('#!/bin/sh\nexec /usr/bin/env DYLD_INSERT_LIBRARIES='+str(lib)+' '+str(helper)+' "$@"\n');wrapper.chmod(0o755)
 if kind!='FENCE':
  p=run('native-'+kind,[str(wrapper),'probe','hevc'],1)
  assert b'VULKAN_INIT_FAILED' in p.stderr
 else:
  run('fence-probe-still-passes',[str(wrapper),'probe','hevc'])
 run('api-'+kind,['/opt/homebrew/bin/node',str(root/'check-fault-api.mjs'),str(wrapper),str(d/(kind.lower()+'-preserved.mp4')),'fail'])

 rows.append({'fault':kind,'rejected':True,'destinationPreserved':True,'librarySha256':hashlib.sha256(lib.read_bytes()).hexdigest()})
r={'baselinePassed':True,'controls':rows,'helperSha256':hashlib.sha256(helper.read_bytes()).hexdigest(),'softwareFallback':False}
(d/'REPORT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
