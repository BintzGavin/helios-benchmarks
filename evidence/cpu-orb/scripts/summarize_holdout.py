#!/usr/bin/python3
import json
import statistics
from pathlib import Path

MANIFEST = Path('/home/user/evidence/helios-cpu-linux-2026-10-02/outputs/holdout-v1/manifest.json')
OUTPUT = Path('/home/user/evidence/helios-cpu-linux-2026-10-02/metrics/component-summary.json')

manifest = json.loads(MANIFEST.read_text())
summary = {'profiles': {}, 'ratiosOfMedians': {}}

for profile in manifest['profiles']:
    profile_id = profile['id']
    records = [r for r in manifest['records'] if r['id'] == profile_id and r['phase'] == 'timed']
    values = lambda getter: [getter(r) for r in records]
    delivered = values(lambda r: r['deliveredWallNs'])
    item = {
        'timedDeliveredWallNs': delivered,
        'medianDeliveredWallNs': statistics.median(delivered),
        'medianEngineProcessWallNs': statistics.median(values(lambda r: r['components']['engine']['wallNs'])),
        'medianRepairWallNs': statistics.median(values(lambda r: r['components'].get('repair', {}).get('wallNs', 0))),
        'medianFinalDecodeWallNs': statistics.median(values(
            lambda r: r['details']['stats']['finalVerifyMs'] * 1_000_000
            if r['engine'] == 'H' else r['components']['verify']['wallNs'])),
    }
    item['finalDecodeShareOfMedianDelivered'] = item['medianFinalDecodeWallNs'] / item['medianDeliveredWallNs']
    if profile['engine'] == 'H':
        item.update(
            medianRenderMs=statistics.median(values(lambda r: r['details']['stats']['renderMs'])),
            medianFinalizeMs=statistics.median(values(lambda r: r['details']['stats']['finalizeMs'])),
            medianFinalVerifyMs=statistics.median(values(lambda r: r['details']['stats']['finalVerifyMs'])),
            medianMaxWorkerDrawMs=statistics.median(values(
                lambda r: max(row['drawMs'] for row in r['details']['stats']['ranges']))),
            medianMaxWorkerEncoderWaitMs=statistics.median(values(
                lambda r: max(row['encoderWaitMs'] for row in r['details']['stats']['ranges']))),
        )
    elif profile['engine'] == 'R':
        raster_done = values(lambda r: r['details']['progress'][-1]['elapsedNs'])
        render_media = values(lambda r: r['details']['renderMediaNs'])
        item.update(
            medianBrowserOpenNs=statistics.median(values(lambda r: r['details']['browserOpenNs'])),
            medianSelectCompositionNs=statistics.median(values(lambda r: r['details']['selectCompositionNs'])),
            medianRenderMediaNs=statistics.median(render_media),
            medianRasterFramesDoneNs=statistics.median(raster_done),
            medianPostRasterRenderMediaNs=statistics.median([total - raster for total, raster in zip(render_media, raster_done)]),
            medianBrowserCloseNs=statistics.median(values(lambda r: r['details']['browserCloseNs'])),
        )
    summary['profiles'][profile_id] = item

for preset in ['medium', 'ultrafast']:
    medians = {
        engine: summary['profiles'][f'{engine}-{preset}-w2-t1']['medianDeliveredWallNs']
        for engine in ['H', 'F', 'R']
    }
    summary['ratiosOfMedians'][preset] = {
        'F_over_H': medians['F'] / medians['H'],
        'R_over_H': medians['R'] / medians['H'],
        'R_over_F': medians['R'] / medians['F'],
    }

OUTPUT.write_text(json.dumps(summary, indent=2) + '\n')
