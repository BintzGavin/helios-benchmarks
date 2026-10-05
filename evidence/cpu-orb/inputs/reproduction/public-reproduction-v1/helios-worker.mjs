import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const c = JSON.parse(await readFile(process.argv[2], 'utf8'));
const now = () => process.hrtime.bigint();
const elapsed = start => Number(now() - start);
const details = { engine: c.engine, node: process.version, ffmpegArgv: [] };
let browser;
try {
  if (c.engine === 'H') {
    const { renderCanvasModule } = await import(pathToFileURL(c.poolModule).href);
    const start = now();
    details.stats = await renderCanvasModule(c.composition, c.output, c.options);
    details.apiWallNs = elapsed(start);
    const s = details.stats;
    if (s.frames !== 300 || !Number.isFinite(s.finalVerifyMs)) throw new Error('Missing Helios completeness evidence');
  } else if (c.engine === 'R') {
    const require = createRequire(c.project + '/package.json');
    const { openBrowser, selectComposition, renderMedia } = require('@remotion/renderer');
    const start = now();
    browser = await openBrowser('chrome', {
      browserExecutable: c.browser, chromeMode: 'headless-shell',
      chromiumOptions: { gl: 'swangle', headless: true }, logLevel: 'warn',
    });
    details.browserOpenNs = elapsed(start);
    const shared = { serveUrl: c.bundle, inputProps: {}, puppeteerInstance: browser,
      browserExecutable: c.browser, chromeMode: 'headless-shell',
      chromiumOptions: { gl: 'swangle', headless: true }, binariesDirectory: c.binariesDirectory, logLevel: 'warn' };
    const selected = now();
    const composition = await selectComposition({ ...shared, id: 'TextGrid' });
    details.selectCompositionNs = elapsed(selected);
    if (composition.width !== 1920 || composition.height !== 1080 || composition.fps !== 30 || composition.durationInFrames !== 300) throw new Error('Unexpected TextGrid composition');
    const rendering = now();
    await renderMedia({ ...shared, composition, codec: 'h264', outputLocation: c.output,
      hardwareAcceleration: 'disable', imageFormat: 'png', muted: true,
      frameRange: [0, 299], x264Preset: c.preset, crf: 11, pixelFormat: 'yuv420p',
      colorSpace: 'bt601', gopSize: 24, concurrency: c.workers, overwrite: false,
      ffmpegOverride: ({ type, args }) => {
        // The stitcher may only remux a parallel pre-encode. Never encode it again.
        const copying = args.some((arg, i) => ['-c:v', '-vcodec', '-codec:video'].includes(arg) && args[i + 1] === 'copy');
        const result = [...args];
        if (!copying) {
          if (!args.some((arg, i) => arg === '-c:v' && args[i + 1] === 'libx264')) throw new Error('Expected software libx264');
          result.splice(result.length - 1, 0,
            '-threads:v', String(c.encoderThreads), '-bf', c.preset === 'ultrafast' ? '0' : '3',
            '-sc_threshold', c.preset === 'ultrafast' ? '0' : '40',
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
  } else throw new Error('Unsupported worker engine');
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
