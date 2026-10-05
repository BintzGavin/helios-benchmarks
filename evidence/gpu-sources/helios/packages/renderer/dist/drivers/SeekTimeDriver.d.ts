import { Page } from 'playwright';
import { TimeDriver } from './TimeDriver.js';
import { PAGE_SEEK_HOOKS } from './seek-shim.js';
export { PAGE_SEEK_HOOKS };
/**
 * How long to wait after load for a page to define `window.helios`, a GSAP timeline or a
 * seek hook. Pages that never define one (plain CSS, WAAPI or rAF animation) start
 * rendering after this grace period instead of waiting out the full stability timeout.
 */
export declare const HOOK_GRACE_MS = 3000;
export interface SeekTimeDriverOptions {
    /**
     * Run the page's pending requestAnimationFrame callbacks on every seek, with the new
     * virtual time, instead of waiting for the browser to produce a frame. Canvas mode needs
     * this: it captures the canvas directly, so nothing else forces a frame between seek and
     * capture (and begin-frame control stops the browser from producing frames on its own).
     */
    flushAnimationFrames?: boolean;
}
export declare class SeekTimeDriver implements TimeDriver {
    private timeout;
    private aggregator;
    private cdpSession;
    private multiFrameCallParams;
    private executionContextIds;
    private flushAnimationFrames;
    private warnedInternalSeekError;
    private callFunctionOnParams;
    private evaluateArgs;
    private handleExecutionContextCreated;
    private handleExecutionContextDestroyed;
    private handleExecutionContextsCleared;
    constructor(timeout?: number, options?: SeekTimeDriverOptions);
    init(page: Page, seed?: number): Promise<void>;
    prepare(page: Page): Promise<void>;
    /**
     * Runtime.callFunctionOn reports page exceptions in the response instead of rejecting.
     * A throwing page hook (window.renderAt etc.) fails the render with the page's own error;
     * anything else keeps the previous behaviour of carrying on, but is no longer silent.
     */
    private checkSeekResult;
    setTime(page: Page, timeInSeconds: number): Promise<void> | void;
}
