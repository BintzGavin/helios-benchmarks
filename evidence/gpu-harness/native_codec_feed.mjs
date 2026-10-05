/** Binary feed/receipt integration. CPU fixture process only until GPU qualification. */
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {once} from 'node:events';
import {resolve,dirname,join} from 'node:path';
import {pathToFileURL} from 'node:url';
const root='/Users/gavinbintz/Documents/Codex/2026-10-02/task';
const fixture=join(root,'checkpoint/codec_fixture_helper.py');
const sha=b=>createHash('sha256').update(b).digest('hex');
const spec=JSON.parse(await readFile(process.argv[2],'utf8'));
let child;
try {
  if(spec.purpose!=='CPU-feed-control') throw Error('GPU_EXECUTION_UNQUALIFIED_NO_LAUNCH');
  if(spec.command[0]!==spec.pythonExecutable || spec.command[1]!==fixture)throw Error('CPU_HELPER_SCOPE');
  for(const p of spec.pins){const b=await readFile(p.path);if(b.length!==p.bytes||sha(b)!==p.sha256)throw Error('PIN_MISMATCH');}
  if(!spec.pins.some(x=>x.path===fixture)||!spec.pins.some(x=>x.path===spec.pythonExecutable)||!spec.pins.some(x=>x.path===spec.recorderModule)||!spec.pins.some(x=>x.path===spec.sceneModule)||!spec.pins.some(x=>x.path===spec.font.path))throw Error('MISSING_CPU_PIN');
  if(![5,7,9].includes(spec.protocol)||!['h264','hevc'].includes(spec.codec)||![1,2,3].includes(spec.frames)||spec.width!==256||spec.height!==128)throw Error('CPU_ENVELOPE');
  if(spec.protocol!==(spec.backend==='vulkan'?9:spec.codec==='hevc'?7:5))throw Error('PROTOCOL_CODEC');
  if(!['encode-binary','reference-binary','raster-binary'].includes(spec.command[2])||spec.command[13]!==spec.codec||spec.command[3]!=='256'||spec.command[4]!=='128'||spec.command[5]!=='30000'||spec.command[6]!=='1001'||spec.command[7]!==String(spec.bitrate)||spec.command[11]!=='30'||spec.command[12]!=='3')throw Error('CPU_NATIVE_ARGV');
  if(spec.outputDirectory!==dirname(resolve(process.argv[2]))||!resolve(spec.outputDirectory).startsWith(join(root,'comparison/codec-orchestration-prep-20261005/cpu-feed-controls/')))throw Error('CPU_OUTPUT_SCOPE');
  if(Object.keys(spec.taskSettings??{}).some(x=>x!=='CODEC_FIXTURE_FAULT')||spec.benchmarkTiming!==false)throw Error('NO_PROFILE_INJECTION_IN_CPU_TESTS');
  const {recordGpuCanvasBinary}=await import(pathToFileURL(spec.recorderModule).href);
  const {createFixtureScene}=await import(pathToFileURL(spec.sceneModule).href);
  const font=await readFile(spec.font.path);const composition=createFixtureScene(font);
  let stderr='',stdout='',stderrBytes=0,stdoutBytes=0;
  child=spawn(spec.command[0],spec.command.slice(1),{stdio:['pipe','pipe','pipe'],env:{...process.env,...(spec.taskSettings??{})},detached:true});
  const done=new Promise((ok,fail)=>{child.on('error',fail);child.on('close',(code,signal)=>code===0?ok():fail(Error(`PRODUCER_EXIT:${code}/${signal}`)));});
  const readErr=(async()=>{for await(const b of child.stderr){stderrBytes+=b.length;if(stderrBytes>65536)throw Error('STDERR_CAP');stderr+=b;}})();
  const raw=spec.command[2]!=='encode-binary';
  const readOut=(async()=>{for await(const b of child.stdout){stdoutBytes+=b.length;if(raw){if(stdoutBytes>spec.frames*256*128*(spec.command[2]==='raster-binary'?4:1.5))throw Error('RAW_OUTPUT_CAP');if(!process.stdout.write(b))await once(process.stdout,'drain');}else{if(stdoutBytes>65536)throw Error('RECEIPT_CAP');stdout+=b;}}})();
  const feed=(async()=>{
    const send=async b=>{if(!child.stdin.write(b))await Promise.race([once(child.stdin,'drain'),done.then(()=>{throw Error('PREMATURE_PRODUCER_EXIT');})]);};
    const header=Buffer.from(JSON.stringify({fonts:{pinned:font.toString('base64')}})+'\n');await send(header);
    const combined=createHash('sha256').update(header);const frames=[];let capacity=1024;
    for(let index=0;index<spec.frames;index++){
      const packet=await recordGpuCanvasBinary(composition,index,capacity);capacity=packet.length;
      if(packet.length>32*1024*1024||packet.readUInt32LE(0)!==0x35464748||packet.readUInt32LE(4)!==packet.length)throw Error('BINARY_ENVELOPE');
      frames.push({index,sourceIndex:index,packetBytes:packet.length,sha256:sha(packet)});combined.update(packet);await send(packet);
    }
    child.stdin.end();return {frames,feedSha256:combined.digest('hex'),headerBytes:header.length};
  })();
  const feedReceipt=await Promise.all([feed,readOut,readErr,done]).then(x=>x[0]);
  const lines=(raw?stderr:stdout).trim().split('\n').filter(Boolean);if(lines.length!==1)throw Error('RECEIPT_COUNT');
  const n=JSON.parse(lines[0]);
  if(n.kind!=='CPU-fixture-synthetic-native-receipt')throw Error('CPU_RECEIPT_KIND');
  if(n.protocol!==spec.protocol||n.transport!=='binary'||n.codec!==spec.codec||n.frames!==spec.frames||n.gop!==30||n.encoderPool!==3||n.bitrate!==spec.bitrate||n.rasterizer!==(spec.backend==='vulkan'?'skia-vulkan':'skia-metal'))throw Error('NATIVE_CONTRACT');
  if(raw){if(n.encoder!=='none'||n.configuredBitrate!==null||n.explicitRawReadbackBytes!==stdoutBytes||stdoutBytes!==spec.frames*256*128*(spec.command[2]==='raster-binary'?4:1.5))throw Error('REFERENCE_CONTRACT');}
  else if(n.encoder!=='videotoolbox'||n.hardwareRequired!==true||n.hardwareUsed!==true||n.configuredBitrate!==spec.bitrate||n.explicitRawReadbackBytes!==0)throw Error('HARDWARE_CONTRACT');
  await writeFile(join(spec.outputDirectory,'DRIVER.json'),JSON.stringify({status:'passed',purpose:spec.purpose,nativeReceipt:n,...feedReceipt,GPUExecuted:false,hardwareFlagsAreSynthetic:true,benchmarkTiming:false},null,2),{flag:'wx'});
} catch(error) {
  if(child){try{process.kill(-child.pid,'SIGTERM');}catch{}}
  console.error(String(error));process.exitCode=1;
}
