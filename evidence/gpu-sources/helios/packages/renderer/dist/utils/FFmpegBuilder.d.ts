import { RendererOptions, FFmpegConfig } from '../types.js';
export declare class FFmpegBuilder {
    static getArgs(options: RendererOptions, outputPath: string, videoInputArgs: string[]): FFmpegConfig;
}
