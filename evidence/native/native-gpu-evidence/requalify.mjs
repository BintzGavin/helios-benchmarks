import { spawn } from 'node:child_process';
import { open, writeFile } from 'node:fs/promises';
const base = '/private/tmp/helios-gpu-evidence', root = '/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios';
async function run(name, script, args) {
  const stdout = await open(`${base}/${name}.stdout.log`, 'wx'), stderr = await open(`${base}/${name}.stderr.log`, 'wx');
  const start = performance.now(), startedAt = new Date().toISOString();
  const child = spawn('/usr/bin/env', ['PATH=/opt/homebrew/bin:/usr/bin:/bin', '/usr/bin/time', '-l', '/opt/homebrew/bin/node', '/Users/gavinbintz/Developer/helios/node_modules/tsx/dist/cli.mjs', script, ...args], { cwd: root, stdio: ['ignore', stdout.fd, stderr.fd] });
  const [exit, signal] = await new Promise(resolve => child.once('close', (...result) => resolve(result)));
  await stdout.close(); await stderr.close();
  await writeFile(`${base}/${name}.process.json`, JSON.stringify({ exit, signal, startedAt, finishedAt: new Date().toISOString(), wallMs: performance.now() - start }, null, 2), { flag: 'wx' });
  console.log(JSON.stringify({ name, exit }));
  if (exit !== 0) throw Error(`${name} failed`);
}
const quality = (name, reference, receipt) => run(`${name}-${receipt}`, `${root}/packages/portable/benchmarks/gpu-quality.ts`, ['--attempt', `${base}/${name}`, '--reference', `${base}/${reference}`, '--receipt', receipt, '--ffmpeg', '/opt/homebrew/bin/ffmpeg', '--ffprobe', '/opt/homebrew/bin/ffprobe']);
if (process.argv[2] === 'saved') {
  await run('direct-oracle-full', `${base}/direct-oracle.mts`, []);
  for (const round of [1, 2, 3]) await quality(`round-${round}-native-hardware`, 'final-reference-hardware-tagged', 'quality-corrected');
  for (const round of [1, 2]) {
    await quality(`round-${round}-native-software`, 'final-reference-software', 'quality-strict');
    await quality(`round-${round}-chromium`, 'chromium-reference-software-01', 'quality-strict');
  }
} else if (process.argv[2] === 'screen') {
  const font = '/Users/gavinbintz/Documents/Codex/2026-10-02/task/preparation/unpacked/helios-gpu-comparison-prep/DM-Sans.ttf';
  for (const bitrate of (process.argv[3] ? process.argv[3].split(',').map(Number) : [40000000, 20000000])) {
    const name = `corrected-screen-hardware-${bitrate}`;
    await run(name, `${root}/packages/portable/benchmarks/gpu.ts`, ['--out', `${base}/${name}`, '--mode', 'hardware', '--purpose', 'screen', '--bitrate', String(bitrate), '--font', font, '--ffmpeg', '/opt/homebrew/bin/ffmpeg', '--ffprobe', '/opt/homebrew/bin/ffprobe']);
    // Preserve a failing quality screen but continue to examine both requested targets.
    try { await quality(name, 'final-reference-hardware-tagged', 'quality'); } catch (e) { console.log(e.message); }
  }
} else if (process.argv[2] === 'hardware100') {
  const font = '/Users/gavinbintz/Documents/Codex/2026-10-02/task/preparation/unpacked/helios-gpu-comparison-prep/DM-Sans.ttf';
  for (const round of ['warmup', '1', '2', '3', '4']) {
    const name = `hardware100-${round}`;
    await run(name, `${root}/packages/portable/benchmarks/gpu.ts`, ['--out', `${base}/${name}`, '--mode', 'hardware', '--purpose', round === 'warmup' ? 'warmup' : 'timed', '--bitrate', '100000000', '--qualification', `${base}/corrected-screen-hardware-100000000/quality.json`, '--font', font, '--ffmpeg', '/opt/homebrew/bin/ffmpeg', '--ffprobe', '/opt/homebrew/bin/ffprobe']);
    if (round !== 'warmup') await quality(name, 'final-reference-hardware-tagged', 'quality');
  }
} else throw Error('Unknown requalification stage');
