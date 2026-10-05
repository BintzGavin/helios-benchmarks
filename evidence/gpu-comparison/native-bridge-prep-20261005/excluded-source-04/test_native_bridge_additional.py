"""Independent CPU-only descendant, codec-error and no-launch controls."""
import asyncio,copy,errno,json,os,pathlib,signal,subprocess,sys,time
from unittest.mock import patch
import native_bridge_runner as m

OUT=m.OUT/'validation-extra-04';OUT.mkdir()
CASES=m.OUT/'cases/validation-extra-04';CASES.mkdir()
BASE=json.loads(next((m.OUT/'cases/validation-04/reference-metal-hevc-300/result').glob('ISSUED-SPEC.json')).read_text())
results=[]

async def descendant(parent_exits):
    d=CASES/('exited-parent' if parent_exits else 'live-parent');d.mkdir()
    marker=d/'CHILD.json'
    # The child inherits the supervisor-owned process group, ignores TERM, and
    # closes the pipes in the exited-parent case. No machine process discovery.
    heartbeat=d/'CPU-heartbeat.txt'
    child='import os,signal,json,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path('+repr(str(marker))+').write_text(json.dumps({"pid":os.getpid(),"group":os.getpgrp(),"CPUOnly":True}));\nfor i in range(2000):Path('+repr(str(heartbeat))+').write_text(str(i));time.sleep(.03)'
    parent='import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,"-c",'+repr(child)+'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);\nwhile not Path('+repr(str(marker))+').exists():time.sleep(.01)\n'+('' if parent_exits else 'time.sleep(60)')
    manager=m.Supervisor(d);p=await manager.spawn([str(m.PYTHON),'-c',parent],'CPU-parent')
    for _ in range(100):
        if marker.exists():break
        await asyncio.sleep(.01)
    assert marker.exists()
    if parent_exits:assert await p.wait()==0
    identity=json.loads(marker.read_text());assert identity['group']==p.pid
    await asyncio.sleep(.12);first=heartbeat.read_text();await asyncio.sleep(.12);assert heartbeat.read_text()!=first
    await manager.stop();assert p.returncode is not None
    await asyncio.sleep(.1);stopped=heartbeat.read_text();await asyncio.sleep(.4);assert heartbeat.read_text()==stopped
    r={'test':'descendant-TERM-refusal-'+('parent-already-exited' if parent_exits else 'parent-running'),'passed':True,'parentExitedBeforeStop':parent_exits,'processes':manager.receipt(),'childIdentity':identity,'CPUHeartbeatProgressedBeforeStop':True,'CPUHeartbeatUnchangedAfterStopSeconds':.4,'independentOSGroupCessationProof':False,'directParentReaped':True,'signal0QueryBlockedBySandbox':True,'GPUExecuted':False,'hardwareQualified':False}
    (d/'TEST.json').write_text(json.dumps(r,indent=2)+'\n');results.append(r)

async def bad_codec(name,elementary,reason):
    d=CASES/name;d.mkdir();s=copy.deepcopy(BASE);s['mode']='hardware';s['elementaryFixture']=m.pin(elementary);s['pins'].append(m.pin(elementary));s['pins'].append(m.pin(__file__));s.pop('nativeCommand',None);s.pop('attemptDirectory',None);s.pop('python',None)
    try:await m.run_job(s,d/'result')
    except m.Refusal as e:assert reason in str(e),str(e)
    else:raise AssertionError('bad codec published')
    f=json.loads(next(d.glob('attempt-*/FAILURE.json')).read_text());assert f['allChildrenReaped'] and not f['publishedBinding'] and not (d/'result').exists()
    r={'test':name,'passed':True,'refusal':f['error'],'fixturePin':m.pin(elementary),'processes':f['processes'],'directProcessesReaped':True,'GPUExecuted':False,'hardwareQualified':False};(d/'TEST.json').write_text(json.dumps(r,indent=2)+'\n');results.append(r)

async def main():
    await descendant(True);await descendant(False)
    broken=m.OUT/'fixtures/broken-elementary.h265';broken.write_bytes(b'not an elementary video\n')
    await bad_codec('copy-mux-failure',broken,'COPY-MUX_EXIT')
    full=m.OUT/'fixtures/full-range-elementary.h265'
    cmd=[str(m.FFMPEG),'-v','error','-xerror','-n','-f','hevc','-i',str(m.OUT/'fixtures/reference.hevc'),'-c:v','copy','-bsf:v','hevc_metadata=video_full_range_flag=1','-f','hevc',str(full)]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=10);assert r.returncode==0 and not r.stderr
    (OUT/'FULL-RANGE-FIXTURE-COMMAND.json').write_text(json.dumps({'argv':cmd,'exit':r.returncode,'fixture':m.pin(full),'CPUOnly':True,'VCLSpeedClaim':False},indent=2)+'\n')
    await bad_codec('conformance-failure',full,'SHARED-CONFORMANCE_EXIT')
    s=m.prepare_native('H-metal-hevc','reference',m.OUT/'native-not-launched/additional-refusal')
    with patch.object(m.shutil,'disk_usage',return_value=type('D',(),{'free':20*1024**3})()):
        try:m.validate(s,pathlib.Path(s['destination']))
        except m.Refusal as e:assert str(e)=='REAL_DEVICE_ACCEPTANCE_DISABLED_NO_LAUNCH'
        else:raise AssertionError('disk spoof activated hardware')
    results.append({'test':'enough-disk-does-not-enable-native','passed':True,'GPUExecuted':False})
    p=OUT/'NATIVE-NO-LAUNCH.json';p.write_text(json.dumps(s)+'\n')
    argv=[str(m.NODE),str(m.DRIVER),str(p)]
    r=subprocess.run(argv,capture_output=True,text=True,timeout=10);assert r.returncode and 'REAL_DEVICE_ACCEPTANCE_DISABLED_NO_LAUNCH' in r.stderr
    results.append({'test':'Node-direct-native-refusal','passed':True,'argv':argv,'exit':r.returncode,'stderr':r.stderr,'GPUExecuted':False})
    # Reaping checks use explicit driver child-wait receipts. The attempted
    # independent signal0 query was sandbox-blocked and is not claimed as proof.
    groups=[];helper_ids=[]
    for p in (m.OUT/'cases/validation-04').glob('*/*/*.json'):
        if p.name not in ['BINDING.json','FAILURE.json']:continue
        data=json.loads(p.read_text())
        for proc in data['processes']:
            assert proc['exit'] is not None
            groups.append({'group':proc['processGroup'],'record':str(p),'directProcessReaped':True})
        if 'producer' in data:
            producer=data['producer'];assert producer['helperWaitCompleted'] and producer['helperExit']['code']==0
            helper_ids.append({'pid':producer['helperPid'],'record':str(p),'waitCompleted':True})
    assert groups and helper_ids
    (OUT/'OWNED-PROCESS-WAITS.json').write_text(json.dumps({'groups':groups,'completedHelperWaits':helper_ids,'independentOSGroupCessationProof':False,'signal0QueryBlockedBySandbox':True,'noMachineProcessOrEnvironmentInspection':True},indent=2)+'\n')
    results.append({'test':'explicit-owned-process-waits','passed':True,'directWaitsChecked':len(groups),'helperWaitsChecked':len(helper_ids),'GPUExecuted':False})
    (OUT/'TEST-REPORT.json').write_text(json.dumps({'status':'passed CPU additional controls','tests':results,'testCount':len(results),'sourcePin':m.pin(__file__),'GPUExports':0,'realDeviceAccepted':False,'hardwareQualified':False,'timingWindowOpen':False},indent=2)+'\n')
    print(json.dumps({'tests':len(results),'GPUExports':0}))

asyncio.run(main())
