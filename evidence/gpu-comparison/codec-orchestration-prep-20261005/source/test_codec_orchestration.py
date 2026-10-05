"""CPU dispatch/guard/profile-compile and retained codec integration tests."""
import copy,json,pathlib,subprocess,sys,time
import codec_orchestration as m
ROOT=m.ROOT;OUT=m.OUT;OUT.mkdir(exist_ok=False)
(OUT/'refusal-controls').mkdir();(OUT/'cpu-feed-controls').mkdir();(OUT/'prepared-profiles').mkdir();(OUT/'retained-codec-controls').mkdir()
results=[];config,ledger,inputpins=m.snapshot()
def result(name,**details):results.append({'test':name,'passed':True,'GPUExecuted':False,**details})
def refusal(name,func,reason):
 try:func()
 except Exception as e:
  assert reason in str(e),(name,str(e),reason);result(name,expectedReason=reason,observedReason=str(e));return
 raise AssertionError(name+' did not refuse')

for lane in config['lanes']:
 for mode in m.MODES:
  s=m.prepare(lane['id'],mode,OUT/'not-launched'/f"{lane['id']}-{mode}")
  assert s['codec']==lane['codec'] and s['frames']==(3 if mode.startswith('positive-') else 300)
  if lane['engine']=='Helios':
   assert s['nativeCommand'][12]==s['codec'] and len(s['nativeCommand'])==13
   assert s['binaryProtocol']==(9 if lane['backend']=='vulkan' else 7 if lane['codec']=='hevc' else 5)
   assert s['nativeCommand'][9]=='' and s['nativeCommand'][10:12]==['30','3']
  else:assert s['contexts']==3 and s['allocationThresholdPerContext']==64 and s['queue']==10
  (OUT/'refusal-controls'/f"SPEC-{lane['id']}-{mode}.json").write_text(json.dumps(s,indent=2)+'\n')
  result('dispatch-'+lane['id']+'-'+mode)
s=m.prepare('H-metal-hevc','hardware',OUT/'not-launched/guard-target')
for key,value,reason in [('codec','h264','CONTRACT_codec'),('binaryProtocol',5,'CONTRACT_binaryProtocol'),('encoderPool',1,'CONTRACT_encoderPool'),('gop',90,'CONTRACT_gop'),('width',256,'CONTRACT_width'),('bitrate',1,'CONTRACT_bitrate'),('liveGPUQualified',True,'QUALIFICATION_FLAG_OVERRIDE')]:
 bad=copy.deepcopy(s);bad[key]=value;refusal('guard-'+key,lambda:m.contract(bad),reason)
bad=copy.deepcopy(s);bad['helper']['sha256']='0'*64;refusal('guard-helper',lambda:m.contract(bad),'CONTRACT_helper')
bad=copy.deepcopy(s);bad['pins'][0]['sha256']='0'*64;refusal('guard-pins',lambda:m.contract(bad),'CONTRACT_ENVELOPE')
bad=copy.deepcopy(s);bad['producerDriver']='/tmp/arbitrary';refusal('guard-driver-replacement',lambda:m.contract(bad),'CONTRACT_ENVELOPE')
bad=m.prepare('H-metal-hevc','profile',OUT/'not-launched/profile-guard');bad['profile']['log']=str(m.CHILD/'hevc-evidence/qualification-01/hardware-profile.jsonl');refusal('guard-historical-profile-log',lambda:m.contract(bad),'PROFILE_SCOPE_OR_SOURCE')
refusal('disk-guard',lambda:m.budget_guard(s,9*m.GIB-1,{}),'DISK_GATE_9GIB')
entry=s['budgetEntries'][0];refusal('cap-guard',lambda:m.budget_guard(s,9*m.GIB,{entry['item']:entry['budgetBytes']+1}),'STAGE_CAP')
refusal('unknown-cap-guard',lambda:m.budget_guard(s,9*m.GIB,{'unplanned':1}),'STAGE_CAP')
refusal('mode-guard',lambda:m.prepare('H-metal-hevc','software',OUT/'not-launched/mode'),'MODE')
refusal('lane-guard',lambda:m.prepare('F-hevc','hardware',OUT/'not-launched/lane'),'LANE')
refusal('outside-output-guard',lambda:m.prepare('H-metal-hevc','hardware',ROOT/'comparison/outside'),'OUTPUT_SCOPE')
existing=OUT/'already-exists';existing.mkdir();(existing/'sentinel').write_text('preserved')
bad=m.prepare('H-metal-hevc','hardware',existing);refusal('existing-output',lambda:m.contract(bad),'EXISTING_OUTPUT');assert (existing/'sentinel').read_text()=='preserved'
argv=[sys.executable,str(pathlib.Path(m.__file__)),'H-metal-hevc','hardware',str(OUT/'not-launched/actual-cli'),'--execute']
p=subprocess.run(argv,capture_output=True,text=True,timeout=20);assert p.returncode==2;r=json.loads(p.stdout);assert r['processesLaunched']==0 and not r['GPUExecuted'] and 'DISK_GATE' in r['reason']
(OUT/'ACTUAL-CLI-REFUSAL.json').write_text(json.dumps({'command':argv,'exit':p.returncode,'stdout':r,'stderr':p.stderr},indent=2)+'\n');result('actual-cli-no-launch',reason=r['reason'])

# New libraries bind fresh logs; loading constructors is explicitly forbidden.
for lane in ['H-metal-hevc','H-vulkan-hevc']:
 spec=m.prepare(lane,'profile',OUT/'prepared-profiles'/lane)
 compile_receipt=m.compile_profile(spec);assert compile_receipt['exit']==0
 result('fresh-profile-compile-'+lane,libraryPin=compile_receipt['libraryPin'],libraryNeverLoaded=True)

font=config['scene']['font'];scene=ROOT/'checkpoint/codec_fixture_scene.mjs';helper=ROOT/'checkpoint/codec_fixture_helper.py';driver=ROOT/'checkpoint/native_codec_feed.mjs';node=pathlib.Path('/opt/homebrew/bin/node').resolve();python=pathlib.Path(sys.executable).resolve()
for backend,codec,protocol in [('metal','h264',5),('metal','hevc',7),('vulkan','h264',9),('vulkan','hevc',9)]:
 for mode in ['encode-binary','reference-binary','raster-binary']:
  name=f'{backend}-{codec}-{mode}';folder=OUT/'cpu-feed-controls'/name;folder.mkdir();lane=next(x for x in config['lanes'] if x['engine']=='Helios' and x['backend']==backend and x['codec']==codec)
  spec={'purpose':'CPU-feed-control','pythonExecutable':str(python),'command':[str(python),str(helper),mode,'256','128','30000','1001','20000000','/unused',backend+'-synthetic-trace','','30','3',codec],
        'recorderModule':lane['recorderModule'],'sceneModule':str(scene),'font':font,'protocol':protocol,'codec':codec,'backend':backend,'frames':3,'width':256,'height':128,'bitrate':20000000,'outputDirectory':str(folder),'benchmarkTiming':False,'taskSettings':{}}
  spec['pins']=[m.pin(x) for x in [python,node,helper,driver,scene,lane['recorderModule'],font['path']]]
  (folder/'SPEC.json').write_text(json.dumps(spec,indent=2)+'\n')
  with (folder/'raw-or-receipt.stdout').open('xb') as stdout,(folder/'driver.stderr.log').open('xb') as stderr:p=subprocess.run([str(node),str(driver),str(folder/'SPEC.json')],stdout=stdout,stderr=stderr,timeout=20)
  assert p.returncode==0,(name,(folder/'driver.stderr.log').read_text())
  receipt=json.loads((folder/'DRIVER.json').read_text());assert len(receipt['frames'])==3 and receipt['hardwareFlagsAreSynthetic'] and not receipt['GPUExecuted']
  assert [x['sha256'] for x in receipt['frames']]==receipt['nativeReceipt']['packetHashes'];result('cpu-feed-'+name)
  if backend=='metal' and codec=='hevc' and mode=='encode-binary':base=spec

for fault in ['wrong-protocol','wrong-codec','software-fallback','wrong-pool','wrong-gop','wrong-bitrate','raw-download','wrong-frame-count','early-exit']:
 folder=OUT/'cpu-feed-controls'/fault;folder.mkdir();s=copy.deepcopy(base);s.update(outputDirectory=str(folder),taskSettings={'CODEC_FIXTURE_FAULT':fault});(folder/'SPEC.json').write_text(json.dumps(s,indent=2)+'\n')
 with (folder/'stdout.log').open('xb') as stdout,(folder/'stderr.log').open('xb') as stderr:p=subprocess.run([str(node),str(driver),str(folder/'SPEC.json')],stdout=stdout,stderr=stderr,timeout=20)
 assert p.returncode!=0 and not (folder/'DRIVER.json').exists();result('cpu-receipt-refusal-'+fault)

for codec,name in [('h264','h264-video.mp4'),('hevc','video.mp4')]:
 r=m.conform_retained(ROOT/'comparison/native-conformance-prep-20261005/fixtures'/name,OUT/'retained-codec-controls'/codec,codec)
 assert r['exit']==0;result('retained-'+codec+'-shared-conformance')
report={'status':'CPU orchestration/profile preparation passed; actual GPU execution unqualified','testCount':len(results),'tests':results,'allOriginalInputPinsVerified':len(inputpins),'codecProtocols':[5,7,9],'newProfileLibrariesCompiled':2,'profileLibrariesNeverLoaded':True,'retainedCodecsConformed':['h264','hevc'],'GPUExports':0,'newCargoBuild':False,'timingWindowOpen':False,'benchmarkTiming':False,'activeSerialGateBytes':9*m.GIB,'streamingGateUnchanged':True,'noFrozenHelperOrSourceChanges':True,'actualGPULaunchIntegrationQualified':False,'remaining':['actual3-frame native codec/CPU-fallback refusal and profile-hooks controls onhardware','full3004K independent stage/ownership/reference/quality gates','native4K streaming bridge/resource acceptance','space and timing notification before benchmarks']}
(OUT/'TEST-REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'tests':len(results),'GPUExports':0}))
