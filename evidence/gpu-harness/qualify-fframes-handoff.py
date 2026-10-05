"""Build fixed BT.601 proxy from same-stream captured BGRA, bind decoded reference bytes.
This proxy does NOT observe VideoToolbox's opaque pre-compression NV12 conversion.
"""
import hashlib, importlib.util, json, os, pathlib, subprocess, sys, time, zlib
root = pathlib.Path(__file__).resolve().parent.parent
evidence = root/'comparison/fframes-original-handoff-20261004'
lane = sys.argv[1]
assert lane in ('controls', 'circles300')
out = evidence/lane
spec = importlib.util.spec_from_file_location('audit',root/'checkpoint/audit-fframes-handoff.py')
audit = importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
binding = audit.audit(out/'capture',lane=='controls')
(out/'capture/independent-handoff-audit.json').write_text(json.dumps(binding,indent=2)+'\n')
cfg = binding['configuration'];n=cfg['frames'];w=cfg['width'];h=cfg['height']
env = {**os.environ,'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'}
ffmpeg='/opt/homebrew/bin/ffmpeg';ffprobe='/opt/homebrew/bin/ffprobe'
reference=out/'reference-same-stream-bt601-proxy.mkv'
assert not reference.exists()
conversion='scale=out_color_matrix=bt601:out_range=tv,format=yuv420p'
graph=f'[0:v]{conversion},split=2[ref][hash]'
argv=[ffmpeg,'-hide_banner','-nostdin','-loglevel','error','-xerror','-filter_complex_threads','1',
      '-f','rawvideo','-pix_fmt','bgra','-s',f'{w}x{h}','-r','30','-i','pipe:0',
      '-filter_complex',graph,'-map','[ref]','-c:v','ffv1','-level','3','-threads','2',
      '-colorspace','smpte170m','-color_range','tv','-frames:v',str(n),str(reference),
      '-map','[hash]','-c:v','rawvideo','-threads','1','-pix_fmt','yuv420p','-frames:v',str(n),
      '-f','framemd5',str(out/'proxy-direct.framemd5')]
receipt={'benchmarkTiming':False,'source':'exact same-stream BGRA; fixed original reference BT601 conversion',
         'opaqueEncoderNV12OracleProved':False,'conversion':conversion,'argv':argv,'startedUnix':time.time(),
         'captureLedgerSha256':binding['ledgerSha256'],'sourceRawBytes':0,'sourceFrames':[]}
with (out/'reference-process.stderr.log').open('w') as err:
    p=subprocess.Popen(argv,env=env,cwd=out,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=err)
    try:
        for item in binding['frames']:
            raw=zlib.decompress((out/'capture'/f"{item['index']:06}.bgra.zlib").read_bytes())
            assert hashlib.sha256(raw).hexdigest()==item['rawSha256']
            p.stdin.write(raw)
            receipt['sourceRawBytes']+=len(raw);receipt['sourceFrames'].append(item['sourceIndex'])
        p.stdin.close();receipt['returncode']=p.wait(timeout=600)
    except BaseException:
        p.kill();p.wait();raise
assert receipt['returncode']==0
decode=[ffmpeg,'-v','error','-xerror','-i',str(reference),'-map','0:v:0','-c:v','rawvideo','-threads','1',
        '-pix_fmt','yuv420p','-f','framemd5',str(out/'proxy-decoded.framemd5')]
r=subprocess.run(decode,env=env,capture_output=True,text=True,timeout=600)
(out/'reference-binding-decode.stderr.log').write_text(r.stderr)
assert r.returncode==0
def hashes(path):return [s.rsplit(',',1)[-1].strip() for s in path.read_text().splitlines() if s and not s.startswith('#')]
a=hashes(out/'proxy-direct.framemd5');b=hashes(out/'proxy-decoded.framemd5')
assert len(a)==len(b)==n and a==b
receipt.update(finishedUnix=time.time(),referenceSha256=audit.sha(reference),referenceBytes=reference.stat().st_size,
               directDecodedPairs=[{'index':i,'direct':x,'decoded':y,'equal':x==y} for i,(x,y) in enumerate(zip(a,b))],
               allProxyReferenceFramesExactlyBound=True,decodeCommand=decode,decodeReturncode=r.returncode)
(out/'reference-binding.json').write_text(json.dumps(receipt,indent=2)+'\n')
validator=root/'preparation/unpacked/helios-gpu-comparison-prep/validate_video.py'
args=['/opt/homebrew/bin/python3',str(validator),str(out/'video.mp4'),'--reference',str(reference),
      '--engine','F-original-MaxPerformance','--reference-engine','F-original-MaxPerformance',
      '--scene','predetermined-color-chroma' if lane=='controls' else 'Circles99kText1k',
      '--width',str(w),'--height',str(h),'--frames',str(n),'--fps','30/1',
      '--ssim-y','0.995','--psnr-y','40','--psnr-uv','35','--ffmpeg',ffmpeg,'--ffprobe',ffprobe,
      '--output',str(out/'quality.json')]
with (out/'quality-process.log').open('w') as log:q=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
probe=[ffprobe,'-v','error','-select_streams','v:0','-show_frames','-show_streams','-of','json',str(out/'video.mp4')]
v=subprocess.run(probe,env=env,capture_output=True,text=True,timeout=600)
assert v.returncode==0
(out/'decoded-frames.json').write_text(v.stdout)
(out/'quality-process.json').write_text(json.dumps({'benchmarkTiming':False,'argv':args,'returncode':q.returncode,
    'decodedFramesCommand':probe,'decodedFramesReturncode':v.returncode,'opaqueEncoderNV12OracleProved':False},indent=2)+'\n')
quality=json.loads((out/'quality.json').read_text())
print(json.dumps({'lane':lane,'referenceBindingPassed':True,'structurePassed':quality['structure_decode_passed'],
                  'qualityPassed':quality['quality_passed'],'quality':quality.get('quality'),'benchmarkTiming':False}))
