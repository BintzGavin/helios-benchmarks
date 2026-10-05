/** Separately frozen live Metal/HEVC bridge. No CPU fixture activation path. */
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {readFile,writeFile,link,stat,realpath} from 'node:fs/promises';
import {dirname,join,resolve} from 'node:path';
import {once} from 'node:events';
import {pathToFileURL} from 'node:url';
const root='/Users/gavinbintz/Documents/Codex/2026-10-02/task';
const scope=join(root,'comparison/native-metal-hevc-live-20261005');
const helper=join(root,'checkpoint/native_bridge_fixture.py');
const cpuRecorders={metal:['/Users/gavinbintz/.codex/worktrees/gpu-hevc/helios/packages/portable/dist/gpu.js','98ca35388bf4def80569dd4a9cd1577150e7398b5f1b06711487c1d6fc275089'],vulkan:['/Users/gavinbintz/.codex/worktrees/gpu-vulkan-interop/helios/packages/portable/dist/gpu.js','235b8b57fe8e45b543c9deefb91f38ec5febe5f8b79e4abc45931ec41a5d55e2']};
const cpuProfileSha='2a8a5b25732b28096c9acdcadaca5b3e99ec2a943d24bef5350bab8b32049a8c';
const digest=b=>createHash('sha256').update(b).digest('hex');
const file=resolve(process.argv[2]);
if((await stat(file)).size>1024*1024)throw Error('SPEC_CAP');
const s=JSON.parse(await readFile(file,'utf8'));
const cpu=false;
let child,closed=false,helperStderr='',stopPromise,shutdownPromise;const tasks=[];
process.stdout.on('error',()=>{});
async function stop(){
 return stopPromise??=(async()=>{
 // Cancel a blocked raw forwarder before waiting for all stream tasks.
 if(child){child.stdout.destroy(Error('BRIDGE_CANCELLED'));process.stdout.destroy(Error('BRIDGE_CANCELLED'));}
 if(child&&!closed){child.kill('SIGTERM');await Promise.race([once(child,'close'),new Promise(r=>setTimeout(r,500))]);if(!closed){child.kill('SIGKILL');await once(child,'close');}}
 await Promise.allSettled(tasks);
 })();
}
async function shutdownReceipt(reason){
 return shutdownPromise??=(async()=>{
 if(child){const tmp=join(dirname(file),'helper-shutdown.pending.json');await writeFile(tmp,JSON.stringify({reason,helperPid:child.pid,helperExit:child.exitCode,helperSignal:child.signalCode,helperWaitCompleted:closed,GPUExecuted:null,helperAttempted:true,executionClass:s.executionClass}),{flag:'wx'});await link(tmp,join(dirname(file),'HELPER-SHUTDOWN.json'));}
 })();
}
process.once('SIGTERM',()=>{(async()=>{await stop();await shutdownReceipt('SUPERVISOR_SIGTERM');process.exit(143);})().catch(e=>{console.error(String(e));process.exit(1);});});
try{
 if(s.executionClass!=='native-live-unqualified'||s.codec!=='hevc'||s.backend!=='metal'||s.protocol!==7)throw Error('LIVE_METAL_HEVC_ONLY');
 const bounded=s.variant==='bounded36',large=s.variant==='circles4k300';
 if(!bounded&&!large)throw Error('LIVE_PRESET');
 const control=['positive-nv12','positive-rgba'].includes(s.mode);
 if(s.frames!==(control?3:bounded?36:300)||s.width!==(bounded?256:3840)||s.height!==(bounded?128:2160)||s.fpsNum!==30||s.fpsDen!==1||s.bitrate!==300000000)throw Error('LIVE_PRESET_OVERRIDE');
 if(s.recorderModule!==cpuRecorders.metal[0]||digest(await readFile(s.recorderModule))!==cpuRecorders.metal[1])throw Error('RECORDER_BINDING');
 if(s.sceneModule!==join(root,'checkpoint',bounded?'live_hevc_scene.mjs':'circles-scene.mts'))throw Error('SCENE_BINDING');
 if(large){const g=JSON.parse(await readFile(join(scope,'BOUNDED-ACCEPTANCE.json'),'utf8'));if(g.status!=='qualified-bounded-live-metal-hevc'||g.GPUExecuted!==true||g.hardwareQualified!==true||g.driver.sha256!==digest(await readFile(new URL(import.meta.url)))||g.helper.sha256!=='9c2b3654ce681d9764643214a745878b8fecb72ed9fcd69f3aea7f0fa709d9ae')throw Error('BOUNDED_LIVE_GATE');}

 if(s.realDeviceAccepted!==false||s.hardwareQualified!==false)throw Error('FIXTURE_CANNOT_AUTHORIZE_HARDWARE');
 if(s.frames<1||s.frames>300||!Number.isInteger(s.frames)||s.sourceStart!==3||![256,3840].includes(s.width)||![128,2160].includes(s.height)||s.fpsNum!==30||s.fpsDen!==1)throw Error('FRAME_ENVELOPE');
 if(!['h264','hevc'].includes(s.codec)||!['metal','vulkan'].includes(s.backend)||s.protocol!==(s.backend==='vulkan'?9:s.codec==='hevc'?7:5))throw Error('CODEC_PROTOCOL');
 if(cpu&&(s.sceneModule!==join(root,'checkpoint/native_bridge_scene_fixture.mjs')||s.recorderModule!==cpuRecorders[s.backend][0]||digest(await readFile(s.recorderModule))!==cpuRecorders[s.backend][1]))throw Error('PINNED_CPU_MODULES_ONLY');
 if(cpu&&(s.nativeCommand[0]!==s.python||s.nativeCommand[1]!==helper||s.nativeCommand.length!==14))throw Error('PINNED_FIXTURE_HELPER_ONLY');
 const a=s.nativeCommand.slice(cpu?2:1);
 if(!['encode-binary','reference-binary','raster-binary'].includes(a[0]))throw Error('NATIVE_MODE');
 if(s.nativeCommand.length!==13||s.nativeCommand[0]!==s.helper.path||s.helper.path!=='/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94/hevc-evidence/helper-candidate-01'||s.helper.sha256!=='9c2b3654ce681d9764643214a745878b8fecb72ed9fcd69f3aea7f0fa709d9ae')throw Error('FROZEN_NATIVE_HELPER_ONLY');
 if(a[1]!==String(s.width)||a[2]!==String(s.height)||a[3]!==String(s.fpsNum)||a[4]!==String(s.fpsDen)||a[5]!==String(s.bitrate)||a[9]!=='30'||a[10]!=='3'||a[11]!==s.codec)throw Error('NATIVE_ABI');
 const dir=dirname(file);
 if(s.fault&&!['device','encoder','bitrate','format'].includes(s.fault))throw Error('FAULT_ENVELOPE');
 if(a[0]!==(['reference','positive-nv12'].includes(s.mode)?'reference-binary':s.mode==='positive-rgba'?'raster-binary':'encode-binary')||a[6]!==join(dir,'elementary.h265')||a[7]!==join(dir,'gpu-transfer.jsonl')||a[8]!=='')throw Error('LIVE_ABI_SCOPE');
 if(!dir.startsWith(join(scope,'attempts/'))||s.attemptDirectory!==dir||await realpath(dir)!==dir)throw Error('OUTPUT_SCOPE');
 if(cpu&&(a[6]!==join(dir,s.codec==='hevc'?'elementary.h265':'elementary.h264')||a[7]!==join(dir,'gpu-transfer-not-actual.jsonl')||a[8]!==''))throw Error('FIXTURE_ABI_OUTPUT_SCOPE');
 for(const p of s.pins){const bytes=await readFile(p.path);if(bytes.length!==p.bytes||digest(bytes)!==p.sha256)throw Error('PIN_MISMATCH');}
 for(const path of [...(cpu?[helper,s.python,s.rawFixture.path]:[s.helper.path]),s.recorderModule,s.sceneModule,s.font.path])if(!s.pins.some(p=>p.path===path))throw Error('MISSING_PIN');
 if(s.profile){
  if(cpu){
   if(s.profile.kind!=='CPU-only-constructor'||s.profile.libraryPin.path!==join(scope,'fixtures/cpu_profile.dylib')||s.profile.libraryPin.sha256!==cpuProfileSha||s.profile.log!==join(dir,'cpu-profile.jsonl'))throw Error('NO_NATIVE_PROFILE_IN_FIXTURE');
   if(s.profile.libraryPin.sha256!==s.trustedCpuProfilePin.sha256||s.profile.libraryPin.path!==s.trustedCpuProfilePin.path)throw Error('UNTRUSTED_CPU_PROFILE');
  }else if(!s.profile.libraryPin||!s.profile.libraryPin.path.startsWith(dir+'/')||s.profile.log!==join(dir,'interposer.jsonl')||!s.pins.some(p=>p.path===s.profile.libraryPin.path&&p.sha256===s.profile.libraryPin.sha256))throw Error('NATIVE_PROFILE_FRESH_PIN_REQUIRED');
 }
 const build=JSON.parse(await readFile(join(dir,'PROFILE-BUILD.json'),'utf8'));if(build.profileSource.sha256!=='6ed403ae9f17384fb2ac47a6323b7f71a129410a380b7ff573eaef86dadfd4be'||build.libraryPin.sha256!==s.profile.libraryPin.sha256||s.profile.libraryPin.path!==join(dir,'transfer-interposer.dylib')||build.log!==join(dir,'interposer.jsonl'))throw Error('LIVE_PROFILE_BUILD');
 if(s.faultLibraryPin&&(s.faultLibraryPin.path!==join(dir,'fault.dylib')||build.faultLibraryPin.sha256!==s.faultLibraryPin.sha256))throw Error('FAULT_LIBRARY_SCOPE');
 const {recordGpuCanvasBinary}=await import(pathToFileURL(s.recorderModule).href);
 const sceneExports=await import(pathToFileURL(s.sceneModule).href);
 const font=await readFile(s.font.path);
 const composition=sceneExports[s.variant==='bounded36'?'createLiveHevcScene':'createCircles'](font);
 const overlay={};
 if(s.profile){overlay.DYLD_INSERT_LIBRARIES=s.profile.libraryPin.path+(s.faultLibraryPin?','+s.faultLibraryPin.path:'');if(cpu)overlay.BRIDGE_CPU_PROFILE_LOG=s.profile.log;}
 // The helper remains in the driver's process group, owned by the Python supervisor.
 child=spawn(s.nativeCommand[0],s.nativeCommand.slice(1),{cwd:root,stdio:['pipe','pipe','pipe'],env:{PATH:'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',...overlay}});
 // A helper may refuse a packet while writes are buffered. Observe stdin errors
 // even when the last write returned true, rather than raising an unhandled event.
 let stdinError;child.stdin.on('error',e=>{stdinError=e;});
 const exit=new Promise((ok,fail)=>{child.on('error',fail);child.on('close',(code,signal)=>{closed=true;code===0?ok({code,signal}):fail(Error(`HELPER_EXIT:${code}/${signal}`));});});tasks.push(exit);
 let stdout='',outBytes=0,rawForwardDrains=0,maxForwardQueue=0;
 const raw=a[0]!=='encode-binary',expectedRaw=s.frames*s.width*s.height*(a[0]==='raster-binary'?4:1.5);
 const err=(async()=>{for await(const b of child.stderr){if(Buffer.byteLength(helperStderr)+b.length>65536)throw Error('HELPER_STDERR_CAP');helperStderr+=b;}})();tasks.push(err);
 const forward=(async()=>{for await(const b of child.stdout){outBytes+=b.length;
  if(raw){if(outBytes>expectedRaw)throw Error('RAW_OUTPUT_CAP');const ready=process.stdout.write(b);maxForwardQueue=Math.max(maxForwardQueue,process.stdout.writableLength);if(!ready){rawForwardDrains++;await once(process.stdout,'drain');}}
  else{if(outBytes>65536)throw Error('HELPER_RECEIPT_CAP');stdout+=b;}
 }})();tasks.push(forward);
 let packetDrainCalls=0,maxPacketQueue=0;
 const feed=(async()=>{
  const write=async b=>{if(stdinError)throw stdinError;const ready=child.stdin.write(b);maxPacketQueue=Math.max(maxPacketQueue,child.stdin.writableLength);if(!ready){packetDrainCalls++;await Promise.race([once(child.stdin,'drain'),exit.then(()=>{throw Error('HELPER_EXIT_BEFORE_FEED_COMPLETE');})]);}if(stdinError)throw stdinError;};
  const header=Buffer.from(JSON.stringify({fonts:{[s.variant==='bounded36'?'pinned':'dm']:font.toString('base64')}})+'\n');await write(header);
  const combined=createHash('sha256').update(header);let capacity=1024;const rows=[];
  for(let ordinal=0;ordinal<s.frames;ordinal++){
   const sourceIndex=s.sourceStart+ordinal;
   const packet=await recordGpuCanvasBinary(composition,sourceIndex,capacity);capacity=packet.length;
   if(packet.length>32*1024*1024||packet.readUInt32LE(0)!==0x35464748||packet.readUInt32LE(4)!==packet.length)throw Error('PACKET_ENVELOPE');
   rows.push({index:ordinal,sourceIndex,packetBytes:packet.length,packetSha256:digest(packet)});combined.update(packet);await write(packet);
  }
  child.stdin.end();return {frameIdentities:rows,headerSha256:digest(header),combinedFeedSha256:combined.digest('hex')};
 })();tasks.push(feed);
 const values=await Promise.all([feed,forward,err,exit]);const fed=values[0];
 const lines=(raw?helperStderr:stdout).trim().split('\n').filter(Boolean);if(lines.length!==1)throw Error('NATIVE_RECEIPT_COUNT');
 const n=JSON.parse(lines[0]);
 if(cpu&&(n.kind!=='BRIDGE_CPU_SYNTHETIC'||n.GPUExecuted!==false))throw Error('FIXTURE_RECEIPT_CANNOT_BE_HARDWARE');
 if(n.protocol!==s.protocol||n.codec!==s.codec||n.transport!=='binary'||n.frames!==s.frames||n.encoderPool!==3||n.gop!==30||n.bitrate!==s.bitrate||n.rasterizer!==`skia-${s.backend}`)throw Error('NATIVE_RECEIPT_CONTRACT');
 if(cpu&&(n.packetHashes.length!==fed.frameIdentities.length||n.packetHashes.some((v,i)=>v!==fed.frameIdentities[i].packetSha256)))throw Error('PACKET_IDENTITY');
 if(raw){if(outBytes!==expectedRaw||n.explicitRawReadbackBytes!==outBytes||n.encoder!=='none'||n.configuredBitrate!==null)throw Error('RAW_BOUNDARY_OR_RECEIPT');}
 else if(n.encoder!=='videotoolbox'||n.hardwareUsed!==true||n.hardwareRequired!==true||n.explicitRawReadbackBytes!==0||n.configuredBitrate!==s.bitrate)throw Error('ENCODE_RECEIPT_CONTRACT');
 if(s.testControl==='reverse-driver-ledger')fed.frameIdentities.reverse();
 const result={status:cpu?'completed-subprocess-fixture':'completed-native-unqualified',executionClass:s.executionClass,hardwareQualified:false,realDeviceAccepted:false,GPUExecuted:!cpu,[cpu?'simulatedNativeContract':'nativeUnqualifiedContract']:n,...fed,rawBytes:raw?outBytes:0,packetDrainCalls,maxPacketQueue,rawForwardDrains,maxForwardQueue,helperPid:child.pid,helperExit:values[3],helperWaitCompleted:true,sourceIndexScope:cpu?'commands use actual draw indices3..; raw/coded payload is retained fixture ordinal data, not rendered by the helper':'actual drawn source indices and direct stdout ordinal binding; independent GPU/quality acceptance still required'};
 const tmp=join(dir,'producer-receipt.pending.json');await writeFile(tmp,JSON.stringify(result,null,2),{flag:'wx'});await link(tmp,join(dir,'PRODUCER.json'));
}catch(e){await stop();try{await shutdownReceipt(String(e));}catch(x){if(x.code!=='EEXIST')throw x;}if(child)console.error(JSON.stringify({helperPid:child.pid,helperExit:child.exitCode,helperSignal:child.signalCode,helperWaitCompleted:closed,helperStderr}));console.error(String(e));process.exitCode=1;}
