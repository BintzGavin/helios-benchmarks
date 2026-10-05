import unittest
from run_matrix import schedule,validate_config

class RunnerTests(unittest.TestCase):
    def test_rotation(self):
        runs=schedule(['H','F','R'])
        self.assertEqual(len(runs),12)
        self.assertEqual([r[2] for r in runs[3:]],list('HFRFRHRHF'))
        self.assertEqual([r[0] for r in runs[:3]],['warmup']*3)
    def test_bad_scene_rejected(self):
        with self.assertRaises(AssertionError):validate_config({'scene':{}})
    def test_empty_command_rejected(self):
        c={'scene':{'width':1920,'height':1080,'frames':300,'fps':30,'name':'TextGrid'},'lane':'gpu-raster-software-x264','engines':[{'id':'H','command':[]},{'id':'F','command':[]}]}
        with self.assertRaises(AssertionError):validate_config(c)

if __name__=='__main__':unittest.main()
