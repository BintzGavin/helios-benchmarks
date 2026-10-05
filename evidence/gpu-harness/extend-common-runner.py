from pathlib import Path
p=Path('preparation/unpacked/helios-gpu-comparison-prep/run_matrix.py');s=p.read_text()
s=s.replace("'circles-adapter','ffmpeg'","'circles-adapter','circles-common-gpu-adapter','ffmpeg'")
s=s.replace("['gpu-raster-software-x264','hardware-product-pipeline']","['gpu-raster-software-x264','hardware-product-pipeline','hardware-common-converter-adapter']")
s=s.replace("    return ids\n\ndef validate_screen",'''    if config['lane']=='hardware-common-converter-adapter':
        shared=config.get('shared_encoder',{})
        assert shared.get('codec')=='required-videotoolbox-h264' and shared.get('color')=='srgb-bt709-limited-nv12', 'Matched hardware/color contract required'
        assert shared.get('pool')==3 and shared.get('gop')==30, 'Matched pool/GOP required'
        assert isinstance(shared.get('bitrate'),int) and 100000<=shared['bitrate']<=1000000000, 'Matched bitrate required'
        for e in config['engines']:
            assert e.get('encoding')==shared and e.get('serial_rasterizer') is True, 'Common converter lane must match settings and serial policy'
    return ids

def validate_screen''')
s=s.replace("if config['lane']=='hardware-product-pipeline' and", "if config['lane'] in ['hardware-product-pipeline','hardware-common-converter-adapter'] and")
p.write_text(s)
p=Path('checkpoint/test_comparison_schedule.py');s=p.read_text();i=s.index("if __name__")
s=s[:i]+'''class CommonLaneContract(unittest.TestCase):
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

'''+s[i:];p.write_text(s)
