"""Source-only native producer/codec runner, accepted with CPU subprocess fixtures.

The real-device branch is hard disabled. CPU receipts cannot activate it.
All gates and frozen implementations are consumed read-only.
"""
import argparse,asyncio,ctypes,hashlib,json,os,pathlib,resource,shutil,signal,sys,time,uuid
import codec_orchestration as old
import stream_nv12_reference as storage

ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=ROOT/'comparison/native-bridge-prep-20261005'
DRIVER=ROOT/'checkpoint/native_stdout_bridge.mjs'
HELPER=ROOT/'checkpoint/native_bridge_fixture.py'
NODE=pathlib.Path('/opt/homebrew/bin/node').resolve()
FFMPEG=pathlib.Path('/opt/homebrew/bin/ffmpeg').resolve()
FFPROBE=pathlib.Path('/opt/homebrew/bin/ffprobe').resolve()
PYTHON=pathlib.Path(sys.executable).resolve()
CHUNK=65536
LOG_CAP=1024*1024
FIXTURE_FREE=256*1024*1024

class Refusal(RuntimeError):pass
pin=old.pin
sha=old.sha

def prepare_native(lane,mode,destination):
    # Consume the previously frozen plan without writing in its scope.
    legacy=old.prepare(lane,mode,old.OUT/'not-launched/native-bridge-placeholder')
    if legacy['engine']!='Helios':raise Refusal('NATIVE_ONLY_F_UNCHANGED')
    dest=pathlib.Path(destination).absolute()
    if not dest.parent.resolve().is_relative_to(OUT/'native-not-launched'):raise Refusal('NATIVE_PLAN_SCOPE')
    oldpath=legacy['directory'];attempt=str(dest.parent/'{UNIQUE_ATTEMPT}')
    raw=mode in ['reference','positive-nv12','positive-rgba']
    def rebase(value):
        if isinstance(value,str):return value.replace(oldpath,attempt)
        if isinstance(value,list):return [rebase(x) for x in value]
        if isinstance(value,dict):return {k:rebase(x) for k,x in value.items()}
        return value
    return {'executionClass':'native-disabled','lane':lane,'mode':mode,'codec':legacy['codec'],'backend':legacy['backend'],'protocol':legacy['binaryProtocol'],
            'width':3840,'height':2160,'frames':legacy['frames'],'sourceStart':3,'fpsNum':30,'fpsDen':1,'bitrate':300000000,'gop':30,'encoderPool':3,
            'nativeCommand':[x.replace(oldpath,attempt) for x in legacy['nativeCommand']],'recorderModule':legacy['recorderModule'],'sceneModule':legacy['sceneModule'],'sceneFactory':'createCircles','font':legacy['font'],
            'driver':pin(DRIVER),'helper':legacy['helper'],'pins':legacy['pins'],'profile':rebase(legacy.get('profile')),'rawOutput':raw,'minFreeBytes':9*1024**3,'destination':str(dest),
            'hardwareQualified':False,'realDeviceAccepted':False,'GPUExecuted':False,'benchmarkTiming':False,'timingWindowOpen':False,'actualBridgeAcceptance':False,
            'nativeProtocolArgvReceiptChecksImplemented':True,'qualification':'real-device branch disabled until new scoped source acceptance, disk gate and actual device/reference/profile tests; no fixture can authorize it'}

def validate(s,destination):
    if s.get('executionClass')=='native-disabled':
        # Test/fixture flags are never interpreted as native acceptance.
        if s.get('hardwareQualified') is not False or s.get('realDeviceAccepted') is not False:raise Refusal('FIXTURE_RECEIPT_CANNOT_AUTHORIZE_NATIVE')
        if shutil.disk_usage(ROOT).free<9*1024**3:raise Refusal('NATIVE_DISK_GATE_9GIB_NO_LAUNCH')
        raise Refusal('REAL_DEVICE_ACCEPTANCE_DISABLED_NO_LAUNCH')
    if s.get('executionClass')!='subprocess-fixture' or s.get('hardwareQualified') is not False or s.get('realDeviceAccepted') is not False:raise Refusal('EXECUTION_CLASS_NOT_AUTHORITY')
    if any(type(s[k]) is not int for k in ['width','height','frames','sourceStart','fpsNum','fpsDen']):raise Refusal('INTEGER_CONTRACT')
    if (s['width'],s['height'],s['sourceStart'],s['fpsNum'],s['fpsDen'])!=(256,128,3,30000,1001) or not 1<=s['frames']<=300:raise Refusal('FIXTURE_ENVELOPE')
    if s['codec'] not in ['h264','hevc'] or s['backend'] not in ['metal','vulkan'] or s['protocol']!=(9 if s['backend']=='vulkan' else 7 if s['codec']=='hevc' else 5):raise Refusal('CODEC_PROTOCOL')
    if s['mode'] not in ['reference','hardware','profile','rgba-control']:raise Refusal('MODE')
    if s['mode'] in ['hardware','profile'] and s['frames']!=300:raise Refusal('RETAINED_ELEMENTARY_COUNT')
    if not 0<s['timeoutSeconds']<=30 or not 0<s['outputCapBytes']<=32*1024*1024:raise Refusal('TIME_OR_OUTPUT_CAP')
    if s.get('benchmarkTiming') is not False or s.get('timingWindowOpen') is not False:raise Refusal('NO_BENCHMARK')
    dest=pathlib.Path(destination)
    if not dest.is_absolute() or not dest.parent.resolve().is_relative_to(OUT/'cases') or any(p.is_symlink() for p in [dest,*dest.parents]):raise Refusal('OUTPUT_SCOPE')
    if dest.exists():raise Refusal('EXISTING_DESTINATION')
    if shutil.disk_usage(dest.parent).free<FIXTURE_FREE:raise Refusal('SMALL_DISK_GATE')
    for p in s['pins']:old.check(p)
    required=[str(p) for p in [DRIVER,HELPER,NODE,PYTHON,FFMPEG,FFPROBE,ROOT/'checkpoint/native_chroma_conformance.py']]+[s['recorderModule'],s['sceneModule'],s['font']['path'],s['rawFixture']['path']]
    if not set(required).issubset({p['path'] for p in s['pins']}):raise Refusal('MISSING_PIN')
    for key in ['rawFixture','elementaryFixture']:
        if key in s:
            old.check(s[key]);p=pathlib.Path(s[key]['path'])
            if not p.resolve().is_relative_to(OUT/'fixtures') or p.is_symlink():raise Refusal('FIXTURE_SOURCE_SCOPE')
    if pathlib.Path(s['rawFixture']['path']).stat().st_size!=14745600:raise Refusal('SOURCE_RAW_ENVELOPE')
    if s.get('profile'):
        p=s['profile']
        if p['kind']!='CPU-only-constructor' or p['libraryPin']!=s['trustedCpuProfilePin'] or not pathlib.Path(p['libraryPin']['path']).is_relative_to(OUT/'fixtures'):raise Refusal('NO_GPU_PROFILE_LIBRARY')
        old.check(p['libraryPin'])
    if s.get('taskSettings'):raise Refusal('NO_ARBITRARY_PROCESS_ENVIRONMENT')

class Supervisor:
    def __init__(self,attempt):self.attempt=attempt;self.processes=[];self.logs=[];self.commands=[]
    async def log(self,reader,path):
        size=0
        with path.open('xb') as f:
            while b:=await reader.read(CHUNK):
                size+=len(b)
                if size>LOG_CAP:raise Refusal('LOG_CAP')
                f.write(b)
    async def spawn(self,argv,label,stdin=False,stdout=False):
        p=await asyncio.create_subprocess_exec(*argv,stdin=asyncio.subprocess.PIPE if stdin else asyncio.subprocess.DEVNULL,stdout=asyncio.subprocess.PIPE if stdout else asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.PIPE,limit=CHUNK,start_new_session=True,cwd=ROOT,env={'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin','TMPDIR':'/tmp'})
        self.processes.append(p);self.commands.append({'label':label,'argv':argv,'pid':p.pid,'processGroup':p.pid,'spawnMonotonic':time.monotonic()})
        self.logs.append(asyncio.create_task(self.log(p.stderr,self.attempt/(label+'.stderr.log'))));return p
    async def run(self,argv,label):
        p=await self.spawn(argv,label,stdout=True)
        t=asyncio.create_task(self.log(p.stdout,self.attempt/(label+'.stdout.log')));self.logs.append(t)
        rc=await p.wait();await t
        if rc:raise Refusal(label.upper()+'_EXIT:'+str(rc))
        return p
    async def settle(self):
        await asyncio.gather(*self.logs)
    async def stop(self):
        # Kill owned process groups even if a driver exited while a descendant held a pipe.
        for p in self.processes:
            try:os.killpg(p.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        for p in self.processes:
            try:await asyncio.wait_for(p.wait(),1)
            except asyncio.TimeoutError:
                try:os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                await p.wait()
        # Do not let an already exited driver mask a descendant ignoring TERM.
        for p in self.processes:
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        await asyncio.gather(*self.logs,return_exceptions=True)
    def receipt(self):
        return [{**x,'exit':p.returncode} for x,p in zip(self.commands,self.processes)]

def ffv1_command(s,path):
    tags=['-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-chroma_sample_location','center']
    return [str(FFMPEG),'-v','error','-xerror','-n','-f','rawvideo','-pix_fmt','yuv420p','-s',f"{s['width']}x{s['height']}",'-r',f"{s['fpsNum']}/{s['fpsDen']}",*tags,'-i','pipe:0','-c:v','ffv1','-level','3','-threads','2','-pix_fmt','yuv420p',*tags,'-frames:v',str(s['frames']),str(path)]

async def run_job(s,destination):
    validate(s,destination);dest=pathlib.Path(destination);attempt=dest.parent/('attempt-'+uuid.uuid4().hex);attempt.mkdir()
    manager=Supervisor(attempt);n=s['frames'];y=s['width']*s['height'];frame_bytes=y*3//2
    mode='reference-binary' if s['mode']=='reference' else 'raster-binary' if s['mode']=='rgba-control' else 'encode-binary'
    command=[str(PYTHON),str(HELPER),mode,str(s['width']),str(s['height']),str(s['fpsNum']),str(s['fpsDen']),'20000000',str(attempt/('elementary.h265' if s['codec']=='hevc' else 'elementary.h264')),str(attempt/'gpu-transfer-not-actual.jsonl'),'','30','3',s['codec']]
    issued={**s,'python':str(PYTHON),'nativeCommand':command,'attemptDirectory':str(attempt)}
    if issued.get('profile'):issued['profile']={**issued['profile'],'log':str(attempt/'cpu-profile.jsonl')}
    spec_file=attempt/'ISSUED-SPEC.json';spec_file.write_text(json.dumps(issued,indent=2)+'\n')
    receipt={'status':'running','executionClass':'subprocess-fixture','hardwareQualified':False,'realDeviceAccepted':False,'GPUExecuted':False,'benchmarkTiming':False,'timingWindowOpen':False,'mode':s['mode'],'codec':s['codec'],'backend':s['backend'],'sourceIndices':[s['sourceStart'],s['sourceStart']+n-1],'rows':[],'maxPlanarWriterQueuedBytes':0,'backpressureObservations':0,'drainCalls':0,'referenceOnlyReadbackBytes':0,'nativeProducerBridgeRealDeviceQualified':False}
    async def monitor():
        while True:
            if shutil.disk_usage(attempt).free<FIXTURE_FREE:raise Refusal('SMALL_DISK_RESERVE')
            size=0
            for p in attempt.iterdir():
                # The conformance writer atomically renames its private staging
                # file. Vanished entries are expected; all other I/O errors fail.
                try:
                    if p.is_file():size+=p.stat().st_size
                except FileNotFoundError:continue
            if size>s['outputCapBytes']:raise Refusal('ATTEMPT_OUTPUT_CAP')
            for t in manager.logs:
                if t.done() and t.exception():raise t.exception()
            await asyncio.sleep(.02)
    async def verify_producer():
        p=attempt/'PRODUCER.json'
        if not p.is_file() or p.stat().st_size>LOG_CAP:raise Refusal('PRODUCER_RECEIPT_ENVELOPE')
        result=json.loads(p.read_text())
        if result.get('executionClass')!='subprocess-fixture' or result.get('hardwareQualified') is not False or result.get('realDeviceAccepted') is not False or result.get('GPUExecuted') is not False:raise Refusal('PRODUCER_CANNOT_AUTHORIZE_HARDWARE')
        ids=result['frameIdentities']
        if len(ids)!=n or any(row['index']!=i or row['sourceIndex']!=s['sourceStart']+i for i,row in enumerate(ids)):raise Refusal('PRODUCER_SOURCE_ORDER')
        receipt['producer']=result
        if s.get('profile'):
            log=attempt/'cpu-profile.jsonl'
            if not log.is_file() or log.read_text().strip()!='CPU_PROFILE_CONSTRUCTOR_NO_GPU':raise Refusal('CPU_PROFILE_LOG_BINDING')
        return result
    async def decode_reference(path):
        dec=await manager.spawn([str(FFMPEG),'-v','error','-xerror','-i',str(path),'-pix_fmt','yuv420p','-fps_mode','passthrough','-f','rawvideo','pipe:1'],'reference-decode',stdout=True)
        for row in receipt['rows']:
            try:plane=await dec.stdout.readexactly(frame_bytes)
            except asyncio.IncompleteReadError as e:raise Refusal('DECODE_SHORT') from e
            if hashlib.md5(plane).hexdigest()!=row['planarMd5']:raise Refusal('DECODE_HASH')
            inverse=bytearray(frame_bytes);inverse[:y]=plane[:y]
            for j in range(y//4):inverse[y+2*j]=plane[y+j];inverse[y+2*j+1]=plane[y+y//4+j]
            row['decodedPlanarMd5']=hashlib.md5(plane).hexdigest();row['inverseNv12Sha256']=hashlib.sha256(inverse).hexdigest()
            if row['inverseNv12Sha256']!=row['rawNv12Sha256']:raise Refusal('INVERSE_HASH')
            row['equal']=True
        if await dec.stdout.read(1) or await dec.wait()!=0:raise Refusal('DECODE_EXIT_OR_EXTRA')
        probe=await manager.spawn([str(FFPROBE),'-v','error','-select_streams','v:0','-show_frames','-show_streams','-of','json',str(path)],'reference-probe',stdout=True)
        data=bytearray()
        while b:=await probe.stdout.read(CHUNK):
            data.extend(b)
            if len(data)>LOG_CAP:raise Refusal('PROBE_CAP')
        if await probe.wait()!=0:raise Refusal('PROBE_EXIT')
        meta=json.loads(data);(attempt/'reference.ffprobe.json').write_bytes(data)
        if len(meta['streams'])!=1 or len(meta['frames'])!=n:raise Refusal('REFERENCE_METADATA_COUNT')
        if meta['streams'][0]['width']!=s['width'] or meta['streams'][0]['height']!=s['height'] or meta['streams'][0]['codec_name']!='ffv1':raise Refusal('REFERENCE_METADATA_FORMAT')
        for row in [meta['streams'][0],*meta['frames']]:
            if any(row.get(k)!=v for k,v in {'pix_fmt':'yuv420p','color_range':'tv','color_space':'bt709','color_transfer':'bt709','color_primaries':'bt709','chroma_location':'center'}.items()):raise Refusal('REFERENCE_METADATA_COLOR')
        for i,row in enumerate(meta['frames']):
            if abs(float(row['best_effort_timestamp_time'])-i*s['fpsDen']/s['fpsNum'])>.000501:raise Refusal('REFERENCE_CADENCE')
    async def pipeline():
        begin=time.monotonic();producer=await manager.spawn([str(NODE),str(DRIVER),str(spec_file)],'native-stdout-driver',stdout=True)
        if s['mode']=='reference':
            reference=attempt/'reference.mkv';encode=ffv1_command(s,reference)
            if s.get('testControl') in ['slow-encoder','broken-encoder']:
                encode=[str(PYTHON),str(ROOT/'checkpoint/native_bridge_encoder_fixture.py'),s['testControl'],json.dumps(encode)]
            enc=await manager.spawn(encode,'ffv1-encoder',stdin=True)
            with pathlib.Path(s['rawFixture']['path']).open('rb') as oracle:
                for i in range(n):
                    try:raw=await producer.stdout.readexactly(frame_bytes)
                    except asyncio.IncompleteReadError as e:raise Refusal(f'RAW_SHORT_FRAME:{i}:{len(e.partial)}') from e
                    if raw!=oracle.read(frame_bytes):raise Refusal('RETAINED_RAW_IDENTITY')
                    plane=storage.planar_split(raw,y)
                    receipt['rows'].append({'index':i,'sourceIndex':s['sourceStart']+i,'retainedRawFixtureOrdinal':i,'rawNv12Sha256':hashlib.sha256(raw).hexdigest(),'planarMd5':hashlib.md5(plane).hexdigest()})
                    receipt['referenceOnlyReadbackBytes']+=len(raw);enc.stdin.write(plane)
                    queued=enc.stdin.transport.get_write_buffer_size();receipt['maxPlanarWriterQueuedBytes']=max(receipt['maxPlanarWriterQueuedBytes'],queued)
                    if queued>CHUNK+frame_bytes:raise Refusal('PLANAR_WRITER_CAP')
                    if queued:receipt['backpressureObservations']+=1
                    await enc.stdin.drain();receipt['drainCalls']+=1
                    del raw,plane
            if await producer.stdout.read(1):raise Refusal('RAW_EXTRA_BYTES')
            if await producer.wait()!=0:raise Refusal('DRIVER_EXIT')
            enc.stdin.close();await enc.stdin.wait_closed()
            if await enc.wait()!=0:raise Refusal('ENCODER_EXIT')
            await manager.settle();await verify_producer()
            if s.get('testControl')=='corrupt-reference':
                with reference.open('r+b') as f:f.write(b'BAD!')
            await decode_reference(reference);receipt['reference']=pin(reference)
        elif s['mode']=='rgba-control':
            total=0;h=hashlib.sha256()
            while b:=await producer.stdout.read(CHUNK):
                total+=len(b);h.update(b)
                if total>n*y*4:raise Refusal('RGBA_CAP')
            if total!=n*y*4 or await producer.wait()!=0:raise Refusal('RGBA_COUNT_OR_EXIT')
            await manager.settle();await verify_producer();receipt['rgbaControl']={'bytes':total,'sha256':h.hexdigest(),'syntheticZeroPayload':True}
        else:
            # Encoded producer emits a sidecar, never a raw stdout payload.
            if await producer.stdout.read(1):raise Refusal('ENCODE_UNEXPECTED_STDOUT')
            if await producer.wait()!=0:raise Refusal('DRIVER_EXIT')
            await manager.settle();await verify_producer()
            elementary=pathlib.Path(command[8]);old.check(s['elementaryFixture'])
            if sha(elementary)!=s['elementaryFixture']['sha256']:raise Refusal('RETAINED_ELEMENTARY_IDENTITY')
            original=attempt/'original.mp4';center=attempt/'center.mp4'
            mux=[str(FFMPEG),'-v','error','-xerror','-n','-r',f"{s['fpsNum']}/{s['fpsDen']}",'-f','hevc' if s['codec']=='hevc' else 'h264','-i',str(elementary),'-c:v','copy','-an','-video_track_timescale',str(s['fpsNum']),'-movflags','+faststart',str(original)]
            await manager.run(mux,'copy-mux')
            await manager.run([str(PYTHON),str(ROOT/'checkpoint/native_chroma_conformance.py'),str(original),str(center),'--codec',s['codec'],'--receipt',str(attempt/'CONFORMANCE.json')],'shared-conformance')
            receipt['candidate']={'original':pin(original),'conformed':pin(center),'mandatoryConformanceAndMuxIncluded':True,'syntheticFixturePipelineElapsedSeconds':time.monotonic()-begin,'clockExcludedFromBenchmarks':True}
            # Mandatory decode succeeds; independent original/center MD5 invariance follows.
            md5=[]
            for path,label in [(original,'original'),(center,'center')]:
                await manager.run([str(FFMPEG),'-v','error','-xerror','-i',str(path),'-pix_fmt','yuv420p','-fps_mode','passthrough','-f','framemd5','-'],label+'-decode')
                data=(attempt/(label+'-decode.stdout.log')).read_text();values=[l.rsplit(',',1)[-1].strip() for l in data.splitlines() if l and not l.startswith('#')]
                if len(values)!=n:raise Refusal('CODED_DECODE_COUNT')
                md5.append(values)
            if md5[0]!=md5[1]:raise Refusal('CODED_DECODE_INVARIANCE')
            receipt['decodedInvariantFrames']=n;receipt['originalDecodedMd5']=md5[0];receipt['conformedDecodedMd5']=md5[1]
        await manager.settle()
        for p in s['pins']:old.check(p)
        receipt.update(status='passed-subprocess-fixture',hardwareQualified=False,realDeviceAccepted=False,GPUExecuted=False,processes=manager.receipt(),pythonMaxRSSBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,allChildrenReaped=all(p.returncode is not None for p in manager.processes),qualificationComplete=False)
        binding=attempt/'BINDING.json';binding.write_text(json.dumps(receipt,indent=2)+'\n')
        sealed={p.name:sha(p) for p in attempt.iterdir() if p.is_file()}
        if s.get('testControl')=='corrupt-before-publish':binding.write_text('{}\n')
        if s.get('testControl')=='fail-before-publish':raise Refusal('INJECTED_BEFORE_PUBLISH')
        if s.get('testControl')=='race-destination':dest.mkdir();(dest/'sentinel').write_text('preserved')
        if any(sha(attempt/name)!=value for name,value in sealed.items()):raise Refusal('PREPUBLISH_HASH')
        for p in attempt.iterdir():
            if p.is_file():
                with p.open('rb') as f:os.fsync(f.fileno())
        fd=os.open(attempt,os.O_RDONLY);os.fsync(fd);os.close(fd)
        storage.atomic_directory(attempt,dest)
        fd=os.open(dest.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
        return receipt
    task=asyncio.create_task(pipeline());watch=asyncio.create_task(monitor())
    try:
        done,_=await asyncio.wait([task,watch],return_when=asyncio.FIRST_COMPLETED,timeout=s['timeoutSeconds'])
        if not done:raise Refusal('TIMEOUT')
        if watch in done:await watch;raise Refusal('WATCHDOG_EXIT')
        return await task
    except BaseException as e:
        task.cancel();await manager.stop();await asyncio.gather(task,return_exceptions=True)
        receipt.update(status='failed-subprocess-fixture',error=type(e).__name__+':'+str(e),processes=manager.receipt(),allChildrenReaped=all(p.returncode is not None for p in manager.processes),publishedBinding=False,partialFilesRetained=True)
        if attempt.exists():(attempt/'FAILURE.json').write_text(json.dumps(receipt,indent=2)+'\n')
        raise
    finally:watch.cancel();await asyncio.gather(watch,return_exceptions=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('spec');p.add_argument('destination');a=p.parse_args()
    try:
        path=pathlib.Path(a.spec)
        if path.is_symlink() or path.stat().st_size>LOG_CAP:raise Refusal('SPEC_ENVELOPE')
        r=asyncio.run(run_job(json.loads(path.read_text()),pathlib.Path(a.destination).absolute()));print(json.dumps({'status':r['status'],'hardwareQualified':False,'GPUExecuted':False}))
    except (Refusal,OSError) as e:print(json.dumps({'status':'refused','reason':str(e),'hardwareQualified':False,'GPUExecuted':False}));raise SystemExit(2)
