import {readFile} from 'node:fs/promises';
import {createTextGrid} from "file:///home/user/benchmark-work/repro-linux/fframes-textgrid.mjs";
export default createTextGrid(await readFile("/home/user/benchmark-work/fframes/render-bench/vs-remotion/fframes/media/DMSans-Regular.ttf"));
