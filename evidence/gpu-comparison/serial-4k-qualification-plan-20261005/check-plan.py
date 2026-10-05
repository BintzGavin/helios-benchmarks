"""Read-only preflight. This deliberately cannot launch jobs."""
import hashlib,json,pathlib,shutil,sys
root=pathlib.Path('/Users/gavinbintz/Documents/Codex/2026-10-02/task')
out=root/'comparison/serial-4k-qualification-plan-20261005'
pins=json.loads((out/'EXACT-INPUT-PINS.json').read_text())['files']
bad=[]
for p in pins:
    try:
        f=pathlib.Path(p['path']);h=hashlib.sha256()
        with f.open('rb') as s:
            for b in iter(lambda:s.read(1024*1024),b''):h.update(b)
        if f.stat().st_size!=p['bytes'] or h.hexdigest()!=p['sha256']:bad.append(p['path'])
    except OSError:bad.append(p['path'])
cfg=json.loads((out/'CONFIG.json').read_text());r=json.loads((out/'RESOURCE-LEDGER.json').read_text())
assert r['direct300Bytes']==3840*2160*3//2*300
assert r['retainedRawPeakBudgetBytes']==sum(x['budgetBytes'] for x in r['entries'])
assert r['retainedRawGateBytes']>=r['retainedRawPeakBudgetBytes']
assert cfg['scene']['sourceIndicesInclusive']==[3,302] and cfg['scene']['frames']==300
assert not cfg['performancePolicy']['timingWindowOpen'] and not r['streamingEnabled']
free=shutil.disk_usage(root).free
print(json.dumps({'status':'BLOCKED' if free<r['retainedRawGateBytes'] or bad or cfg['launchPrerequisitesStillPending'] else 'read-only-preflight-passed',
 'pinsChecked':len(pins),'mismatchedPins':bad,'freeBytes':free,'requiredFreeBytes':r['retainedRawGateBytes'],'shortfallBytes':max(0,r['retainedRawGateBytes']-free),
 'arithmeticAndSceneChecksPassed':True,'integrationPrerequisites':cfg['launchPrerequisitesStillPending'],'jobsLaunched':False,'timingWindowOpen':False},indent=2))
sys.exit(1 if bad else 0)
