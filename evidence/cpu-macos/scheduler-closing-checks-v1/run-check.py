from pathlib import Path
import json, subprocess, sys, re, time
receipt = Path(__file__).parent
command = sys.argv[2:]
started = time.time()
result = subprocess.run(command, cwd='/private/tmp/helios-scheduler-merge-20261001', text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
def sanitized(text):
    text = re.sub(r'(https?://)[^\s/@]+:[^\s/@]+@', r'\1[REDACTED]@', text)
    text = re.sub(r'(?i)(authorization\s*[:=]\s*|bearer\s+|(?:token|password|api[_-]?key)\s*[:=]\s*)[^\s,;]+', r'\1[REDACTED]', text)
    return text
(receipt / (sys.argv[1] + '.stdout.log')).write_text(sanitized(result.stdout))
(receipt / (sys.argv[1] + '.stderr.log')).write_text(sanitized(result.stderr))
record = {'command': command, 'cwd': '/private/tmp/helios-scheduler-merge-20261001', 'exit_code': result.returncode, 'duration_seconds': round(time.time() - started, 3)}
(receipt / (sys.argv[1] + '.json')).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
print(sanitized(result.stdout)[-4500:])
print(sanitized(result.stderr)[-4500:])
sys.exit(result.returncode)
