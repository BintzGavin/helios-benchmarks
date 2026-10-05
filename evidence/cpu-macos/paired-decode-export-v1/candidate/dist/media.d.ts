import { Plan, Node, Fps } from './plan.js';
export interface MediaTools {
    ffmpeg?: string;
    ffprobe?: string;
    signal?: AbortSignal;
}
export interface VideoInfo {
    width: number;
    height: number;
    fps: Fps;
    duration: number;
}
export declare function videoInfo(path: string, tools?: MediaTools, checkCadence?: boolean): Promise<VideoInfo>;
export interface WavInfo {
    offset: number;
    frames: number;
    channels: number;
    bytesPerSample: number;
    format: number;
}
export declare function wavInfo(path: string): Promise<WavInfo>;
export declare function mixAudio(plan: Plan, paths: Map<string, string>, output: string, signal?: AbortSignal): Promise<void>;
export declare function muxAudio(plan: Plan, paths: Map<string, string>, video: string, output: string, tools?: MediaTools): Promise<void>;
export declare class VideoDecoder {
    private process;
    private reader;
    private next;
    private cached?;
    private rawBytes;
    constructor(path: string, sourceIndex: number, info: VideoInfo, tools: MediaTools & {
        format?: 'png' | 'rgba';
    });
    frame(index: number): Promise<Buffer>;
    close(): Promise<void>;
}
export declare function activeVideos(plan: Plan, frame: number): Node[];
