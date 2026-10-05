"""Independent retained-small-scene checks: official demux/decoder plus pure byte/CPU oracle."""
import pathlib,json,hashlib,subprocess,re,math,shutil,struct
root=pathlib.Path(__file__).resolve().parent.parent;r=root/'comparison/native-conformance-prep-20261005';old=pathlib.Path('/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94/vulkan-evidence/qualification-02')
FFMPEG='/opt/homebrew/bin/ffmpeg';FFPROBE='/opt/homebrew/bin/ffprobe'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(cmd,label):
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=60);(r/(label+'.stdout')).write_text(p.stdout);(r/(label+'.stderr')).write_text(p.stderr);assert p.returncode==0;return p.stdout
# Predetermined protocol written before examining any oracle comparison.
protocol={'preparationOnly':True,'noNewGpuExportOr4KQualification':True,'frames':300,'width':256,'height':128,'fps':'30000/1001','center':{'physicalCentroid':[.5,.5],'equal2x2Weights':[.25,.25,.25,.25],'locationCodeTopBottom':[1,1]},'color':'sRGB EOTF then BT709 OETF, 709 limited Y16+219luma,U/V128+224chroma','nominalTolerance':1,'RGBStorage':'RGBA8Unorm pinned metal.mm; no alternate channel fitting','controlSources':'retained separate3 same-scene RGBA and NV12 controls at frames0/150/299; not a fresh same-stream GPU test','solidControlCoordinates':[[16,16],[240,16],[16,120],[240,80]],'solidColors':[[255,0,0],[0,255,0],[0,0,255],[255,255,255]],'floorsUnchanged':{'ssimY':.995,'psnrY':40,'psnrU':35,'psnrV':35},'mandatoryConformanceCopyAndParserCostIncludedInFutureExportClocks':True,'nativePool':3,'modifiedFPoolPerContext':64,'atomicOutput':'reject existing destination; private temporary candidate; link only after metadata/payload gates; no replace'}
(r/'CONTROL-PROTOCOL.json').write_text(json.dumps(protocol,indent=2)+'\n')
def hexbytes(text):
 b=bytearray()
 for line in text.splitlines():
  if ':' in line:b.extend(bytes.fromhex(line.split(':',1)[1].strip().split('  ',1)[0]))
 return bytes(b)
def parse_params(data,codec):
 out=[]
 if codec=='h264':
  pos=6
  for kind in range(2):
   count=data[5]&31 if kind==0 else data[pos]
   if kind:pos+=1
   for i in range(count):
    n=int.from_bytes(data[pos:pos+2],'big');pos+=2;out.append(data[pos:pos+n]);pos+=n
 else:
  pos=23
  for array in range(data[22]):
   count=int.from_bytes(data[pos+1:pos+3],'big');pos+=3
   for i in range(count):
    n=int.from_bytes(data[pos:pos+2],'big');pos+=2;out.append(data[pos:pos+n]);pos+=n
 return out
codec_reports=[]
for codec in ['h264','hevc']:
 source=r/('original-'+codec+'.mp4');dest=r/('center-'+codec+'.mp4');summaries=[];ps=[];sps=[];decoded=[];before_source=sha(source)
 for prefix,p in [('original',source),('center',dest)]:
  doc=json.loads(run([FFPROBE,'-v','error','-select_streams','v:0','-show_packets','-show_data','-show_entries','packet=pts,dts,duration,data','-of','json',str(p)],codec+'-'+prefix+'-packets'))
  sample=[]
  for packet in doc['packets']:
   raw=hexbytes(packet['data']);off=0;nals=[]
   while off<len(raw):
    n=int.from_bytes(raw[off:off+4],'big');off+=4;assert n and off+n<=len(raw);nal=raw[off:off+n];off+=n;typ=nal[0]&31 if codec=='h264' else (nal[0]>>1)&63;nals.append({'type':typ,'sha256':hashlib.sha256(nal).hexdigest(),'bytes':n})
   assert off==len(raw);sample.append({'pts':packet['pts'],'dts':packet['dts'],'duration':packet['duration'],'nals':nals})
  summaries.append(sample)
  streams=json.loads(run([FFPROBE,'-v','error','-show_streams','-show_data','-of','json',str(p)],codec+'-'+prefix+'-parameters'));params=parse_params(hexbytes(streams['streams'][0]['extradata']),codec);styp=7 if codec=='h264' else 33
  sps.append(next(n for n in params if (n[0]&31 if codec=='h264' else n[0]>>1&63)==styp));ps.append([n.hex() for n in params if (n[0]&31 if codec=='h264' else n[0]>>1&63)!=styp])
  digest=run([FFMPEG,'-v','error','-xerror','-i',str(p),'-map','0:v:0','-an','-pix_fmt','yuv420p','-fps_mode','passthrough','-f','framemd5','-'],codec+'-'+prefix+'-decoded')
  decoded.append([x.strip() for x in digest.splitlines() if x and not x.startswith('#')])
 styp=7 if codec=='h264' else 33;assert ps[0]==ps[1] and len(summaries[0])==len(summaries[1])==len(decoded[0])==len(decoded[1])==300
 assert decoded[0]==decoded[1]
 for a,b in zip(*summaries):
  assert [a[k] for k in ['pts','dts','duration']]==[b[k] for k in ['pts','dts','duration']]
  assert [x for x in a['nals'] if x['type']!=styp]==[x for x in b['nals'] if x['type']!=styp]
 # Independent RBSP bit comparison, including the stop bit; padding is excluded.
 bits=[''.join(f'{x:08b}' for x in n.replace(b'\0\0\3',b'\0\0')).rstrip('0') for n in sps]
 a,b=bits;prefix=next(i for i,(x,y) in enumerate(zip(a,b)) if x!=y);suffix=0
 while a[-1-suffix]==b[-1-suffix]:suffix+=1
 assert a[prefix:len(a)-suffix]=='0' and b[prefix:len(b)-suffix]=='1010010'
 assert a[:prefix]==b[:prefix] and a[len(a)-suffix:]==b[len(b)-suffix:] and sha(source)==before_source
 codec_reports.append({'codec':codec,'passed':True,'frames':300,'allNonSPSNALPayloadsExactlyEqual':True,'PPSVPSAndVCLExactlyEqual':True,'allDecodedFrameRowsExactlyEqual':True,'independentSPSRBSPOnlyEdit':{'offset':prefix,'old':'0','new':'1010010','prefixSuffixStopBitExactlyEqual':True},'sourceSha256':sha(source),'centerSha256':sha(dest)})
# Independent physical conversion oracle on retained separate positive-control raw streams.
rgba=(old/'rgba-control.raw').read_bytes();actual=(old/'nv12-control.raw').read_bytes();assert len(rgba)==256*128*4*3 and len(actual)==256*128*3//2*3
metal=pathlib.Path('/Users/gavinbintz/.codex/worktrees/gpu-vulkan-interop/helios/packages/portable/native/metal.mm');assert 'MTLPixelFormatRGBA8Unorm' in metal.read_text()
def transfer(v):
 x=v/255.;l=x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
 return 4.5*l if l<.018 else 1.099*l**.45-.099
expected=bytearray();color=[]
for frame in range(3):
 ys=bytearray(256*128);uv=bytearray(256*64)
 for y in range(0,128,2):
  for x in range(0,256,2):
   cb=cr=0.
   for dy in range(2):
    for dx in range(2):
     off=(frame*256*128+(y+dy)*256+x+dx)*4;rv,gv,bv,av=rgba[off:off+4];assert av==255
     rr,gg,bb=map(transfer,[rv,gv,bv]);l=.2126*rr+.7152*gg+.0722*bb;ys[(y+dy)*256+x+dx]=round(16+219*l);cb+=(bb-l)/1.8556;cr+=(rr-l)/1.5748
   uv[y//2*256+x]=round(128+56*cb);uv[y//2*256+x+1]=round(128+56*cr)
 predicted=bytes(ys+uv);observed=actual[frame*49152:(frame+1)*49152];maximum=max(abs(a-b) for a,b in zip(predicted,observed));assert maximum<=1
 for (x,y),rgb in zip(protocol['solidControlCoordinates'],protocol['solidColors']):
  off=(frame*32768+y*256+x)*4;assert list(rgba[off:off+3])==rgb
 expected.extend(predicted);color.append({'frameControl':frame,'sourceFrame':[0,150,299][frame],'maximumNominalCodeError':maximum,'differingBytes':sum(a!=b for a,b in zip(predicted,observed))})
(r/'independent-control-predicted.nv12').write_bytes(expected)
# New small lossless reference from retained GPU NV12 using pure planar splitting; explicit center input/output.
nv12=(old/'reference.nv12').read_bytes();assert len(nv12)==49152*300;planar=bytearray();md5s=[]
for i in range(300):
 raw=nv12[i*49152:(i+1)*49152];y=raw[:32768];uv=raw[32768:];p=y+uv[0::2]+uv[1::2];planar.extend(p);md5s.append(hashlib.md5(p).hexdigest())
ref=r/'reference-centered-small.mkv';assert not ref.exists()
cmd=[FFMPEG,'-v','error','-xerror','-f','rawvideo','-pix_fmt','yuv420p','-s','256x128','-r','30000/1001','-color_range','tv','-colorspace','bt709','-color_trc','bt709','-color_primaries','bt709','-chroma_sample_location','center','-i','pipe:0','-frames:v','300','-c:v','ffv1','-level','3','-threads','2','-color_range','tv','-colorspace','bt709','-color_trc','bt709','-color_primaries','bt709','-chroma_sample_location','center',str(ref)]
p=subprocess.run(cmd,input=bytes(planar),capture_output=True,timeout=60);(r/'reference-creation.stderr').write_bytes(p.stderr);assert p.returncode==0 and not p.stderr
result=run([FFMPEG,'-v','error','-xerror','-i',str(ref),'-map','0:v:0','-pix_fmt','yuv420p','-f','framemd5','-'],'reference-centered-decoded');rows=[x for x in result.splitlines() if x and not x.startswith('#')];assert len(rows)==300 and [x.split(',')[-1].strip() for x in rows]==md5s
report={'passed':True,'preparationOnly':True,'new4KQualification':False,'newGPUExportOrEncoderRun':False,'codecs':codec_reports,'independentPredeterminedCenteredControl':{'passed':True,'maximumTolerance':1,'frames':color,'separateControlRenderReproducibilityLimitDisclosed':True,'fineEdgesFromRGBAIncluded':True,'rawSources':[{'path':str(old/n),'sha256':sha(old/n)} for n in ['rgba-control.raw','nv12-control.raw']]},'smallReference':{'path':str(ref),'sha256':sha(ref),'pureNV12PlanarByteSplit':True,'all300DirectDecodedMD5sEqual':True,'command':cmd,'sourceNV12':str(old/'reference.nv12'),'sourceSha256':sha(old/'reference.nv12')},'nativePool':3,'FPoolPerContext':64,'benchmarkTiming':False,'zeroCopyProved':False}
(r/'INDEPENDENT-VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
