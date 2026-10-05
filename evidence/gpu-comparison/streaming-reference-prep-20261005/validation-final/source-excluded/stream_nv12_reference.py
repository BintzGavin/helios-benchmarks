"""Bounded storage correctness slice. CLI accepts copied small fixtures only.

No GPU, hardware encoder or 4K launch is reachable from this entry point.
Reference capture is an explicitly readback-only, excluded future operation.
"""
import asyncio, ctypes, hashlib, json, os, pathlib, resource, shutil, signal, sys, uuid

MAX_LOG = 1024 * 1024
PIPE_LIMIT = 65536
SMALL_FREE_GATE = 256 * 1024 * 1024
ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKER = pathlib.Path(__file__).with_name('nv12_fixture_worker.py')
FFMPEG = pathlib.Path('/opt/homebrew/bin/ffmpeg').resolve()
FFPROBE = pathlib.Path('/opt/homebrew/bin/ffprobe').resolve()

class Refusal(RuntimeError): pass

def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()

def file_pin(path):
    p = pathlib.Path(path).resolve()
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}

def check_pin(p):
    f = pathlib.Path(p['path'])
    if not f.is_file() or f.stat().st_size != p['bytes'] or sha(f) != p['sha256']:
        raise Refusal('PIN_MISMATCH: '+str(f))

def strict_json(path):
    p = pathlib.Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_LOG:
        raise Refusal('JSON_ENVELOPE')
    return json.loads(p.read_text())

def atomic_directory(source, destination):
    """Darwin RENAME_EXCL, verified against the installed SDK sys/stdio.h."""
    if sys.platform != 'darwin': raise Refusal('ATOMIC_NO_REPLACE_UNSUPPORTED')
    lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    call = lib.renameatx_np
    call.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    call.restype = ctypes.c_int
    # Absolute paths; AT_FDCWD=-2 and RENAME_EXCL=4 on this qualified Mac.
    if call(-2, os.fsencode(source), -2, os.fsencode(destination), 4):
        e = ctypes.get_errno(); raise OSError(e, os.strerror(e), str(destination))

def validate_spec(spec, destination):
    if spec.get('purpose') != 'copied-small-NV12-storage-test': raise Refusal('FIXTURE_ONLY')
    w,h,n = spec['width'],spec['height'],spec['frames']
    if any(type(v) is not int for v in [w,h,n,spec['sourceStart'],spec['fpsNum'],spec['fpsDen']]): raise Refusal('INTEGER_CONTRACT')
    if not (0<w<=256 and 0<h<=128 and w%2==h%2==0 and 1<=n<=300 and 0<=spec['sourceStart']<=100000 and 1<=spec['fpsNum']<=60000 and 1<=spec['fpsDen']<=1001): raise Refusal('SMALL_ENVELOPE')
    if n*w*h*3//2 > 16*1024*1024: raise Refusal('RAW_BYTE_CAP')
    if spec.get('benchmarkTiming') is not False or spec.get('timingWindowOpen') is not False: raise Refusal('NOT_BENCHMARK')
    if not 0<spec.get('encodedCapBytes',0)<=16*1024*1024: raise Refusal('ENCODED_CAP')
    if not 0<spec.get('timeoutSeconds',0)<=30: raise Refusal('TIME_CAP')
    for p in spec['pins']: check_pin(p)
    required = {str(p.resolve()) for p in [WORKER, FFMPEG, FFPROBE, pathlib.Path(sys.executable), pathlib.Path(spec['source'])]}
    if not required.issubset({p['path'] for p in spec['pins']}): raise Refusal('UNPINNED_RUNTIME_OR_SOURCE')
    source = pathlib.Path(spec['source'])
    if source.is_symlink() or not source.resolve().is_relative_to(ROOT/'comparison/streaming-reference-prep-20261005/fixtures'): raise Refusal('COPIED_FIXTURE_REQUIRED')
    if source.stat().st_size != spec['fixtureFrames']*w*h*3//2 or spec['fixtureFrames']<n: raise Refusal('SOURCE_SIZE')
    if spec['sourceSha256']!=sha(source): raise Refusal('SOURCE_HASH')
    if len(spec['expectedFrames'])!=n: raise Refusal('EXPECTED_FRAME_COUNT')
    for i,x in enumerate(spec['expectedFrames']):
        if x['index']!=i or x['sourceIndex']!=i+spec['sourceStart'] or len(x['rawNv12Sha256'])!=64: raise Refusal('EXPECTED_ORDER')
    dest = pathlib.Path(destination)
    if not dest.is_absolute() or not dest.parent.resolve().is_relative_to(ROOT/'comparison/streaming-reference-prep-20261005/cases'): raise Refusal('DESTINATION_SCOPE')
    if dest.exists() or dest.is_symlink(): raise Refusal('EXISTING_DESTINATION')
    if shutil.disk_usage(dest.parent).free < SMALL_FREE_GATE: raise Refusal('SMALL_DISK_GATE')

def planar_split(raw, y):
    out = bytearray(len(raw)); out[:y] = memoryview(raw)[:y]
    out[y:y+y//4] = raw[y::2]; out[y+y//4:] = raw[y+1::2]
    return out

async def log_stream(reader, path):
    total=0
    with path.open('xb') as f:
        while b := await reader.read(PIPE_LIMIT):
            total += len(b)
            if total>MAX_LOG: raise Refusal('LOG_CAP')
            f.write(b)
    return total

async def terminate(p):
    if p.returncode is None:
        try: os.killpg(p.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: await asyncio.wait_for(p.wait(), 1)
        except asyncio.TimeoutError:
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            await p.wait()

async def run_reference(spec, destination):
    validate_spec(spec,destination)
    dest=pathlib.Path(destination); attempt=dest.parent/('attempt-'+uuid.uuid4().hex); attempt.mkdir()
    (attempt/'SPEC.json').write_text(json.dumps(spec,indent=2)+'\n')
    w,h,n=spec['width'],spec['height'],spec['frames']; y=w*h; frame_bytes=y*3//2
    reference=attempt/'reference.mkv'
    tags=['-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-chroma_sample_location','center']
    encode=[str(FFMPEG),'-v','error','-xerror','-n','-f','rawvideo','-pix_fmt','yuv420p','-s',f'{w}x{h}','-r',f"{spec['fpsNum']}/{spec['fpsDen']}",*tags,'-i','pipe:0','-c:v','ffv1','-level','3','-threads','2','-pix_fmt','yuv420p',*tags,'-frames:v',str(n),str(reference)]
    producer=[sys.executable,str(WORKER),'producer',str(attempt/'SPEC.json')]
    encoder=encode
    if spec.get('testControl') in ['slow-consumer','broken-pipe','encoder-failure']:
        encoder=[sys.executable,str(WORKER),'encoder',spec['testControl'],json.dumps(encode)]
    receipt={'status':'running','producerCommand':producer,'encoderCommand':encoder,'actualFFV1Command':encode,'frames':[],'explicitReferenceOnlyRawBytes':0,'maxWriterQueuedBytes':0,'drainCalls':0,'backpressureObservations':0,'benchmarkTiming':False,'timingWindowOpen':False,'GPUExecuted':False,'zeroCopyProved':False}
    processes=[]; background=[]
    async def spawn(argv, label, stdin=None):
        p=await asyncio.create_subprocess_exec(*argv,stdin=stdin,stdout=asyncio.subprocess.PIPE if label in ['producer','decode'] else asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.PIPE,limit=PIPE_LIMIT,start_new_session=True)
        processes.append(p); background.append(asyncio.create_task(log_stream(p.stderr,attempt/(label+'.stderr.log'))));return p
    async def monitor():
        while True:
            if shutil.disk_usage(attempt).free<SMALL_FREE_GATE: raise Refusal('SMALL_DISK_RESERVE')
            if reference.exists() and reference.stat().st_size>spec['encodedCapBytes']: raise Refusal('REFERENCE_CAP')
            for t in background:
                if t.done() and t.exception(): raise t.exception()
            await asyncio.sleep(.02)
    async def pipeline():
        prod=await spawn(producer,'producer');enc=await spawn(encoder,'encoder',asyncio.subprocess.PIPE)
        for i in range(n):
            try: raw=await prod.stdout.readexactly(frame_bytes)
            except asyncio.IncompleteReadError as e: raise Refusal(f'SHORT_FRAME:{i}:{len(e.partial)}') from e
            raw_sha=hashlib.sha256(raw).hexdigest()
            if raw_sha!=spec['expectedFrames'][i]['rawNv12Sha256']: raise Refusal('DIRECT_SOURCE_HASH')
            plane=planar_split(raw,y)
            receipt['frames'].append({'index':i,'sourceIndex':spec['sourceStart']+i,'rawNv12Sha256':raw_sha,'planarSha256':hashlib.sha256(plane).hexdigest(),'planarMd5':hashlib.md5(plane).hexdigest()})
            receipt['explicitReferenceOnlyRawBytes']+=len(raw)
            enc.stdin.write(plane)
            queued=enc.stdin.transport.get_write_buffer_size();receipt['maxWriterQueuedBytes']=max(receipt['maxWriterQueuedBytes'],queued)
            if queued>PIPE_LIMIT+frame_bytes:raise Refusal('WRITE_BUFFER_CAP')
            if queued:receipt['backpressureObservations']+=1
            await enc.stdin.drain();receipt['drainCalls']+=1
            del raw,plane
        if await prod.stdout.read(1): raise Refusal('EXTRA_BYTES')
        if await prod.wait()!=0: raise Refusal('PRODUCER_EXIT')
        enc.stdin.close();await enc.stdin.wait_closed()
        if await enc.wait()!=0: raise Refusal('ENCODER_EXIT')
        await asyncio.gather(*background)
        identities=[json.loads(l) for l in (attempt/'producer.stderr.log').read_text().splitlines() if l.startswith('{')]
        if len(identities)!=1: raise Refusal('PRODUCER_RECEIPT_COUNT')
        p=identities[0];expected=[{'index':i,'sourceIndex':i+spec['sourceStart']} for i in range(n)]
        if p.get('frameIdentities')!=expected or p.get('frames')!=n or p.get('sourceSha256')!=spec['sourceSha256']: raise Refusal('PRODUCER_SOURCE_ORDER')
        receipt['producerReceipt']=p
        if not reference.is_file() or reference.stat().st_size>spec['encodedCapBytes']: raise Refusal('ENCODED_CAP')
        if spec.get('testControl')=='corrupt-reference':
            with reference.open('r+b') as f:f.seek(0);f.write(b'BAD!')
        decode=[str(FFMPEG),'-v','error','-xerror','-i',str(reference),'-map','0:v:0','-threads','1','-pix_fmt','yuv420p','-fps_mode','passthrough','-f','rawvideo','pipe:1']
        receipt['decodeCommand']=decode;dec=await spawn(decode,'decode')
        for row in receipt['frames']:
            try: plane=await dec.stdout.readexactly(frame_bytes)
            except asyncio.IncompleteReadError as e: raise Refusal('REFERENCE_DECODE_SHORT') from e
            if hashlib.md5(plane).hexdigest()!=row['planarMd5'] or hashlib.sha256(plane).hexdigest()!=row['planarSha256']:raise Refusal('REFERENCE_HASH')
            # Independent inverse shape: explicit plane addressing and interleaved destination strides.
            inverse=bytearray(frame_bytes);inverse[:y]=plane[:y]
            for j in range(y//4):inverse[y+2*j]=plane[y+j];inverse[y+2*j+1]=plane[y+y//4+j]
            row['inverseNv12Sha256']=hashlib.sha256(inverse).hexdigest()
            if row['inverseNv12Sha256']!=row['rawNv12Sha256']:raise Refusal('INVERSE_HASH')
            row['decodedPlanarMd5']=hashlib.md5(plane).hexdigest();row['equal']=True
            del plane,inverse
        if await dec.stdout.read(1) or await dec.wait()!=0:raise Refusal('REFERENCE_DECODE_EXIT_OR_EXTRA')
        await asyncio.gather(*background)
        probe=[str(FFPROBE),'-v','error','-select_streams','v:0','-show_frames','-show_streams','-of','json',str(reference)]
        q=await asyncio.create_subprocess_exec(*probe,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,limit=PIPE_LIMIT,start_new_session=True);processes.append(q)
        data,err=await q.communicate()
        if q.returncode or err or len(data)>MAX_LOG:raise Refusal('PROBE_ENVELOPE')
        meta=json.loads(data);(attempt/'reference.ffprobe.json').write_bytes(data)
        if len(meta.get('streams',[]))!=1 or len(meta.get('frames',[]))!=n:raise Refusal('METADATA_COUNT')
        st=meta['streams'][0]
        if st.get('codec_name')!='ffv1' or st.get('pix_fmt')!='yuv420p' or st.get('width')!=w or st.get('height')!=h:raise Refusal('METADATA_FORMAT')
        for row in [st,*meta['frames']]:
            if any(row.get(k)!=v for k,v in {'color_range':'tv','color_space':'bt709','color_transfer':'bt709','color_primaries':'bt709','chroma_location':'center'}.items()):raise Refusal('METADATA_COLOR')
        # Matroska rounds to milliseconds: ordinal t=i*den/num must be within0.5ms.
        for i,row in enumerate(meta['frames']):
            if abs(float(row['best_effort_timestamp_time'])-i*spec['fpsDen']/spec['fpsNum'])>.000501:raise Refusal('REFERENCE_CADENCE')
        receipt['referenceSha256']=sha(reference);receipt['referenceBytes']=reference.stat().st_size
        receipt['probeCommand']=probe;receipt['sourcePin']=file_pin(spec['source']);receipt['noColorArithmetic']=True
        receipt['hashAndCadenceColorChecksPassed']=True;receipt['framesBound']=n;receipt['allInverseHashesEqual']=True
        receipt['status']='passed';receipt['processExits']=[p.returncode for p in processes]
        receipt['selfMaxRSSBytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        binding=attempt/'BINDING.json';binding.write_text(json.dumps(receipt,indent=2)+'\n')
        sealed={str(p):sha(p) for p in [reference,binding]}
        if spec.get('testControl')=='corrupt-before-commit':
            with reference.open('r+b') as f:
                f.seek(-1,2);old=f.read(1);f.seek(-1,2);f.write(bytes([old[0]^1]))
        if spec.get('testControl')=='corrupt-binding':binding.write_text('{}\n')
        if spec.get('testControl')=='fail-before-commit':raise Refusal('INJECTED_BEFORE_COMMIT')
        if spec.get('testControl')=='race-destination':dest.mkdir();(dest/'sentinel').write_text('preserved competing destination')
        for p,expected_hash in sealed.items():
            if sha(p)!=expected_hash:raise Refusal('PRECOMMIT_HASH')
        check_pin(receipt['sourcePin'])
        for p in spec['pins']:check_pin(p)
        for p in attempt.iterdir():
            if p.is_file():
                with p.open('rb') as f:os.fsync(f.fileno())
        fd=os.open(attempt,os.O_RDONLY);os.fsync(fd);os.close(fd)
        atomic_directory(attempt,dest)
        fd=os.open(dest.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
        return receipt
    task=asyncio.create_task(pipeline());watch=asyncio.create_task(monitor())
    try:
        done,_=await asyncio.wait([task,watch],timeout=spec['timeoutSeconds'],return_when=asyncio.FIRST_COMPLETED)
        if not done:raise Refusal('TIMEOUT')
        if watch in done:await watch;raise Refusal('WATCHDOG_EXIT')
        return await task
    except BaseException as e:
        task.cancel()
        for p in processes:await terminate(p)
        await asyncio.gather(task,*background,return_exceptions=True)
        receipt.update(status='failed',error=type(e).__name__+': '+str(e),processExits=[p.returncode for p in processes],partialArtifactsRetained=True,publishedBinding=False)
        if attempt.exists():(attempt/'FAILURE.json').write_text(json.dumps(receipt,indent=2)+'\n')
        raise
    finally:
        watch.cancel();await asyncio.gather(watch,return_exceptions=True)

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('SPEC.json DESTINATION')
    result=asyncio.run(run_reference(strict_json(sys.argv[1]),pathlib.Path(sys.argv[2]).absolute()))
    print(json.dumps({'status':result['status'],'frames':result['framesBound'],'GPUExecuted':False}))
