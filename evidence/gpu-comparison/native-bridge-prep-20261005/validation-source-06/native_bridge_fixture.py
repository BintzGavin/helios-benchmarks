"""CPU ABI/process fixture; all native GPU/encoder contract flags are synthetic."""
import hashlib,json,os,pathlib,signal,struct,sys,time
s=json.loads(pathlib.Path(os.environ['BRIDGE_FIXTURE_SPEC']).read_text());a=sys.argv[1:];mode,w,h,num,den,bitrate,path,trace,capture,gop,pool,codec=a
fault=s.get('testControl','');header=sys.stdin.buffer.readline(1024*1024);assert header.endswith(b'\n') and json.loads(header)['fonts']
if fault=='hang-helper':signal.signal(signal.SIGTERM,signal.SIG_IGN)
rows=[];n=0;raw_file=pathlib.Path(s['rawFixture']['path'])
with raw_file.open('rb') as raw:
 while True:
  prefix=sys.stdin.buffer.read(32)
  if not prefix:break
  assert len(prefix)==32;magic,length,count,reserved=struct.unpack('<IIII',prefix[:16]);assert magic==0x35464748 and 32<=length<=32*1024*1024 and not reserved
  data=sys.stdin.buffer.read(length-32);assert len(data)==length-32
  if fault=='early-helper-exit':raise SystemExit(8)
  rows.append(hashlib.sha256(prefix+data).hexdigest());n+=1
  if mode=='reference-binary':
   b=raw.read(256*128*3//2);assert len(b)==49152
   if fault=='short-raw' and n==s['frames']:b=b[:-1]
   for offset in range(0,len(b),8191):sys.stdout.buffer.write(b[offset:offset+8191]);sys.stdout.buffer.flush()
  elif mode=='raster-binary':sys.stdout.buffer.write(b'\0'*(256*128*4));sys.stdout.buffer.flush()
  if fault=='hang-helper':time.sleep(60)
 if fault=='extra-raw':sys.stdout.buffer.write(b'x');sys.stdout.buffer.flush()
 if fault=='fail-after-raw':raise SystemExit(9)
 if mode=='encode-binary':pathlib.Path(path).write_bytes(pathlib.Path(s['elementaryFixture']['path']).read_bytes())
receipt={'kind':'BRIDGE_CPU_SYNTHETIC','GPUExecuted':False,'protocol':s['protocol'],'codec':codec,'transport':'binary','frames':n,'encoderPool':int(pool),'gop':int(gop),'bitrate':int(bitrate),'configuredBitrate':int(bitrate) if mode=='encode-binary' else None,'rasterizer':'skia-'+s['backend'],'encoder':'videotoolbox' if mode=='encode-binary' else 'none','hardwareUsed':mode=='encode-binary','hardwareRequired':mode=='encode-binary','explicitRawReadbackBytes':0 if mode=='encode-binary' else n*256*128*(4 if mode=='raster-binary' else 3)//(1 if mode=='raster-binary' else 2),'packetHashes':rows}
if fault=='wrong-protocol':receipt['protocol']=4
if fault=='software-fallback':receipt['hardwareUsed']=False
if fault=='pretend-real-hardware':receipt.pop('kind');receipt['GPUExecuted']=True
if fault=='wrong-frame-count':receipt['frames']=n-1
if fault=='wrong-packet-hash':receipt['packetHashes'][0]='0'*64
print(json.dumps(receipt),file=sys.stderr if mode!='encode-binary' else sys.stdout,flush=True)
