import importlib.util,pathlib,sys,tempfile,shutil,json,hashlib,subprocess
root=pathlib.Path(__file__).resolve().parent.parent;r=root/'comparison/native-conformance-prep-20261005/final-v3'
s=importlib.util.spec_from_file_location('nativeconform',root/'checkpoint/native_chroma_conformance.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);results=[]
with tempfile.TemporaryDirectory(prefix='native-chroma-atomic-',dir=root/'checkpoint') as dirname:
 t=pathlib.Path(dirname)
 for codec in ['h264','hevc']:
  source=t/(codec+'-source.mp4');shutil.copy2(r/('original-'+codec+'.mp4'),source);orig=m.sha(source)
  def test(name,call,dest,preserved=None):
   before=set(t.iterdir())
   try:call()
   except (m.Refused,FileExistsError,RuntimeError):pass
   else:raise AssertionError('accepted '+name)
   assert m.sha(source)==orig
   if preserved is not None:assert dest.read_bytes()==preserved
   else:assert not dest.exists()
   assert not [x for x in t.iterdir() if x.name.endswith('.candidate')]
   results.append({'codec':codec,'case':name,'rejected':True,'noTemporaryCandidateLeaked':True})
  dest=t/(codec+'-existing.mp4');dest.write_bytes(b'preserved destination');test('existing destination',lambda:m.conform(source,dest,codec),dest,b'preserved destination')
  target=t/(codec+'-symlink.mp4');target.symlink_to(source);test('symlink destination',lambda:m.conform(source,target,codec),target,source.read_bytes())
  dest=t/(codec+'-wrong.mp4');test('wrong codec',lambda:m.conform(source,dest,'h264' if codec=='hevc' else 'hevc'),dest)
  bad=t/(codec+'-truncated.mp4');bad.write_bytes(source.read_bytes()[:32]);dest=t/(codec+'-truncated-out.mp4');test('truncated input',lambda:m.conform(bad,dest,codec),dest)
  maxframes=m.MAX_FRAMES;m.MAX_FRAMES=1;dest=t/(codec+'-frame-cap.mp4');test('frame envelope',lambda:m.conform(source,dest,codec),dest);m.MAX_FRAMES=maxframes
  maxpacket=m.MAX_PACKET;m.MAX_PACKET=1;dest=t/(codec+'-packet-cap.mp4');test('packet envelope',lambda:m.conform(source,dest,codec),dest);m.MAX_PACKET=maxpacket
  def fail(temp,dest):raise RuntimeError('injected precommit failure')
  dest=t/(codec+'-fault.mp4');test('post-validation precommit failure',lambda:m.conform(source,dest,codec,fault=fail),dest)
  def corrupt(temp,dest):
   data=bytearray(temp.read_bytes());data[-1]^=1;temp.write_bytes(data)
  dest=t/(codec+'-corrupt.mp4');test('post-validation candidate corruption',lambda:m.conform(source,dest,codec,fault=corrupt),dest)
  def race(temp,dest):dest.write_bytes(b'competing complete destination')
  dest=t/(codec+'-race.mp4');test('destination creation race',lambda:m.conform(source,dest,codec,fault=race),dest,b'competing complete destination')
  # Reject an altered NAL length in a real sample, without writing partial output.
  _,packets,_=m.inspect(source);data=bytearray(source.read_bytes());pos=int(packets[0]['pos']);data[pos:pos+4]=b'\xff'*4;bad=t/(codec+'-invalid-length.mp4');bad.write_bytes(data);dest=t/(codec+'-invalid-length-out.mp4');test('malformed actual sample NAL length',lambda:m.conform(bad,dest,codec),dest)
  original_correct=m.correct_sps
  def bad_level(nal,codec,fields):
   corrected,receipt=original_correct(nal,codec,fields);name='level_idc' if codec=='h264' else 'general_level_idc';field=next(x for x in fields if x['name']==name);raw=bytearray(m.unescape(corrected,codec));offset=field['offset']+len(field['bits'])-1;raw[offset//8]^=1<<(7-offset%8);return m.escape(raw,codec),receipt
  m.correct_sps=bad_level;dest=t/(codec+'-other-SPS.mp4');test('other SPS semantic field mutation',lambda:m.conform(source,dest,codec),dest);m.correct_sps=original_correct
  original_config=m.replace_config
  def bad_configuration(body,codec,replacement=None):
   out,nals=original_config(body,codec,replacement)
   if replacement:
    raw=bytearray(out);raw[0]^=1;out=bytes(raw)
   return out,nals
  m.replace_config=bad_configuration;dest=t/(codec+'-other-config.mp4');test('non-SPS codec configuration header mutation',lambda:m.conform(source,dest,codec),dest);m.replace_config=original_config
  def bad_pps(body,codec,replacement=None):
   out,nals=original_config(body,codec,replacement)
   if replacement:
    pps=next(n for n in nals if m.nal_type(n,codec)==(8 if codec=='h264' else 34));pos=out.index(pps);raw=bytearray(out);raw[pos+len(pps)-1]^=1;out=bytes(raw)
   return out,nals
  m.replace_config=bad_pps;dest=t/(codec+'-PPS-mutant.mp4');test('PPS configuration payload mutation',lambda:m.conform(source,dest,codec),dest);m.replace_config=original_config
  dest=t/(codec+'-receipt-collision.mp4')
  process=subprocess.run(['/opt/homebrew/bin/python3',str(root/'checkpoint/native_chroma_conformance.py'),str(source),str(dest),'--codec',codec,'--receipt',str(dest)],capture_output=True,text=True)
  assert process.returncode!=0 and not dest.exists() and m.sha(source)==orig
  results.append({'codec':codec,'case':'CLI receipt/output collision','rejected':True,'noTemporaryCandidateLeaked':True})
  # Bit-exact fixed point for a stream already signaling center.
  already=r/('center-'+codec+'.mp4');dest=t/(codec+'-idempotent.mp4');ok=m.conform(already,dest,codec);assert m.sha(dest)==m.sha(already);results.append({'codec':codec,'case':'already-center idempotent','passed':True,'byteExact':True})
report={'passed':True,'negativeCasesRejected':sum(x.get('rejected',False) for x in results),'idempotentPositiveCases':2,'cases':results,'adapterSha256':m.sha(root/'checkpoint/native_chroma_conformance.py'),'noGPUOrCargoOrEncoderExport':True,'benchmarkTiming':False}
(r/'ATOMIC-FAIL-CLOSED-TESTS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
