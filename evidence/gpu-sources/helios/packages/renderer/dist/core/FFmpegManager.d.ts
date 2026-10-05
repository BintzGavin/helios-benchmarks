import { ChildProcess } from 'child_process';
import { RendererOptions, RenderJobOptions } from '../types.js';
export declare class FFmpegManager {
    private options;
    private jobOptions?;
    private process;
    private startPromise;
    ffmpegPath: string;
    constructor(options: RendererOptions, jobOptions?: RenderJobOptions | undefined);
    spawn(args: string[], inputBuffers: {
        index: number;
        buffer: Buffer;
    }[]): ChildProcess;
    waitUntilStarted(): Promise<void>;
    getExitPromise(capturedErrors: Error[]): Promise<void>;
    kill(): void;
    get stdin(): import("node:stream").Writable | null | undefined;
    emitError(err: Error): void;
}
