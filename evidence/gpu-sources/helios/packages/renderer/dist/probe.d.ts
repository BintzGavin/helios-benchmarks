import { BrowserConfig } from './types.js';
export interface CompositionInfo {
    /**
     * What drives the page's frames:
     * - 'helios': a `window.helios` instance
     * - 'hook': a frame function, `window.renderAt(t)`, `__render(t)` or `seek(t)` (see `hook`)
     * - 'gsap': a `window.__helios_gsap_timeline__`
     * - 'none': nothing; the page animates on its own (CSS, WAAPI, rAF)
     */
    driver: 'helios' | 'hook' | 'gsap' | 'none';
    /** The frame function the renderer will call, when `driver` is 'hook'. */
    hook?: string;
    /** Declared by a Helios composition. */
    durationInSeconds?: number;
    fps?: number;
    width?: number;
    height?: number;
}
export interface ProbeOptions {
    browserConfig?: BrowserConfig;
    /** Viewport to load the page at. Defaults to 1920x1080. */
    width?: number;
    height?: number;
    /** Upper bound on waiting for the page to load. Defaults to 30s. */
    timeoutMs?: number;
}
/**
 * Loads a composition once and reports what drives it and, for Helios compositions, the
 * duration, fps and size it declares -- so a caller can render it without being told.
 */
export declare function probeComposition(url: string, options?: ProbeOptions): Promise<CompositionInfo>;
