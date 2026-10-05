import argparse,collections,hashlib,importlib.util,json,pathlib
root=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('nv12audit',root/'checkpoint/audit-concurrent-nv12.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

def stages(directory):
    core=[json.loads(x) for x in (directory/'capture/handoff.jsonl').read_text().splitlines()]
    rows=[json.loads(x) for x in (directory/'gpu-transfer.jsonl').read_text().splitlines()]
    assert [r['seq'] for r in rows]==list(range(1,len(rows)+1))
    n=core[0]['frames'];expected=set(range(n))
    def indexed(event,source):
        selected=[r for r in source if r['event']==event and r.get('index') in expected]
        assert len(selected)==n and {r['index'] for r in selected}==expected,event
        return {r['index']:r for r in selected}
    raster=indexed('raster-complete',core);handoff=indexed('gpu-complete',core)
    begin=indexed('conversion-begin',rows);complete=indexed('conversion-complete',rows)
    source_release=indexed('source-avbuffer-owner-release',rows);dest_release=indexed('avbuffer-owner-release',rows)
    bindings=[]
    for i in range(n):
        a,b,c,d,e,f=raster[i],begin[i],complete[i],source_release[i],handoff[i],dest_release[i]
        assert a['fence']=='flush_submit_and_sync_cpu returned'
        assert a['sourcePixelBuffer']==b['sourcePixelBuffer']==d['sourcePixelBuffer']
        assert a['sourceTexture']==b['sourceTexture']
        assert b['pixelBuffer']==c['pixelBuffer']==e['pixelBuffer']==f['pixelBuffer']
        assert b['surfaceId']==c['surfaceId']==f['surfaceId']
        assert b['context']==c['context']==d['context']==f['context']
        assert b['seq']<c['seq']<d['seq'] and c['seq']<f['seq']
        assert c['completed'] and b['sourceFenceAlreadyCompleted']
        assert c['sameSourceTextureIOSurface'] and c['sameDestinationIOSurfacePlanes']
        assert c['gpuEndSeconds']>=c['gpuStartSeconds']>0
        bindings.append({'index':i,'context':b['context'],'sourceSurfaceId':b['sourceSurfaceId'],
                         'destinationSurfaceId':b['surfaceId'],'gpuStartSeconds':c['gpuStartSeconds'],'gpuEndSeconds':c['gpuEndSeconds']})
    active={r['context'] for r in begin.values()}
    creates={r['context']:r for r in rows if r['event']=='converter-create'}
    assert all(creates[x]['poolThreshold']==64 and creates[x]['extraGpuCopy'] is False for x in active)
    assert len({creates[x]['deviceRegistryId'] for x in active})==1
    # CoreVideo alone allocates/recycles; ensure no overlapping observed AVBuffer owners.
    live={};peak=collections.Counter()
    for r in rows:
        if r.get('index') not in expected:continue
        if r['event']=='conversion-begin':
            key=r['pixelBuffer'];assert key not in live
            live[key]=r;peak[r['context']]=max(peak[r['context']],sum(x['context']==r['context'] for x in live.values()))
        if r['event']=='avbuffer-owner-release':
            old=live.pop(r['pixelBuffer']);assert old['index']==r['index']
    assert not live and max(peak.values())<=64
    result={'passed':True,'frames':n,'actualConversionContexts':len(active),'deviceRegistryId':creates[next(iter(active))]['deviceRegistryId'],
            'directSkiaTextureImport':True,'extraGpuCopy':False,'peakObservedAVBufferOwnersByContext':dict(peak),
            'sourceOwnedThroughConversionFence':True,'observedDestinationOwnersAllReleased':True,
            'opaqueEncoderOwnershipKnown':False,'zeroCopyProved':False,'benchmarkTiming':False,
            'coreLedgerSha256':audit.sha(directory/'capture/handoff.jsonl'),'gpuTraceSha256':audit.sha(directory/'gpu-transfer.jsonl'),'indexedStages':bindings}
    if n==300:assert len(active)==3,'full workload must exercise all production GPU contexts'
    (directory/'GPU-STAGE-AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def profile(evidence):
    def read(lane):
        p=evidence/lane/'interposer.jsonl';rows=[json.loads(x) for x in p.read_text().splitlines()]
        assert sum(r['event']=='interposer-installed' for r in rows)==1
        return rows,dict(collections.Counter(r['event'] for r in rows))
    normal,counts=read('profile3-02');positive,pc=read('positive3-02')
    downloads=['CVPixelBufferLockBaseAddress','IOSurfaceLock','texture-getBytes','texture-to-buffer']
    assert all(counts.get(event,0)==0 for event in downloads)
    assert pc.get('texture-to-buffer')==3 and sum(r['bytes'] for r in positive if r['event']=='texture-to-buffer')==256*128*4*3
    assert pc.get('CVPixelBufferLockBaseAddress')==3 and pc.get('CVPixelBufferGetBaseAddressOfPlane')==6
    assert not list((evidence/'profile3-02/capture').glob('*.nv12.zlib'))
    for lane in ['profile3-02','positive3-02','capture3']:stages(evidence/lane)
    capture=evidence/'capture3/metal.gputrace'
    assert capture.is_dir() and sum(p.stat().st_size for p in capture.rglob('*') if p.is_file())>100000
    result={'passed':True,'scope':'separate excluded 3-frame actual GPU profile, not 4K profile yet',
            'uncaptured':counts,'positiveControls':pc,'positiveRGBABytes':256*128*4*3,'metalCaptureBytes':sum(p.stat().st_size for p in capture.rglob('*') if p.is_file()),
            'systemPointerQueriesIntentUnknown':True,'unhookedDriverEncoderTransfersUnknown':True,
            'hookScope':'CV/IOSurface map and pointer APIs; concrete probed Metal texture getBytes variant and texture-to-buffer selector; buffer contents intent unknown',
            'zeroCopyProved':False,'benchmarkTiming':False,'converterSha256':json.loads((evidence/'profile3-02/process.json').read_text())['converterSha256']}
    (evidence/'BOUNDED-PROFILE-REPORT.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=pathlib.Path);p.add_argument('--profile',action='store_true');args=p.parse_args()
    result=profile(args.directory) if args.profile else stages(args.directory)
    print(json.dumps({k:v for k,v in result.items() if k!='indexedStages'}))
