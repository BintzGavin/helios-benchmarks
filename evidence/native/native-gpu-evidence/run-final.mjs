import { spawn } from 'node:child_process';
import { open, writeFile, readFile, appendFile, copyFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const root = '/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios';
const evidence = '/private/tmp/helios-gpu-evidence';
const node = '/opt/homebrew/bin/node';
const tsx = '/Users/gavinbintz/Developer/helios/node_modules/tsx/dist/cli.mjs';
const font = '/Users/gavinbintz/Documents/Codex/2026-10-02/task/preparation/unpacked/helios-gpu-comparison-prep/DM-Sans.ttf';
const common = ['--font', font, '--ffmpeg', '/opt/homebrew/bin/ffmpeg', '--ffprobe', '/opt/homebrew/bin/ffprobe'];
async function run(name, script, args) {
  const stdout = await open(`${evidence}/${name}.stdout.log`, 'wx');
  const stderr = await open(`${evidence}/${name}.stderr.log`, 'wx');
  const startedAt = new Date().toISOString(), started = performance.now();
  const child = spawn('/usr/bin/env', ['PATH=/opt/homebrew/bin:/usr/bin:/bin', '/usr/bin/time', '-l', node, tsx, `${root}/packages/portable/benchmarks/${script}`, ...args], { cwd: root, stdio: ['ignore', stdout.fd, stderr.fd] });
  const result = await new Promise((resolve, reject) => { child.once('error', reject); child.once('close', (exit, signal) => resolve({ exit, signal })); });
  await stdout.close(); await stderr.close();
  const receipt = { name, startedAt, finishedAt: new Date().toISOString(), wallMs: performance.now() - started, ...result };
  await writeFile(`${evidence}/${name}.process.json`, JSON.stringify(receipt, null, 2), { flag: 'wx' });
  await appendFile(`${evidence}/final-run-journal.jsonl`, JSON.stringify(receipt) + '\n');
  console.log(JSON.stringify(receipt));
  if (result.exit !== 0) throw new Error(`${name} failed; inspect retained receipts`);
}
const native = (name, mode, purpose, extra = []) => run(name, 'gpu.ts', ['--out', `${evidence}/${name}`, '--mode', mode, '--purpose', purpose, '--bitrate', '180000000', ...common, ...extra]);
const chrome = (name, purpose) => run(name, 'gpu-chromium.ts', ['--out', `${evidence}/${name}`, '--mode', 'software', '--purpose', purpose, '--chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ...common, '--qualification', `${evidence}/chromium-screen-software-11-01/quality.json`]);
const quality = (name, reference) => run(`${name}-quality`, 'gpu-quality.ts', ['--attempt', `${evidence}/${name}`, '--reference', `${evidence}/${reference}`, '--ffmpeg', '/opt/homebrew/bin/ffmpeg', '--ffprobe', '/opt/homebrew/bin/ffprobe']);
if (process.argv[2] === 'qualify') {
  const executable = `${root}/packages/portable/native/target/release/helios-gpu`;
  const sha256 = createHash('sha256').update(await readFile(executable)).digest('hex');
  await copyFile(executable, `${evidence}/native-${sha256}`);
  await writeFile(`${evidence}/frozen-release.json`, JSON.stringify({ sha256, executable, frozenAt: new Date().toISOString() }, null, 2), { flag: 'wx' });
  await native('final-reference-hardware', 'reference-hardware', 'reference');
  await native('final-reference-software', 'reference-software', 'reference');
  await native('final-screen-hardware-180m', 'hardware', 'screen');
  await quality('final-screen-hardware-180m', 'final-reference-hardware');
  await native('final-screen-software-11', 'software', 'screen');
  await quality('final-screen-software-11', 'final-reference-software');
} else if (process.argv[2] === 'rounds') {
  await native('final-warmup-software', 'software', 'warmup');
  await chrome('final-warmup-chromium', 'warmup');
  await native('final-warmup-hardware', 'hardware', 'warmup');
  for (const round of [1, 2, 3, 4]) {
    const nativeName = `round-${round}-native-software`, chromeName = `round-${round}-chromium`;
    const nativeRun = () => native(nativeName, 'software', 'timed', ['--qualification', `${evidence}/final-screen-software-11/quality.json`]);
    if (round === 2 || round === 3) { await chrome(chromeName, 'timed'); await nativeRun(); }
    else { await nativeRun(); await chrome(chromeName, 'timed'); }
    await quality(nativeName, 'final-reference-software');
    await quality(chromeName, 'chromium-reference-software-01');
    const hardwareName = `round-${round}-native-hardware`;
    await native(hardwareName, 'hardware', 'timed', ['--qualification', `${evidence}/final-screen-hardware-180m/quality.json`]);
    await quality(hardwareName, 'final-reference-hardware');
  }
} else if (process.argv[2] === 'reference-color-fix') {
  await native('final-reference-hardware-tagged', 'reference-hardware', 'reference');
} else if (process.argv[2] === 'remaining-pair') {
  await native('round-4-native-software', 'software', 'timed', ['--qualification', `${evidence}/final-screen-software-11/quality.json`]);
  await chrome('round-4-chromium', 'timed');
  await quality('round-4-native-software', 'final-reference-software');
  await quality('round-4-chromium', 'chromium-reference-software-01');
  await native('round-4-native-hardware', 'hardware', 'timed', ['--qualification', `${evidence}/final-screen-hardware-180m/quality.json`]);
  await quality('round-4-native-hardware', 'final-reference-hardware-tagged');
} else throw new Error('Unknown final stage');
