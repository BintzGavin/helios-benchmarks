import hashlib,importlib.util,json,os,pathlib,subprocess,sys,time,zlib
root=pathlib.Path(__file__).resolve().parent.parent
evidence=root/'comparison/fframes-concurrent-nv12-20261004'
lane=sys.argv[1];assert lane in ('smoke3-02','controls36','circles300')
out=evidence/lane;env={**os.environ,'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'}
ffmpeg='/opt/homebrew/bin/ffmpeg';ffprobe='/opt/homebrew/bin/ffprobe'
spec=importlib.util.spec_from_file_location('audit',root/'checkpoint/audit-concurrent-nv12.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
binding=audit.audit(out/'capture',lane!='circles300');cfg=binding['configuration'];n=cfg['frames'];w=cfg['width'];h=cfg['height']
(out/'capture/independent-handoff-audit.json').write_text(json.dumps(binding,indent=2)+'\n')
reference=out/'reference-direct-nv12-02.mkv';candidate=out/'video-center.mp4';assert not reference.exists() and candidate.exists()
csp=importlib.util.spec_from_file_location('conform',root/'checkpoint/conform-nv12-chroma.py')
cm=importlib.util.module_from_spec(csp);csp.loader.exec_module(cm)
conformance=json.loads((out/'CHROMA-CONFORMANCE.json').read_text())
assert conformance['allVCLPayloadsExactlyEqual'] and conformance['allDecodedFrameBytesExactlyEqual']
assert conformance['originalVideoSha256']==audit.sha(out/'video.mp4') and conformance['normalizedVideoSha256']==audit.sha(candidate)
def decode_md5(path,label):
    cmd=[ffmpeg,'-v','error','-xerror','-i',str(path),'-map','0:v:0','-threads','1','-c:v','rawvideo','-pix_fmt','yuv420p','-f','framemd5',str(out/(label+'.framemd5'))]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=600);(out/(label+'.stderr.log')).write_text(r.stderr);assert r.returncode==0 and not r.stderr
    rows=[s.rsplit(',',1)[-1].strip() for s in (out/(label+'.framemd5')).read_text().splitlines() if s and not s.startswith('#')]
    assert len(rows)==n;return rows,cmd
# NV12 is split to planar420 by pure indexing. No matrix/range/transfer/sampling arithmetic.
argv=[ffmpeg,'-v','error','-xerror','-f','rawvideo','-pix_fmt','yuv420p','-s',f'{w}x{h}','-r','30',
      '-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
      '-chroma_sample_location','center','-i','pipe:0','-c:v','ffv1','-level','3','-threads','2',
      '-pix_fmt','yuv420p','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
      '-chroma_sample_location','center','-frames:v',str(n),str(reference)]
direct=[]
with (out/'reference-02.stderr.log').open('w') as err:
    p=subprocess.Popen(argv,env=env,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=err)
    try:
        for item in binding['frames']:
            raw=zlib.decompress((out/'capture'/f"{item['index']:06}.nv12.zlib").read_bytes());assert hashlib.sha256(raw).hexdigest()==item['rawSha256']
            plane=raw[:w*h]+raw[w*h::2]+raw[w*h+1::2];assert len(plane)==w*h*3//2
            direct.append({'index':item['index'],'sourceIndex':item['sourceIndex'],'rawNV12Sha256':item['rawSha256'],'planarMd5':hashlib.md5(plane).hexdigest()})
            p.stdin.write(plane)
        p.stdin.close();rc=p.wait(timeout=600)
    except BaseException:p.kill();p.wait();raise
assert rc==0
decoded,decode_command=decode_md5(reference,'reference-direct-02');assert [r['planarMd5'] for r in direct]==decoded
for r,md5 in zip(direct,decoded):r.update(decodedMd5=md5,equal=True)
(out/'DIRECT-NV12-REFERENCE-BINDING.json').write_text(json.dumps({'passed':True,'frames':n,'pairs':direct,
    'sourceReadbackBytes':w*h*3//2*n,'noColorArithmetic':True,'originalEncoderInputNV12':True,
    'referenceSha256':audit.sha(reference),'referenceCommand':argv,'returncode':rc,'decodeCommand':decode_command,
    'benchmarkTiming':False,'opaqueEncoderDriverCopiesUnknown':True,'zeroCopyProved':False},indent=2)+'\n')
validator=root/'preparation/unpacked/helios-gpu-comparison-prep/validate_video.py'
args=['/opt/homebrew/bin/python3',str(validator),str(candidate),'--reference',str(reference),
      '--engine','F-modified-concurrent-NV12','--reference-engine','F-modified-concurrent-NV12',
      '--scene','Circles99kText1k' if lane=='circles300' else 'predeterminedNV12controls',
      '--width',str(w),'--height',str(h),'--frames',str(n),'--fps','30/1','--ssim-y','.995','--psnr-y','40','--psnr-uv','35',
      '--ffmpeg',ffmpeg,'--ffprobe',ffprobe,'--output',str(out/'quality.json')]
with (out/'quality-process.log').open('w') as log:r=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
probe=[ffprobe,'-v','error','-select_streams','v:0','-show_frames','-show_streams','-of','json',str(candidate)]
p=subprocess.run(probe,capture_output=True,text=True,timeout=600);assert p.returncode==0
(out/'decoded-frames.json').write_text(p.stdout)
(out/'quality-process.json').write_text(json.dumps({'argv':args,'returncode':r.returncode,'probeCommand':probe,'probeReturncode':p.returncode,'benchmarkTiming':False},indent=2)+'\n')
quality=json.loads((out/'quality.json').read_text())
print(json.dumps({'lane':lane,'directNV12ReferenceBindingPassed':True,'parameterSetConformancePixelAndVCLEqualityPassed':True,
    'qualityPassed':quality['quality_passed'],'structurePassed':quality['structure_decode_passed'],
    'ssim':quality['quality'].get('ssim',{}).get('minimum'),'psnr':quality['quality'].get('psnr',{}).get('minimum')}))
sys.exit(not quality['passed'])
