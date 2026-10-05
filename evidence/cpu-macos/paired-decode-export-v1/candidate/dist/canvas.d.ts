import { type SKRSContext2D } from './skia-binding.js';
import { type Fps, type Plan } from './plan.js';
import { type SoftwareEncoderOptions } from './render.js';
export interface CanvasFrame {
    index: number;
    time: number;
    fonts: Readonly<Record<string, string>>;
}
/** Trusted code installed with a worker. Not executable input to the JSON render service. */
export interface CanvasComposition {
    width: number;
    height: number;
    fps: Fps;
    frameCount: number;
    background?: string;
    fonts?: Record<string, Uint8Array>;
    /** Paint the requested frame directly; do not depend on prior calls or wall time. */
    draw(context: SKRSContext2D, frame: CanvasFrame): void | Promise<void>;
}
export interface CanvasRenderOptions {
    ffmpeg?: string;
    ffprobe?: string;
    signal?: AbortSignal;
    start?: number;
    end?: number;
    encoder?: SoftwareEncoderOptions;
    onFrame?: (index: number) => void | Promise<void>;
}
export interface CanvasFrameTimings {
    rasterizeMs: number;
    pixelExtractionMs: number;
}
export interface CanvasRangeStats extends CanvasFrameTimings {
    frames: number;
    preparationMs: number;
    drawMs: number;
    encoderWaitMs: number;
    encodeMs: number;
    verifyMs: number;
}
/** One retained CPU surface. Use separate instances for concurrent frame ranges. */
export declare class CanvasFrameRenderer {
    private composition;
    readonly plan: Plan;
    private canvas;
    private fonts;
    private acquired;
    private busy;
    private closed;
    constructor(composition: CanvasComposition);
    render(index: number, timings?: CanvasFrameTimings): Promise<Buffer>;
    close(): void;
}
/** Software-only encoding of an exact half-open range, suitable for stateless workers. */
export declare function renderCanvasVideo(composition: CanvasComposition, output: string, options?: CanvasRenderOptions): Promise<void>;
export declare function encodeCanvasRange(renderer: CanvasFrameRenderer, output: string, options?: CanvasRenderOptions, internalChunk?: boolean): Promise<CanvasRangeStats>;
