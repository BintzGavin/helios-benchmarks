"""Bounded SPS-only conformance for pinned native, single-video, unfragmented MP4.
Copies compressed samples; changes SPS chroma-siting bits and necessary MP4 sizes/offsets.
No decoder, rasterizer, encoder, raw-frame readback, or generic MP4 repair in this adapter.
"""
import dataclasses,hashlib,json,os,pathlib,re,struct,subprocess,tempfile,time
FFMPEG='/opt/homebrew/bin/ffmpeg';FFPROBE='/opt/homebrew/bin/ffprobe'
MAX_META=16*1024*1024;MAX_PACKET=64*1024*1024;MAX_FRAMES=30000
class Refused(ValueError):pass
def require(ok,message):
 if not ok:raise Refused(message)
def sha(p):
 with pathlib.Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def command(argv):
 p=subprocess.run(argv,capture_output=True,text=True,timeout=60)
 require(p.returncode==0,'media parser refused input');return p

def trace_sps(path):
 argv=[FFMPEG,'-hide_banner','-loglevel','trace','-i',str(path),'-map','0:v:0','-frames:v','1','-c:v','copy','-bsf:v','trace_headers','-f','null','-']
 p=command(argv);groups=[];current=None
 for line in p.stderr.splitlines():
  if '[trace_headers @' not in line:continue
  if 'Sequence Parameter Set' in line:
   if current is not None:groups.append(current)
   current=[];continue
  if current is not None and any(x in line for x in ['Picture Parameter Set','Video Parameter Set','Packet:','Slice Header','Supplemental Enhancement']):
   groups.append(current);current=None
  if current is not None:
   m=re.search(r'\]\s+(\d+)\s+(\S+)\s+([01]+)\s+=\s+(-?\d+)',line)
   if m:current.append({'offset':int(m[1]),'name':m[2],'bits':m[3],'value':int(m[4])})
 if current is not None:groups.append(current)
 require(bool(groups) and all(g==groups[0] for g in groups),'ambiguous SPS syntax')
 fields=groups[0];require(sum(x['name']=='chroma_loc_info_present_flag' for x in fields)==1,'missing chroma location VUI field')
 return fields,{'argv':argv,'returncode':p.returncode,'stderr':p.stderr}

def nal_type(nal,codec):
 require(len(nal)>= (1 if codec=='h264' else 2),'short NAL header')
 require(nal[0]&128==0,'forbidden NAL bit')
 if codec=='h264':return nal[0]&31
 require(nal[1]&7!=0 and ((nal[0]&1)<<5 | nal[1]>>3)==0,'unsupported HEVC layer/temporal header')
 return nal[0]>>1 &63

def unescape(nal,codec):
 header=1 if codec=='h264' else 2;out=bytearray(nal[:header]);z=0;i=header
 while i<len(nal):
  b=nal[i]
  if z==2 and b==3:
   require(i+1<len(nal) and nal[i+1]<=3,'invalid emulation prevention');z=0;i+=1;continue
  out.append(b);z=z+1 if b==0 else 0;i+=1
 return bytes(out)
def escape(rbsp,codec):
 header=1 if codec=='h264' else 2;out=bytearray(rbsp[:header]);z=0
 for b in rbsp[header:]:
  if z==2 and b<=3:out.append(3);z=0
  out.append(b);z=z+1 if b==0 else 0
 return bytes(out)

def correct_sps(nal,codec,fields):
 rbsp=unescape(nal,codec);bits=''.join(f'{b:08b}' for b in rbsp)
 flag=next(x for x in fields if x['name']=='chroma_loc_info_present_flag');stop=next(x for x in fields if x['name']=='rbsp_stop_one_bit')
 require(bits[flag['offset']:flag['offset']+len(flag['bits'])]==flag['bits'],'parser/RBSP flag mismatch')
 end=flag['offset']+1
 if flag['value']:
  for name in ['chroma_sample_loc_type_top_field','chroma_sample_loc_type_bottom_field']:
   x=next((x for x in fields if x['name']==name),None);require(x is not None and x['offset']==end,'unsupported VUI ordering');require(bits[end:end+len(x['bits'])]==x['bits'],'parser/RBSP location mismatch');end+=len(x['bits'])
 require(bits[stop['offset']]=='1' and set(bits[stop['offset']+1:])<= {'0'},'invalid SPS trailing bits')
 meaningful=bits[:stop['offset']+1];replacement='1'+'010'+'010' # present flag and unsigned Exp-Golomb 1/1
 new=meaningful[:flag['offset']]+replacement+meaningful[end:];new+='0'*((-len(new))%8)
 payload=escape(bytes(int(new[i:i+8],2) for i in range(0,len(new),8)),codec)
 return payload,{'oldFlagOffset':flag['offset'],'oldLocationEnd':end,'oldStopBit':stop['offset'],'newLocationBits':replacement,'allRemainingRBSPBitsIdentical':True,'oldSPSsha256':hashlib.sha256(nal).hexdigest(),'newSPSsha256':hashlib.sha256(payload).hexdigest()}

@dataclasses.dataclass
class Box:
 type:bytes;body:bytes=b'';children:list|None=None;prefix:bytes=b'';wide:bool=False;old_start:int=0;old_size:int=0
 def encode(self):
  payload=self.prefix+b''.join(x.encode() for x in self.children) if self.children is not None else self.body
  n=len(payload)+(16 if self.wide else 8);require(self.wide or n<2**32,'32-bit box overflow')
  return (struct.pack('>I4sQ',1,self.type,n) if self.wide else struct.pack('>I4s',n,self.type))+payload
CONTAINERS={b'moov',b'trak',b'mdia',b'minf',b'stbl',b'edts'}
ALLOWED={b'moov':{b'mvhd',b'trak',b'udta'},b'trak':{b'tkhd',b'edts',b'mdia'},b'mdia':{b'mdhd',b'hdlr',b'minf'},b'minf':{b'vmhd',b'dinf',b'stbl'},b'stbl':{b'stsd',b'stts',b'stss',b'ctts',b'stsc',b'stsz',b'stco',b'co64'},b'edts':{b'elst'},b'avc1':{b'avcC',b'colr',b'pasp',b'btrt',b'fiel',b'clap'},b'hvc1':{b'hvcC',b'colr',b'pasp',b'btrt',b'fiel',b'clap'},b'hev1':{b'hvcC',b'colr',b'pasp',b'btrt',b'fiel',b'clap'}}
def boxes(data,parent=None):
 out=[];i=0
 while i<len(data):
  require(i+8<=len(data),'truncated MP4 box');n,t=struct.unpack_from('>I4s',data,i);header=8;wide=n==1
  if wide:require(i+16<=len(data),'truncated wide box');n=struct.unpack_from('>Q',data,i+8)[0];header=16
  require(n>=header and i+n<=len(data),'invalid MP4 box size')
  if parent in ALLOWED:require(t in ALLOWED[parent],'unsupported MP4 child '+repr(t))
  payload=data[i+header:i+n];node=Box(t,body=payload,wide=wide)
  prefix=None
  if t in CONTAINERS:prefix=0
  if t==b'stsd':require(len(payload)>=8 and payload[:4]==b'\0'*4 and int.from_bytes(payload[4:8],'big')==1,'unsupported sample descriptions');prefix=8
  if t in {b'avc1',b'hvc1',b'hev1'}:require(len(payload)>=78 and payload[6:8]==b'\0\1','unsupported sample entry');prefix=78
  if prefix is not None:node.prefix=payload[:prefix];node.children=boxes(payload[prefix:],t);node.body=b''
  out.append(node);i+=n
 return out
def walk(nodes):
 for b in nodes:
  yield b
  if b.children is not None:yield from walk(b.children)
def one(nodes,t):
 matches=[b for b in walk(nodes) if b.type==t];require(len(matches)==1,'expected one '+repr(t));return matches[0]

def replace_config(body,codec,replacement=None):
 require(body and body[0]==1,'unsupported codec configuration');out=bytearray();nals=[]
 if codec=='h264':
  require(len(body)>=7 and body[4]&3==3,'requires four-byte AVCC lengths');out.extend(body[:6]);offset=6;counts=[body[5]&31]
  for part in range(2):
   if part:require(offset<len(body),'short PPS array');counts.append(body[offset]);out.append(body[offset]);offset+=1
   for _ in range(counts[part]):
    require(offset+2<=len(body),'short parameter length');n=int.from_bytes(body[offset:offset+2],'big');offset+=2;require(n and offset+n<=len(body),'short parameter NAL');nal=body[offset:offset+n];offset+=n
    require(nal_type(nal,codec)==(7 if part==0 else 8),'invalid AVCC parameter type');nals.append(nal)
    if replacement and nal==replacement[0]:nal=replacement[1]
    out.extend(len(nal).to_bytes(2,'big'));out.extend(nal)
  out.extend(body[offset:]) # AVC high-profile extension retained exactly.
 else:
  require(len(body)>=23 and body[21]&3==3,'requires four-byte HVCC lengths');out.extend(body[:23]);offset=23
  for _ in range(body[22]):
   require(offset+3<=len(body),'short HVCC array');typ=body[offset]&63;count=int.from_bytes(body[offset+1:offset+3],'big');out.extend(body[offset:offset+3]);offset+=3
   require(typ in {32,33,34,39,40},'unsupported HVCC array')
   for _ in range(count):
    require(offset+2<=len(body),'short parameter length');n=int.from_bytes(body[offset:offset+2],'big');offset+=2;require(n and offset+n<=len(body),'short parameter NAL');nal=body[offset:offset+n];offset+=n
    require(nal_type(nal,codec)==typ,'HVCC type mismatch');nals.append(nal)
    if replacement and nal==replacement[0]:nal=replacement[1]
    out.extend(len(nal).to_bytes(2,'big'));out.extend(nal)
  require(offset==len(body),'trailing HVCC bytes')
 return bytes(out),nals

def inspect(path):
 argv=[FFPROBE,'-v','error','-show_streams','-show_packets','-read_intervals','%+#'+str(MAX_FRAMES+1),'-of','json',str(path)];p=command(argv);doc=json.loads(p.stdout)
 require(len(doc['streams'])==1 and doc['streams'][0]['codec_type']=='video','only one video track supported');s=doc['streams'][0];codec=s['codec_name'];require(codec in {'h264','hevc'},'unsupported codec')
 require(s.get('has_b_frames')==0 and s['pix_fmt']=='yuv420p','requires native Main8bit420/no B frames')
 require(all(s.get(k)==v for k,v in {'color_range':'tv','color_space':'bt709','color_transfer':'bt709','color_primaries':'bt709'}.items()),'requires limited BT709 contract')
 packets=doc['packets'];require(0<len(packets)<=MAX_FRAMES,'frame envelope exceeded')
 from fractions import Fraction
 fps=Fraction(s['avg_frame_rate']);tb=Fraction(s['time_base']);require(fps>0,'invalid frame rate')
 for i,x in enumerate(packets):
  require(x['pts']==x['dts'] and Fraction(x['pts'])*tb==Fraction(i,1)/fps and Fraction(x['duration'])*tb==1/fps,'nonuniform/nonzero/reordered cadence unsupported')
  require(0<int(x['size'])<=MAX_PACKET,'packet envelope exceeded')
 return s,packets,{'argv':argv,'returncode':p.returncode}
def nals(data,codec):
 out=[];off=0
 while off<len(data):
  require(off+4<=len(data),'truncated NAL length');n=int.from_bytes(data[off:off+4],'big');off+=4;require(0<n<=len(data)-off,'invalid NAL length');nal=data[off:off+n];off+=n;nal_type(nal,codec);out.append(nal)
 return out
def packet_summary(path,codec,packets):
 summaries=[]
 with path.open('rb') as f:
  for i,p in enumerate(packets):
   f.seek(int(p['pos']));data=f.read(int(p['size']));require(len(data)==int(p['size']),'short MP4 packet')
   summaries.append([{'type':nal_type(n,codec),'bytes':len(n),'sha256':hashlib.sha256(n).hexdigest()} for n in nals(data,codec)])
 return summaries

def conform(source,destination,expected_codec=None,fault=None):
 source=pathlib.Path(source);destination=pathlib.Path(destination);start=time.monotonic()
 require(source.is_file() and not source.is_symlink() and source.resolve()!=destination.resolve(),'invalid source/destination')
 require(not destination.exists() and not destination.is_symlink(),'destination exists');oldhash=sha(source)
 stream,packets,probe=inspect(source);codec=stream['codec_name'];require(expected_codec is None or codec==expected_codec,'codec mismatch')
 fields,tr=trace_sps(source);top=[];size=source.stat().st_size
 with source.open('rb') as f:
  off=0
  while off<size:
   f.seek(off);h=f.read(16);require(len(h)>=8,'truncated top-level box');n,t=struct.unpack('>I4s',h[:8]);wide=n==1;header=16 if wide else 8
   if wide:require(len(h)==16,'short extended box');n=struct.unpack('>Q',h[8:16])[0]
   require(t in {b'ftyp',b'moov',b'free',b'mdat'} and n>=header and off+n<=size,'unsupported top-level MP4 layout')
   if t==b'mdat':node=Box(t,wide=wide,old_start=off,old_size=n)
   else:
    require(n<=MAX_META,'metadata envelope exceeded');f.seek(off+header);payload=f.read(n-header);node=Box(t,body=payload,wide=wide,old_start=off,old_size=n)
    if t==b'moov':node.children=boxes(payload,b'moov');node.body=b''
   top.append(node);off+=n
 require(sum(b.type==b'mdat' for b in top)==1 and sum(b.type==b'moov' for b in top)==1,'requires one moov and mdat')
 require(sum(b.type==b'trak' for b in walk(top))==1,'requires one track')
 mdat=one(top,b'mdat');head=16 if mdat.wide else 8;cursor=mdat.old_start+head
 for p in packets:require(int(p['pos'])==cursor,'mdat sample coverage not contiguous');cursor+=int(p['size'])
 require(cursor==mdat.old_start+mdat.old_size,'mdat contains unaccounted bytes')
 config=one(top,b'avcC' if codec=='h264' else b'hvcC');_,params=replace_config(config.body,codec);styp=7 if codec=='h264' else 33;sps=[n for n in params if nal_type(n,codec)==styp];require(len(sps)==1,'requires one static SPS')
 old_config=config.body
 corrected,rbsp=correct_sps(sps[0],codec,fields);config.body,_=replace_config(config.body,codec,(sps[0],corrected))
 require(old_config.count(sps[0])==1,'ambiguous SPS configuration bytes')
 pos=old_config.index(sps[0]);require(pos>=2 and int.from_bytes(old_config[pos-2:pos],'big')==len(sps[0]),'invalid SPS configuration length')
 expected_config=old_config[:pos-2]+len(corrected).to_bytes(2,'big')+corrected+old_config[pos+len(sps[0]):]
 require(config.body==expected_config,'non-SPS codec configuration bytes changed')
 lengths=[];summaries=[]
 with source.open('rb') as f:
  for p in packets:
   f.seek(int(p['pos']));data=f.read(int(p['size']));a=nals(data,codec);new=[]
   for n in a:
    if nal_type(n,codec)==styp:require(n==sps[0],'dynamic SPS unsupported');n=corrected
    new.append(n)
   lengths.append(sum(4+len(n) for n in new))
   summaries.append([{'type':nal_type(n,codec),'bytes':len(n),'sha256':hashlib.sha256(n).hexdigest()} for n in new])
 stsz=one(top,b'stsz');require(len(stsz.body)>=12 and stsz.body[:4]==b'\0'*4,'invalid stsz');fixed,count=struct.unpack('>II',stsz.body[4:12]);require(count==len(packets),'stsz count mismatch')
 oldlengths=[fixed]*count if fixed else list(struct.unpack('>'+str(count)+'I',stsz.body[12:]));require(oldlengths==[int(p['size']) for p in packets],'sample sizes disagree')
 # Always retain variable-size table shape; fixed-size input is explicitly unsupported.
 require(fixed==0,'fixed-size sample table unsupported');stsz.body=stsz.body[:12]+struct.pack('>'+str(count)+'I',*lengths)
 old_offsets=[];offset_nodes=[b for b in walk(top) if b.type in {b'stco',b'co64'}];require(len(offset_nodes)==1,'expected one chunk offset table')
 for node in offset_nodes:
  require(node.body[:4]==b'\0'*4,'unsupported chunk table version');ct=int.from_bytes(node.body[4:8],'big');width=4 if node.type==b'stco' else 8;require(len(node.body)==8+ct*width,'invalid chunk table')
  old_offsets=[int.from_bytes(node.body[8+i*width:8+(i+1)*width],'big') for i in range(ct)]
 delta=sum(lengths)-sum(oldlengths);new_mdat_size=mdat.old_size+delta;require(mdat.wide or new_mdat_size<2**32,'mdat32 overflow')
 layout=0
 for b in top:
  if b is mdat:new_start=layout+head;layout+=new_mdat_size
  else:layout+=len(b.encode())
 new_positions=[];cursor=new_start
 for n in lengths:new_positions.append(cursor);cursor+=n
 mapping={int(p['pos']):n for p,n in zip(packets,new_positions)};require(all(x in mapping for x in old_offsets),'chunk not at sample boundary')
 for node in offset_nodes:
  width=4 if node.type==b'stco' else 8;values=[mapping[x] for x in old_offsets];require(all(x<2**(8*width) for x in values),'chunk offset overflow');node.body=node.body[:8]+b''.join(x.to_bytes(width,'big') for x in values)
 fd,tmp=tempfile.mkstemp(prefix='.'+destination.name+'.',suffix='.candidate',dir=destination.parent);temp=pathlib.Path(tmp);committed=False
 try:
  with os.fdopen(fd,'wb') as out,source.open('rb') as f:
   for b in top:
    if b is not mdat:out.write(b.encode());continue
    out.write(struct.pack('>I4sQ',1,b'mdat',new_mdat_size) if mdat.wide else struct.pack('>I4s',new_mdat_size,b'mdat'))
    for p in packets:
     f.seek(int(p['pos']));a=nals(f.read(int(p['size'])),codec)
     for n in a:
      if nal_type(n,codec)==styp:n=corrected
      out.write(len(n).to_bytes(4,'big'));out.write(n)
   out.flush();os.fsync(out.fileno())
  new_stream,new_packets,new_probe=inspect(temp);new_fields,new_trace=trace_sps(temp)
  cfg_command=[FFPROBE,'-v','error','-select_streams','v:0','-show_streams','-show_data','-show_entries','stream=extradata','-of','json',str(temp)]
  cfg_result=command(cfg_command);cfg_text=json.loads(cfg_result.stdout)['streams'][0]['extradata'];cfg_bytes=bytearray()
  for line in cfg_text.splitlines():
   if ':' in line:cfg_bytes.extend(bytes.fromhex(line.split(':',1)[1].strip().split('  ',1)[0]))
  require(bytes(cfg_bytes)==expected_config,'serialized codec configuration changed')
  ignored={'chroma_loc_info_present_flag','chroma_sample_loc_type_top_field','chroma_sample_loc_type_bottom_field','rbsp_alignment_zero_bit'}
  require([(x['name'],x['value']) for x in fields if x['name'] not in ignored]==[(x['name'],x['value']) for x in new_fields if x['name'] not in ignored],'non-location SPS fields changed')
  for name,value in [('chroma_loc_info_present_flag',1),('chroma_sample_loc_type_top_field',1),('chroma_sample_loc_type_bottom_field',1)]:require(sum(x['name']==name and x['value']==value for x in new_fields)==1,'wrong corrected chroma location')
  require(new_stream.get('chroma_location')=='center','corrected stream does not signal center')
  require([(p['pts'],p['dts'],p['duration']) for p in packets]==[(p['pts'],p['dts'],p['duration']) for p in new_packets] and stream['time_base']==new_stream['time_base'],'sample timing changed')
  actual=packet_summary(temp,codec,new_packets);require(actual==summaries,'rewritten packet payload mismatch')
  before=packet_summary(source,codec,packets)
  require([[x for x in a if x['type']!=styp] for a in before]==[[x for x in a if x['type']!=styp] for a in actual],'non-SPS sample payload changed')
  require(sha(source)==oldhash,'source changed during correction')
  verified_hash=sha(temp)
  if fault:fault(temp,destination)
  require(sha(temp)==verified_hash and sha(source)==oldhash,'files changed before atomic commit')
  # Atomic create with no replacement even if another writer wins the destination race.
  os.link(temp,destination);committed=True;temp.unlink()
  result={'codec':codec,'frames':len(packets),'width':stream['width'],'height':stream['height'],'fps':stream['avg_frame_rate'],'inputSha256':oldhash,'outputSha256':sha(destination),'SPS':rbsp,'fieldsBefore':fields,'fieldsAfter':new_fields,'allNonSPSNALPayloadsExactlyEqual':True,'PPSVPSAndVCLExactlyEqual':True,'codecConfigurationOutsideSPSExactlyEqual':True,'sampleCountOrderCadenceAndTablesPreserved':True,'atomicNoReplace':True,'noRawFrameReadbackOrFullDecodeStageInAdapter':True,'mandatoryExportStageSeconds':time.monotonic()-start,'benchmarkTiming':False,'adapterPreparationOnly':True,'commands':[probe,{'argv':tr['argv'],'returncode':tr['returncode']},new_probe,{'argv':new_trace['argv'],'returncode':new_trace['returncode']}],'sourceTrace':tr['stderr'],'destinationTrace':new_trace['stderr'],'packetPayloadsBefore':before,'packetPayloadsAfter':actual}
  return result
 finally:
  if temp.exists():temp.unlink()

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=pathlib.Path);parser.add_argument('destination',type=pathlib.Path);parser.add_argument('--codec',choices=['h264','hevc'],required=True);parser.add_argument('--receipt',type=pathlib.Path,required=True)
 args=parser.parse_args();require(not args.receipt.exists() and not args.receipt.is_symlink(),'receipt exists');require(args.receipt.resolve() not in {args.source.resolve(),args.destination.resolve()},'receipt/source/output collision');result=conform(args.source,args.destination,args.codec)
 for key in ['sourceTrace','destinationTrace']:
  (args.receipt.parent/(args.receipt.name+'.'+key+'.log')).write_text(result.pop(key))
 args.receipt.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'codec':result['codec'],'frames':result['frames'],'outputSha256':result['outputSha256'],'adapterPreparationOnly':True,'benchmarkTiming':False}))
