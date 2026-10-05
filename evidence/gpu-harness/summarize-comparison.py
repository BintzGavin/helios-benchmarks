import pathlib,json,statistics,sys
root=pathlib.Path(sys.argv[1]);m=json.loads((root/'manifest.json').read_text());out={'status':'qualified','scene':m['config']['scene'],'lane':m['config']['lane'],'limitations':m['config']['limitations'],'zeroCopyProved':False,'warmupsExcluded':True,'engines':{}}
for engine in [e['id'] for e in m['config']['engines']]:
 rows=[r for r in m['results'] if r['phase']=='timed' and r['engine']==engine]
 assert len(rows)==4 and all(r['quality_status']=='passed' for r in rows)
 qualities=[json.loads((root/f"timed-{r['round']}-{engine}/quality.json").read_text()) for r in rows]
 out['engines'][engine]={'exportSeconds':[r['export_ns']/1e9 for r in rows],'deliveredSeconds':[r['delivered_ns']/1e9 for r in rows],'medianExportSeconds':statistics.median(r['export_ns']/1e9 for r in rows),'medianDeliveredSeconds':statistics.median(r['delivered_ns']/1e9 for r in rows),'allPass':all(q['passed'] for q in qualities),'worstSsimY':min(q['quality']['ssim']['minimum']['Y'] for q in qualities),'worstPsnr':{plane:min(q['quality']['psnr']['minimum']['psnr_'+plane.lower()] for q in qualities) for plane in ['Y','U','V']}}
(root/'reviewed-summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
