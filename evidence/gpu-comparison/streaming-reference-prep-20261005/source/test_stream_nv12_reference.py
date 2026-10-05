"""Actual CPU storage tests on copied retained bytes; no GPU launch."""
import asyncio,copy,hashlib,json,pathlib,shutil,subprocess,sys,time
import stream_nv12_reference as m

ROOT=m.ROOT;OUT=ROOT/'comparison/streaming-reference-prep-20261005'
OUT.mkdir(exist_ok=True);(OUT/'fixtures').mkdir(exist_ok=True);(OUT/'cases').mkdir(exist_ok=True)
RUN=OUT/'validation-final-03';RUN.mkdir(exist_ok=False)
CASES=OUT/'cases/validation-final-03';CASES.mkdir()
old=ROOT/'comparison/native-conformance-prep-20261005/fixtures/reference.nv12'
fixture=OUT/'fixtures/reference.nv12'
if not fixture.exists():shutil.copy2(old,fixture)
assert m.sha(old)==m.sha(fixture)
pins=[m.file_pin(p) for p in [fixture,m.WORKER,m.FFMPEG,m.FFPROBE,sys.executable,pathlib.Path(m.__file__),pathlib.Path(__file__)]]
rows=[];frame_bytes=256*128*3//2
with fixture.open('rb') as f:
    for i in range(300):rows.append({'index':i,'sourceIndex':i,'rawNv12Sha256':hashlib.sha256(f.read(frame_bytes)).hexdigest()})
base={'purpose':'copied-small-NV12-storage-test','width':256,'height':128,'frames':300,'fixtureFrames':300,'sourceStart':0,'fpsNum':30000,'fpsDen':1001,'source':str(fixture),'sourceSha256':m.sha(fixture),'expectedFrames':rows,'pins':pins,'encodedCapBytes':16*1024*1024,'timeoutSeconds':30,'benchmarkTiming':False,'timingWindowOpen':False}
results=[]
def case_spec(n=3):
    s=copy.deepcopy(base);s['frames']=n;s['expectedFrames']=s['expectedFrames'][:n];return s

def independently_decode(destination,s):
    """Independent consumer: read complete copied fixture directly, invert decoded planes with zip."""
    ref=destination/'reference.mkv';binding=json.loads((destination/'BINDING.json').read_text());y=s['width']*s['height'];size=y*3//2
    argv=[str(m.FFMPEG),'-v','error','-xerror','-i',str(ref),'-pix_fmt','yuv420p','-fps_mode','passthrough','-f','rawvideo','-']
    p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    pairs=[]
    with fixture.open('rb') as source:
        for i in range(s['frames']):
            decoded=bytearray()
            while len(decoded)<size:
                b=p.stdout.read(size-len(decoded));assert b,'short independent decode';decoded.extend(b)
            raw=source.read(size)
            # Scalar interleave expressed independently from producer split/coreinverse.
            rebuilt=decoded[:y]+bytearray(x for uv in zip(decoded[y:y+y//4],decoded[y+y//4:]) for x in uv)
            assert rebuilt==raw
            expected_md5=hashlib.md5(raw[:y]+bytes(raw[y::2])+bytes(raw[y+1::2])).hexdigest()
            br=binding['frames'][i]
            assert br['index']==i and br['sourceIndex']==i+s['sourceStart']
            assert hashlib.sha256(raw).hexdigest()==br['rawNv12Sha256']==br['inverseNv12Sha256']
            assert hashlib.md5(decoded).hexdigest()==br['planarMd5']==expected_md5
            pairs.append({'index':i,'sourceIndex':br['sourceIndex'],'directFixtureNv12Sha256':hashlib.sha256(raw).hexdigest(),'independentlyReconstructedNv12Sha256':hashlib.sha256(rebuilt).hexdigest(),'independentDecodedPlanarMd5':expected_md5,'equal':True})
    assert not p.stdout.read(1);err=p.stderr.read();rc=p.wait(timeout=10);assert rc==0 and not err
    receipt={'status':'passed','frames':len(pairs),'pairs':pairs,'referenceSha256':m.sha(ref),'copiedSourcePin':m.file_pin(fixture),'decodeCommand':argv,'decodeExit':rc,'noColorArithmetic':True,'GPUExecuted':False,'benchmarkTiming':False}
    (destination.parent/'INDEPENDENT-INVERSE-BINDING.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return binding

async def run(name,s,expected=None,prepare=None):
    folder=CASES/name;folder.mkdir();dest=folder/'result'
    if prepare:prepare(dest)
    before=m.sha(fixture);start=time.monotonic();error=None;binding=None
    try:binding=await m.run_reference(s,dest)
    except Exception as e:error=type(e).__name__+': '+str(e)
    elapsed=time.monotonic()-start
    if expected:
        allowed=expected if isinstance(expected,list) else [expected]
        assert error and any(reason in error for reason in allowed),(name,error,expected)
        assert not (dest/'BINDING.json').exists(),name
        if dest.exists() and (dest/'sentinel').exists():assert (dest/'sentinel').read_text()=='preserved competing destination'
        for fail in folder.glob('attempt-*/FAILURE.json'):
            r=json.loads(fail.read_text());assert not r['publishedBinding'] and all(c is not None for c in r['processExits'])
    else:
        assert error is None,(name,error)
        binding=independently_decode(dest,s)
        assert binding['status']=='passed' and binding['framesBound']==s['frames']
        if name=='slow-consumer-300':assert binding['backpressureObservations']>0
    assert m.sha(fixture)==before
    item={'case':name,'passed':True,'expectedRefusal':expected,'observedError':error,'secondsExcludedFromBenchmarks':elapsed,'sourceUnchanged':True,'GPUExecuted':False,'atomicFinalExists':(dest/'BINDING.json').exists()}
    if binding:item.update(frames=binding['framesBound'],maxWriterQueuedBytes=binding['maxWriterQueuedBytes'],drainCalls=binding['drainCalls'],backpressureObservations=binding['backpressureObservations'],selfMaxRSSBytes=binding['selfMaxRSSBytes'])
    (folder/'TEST.json').write_text(json.dumps(item,indent=2)+'\n');results.append(item)

async def main():
    await run('irregular-chunks-300',copy.deepcopy(base))
    s=case_spec(1);s['producerChunkSizes']=[1];await run('one-byte-chunks',s)
    s=copy.deepcopy(base);s['testControl']='slow-consumer';await run('slow-consumer-300',s)
    controls={'short-boundary':'SHORT_FRAME','short-midframe':'SHORT_FRAME','extra-byte':'EXTRA_BYTES','extra-frame':'EXTRA_BYTES','producer-failure':'PRODUCER_EXIT','bad-source-byte':'DIRECT_SOURCE_HASH','duplicate-index':'PRODUCER_SOURCE_ORDER','source-order':'PRODUCER_SOURCE_ORDER','producer-source-hash':'PRODUCER_SOURCE_ORDER','broken-pipe':['Pipe','ENCODER_EXIT','ConnectionResetError'],'encoder-failure':['Pipe','ENCODER_EXIT','ConnectionResetError'],'corrupt-reference':'REFERENCE_DECODE_SHORT','corrupt-before-commit':'PRECOMMIT_HASH','corrupt-binding':'PRECOMMIT_HASH','fail-before-commit':'INJECTED_BEFORE_COMMIT','race-destination':'File exists'}
    for fault,reason in controls.items():
        s=case_spec();s['testControl']=fault;await run(fault,s,reason)
    s=case_spec();s['encodedCapBytes']=1;await run('encoded-cap',s,'CAP')
    s=case_spec();s['timeoutSeconds']=.000001;await run('timeout',s,'TIMEOUT')
    s=case_spec();s['expectedFrames'][1]['sourceIndex']=8;await run('expected-order-guard',s,'EXPECTED_ORDER')
    s=case_spec();s['sourceSha256']='0'*64;await run('expected-source-guard',s,'SOURCE_HASH')
    s=case_spec();s['pins'][0]['sha256']='0'*64;await run('pin-guard',s,'PIN_MISMATCH')
    s=case_spec();s['width']=3840;s['height']=2160;await run('4k-refusal',s,'SMALL_ENVELOPE')
    s=case_spec();s['fixtureFrames']=301;await run('fixture-source-envelope',s,'SMALL_ENVELOPE')
    s=case_spec();s['purpose']='native-GPU-reference';await run('gpu-producer-refusal',s,'FIXTURE_ONLY')
    s=case_spec();await run('existing-directory',s,'EXISTING_DESTINATION',lambda d:(d.mkdir(),(d/'sentinel').write_text('preserved competing destination')))
    s=case_spec();await run('symlink-destination',s,'EXISTING_DESTINATION',lambda d:d.symlink_to(fixture))
    print(json.dumps({'status':'passed','tests':len(results),'all300IndependentBindings':True,'GPUExecuted':False}))
    report={'status':'bounded copied-fixture streaming storage tests passed','tests':results,'testCount':len(results),'positiveCases':sum(not x['expectedRefusal'] for x in results),'negativeCases':sum(bool(x['expectedRefusal']) for x in results),'pins':pins,'copiedSource':m.file_pin(fixture),'originalSource':m.file_pin(old),'all300IndependentInverseHashesEqual':True,'streaming6GiBGateStillProposed':True,'no4KReferenceQualification':True,'noGPUExportOrNativeBuild':True,'noBenchmarkTiming':True,'timingWindowOpen':False,'atomicPublication':'Darwin renameatx_np RENAME_EXCL directory; no-replace reference+binding+logs asone publication','memoryBound':'exact-frame reader, bounded asyncio pipes; no frame accumulation; one raw plus planar and quarter-frame split temporary; decoder inverse separatephase; RSS measured per positive receipt','sampleActualRawBytes':300*frame_bytes,'fourKRawBytesAvoidableIfQualified':3732480000,'full4KRuntimeMemoryNotMeasured':True}
    (RUN/'TEST-REPORT.json').write_text(json.dumps(report,indent=2)+'\n')

asyncio.run(main())
