"""Live Metal/HEVC acceptance, separately frozen from CPU preparation.

Only fixed presets and the archived9c2b helper are reachable. Retained NV12,
9GiB serial gate and the unchanged quality floors remain authoritative.
"""
import argparse,asyncio,hashlib,json,os,pathlib,resource,shutil,sys,time,uuid
import codec_orchestration as old
import native_bridge_runner as prepared
import stream_nv12_reference as storage
from fractions import Fraction

ROOT=old.ROOT;OUT=ROOT/'comparison/native-metal-hevc-live-20261005'
DRIVER=ROOT/'checkpoint/live_hevc_bridge.mjs'
NODE=prepared.NODE;PYTHON=prepared.PYTHON;FFMPEG=prepared.FFMPEG;FFPROBE=prepared.FFPROBE
HELPER=pathlib.Path('/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94/hevc-evidence/helper-candidate-01')
HELPER_SHA='9c2b3654ce681d9764643214a745878b8fecb72ed9fcd69f3aea7f0fa709d9ae'
PROFILE=pathlib.Path('/Users/gavinbintz/.codex/worktrees/gpu-hevc/helios/packages/portable/benchmarks/profile-gpu.mm')
CONFORMANCE=ROOT/'checkpoint/native_chroma_conformance.py'
QUALITY=ROOT/'preparation/unpacked/helios-gpu-comparison-prep/validate_video.py'
GATE=9*1024**3;RESERVE=1024**3;HALF=512*1024**2
MODES=['reference','hardware','profile','positive-nv12','positive-rgba']
sha=old.sha;pin=old.pin
class Refusal(RuntimeError):pass
def dump(p,value):
    with pathlib.Path(p).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def fixed(variant,mode):
    if variant not in ['bounded36','circles4k300'] or mode not in MODES:raise Refusal('PRESET')
    bounded=variant=='bounded36';control=mode.startswith('positive-')
    return {'executionClass':'native-live-unqualified','variant':variant,'mode':mode,'codec':'hevc','backend':'metal','protocol':7,'width':256 if bounded else 3840,'height':128 if bounded else 2160,'frames':3 if control else 36 if bounded else 300,'sourceStart':3,'fpsNum':30,'fpsDen':1,'bitrate':300000000,'gop':30,'encoderPool':3,'hardwareQualified':False,'realDeviceAccepted':False,'benchmarkTiming':False,'timingWindowOpen':False}
def source_guard():
    f=OUT/'LIVE-FREEZE.json';j=json.loads(f.read_text())
    for p in j['pins']:old.check(p)
    if sha(HELPER)!=HELPER_SHA:raise Refusal('HELPER_CHANGED')
    return j
def acceptance_gate():
    p=OUT/'BOUNDED-ACCEPTANCE.json'
    if not p.exists():raise Refusal('BOUNDED_LIVE_ACCEPTANCE_REQUIRED')
    g=json.loads(p.read_text())
    if g.get('status')!='qualified-bounded-live-metal-hevc' or g.get('GPUExecuted') is not True or g.get('hardwareQualified') is not True or g.get('driver')!=pin(DRIVER) or g.get('helper')!=pin(HELPER):raise Refusal('BOUND_ACCEPTANCE_CHANGED')
    for p in g['acceptancePins']:old.check(p)
    return g
def start_guard(variant,mode,dest,free=None):
    fixed(variant,mode)
    if variant=='circles4k300':acceptance_gate()
    dest=pathlib.Path(dest)
    if not dest.is_absolute() or not dest.parent.resolve().is_relative_to(OUT) or any(p.is_symlink() for p in [dest,*dest.parents]):raise Refusal('OUTPUT_SCOPE')
    if dest.exists():raise Refusal('EXISTING_DESTINATION')
    amount=shutil.disk_usage(ROOT).free if free is None else free
    if amount<GATE:raise Refusal('SERIAL_9GIB_GATE')
    return amount

def parse_lines(path,cap=HALF):
    p=pathlib.Path(path)
    if p.stat().st_size>cap:raise Refusal('EVENT_CAP')
    rows=[]
    with p.open() as f:
        for line in f:
            if len(line)>65536:raise Refusal('EVENT_LINE_CAP')
            rows.append(json.loads(line))
    return rows
def gpu_audit(trace,interposer,s):
    t=parse_lines(trace);p=parse_lines(interposer);n=s['frames'];mode=s['mode'];encoded=mode in ['hardware','profile']
    counters={}
    for e in p:counters[e['event']]=counters.get(e['event'],0)+1
    if counters.get('profiler-hooks-installed',0)<1 or counters.get('profiler-hooks-incomplete',0):raise Refusal('PROFILE_HOOKS')
    events={}
    for order,e in enumerate(t):events.setdefault(e['event'],[]).append((order,e))
    raster=events.get('raster-submitted',[])
    if [e['frame'] for _,e in raster]!=list(range(n)):raise Refusal('RASTER_ORDER')
    proof=[];last_release={}
    if mode!='positive-rgba':
        cv=events.get('conversion-complete',[])
        if [e['frame'] for _,e in cv]!=list(range(n)):raise Refusal('CONVERSION_COUNT')
        for (order,e),(start,_) in zip(cv,raster):
            if not start<order or not e['sameIOSurfacePlanes'] or not 0<e['gpuStartSeconds']<e['gpuEndSeconds']:raise Refusal('ACTUAL_GPU_CONVERSION')
    if encoded:
        create=events.get('surface-create',[])
        if len(create)!=1:raise Refusal('HARDWARE_CREATION')
        c=create[0][1]
        for k,v in {'codec':'hevc','hardwareRequired':True,'hardwareUsed':True,'bitrate':300000000,'configuredBitrate':300000000,'gop':30,'poolCapacity':3,'rasterStorage':'private','format':'nv12-video-range'}.items():
            if c.get(k)!=v:raise Refusal('HARDWARE_'+k)
        by={}
        for order,e in enumerate(t):
            if 'frame' in e:by.setdefault(e['frame'],{}).setdefault(e['event'],[]).append((order,e))
        for i in range(n):
            row=by[i];names=['surface-acquire','conversion-complete','encoder-submit','application-surface-release','encoder-callback','callback-owner-release']
            if any(len(row.get(k,[]))!=1 for k in names):raise Refusal('OWNERSHIP_EVENT_COUNT')
            at={k:row[k][0][0] for k in names};v={k:row[k][0][1] for k in names};sid=v['surface-acquire']['surfaceId']
            if any(v[k]['surfaceId']!=sid for k in names):raise Refusal('SURFACE_IDENTITY')
            if not at['surface-acquire']<at['conversion-complete']<at['encoder-submit']<at['encoder-callback']<at['callback-owner-release'] or at['application-surface-release']<at['encoder-submit']:raise Refusal('FENCE_OR_OWNER_ORDER')
            if v['encoder-callback']['status']!=0 or v['encoder-callback']['dropped']:raise Refusal('CALLBACK_FAILED')
            if sid in last_release and not last_release[sid]<at['surface-acquire']:raise Refusal('OWNER_RELEASE_BEFORE_REUSE')
            last_release[sid]=at['callback-owner-release'];proof.append({'frame':i,'sourceIndex':i+3,'surfaceId':sid,'orders':at,'passed':True})
        finish=events.get('encoder-finish',[])
        if len(finish)!=1 or finish[0][1]['frames']!=n or not finish[0][1]['allCallbacksComplete'] or not 1<=finish[0][1]['peakInFlight']<=3:raise Refusal('ENCODER_DRAIN')
        raw=['CVPixelBufferLockBaseAddress','IOSurfaceLock','MTLTextureGetBytes','MTLBlitTextureToBuffer']
        if any(counters.get(k,0) for k in raw):raise Refusal('HARDWARE_RAW_DOWNLOAD_OBSERVED')
    elif mode=='positive-nv12':
        if counters.get('CVPixelBufferLockBaseAddress',0)<n or counters.get('CVPixelBufferGetBaseAddressOfPlane',0)<2*n:raise Refusal('NV12_POSITIVE_NOT_DETECTED')
    elif mode=='positive-rgba':
        if counters.get('MTLBlitTextureToBuffer',0)+counters.get('MTLTextureGetBytes',0)<n:raise Refusal('RGBA_POSITIVE_NOT_DETECTED')
    return {'status':'passed actual GPU/profile/ownership scope','GPUExecuted':True,'frames':n,'hookEvents':counters,'ownership':proof,'nativeTrace':pin(trace),'interposerLog':pin(interposer),'zeroCopyProved':False,'opaqueTransfersAndPointerIntent':'unknown','mode':mode}

def control_audit(rawfile,s):
    if s['variant']!='bounded36':raise Refusal('SMALL_CONTROL_ONLY')
    w,h=256,128;y=w*h;size=y*3//2;rows=[]
    # Independent BT709 limited equations on primary endpoints: no reference fit.
    colors=[('red',16,16,(1,0,0)),('green',144,16,(0,1,0)),('blue',16,80,(0,0,1)),('white',240,80,(1,1,1))]
    def values(rgb):
        r,g,b=rgb;l=.2126*r+.7152*g+.0722*b
        return (16+219*l,128+112*(b-l)/(1-.0722),128+112*(r-l)/(1-.2126))
    with pathlib.Path(rawfile).open('rb') as f:
        for frame in range(min(3,s['frames'])):
            raw=f.read(size)
            for name,x,z,rgb in colors:
                predicted=values(rgb);actual=(raw[z*w+x],raw[y+(z//2)*w+(x//2)*2],raw[y+(z//2)*w+(x//2)*2+1])
                if any(abs(a-b)>1 for a,b in zip(actual,predicted)):raise Refusal('INDEPENDENT_PRIMARY_COLOR')
                rows.append({'frame':frame,'sourceIndex':frame+3,'sample':name,'predicted':predicted,'actual':actual,'maxCodeError':max(abs(a-b) for a,b in zip(actual,predicted))})
            avg=values((.75,0,.25));actual=(raw[y+(96//2)*w+16],raw[y+(96//2)*w+17])
            if any(abs(a-b)>1 for a,b in zip(actual,avg[1:])):raise Refusal('CENTERED_2X2_CHROMA_CONTROL')
            for x,z,rgb in [(16,96,(1,0,0)),(17,96,(1,0,0)),(16,97,(1,0,0)),(17,97,(0,0,1))]:
                if abs(raw[z*w+x]-values(rgb)[0])>1:raise Refusal('CONTROL_LUMA_PATTERN')
            rows.append({'frame':frame,'sourceIndex':frame+3,'sample':'3red1blue-centered2x2','predictedUV':avg[1:],'actualUV':actual,'maxCodeError':max(abs(a-b) for a,b in zip(actual,avg[1:]))})
    return {'status':'passed predetermined independent physical color/chroma controls','fixedMaxCodeError':1,'referenceFitted':False,'rows':rows}

async def run(variant,mode,dest,fault=None):
    frozen=source_guard();start_free=start_guard(variant,mode,dest);s=fixed(variant,mode)
    if fault not in [None,'device','encoder','format'] or fault and (variant!='bounded36' or mode!='hardware'):raise Refusal('FAULT_SCOPE')
    (OUT/'attempts').mkdir(exist_ok=True);attempt=OUT/'attempts'/('attempt-'+uuid.uuid4().hex);attempt.mkdir();dest=pathlib.Path(dest)
    manager=prepared.Supervisor(attempt);w,h,n=s['width'],s['height'],s['frames'];y=w*h;frame_size=y*3//2
    large=variant=='circles4k300';cap=(64*1024**2 if not large else 9503842304-RESERVE);logcap=HALF if large else 8*1024**2
    stage_receipts=[];receipt={**s,'status':'running-native-unqualified','helper':pin(HELPER),'driver':pin(DRIVER),'sourceFreeze':pin(OUT/'LIVE-FREEZE.json'),'rows':[],'startFreeBytes':start_free,'GPUExecuted':False,'actualGPUBridgeAccepted':False,'rawReferenceRetentionRequired':True,'streaming6GiBGateEnabled':False}
    def guard(stage,remaining=0):
        free=shutil.disk_usage(ROOT).free
        if free<RESERVE+remaining:raise Refusal('REMAINING_BUDGET_'+stage)
        stage_receipts.append({'stage':stage,'freeBytes':free,'remainingAllocationBytes':remaining,'reserveBytes':RESERVE,'passed':True})
    async def monitor():
        while True:
            if shutil.disk_usage(ROOT).free<RESERVE:raise Refusal('DISK_RESERVE')
            total=0
            for p in attempt.iterdir():
                try:
                    if p.is_file():
                        size=p.stat().st_size;total+=size
                        maximum=n*w*h*4 if p.name=='reference.rgba' else n*frame_size if p.name=='reference.nv12' else 1024**3 if p.name=='reference.mkv' else HALF if p.name.endswith(('.h265','.mp4','.candidate')) else logcap
                        if size>maximum:raise Refusal('FILE_CAP_'+p.name)
                except FileNotFoundError:continue
            if total>cap:raise Refusal('ATTEMPT_CAP')
            for task in manager.logs:
                if task.done() and task.exception():raise task.exception()
            await asyncio.sleep(.05)
    async def producer_receipt():
        result=json.loads((attempt/'PRODUCER.json').read_text())
        if result['executionClass']!='native-live-unqualified' or result['GPUExecuted'] is not True or result['hardwareQualified'] is not False or len(result['frameIdentities'])!=n:raise Refusal('PRODUCER_LIVE_CLASS')
        if any(r['index']!=i or r['sourceIndex']!=i+3 for i,r in enumerate(result['frameIdentities'])):raise Refusal('SOURCE_ORDER')
        receipt['producer']=result;receipt['GPUExecuted']=True
    async def decode_reference(path):
        cmd=[str(FFMPEG),'-v','error','-xerror','-i',str(path),'-pix_fmt','yuv420p','-fps_mode','passthrough','-f','rawvideo','pipe:1']
        dec=await manager.spawn(cmd,'reference-decode',stdout=True)
        with (attempt/'reference.nv12').open('rb') as original:
            for row in receipt['rows']:
                try:plane=await dec.stdout.readexactly(frame_size)
                except asyncio.IncompleteReadError as e:raise Refusal('REFERENCE_DECODE_SHORT') from e
                inverse=bytearray(frame_size);inverse[:y]=plane[:y];inverse[y::2]=plane[y:y+y//4];inverse[y+1::2]=plane[y+y//4:]
                direct=original.read(frame_size)
                if direct!=inverse or hashlib.md5(plane).hexdigest()!=row['planarMd5']:raise Refusal('DIRECT_REFERENCE_BYTE_BINDING')
                row.update(decodedPlanarMd5=hashlib.md5(plane).hexdigest(),inverseNv12Sha256=hashlib.sha256(inverse).hexdigest(),equal=True)
        if await dec.stdout.read(1) or await dec.wait()!=0:raise Refusal('REFERENCE_DECODE_EXIT_OR_EXTRA')
        receipt['directReferenceBindingPassed']=True;receipt['referenceDecodeCommand']=cmd
    async def pipeline():
        begin=time.monotonic();guard('profile-compile')
        lib=attempt/'transfer-interposer.dylib';log=attempt/'interposer.jsonl'
        compile_cmd=['/usr/bin/xcrun','clang++','-dynamiclib','-fobjc-arc','-std=c++17','-isysroot','/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk',f'-DHELIOS_PROFILE_PATH="{log}"',str(PROFILE),'-framework','Foundation','-framework','Metal','-framework','CoreVideo','-framework','IOSurface','-o',str(lib)]
        await manager.run(compile_cmd,'profile-compile');profile={'libraryPin':pin(lib),'log':str(log)}
        fault_pin=None
        if fault:
            f=attempt/'fault.dylib';cmd=['/usr/bin/xcrun','clang++','-dynamiclib','-fobjc-arc','-std=c++17','-DFAIL_'+fault.upper(),str(ROOT/'checkpoint/live_hevc_faults.mm'),'-framework','Metal','-framework','CoreMedia','-framework','CoreVideo','-framework','VideoToolbox','-o',str(f)]
            await manager.run(cmd,'fault-compile');fault_pin=pin(f)
        dump(attempt/'PROFILE-BUILD.json',{'compileCommand':compile_cmd,'profileSource':pin(PROFILE),'libraryPin':pin(lib),'log':str(log),'faultLibraryPin':fault_pin,'taskSettings':{'TMPDIR':'/tmp'},'fresh':True})
        native_mode='reference-binary' if mode in ['reference','positive-nv12'] else 'raster-binary' if mode=='positive-rgba' else 'encode-binary'
        command=[str(HELPER),native_mode,str(w),str(h),'30','1','300000000',str(attempt/'elementary.h265'),str(attempt/'gpu-transfer.jsonl'),'','30','3','hevc']
        _,_,inputs=old.snapshot();font=json.loads((old.PLAN/'CONFIG.json').read_text())['scene']['font']
        issued={**s,'helper':pin(HELPER),'recorderModule':prepared.CPU_RECORDERS['metal'][0],'sceneModule':str(ROOT/'checkpoint/live_hevc_scene.mjs' if not large else ROOT/'checkpoint/circles-scene.mts'),'font':font,'profile':profile,'faultLibraryPin':fault_pin,'nativeCommand':command,'attemptDirectory':str(attempt),'pins':frozen['pins']+[pin(lib)]+([fault_pin] if fault_pin else [])}
        dump(attempt/'ISSUED-SPEC.json',issued)
        # Fresh per-stage prediction honors the retained-raw serial budget. The
        #9GiB incremental gate applies anew at lane start, not per output byte.
        if mode in ['reference','positive-nv12']:guard('native-reference',n*frame_size+(1024**3 if large else 8*1024**2))
        else:guard('native-encode-or-control',4*HALF if large else 32*1024**2)
        proc=await manager.spawn([str(NODE),str(DRIVER),str(attempt/'ISSUED-SPEC.json')],'live-driver',stdout=True)
        if native_mode=='reference-binary':
            ref=attempt/'reference.mkv';enc=await manager.spawn(prepared.ffv1_command(s,ref),'ffv1-reference',stdin=True)
            receipt.update(maxPlanarWriterQueuedBytes=0,rawReferenceBytes=0)
            with (attempt/'reference.nv12').open('xb') as f:
                for i in range(n):
                    try:raw=await proc.stdout.readexactly(frame_size)
                    except asyncio.IncompleteReadError as e:raise Refusal('RAW_SHORT:'+str(i)) from e
                    f.write(raw);plane=storage.planar_split(raw,y);receipt['rows'].append({'index':i,'sourceIndex':i+3,'rawNv12Sha256':hashlib.sha256(raw).hexdigest(),'planarMd5':hashlib.md5(plane).hexdigest()})
                    enc.stdin.write(plane);queued=enc.stdin.transport.get_write_buffer_size();receipt['maxPlanarWriterQueuedBytes']=max(receipt['maxPlanarWriterQueuedBytes'],queued)
                    if queued>65536+frame_size:raise Refusal('REFERENCE_BACKPRESSURE_CAP')
                    await enc.stdin.drain();receipt['rawReferenceBytes']+=len(raw);del raw,plane
                f.flush();os.fsync(f.fileno())
            if await proc.stdout.read(1) or await proc.wait()!=0:raise Refusal('REFERENCE_DRIVER_EXIT_OR_EXTRA')
            enc.stdin.close();await enc.stdin.wait_closed()
            if await enc.wait()!=0:raise Refusal('REFERENCE_ENCODER_EXIT')
            await producer_receipt();guard('reference-byte-binding');await decode_reference(ref)
            receipt['reference']=pin(ref);receipt['rawReference']=pin(attempt/'reference.nv12')
            if not large:receipt['independentColorControls']=control_audit(attempt/'reference.nv12',s)
        elif native_mode=='raster-binary':
            total=0
            with (attempt/'reference.rgba').open('xb') as f:
                while b:=await proc.stdout.read(65536):
                    total+=len(b)
                    if total>n*y*4:raise Refusal('RGBA_CAP')
                    f.write(b)
            if total!=n*y*4 or await proc.wait()!=0:raise Refusal('RGBA_COUNT_OR_EXIT')
            await producer_receipt();receipt['rgbaControl']=pin(attempt/'reference.rgba')
        else:
            if await proc.stdout.read(1) or await proc.wait()!=0:raise Refusal('ENCODE_DRIVER_EXIT_OR_UNEXPECTED_STDOUT')
            await producer_receipt();guard('copy-mux-and-conformance',3*HALF if large else 16*1024**2)
            original=attempt/'original.mp4';center=attempt/'center.mp4'
            mux=[str(FFMPEG),'-v','error','-xerror','-n','-r','30','-f','hevc','-i',str(attempt/'elementary.h265'),'-c:v','copy','-an','-video_track_timescale','30','-movflags','+faststart',str(original)]
            await manager.run(mux,'copy-mux');await manager.run([str(PYTHON),str(CONFORMANCE),str(original),str(center),'--codec','hevc','--receipt',str(attempt/'CONFORMANCE.json')],'center-conformance')
            receipt['candidate']={'original':pin(original),'conformed':pin(center),'elementary':pin(attempt/'elementary.h265'),'exportIncludesConformanceAndMux':True,'excludedAcceptanceExportSeconds':time.monotonic()-begin,'benchmarkTiming':False}
            hashes=[];guard('mandatory-decode-and-invariance')
            for path,label in [(original,'original'),(center,'center')]:
                await manager.run([str(FFMPEG),'-v','error','-xerror','-i',str(path),'-pix_fmt','yuv420p','-fps_mode','passthrough','-f','framemd5','-'],label+'-decode')
                vals=[l.rsplit(',',1)[-1].strip() for l in (attempt/(label+'-decode.stdout.log')).read_text().splitlines() if l and not l.startswith('#')]
                if len(vals)!=n:raise Refusal('DECODE_COUNT')
                hashes.append(vals)
            if hashes[0]!=hashes[1]:raise Refusal('SPS_DECODED_INVARIANCE')
            receipt.update(originalDecodedMd5=hashes[0],conformedDecodedMd5=hashes[1],allDecodedFramesUnchanged=True)
            await manager.run([str(FFPROBE),'-v','error','-select_streams','v:0','-show_frames','-show_streams','-of','json',str(center)],'center-probe')
            meta=json.loads((attempt/'center-probe.stdout.log').read_text());st=meta['streams'][0];frames=meta['frames']
            if len(meta['streams'])!=1 or len(frames)!=n or st['codec_name']!='hevc' or (st['width'],st['height'])!=(w,h) or st['r_frame_rate']!='30/1' or st['avg_frame_rate']!='30/1':raise Refusal('CODEC_CADENCE_CONTRACT')
            tags={'pix_fmt':'yuv420p','color_range':'tv','color_space':'bt709','color_transfer':'bt709','color_primaries':'bt709','chroma_location':'center'}
            for row in [st,*frames]:
                if any(row.get(k)!=v for k,v in tags.items()):raise Refusal('DECODED_CENTERED_COLOR')
            keys=[]
            for i,row in enumerate(frames):
                if Fraction(row['pts'])*Fraction(st['time_base'])!=Fraction(i,30) or row.get('pict_type')=='B':raise Refusal('DECODED_EXACT_PTS')
                if row.get('key_frame'):keys.append(i)
            spacing=[b-a for a,b in zip(keys,keys[1:])]+[n-keys[-1]] if keys else [n+30]
            if not keys or keys[0]!=0 or max(spacing)>30:raise Refusal('DECODED_GOP')
            receipt['decodedCadenceColorGop']={'passed':True,'keyframeIndices':keys,'maximumSpacing':max(spacing),'tags':tags}
        await manager.settle();receipt['gpuAudit']=gpu_audit(attempt/'gpu-transfer.jsonl',log,s)
        source_guard();receipt.update(status='completed-native-unqualified',GPUExecuted=True,hardwareQualified=False,realDeviceAccepted=False,stageResourceReceipts=stage_receipts,processes=manager.receipt(),allDirectChildrenReaped=all(p.returncode is not None for p in manager.processes),pythonMaxRSSBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,profileLibrary=pin(lib),endFreeBytes=shutil.disk_usage(ROOT).free,zeroCopyProved=False)
        dump(attempt/'BINDING.json',receipt);sealed={p.name:sha(p) for p in attempt.iterdir() if p.is_file()}
        for p in attempt.iterdir():
            if p.is_file():
                with p.open('rb') as f:os.fsync(f.fileno())
        if any(sha(attempt/name)!=value for name,value in sealed.items()):raise Refusal('ATOMIC_PIN_CHANGED')
        storage.atomic_directory(attempt,dest);fd=os.open(dest.parent,os.O_RDONLY);os.fsync(fd);os.close(fd);return receipt
    task=asyncio.create_task(pipeline());watch=asyncio.create_task(monitor())
    try:
        done,_=await asyncio.wait([task,watch],return_when=asyncio.FIRST_COMPLETED,timeout=900 if large else 120)
        if not done:raise Refusal('LIVE_TIMEOUT')
        if watch in done:await watch;raise Refusal('WATCHDOG_EXIT')
        return await task
    except BaseException as e:
        task.cancel();await manager.stop();await asyncio.gather(task,return_exceptions=True)
        receipt.update(status='failed-live-acceptance-attempt',error=type(e).__name__+':'+str(e),processes=manager.receipt(),allDirectChildrenReaped=all(p.returncode is not None for p in manager.processes),publishedBinding=False,stageResourceReceipts=stage_receipts)
        if attempt.exists():dump(attempt/'FAILURE.json',receipt)
        raise
    finally:watch.cancel();await asyncio.gather(watch,return_exceptions=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('variant',choices=['bounded36','circles4k300']);p.add_argument('mode',choices=MODES);p.add_argument('destination');p.add_argument('--fault',choices=['device','encoder','format']);a=p.parse_args()
    try:r=asyncio.run(run(a.variant,a.mode,pathlib.Path(a.destination).absolute(),a.fault));print(json.dumps({'status':r['status'],'GPUExecuted':r['GPUExecuted'],'qualified':False}))
    except Exception as e:print(json.dumps({'status':'failed-or-refused','reason':type(e).__name__+':'+str(e)}));raise SystemExit(2)
