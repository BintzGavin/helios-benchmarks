import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { once } from 'node:events';
import { pathToFileURL } from 'node:url';
const study='/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/remotion-setup';
const project=join(study,'project'), bundle=join(study,'bundle');
const require=createRequire(join(project,'package.json'));
const {openBrowser,selectComposition,renderFrames}=require('@remotion/renderer');
const helios='/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios';
const {videoEncoderArgs}=await import(pathToFileURL(join(helios,'packages/portable/src/render.ts')).href);
const [mode,destination,frameArgument='300']=process.argv.slice(2), frames=Number(frameArgument);
if(!['software','reference-software'].includes(mode)||!destination||!Number.isInteger(frames)||frames<1||frames>300) throw new Error('Usage software|reference-software OUTPUT [FRAMES]');
const output=resolve(destination),directory=dirname(output);await mkdir(directory,{recursive:true});
const concurrency=Number(process.env.COMPARISON_CONCURRENCY??'1');
if(!Number.isInteger(concurrency)||concurrency<1||concurrency>16) throw new Error('Invalid concurrency');
const font=await readFile(join(project,'public/DMSans-Regular.ttf'));
const fontSha256=createHash('sha256').update(font).digest('hex');
if(fontSha256!=='9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5') throw new Error('Font identity mismatch');
const browserExecutable='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const attempt:any={engine:'R',mode,frames,fontSha256,remotion:'4.0.529',browserExecutable,concurrency,rawReadback:true,gpuRasterProved:false,zeroCopyProved:false,transport:'PNG/CDP buffer with ordered pipe, no raw intermediate disk',status:'running',startedAt:new Date().toISOString()};
const receipt=join(directory,'adapter.json');await writeFile(receipt,JSON.stringify(attempt,null,2),{flag:'wx'});
let browser,encoder;const started=performance.now();
try {
  const chromiumOptions={gl:'angle',headless:true};
  browser=await openBrowser('chrome',{browserExecutable,chromeMode:'chrome-for-testing',chromiumOptions,logLevel:'warn'});
  const info=await browser.connection.send('SystemInfo.getInfo');
  const gpu=info.value.gpu;
  attempt.gpuInventory={devices:gpu.devices?.map((d:any)=>({vendorId:d.vendorId,deviceId:d.deviceId,vendorString:d.vendorString,deviceString:d.deviceString})),featureStatus:gpu.featureStatus,glRenderer:gpu.auxAttributes?.glRenderer};
  if(!/Apple M3 Pro/.test(attempt.gpuInventory.glRenderer??'')) throw new Error('Expected physical Metal device absent; no software GPU result accepted');
  const shared={serveUrl:bundle,inputProps:{},puppeteerInstance:browser,browserExecutable,chromeMode:'chrome-for-testing',chromiumOptions,logLevel:'warn'};
  let traceDone:Promise<any>|undefined;
  if(process.env.COMPARISON_PROFILE==='1') {
    attempt.excludedProfile=true;
    traceDone=new Promise(ok=>browser.connection.once('Tracing.tracingComplete',ok));
    await browser.connection.send('Tracing.start',{categories:'gpu,cc,blink,disabled-by-default-skia.gpu,disabled-by-default-gpu.service,disabled-by-default-cc.debug',transferMode:'ReturnAsStream'});
  }
  const composition=await selectComposition({...shared,id:'TextGrid'});
  if(composition.width!==1920||composition.height!==1080||composition.fps!==30||composition.durationInFrames!==300) throw new Error('Fixture geometry mismatch');
  const software=videoEncoderArgs({width:1920,height:1080,fps:{num:30,den:1}},frames,output,'png',{preset:'medium',crf:11,threads:2,gop:90,bframes:0,sceneCut:false,colorConversion:'srgb-bt709'});
  const args=mode==='reference-software'?['-v','error','-y','-filter_threads','1','-f','image2pipe','-c:v','png','-r','30','-i','pipe:0','-vf',software[software.indexOf('-vf')+1],'-c:v','ffv1','-level','3','-threads','2','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-color_range','tv','-frames:v',String(frames),output]:software;
  attempt.encoderCommand={executable:'/opt/homebrew/bin/ffmpeg',args};
  encoder=spawn('/opt/homebrew/bin/ffmpeg',args,{stdio:['pipe','ignore','pipe']});let stderr='';encoder.stderr.on('data',x=>stderr+=x);
  const done=new Promise<void>((ok,fail)=>{encoder.on('error',fail);encoder.on('close',(code,signal)=>{attempt.encoderExit={code,signal,stderr};code===0?ok():fail(new Error(`FFmpeg ${code}/${signal}: ${stderr}`))})});
  let next=0,peakPending=0;const pending=new Map<number,Buffer>();let flushing=Promise.resolve();
  await renderFrames({...shared,composition,imageFormat:'png',outputDir:null,frameRange:[0,frames-1],muted:true,concurrency,onStart:(data:any)=>{attempt.renderStart=data},onFrameUpdate:()=>{},onFrameBuffer:async(bytes:Buffer,frame:number)=>{
    // Dense TextGrid cannot be an almost-empty screenshot. Retain/reject; never repair a timed frame.
    if(bytes.length<50000) {
      await writeFile(join(directory,`rejected-frame-${frame}.png`),bytes);
      throw new Error(`Blank or incomplete TextGrid screenshot at frame ${frame}: ${bytes.length} PNG bytes`);
    }
    if(pending.has(frame)||frame<next) throw new Error('Duplicate frame callback');
    pending.set(frame,bytes);peakPending=Math.max(peakPending,pending.size);
    flushing=flushing.then(async()=>{while(pending.has(next)){const value=pending.get(next)!;pending.delete(next++);if(!encoder.stdin.write(value)) await Promise.race([once(encoder.stdin,'drain'),done.then(()=>{throw new Error('Encoder ended before frames')})]);}});
    return flushing;
  }});
  await flushing;if(next!==frames||pending.size) throw new Error('Missing ordered frames');encoder.stdin.end();await done;
  attempt.peakPendingFrames=peakPending;
  if(traceDone) {
    await browser.connection.send('Tracing.end');const {stream}=await traceDone;let trace='';
    for(;;){const {value}=await browser.connection.send('IO.read',{handle:stream});trace+=value.data;if(value.eof)break;}
    await browser.connection.send('IO.close',{handle:stream});await writeFile(join(directory,'chrome-trace.json'),trace);
  }
  await browser.close({silent:true});browser=undefined;attempt.status='complete';attempt.exportMs=performance.now()-started;
} catch(error){attempt.status='failed';attempt.error=String(error);encoder?.kill('SIGKILL');process.exitCode=1;}
finally{if(browser) await browser.close({silent:true}).catch(()=>{});attempt.finishedAt=new Date().toISOString();await writeFile(receipt,JSON.stringify(attempt,null,2));console.log(JSON.stringify(attempt));if(attempt.status==='failed')process.exit(1);}
