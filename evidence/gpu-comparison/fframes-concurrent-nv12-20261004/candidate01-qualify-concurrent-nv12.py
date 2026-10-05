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
reference=out/'reference-direct-nv12.mkv';candidate=out/'video-center.mp4';assert not reference.exists() and not candidate.exists()
normalize=[ffmpeg,'-v','error','-xerror','-i',str(out/'video.mp4'),'-map','0:v:0','-an','-c:v','copy',
           '-bsf:v','h264_metadata=chroma_sample_loc_type=1','-movflags','+faststart',str(candidate)]
start=time.time();result=subprocess.run(normalize,env=env,capture_output=True,text=True,timeout=600)
(out/'conformance.stderr.log').write_text(result.stderr);assert result.returncode==0 and not result.stderr
conformance={'command':normalize,'returncode':result.returncode,'benchmarkTiming':False,
             'originalVideoSha256':audit.sha(out/'video.mp4'),'normalizedVideoSha256':audit.sha(candidate),
             'reason':'Signal actual centered 2x2 box samples; VT retained left despite requested center attachment.',
             'requiredExportStage':True,'futureExportTimesMustIncludeThisStage':True,'startedUnix':start,'finishedUnix':time.time()}
# Direct AVCC sample payloads from ffprobe-demuxed byte offsets, without re-encoding.
def vcl(path):
    cmd=[ffprobe,'-v','error','-select_streams','v:0','-show_packets','-show_streams',
         '-show_entries','packet=pos,size,pts,duration:stream=nal_length_size,is_avc','-of','json',str(path)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=600);assert p.returncode==0
    doc=json.loads(p.stdout);assert doc['streams'][0]['is_avc']=='true' and doc['streams'][0]['nal_length_size']=='4'
    payloads=[]
    with path.open('rb') as f:
        for packet in doc['packets']:
            f.seek(int(packet['pos']));data=f.read(int(packet['size']));offset=0
            while offset<len(data):
                assert offset+4<=len(data);size=int.from_bytes(data[offset:offset+4],'big');offset+=4
                assert 0<size<=len(data)-offset;nal=data[offset:offset+size];offset+=size
                if 1<=nal[0]&31<=5:payloads.append({'nalType':nal[0]&31,'bytes':len(nal),'sha256':hashlib.sha256(nal).hexdigest()})
            assert offset==len(data)
    assert payloads
    return payloads,cmd
a,ac=vcl(out/'video.mp4');b,bc=vcl(candidate);assert a==b
conformance.update(allVCLPayloadsExactlyEqual=True,vclPayloads=a,originalPacketCommand=ac,normalizedPacketCommand=bc)
def decode_md5(path,label):
    cmd=[ffmpeg,'-v','error','-xerror','-i',str(path),'-map','0:v:0','-threads','1','-c:v','rawvideo','-pix_fmt','yuv420p','-f','framemd5',str(out/(label+'.framemd5'))]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=600);(out/(label+'.stderr.log')).write_text(r.stderr);assert r.returncode==0 and not r.stderr
    rows=[s.rsplit(',',1)[-1].strip() for s in (out/(label+'.framemd5')).read_text().splitlines() if s and not s.startswith('#')]
    assert len(rows)==n;return rows,cmd
before,before_cmd=decode_md5(out/'video.mp4','candidate-original');after,after_cmd=decode_md5(candidate,'candidate-center');assert before==after
conformance.update(allDecodedFrameBytesExactlyEqual=True,decodedPairs=[{'index':i,'original':x,'normalized':y} for i,(x,y) in enumerate(zip(before,after))],originalDecode=before_cmd,normalizedDecode=after_cmd)
(out/'CHROMA-CONFORMANCE.json').write_text(json.dumps(conformance,indent=2)+'\n')
# NV12 is split to planar420 by pure indexing. No matrix/range/transfer/sampling arithmetic.
argv=[ffmpeg,'-v','error','-xerror','-f','rawvideo','-pix_fmt','yuv420p','-s',f'{w}x{h}','-r','30',
      '-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
      '-chroma_sample_location','center','-i','pipe:0','-c:v','ffv1','-level','3','-threads','2',
      '-pix_fmt','yuv420p','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
      '-chroma_sample_location','center','-frames:v',str(n),str(reference)]
direct=[]
with (out/'reference.stderr.log').open('w') as err:
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
decoded,decode_command=decode_md5(reference,'reference-direct');assert [r['planarMd5'] for r in direct]==decoded
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
