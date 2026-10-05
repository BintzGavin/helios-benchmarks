"""CPU refusal/syntax controls for the separately enabled live preset runner."""
import json,pathlib,subprocess
import live_hevc_runner as m
from unittest.mock import patch
out=m.OUT/'cpu-guards';out.mkdir();tests=[]
def refused(name,fn,expected):
    try:fn()
    except Exception as e:assert expected in str(e),(name,str(e));tests.append({'test':name,'passed':True,'reason':str(e),'GPUJobsStarted':False})
    else:raise AssertionError(name)
refused('variant',lambda:m.fixed('fixture','reference'),'PRESET')
refused('mode',lambda:m.fixed('bounded36','software'),'PRESET')
refused('disk',lambda:m.start_guard('bounded36','reference',m.OUT/'refusal-no-launch',free=m.GATE-1),'SERIAL_9GIB_GATE')
refused('outside',lambda:m.start_guard('bounded36','reference',m.ROOT/'outside-no-launch',free=m.GATE),'OUTPUT_SCOPE')
refused('4K-unqualified',lambda:m.start_guard('circles4k300','reference',m.OUT/'4K-no-launch',free=m.GATE),'BOUNDED_LIVE_ACCEPTANCE_REQUIRED')
(out/'existing').mkdir();refused('existing',lambda:m.start_guard('bounded36','reference',out/'existing',free=m.GATE),'EXISTING_DESTINATION')
(out/'symlink').symlink_to(out/'existing');refused('symlink',lambda:m.start_guard('bounded36','reference',out/'symlink',free=m.GATE),'OUTPUT_SCOPE')
fake=out/'fake-acceptance';fake.mkdir()
with patch.object(m,'OUT',fake):
    (fake/'BOUNDED-ACCEPTANCE.json').write_text(json.dumps({'status':'qualified-bounded-live-metal-hevc','GPUExecuted':False,'hardwareQualified':False})+'\n')
    refused('CPU-receipt-cannot-qualify-live',m.acceptance_gate,'BOUND_ACCEPTANCE_CHANGED')
for mode in m.MODES:
    s=m.fixed('bounded36',mode);assert s['frames']==(3 if mode.startswith('positive-') else 36) and s['sourceStart']==3 and s['bitrate']==300000000 and s['encoderPool']==3
    tests.append({'test':'fixed-'+mode,'passed':True,'preset':s,'GPUJobsStarted':False})
commands=[]
for fault in ['DEVICE','ENCODER','FORMAT']:
    argv=['/usr/bin/xcrun','clang++','-fsyntax-only','-fobjc-arc','-std=c++17','-DFAIL_'+fault,str(m.ROOT/'checkpoint/live_hevc_faults.mm')]
    p=subprocess.run(argv,capture_output=True,text=True,timeout=20,env={'PATH':'/usr/bin:/bin','TMPDIR':'/tmp'});assert p.returncode==0,p.stderr
    commands.append({'argv':argv,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'GPUConstructorLoaded':False})
    tests.append({'test':'fault-syntax-'+fault,'passed':True,'GPUJobsStarted':False})
argv=[str(m.NODE),'--check',str(m.DRIVER)];p=subprocess.run(argv,capture_output=True,text=True,timeout=10);assert p.returncode==0,p.stderr
commands.append({'argv':argv,'exit':p.returncode,'stderr':p.stderr});tests.append({'test':'node-syntax','passed':True,'GPUJobsStarted':False})
(out/'REPORT.json').write_text(json.dumps({'status':'passed CPU prelaunch controls only','tests':tests,'testCount':len(tests),'commands':commands,'GPUJobsStarted':False},indent=2)+'\n');print(json.dumps({'tests':len(tests),'GPUJobsStarted':False}))
