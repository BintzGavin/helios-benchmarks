// Reuse the frozen strict CPU JPEG worker, changing only preset-dependent settings.
import {readFile} from 'node:fs/promises';
const sourcePath = new URL('../remotion-cpu-jpeg-study-v1/worker.mjs', import.meta.url);
let source = await readFile(sourcePath, 'utf8');
for (const [before, after] of [
  ["x264Preset: 'medium'", "x264Preset: c.preset"],
  ["'-bf', '3', '-sc_threshold', '40'", "'-bf', c.preset === 'ultrafast' ? '0' : '3', '-sc_threshold', c.preset === 'ultrafast' ? '0' : '40'"],
]) {
  if (source.split(before).length !== 2) throw new Error('Frozen Remotion worker shape changed');
  source = source.replace(before, after);
}
await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
