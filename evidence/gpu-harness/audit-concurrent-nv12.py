"""Independent post-render audit of modified production-concurrent explicit NV12 handoff."""
import argparse
import hashlib
import json
import pathlib
import zlib


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def audit_ledger(rows, download=True):
    assert [r['seq'] for r in rows] == list(range(1, len(rows) + 1)), 'global sequence'
    init = [r for r in rows if r['event'] == 'initialize']
    assert len(init) == 1 and init[0]['benchmarkTiming'] is False
    cfg = init[0]
    plans = [r for r in rows if r['event'] == 'pipeline']
    assert len(plans) == 1
    plan = plans[0]
    # On the pinned 11-core M3 Pro the unchanged policy is 3 GPU, 5+5 workers, queue10.
    assert (plan['gpuContexts'], plan['generators'], plan['encoderWorkers'],
            plan['configuredEncoderThreads'], plan['queueSize']) == (3, 5, 5, 11, 10), 'production policy'
    for role, n in [('gpu', 3), ('generator', 5), ('encoder', 5)]:
        started = [r['thread'] for r in rows if r['event'] == 'worker-start' and r['role'] == role]
        assert len(started) == n and len(set(started)) == n, f'{role} starts'
    phases = ['gpu-complete', 'capture-begin', 'capture-complete', 'encoder-send-begin',
              'encoder-send-return', 'avbuffer-final-reference-release']
    maps = {phase: {} for phase in phases}
    for r in rows:
        if r['event'] in maps:
            d = maps[r['event']]
            assert r['index'] not in d, 'duplicate phase/index'
            d[r['index']] = r
    expected = set(range(cfg['frames']))
    assert all(set(d) == expected for d in maps.values()), 'complete indexed phase coverage'
    bindings = []
    for index in sorted(expected):
        rs = [maps[p][index] for p in phases]
        assert [r['seq'] for r in rs] == sorted(r['seq'] for r in rs), 'per-frame fence/capture/send/release order'
        g, b, c, s, returned, release = rs
        assert g['fence'] == 'Skia raster then Metal conversion completion returned', 'actual source GPU completion'
        assert g['sourceIndex'] == c['sourceIndex'] == index + cfg['sourceOffset'], 'source mapping'
        assert len({r['segment'] for r in rs}) == 1, 'scheduler/encoder segment binding'
        assert len({r['pixelBuffer'] for r in (g, b, c, returned, release)}) == 1, 'pixelbuffer identity'
        assert len({r['avframe'] for r in (g, b, c, returned)}) == 1, 'AVFrame identity'
        assert len({r['avbuffer'] for r in (g, b, c, returned)}) == 1, 'AVBuffer identity'
        assert c['originalIdentityUnchanged'] is True and returned['success'] is True
        assert c['packedBytes'] == (cfg['width'] * cfg['height'] * 3 // 2 if download else 0) and c['downloadFormat'] == 'nv12'
        if not download:assert c['compressedBytes']==0
        assert b['encoder'] == c['encoder'] == s['encoder'] == returned['encoder'], 'original encoder'
        assert s['pts'] == index
        bindings.append({'index': index, 'sourceIndex': g['sourceIndex'], 'segment': g['segment'],
                         'encoder': s['encoder'], 'pixelBuffer': g['pixelBuffer'], 'renderer': g['renderer']})
    sends = [r for r in rows if r['event'] == 'encoder-send-return']
    for segment in {r['segment'] for r in sends}:
        part = [r for r in sends if r['segment'] == segment]
        indexes = [r['index'] for r in part]
        assert indexes == list(range(min(indexes), max(indexes) + 1)), 'segment contiguous ordered sends'
        assert indexes[0] == segment and len({r['encoder'] for r in part}) == 1
        drains = [r for r in rows if r['event'] == 'encoder-drained' and r['encoder'] == part[0]['encoder']
                  and r['seq'] > part[-1]['seq']]
        assert drains, 'actual original codec drain'
    assert rows[-1]['event'] == 'finalize' and rows[-1]['passed'] is True, 'mandatory complete ledger'
    return cfg, plan, bindings


def control_oracle(source):
    import math
    colors=[(0,0,0),(255,255,255),(255,0,0),(0,255,0),(0,0,255),(0,255,255),(255,0,255),(255,255,0)]
    def rgb(x,y):
        if y<32:return colors[x//32]
        if y<64:return (255,0,0) if (x//2+y//2+source)%2==0 else (0,255,255)
        if y<96:return (0,255,0) if (x+source)%2==0 else (255,0,255)
        v=(x+source)%256;return v,v,v
    def transfer(v):
        s=v/255.;linear=s/12.92 if s<=.04045 else ((s+.055)/1.055)**2.4
        return 4.5*linear if linear<.018 else 1.099*linear**.45-.099
    lumas=bytearray(256*128);uv=bytearray(256*64)
    for py in range(64):
        for px in range(128):
            cb=cr=0.
            for dy in range(2):
                for dx in range(2):
                    x,y=px*2+dx,py*2+dy;r,g,b=map(transfer,rgb(x,y));l=.2126*r+.7152*g+.0722*b
                    lumas[y*256+x]=round(16+219*l);cb+=(b-l)/1.8556;cr+=(r-l)/1.5748
            uv[py*256+px*2]=round(128+56*cb);uv[py*256+px*2+1]=round(128+56*cr)
    return bytes(lumas+uv)


def audit(directory, controls=False):
    rows = [json.loads(line) for line in (directory / 'handoff.jsonl').read_text().splitlines()]
    cfg, plan, bindings = audit_ledger(rows)
    files = sorted(directory.glob('*.nv12.zlib'))
    assert [p.name for p in files] == [f'{i:06}.nv12.zlib' for i in range(cfg['frames'])]
    captures = {r['index']: r for r in rows if r['event'] == 'capture-complete'}
    for p, item in zip(files, bindings):
        encoded = p.read_bytes()
        d = zlib.decompressobj()
        raw = d.decompress(encoded, cfg['width'] * cfg['height'] * 3 // 2 + 1)
        assert d.eof and not d.unused_data and not d.unconsumed_tail, 'bounded zlib framing'
        assert len(raw) == captures[item['index']]['packedBytes']
        assert len(encoded) == captures[item['index']]['compressedBytes']
        item.update(compressedBytes=len(encoded), rawBytes=len(raw), compressedSha256=hashlib.sha256(encoded).hexdigest(),
                    rawSha256=hashlib.sha256(raw).hexdigest(), rawMd5=hashlib.md5(raw).hexdigest())
        if controls:
            assert (cfg['width'], cfg['height']) == (256, 128)
            expected = control_oracle(item['sourceIndex'])
            differing = sum(a != b for a, b in zip(expected, raw))
            item.update(independentOracleSha256=hashlib.sha256(expected).hexdigest(), differingBytes=differing)
            maximum=max(abs(a-b) for a,b in zip(raw,expected));item['maximumNominalCodeValueError']=maximum
            assert maximum<=1, f"independent NV12 color control failed frame {item['index']}: maxdelta {maximum}"
    return {'passed': True, 'benchmarkTiming': False, 'zeroCopyProved': False,
            'source': 'modified MaxPerformance explicit GPU NV12 CVPixelBuffer at encoder handoff',
            'directExplicitNV12OracleProved': True, 'avbufferLifetimeObserved': True,
            'opaqueEncoderLifetimeKnown': False, 'independentPredeterminedControls': controls,
            'configuration': cfg, 'pipeline': plan, 'ledgerSha256': sha(directory / 'handoff.jsonl'), 'frames': bindings}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=pathlib.Path)
    parser.add_argument('--controls', action='store_true')
    args = parser.parse_args()
    result = audit(args.directory, args.controls)
    (args.directory / 'independent-handoff-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('configuration', 'pipeline', 'frames')}))
