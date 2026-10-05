import {createCircles} from './circles-scene.mts';
import {recordGpuCanvas} from '/Users/gavinbintz/.codex/worktrees/gpu-circles-gop/helios/packages/portable/src/gpu.ts';
import {readFile,writeFile} from 'node:fs/promises';
const font=await readFile('preparation/unpacked/helios-gpu-comparison-prep/DM-Sans.ttf');
const c=createCircles(font),records=[];
for (const frame of [3,4,302]) {
 const start=performance.now();const commands=await recordGpuCanvas(c,frame);const recorded=performance.now();
 const json=JSON.stringify(commands);const serialized=performance.now();
 records.push({frame,commands:commands.commands.length,bytes:Buffer.byteLength(json),recordMs:recorded-start,stringifyMs:serialized-recorded,totalMs:serialized-start});
}
const report={scope:'excluded CPU command preparation probe; no GPU render, no throughput claim; one cold and two subsequent frames',records};
await writeFile('comparison/circles-recording-profile.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
