/**
 * Page-defined "draw the frame at time t" functions the renderer calls on every frame,
 * in priority order. `t` is in seconds; a returned promise is awaited before capture.
 * These are the shapes agents write unprompted (`renderAt(t)`, `__render(t)`, `seek(t)`).
 */
export declare const PAGE_SEEK_HOOKS: readonly ["renderAt", "__render", "seek"];
/** Marks errors thrown by a page hook so they fail the render instead of being ignored. */
export declare const PAGE_HOOK_ERROR_MARKER = "[helios:page-hook]";
export interface SeekScriptOptions {
    /**
     * Run the page's pending requestAnimationFrame callbacks on every seek, with the new
     * virtual time. See SeekTimeDriverOptions.flushAnimationFrames.
     */
    flushAnimationFrames?: boolean;
}
export interface PageShimOptions extends SeekScriptOptions {
    /** Seed for the deterministic Math.random(). Defaults to the renderer's default seed. */
    seed?: number;
}
/**
 * Installs virtual time in the page: window.__HELIOS_VIRTUAL_TIME__ drives performance.now(),
 * Date.now() and requestAnimationFrame timestamps, and window.__helios_flush_animation_frames
 * runs pending rAF callbacks. Must stay self-contained: Playwright serializes it with toString().
 */
export declare const installVirtualTime: () => void;
/**
 * The script that defines window.__helios_seek(t, timeoutMs) and
 * window.__helios_invalidate_cache in the page. Expects installVirtualTime to have run first.
 * We wrap it in an IIFE to avoid polluting the global namespace with helper functions.
 */
export declare function buildSeekScript(options?: SeekScriptOptions): string;
/**
 * One self-contained script that gives a plain browser page the renderer's "frame at t"
 * semantics: seeded Math.random(), virtual time, and window.__helios_seek(t, timeoutMs).
 * Put it in a <script> before any page script, e.g. at the top of an MCP App view's
 * srcdoc iframe, then call window.__helios_seek(t, timeoutMs) to show the frame at t
 * exactly as a render would. The renderer's SeekTimeDriver injects the same pieces
 * (getSeedScript, installVirtualTime, buildSeekScript) through Playwright.
 */
export declare function buildPageShim(options?: PageShimOptions): string;
