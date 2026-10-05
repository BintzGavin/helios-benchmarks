import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {once} from 'node:events';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const c = JSON.parse(await readFile(process.argv[2], 'utf8'));
const details = {reference: c.reference, node: process.version, frames: [], imageFormat: 'png'};
let browser, renderer;
const flags = ['--disable-gpu', '--disable-gpu-compositing', '--disable-gpu-rasterization'];
const featureKeys = ['gpu_compositing', 'rasterization', '2d_canvas', 'canvas_oop_rasterization',
  'webgl', 'webgl2', 'webgpu', 'video_decode', 'video_encode', 'vulkan', 'skia_graphite'];
async function gpuReceipt() {
  const receipt = {expectedGpuFlags: [], featureStatus: {}, glRenderer: null, glVendor: null};
  const [system, command] = await Promise.allSettled([
    browser.connection.send('SystemInfo.getInfo'), browser.connection.send('Browser.getBrowserCommandLine')]);
  if (system.status === 'fulfilled') {
    const gpu = system.value.value.gpu ?? {};
    for (const key of featureKeys) {
      if (Object.hasOwn(gpu.featureStatus ?? {}, key)) receipt.featureStatus[key] = gpu.featureStatus[key];
    }
    receipt.glRenderer = gpu.auxAttributes?.glRenderer ?? null;
    receipt.glVendor = gpu.auxAttributes?.glVendor ?? null;
  } else receipt.systemInfoFailure = String(system.reason);
  if (command.status === 'fulfilled') {
    receipt.expectedGpuFlags = (command.value.value.arguments ?? []).filter(arg => flags.includes(arg));
  } else receipt.commandLineFailure = String(command.reason);
  // Raw browser argv and GPU device/auxiliary lists are deliberately never retained.
  receipt.missingFlags = flags.filter(flag => !receipt.expectedGpuFlags.includes(flag));
  receipt.invalidRequiredStages = ['gpu_compositing', 'rasterization'].filter(key => {
    const value = receipt.featureStatus[key];
    return typeof value !== 'string' || !value.trim() || !/software|disabled|unavailable/i.test(value);
  });
  receipt.admissionPassed = system.status === 'fulfilled' && command.status === 'fulfilled' &&
    !receipt.missingFlags.length && !receipt.invalidRequiredStages.length;
  return receipt;
}
try {
  if (c.reference === 'H') {
    const {CanvasFrameRenderer} = await import(pathToFileURL(c.canvasModule).href);
    const {default: composition} = await import(pathToFileURL(c.compositionModule).href);
    renderer = new CanvasFrameRenderer(composition);
    details.imageFormat = 'raw-rgba';
    for (let index = 0; index < 300; index++) {
      const pixels = await renderer.render(index);
      if (pixels.length !== 1920 * 1080 * 4) throw new Error('Unexpected RGBA size');
      details.frames.push({index, bytes: pixels.length, sha256: createHash('sha256').update(pixels).digest('hex')});
      if (!process.stdout.write(pixels)) await once(process.stdout, 'drain');
    }
  } else {
    const strictCpu = c.reference === 'R-cpu';
    details.cpuLabel = strictCpu ? 'strict-CPU-PNG-reference' : 'GPU-stages-unattested-legacy-PNG-reference';
    const require = createRequire(c.project + '/package.json');
    const {openBrowser, selectComposition, renderFrames} = require('@remotion/renderer');
    browser = await openBrowser('chrome', {browserExecutable: c.browser, chromeMode: 'headless-shell',
      chromiumOptions: {gl: 'swangle', headless: true}, logLevel: 'warn'});
    details.gpuBefore = await gpuReceipt();
    if (strictCpu && !details.gpuBefore.admissionPassed) throw new Error('Strict CPU PNG reference admission failed');
    const shared = {serveUrl: c.bundle, inputProps: {}, puppeteerInstance: browser,
      browserExecutable: c.browser, chromeMode: 'headless-shell',
      chromiumOptions: {gl: 'swangle', headless: true}, binariesDirectory: c.binariesDirectory, logLevel: 'warn'};
    const composition = await selectComposition({...shared, id: 'TextGrid'});
    if (composition.width !== 1920 || composition.height !== 1080 || composition.fps !== 30 ||
      composition.durationInFrames !== 300) throw new Error('Unexpected TextGrid composition');
    await mkdir(c.pngDirectory);
    let totalBytes = 0;
    const seen = new Set();
    await renderFrames({...shared, composition, imageFormat: 'png', frameRange: [0, 299],
      muted: true, concurrency: c.workers, outputDir: null, onStart: () => {}, onFrameUpdate: () => {},
      onFrameBuffer: async (buffer, frame) => {
        if (!Number.isInteger(frame) || frame < 0 || frame >= 300 || seen.has(frame)) throw new Error('Invalid/duplicate PNG frame');
        // Reserve synchronously before concurrent writes, keeping retained PNGs bounded.
        totalBytes += buffer.length;
        if (totalBytes > c.pngLimit) throw new Error('PNG reference scratch budget exceeded');
        seen.add(frame);
        const file = c.pngDirectory + '/frame-' + String(frame).padStart(3, '0') + '.png';
        await writeFile(file, buffer, {flag: 'wx'});
        details.frames.push({index: frame, bytes: buffer.length, sha256: createHash('sha256').update(buffer).digest('hex')});
      }});
    if (seen.size !== 300) throw new Error('Missing PNG frames');
    details.frames.sort((a, b) => a.index - b.index);
    details.pngBytes = totalBytes;
    details.gpuAfter = await gpuReceipt();
    if (strictCpu && !details.gpuAfter.admissionPassed) throw new Error('Strict CPU PNG reference final stage check failed');
  }
} catch (error) {
  details.failure = error?.stack ?? String(error);
  console.error(details.failure);
  process.exitCode = 1;
} finally {
  try { renderer?.close(); } catch (error) { details.cleanupFailure = String(error); process.exitCode = 1; }
  if (browser) {
    try { await browser.close({silent: true}); }
    catch (error) { details.cleanupFailure = String(error); process.exitCode = 1; }
  }
  await writeFile(c.details, JSON.stringify(details, null, 2) + '\n');
}
