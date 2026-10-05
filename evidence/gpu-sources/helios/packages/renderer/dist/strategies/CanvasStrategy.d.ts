import { Page } from 'playwright';
import { RenderStrategy } from './RenderStrategy.js';
import { RendererOptions, FFmpegConfig } from '../types.js';
export declare class CanvasStrategy implements RenderStrategy {
    private options;
    private useWebCodecs;
    private useH264;
    private discoveredAudioTracks;
    private cleanupAudio;
    constructor(options: RendererOptions);
    init(page: Page): Promise<void>;
    private parseBitrate;
    diagnose(page: Page): Promise<any>;
    prepare(page: Page): Promise<void>;
    capture(page: Page, frameTime: number): Promise<any>;
    private captureWebCodecs;
    private captureCanvas;
    finish(page: Page): Promise<Buffer | void>;
    getFFmpegArgs(options: RendererOptions, outputPath: string): FFmpegConfig;
    cleanup(): Promise<void>;
}
