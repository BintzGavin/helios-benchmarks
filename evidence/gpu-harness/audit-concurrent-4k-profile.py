import pathlib,json,collections,importlib.util,hashlib
root=pathlib.Path(__file__).resolve().parent.parent;r=root/'comparison/fframes-concurrent-nv12-20261004'
def module(name,file):
 s=importlib.util.spec_from_file_location(name,root/'checkpoint'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
nv=module('nv','audit-concurrent-nv12.py');gpu=module('gpu','audit-concurrent-gpu.py')
def transfer(lane):
 counts=collections.Counter();rawbytes=0;locks=[]
 with (r/lane/'interposer.jsonl').open() as f:
  for line in f:
   row=json.loads(line);counts[row['event']]+=1
   if row['event']=='texture-to-buffer':rawbytes+=row['bytes']
 assert counts['interposer-installed']==1
 return dict(counts),rawbytes
reports={}
for lane in ['profile4k300','positive4k3']:
 rows=[json.loads(x) for x in (r/lane/'capture/handoff.jsonl').read_text().splitlines()]
 cfg,plan,bindings=nv.audit_ledger(rows,download=lane=='positive4k3');assert (cfg['width'],cfg['height'])==(3840,2160)
 process=json.loads((r/lane/'process.json').read_text());assert process['returncode']==0 and process['binarySha256']=='665ce943531be9a35d61aa7629e12646e280d0568c1ca6a576816f15963210a8' and process['converterSha256']=='11522ab92e119b84f9af86b9abf5864263c774a21ac7505b82a6556b6e9e132d'
 assert (r/lane/'stderr-time-l.log').read_text().count('COMPARISON_ACTUAL_EXPORT_PATH=HardwareFrames')>=1
 stages=gpu.stages(r/lane);counts,rawbytes=transfer(lane)
 reports[lane]={'counts':counts,'rgbaDownloadBytes':rawbytes,'stages':{k:v for k,v in stages.items() if k!='indexedStages'},'pipeline':plan,'frames':cfg['frames'],'binarySha256':process['binarySha256'],'converterSha256':process['converterSha256'],'interposerSha256':nv.sha(r/'transfer-interposer.dylib'),'ledgerSha256':nv.sha(r/lane/'capture/handoff.jsonl'),'transferSha256':nv.sha(r/lane/'interposer.jsonl'),'processSha256':nv.sha(r/lane/'process.json')}
normal=reports['profile4k300'];positive=reports['positive4k3']
assert normal['frames']==300 and normal['stages']['actualConversionContexts']==3
assert not list((r/'profile4k300/capture').glob('*.nv12.zlib'))
for event in ['CVPixelBufferLockBaseAddress','IOSurfaceLock','texture-getBytes','texture-to-buffer']:assert normal['counts'].get(event,0)==0
assert positive['counts']['texture-to-buffer']==3 and positive['rgbaDownloadBytes']==3840*2160*4*3
assert positive['counts']['CVPixelBufferLockBaseAddress']==3 and positive['counts']['CVPixelBufferGetBaseAddressOfPlane']==6
out={'passed':True,'scope':'excluded full300 actual4K circles workload uncaptured, separate3 same4K positive controls','benchmarkTiming':False,'zeroCopyProved':False,'modifiedPipeline':True,'originalProduct':False,'fullWorkload':normal,'positiveControls':positive,'captureReadbackOff':True,'hookedRawDownloadsObserved':0,'opaqueDriverEncoderTransfersUnknown':True,'pointerQueriesAndBufferContentsIntentUnknown':True,'hookScope':'CV/IOSurface lock/pointer APIs and concrete probed Metal getBytes/texture-to-buffer selectors; unhooked paths unknown','actualMetalCapture':'256x128 capture3 retained and passed; separate4K capture ENOSPC failed/excluded, not counted','mandatorySPSConformanceRunsAfterProfilingExport':True}
(r/'FULL-4K-TRANSFER-PROFILE.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['fullWorkload','positiveControls']}));print(normal['counts']);print(positive['counts'])
