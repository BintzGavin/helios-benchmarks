"""Codec-aware launch preparation. GPU execution remains fail-closed/unqualified.

Frozen production settings are consumed read-only. No override of helper,
codec, geometry, protocol, concurrency or disk gate is exposed by the CLI.
"""
import argparse, hashlib, json, pathlib, re, shutil, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
PLAN=ROOT/'comparison/serial-4k-qualification-plan-20261005'
OUT=ROOT/'comparison/codec-orchestration-prep-20261005'
REPORT_SHA='af3a9e30b93ad7841dfd5f7c52735d423d77ed303e963f83392ca3d7f8498978'
GIB=1024**3
LIVE_GPU_QUALIFIED=False
MODES=('hardware','reference','profile','positive-nv12','positive-rgba')
CHILD=pathlib.Path('/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94')

class Refusal(RuntimeError):pass
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def pin(p):
 p=pathlib.Path(p).resolve();return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(p):
 f=pathlib.Path(p['path'])
 if not f.is_file() or f.stat().st_size!=p['bytes'] or sha(f)!=p['sha256']:raise Refusal('PIN_MISMATCH:'+str(f))
def snapshot():
 if sha(PLAN/'FINAL-REPORT.json')!=REPORT_SHA:raise Refusal('FROZEN_REPORT_CHANGED')
 report=json.loads((PLAN/'FINAL-REPORT.json').read_text())
 for k in ['configuration','resourceLedger','inputPins']:check(report[k])
 return json.loads((PLAN/'CONFIG.json').read_text()),json.loads((PLAN/'RESOURCE-LEDGER.json').read_text()),json.loads((PLAN/'EXACT-INPUT-PINS.json').read_text())['files']
def path_scope(path):
 p=pathlib.Path(path)
 if not p.is_absolute() or not p.parent.resolve().is_relative_to(OUT) or any(x.is_symlink() for x in [p,*p.parents]):raise Refusal('OUTPUT_SCOPE')
 if not re.fullmatch(r'[/A-Za-z0-9_.-]+',str(p)):raise Refusal('OUTPUT_CHARACTERS')
 return p

def prepare(lane_id,mode,directory):
 config,ledger,pins=snapshot()
 if mode not in MODES:raise Refusal('MODE')
 choices=[x for x in config['lanes'] if x['id']==lane_id]
 if len(choices)!=1:raise Refusal('LANE')
 out=path_scope(directory);lane=choices[0];frames=3 if mode.startswith('positive-') else 300
 def replace(arg):return arg.replace('{OUT}',str(out))
 spec={'lane':lane_id,'engine':lane['engine'],'codec':lane['codec'],'backend':lane['backend'],'mode':mode,'frames':frames,'width':3840,'height':2160,'fpsNum':30,'fpsDen':1,'sourceStart':3,'bitrate':300000000,'gop':30,'directory':str(out),'helper':lane['helper'],'workingDirectory':str(ROOT),'taskSettings':{},'producerDriver':str(ROOT/'checkpoint/native_codec_feed.mjs'),'producerDriverPin':pin(ROOT/'checkpoint/native_codec_feed.mjs'),'sceneModule':str(ROOT/'checkpoint/circles-scene.mts'),'scenePin':pin(ROOT/'checkpoint/circles-scene.mts'),'font':config['scene']['font'],'pins':pins,'minFreeBytes':ledger['retainedRawGateBytes'],'budgetEntries':ledger['entries'],'liveGPUQualified':False,'GPUExecuted':False,'benchmarkTiming':False,'timingWindowOpen':False,'executionEligible':False,'conformanceCommand':[replace(x) for x in lane['conformanceCommand']],'qualityCommand':[replace(x) for x in lane['qualityCommand']],'integrationScope':'commands/CPU refusals only; actual GPU/source/lifetime qualification pending'}
 if lane['engine']=='Helios':
  argv=[replace(x) for x in lane['nativeCommand']]
  argv[1]='reference-binary' if mode in ['reference','positive-nv12'] else 'raster-binary' if mode=='positive-rgba' else 'encode-binary'
  if argv[1]!='encode-binary':argv[7]='/unused'
  spec.update(nativeCommand=argv,binaryProtocol=lane['binaryProtocol'],encoderPool=3,recorderModule=lane['recorderModule'],rawOutput=mode in ['reference','positive-nv12','positive-rgba'],expectedRawBytes=frames*3840*2160*(4 if mode=='positive-rgba' else 3)//(1 if mode=='positive-rgba' else 2),muxCommand=[replace(x) for x in lane['muxCommand']])
  if mode in ['profile','positive-nv12','positive-rgba']:
   source=pathlib.Path(lane['recorderModule']).parents[1]/'benchmarks/profile-gpu.mm'
   log=out/'interposer.jsonl';lib=out/'transfer-interposer.dylib'
   compile_cmd=['/usr/bin/xcrun','clang++','-dynamiclib','-fobjc-arc','-std=c++17','-isysroot','/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk',f'-DHELIOS_PROFILE_PATH="{log}"']
   if lane['backend']=='vulkan':
    runtime='/private/tmp/helios-vulkan-runtime-01a101cb/MoltenVK/MoltenVK'
    compile_cmd+=['-DHELIOS_PROFILE_VULKAN','-I',runtime+'/include','-L',runtime+'/dynamic/dylib/macOS','-lMoltenVK','-Wl,-rpath,'+runtime+'/dynamic/dylib/macOS']
   compile_cmd += [str(source),'-framework','Foundation','-framework','Metal','-framework','CoreVideo','-framework','IOSurface','-o',str(lib)]
   spec['profile']={'compileCommand':compile_cmd,'sourcePin':pin(source),'library':str(lib),'log':str(log),'freshCompileRequired':True,'frozenHistoricalInterposerReuseAllowed':False,'constructorUsesGPU':True,'neverLoadInCPUControls':True}
   spec['taskSettings']['DYLD_INSERT_LIBRARIES']=str(lib)
 else:
  spec['nativeCommand']=[replace(x) for x in lane['command']];spec['nativeCommand'][4]=str(frames)
  spec['taskSettings']={k:replace(v) for k,v in lane['taskSettings'].items()}
  spec.update(converter=lane['converter'],contexts=3,generationWorkers=5,encoderWorkers=5,queue=10,segments=5,allocationThresholdPerContext=64,rawOutput=mode in ['reference','positive-nv12','positive-rgba'])
  if mode=='hardware' or mode=='profile':spec['taskSettings']['FFRAMES_CAPTURE_NO_DOWNLOAD']='1'
  if mode.startswith('positive-'):spec['taskSettings']['FFRAMES_NV12_POSITIVE_RGBA']='1' if mode=='positive-rgba' else '0'
  if mode=='profile' or mode.startswith('positive-'):
   library=ROOT/'comparison/fframes-concurrent-nv12-20261004/transfer-interposer.dylib'
   spec['profile']={'library':str(library),'libraryPin':pin(library),'log':str(out/'interposer.jsonl'),'runtimeLogSetting':'FFRAMES_EXTERNAL_TRANSFER_LOG','freshCompileRequired':False,'constructorUsesGPU':True,'neverLoadInCPUControls':True}
   spec['taskSettings'].update(DYLD_INSERT_LIBRARIES=str(library),FFRAMES_EXTERNAL_TRANSFER_LOG=str(out/'interposer.jsonl'))
 return spec

def contract(spec):
 lane=spec['lane'];out=path_scope(spec['directory']);mode=spec['mode']
 canonical=prepare(lane,mode,out)
 # Compare production contract to the read-only canonical configuration.
 for k in ['engine','codec','backend','width','height','frames','fpsNum','fpsDen','sourceStart','bitrate','gop','nativeCommand','helper','taskSettings','minFreeBytes','budgetEntries','conformanceCommand','qualityCommand']:
  if spec.get(k)!=canonical.get(k):raise Refusal('CONTRACT_'+k)
 for k in ['binaryProtocol','encoderPool','contexts','generationWorkers','encoderWorkers','queue','allocationThresholdPerContext']:
  if spec.get(k)!=canonical.get(k):raise Refusal('CONTRACT_'+k)
 if spec.get('profile')!=canonical.get('profile'):raise Refusal('PROFILE_SCOPE_OR_SOURCE')
 if spec.get('benchmarkTiming') is not False or spec.get('timingWindowOpen') is not False:raise Refusal('TIMING_DISABLED')
 if spec.get('liveGPUQualified') is not False:raise Refusal('QUALIFICATION_FLAG_OVERRIDE')
 if spec!=canonical:raise Refusal('CONTRACT_ENVELOPE')
 for key in ['producerDriverPin','scenePin','font']:check(spec[key])
 if spec.get('pins')!=canonical['pins']:raise Refusal('PIN_SET_CHANGED')
 for p in spec['pins']:check(p)
 if out.exists() or out.is_symlink():raise Refusal('EXISTING_OUTPUT')
 return canonical

def budget_guard(spec,free_bytes,stage_bytes):
 if free_bytes<spec['minFreeBytes']:raise Refusal('DISK_GATE_9GIB')
 caps={x['item']:x['budgetBytes'] for x in spec['budgetEntries']}
 for item,size in stage_bytes.items():
  if item not in caps or type(size) is not int or size<0 or size>caps[item]:raise Refusal('STAGE_CAP')
 if free_bytes<1024**3:raise Refusal('RESERVE')

def execute(spec):
 contract(spec);budget_guard(spec,shutil.disk_usage(ROOT).free,{})
 # Deliberately unqualified: actual small GPU integration is a separate future gate.
 if not LIVE_GPU_QUALIFIED:raise Refusal('ACTUAL_GPU_INTEGRATION_UNQUALIFIED_NO_LAUNCH')
 raise Refusal('LIVE_EXECUTION_NOT_ENABLED_IN_PREPARATION')

def compile_profile(spec):
 """Small CPU compiler operation only. Never dlopen or run the constructor."""
 contract(spec)
 if spec['engine']!='Helios' or 'profile' not in spec:raise Refusal('FRESH_NATIVE_PROFILE_ONLY')
 if shutil.disk_usage(ROOT).free<256*1024*1024:raise Refusal('SMALL_DISK_GATE')
 out=pathlib.Path(spec['directory']);out.mkdir(exist_ok=False)
 (out/'PREPARED-SPEC.json').write_text(json.dumps(spec,indent=2)+'\n')
 profile=spec['profile'];check(profile['sourcePin']);argv=profile['compileCommand']
 with (out/'compile.stdout.log').open('x') as stdout,(out/'compile.stderr.log').open('x') as stderr:
  p=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=30,env={'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin','TMPDIR':'/tmp'})
 result={'command':argv,'exit':p.returncode,'sourcePin':profile['sourcePin'],'compileOnly':True,'libraryNeverLoaded':True,'GPUConstructorExecuted':False,'GPUExecuted':False,'newCargoBuild':False,'benchmarkTiming':False,'intendedLogPath':profile['log'],'xcrunPin':pin('/usr/bin/xcrun'),'clangPin':pin('/Library/Developer/CommandLineTools/usr/bin/clang')}
 lib=pathlib.Path(profile['library'])
 if lib.exists():result['libraryPin']=pin(lib)
 (out/'COMPILE.json').write_text(json.dumps(result,indent=2)+'\n')
 if p.returncode or not lib.is_file() or lib.stat().st_size>2*1024*1024:raise Refusal('PROFILE_COMPILE')
 if profile['log'].encode() not in lib.read_bytes():raise Refusal('PROFILE_LITERAL_LOG_BINDING')
 if pathlib.Path(profile['log']).exists():raise Refusal('GPU_PROFILE_LOG_UNEXPECTEDLY_CREATED')
 check(profile['sourcePin']);return result

def conform_retained(source,directory,codec):
 """Small CPU-only integration of the unchanged shared adapter and codec guards."""
 source=pathlib.Path(source).resolve();out=path_scope(directory)
 fixtures=ROOT/'comparison/native-conformance-prep-20261005/fixtures'
 if source.parent!=fixtures or source.name not in ['h264-video.mp4','video.mp4'] or source.stat().st_size>2*1024*1024:raise Refusal('SMALL_RETAINED_SOURCE_ONLY')
 if codec!=('h264' if source.name=='h264-video.mp4' else 'hevc'):raise Refusal('FIXTURE_CODEC')
 if shutil.disk_usage(ROOT).free<256*1024*1024:raise Refusal('SMALL_DISK_GATE')
 config,_,_=snapshot();check(config['sharedConformanceAdapter']);out.mkdir(exist_ok=False)
 src=out/'original.mp4';shutil.copy2(source,src)
 argv=[sys.executable,config['sharedConformanceAdapter']['path'],str(src),str(out/'center.mp4'),'--codec',codec,'--receipt',str(out/'CONFORMANCE.json')]
 with (out/'process.stdout.log').open('x') as stdout,(out/'process.stderr.log').open('x') as stderr:
  p=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=30)
 result={'command':argv,'exit':p.returncode,'source':pin(source),'copiedSource':pin(src),'GPUExecuted':False,'benchmarkTiming':False,'timingWindowOpen':False}
 (out/'PROCESS.json').write_text(json.dumps(result,indent=2)+'\n')
 if p.returncode or sha(source)!=sha(src):raise Refusal('CONFORMANCE_INTEGRATION')
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('lane');p.add_argument('mode',choices=MODES);p.add_argument('directory');p.add_argument('--execute',action='store_true');a=p.parse_args()
 try:
  s=prepare(a.lane,a.mode,pathlib.Path(a.directory).absolute())
  if a.execute:execute(s)
  print(json.dumps(s,indent=2))
 except (Refusal,OSError) as e:print(json.dumps({'status':'refused','reason':str(e),'GPUExecuted':False,'processesLaunched':0}));raise SystemExit(2)
