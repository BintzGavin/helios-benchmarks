import hashlib,json,os,pathlib,signal,subprocess,sys,time
root=pathlib.Path(__file__).resolve().parent.parent
evidence=root/'comparison/fframes-concurrent-nv12-20261004'
lane=sys.argv[1]
allowed={'profile4k300','positive4k3','capture4k3','smoke3','smoke3-02','controls36','profile3','profile3-02','positive3','positive3-02','capture3','circles300','fault-device','fault-convert','fault-identity','fault-pool'}
assert lane in allowed
out=evidence/lane;out.mkdir(exist_ok=False)
capture=out/'capture'
binary=root/'build/fframes-current/release'/('circles-concurrent-nv12' if lane=='circles300' or '4k' in lane else 'nv12-color-controls')
argv=[str(binary),'hardware',str(out/'video.mp4'),str(root/'comparison/font'),'300' if lane in {'circles300','profile4k300'} else '3','300000000'] if lane=='circles300' or '4k' in lane else [str(binary),str(out/'video.mp4'),str(capture),'36' if lane=='controls36' else '3']
settings={'FFRAMES_EXPLICIT_NV12':'1','FFRAMES_HANDOFF_CAPTURE':str(capture),'FFRAMES_NV12_TRACE':str(out/'gpu-transfer.jsonl'),'COMPARISON_REQUIRE_HARDWARE_FRAMES':'1'}
if lane.startswith('smoke3'):settings['FFRAMES_NV12_POOL_TEST']='1'
if lane.startswith('profile') or lane.startswith('capture'):settings['FFRAMES_CAPTURE_NO_DOWNLOAD']='1'
if lane.startswith('positive'):settings['FFRAMES_NV12_POSITIVE_RGBA']='1'
if lane.startswith('profile') or lane.startswith('positive'):
    settings['DYLD_INSERT_LIBRARIES']=str(evidence/'transfer-interposer.dylib')
    settings['FFRAMES_EXTERNAL_TRANSFER_LOG']=str(out/'interposer.jsonl')
if lane.startswith('capture'):settings.update(FFRAMES_NV12_METAL_CAPTURE=str(out/'metal.gputrace'),MTL_CAPTURE_ENABLED='1')
if lane.startswith('fault-'):settings['FFRAMES_NV12_FAULT']=lane.removeprefix('fault-')
env={**os.environ,'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',**settings}
receipt={'lane':lane,'benchmarkTiming':False,'timingWindowOpen':False,'modifiedPipeline':True,'originalProduct':False,
         'argv':argv,'taskSettings':settings,'binarySha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
         'converterSha256':hashlib.sha256((root/'sources/fframes-concurrent-nv12/nv12-converter.dylib').read_bytes()).hexdigest(),'startedUnix':time.time()}
with (out/'stdout.log').open('w') as stdout,(out/'stderr-time-l.log').open('w') as stderr:
    launch=argv
    if 'DYLD_INSERT_LIBRARIES' in settings:
        launch=['/usr/bin/env','DYLD_INSERT_LIBRARIES='+settings['DYLD_INSERT_LIBRARIES'],*argv]
        env.pop('DYLD_INSERT_LIBRARIES',None)
    receipt['resourceCommand']=['/usr/bin/time','-l',*launch]
    p=subprocess.Popen(receipt['resourceCommand'],cwd=root,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
    receipt['pid']=p.pid;(out/'process.json').write_text(json.dumps(receipt,indent=2)+'\n')
    try:receipt['returncode']=p.wait(timeout=1200)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
        receipt.update(returncode=p.returncode,timeout=True)
receipt.update(status='completed' if receipt['returncode']==0 else 'failed',finishedUnix=time.time())
if (out/'video.mp4').exists():receipt['videoSha256']=hashlib.sha256((out/'video.mp4').read_bytes()).hexdigest()
if lane.startswith('fault-'):
    receipt['faultRefusedBeforeCompleteOutput']=receipt['returncode']!=0 and not (out/'video.mp4').exists()
(out/'process.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
sys.exit(0 if lane.startswith('fault-') and receipt.get('faultRefusedBeforeCompleteOutput') else int(receipt['returncode']!=0))
