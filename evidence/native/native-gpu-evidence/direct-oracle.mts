import { spawn } from 'node:child_process';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { once } from 'node:events';
import { createTextGrid } from '/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios/packages/portable/benchmarks/fframes-textgrid.mjs';
import { recordGpuCanvas } from '/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios/packages/portable/src/gpu.ts';
const base = '/private/tmp/helios-gpu-evidence/';
const font = await readFile('/Users/gavinbintz/Documents/Codex/2026-10-02/task/preparation/unpacked/helios-gpu-comparison-prep/DM-Sans.ttf');
const composition = createTextGrid(font), width = 1920, height = 1080, y = width * height, bytes = y * 3 / 2;
const child = spawn('/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios/packages/portable/native/target/release/helios-gpu', ['reference', '1920', '1080', '30', '1', '180000000', '/unused', base + 'direct-oracle-transfer.jsonl'], { stdio: ['pipe', 'pipe', 'pipe'] });
let stderr = '', buffer = Buffer.alloc(bytes), cursor = 0;
const hashes: string[] = [];
child.stderr.on('data', b => { stderr += b.toString(); });
const reading = (async () => {
  for await (const chunk of child.stdout) {
    let offset = 0;
    while (offset < chunk.length) {
      const count = Math.min(bytes - cursor, chunk.length - offset);
      chunk.copy(buffer, cursor, offset, offset + count); cursor += count; offset += count;
      if (cursor === bytes) {
        const planar = Buffer.alloc(bytes); buffer.copy(planar, 0, 0, y);
        for (let i = 0; i < y / 4; i++) { planar[y + i] = buffer[y + 2 * i]; planar[y + y / 4 + i] = buffer[y + 2 * i + 1]; }
        hashes.push(createHash('md5').update(planar).digest('hex')); cursor = 0;
      }
    }
  }
})();
const done = once(child, 'close');
const feeding = (async () => {
  const send = async message => { if (!child.stdin.write(JSON.stringify(message) + '\n')) await once(child.stdin, 'drain'); };
  await send({ fonts: { dm: font.toString('base64') } });
  for (let index = 0; index < 300; index++) await send(await recordGpuCanvas(composition, index));
  child.stdin.end();
})();
await Promise.all([reading, feeding]);
const [exit, signal] = await done;
await writeFile(base + 'direct-oracle-native.stderr.json', stderr, { flag: 'wx' });
const expected = (await readFile(base + 'tagged-reference-hardware.framemd5', 'utf8')).split('\n').filter(line => line && !line.startsWith('#')).map(line => line.split(',').at(-1)!.trim());
const mismatches = hashes.map((hash, index) => hash === expected[index] ? null : index).filter(index => index !== null);
const result = { exit, signal, frames: hashes.length, incompleteBytes: cursor, directPlanarMd5: hashes, reference: base + 'final-reference-hardware-tagged/reference.mkv', referenceHashes: expected, mismatches, passed: exit === 0 && hashes.length === 300 && cursor === 0 && mismatches.length === 0, conversion: 'NV12 planar layout split only; no pixel arithmetic or color library', originalReferenceInvalidated: true };
await writeFile(base + 'hardware-reference-direct-binding.json', JSON.stringify(result, null, 2), { flag: 'wx' });
console.log(JSON.stringify({ exit, frames: hashes.length, mismatches, passed: result.passed }));
if (!result.passed) process.exitCode = 1;
