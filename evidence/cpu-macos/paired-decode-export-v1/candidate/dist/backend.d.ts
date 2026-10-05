import { Plan } from './plan.js';
import { AssetFiles, RenderOptions } from './render.js';
export interface RenderBackend {
    readonly identity: string;
    fingerprint?(): Promise<string>;
    preflight(plan: Plan, assets: AssetFiles, signal: AbortSignal): Promise<void>;
    chunk(plan: Plan, assets: AssetFiles, output: string, start: number, end: number, signal: AbortSignal): Promise<void>;
    finalize(plan: Plan, assets: AssetFiles, chunks: {
        path: string;
        start: number;
        end: number;
    }[], output: string, signal: AbortSignal): Promise<void>;
}
export declare class NativeBackend implements RenderBackend {
    private options;
    readonly identity: string;
    private cached?;
    private build?;
    constructor(options?: Pick<RenderOptions, 'ffmpeg' | 'ffprobe' | 'rasterizer'>);
    fingerprint(): Promise<string>;
    preflight(plan: Plan, assets: AssetFiles, signal: AbortSignal): Promise<void>;
    chunk(plan: Plan, assets: AssetFiles, output: string, start: number, end: number, signal: AbortSignal): Promise<void>;
    finalize(plan: Plan, assets: AssetFiles, chunks: {
        path: string;
        start: number;
        end: number;
    }[], output: string, signal: AbortSignal): Promise<void>;
}
