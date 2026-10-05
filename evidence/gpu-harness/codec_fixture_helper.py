"""Deliberately synthetic CPU process; never a GPU or encoding attestation."""
import hashlib,json,os,struct,sys
a=sys.argv[1:];mode,w,h,num,den,bitrate,path,trace,capture,gop,pool,codec=a
w,h,bitrate,gop,pool=map(int,[w,h,bitrate,gop,pool]);fault=os.environ.get('CODEC_FIXTURE_FAULT','')
header=sys.stdin.buffer.readline(1024*1024)
assert header.endswith(b'\n') and json.loads(header)['fonts']
n=0;packets=[]
while True:
 prefix=sys.stdin.buffer.read(32)
 if not prefix:break
 assert len(prefix)==32;magic,length,count,reserved=struct.unpack('<IIII',prefix[:16]);assert magic==0x35464748 and 32<=length<=32*1024*1024 and not reserved
 data=sys.stdin.buffer.read(length-32);assert len(data)==length-32
 packets.append(hashlib.sha256(prefix+data).hexdigest());n+=1
 if fault=='early-exit':raise SystemExit(8)
receipt={'kind':'CPU-fixture-synthetic-native-receipt','protocol':9 if 'vulkan' in trace else 7 if codec=='hevc' else 5,'codec':codec,'transport':'binary','bitrate':bitrate,'configuredBitrate':bitrate if mode=='encode-binary' else None,'gop':gop,'encoderPool':pool,'frames':n,'rasterizer':'skia-vulkan' if 'vulkan' in trace else 'skia-metal','encoder':'videotoolbox' if mode=='encode-binary' else 'none','hardwareRequired':mode=='encode-binary','hardwareUsed':mode=='encode-binary','explicitRawReadbackBytes':0 if mode=='encode-binary' else n*w*h*(4 if mode=='raster-binary' else 3)//(1 if mode=='raster-binary' else 2),'zeroCopyProved':False,'GPUExecuted':False,'packetHashes':packets}
if fault=='wrong-protocol':receipt['protocol']=4
if fault=='wrong-codec':receipt['codec']='h264' if codec=='hevc' else 'hevc'
if fault=='software-fallback':receipt['hardwareUsed']=False
if fault=='wrong-pool':receipt['encoderPool']=1
if fault=='wrong-gop':receipt['gop']=90
if fault=='wrong-bitrate':receipt['configuredBitrate']=1
if fault=='raw-download':receipt['explicitRawReadbackBytes']=1
if fault=='wrong-frame-count':receipt['frames']=n-1
if mode=='encode-binary':print(json.dumps(receipt))
else:
 if fault!='short-raw':sys.stdout.buffer.write(b'\0'*receipt['explicitRawReadbackBytes'])
 sys.stdout.buffer.flush();print(json.dumps(receipt),file=sys.stderr)
