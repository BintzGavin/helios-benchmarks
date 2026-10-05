import argparse,ast,hashlib,importlib.util,json,pathlib
root=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',required=True);parser.add_argument('--results',type=pathlib.Path,required=True);args=parser.parse_args()
destination=args.results.resolve();destination.mkdir(parents=True,exist_ok=False)
original=root/'quality-measurement-v1/results/full-v1/manifest.json';data=json.loads(original.read_text());modulePath=root/'quality-measurement-v1/run.py'
assert hashlib.sha256(modulePath.read_bytes()).hexdigest()==data['sourceRuntimeSha256'][str(modulePath)]
spec=importlib.util.spec_from_file_location('saved_quality_v1',modulePath);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
function=next(x for x in ast.parse(modulePath.read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='metrics')
source=ast.get_source_segment(modulePath.read_text(),function);assert source.count('setpts=N/(30*TB)')==2
source=source.replace('setpts=N/(30*TB)','settb=expr=1/30,setpts=N');exec(compile(source,str(__file__),'exec'),module.__dict__)
data['originalMeasurementManifest']=str(original);data['originalMeasurementManifestSha256']=module.sha(original);data['comparisonClockRevision']='Affected Remotion metric comparisons use exact common 1/30 timebase and integer frame index. Original actual cadence evidence is unchanged.';data['revisionScriptSha256']=module.sha(pathlib.Path(__file__));data['status']='running'
module.save(destination/'manifest.json',data)
try:
 for artifact in data['artifacts']:
  if not artifact['referenceKey'].startswith('R'):continue
  folder=destination/(artifact['referenceKey']+'-'+artifact['outputSha256']);folder.mkdir();output=pathlib.Path(artifact['savedCopies'][0]['path']);reference=data['references'][artifact['referenceKey']]
  assert artifact['cadence']['matchesExact30fps300Frames'] and module.sha(output)==artifact['outputSha256'] and module.sha(pathlib.Path(reference['path']))==reference['sha256']
  artifact['originalMetricDirectory']=artifact['directory'];artifact['directory']=str(folder);artifact['quality']=module.metrics(folder,output,pathlib.Path(reference['path']));artifact['comparisonClock']='1/30, integer N'
  module.save(folder/'measurement.json',artifact);module.save(destination/'manifest.json',data);print('Measured',artifact['referenceKey'],artifact['outputSha256'][:12],flush=True)
 assert module.sha(original)==data['originalMeasurementManifestSha256']
 data['status']='measurement-complete';data['metricRevisionArtifacts']=4
except Exception as error:
 data.update(status='failed',failure=f'{type(error).__name__}: {error}');raise
finally:module.save(destination/'manifest.json',data)
