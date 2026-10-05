import {createCircles} from './circles-scene.mts';
import {recordGpuCanvas,recordGpuCanvasBinary} from '/Users/gavinbintz/.codex/worktrees/gpu-binary-transport/helios/packages/portable/src/gpu.ts';
import {readFile,writeFile} from 'node:fs/promises';
const font=await readFile('preparation/unpacked/helios-gpu-comparison-prep/DM-Sans.ttf');
const scene=createCircles(font),records=[];let capacity=0;
for(const frame of [3,4,302]) {
 const a=performance.now(),jsonCommands=await recordGpuCanvas(scene,frame),b=performance.now(),json=JSON.stringify(jsonCommands),c=performance.now();
 const packet=await recordGpuCanvasBinary(scene,frame,capacity),d=performance.now();capacity=packet.length;
 records.push({frame,commands:jsonCommands.commands.length,jsonBytes:Buffer.byteLength(json),binaryBytes:packet.length,jsonRecordMs:b-a,jsonStringifyMs:c-b,jsonTotalMs:c-a,binaryRecordMs:d-c});
}
const report={scope:'excluded CPU preparation probe on one idle host; no GPU render or export; three frames only, not video throughput',records};
await writeFile('comparison/circles-binary-recording-profile.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
