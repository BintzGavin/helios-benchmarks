#!/usr/bin/env python3
"""Balanced benchmark supervisor. Templates are plans, never fabricated measurements."""
import argparse, datetime, hashlib, json, pathlib, statistics, subprocess, sys, time
import os, threading

def sha(path):
    with open(path,'rb') as handle:
        return hashlib.file_digest(handle,'sha256').hexdigest()

def schedule(ids, rounds=3):
    return [("warmup",0,i) for i in ids] + [("timed",r+1,ids[(j+r)%len(ids)]) for r in range(rounds) for j in range(len(ids))]

def balanced_schedule(ids):
    """Four rounds with each engine pair ordered equally often in either direction."""
    orders=[ids,list(reversed(ids)),list(reversed(ids)),ids]
    return [("warmup",0,i) for i in ids]+[("timed",r+1,i) for r,order in enumerate(orders) for i in order]

def resource_samples(stop,path):
    # Read-only host process observations, lightweight and equal for every engine.
    # The exported process group and exact child argv are in the adapter receipts.
    with path.open('w') as handle:
        while not stop.is_set():
            result=subprocess.run(['/bin/ps','-axo','pid,ppid,pgid,%cpu,rss,comm'],capture_output=True,text=True)
            rows=[line for line in result.stdout.splitlines() if any(name in line for name in ['helios-gpu','textgrid-adapter','ffmpeg','Google Chrome','node'])]
            handle.write(json.dumps({'monotonic_ns':time.perf_counter_ns(),'process_rows':rows})+'\n');handle.flush()
            stop.wait(1)

def validate_config(config):
    assert config['scene']=={'width':1920,'height':1080,'frames':300,'fps':30,'name':'TextGrid'}, 'Fixture mismatch'
    assert config['lane'] in ['gpu-raster-software-x264','hardware-product-pipeline']
    assert len(config['engines'])>=2, 'At least two engines required'
    ids=[e['id'] for e in config['engines']]
    assert len(ids)==len(set(ids)), 'Duplicate engine IDs'
    for e in config['engines']:
        assert isinstance(e['command'],list) and e['command'], 'Command must be argv array'
        assert any('{output}' in a for a in e['command']), 'Command must use isolated output path'
        assert e.get('source_pin') and e.get('backend') and e.get('codec'), 'Pin/backend/codec required'
    return ids

def validate_screen(engine):
    path=pathlib.Path(engine.get('screen_quality',''))
    if not engine.get('screen_quality_passed') or not path.is_file():
        raise ValueError('missing all-frame quality screen')
    if sha(path)!=engine['screen_quality_sha256']:
        raise ValueError('screen receipt hash changed')
    screen=json.loads(path.read_text())
    if screen.get('passed') is not True or screen.get('quality',{}).get('status')!='evaluated':
        raise ValueError('screen did not pass evaluated fidelity')
    for binding in engine.get('file_bindings',[]):
        if sha(binding['path'])!=binding['sha256']:
            raise ValueError('source/executable binding changed: '+binding['path'])

def main():
    p=argparse.ArgumentParser()
    p.add_argument('config');p.add_argument('--execute',action='store_true')
    p.add_argument('--preflight',default='evidence/preflight.json');p.add_argument('--out',default='outputs')
    args=p.parse_args();config=json.loads(pathlib.Path(args.config).read_text());ids=validate_config(config)
    runs=balanced_schedule(ids) if config.get('four_balanced_rounds') else schedule(ids)
    plan={'lane':config['lane'],'scene':config['scene'],'runs':runs,'status':'dry-run-only','performance_results':None}
    if not args.execute:
        print(json.dumps(plan,indent=2));return 0
    host=json.loads(pathlib.Path(args.preflight).read_text())
    if not host.get('physical_gpu_observed'):
        raise SystemExit('BLOCKED: preflight did not observe a physical GPU; no timed exports started')
    if config['lane']=='hardware-product-pipeline' and not host.get('hardware_encoder_available'):
        raise SystemExit('BLOCKED: no actual hardware encode succeeded; no timed exports started')
    engines={e['id']:e for e in config['engines']}
    for e in engines.values():
        if not e.get('ready'):
            raise SystemExit('BLOCKED: '+e['id']+' adapter not qualified: '+e.get('blocker','missing runtime validation'))
        for item in ['gpu_evidence','reference']:
            if not pathlib.Path(e[item]).is_file(): raise SystemExit('BLOCKED: missing '+e['id']+' '+item)
        if sha(e['reference'])!=e['reference_sha256']: raise SystemExit('BLOCKED: reference hash changed')
        if not e.get('runtime_attestation_reviewed'):
            raise SystemExit('BLOCKED: review actual selected device and active encoding/raster path for '+e['id'])
        try: validate_screen(e)
        except ValueError as error: raise SystemExit('BLOCKED: '+e['id']+' '+str(error))
    out=pathlib.Path(args.out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    frozen={'config':config,'config_sha256':sha(args.config),'preflight':host,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':[]}
    (out/'manifest.json').write_text(json.dumps(frozen,indent=2))
    validator=pathlib.Path(__file__).with_name('validate_video.py')
    for phase,round_,engine_id in plan['runs']:
        e=engines[engine_id];run=out/f'{phase}-{round_}-{engine_id}';run.mkdir()
        validate_screen(e)
        output=run/'output.mp4';argv=[a.replace('{output}',str(output)) for a in e['command']]
        stop=threading.Event();monitor=threading.Thread(target=resource_samples,args=(stop,run/'resources.jsonl'),daemon=True);monitor.start()
        start=time.perf_counter_ns()
        with open(run/'export.log','w') as log:
            result=subprocess.run(argv,cwd=e.get('cwd'),env=None,stdout=log,stderr=subprocess.STDOUT)
        export_end=time.perf_counter_ns()
        stop.set();monitor.join()
        if result.returncode or not output.is_file(): raise SystemExit('Export failed; logs preserved at '+str(run))
        # Every lane uses exactly one full post-export decode. Fidelity evaluation is later.
        with open(run/'decode.log','w') as log:
            decode=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-xerror','-threads','8','-i',str(output),'-map','0:v:0','-f','null','-'],stdout=log,stderr=subprocess.STDOUT)
        delivery_end=time.perf_counter_ns()
        receipt={'phase':phase,'round':round_,'engine':engine_id,'command':argv,'export_ns':export_end-start,'delivered_ns':delivery_end-start,'decode_returncode':decode.returncode,'output_sha256':sha(output),'bytes':output.stat().st_size,'quality_status':'not-yet-run'}
        frozen['results'].append(receipt);(out/'manifest.json').write_text(json.dumps(frozen,indent=2))
        if decode.returncode: raise SystemExit('Decode failed; no qualified result')
        # Exact validator contract is documented separately. Keep measurement outside delivery clock.
        quality=subprocess.run([sys.executable,str(validator),str(output),'--reference',e['reference'],'--engine',engine_id,'--reference-engine',engine_id,'--ssim-y','0.995','--psnr-y','40','--psnr-uv','35','--output',str(run/'quality.json')])
        receipt['quality_status']='passed' if quality.returncode==0 else 'failed'
        (out/'manifest.json').write_text(json.dumps(frozen,indent=2))
        if quality.returncode: raise SystemExit('Quality/cadence failed; no superiority claim')
    medians={i:statistics.median(r['delivered_ns'] for r in frozen['results'] if r['phase']=='timed' and r['engine']==i)/1e9 for i in ids}
    summary={'status':'structure-and-fidelity-qualified-recorded-pipelines','median_delivered_seconds':medians,'no_cross_lane_comparison':True,'comparability_and_runtime_acceleration_require_evidence_review':True}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2));return 0

if __name__=='__main__': raise SystemExit(main())
