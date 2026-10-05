import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';

const c = JSON.parse(await readFile(process.argv[2], 'utf8'));
const now = () => process.hrtime.bigint();
const elapsed = start => Number(now() - start);
const expectedFlags = ['--disable-gpu', '--disable-gpu-compositing', '--disable-gpu-rasterization'];
const featureKeys = ['gpu_compositing', 'rasterization', '2d_canvas', 'canvas_oop_rasterization',
  'webgl', 'webgl2', 'webgpu', 'video_decode', 'video_encode', 'vulkan', 'skia_graphite'];
const details = { engine: 'R', node: process.version, ffmpegArgv: [], progress: [],
  gpuEvidence: { expectedGpuFlags: [], featureStatus: {}, glRenderer: null, glVendor: null,
    admissionPassed: false } };
let browser;
try {
  const require = createRequire(c.project + '/package.json');
  const { openBrowser, selectComposition, renderMedia } = require('@remotion/renderer');
  const start = now();
  browser = await openBrowser('chrome', {
    browserExecutable: c.browser, chromeMode: 'headless-shell',
    chromiumOptions: { gl: 'swangle', headless: true }, logLevel: 'warn',
  });
  details.browserOpenNs = elapsed(start);
  const querying = now();
  const [system, command] = await Promise.allSettled([
    browser.connection.send('SystemInfo.getInfo'),
    browser.connection.send('Browser.getBrowserCommandLine'),
  ]);
  details.gpuQueryNs = elapsed(querying);
  if (system.status === 'fulfilled') {
    const gpu = system.value.value.gpu ?? {};
    for (const key of featureKeys) {
      if (Object.hasOwn(gpu.featureStatus ?? {}, key)) details.gpuEvidence.featureStatus[key] = gpu.featureStatus[key];
    }
    details.gpuEvidence.glRenderer = gpu.auxAttributes?.glRenderer ?? null;
    details.gpuEvidence.glVendor = gpu.auxAttributes?.glVendor ?? null;
  } else details.gpuEvidence.systemInfoFailure = String(system.reason);
  if (command.status === 'fulfilled') {
    details.gpuEvidence.expectedGpuFlags = (command.value.value.arguments ?? []).filter(arg => expectedFlags.includes(arg));
  } else details.gpuEvidence.commandLineFailure = String(command.reason);
  // Never retain raw command-line arguments, auxiliary attributes, or GPU device lists.
  const missingFlags = expectedFlags.filter(flag => !details.gpuEvidence.expectedGpuFlags.includes(flag));
  const invalidStages = ['gpu_compositing', 'rasterization'].filter(key => {
    const value = details.gpuEvidence.featureStatus[key];
    return typeof value !== 'string' || !value.trim() || !/software|disabled|unavailable/i.test(value);
  });
  details.gpuEvidence.missingFlags = missingFlags;
  details.gpuEvidence.invalidRequiredStages = invalidStages;
  if (system.status !== 'fulfilled' || command.status !== 'fulfilled' || missingFlags.length || invalidStages.length) {
    throw new Error('CPU admission failed: required GPU flags or DOM stage status evidence missing/invalid');
  }
  details.gpuEvidence.admissionPassed = true;
  const shared = { serveUrl: c.bundle, inputProps: {}, puppeteerInstance: browser,
    browserExecutable: c.browser, chromeMode: 'headless-shell',
    chromiumOptions: { gl: 'swangle', headless: true }, binariesDirectory: c.binariesDirectory, logLevel: 'warn' };
  const selected = now();
  const composition = await selectComposition({ ...shared, id: 'TextGrid' });
  details.selectCompositionNs = elapsed(selected);
  if (composition.width !== 1920 || composition.height !== 1080 || composition.fps !== 30 || composition.durationInFrames !== 300) throw new Error('Unexpected TextGrid composition');
  const rendering = now();
  const milestones = new Set([1, 50, 100, 150, 200, 250, 300]);
  const reported = new Set();
  await renderMedia({ ...shared, composition, codec: 'h264', outputLocation: c.output,
    hardwareAcceleration: 'disable', imageFormat: 'jpeg', jpegQuality: c.jpegQuality, muted: true,
    frameRange: [0, 299], x264Preset: 'medium', crf: 11, pixelFormat: 'yuv420p',
    colorSpace: 'bt601', gopSize: 24, concurrency: c.workers, overwrite: false,
    onProgress: progress => {
      if (milestones.has(progress.renderedFrames) && !reported.has(progress.renderedFrames)) {
        reported.add(progress.renderedFrames);
        details.progress.push({ elapsedNs: elapsed(rendering), ...progress });
      }
    },
    ffmpegOverride: ({ type, args }) => {
      // The stitcher may only remux a parallel pre-encode. Never encode it again.
      const copying = args.some((arg, i) => ['-c:v', '-vcodec', '-codec:video'].includes(arg) && args[i + 1] === 'copy');
      const result = [...args];
      if (!copying) {
        if (!args.some((arg, i) => arg === '-c:v' && args[i + 1] === 'libx264')) throw new Error('Expected software libx264');
        result.splice(result.length - 1, 0,
          '-threads:v', String(c.encoderThreads), '-bf', '3', '-sc_threshold', '40',
          '-qmin', '15', '-qmax', '60', '-qcomp', '0.6', '-qdiff', '4',
          '-vf', 'scale=out_color_matrix=bt601:out_range=tv,format=yuv420p',
          '-colorspace:v', 'smpte170m', '-color_range', 'tv');
      }
      details.ffmpegArgv.push({ type, copying, executable: c.binariesDirectory + '/ffmpeg', args: result });
      return result;
    },
  });
  details.renderMediaNs = elapsed(rendering);
  if (!details.ffmpegArgv.some(a => !a.copying)) throw new Error('Missing encoding argv evidence');
} catch (error) {
  details.failure = error?.stack ?? String(error);
  console.error(details.failure);
  process.exitCode = 1;
} finally {
  if (browser) {
    const closing = now();
    try { await browser.close({ silent: true }); }
    catch (error) { details.cleanupFailure = String(error); process.exitCode = 1; }
    details.browserCloseNs = elapsed(closing);
  }
  await writeFile(c.details, JSON.stringify(details, null, 2) + '\n');
}
