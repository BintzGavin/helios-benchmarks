"""Negative receipt tests using measured ledgers, not synthetic implementation copies."""
import copy,importlib.util,json,pathlib,tempfile,zlib,shutil,hashlib
root=pathlib.Path(__file__).resolve().parent.parent;r=root/'comparison/fframes-concurrent-nv12-20261004'
def mod(name,file):
 s=importlib.util.spec_from_file_location(name,root/'checkpoint'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
nv=mod('nv','audit-concurrent-nv12.py');gpu=mod('gpu','audit-concurrent-gpu.py');sp=mod('sp','audit-nv12-conformance.py');results=[]
core=[json.loads(l) for l in (r/'circles300/capture/handoff.jsonl').read_text().splitlines()];trace=[json.loads(l) for l in (r/'circles300/gpu-transfer.jsonl').read_text().splitlines()]
assert nv.audit_ledger(core)[0]['frames']==300
with tempfile.TemporaryDirectory(prefix='nv12-receipt-tests-',dir=root/'checkpoint') as name:
 t=pathlib.Path(name);(t/'capture').mkdir()
 def stages(c,g):
  (t/'capture/handoff.jsonl').write_text('\n'.join(json.dumps(x) for x in c)+'\n');(t/'gpu-transfer.jsonl').write_text('\n'.join(json.dumps(x) for x in g)+'\n');return gpu.stages(t)
 assert stages(core,trace)['frames']==300
 for event,key,value in [('conversion-begin','sourceFenceAlreadyCompleted',False),('conversion-complete','completed',False),('conversion-complete','sameDestinationIOSurfacePlanes',False),('conversion-complete','sameSourceTextureIOSurface',False),('conversion-complete','gpuStartSeconds',0),('source-avbuffer-owner-release','sourcePixelBuffer',0),('avbuffer-owner-release','surfaceId',0),('converter-create','poolThreshold',65)]:
  mutant=copy.deepcopy(trace);active=next(x['context'] for x in trace if x['event']=='conversion-begin' and x.get('index')==0)
  next(x for x in mutant if x['event']==event and (x.get('index')==0 if event!='converter-create' else x['context']==active))[key]=value
  try:stages(core,mutant)
  except (AssertionError,KeyError):results.append({'case':event+'/'+key,'rejected':True})
  else:raise AssertionError('accepted mutated stage '+key)
 # Actual source frame/segment order and codec-drain coverage must fail closed.
 for event,key,value in [('gpu-complete','sourceIndex',999),('encoder-send-return','segment',999),('encoder-send-return','success',False),('capture-complete','packedBytes',1)]:
  mutant=copy.deepcopy(core);next(x for x in mutant if x['event']==event)[key]=value
  try:nv.audit_ledger(mutant)
  except (AssertionError,KeyError):results.append({'case':event+'/'+key,'rejected':True})
  else:raise AssertionError('accepted mutated handoff '+key)
 # A real captured control differs by 3 codes: exceeds predetermined +/-1 tolerance.
 controls=t/'controls';shutil.copytree(r/'controls36/capture',controls)
 raw=bytearray(zlib.decompress((controls/'000000.nv12.zlib').read_bytes()));raw[0]=19;encoded=zlib.compress(raw);(controls/'000000.nv12.zlib').write_bytes(encoded)
 rows=[json.loads(l) for l in (controls/'handoff.jsonl').read_text().splitlines()];next(x for x in rows if x['event']=='capture-complete' and x['index']==0)['compressedBytes']=len(encoded)
 (controls/'handoff.jsonl').write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
 try:nv.audit(controls,True)
 except AssertionError:results.append({'case':'independent predetermined color oracle +3code corruption','rejected':True})
 else:raise AssertionError('accepted altered control pixel')
audit=json.loads((r/'circles300/SPS-FIELD-CADENCE-AUDIT.json').read_text());a,b=audit['fields']['old'],audit['fields']['new'];sp.compare(a,b)
for key,value in [('matrix_coefficients',6),('chroma_sample_loc_type_top_field',0),('timing_info_present_flag',1)]:
 mutant=copy.deepcopy(b);next(x for x in mutant if x[0]==key)[1]=value
 try:sp.compare(a,mutant)
 except AssertionError:results.append({'case':'SPS/'+key,'rejected':True})
 else:raise AssertionError('accepted other SPS change '+key)
# Current source/helper and archived source package are checked before test completion.
pins=json.loads((r/'BUILD-READY.json').read_text())
for x in pins['source']:assert nv.sha(pathlib.Path(pins['sourceDirectory'])/x['path'])==x['sha256']
for x in pins['helpers']:
 for key in ['path','immutableCopy']:assert nv.sha(pathlib.Path(x[key]))==x['sha256']
report={'passed':True,'negativeControls':results,'mutationsRejected':len(results),'baselineMeasured300StageAndLedgerPassed':True,'sourcePins':len(pins['source']),'helpers':len(pins['helpers']),'hardwareFaultControls':4,'hardwarePoolThresholdRetainedOwnerControl':'smoke3-02/gpu-transfer.jsonl','benchmarkTiming':False}
(r/'ACCEPTANCE-TESTS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
