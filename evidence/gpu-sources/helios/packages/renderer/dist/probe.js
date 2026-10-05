import { BrowserPool } from './core/BrowserPool.js';
import { launchChromium } from './core/launchBrowser.js';
import { PAGE_SEEK_HOOKS, HOOK_GRACE_MS } from './drivers/SeekTimeDriver.js';
/**
 * Loads a composition once and reports what drives it and, for Helios compositions, the
 * duration, fps and size it declares -- so a caller can render it without being told.
 */
export async function probeComposition(url, options = {}) {
    const width = options.width ?? 1920;
    const height = options.height ?? 1080;
    const timeout = options.timeoutMs ?? 30000;
    const launchOptions = new BrowserPool({
        width,
        height,
        fps: 30,
        durationInSeconds: 1,
        mode: 'dom',
        browserConfig: options.browserConfig,
    }).getLaunchOptions();
    const browser = await launchChromium(launchOptions);
    try {
        const page = await browser.newPage({ viewport: { width, height } });
        await page.goto(url, { waitUntil: 'load', timeout });
        // Same readiness rule as rendering: whatever drives the page may be defined by a
        // module that finishes after load, so give it the same grace period.
        await page
            .waitForFunction((hookNames) => {
            const w = window;
            return typeof w.helios !== 'undefined' ||
                typeof w.__helios_gsap_timeline__ !== 'undefined' ||
                hookNames.some((name) => typeof w[name] === 'function');
        }, [...PAGE_SEEK_HOOKS], { timeout: Math.min(timeout, HOOK_GRACE_MS), polling: 100 })
            .catch(() => { });
        // A string, not a function: transpilers can inject helpers (esbuild's __name) that do
        // not exist in the page.
        return await page.evaluate(`(() => {
      const hookNames = ${JSON.stringify(PAGE_SEEK_HOOKS)};
      function positive(v) {
        const n = v && typeof v === 'object' && 'value' in v ? v.value : v;
        return typeof n === 'number' && Number.isFinite(n) && n > 0 ? n : undefined;
      }
      const helios = window.helios;
      if (helios && typeof helios.seek === 'function') {
        return {
          driver: 'helios',
          durationInSeconds: positive(helios.duration),
          fps: positive(helios.fps),
          width: positive(helios.width),
          height: positive(helios.height),
        };
      }
      const hook = hookNames.find((name) => typeof window[name] === 'function');
      if (hook) return { driver: 'hook', hook };
      if (typeof window.__helios_gsap_timeline__ !== 'undefined') return { driver: 'gsap' };
      return { driver: 'none' };
    })()`);
    }
    finally {
        await browser.close();
    }
}
