import type { Font } from 'fontkit';
import { TextLayout } from './text.js';
import { VideoInfo } from './media.js';
import { Plan, Fps } from './plan.js';
export type AssetFiles = Map<string, string>;
export type Rasterizer = 'native' | 'wasm' | 'skia';
export interface SoftwareEncoderOptions {
    preset?: 'ultrafast' | 'superfast' | 'veryfast' | 'faster' | 'fast' | 'medium' | 'slow' | 'slower' | 'veryslow' | 'placebo';
    crf?: number;
    threads?: number;
    gop?: number;
    bframes?: number;
    sceneCut?: boolean;
    qmin?: number;
    qmax?: number;
    qcompress?: number;
    maxQdiff?: number;
    colorConversion?: 'srgb-bt709' | 'rgb-bt601';
}
export interface PreparedScene {
    fonts: Map<string, Font>;
    text: Map<string, TextLayout>;
    images: Map<string, Buffer>;
    videos: Map<string, VideoInfo>;
    frames: Map<string, Buffer>;
}
export interface RenderOptions {
    ffmpeg?: string;
    ffprobe?: string;
    signal?: AbortSignal;
    start?: number;
    end?: number;
    rasterizer?: Rasterizer;
    prepared?: PreparedScene;
    videoOnly?: boolean;
    framesReady?: boolean;
    onFrame?: (index: number) => void | Promise<void>;
}
export declare function prepareScene(plan: Plan, assets: AssetFiles, options?: RenderOptions, checkCadence?: boolean): Promise<PreparedScene>;
export declare function frameSvg(plan: Plan, index: number, prepared?: PreparedScene): string;
export declare function renderFrame(plan: Plan, index: number, assets: AssetFiles, options?: RenderOptions): Promise<{
    pixels: Buffer;
    png: Buffer;
    svg: string;
}>;
export declare function renderVideo(plan: Plan, assets: AssetFiles, output: string, options?: RenderOptions): Promise<void>;
/** Shared software-encoder settings for the runtime and controlled capture benchmark. */
export declare function videoEncoderArgs(plan: Plan, frames: number, output: string, input?: 'rgba' | 'png', encoder?: SoftwareEncoderOptions): string[];
export declare function probeVideo(path: string, options?: Pick<RenderOptions, 'ffprobe' | 'signal'>): Promise<{
    frameCount: number;
    width: number;
    height: number;
    fps: Fps;
    codec: string;
    duration: number;
    audioCodec?: string;
}>;
/** For freshly encoded H.264 chunks only; delivery still requires full decode verification. */
export declare function probeEncodedChunk(path: string, options?: Pick<RenderOptions, 'ffprobe' | 'signal'>): Promise<{
    frameCount: number;
    width: any;
    height: any;
    fps: {
        num: any;
        den: any;
    };
    codec: any;
    duration: number;
    audioCodec: any;
}>;
