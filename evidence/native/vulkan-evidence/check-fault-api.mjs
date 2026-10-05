import { readFile, writeFile } from 'node:fs/promises';
const { renderGpuCanvasVideo } = await import('/Users/gavinbintz/.codex/worktrees/gpu-vulkan-interop/helios/packages/portable/dist/gpu.js');
const [helper, output, expected] = process.argv.slice(2);
await writeFile(output, 'preserved destination');
let code = null;
try { await renderGpuCanvasVideo({ width:64, height:64, fps:{num:30,den:1}, frameCount:3, draw(ctx) {ctx.fillStyle='#ff0000';ctx.fillRect(0,0,64,64);} }, output, {backend:'vulkan',codec:'hevc',executable:helper,ffmpeg:'/opt/homebrew/bin/ffmpeg',ffprobe:'/opt/homebrew/bin/ffprobe'}); }
catch (error) {code=error.code;}
if (expected === 'pass') { if (code !== null || (await readFile(output)).length < 100) throw new Error('Baseline failed: '+code); }
else if (code !== 'MEDIA_PROCESS' || (await readFile(output,'utf8')) !== 'preserved destination') throw new Error('Expected atomic MEDIA_PROCESS, got '+code);
console.log(JSON.stringify({expected,code,destinationPreserved:expected==='fail',fallback:false}));
