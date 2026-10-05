import { readFile, writeFile } from 'node:fs/promises';
import { createTextGrid } from '/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios/packages/portable/benchmarks/fframes-textgrid.mjs';
import { recordGpuCanvas } from '/Users/gavinbintz/.codex/worktrees/native-gpu-rendering/helios/packages/portable/src/gpu.ts';
const font = await readFile('/Users/gavinbintz/Documents/Codex/2026-10-02/task/preparation/unpacked/helios-gpu-comparison-prep/DM-Sans.ttf');
const composition = createTextGrid(font);
const rows = [JSON.stringify({ fonts: { dm: font.toString('base64') } })];
for (const frame of [0, 1, 299]) rows.push(JSON.stringify(await recordGpuCanvas(composition, frame)));
await writeFile('/private/tmp/helios-gpu-evidence/profile-input.jsonl', rows.join('\n') + '\n');
