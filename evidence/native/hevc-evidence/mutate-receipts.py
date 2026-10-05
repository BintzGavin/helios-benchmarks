import json, subprocess, hashlib
from pathlib import Path
root = Path('/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94/hevc-evidence')
worktree = Path('/Users/gavinbintz/.codex/worktrees/gpu-hevc/helios')
source = worktree / 'packages/portable/src/gpu.ts'
original = source.read_text()
directory = root / 'mutations'; directory.mkdir(exist_ok=True)
command = ['/opt/homebrew/bin/node', 'node_modules/vitest/vitest.mjs', 'run', '--no-file-parallelism', 'packages/portable/tests/gpu-hevc.test.ts', '-t', 'receipts']
def execute(name):
    with (directory / (name + '.log')).open('wb') as out:
        return subprocess.run(command, cwd=worktree, stdout=out, stderr=subprocess.STDOUT, timeout=30).returncode
assert execute('baseline') == 0
changes = [
    ('probe-codec', "result.codec !== 'hevc' || ", ''),
    ('probe-protocol', 'result.protocol !== 6 || ', ''),
    ('probe-hardware-used', ' || result.hardwareUsed !== true', ''),
    ('completion-codec', "(result.codec ?? 'h264') !== codec || ", ''),
    ('completion-hardware', " || (codec === 'hevc' && (result.hardwareRequired !== true || result.hardwareUsed !== true))", ''),
]
results = []
try:
    for name, old, new in changes:
        assert old in original
        source.write_text(original.replace(old, new, 1))
        code = execute(name)
        log = (directory / (name + '.log')).read_text()
        assert code == 1 and 'AssertionError' in log and 'failed' in log, name + ' survived or failed without assertion'
        results.append({'mutation': name, 'exit': code, 'caughtByAssertion': True})
finally:
    source.write_text(original)
assert hashlib.sha256(source.read_bytes()).hexdigest() == hashlib.sha256(original.encode()).hexdigest()
assert execute('restored') == 0
(directory / 'REPORT.json').write_text(json.dumps({'passingBaseline': True, 'mutants': results, 'restoredSourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'restoredTestsPassed': True, 'scope': 'HEVC capability/completion codec, protocol and hardware guards; native format and initialization checked separately with real fault interposers'}, indent=2))
print(json.dumps({'killed': len(results), 'survived': 0, 'passingBaselineAndRestored': True}))
