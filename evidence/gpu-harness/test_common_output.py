import importlib.util,pathlib,unittest,copy
spec=importlib.util.spec_from_file_location('gate',pathlib.Path(__file__).with_name('check-common-output.py'));gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
class OutputGate(unittest.TestCase):
 def fixture(self):
  probe={'streams':[{'pix_fmt':'yuv420p','color_range':'tv','color_space':'bt709','color_transfer':'bt709','color_primaries':'bt709'}],'frames':[{'key_frame':int(i%30==0)} for i in range(31)]}
  events=[{'event':'surface-create','protocol':4,'bitrate':500000000,'configuredBitrate':500000000,'gop':30,'poolCapacity':3,'format':'nv12-video-range','rawCpuMapCallsInBridge':0}]
  for i in range(31):
   for event in ['raster-submitted','conversion-complete','encoder-submit','encoder-callback']:events.append({'event':event,'frame':i,'surfaceId':i%3,'sameIOSurfacePlanes':True,'status':0,'dropped':False})
  events.append({'event':'encoder-finish','frames':31,'allCallbacksComplete':True});return probe,events
 def test_accepts_valid_decoded_and_transfer_contract(self):
  p,e=self.fixture();self.assertTrue(gate.inspect(p,e,500000000,31)['passed'])
 def test_rejects_silent_configuration_change(self):
  p,e=self.fixture();e[0]['configuredBitrate']=8000000;self.assertFalse(gate.inspect(p,e,500000000,31)['passed'])
 def test_rejects_missing_callback_and_conversion_order(self):
  for change in ['missing','order','drop']:
   p,e=self.fixture()
   if change=='missing':e.pop(4)
   if change=='order':e[2],e[3]=e[3],e[2]
   if change=='drop':e[4]['dropped']=True
   self.assertFalse(gate.inspect(p,e,500000000,31)['passed'])
 def test_rejects_decoded_gop_or_color_mismatch(self):
  p,e=self.fixture();p['frames'][30]['key_frame']=0;self.assertFalse(gate.inspect(p,e,500000000,31)['passed'])
  p,e=self.fixture();p['streams'][0]['color_space']='smpte170m';self.assertFalse(gate.inspect(p,e,500000000,31)['passed'])
if __name__=='__main__':unittest.main()
