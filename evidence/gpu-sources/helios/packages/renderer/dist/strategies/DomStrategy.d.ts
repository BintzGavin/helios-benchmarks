import { Page } from 'playwright';
import { RenderStrategy } from './RenderStrategy.js';
import { RendererOptions, FFmpegConfig } from '../types.js';
export declare class DomStrategy implements RenderStrategy {
    private options;
    private discoveredAudioTracks;
    private cleanupAudio;
    private cdpSession;
    private lastFrameData;
    private cdpScreenshotParams;
    private emptyImageBase64;
    private frameInterval;
    private beginFrameParams;
    constructor(options: RendererOptions);
    diagnose(page: Page): Promise<any>;
    prepare(page: Page): Promise<void>;
    processCaptureResult(result: any): string | Buffer;
    capture(page: Page, frameTime: number): Promise<any>;
    finish(page: Page): Promise<void>;
    getFFmpegArgs(options: RendererOptions, outputPath: string): FFmpegConfig;
    cleanup(): Promise<void>;
}
