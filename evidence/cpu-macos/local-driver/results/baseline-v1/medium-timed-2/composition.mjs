import { readFile } from 'node:fs/promises';
import { createTextGrid } from "file:///Users/gavinbintz/Developer/helios/packages/portable/benchmarks/fframes-textgrid.mjs";
export default createTextGrid(await readFile("/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/source/fframes/render-bench/vs-remotion/fframes/media/DMSans-Regular.ttf"));
