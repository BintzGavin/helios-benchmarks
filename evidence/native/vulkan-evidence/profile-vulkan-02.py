from pathlib import Path
import subprocess,json,hashlib,collections
r=Path(__file__).parent;d=r/'profile-03';d.mkdir(exist_ok=True)
w=Path('/Users/gavinbintz/.codex/worktrees/gpu-vulkan-interop/helios/packages/portable')
helper=r/'helper-candidate-02';q=r/'qualification-01';executions=[]
def run(name,args,data=None,output=None):
 with (output or d/(name+'.stdout')).open('wb') as out,(d/(name+'.stderr')).open('wb') as err:p=subprocess.run(args,input=data,stdout=out,stderr=err,timeout=90)
 executions.append({'name':name,'exit':p.returncode,'args':[str(x) for x in args]});(d/'executions.json').write_text(json.dumps(executions,indent=2))
 assert p.returncode==0,(name,p.returncode)
def native(mode,output,trace):return [str(helper),mode,'256','128','30000','1001','20000000',str(output),str(trace),'','30','3','hevc']
profiles={}
for lane,mode,data,output in [('hardware','encode-binary',(q/'frames-300.bin').read_bytes(),d/'profiled-300.hevc'),('nv12-control','reference-binary',(q/'frames-3.bin').read_bytes(),d/'nv12.raw'),('rgba-control','raster-binary',(q/'frames-3.bin').read_bytes(),d/'rgba.raw')]:
 lib=d/(lane+'.dylib');log=d/(lane+'-profile.jsonl');assert not log.exists(),'Fresh profile required'
 run('compile-'+lane,['/usr/bin/env','TMPDIR=/private/tmp','/usr/bin/xcrun','clang++','-std=c++17','-dynamiclib','-fobjc-arc','-DHELIOS_PROFILE_VULKAN','-DHELIOS_PROFILE_PATH="'+str(log)+'"','-I','/private/tmp/helios-vulkan-runtime-01a101cb/MoltenVK/MoltenVK/include',str(w/'benchmarks/profile-gpu.mm'),'-L','/private/tmp/helios-vulkan-runtime-01a101cb/MoltenVK/MoltenVK/dynamic/dylib/macOS','-lMoltenVK','-Wl,-rpath,/private/tmp/helios-vulkan-runtime-01a101cb/MoltenVK/MoltenVK/dynamic/dylib/macOS','-framework','Foundation','-framework','Metal','-framework','CoreVideo','-framework','IOSurface','-o',str(lib)])
 trace=d/(lane+'-trace.jsonl')
 args=native(mode,output if lane=='hardware' else '/unused',trace)
 run(lane,['/usr/bin/env','DYLD_INSERT_LIBRARIES='+str(lib),*args],data,output if lane!='hardware' else None)
 rows=[json.loads(x) for x in log.read_text().splitlines()];counts=dict(collections.Counter(x['event'] for x in rows))
 assert counts.get('profiler-hooks-installed',0)>0 and counts.get('vulkan-profiler-hooks-installed',0)>0
 assert not counts.get('profiler-hooks-incomplete',0) and not counts.get('vulkan-profiler-hooks-incomplete',0)
 transfers=['CVPixelBufferLockBaseAddress','IOSurfaceLock','MTLTextureGetBytes','MTLBlitTextureToBuffer','VulkanCopyImageToBuffer','VulkanCopyImageToBuffer2','VulkanCopyImageToBuffer2KHR']
 profiles[lane]={'events':counts,'hookedRawDownloadTransfers':sum(counts.get(x,0) for x in transfers),'profileSha256':hashlib.sha256(log.read_bytes()).hexdigest(),'interposerSha256':hashlib.sha256(lib.read_bytes()).hexdigest()}
 if lane=='hardware':
  assert profiles[lane]['hookedRawDownloadTransfers']==0
  assert counts['VulkanQueueSubmitCommands']>=300 and counts['VulkanQueueSubmitFence']==300 and counts['VulkanFenceWaitComplete']>=300
 else:assert profiles[lane]['hookedRawDownloadTransfers']>=3
report={'status':'passed extended Vulkan and Metal transfer profile','helperSha256':hashlib.sha256(helper.read_bytes()).hexdigest(),'profileSourceSha256':hashlib.sha256((w/'benchmarks/profile-gpu.mm').read_bytes()).hexdigest(),'hardwareFrames':300,'positiveControlFrames':3,'profiles':profiles,'pointerAndMappedMemoryAccessIntent':'unknown','opaqueDriverEncoderTransfers':'unknown','zeroCopyProved':False,'profiledElementarySha256':hashlib.sha256((d/'profiled-300.hevc').read_bytes()).hexdigest(),'profiledOutputExcludedFromPerformance':True}
(d/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
