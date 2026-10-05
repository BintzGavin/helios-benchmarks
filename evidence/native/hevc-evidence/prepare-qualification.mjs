import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const root = '/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94/hevc-evidence';
const worktree = '/Users/gavinbintz/.codex/worktrees/gpu-hevc/helios';
const { recordGpuCanvasBinary, renderGpuCanvasVideo } = await import(worktree + '/packages/portable/dist/gpu.js');
const font = await readFile(worktree + '/packages/portable/tests/fixtures/fonts/NotoSans-Regular.ttf');
const scene = {
  width: 256, height: 128, fps: { num: 30000, den: 1001 }, frameCount: 300,
  fonts: { pinned: font }, background: '#000000',
  draw(ctx, { index }) {
    for (const [color, x, y] of [['#ff0000', 0, 0], ['#00ff00', 128, 0], ['#0000ff', 0, 64], ['#ffffff', 128, 64]]) {
      ctx.fillStyle = color; ctx.fillRect(x, y, 128, 64);
    }
    ctx.save(); ctx.translate(128, 64); ctx.rotate(index / 300);
    ctx.fillStyle = '#ffff00'; ctx.beginPath(); ctx.arc(24 * Math.sin(index / 11), 0, 15, 0, Math.PI * 2); ctx.fill(); ctx.restore();
    ctx.fillStyle = '#000000'; ctx.font = '15px pinned'; ctx.fillText('HEVC ' + String(index).padStart(3, '0'), 150, 110);
  },
};
await mkdir(root + '/qualification-01', { recursive: true });
const directory = root + '/qualification-01';
if (process.argv[2] === 'prepare') {
  const header = Buffer.from(JSON.stringify({ fonts: { pinned: font.toString('base64') } }) + '\n');
  const packets = [];
  for (let index = 0; index < 300; index++) packets.push(await recordGpuCanvasBinary(scene, index));
  await writeFile(directory + '/frames-300.bin', Buffer.concat([header, ...packets]));
  await writeFile(directory + '/frames-3.bin', Buffer.concat([header, packets[0], packets[150], packets[299]]));
  await writeFile(directory + '/CONFIG.json', JSON.stringify({ scene: 'HEVC-color-text-circle-contract', width: 256, height: 128, fps: scene.fps, frames: 300, sourceFrames: '0..299', codec: 'hevc', bitrate: 20000000, gop: 30, encoderPool: 3, transport: 'binary', fontSha256: createHash('sha256').update(font).digest('hex'), floors: { ssimY: 0.995, psnrY: 40, psnrU: 35, psnrV: 35 }, benchmarkTiming: false, zeroCopyProved: false }, null, 2));
} else if (process.argv[2] === 'encode') {
  await renderGpuCanvasVideo(scene, directory + '/video.mp4', { codec: 'hevc', bitrate: 20000000, gop: 30, encoderPool: 3, transport: 'binary', executable: directory + '/profiled-helper', trace: directory + '/hardware-trace.jsonl', ffmpeg: '/opt/homebrew/bin/ffmpeg', ffprobe: '/opt/homebrew/bin/ffprobe' });
} else if (process.argv[2] === 'format-fault') {
  const path = directory + '/fault-preserved.mp4';
  await writeFile(path, 'preserved destination');
  let rejected = false;
  try { await renderGpuCanvasVideo({ ...scene, frameCount: 3 }, path, { codec: 'hevc', executable: directory + '/format-fault-helper', ffmpeg: '/opt/homebrew/bin/ffmpeg', ffprobe: '/opt/homebrew/bin/ffprobe' }); }
  catch (error) { rejected = error.code === 'MEDIA_PROCESS'; }
  if (!rejected || (await readFile(path, 'utf8')) !== 'preserved destination') throw new Error('Format fault did not fail atomically');
  await writeFile(directory + '/format-fault-api.json', JSON.stringify({ rejected: true, destinationPreserved: true, softwareFallback: false }));
} else throw new Error('Expected prepare, encode or format-fault');
