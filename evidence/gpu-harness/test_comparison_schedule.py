import importlib.util, pathlib, unittest, tempfile, json
root=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('runner',root/'preparation/unpacked/helios-gpu-comparison-prep/run_matrix.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

class BalancedOrder(unittest.TestCase):
 def test_each_pair_runs_in_either_order_twice(self):
  ids=['H','F','R']; runs=runner.balanced_schedule(ids)
  self.assertEqual(runs[:3],[('warmup',0,i) for i in ids])
  for a,b in [('H','F'),('H','R'),('F','R')]:
   before=0
   for round_ in range(1,5):
    order=[i for phase,r,i in runs if phase=='timed' and r==round_]
    self.assertCountEqual(order,ids)
    before+=order.index(a)<order.index(b)
   self.assertEqual(before,2)
 def test_warmups_are_excluded_and_counts_equal(self):
  runs=runner.balanced_schedule(['H','F'])
  for engine in ['H','F']:
   self.assertEqual(sum(p=='timed' and e==engine for p,_,e in runs),4)
   self.assertEqual(sum(p=='warmup' and e==engine for p,_,e in runs),1)

class FrozenQualityGate(unittest.TestCase):
 def test_failed_receipt_cannot_be_promoted_by_config_flag(self):
  with tempfile.TemporaryDirectory() as directory:
   path=pathlib.Path(directory)/'quality.json'
   path.write_text(json.dumps({'passed':False,'quality':{'status':'evaluated'}}))
   engine={'screen_quality_passed':True,'screen_quality':str(path),'screen_quality_sha256':runner.sha(path)}
   with self.assertRaisesRegex(ValueError,'did not pass'): runner.validate_screen(engine)
 def test_changed_executable_fails_before_timing(self):
  with tempfile.TemporaryDirectory() as directory:
   path=pathlib.Path(directory)/'quality.json';binary=pathlib.Path(directory)/'binary'
   path.write_text(json.dumps({'passed':True,'quality':{'status':'evaluated'}}));binary.write_bytes(b'original')
   engine={'screen_quality_passed':True,'screen_quality':str(path),'screen_quality_sha256':runner.sha(path),'file_bindings':[{'path':str(binary),'sha256':runner.sha(binary)}]}
   runner.validate_screen(engine);binary.write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'binding changed'): runner.validate_screen(engine)

class SceneContract(unittest.TestCase):
 def config(self,scene):
  return {'scene':scene,'lane':'hardware-product-pipeline','engines':[{'id':i,'command':['render','{output}'],'source_pin':'pin','backend':'Metal','codec':'VT'} for i in ['H','F']]}
 def test_circle_requires_exact_dimensions_and_source_start(self):
  scene={'width':3840,'height':2160,'frames':300,'fps':30,'name':'Circles99kText1k','source_start':3}
  self.assertEqual(runner.validate_config(self.config(scene)),['H','F'])
  for wrong in [dict(scene,source_start=0),dict(scene,width=1920),dict(scene,name='TextGrid')]:
   with self.assertRaisesRegex(AssertionError,'Fixture mismatch'): runner.validate_config(self.config(wrong))

class CommonLaneContract(unittest.TestCase):
 def config(self):
  scene={'width':3840,'height':2160,'frames':300,'fps':30,'name':'Circles99kText1k','source_start':3}
  encoder={'codec':'required-videotoolbox-h264','color':'srgb-bt709-limited-nv12','pool':3,'gop':30,'bitrate':500000000}
  c=SceneContract().config(scene);c.update(lane='hardware-common-converter-adapter',shared_encoder=encoder)
  for e in c['engines']: e.update(encoding=dict(encoder),serial_rasterizer=True)
  return c
 def test_common_lane_cannot_hide_different_encoder_settings(self):
  self.assertEqual(runner.validate_config(self.config()),['H','F'])
  for field,wrong in [('bitrate',8000000),('gop',90),('color','bt601'),('pool',1)]:
   c=self.config();c['engines'][1]['encoding'][field]=wrong
   with self.assertRaisesRegex(AssertionError,'match settings'):runner.validate_config(c)
 def test_common_lane_rejects_parallel_raster_policy(self):
  c=self.config();c['engines'][1]['serial_rasterizer']=False
  with self.assertRaisesRegex(AssertionError,'serial policy'):runner.validate_config(c)

if __name__=='__main__': unittest.main()
