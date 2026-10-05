"""Bounded restoration tests; no benchmark or native binary execution."""
import hashlib
import importlib.util
import io
import json
import pathlib
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('fetch', pathlib.Path(__file__).with_name('fetch_evidence.py'))
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)

def digest(data):
    return hashlib.sha256(data).hexdigest()

class RestorationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.repo = self.base / 'repo'
        (self.repo / 'data').mkdir(parents=True)
        self.output = self.base / 'restored'
        self.payload = b'exact original evidence\x00\xff'

    def run_fetch(self, rows, assets=None, response=None):
        (self.repo / 'data/evidence-catalog.json').write_text(json.dumps({'files':rows,'assets':assets or []}))
        with patch.object(fetch, 'ROOT', self.repo), patch('sys.argv', ['fetch','--match','study/','--directory',str(self.output)]), patch.object(fetch.urllib.request,'urlopen',return_value=io.BytesIO(response or b'')), patch('sys.stdout',new_callable=io.StringIO):
            fetch.main()

    def row(self, storage, name='study/original.bin'):
        return {'path':name,'kind':'file','bytes':len(self.payload),'sha256':digest(self.payload),'storage':storage}

    def asset(self, name, data):
        return {'name':name,'bytes':len(data),'sha256':digest(data),'url':'https://example.invalid/'+name}

    def test_git_bytes(self):
        (self.repo / 'receipt.bin').write_bytes(self.payload)
        self.run_fetch([self.row({'kind':'git','path':'receipt.bin'})])
        self.assertEqual((self.output / 'study/original.bin').read_bytes(),self.payload)

    def test_direct_asset(self):
        self.run_fetch([self.row({'kind':'release-asset','name':'object.bin'})],[self.asset('object.bin',self.payload)],self.payload)
        self.assertEqual((self.output / 'study/original.bin').read_bytes(),self.payload)

    def bundle(self, symlink=False):
        out = io.BytesIO()
        with tarfile.open(fileobj=out,mode='w:gz') as archive:
            info = tarfile.TarInfo('objects/'+digest(self.payload))
            if symlink:
                info.type=tarfile.SYMTYPE
                info.linkname='outside'
                archive.addfile(info)
            else:
                info.size=len(self.payload)
                archive.addfile(info,io.BytesIO(self.payload))
        return out.getvalue()

    def test_bundle_bytes(self):
        data=self.bundle()
        self.run_fetch([self.row({'kind':'release-bundle','name':'bundle.tar.gz','member':'objects/'+digest(self.payload)})],[self.asset('bundle.tar.gz',data)],data)
        self.assertEqual((self.output / 'study/original.bin').read_bytes(),self.payload)

    def test_corrupt_download_refused(self):
        with self.assertRaisesRegex(ValueError,'download mismatch'):
            self.run_fetch([self.row({'kind':'release-asset','name':'object.bin'})],[self.asset('object.bin',self.payload)],b'corrupt')
        self.assertFalse((self.output / 'study/original.bin').exists())

    def test_bundle_symlink_refused(self):
        data=self.bundle(symlink=True)
        with self.assertRaisesRegex(ValueError,'invalid object member'):
            self.run_fetch([self.row({'kind':'release-bundle','name':'bundle.tar.gz','member':'objects/'+digest(self.payload)})],[self.asset('bundle.tar.gz',data)],data)

    def test_destination_escape_refused(self):
        (self.repo / 'receipt.bin').write_bytes(self.payload)
        with self.assertRaisesRegex(ValueError,'unsafe evidence path'):
            self.run_fetch([self.row({'kind':'git','path':'receipt.bin'},'study/../../escape.bin')])
        self.assertFalse((self.base / 'escape.bin').exists())

    def test_git_source_escape_refused(self):
        (self.base / 'outside.bin').write_bytes(self.payload)
        with self.assertRaisesRegex(ValueError,'unsafe Git evidence source'):
            self.run_fetch([self.row({'kind':'git','path':'../outside.bin'})])

    def test_existing_output_refused(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError,'output directory must be new'):
            self.run_fetch([self.row({'kind':'git','path':'receipt.bin'})])

    def test_corrupt_git_receipt_refused(self):
        (self.repo / 'receipt.bin').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'restored identity mismatch'):
            self.run_fetch([self.row({'kind':'git','path':'receipt.bin'})])

if __name__ == '__main__':
    unittest.main()
