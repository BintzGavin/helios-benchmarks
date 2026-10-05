import { readFile, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const config = JSON.parse(await readFile(process.argv[2], 'utf8'));
try {
  const { renderCanvasModule } = await import(pathToFileURL(config.poolModule).href);
  const stats = await renderCanvasModule(config.composition, config.output, config.options);
  await writeFile(config.stats, JSON.stringify({ stats, node: process.version }, null, 2) + '\n');
  console.log(JSON.stringify({ status: 'complete', stats: config.stats, output: config.output }));
} catch (error) {
  console.error(error?.stack ?? String(error));
  process.exitCode = 1;
}
