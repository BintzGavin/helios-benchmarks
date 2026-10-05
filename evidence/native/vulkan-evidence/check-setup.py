import json
import pathlib
import subprocess

root = pathlib.Path(__file__).parent
result = subprocess.run([str(root / 'interop-probe'), str(root / 'probe.h264'), str(root / 'probe-trace.jsonl')], capture_output=True, text=True)
(root / 'probe.stderr').write_text(result.stderr)
(root / 'probe.stdout').write_text(result.stdout)
assert result.returncode == 0, result.stderr
receipt = json.loads(result.stdout)
assert receipt['deviceType'] in [1, 2], receipt
assert receipt['metalObjects'] and receipt['sameImportedTexture'] and receipt['hardwareUsed'], receipt
assert receipt['vulkanSubmissions'] == receipt['completedFences'] == receipt['encoderFrames'] == 3, receipt
assert receipt['zeroCopyProved'] is False
events = [json.loads(line) for line in (root / 'probe-trace.jsonl').read_text().splitlines()]
assert sum(e.get('event') == 'conversion-complete' for e in events) == 3
assert sum(e.get('event') == 'encoder-callback' for e in events) == 3
print(json.dumps({'setupAcceptance': 'passed', 'receipt': receipt}))
