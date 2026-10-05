import { WorkerInfo } from "./BrowserPool.js";
import { FFmpegManager } from "./FFmpegManager.js";
import { RendererOptions, RenderJobOptions } from "../types.js";
export declare class CaptureLoop {
    private options;
    private pool;
    private ffmpegManager;
    private totalFrames;
    private startFrame;
    private capturedErrors;
    private jobOptions?;
    private drainPromise;
    constructor(options: RendererOptions, pool: WorkerInfo[], ffmpegManager: FFmpegManager, totalFrames: number, startFrame: number, capturedErrors: Error[], jobOptions?: RenderJobOptions | undefined);
    private setupDrainListeners;
    run(): Promise<void>;
}
