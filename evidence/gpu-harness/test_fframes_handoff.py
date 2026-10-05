import copy, importlib.util, json, pathlib, unittest
path = pathlib.Path(__file__).with_name('audit-fframes-handoff.py')
spec = importlib.util.spec_from_file_location('audit', path)
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
rows = [json.loads(s) for s in (path.parent.parent/'comparison/fframes-original-handoff-20261004/controls/capture/handoff.jsonl').read_text().splitlines()]


class HandoffMutations(unittest.TestCase):
    def test_actual_hardware_control_baseline(self):
        result = audit.audit(path.parent.parent/'comparison/fframes-original-handoff-20261004/controls/capture', True)
        self.assertTrue(result['passed'])

    def check_mutant(self, event, change):
        mutant = copy.deepcopy(rows)
        row = next(r for r in mutant if r['event'] == event)
        change(row)
        with self.assertRaises(AssertionError): audit.audit_ledger(mutant)

    def test_wrong_source_frame(self): self.check_mutant('gpu-complete', lambda r: r.update(sourceIndex=302))
    def test_wrong_segment(self): self.check_mutant('encoder-send-begin', lambda r: r.update(segment=99))
    def test_wrong_buffer(self): self.check_mutant('capture-complete', lambda r: r.update(pixelBuffer=1))
    def test_wrong_pts(self): self.check_mutant('encoder-send-begin', lambda r: r.update(pts=99))
    def test_changed_concurrency(self): self.check_mutant('pipeline', lambda r: r.update(gpuContexts=1))
    def test_not_actual_fence(self): self.check_mutant('gpu-complete', lambda r: r.update(fence='queued only'))
    def test_missing_release(self): self.check_mutant('avbuffer-final-reference-release', lambda r: r.update(event='missing'))
    def test_missing_worker(self): self.check_mutant('worker-start', lambda r: r.update(event='missing'))
    def test_missing_drain(self):
        mutant = copy.deepcopy(rows)
        for r in mutant:
            if r['event'] == 'encoder-drained': r['event'] = 'missing'
        with self.assertRaises(AssertionError): audit.audit_ledger(mutant)
    def test_send_before_gpu_completion(self):
        mutant = copy.deepcopy(rows)
        complete = next(r for r in mutant if r['event']=='gpu-complete')
        capture = next(r for r in mutant if r['event']=='capture-begin' and r['index']==complete['index'])
        a,b = mutant.index(complete),mutant.index(capture)
        mutant[a],mutant[b] = mutant[b],mutant[a]
        for i,r in enumerate(mutant,1):r['seq']=i
        with self.assertRaises(AssertionError): audit.audit_ledger(mutant)


if __name__=='__main__': unittest.main()
