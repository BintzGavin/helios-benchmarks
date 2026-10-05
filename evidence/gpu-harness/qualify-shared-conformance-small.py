import pathlib,json,shutil,importlib.util,sys,subprocess
root=pathlib.Path(__file__).resolve().parent.parent;r=root/'comparison/native-conformance-prep-20261005/final-v3';out=r/'modified-F-controls36-local-fixtures';out.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('c',root/'checkpoint/native_chroma_conformance.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
old=r.parent/'fixtures/modified-F-controls36';src=out/'original.mp4';shutil.copy2(old/'video.mp4',src);result=m.conform(src,out/'center.mp4','h264');result['adapterSha256']=m.sha(root/'checkpoint/native_chroma_conformance.py')
for key in ['sourceTrace','destinationTrace']:(out/(key+'.log')).write_text(result.pop(key))
(out/'CONFORMANCE.json').write_text(json.dumps(result,indent=2)+'\n')
argv=['/opt/homebrew/bin/python3',str(root/'preparation/unpacked/helios-gpu-comparison-prep/validate_video.py'),str(out/'center.mp4'),'--reference',str(old/'reference-direct-nv12.mkv'),'--engine','modified-F-controls36-shared-conformance','--reference-engine','modified-F-controls36-shared-conformance','--scene','predeterminedNV12controls','--width','256','--height','128','--frames','36','--fps','30/1','--ssim-y','.995','--psnr-y','40','--psnr-uv','35','--ffmpeg','/opt/homebrew/bin/ffmpeg','--ffprobe','/opt/homebrew/bin/ffprobe','--output',str(out/'quality.json')]
with (out/'quality-process.stdout.log').open('w') as stdout,(out/'quality-process.stderr.log').open('w') as stderr:p=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=120)
assert p.returncode==0
rows=[]
for path,name in [(src,'original'),(out/'center.mp4','center')]:
 cmd=['/opt/homebrew/bin/ffmpeg','-v','error','-xerror','-i',str(path),'-pix_fmt','yuv420p','-fps_mode','passthrough','-f','framemd5','-'];p=subprocess.run(cmd,capture_output=True,text=True,timeout=60);assert p.returncode==0 and not p.stderr;(out/(name+'.framemd5')).write_text(p.stdout);rows.append([l for l in p.stdout.splitlines() if l and not l.startswith('#')])
assert rows[0]==rows[1] and len(rows[0])==36
(out/'QUALIFICATION.json').write_text(json.dumps({'passed':True,'frames':36,'preparationOnly':True,'sameFrozenAdapterForHAndModifiedF':True,'everyDecodedFrameRowEqual':True,'qualityProcess':{'argv':argv,'returncode':0},'sourceReferenceSha256':m.sha(old/'reference-direct-nv12.mkv'),'originalProduct':False,'benchmarkTiming':False,'no4KQualification':True},indent=2)+'\n');print('Shared adapter modified-F36 preparation passes')
