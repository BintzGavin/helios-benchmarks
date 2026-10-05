import functools, http.server, json, os, pathlib, subprocess, threading
root=pathlib.Path(__file__).resolve().parent.parent
prep=root/'preparation/unpacked/helios-gpu-comparison-prep'
receipts=root/'checkpoint'
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(prep)))
threading.Thread(target=server.serve_forever,daemon=True).start()
argv=['node',str(prep/'render_helios.mjs'),str(root/'sources/helios/packages/renderer/dist/index.js'),f'http://127.0.0.1:{server.server_port}/textgrid.html',str(receipts/'helios-smoke-3frames.mp4'),'medium','libx264']
env=dict(os.environ,SMOKE_FRAMES='3',CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',GPU_RECEIPT=str(receipts/'helios-smoke-runtime.json'),HELIOS_SKIP_BROWSER_DOWNLOAD='1')
try:
    result=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=50)
    receipt={'argv':argv,'environment':{k:env[k] for k in ['SMOKE_FRAMES','CHROME','GPU_RECEIPT','HELIOS_SKIP_BROWSER_DOWNLOAD']},'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'benchmark_timing':False}
except subprocess.TimeoutExpired as e: receipt={'argv':argv,'error':str(e),'benchmark_timing':False}
finally: server.shutdown();server.server_close()
(receipts/'helios-smoke-process.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
