import { BrowserConfig } from './types.js';
export interface CaptureFramesOptions {
    /** Viewport size. Defaults to 1920x1080. */
    width?: number;
    height?: number;
    /** Cut each frame to this region, in page pixels. */
    crop?: {
        x: number;
        y: number;
        width: number;
        height: number;
    };
    /** Scale the PNGs, e.g. 0.25 for quarter size. Defaults to 1. */
    scale?: number;
    browserConfig?: BrowserConfig;
    /** How long a frame may wait for fonts, media or the page's hook. Defaults to 30s. */
    stabilityTimeout?: number;
}
export interface ContactSheetOptions extends CaptureFramesOptions {
    /** Frames per row. Defaults to up to 4. */
    columns?: number;
    /** Width of each thumbnail, in pixels. Defaults to 480, or the frame width if smaller. */
    cellWidth?: number;
}
/**
 * Renders the frames at the given times (seconds) as PNGs, straight from the page: the same
 * seek and capture path as a DOM-mode render, without encoding a video. For looking at a
 * composition while working on it.
 */
export declare function captureFrames(url: string, times: number[], options?: CaptureFramesOptions): Promise<Buffer[]>;
/**
 * Renders the frames at the given times and lays them out in one labelled PNG, left to
 * right and top to bottom.
 */
export declare function captureContactSheet(url: string, times: number[], options?: ContactSheetOptions): Promise<Buffer>;
