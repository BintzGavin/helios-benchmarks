"""CPU subprocess integration of native ABI feed/raw/codec/profile supervision."""
import asyncio,copy,hashlib,json,pathlib,shutil,subprocess,sys,time
from unittest.mock import patch
import native_bridge_runner as m

ROOT=m.ROOT;OUT=m.OUT;OUT.mkdir(exist_ok=True)
for n in ['cases','fixtures','native-not-launched']: (OUT/n).mkdir(exist_ok=True)
fixtures=OUT/'fixtures';raw=fixtures/'reference.nv12';shutil.copy2(ROOT/'comparison/native-conformance-prep-20261005/fixtures/reference.nv12',raw)
assert m.sha(raw)==m.sha(ROOT/'comparison/native-conformance-prep-20261005/fixtures/reference.nv12')
originals={};elementary={};commands=[]
for codec,name,fmt in [('h264','h264-video.mp4','h264'),('hevc','video.mp4','hevc')]:
    src=fixtures/name;shutil.copy2(ROOT/'comparison/native-conformance-prep-20261005/fixtures'/name,src);originals[codec]=m.pin(src)
    target=fixtures/('reference.'+fmt)
    argv=[str(m.FFMPEG),'-v','error','-xerror','-n','-i',str(src),'-map','0:v:0','-c:v','copy','-f',fmt,str(target)]
    if not target.exists():
        r=subprocess.run(argv,capture_output=True,text=True,timeout=10);assert r.returncode==0 and not r.stderr
        commands.append({'argv':argv,'exit':r.returncode})
    else:commands.append({'argv':argv,'status':'retained prior successful same-source copy extraction, not repeated'})
    elementary[codec]=m.pin(target)

# CPU constructor only: no Metal, CoreVideo, Vulkan or encoder libraries.
source=fixtures/'cpu_profile.c';source.write_text('#include <stdlib.h>\n#include <fcntl.h>\n#include <unistd.h>\n__attribute__((constructor)) static void trace(void){const char *p=getenv("BRIDGE_CPU_PROFILE_LOG");if(!p)return;int fd=open(p,O_WRONLY|O_CREAT|O_EXCL,0600);if(fd>=0){write(fd,"CPU_PROFILE_CONSTRUCTOR_NO_GPU\\n",31);close(fd);}}\n')
lib=fixtures/'cpu_profile.dylib';cmd=['/usr/bin/xcrun','clang','-dynamiclib',str(source),'-o',str(lib)]
p=subprocess.run(cmd,capture_output=True,text=True,timeout=15,env={'PATH':'/usr/bin:/bin','TMPDIR':'/tmp'});assert p.returncode==0,p.stderr;commands.append({'argv':cmd,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'taskSettings':{'TMPDIR':'/tmp'},'CPUConstructorOnly':True})
profile_pin=m.pin(lib)
legacy,_,oldpins=m.old.snapshot()
font=legacy['scene']['font'];scene=ROOT/'checkpoint/codec_fixture_scene.mjs'
pins=[m.pin(p) for p in [m.DRIVER,m.HELPER,m.NODE,m.PYTHON,m.FFMPEG,m.FFPROBE,ROOT/'checkpoint/native_chroma_conformance.py',ROOT/'checkpoint/native_bridge_runner.py',ROOT/'checkpoint/native_bridge_encoder_fixture.py',pathlib.Path(__file__),scene,raw,lib,source]]
results=[]
def spec(mode='reference',codec='hevc',backend='metal',frames=300):
    lane=next(x for x in legacy['lanes'] if x['engine']=='Helios' and x['codec']==codec and x['backend']==backend)
    return {'executionClass':'subprocess-fixture','hardwareQualified':False,'realDeviceAccepted':False,'GPUExecuted':False,'mode':mode,'codec':codec,'backend':backend,'protocol':lane['binaryProtocol'],'width':256,'height':128,'frames':frames,'sourceStart':3,'fpsNum':30000,'fpsDen':1001,'bitrate':20000000,
            'timeoutSeconds':30,'outputCapBytes':32*1024*1024,'rawFixture':m.pin(raw),'elementaryFixture':elementary[codec],'font':font,'sceneModule':str(scene),'recorderModule':lane['recorderModule'],'pins':pins+[font,m.pin(lane['recorderModule']),elementary[codec]],'benchmarkTiming':False,'timingWindowOpen':False}
def independent(reference,receipt):
    argv=[str(m.FFMPEG),'-v','error','-xerror','-i',str(reference),'-pix_fmt','yuv420p','-fps_mode','passthrough','-f','rawvideo','-'];p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    pairs=[];y=256*128;size=y*3//2
    with raw.open('rb') as original:
        for i,row in enumerate(receipt['rows']):
            plane=bytearray()
            while len(plane)<size:
                b=p.stdout.read(size-len(plane));assert b;plane.extend(b)
            rebuilt=plane[:y]+bytearray(v for pair in zip(plane[y:y+y//4],plane[y+y//4:]) for v in pair)
            direct=original.read(size);assert direct==rebuilt
            assert row['index']==i and row['sourceIndex']==i+3
            assert hashlib.sha256(direct).hexdigest()==row['rawNv12Sha256']==row['inverseNv12Sha256']
            assert hashlib.md5(plane).hexdigest()==row['planarMd5']==row['decodedPlanarMd5']
            pairs.append({'index':i,'commandSourceIndex':i+3,'retainedRawFixtureOrdinal':i,'rawNv12Sha256':hashlib.sha256(direct).hexdigest(),'independentInverseSha256':hashlib.sha256(rebuilt).hexdigest(),'planarMd5':hashlib.md5(plane).hexdigest(),'equal':True})
    assert not p.stdout.read(1);err=p.stderr.read();assert p.wait(timeout=10)==0 and not err
    return {'status':'passed-subprocess-fixture','pairs':pairs,'frames':len(pairs),'reference':m.pin(reference),'decodeCommand':argv,'GPUExecuted':False,'noRenderedPixelCorrespondenceClaimed':True}

async def run(name,s,expected=None,prepare=None,cancel=False):
    folder=OUT/'cases'/name;folder.mkdir();dest=folder/'result'
    if prepare:prepare(dest)
    before=m.sha(raw);error=None;r=None;start=time.monotonic()
    try:
        if cancel:
            t=asyncio.create_task(m.run_job(s,dest));await asyncio.sleep(.2);t.cancel();await t
        else:r=await m.run_job(s,dest)
    except BaseException as e:error=type(e).__name__+':'+str(e)
    if expected:
        allowed=expected if isinstance(expected,list) else [expected];assert error and any(x in error for x in allowed),(name,error,expected)
        assert not (dest/'BINDING.json').exists()
        for p in folder.glob('attempt-*/FAILURE.json'):
            f=json.loads(p.read_text());assert f['allChildrenReaped'] and not f['publishedBinding'] and all(x['exit'] is not None for x in f['processes'])
        if (dest/'sentinel').exists():assert (dest/'sentinel').read_text()=='preserved'
    else:
        assert error is None,(name,error)
        assert r['allChildrenReaped'] and not r['hardwareQualified'] and not r['realDeviceAccepted'] and not r['GPUExecuted']
        assert all(x['sourceIndex']==i+3 for i,x in enumerate(r['producer']['frameIdentities']))
        if s['mode']=='reference':
            inverse=independent(dest/'reference.mkv',r);(folder/'INDEPENDENT-BINDING.json').write_text(json.dumps(inverse,indent=2)+'\n')
            if name=='reference-slow-300':assert r['backpressureObservations']>0 and r['producer']['rawForwardDrains']>0
        if s['mode'] in ['hardware','profile']:assert r['decodedInvariantFrames']==300 and r['candidate']['mandatoryConformanceAndMuxIncluded']
    assert m.sha(raw)==before
    item={'test':name,'passed':True,'expectedRefusal':expected,'observedError':error,'secondsExcludedFromBenchmark':time.monotonic()-start,'GPUExecuted':False,'sourceUnchanged':True,'publishedFixtureBinding':(dest/'BINDING.json').exists()}
    if r:item.update(frames=s['frames'],pythonMaxRSSBytes=r['pythonMaxRSSBytes'],maxPlanarWriterQueuedBytes=r['maxPlanarWriterQueuedBytes'],backpressureObservations=r['backpressureObservations'],producerRawForwardDrains=r['producer']['rawForwardDrains'],producerMaxForwardQueue=r['producer']['maxForwardQueue'])
    (folder/'TEST.json').write_text(json.dumps(item,indent=2)+'\n');results.append(item)

async def main():
    await run('reference-metal-hevc-300',spec())
    await run('reference-vulkan-h264-300',spec(codec='h264',backend='vulkan'))
    s=spec();s['testControl']='slow-encoder';await run('reference-slow-300',s)
    await run('rgba-three',spec(mode='rgba-control',frames=3))
    for codec in ['h264','hevc']:await run('encoded-'+codec+'-300',spec(mode='hardware',codec=codec))
    s=spec(mode='profile');s.update(profile={'kind':'CPU-only-constructor','libraryPin':profile_pin},trustedCpuProfilePin=profile_pin);await run('encoded-cpu-profile-300',s)
    reasons={'short-raw':['RAW_SHORT_FRAME','DRIVER_EXIT'],'extra-raw':['RAW_EXTRA_BYTES','DRIVER_EXIT'],'fail-after-raw':'DRIVER_EXIT','early-helper-exit':['RAW_SHORT_FRAME','DRIVER_EXIT'],'wrong-protocol':'DRIVER_EXIT','wrong-frame-count':'DRIVER_EXIT','wrong-packet-hash':'DRIVER_EXIT','pretend-real-hardware':'DRIVER_EXIT','reverse-driver-ledger':'PRODUCER_SOURCE_ORDER','broken-encoder':['BrokenPipeError','ConnectionResetError','ENCODER_EXIT'],'corrupt-reference':'DECODE_SHORT','corrupt-before-publish':'PREPUBLISH_HASH','fail-before-publish':'INJECTED_BEFORE_PUBLISH','race-destination':'File exists'}
    for fault,reason in reasons.items():s=spec(frames=3);s['testControl']=fault;await run(fault,s,reason)
    s=spec();s['testControl']='software-fallback';s['mode']='hardware';await run('software-fallback',s,'DRIVER_EXIT')
    s=spec(frames=3);s['testControl']='hang-helper';s['timeoutSeconds']=.5;await run('process-group-timeout',s,'TIMEOUT')
    s=spec(frames=3);s['testControl']='hang-helper';await run('process-group-cancellation',s,'CancelledError',cancel=True)
    s=spec(frames=3);s['outputCapBytes']=1;await run('output-cap',s,'ATTEMPT_OUTPUT_CAP')
    s=spec(frames=3);s['sourceStart']=0;await run('source-index-override',s,'FIXTURE_ENVELOPE')
    s=spec(frames=3);s['hardwareQualified']=True;await run('fixture-qualification-forgery',s,'EXECUTION_CLASS_NOT_AUTHORITY')
    s=spec(frames=3);s['pins'][0]['sha256']='0'*64;await run('runtime-pin-refusal',s,'PIN_MISMATCH')
    s=spec(frames=3);await run('existing-destination',s,'EXISTING_DESTINATION',lambda d:(d.mkdir(),(d/'sentinel').write_text('preserved')))
    s=spec(frames=3);await run('symlink-destination',s,'OUTPUT_SCOPE',lambda d:d.symlink_to(raw))
    # No actual native driver or profiling library is reachable.
    for lane in ['H-metal-hevc','H-metal-h264','H-vulkan-hevc','H-vulkan-h264']:
        for mode in ['hardware','reference','profile','positive-nv12','positive-rgba']:
            s=m.prepare_native(lane,mode,OUT/'native-not-launched'/f'{lane}-{mode}');(OUT/'native-not-launched'/f'{lane}-{mode}.json').write_text(json.dumps(s,indent=2)+'\n')
            try:m.validate(s,pathlib.Path(s['destination']))
            except m.Refusal as e:assert 'NATIVE_DISK_GATE' in str(e) or 'REAL_DEVICE_ACCEPTANCE_DISABLED' in str(e)
            else:raise AssertionError('native accepted')
            results.append({'test':'native-no-launch-'+lane+'-'+mode,'passed':True,'GPUExecuted':False,'nativeHelperStarted':False})
    n=m.prepare_native('H-metal-hevc','reference',OUT/'native-not-launched/forged');n['realDeviceAccepted']=True
    try:m.validate(n,pathlib.Path(n['destination']))
    except m.Refusal as e:assert 'FIXTURE_RECEIPT_CANNOT_AUTHORIZE_NATIVE' in str(e)
    else:raise AssertionError('forged native accepted')
    results.append({'test':'native-acceptance-forgery','passed':True,'GPUExecuted':False})
    report={'status':'native bridge source/process preparation passed with subprocess fixtures only','tests':results,'testCount':len(results),'sourceIndicesUsed':[3,302],'retainedRawFixtureIndices':[0,299],'noRenderedPixelCorrespondenceClaimed':True,'helperHardwareFlagsSynthetic':True,'all300IndependentBindings':3,'codedConformanceAndDecodedInvariance':{'h264':300,'hevc':300,'CPUProfileHEVC':300},'preparationCommands':commands,'CPUProfileLibrary':profile_pin,'GPUProfileLibrariesNeverLoaded':True,'GPUExports':0,'newCargoBuild':False,'realDeviceAccepted':False,'hardwareQualified':False,'nativeExecutionDisabled':True,'activeSerialGateBytes':9*1024**3,'activeBalancedGateBytes':15*1024**3,'streaming6GiBGateDisabled':True,'benchmarkTiming':False,'timingWindowOpen':False}
    (OUT/'TEST-REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'tests':len(results),'GPUExports':0}))

asyncio.run(main())
