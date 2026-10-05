import pathlib,json,hashlib,importlib.util,sys,shutil,subprocess
root=pathlib.Path(__file__).resolve().parent.parent;r=root/'comparison/native-conformance-prep-20261005';out=r/'final-v3';out.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('conform',root/'checkpoint/native_chroma_conformance.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
for codec in ['h264','hevc']:
 src=out/('original-'+codec+'.mp4');shutil.copy2(r/('original-'+codec+'.mp4'),src);dest=out/('center-'+codec+'.mp4');result=m.conform(src,dest,codec)
 result['adapterSha256']=m.sha(root/'checkpoint/native_chroma_conformance.py')
 for name,key in [('source-SPS-trace','sourceTrace'),('center-SPS-trace','destinationTrace')]: (out/(codec+'-'+name+'.log')).write_text(result.pop(key))
 (out/(codec+'-CONFORMANCE.json')).write_text(json.dumps(result,indent=2)+'\n');assert m.sha(dest)==m.sha(r/('center-'+codec+'.mp4'))
for script in ['validate-native-conformance-prep.py','test_native_chroma_conformance.py']:
 with (out/(script+'.stdout.log')).open('w') as stdout,(out/(script+'.stderr.log')).open('w') as stderr:
  p=subprocess.run(['/opt/homebrew/bin/python3',str(root/'checkpoint'/script)],stdout=stdout,stderr=stderr,timeout=60)
 assert p.returncode==0,script
validator=root/'preparation/unpacked/helios-gpu-comparison-prep/validate_video.py';receipts=[]
for codec in ['h264','hevc']:
 argv=['/opt/homebrew/bin/python3',str(validator),str(out/('center-'+codec+'.mp4')),'--reference',str(out/'reference-centered-small.mkv'),'--engine','native-'+codec+'-center-small-prep','--reference-engine','native-'+codec+'-center-small-prep','--scene','retained-color-text-circle-small','--width','256','--height','128','--frames','300','--fps','30000/1001','--ssim-y','.995','--psnr-y','40','--psnr-uv','35','--ffmpeg','/opt/homebrew/bin/ffmpeg','--ffprobe','/opt/homebrew/bin/ffprobe','--output',str(out/(codec+'-quality.json'))]
 with (out/(codec+'-quality-process.stdout.log')).open('w') as stdout,(out/(codec+'-quality-process.stderr.log')).open('w') as stderr:p=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=120)
 assert p.returncode==0;receipts.append({'argv':argv,'returncode':p.returncode,'benchmarkTiming':False,'smallAdapterPreparationOnly':True})
 probe=['/opt/homebrew/bin/ffprobe','-v','error','-show_streams','-show_frames','-of','json',str(out/('center-'+codec+'.mp4'))];p=subprocess.run(probe,capture_output=True,text=True,timeout=60);assert p.returncode==0;(out/(codec+'-decoded-cadence-color.json')).write_text(p.stdout)
 from fractions import Fraction
 d=json.loads(p.stdout);st=d['streams'][0];frames=d['frames'];assert len(frames)==300
 for i,f in enumerate(frames):
  assert Fraction(f['pts'])*Fraction(st['time_base'])==Fraction(i*1001,30000)
  assert Fraction(f['duration'])*Fraction(st['time_base'])==Fraction(1001,30000)
  for k,v in {'width':256,'height':128,'color_range':'tv','color_space':'bt709','color_transfer':'bt709','color_primaries':'bt709','chroma_location':'center'}.items():assert f[k]==v
 keys=[i for i,f in enumerate(frames) if f['key_frame']];assert keys==list(range(0,300,30))
 q=json.loads((out/(codec+'-quality.json')).read_text());print(codec,q['passed'],q['quality']['ssim']['minimum'],q['quality']['psnr']['minimum'])
(out/'QUALITY-PROCESS-RECEIPTS.json').write_text(json.dumps(receipts,indent=2)+'\n')
print('Final adapter small-scene gates pass; no newGPU or4Kqualification/timings')
