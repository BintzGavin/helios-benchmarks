import { type CanvasComposition, type CanvasRenderOptions, type CanvasRangeStats } from './canvas.js';
export interface CanvasPoolOptions extends Omit<CanvasRenderOptions, 'onFrame'> {
    concurrency?: number;
    chunkFrames?: number;
    onProgress?: (completed: number, total: number) => void | Promise<void>;
}
export interface CanvasPoolResult {
    frames: number;
    chunks: number;
    workers: number;
    ranges: CanvasRangeStats[];
    renderMs: number;
    finalizeMs: number;
    finalVerifyMs: number;
}
export declare function loadCanvasComposition(module: URL): Promise<CanvasComposition>;
/** Persistent CPU workers dynamically claim contiguous ranges; each range seeks independently. */
export declare function renderCanvasModule(modulePath: string | URL, output: string, options?: CanvasPoolOptions): Promise<CanvasPoolResult>;
