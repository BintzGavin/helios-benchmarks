import { readFile, writeFile, readdir, stat, copyFile, readlink } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
const evidence = '/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94/native-gpu-evidence';
const root = '/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios';
const json = async path => JSON.parse(await readFile(path, 'utf8'));
const median = values => { const sorted = [...values].sort((a,b) => a-b); return (sorted[1] + sorted[2]) / 2; };
const lanes = [];
for (const lane of ['native-software', 'chromium', 'native-hardware', 'hardware100']) {
  const rounds = [];
  for (const index of [1,2,3,4]) {
    const name = lane === 'hardware100' ? `hardware100-${index}` : `round-${index}-${lane}`;
    const attempt = await json(join(evidence,name,'attempt.json'));
    const qualityName = lane === 'native-hardware' && index < 4 ? 'quality-corrected' : (['native-software','chromium'].includes(lane) && index < 3 ? 'quality-strict' : 'quality');
    const quality = await json(join(evidence,name,qualityName + '.json'));
    if (attempt.status !== 'complete' || !attempt.timingQualified || !quality.passed || quality.frames !== 300) throw Error('Unqualified final timing: ' + name);
    rounds.push({ name, exportSeconds: attempt.renderingMs / 1000, adapterVerificationSeconds: attempt.verificationMs / 1000, fullAdapterSeconds: (attempt.renderingMs + attempt.verificationMs) / 1000, hardwareApiDeliveredSeconds: attempt.apiVerificationMs ? (attempt.renderingMs + attempt.apiVerificationMs) / 1000 : undefined, qualityReceipt: join(evidence,name,qualityName + '.json'), output: join(evidence,name,'video.mp4'), quality });
  }
  const times = rounds.map(x=>x.exportSeconds);
  lanes.push({ lane, rounds, medianExportSeconds: median(times), minimumExportSeconds: Math.min(...times), maximumExportSeconds: Math.max(...times), medianFullAdapterSeconds: median(rounds.map(x=>x.fullAdapterSeconds)), medianHardwareApiDeliveredSeconds: rounds.every(x=>x.hardwareApiDeliveredSeconds) ? median(rounds.map(x=>x.hardwareApiDeliveredSeconds)) : undefined });
}
const native = lanes.find(x=>x.lane==='native-software'), chrome = lanes.find(x=>x.lane==='chromium');
const rows = (await readFile(join(evidence,'full-profile-interposer.jsonl'),'utf8')).trim().split('\n').map(JSON.parse);
const events = Object.fromEntries([...new Set(rows.map(x=>x.event))].map(name=>[name,rows.filter(x=>x.event===name).length]));
const transfer = (await readFile(join(evidence,'full-profile-transfer.jsonl'),'utf8')).trim().split('\n').map(JSON.parse);
for (let frame=0;frame<300;frame++) {
  const frameEvents=transfer.filter(x=>x.frame===frame);
  if (frameEvents.map(x=>x.event).join(',')!=='raster-submitted,conversion-complete,encoder-submit,encoder-callback,surface-recyclable' || !frameEvents[1].sameIOSurfacePlanes || frameEvents[1].gpuEndSeconds<=frameEvents[1].gpuStartSeconds || frameEvents[3].status || frameEvents[3].dropped) throw Error('Bad surface/fence receipt');
}
const binding = await json(join(evidence,'hardware-reference-direct-binding.json'));
if (!binding.passed || binding.frames!==300 || binding.mismatches.length) throw Error('Unbound lossless oracle');
if ((await readFile(join(evidence,'native-software-sei.txt'),'utf8'))!==(await readFile(join(evidence,'chromium-software-sei.txt'),'utf8'))) throw Error('Software encoder SEI mismatch');
const report = { status:'qualified-local-Metal-TextGrid', nativeSourceCommit:'5e0cc9c7ba29d6d30dbd2fadfe1e3dfbcc101872', mergedExternally:'5299bf7f9ad69f54c25b26b0b0774fbcc7d5f723', nativeSha256:'87aec3f3d39db8956490942429e6a865741c04515ad6b98753aaf6599c197a90', evidence, receiptAlias:'/private/tmp/helios-gpu-evidence', host:'Apple M3 Pro,11CPU,14GPU,18GB,macOS26.3', scene:'TextGrid3334 labels,1920x1080,300 frames,30/1fps,no audio,pinned DM Sans', order:'AB/BA/BA/AB, sequential fresh processes after excluded warmups', lanes, matchedSoftwareRatio:chrome.medianExportSeconds/native.medianExportSeconds, matchedSoftwareTimeReduction:1-native.medianExportSeconds/chrome.medianExportSeconds, everyPairNativeFaster:native.rounds.every((x,i)=>x.exportSeconds<chrome.rounds[i].exportSeconds), transferProof:{ frames:300, events, surfaceIds:[...new Set(transfer.filter(x=>x.surfaceId).map(x=>x.surfaceId))], positiveControls:join(evidence,'final-positive-controls.jsonl'), actualMetalCapture:join(evidence,'final-metal.gputrace'), actualChromiumTrace:join(evidence,'chromium-profile-02/chrome-trace.json'), applicationRawDownloadObserved:false, zeroCopyProved:false, limits:'Driver/encoder internals and unhooked operations opaque; pointer getters/buffer contents extents do not prove copied byte counts.' }, oracle:{ originalInvalidated:join(evidence,'final-reference-hardware/reference.mkv'), corrected:join(evidence,'final-reference-hardware-tagged/reference.mkv'), directBinding:join(evidence,'hardware-reference-direct-binding.json'), note:'Original raw-NV12 metadata omission changed pixels. Completed candidate videos and render clocks were preserved; new quality/cadence receipts requalify them.' }, support:'macOS arm64 Metal/H264 only; HEVC,Vulkan,Intel,Windows,GPU media,broad Canvas/99k-circle public API,remote GPU unqualified/unsupported', fullComparison:'Originating comparison chat owns equivalent Helios/fframes/Remotion and the separate4K upstream claim; no win over that claim is asserted.' };
await writeFile(join(evidence,'FINAL-REPORT.json'),JSON.stringify(report,null,2),{flag:'wx'});
for (const name of ['helios-gpu-final-suite-03.log','helios-gpu-final-ts-build-03.log','helios-gpu-final-followup-tests.log','helios-gpu-final-followup-typecheck.log','helios-gpu-final-faults.json','helios-gpu-final-faults.stderr.log','helios-gpu-reference-regression-red.log','helios-gpu-reference-regression-green.log','helios-gpu-release-final.stderr.log','helios-gpu-build.stderr.log']) await copyFile('/private/tmp/'+name,join(evidence,name));
const sourcePaths=['packages/portable/native/src/main.rs','packages/portable/native/metal.mm','packages/portable/native/Cargo.lock','packages/portable/native/Cargo.toml','packages/portable/native/build.rs','packages/portable/src/gpu.ts','packages/portable/benchmarks/gpu.ts','packages/portable/benchmarks/gpu-reference.ts','packages/portable/benchmarks/gpu-quality.ts','packages/portable/benchmarks/gpu-chromium.ts','packages/portable/benchmarks/fframes-textgrid.mjs','packages/portable/benchmarks/profile-gpu.mm'];
const sources=[];for(const path of sourcePaths)sources.push({path,sha256:createHash('sha256').update(await readFile(join(root,path))).digest('hex')});
const chromeVersion=await readlink('/Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Versions/Current');
const chromeFramework=`/Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Versions/${chromeVersion}/Google Chrome Framework`;
const build={sources,chromeVersion,chromeFrameworkSha256:createHash('sha256').update(await readFile(chromeFramework)).digest('hex'),nativeExecutable:root+'/packages/portable/native/target/release/helios-gpu',skiaPrebuiltUrl:'https://github.com/rust-skia/skia-binaries/releases/download/0.91.0/skia-binaries-fab0a5adad3361364d3e-aarch64-apple-darwin-metal-pdf-svg-textlayout-webpd-webpe.tar.gz',skiaMilestone:143,cargoHome:'/private/tmp/helios-gpu-cargo',note:'Official skia-safe/skia-bindings0.91.0, locked Cargo dependency checksums; prebuilt download succeeded. This archive is not ABI-compatible evidence for upstream fframes skia-safe0.153.3.'};
await writeFile(join(evidence,'FINAL-BUILD-PINS.json'),JSON.stringify(build,null,2),{flag:'wx'});
const manifest=[];
async function walk(directory){for(const entry of await readdir(directory,{withFileTypes:true})){const path=join(directory,entry.name);if(entry.name.endsWith('.gputrace')){manifest.push({path,kind:'actual-Metal-capture-directory',contentsNotInspectedByManifest:true});continue;}if(entry.isDirectory())await walk(path);else if(entry.isFile()){const info=await stat(path);manifest.push({path,bytes:info.size,sha256:createHash('sha256').update(await readFile(path)).digest('hex')});}}}
await walk(evidence);
await writeFile(join(evidence,'RECEIPT-MANIFEST.json'),JSON.stringify({evidence,files:manifest,generatedAt:new Date().toISOString(),captureMetadataNotRead:true},null,2),{flag:'wx'});
console.log(JSON.stringify({lanes:lanes.map(({lane,medianExportSeconds,medianHardwareApiDeliveredSeconds})=>({lane,medianExportSeconds,medianHardwareApiDeliveredSeconds})),matchedSoftwareTimeReduction:report.matchedSoftwareTimeReduction,files:manifest.length}));
