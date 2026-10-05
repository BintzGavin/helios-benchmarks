// Concrete Helios browser adapter for controlled GPU-requested rasterization / x264 lane.
// Does not prove GPU use: capture runtime GPU evidence on the real host separately.
import {pathToFileURL} from 'node:url';
import {dirname, join} from 'node:path';
import {writeFile} from 'node:fs/promises';
const [modulePath, url, output, preset='medium', codec='libx264'] = process.argv.slice(2);
if (!modulePath || !url || !output) throw new Error('Usage: node render_helios.mjs RENDERER_INDEX_URL_OR_PATH SCENE_URL OUTPUT [PRESET] [CODEC]');
const {Renderer} = await import(modulePath.startsWith('file:') ? modulePath : pathToFileURL(modulePath));
const frames=Number(process.env.SMOKE_FRAMES || 300);
if (!Number.isInteger(frames) || frames<1 || frames>300) throw new Error('Invalid smoke frame count');
if (process.env.GPU_RECEIPT) {
  const {BrowserPool}=await import(pathToFileURL(join(dirname(modulePath), 'core/BrowserPool.js')));
  const originalInit=BrowserPool.prototype.init;
  BrowserPool.prototype.init=async function(...args) {
    await originalInit.apply(this,args);
    const worker=this.workers[0];
    const session=await worker.browser.newBrowserCDPSession();
    const systemInfo=await session.send('SystemInfo.getInfo');
    const fixture=await worker.page.evaluate(()=>window.fixture);
    await writeFile(process.env.GPU_RECEIPT,JSON.stringify({systemInfo,fixture,frames,notes:['Runtime device and feature evidence only; Canvas GPU work requires trace qualification.']},null,2));
    if (fixture?.nodes!==3334) throw new Error('TextGrid fixture mismatch');
    if (/swiftshader|llvmpipe|lavapipe/i.test(JSON.stringify(systemInfo.gpu.devices))) throw new Error('Software GPU rejected');
  };
}
const options={width:1920,height:1080,fps:30,durationInSeconds:frames/30,frameCount:frames,
  mode:'canvas',webCodecsPreference:'disabled',intermediateImageFormat:'png',
  videoCodec:codec,pixelFormat:'yuv420p',ffmpegPath:process.env.FFMPEG || 'ffmpeg',
  browserConfig:{gpu:true, executablePath:process.env.CHROME || undefined,args:['--enable-gpu']},
};
if (codec==='libx264') Object.assign(options,{crf:18,preset});
if (!['libx264','ffv1'].includes(codec)) throw new Error('This controlled adapter supports x264 or a lossless FFV1 reference only. Hardware/WebCodecs needs separate qualified adapter.');
await new Renderer(options).render(url,output);
