import pathlib,subprocess,re,json,hashlib
from fractions import Fraction
root=pathlib.Path(__file__).resolve().parent.parent
def spsfields(text):
 groups=[];fields=None
 for l in text.splitlines():
  if '[trace_headers @' not in l:continue
  if 'Sequence Parameter Set' in l:
   if fields is not None:groups.append(fields)
   fields=[];continue
  if fields is not None and ('Picture Parameter Set' in l or 'Packet:' in l):
   groups.append(fields);fields=None
  if fields is not None:
   m=re.search(r'\]\s+\d+\s+([\w\[\]]+)\s+[01]+\s+=\s+(-?\d+)',l)
   if m:fields.append([m[1],int(m[2])])
 if fields is not None:groups.append(fields)
 assert groups and all(g==groups[0] for g in groups)
 assert sum(x[0]=='chroma_loc_info_present_flag' for x in groups[0])==1
 return groups[0]
def compare(a,b):
 allowed={'chroma_loc_info_present_flag','chroma_sample_loc_type_top_field','chroma_sample_loc_type_bottom_field','rbsp_alignment_zero_bit'}
 assert [x for x in a if x[0] not in allowed]==[x for x in b if x[0] not in allowed]
 assert [x for x in a if x[0].startswith('chroma_loc') or x[0].startswith('chroma_sample_loc')]==[['chroma_loc_info_present_flag',0]]
 assert [x for x in b if x[0].startswith('chroma_loc') or x[0].startswith('chroma_sample_loc')]==[['chroma_loc_info_present_flag',1],['chroma_sample_loc_type_top_field',1],['chroma_sample_loc_type_bottom_field',1]]
 assert all(x[1]==0 for x in a+b if x[0]=='rbsp_alignment_zero_bit')
def audit(r):
 fields={};commands=[]
 for kind,name in [('old','video.mp4'),('new','video-center.mp4')]:
  argv=['/opt/homebrew/bin/ffmpeg','-hide_banner','-loglevel','trace','-i',str(r/name),'-map','0:v:0','-frames:v','1','-c:v','copy','-bsf:v','trace_headers','-f','null','-']
  p=subprocess.run(argv,capture_output=True,text=True,timeout=60);assert p.returncode==0
  (r/(kind+'-first-packet-trace.stderr.log')).write_text(p.stderr);fields[kind]=spsfields(p.stderr);commands.append(argv)
 compare(fields['old'],fields['new'])
 c=json.loads((r/'CHROMA-CONFORMANCE.json').read_text());assert c['PPSbytesUnchanged'] and c['allVCLPayloadsExactlyEqual'] and c['allDecodedFrameBytesExactlyEqual']
 d=json.loads((r/'decoded-frames.json').read_text());s=d['streams'][0];n=len(d['frames']);keys=[]
 for i,f in enumerate(d['frames']):
  assert Fraction(f['pts'])*Fraction(s['time_base'])==Fraction(i,30)
  assert Fraction(f['duration'])*Fraction(s['time_base'])==Fraction(1,30)
  for k,v in {'width':s['width'],'height':s['height'],'pix_fmt':'yuv420p','color_range':'tv','color_space':'bt709','color_transfer':'bt709','color_primaries':'bt709','chroma_location':'center'}.items():assert f[k]==v,(i,k)
  if f['key_frame']:keys.append(i)
 assert keys[0]==0 and max(b-a for a,b in zip(keys,keys[1:]+[n]))<=30
 out={'passed':True,'frames':n,'fields':fields,'parserCommands':commands,'independentParser':'FFmpeg trace_headers SPS syntax','onlySemanticChanges':'chroma location flag 0->1, top/bottom1; byte alignment padding length changes','allOtherSPSFieldsEqual':True,'PPSUnchanged':True,'everyVCLPayloadExactlyEqual':True,'allDecodedFramesExactlyEqual':True,'cadenceColorGOPPassed':True,'keyframes':keys,'maxGop':max(b-a for a,b in zip(keys,keys[1:]+[n])),'benchmarkTiming':False}
 (r/'SPS-FIELD-CADENCE-AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':
 import sys
 d=audit(pathlib.Path(sys.argv[1]));print({k:v for k,v in d.items() if k not in ['fields','parserCommands']})
