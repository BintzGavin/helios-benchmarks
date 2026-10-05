import functools, http.server, json, pathlib, subprocess, sys, threading

root = pathlib.Path(__file__).resolve().parent.parent
prep = root / 'preparation/unpacked/helios-gpu-comparison-prep'
receipts = root / 'checkpoint'
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(prep)))
threading.Thread(target=server.serve_forever, daemon=True).start()
argv = ['node', str(prep / 'browser_probe.mjs'), '/Users/gavinbintz/Developer/helios/node_modules/playwright-core/index.mjs', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', str(receipts / 'browser-host.json'), f'http://127.0.0.1:{server.server_port}/textgrid.html']
try:
    result = subprocess.run(argv, capture_output=True, text=True, timeout=45)
    receipt = {'argv': argv, 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'kind': 'capability-smoke-only', 'benchmark_timing': False}
except subprocess.TimeoutExpired as e:
    receipt = {'argv': argv, 'error': str(e), 'benchmark_timing': False}
finally:
    server.shutdown()
    server.server_close()
(receipts / 'browser-smoke-process.json').write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt))
