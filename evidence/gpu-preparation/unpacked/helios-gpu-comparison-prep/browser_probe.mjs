// Usage: node browser_probe.mjs /absolute/path/to/playwright/index.mjs /path/to/chrome output.json
import {writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const [playwrightPath, executablePath, output='evidence/browser-probe.json', sceneUrl='about:blank'] = process.argv.slice(2);
if (!playwrightPath || !executablePath) throw new Error('Supply existing Playwright module and Chromium executable paths; this script installs nothing');
const {chromium} = await import(pathToFileURL(playwrightPath));
const browser = await chromium.launch({executablePath, headless: true, ignoreDefaultArgs:['--enable-unsafe-swiftshader'], args: ['--enable-gpu']});
try {
  const session = await browser.newBrowserCDPSession();
  const systemInfo = await session.send('SystemInfo.getInfo');
  const version = await session.send('Browser.getVersion');
  const page = await browser.newPage();
  const response = await page.goto(sceneUrl);
  if (sceneUrl !== 'about:blank') {
    if (!response?.ok()) throw new Error(`Scene HTTP status ${response?.status()}`);
    await page.waitForFunction(() => window.fixture?.nodes === 3334 && typeof window.renderAt === 'function');
    await page.evaluate(() => window.sceneReady);
    await page.evaluate(() => window.renderAt(1 / 30));
  }
  const pageInfo = await page.evaluate(async () => {
    const test = document.createElement('canvas');
    const gl = test.getContext('webgl2') || test.getContext('webgl');
    const ext = gl && gl.getExtension('WEBGL_debug_renderer_info');
    const renderer = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null;
    const codecSupport = {};
    for (const codec of ['avc1.4d002a', 'hvc1.1.6.L120.B0']) {
      try { codecSupport[codec] = await VideoEncoder.isConfigSupported({codec, width:1920, height:1080, bitrate:25000000, framerate:30, hardwareAcceleration:'prefer-hardware'}); }
      catch(e) { codecSupport[codec] = {error:String(e)}; }
    }
    return {renderer, codecSupport, userAgent:navigator.userAgent, fixture:window.fixture};
  });
  await writeFile(output, JSON.stringify({version,systemInfo,pageInfo,notes:[
    'WebGL device info and GPU feature status do not by themselves prove Canvas2D hardware rasterization.',
    'WebCodecs prefer-hardware is a preference and isConfigSupported is not runtime encoding attestation.',
    'Capture engine-specific GPU/encoder telemetry during the actual timed process before claiming acceleration.'
  ]}, null, 2));
} finally { await browser.close(); }
