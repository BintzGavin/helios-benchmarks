import {spawn} from 'node:child_process';import {once} from 'node:events';import {createHash} from 'node:crypto';import {mkdir,readFile,writeFile} from 'node:fs/promises';import {createCircles} from './circles-scene.mts';
import {recordGpuCanvasBinary} from '/Users/gavinbintz/.codex/worktrees/gpu-binary-transport/helios/packages/portable/src/gpu.ts';
const root='/Users/gavinbintz/Documents/Codex/2026-10-02/task',helper='/Users/gavinbintz/.codex/worktrees/gpu-binary-transport/helios/packages/portable/native/target/release/helios-gpu',dir=root+'/comparison/circles-binary-profile-h';await mkdir(dir,{recursive:true});
const font=await readFile(root+'/preparation/unpacked/helios-gpu-comparison-prep/DM-Sans.ttf'),scene=createCircles(font),receipts=[];
for(const mode of ['encode-binary','reference-binary','raster-binary']){
 const args=[mode,'3840','2160','30','1','500000000',dir+'/profile.h264',dir+'/'+mode+'.transfer.jsonl',mode==='encode-binary'?dir+'/actual-metal.gputrace':'','30','3'];
 const p=spawn(helper,args,{env:{...process.env,DYLD_INSERT_LIBRARIES:root+'/comparison/circles-binary-profile-h.dylib',MTL_CAPTURE_ENABLED:'1'},stdio:['pipe','pipe','pipe']});let stderr='',stdout='',bytes=0;const hash=createHash('sha256');p.stderr.on('data',b=>stderr+=b);p.stdout.on('data',b=>{bytes+=b.length;hash.update(b);if(mode==='encode-binary')stdout+=b;});
 const done=new Promise<void>((ok,fail)=>{p.on('error',fail);p.on('close',code=>code===0?ok():fail(Error(`${mode}:${code}:${stderr}`)))});
 const send=async(b:Buffer|string)=>{if(!p.stdin.write(b))await Promise.race([once(p.stdin,'drain'),done.then(()=>{throw Error('early exit')})]);};await send(JSON.stringify({fonts:{dm:font.toString('base64')}})+'\n');let capacity=1024;
 for(let i=3;i<6;i++){const packet=await recordGpuCanvasBinary(scene,i,capacity);capacity=packet.length;await send(packet);}p.stdin.end();await done;
 receipts.push({mode,args,stdoutBytes:bytes,stdoutSha256:hash.digest('hex'),stdout,stderr,status:'complete',referenceOnlyDownloads:mode!=='encode-binary'});
}
await writeFile(dir+'/process-receipts.json',JSON.stringify(receipts,null,2));console.log(JSON.stringify(receipts.map(x=>({mode:x.mode,status:x.status,stdoutBytes:x.stdoutBytes}))));
