import argparse,hashlib,json,math,pathlib,re
parser=argparse.ArgumentParser()
parser.add_argument('--measurement',type=pathlib.Path,required=True)
parser.add_argument('--output',type=pathlib.Path,required=True)
a=parser.parse_args()
policy=pathlib.Path('/Users/gavinbintz/Developer/helios/packages/portable/benchmarks/fframes-quality.ts')
text=policy.read_text()
fields={'minSsimY':('ssim','Y'),'minPsnrY':('psnr','psnr_y'),'minPsnrU':('psnr','psnr_u'),'minPsnrV':('psnr','psnr_v')}
limits={key:float(re.search(r'result\.'+key+r' >= ([0-9.]+)',text).group(1)) for key in fields}
assert limits=={'minSsimY':0.995,'minPsnrY':40.0,'minPsnrU':35.0,'minPsnrV':35.0},'Existing fidelity criteria changed'
data=json.loads(a.measurement.read_text())
if not data['status'].startswith('measurement-complete'):raise RuntimeError('Measurement not terminal; no admission produced')
records=[]
for artifact in data['artifacts']:
 quality=artifact.get('quality',{});frames=quality.get('frames',[])
 violations=[];minima={key:math.inf for key in fields}
 for frame in frames:
  for key,(kind,plane) in fields.items():
   value=float(frame[kind][plane]);minima[key]=min(minima[key],value)
   if math.isnan(value) or value<limits[key] or (kind=='ssim' and (not math.isfinite(value) or not 0<=value<=1)):violations.append({'frameIndex':frame['index'],'criterion':key,'actual':str(value),'required':limits[key]})
 complete=artifact.get('status')=='complete' and [f['index'] for f in frames]==list(range(300))
 cadence=artifact.get('cadence',{}).get('matchesExact30fps300Frames',False)
 records.append({'outputSha256':artifact['outputSha256'],'referenceKey':artifact['referenceKey'],'savedCopies':artifact['savedCopies'],'completeQuality':complete,'completeCadence':cadence,'minima':{k:str(v) for k,v in minima.items()},'violations':violations,'passedExistingFidelityAndCadencePolicy':complete and cadence and not violations})
result={'measurementManifest':str(a.measurement),'measurementManifestSha256':hashlib.sha256(a.measurement.read_bytes()).hexdigest(),'policySource':str(policy),'policySourceSha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'thresholds':limits,'records':records,'note':'Existing preregistered per-frame own-rasterizer fidelity policy; no new timing or cross-rasterizer equivalence claim.'}
with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps({'artifactReferencePairs':len(records),'passed':sum(x['passedExistingFidelityAndCadencePolicy'] for x in records),'thresholds':limits}))
