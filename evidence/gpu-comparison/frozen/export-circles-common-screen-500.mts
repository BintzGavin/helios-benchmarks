/** Task-owned matched TextGrid exporter. Decoded delivery checks belong to run_matrix.py. */
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { once } from 'node:events';
import { pipeline } from 'node:stream/promises';
import { pathToFileURL } from 'node:url';

const root = '/Users/gavinbintz/Documents/Codex/2026-10-02/task';
const helios = '/Users/gavinbintz/.codex/worktrees/gpu-bitrate-budget/helios';
const { createCircles } = await import(pathToFileURL(join(root,'checkpoint/circles-scene.mts')).href);
const { recordGpuCanvas } = await import(pathToFileURL(join(helios,'packages/portable/src/gpu.ts')).href);
const { videoEncoderArgs } = await import(pathToFileURL(join(helios,'packages/portable/src/render.ts')).href);
const [engine, mode, destination, frameArgument='300', bitrateArgument='100000000'] = process.argv.slice(2);
if (!['H','F'].includes(engine) || !['software','reference-software','hardware','reference-hardware'].includes(mode) || !destination) throw new Error('Usage H|F software|reference-software|hardware|reference-hardware OUTPUT [FRAMES] [BITRATE]');
const frames=Number(frameArgument), bitrate=Number(bitrateArgument);
if (!Number.isInteger(frames)||frames<1||frames>300||!Number.isInteger(bitrate)||bitrate<100000||bitrate>1000000000) throw new Error('Invalid range/bitrate');
const fontPath=join(root,'preparation/unpacked/helios-gpu-comparison-prep/DM-Sans.ttf'), font=await readFile(fontPath);
const sha=(bytes:Buffer)=>createHash('sha256').update(bytes).digest('hex');
if (sha(font)!=='9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5') throw new Error('Font identity changed');
const executable=engine==='H'?join(helios,'packages/portable/native/target/release/helios-gpu'):join(root,'build/fframes-current/release/circles-common-gpu-adapter');
const output=resolve(destination), directory=dirname(output);
await mkdir(directory,{recursive:true});
const attempt:any={engine,mode,frames,bitrate,sourceFrameRange:[3,3+frames],gop:30,scene:'Circles99kText1k',fontSha256:sha(font),executableSha256:sha(await readFile(executable)),commands:[],status:'running',zeroCopyProved:false,rawReadback:mode!=='hardware',commonConverterLane:true,extraGpuTextureCopy:engine==='F',serialRasterizer:true,verificationOwner:'run_matrix.py; one full post-export decode plus independent cadence/fidelity gates',startedAt:new Date().toISOString()};
const receiptPath=join(directory,'adapter.json');
await writeFile(receiptPath,JSON.stringify(attempt,null,2),{flag:'wx'});
const started=performance.now();
function worker(command:string,args:string[],suffix:string,env=process.env) {
  attempt.commands.push({command,args});
  const p=spawn(command,args,{env,stdio:['pipe','pipe','pipe']});
  let err='',out=''; p.stderr.on('data',x=>{err+=x});
  const done=new Promise<void>((ok,fail)=>{p.on('error',fail);p.on('close',(code,signal)=>{attempt[suffix]={code,signal,stderr:err};code===0?ok():fail(new Error(`${suffix} failed ${code}/${signal}: ${err.slice(-2000)}`))})});
  return {p,done};
}
try {
  const hardware=mode==='hardware', reference=mode.startsWith('reference-');
  const plan={width:3840,height:2160,fps:{num:30,den:1}};
  const software=videoEncoderArgs(plan,frames,output,'rgba',{preset:'medium',crf:11,threads:2,gop:30,bframes:0,sceneCut:false,colorConversion:'srgb-bt709'});
  let encoding=software;
  if(reference) {
    const filter=mode==='reference-hardware'?'setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709,format=yuv420p':software[software.indexOf('-vf')+1];
    const tags=['-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709'];
    encoding=['-hide_banner','-loglevel','error','-y','-filter_threads','1','-f','rawvideo','-pix_fmt',mode==='reference-hardware'?'nv12':'rgba','-s','3840x2160','-r','30','-i','pipe:0','-vf',filter,'-c:v','ffv1','-level','3','-threads','2',...tags,'-color_range','tv','-frames:v',String(frames),output];
  }
  const elementary=join(directory,'elementary.h264');
  const args=engine==='H'?[hardware?'encode':mode==='reference-hardware'?'reference':'raster','3840','2160','30','1',String(bitrate),hardware?elementary:'/unused',join(directory,'transfer.jsonl'),'', '30', '3']:[hardware?'hardware':mode==='reference-hardware'?'reference':'unsupported-software',output,join(root,'comparison/font'),String(frames),String(bitrate)];
  const producer=worker(executable,args,'producer',engine==='F'&&hardware?{...process.env,COMPARISON_REQUIRE_HARDWARE_FRAMES:'1'}:process.env);
  const feed=engine==='H'?(async()=>{
    const send=async(message:unknown)=>{if(!producer.p.stdin.write(JSON.stringify(message)+'\n')) await Promise.race([once(producer.p.stdin,'drain'),producer.done.then(()=>{throw new Error('Producer exited before input finished')})]);};
    await send({fonts:{dm:font.toString('base64')}});
    const composition=createCircles(font);
    for(let index=3;index<frames+3;index++) await send(await recordGpuCanvas(composition,index));
    producer.p.stdin.end();
  })():(producer.p.stdin.end(),Promise.resolve());
  if(hardware) {
    let stdout='';producer.p.stdout.on('data',x=>stdout+=x);
    await Promise.all([feed,producer.done]);attempt.nativeReceipt=JSON.parse(stdout.trim());
    if(engine==='H'||engine==='F') {
      if(attempt.nativeReceipt.frames!==frames||attempt.nativeReceipt.encoder!==(engine==='H'?'videotoolbox':'requiredVideoToolboxH264')||attempt.nativeReceipt.explicitRawReadbackBytes!==0) throw new Error('Native receipt mismatch');
      const mux=worker('/opt/homebrew/bin/ffmpeg',['-v','error','-y','-r','30','-f','h264','-i',engine==='H'?elementary:output.replace(/\.[^.]+$/,'.h264'),'-c:v','copy','-an','-video_track_timescale','30','-movflags','+faststart',output],'mux');mux.p.stdin.end();mux.p.stdout.resume();await mux.done;
    } else throw new Error('Unsupported common adapter engine');
  } else {
    const encoder=worker('/opt/homebrew/bin/ffmpeg',encoding,'encoder');encoder.p.stdout.resume();
    try{await Promise.all([feed,pipeline(producer.p.stdout,encoder.p.stdin),producer.done,encoder.done]);}
    catch(e){producer.p.kill('SIGKILL');encoder.p.kill('SIGKILL');await Promise.allSettled([feed,producer.done,encoder.done]);throw e;}
  }
  attempt.status='complete';attempt.exportMs=performance.now()-started;
} catch(error) {attempt.status='failed';attempt.error=String(error);process.exitCode=1;}
finally {attempt.finishedAt=new Date().toISOString();await writeFile(receiptPath,JSON.stringify(attempt,null,2));console.log(JSON.stringify(attempt));}
