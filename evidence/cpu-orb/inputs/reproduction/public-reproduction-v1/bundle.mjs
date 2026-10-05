// Setup only; receives explicit project and bundle paths, never reads environment values.
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
const project = resolve(process.argv[2]);
const output = resolve(process.argv[3]);
const require = createRequire(project + '/package.json');
const {bundle} = require('@remotion/bundler');
await bundle({entryPoint: project + '/src/index.ts', outDir: output, publicDir: project + '/public'});
console.log(output);

