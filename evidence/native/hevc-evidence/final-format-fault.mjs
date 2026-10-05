import { writeFile, readFile } from 'node:fs/promises';
const directory = '/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94/hevc-evidence/qualification-01';
const { renderGpuCanvasVideo } = await import('/Users/gavinbintz/.codex/worktrees/gpu-hevc/helios/packages/portable/dist/gpu.js');
const output = directory + '/format-fault-final-preserved.mp4';
await writeFile(output, 'preserved destination');
let rejected = false;
try {
  await renderGpuCanvasVideo({ width: 128, height: 128, fps: { num: 30, den: 1 }, frameCount: 3, draw(ctx) { ctx.fillStyle = '#ff0000'; ctx.fillRect(0, 0, 128, 128); } }, output, { codec: 'hevc', executable: directory + '/format-fault-final-helper', ffmpeg: '/opt/homebrew/bin/ffmpeg', ffprobe: '/opt/homebrew/bin/ffprobe' });
} catch (error) { rejected = error.code === 'MEDIA_PROCESS'; }
if (!rejected || (await readFile(output, 'utf8')) !== 'preserved destination') throw new Error('Final format fault did not preserve destination');
await writeFile(directory + '/format-fault-final-api.json', JSON.stringify({ rejected: true, destinationPreserved: true, softwareFallback: false }));
