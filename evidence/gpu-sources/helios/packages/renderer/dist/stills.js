import { BrowserPool } from './core/BrowserPool.js';
/**
 * Renders the frames at the given times (seconds) as PNGs, straight from the page: the same
 * seek and capture path as a DOM-mode render, without encoding a video. For looking at a
 * composition while working on it.
 */
export async function captureFrames(url, times, options = {}) {
    const pool = createPool(options);
    try {
        return await captureWithPool(pool, url, times, options);
    }
    finally {
        await pool.close();
        await pool.cleanupStrategies();
    }
}
/**
 * Renders the frames at the given times and lays them out in one labelled PNG, left to
 * right and top to bottom.
 */
export async function captureContactSheet(url, times, options = {}) {
    const pool = createPool(options);
    try {
        const frameWidth = options.crop?.width ?? options.width ?? 1920;
        const cellWidth = Math.round(options.cellWidth ?? Math.min(480, frameWidth));
        // Capture at thumbnail size: sharper than CSS downscaling, and far smaller.
        const frames = await captureWithPool(pool, url, times, { ...options, scale: cellWidth / frameWidth });
        const columns = Math.max(1, Math.round(options.columns ?? Math.min(4, frames.length)));
        const gap = 8;
        const cells = frames.map((png, i) => `
      <figure>
        <img src="data:image/png;base64,${png.toString('base64')}">
        <figcaption>${formatTime(times[i])}</figcaption>
      </figure>`).join('');
        const html = `<!doctype html><html><head><style>
      html, body { margin: 0; background: #16161a; }
      .grid { display: grid; grid-template-columns: repeat(${columns}, ${cellWidth}px); gap: ${gap}px; padding: ${gap}px; width: max-content; }
      figure { margin: 0; }
      img { display: block; width: ${cellWidth}px; height: auto; background: #000; }
      figcaption { font: 600 14px/1 system-ui, sans-serif; color: #d8d8e0; padding: 6px 2px 0; }
    </style></head><body><div class="grid">${cells}</div></body></html>`;
        // A fresh page: the render page carries the virtual clock and seek hooks.
        const sheetPage = await pool.workers[0].context.newPage();
        await sheetPage.setViewportSize({ width: columns * cellWidth + (columns + 1) * gap, height: 100 });
        await sheetPage.setContent(html);
        // A string, not a function: transpilers can inject helpers that do not exist in the page.
        await sheetPage.evaluate('Promise.all(Array.from(document.images, (img) => img.decode()))');
        const grid = await sheetPage.$('.grid');
        return await grid.screenshot({ type: 'png' });
    }
    finally {
        await pool.close();
        await pool.cleanupStrategies();
    }
}
function createPool(options) {
    return new BrowserPool({
        width: options.width ?? 1920,
        height: options.height ?? 1080,
        fps: 30,
        durationInSeconds: 1,
        mode: 'dom',
        browserConfig: options.browserConfig,
        stabilityTimeout: options.stabilityTimeout,
    });
}
async function captureWithPool(pool, url, times, options) {
    await pool.init(url);
    const { page, timeDriver } = pool.workers[0];
    const cdp = page._sharedCdpSession;
    const scale = options.scale ?? 1;
    const region = options.crop ?? (scale !== 1 ? { x: 0, y: 0, width: options.width ?? 1920, height: options.height ?? 1080 } : undefined);
    const clip = region ? { ...region, scale } : undefined;
    const frames = [];
    for (const t of times) {
        await timeDriver.setTime(page, t);
        const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', fromSurface: true, ...(clip ? { clip } : {}) });
        frames.push(Buffer.from(data, 'base64'));
    }
    if (pool.capturedErrors.length > 0)
        throw pool.capturedErrors[0];
    return frames;
}
function formatTime(t) {
    return `${Number(t.toFixed(3))}s`;
}
