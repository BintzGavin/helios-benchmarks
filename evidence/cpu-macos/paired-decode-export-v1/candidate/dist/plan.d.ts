export declare const PROFILE: "portable-v1";
export declare const LIMITS: Readonly<{
    nodes: 2000;
    keys: 5000;
    depth: 16;
    imagePixels: 16000000;
    decodedImagePixels: 32000000;
    assetBytes: number;
    totalAssetBytes: number;
    fontBytes: number;
    textCharacters: 20000;
    assets: 256;
    inputBytes: number;
}>;
export type Fps = {
    num: number;
    den: number;
};
export type Scalar = number | {
    keyframes: {
        frame: number;
        value: number;
        easing?: 'linear' | 'hold' | 'ease-in' | 'ease-out' | 'ease-in-out';
    }[];
};
export type Length = Scalar | `${number}%`;
export type Paint = string | {
    type: 'linear';
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    stops: {
        offset: number;
        color: string;
    }[];
};
export type Clip = {
    type: 'rect';
    width: number;
    height: number;
    radius?: number;
} | {
    type: 'path';
    d: string;
};
export interface Node {
    id: string;
    type: 'rect' | 'ellipse' | 'path' | 'group' | 'text' | 'image' | 'video';
    x?: Length;
    y?: Length;
    width?: Length;
    height?: Length;
    opacity?: Scalar;
    start?: number;
    end?: number;
    transform?: {
        scaleX?: Scalar;
        scaleY?: Scalar;
        rotation?: Scalar;
        originX?: number;
        originY?: number;
    };
    clip?: Clip;
    fill?: Paint;
    stroke?: {
        color: string;
        width: number;
    };
    radius?: number;
    d?: string;
    children?: Node[];
    layout?: {
        direction: 'row' | 'column';
        gap?: number;
        padding?: number;
        align?: 'start' | 'center' | 'end';
    };
    text?: string;
    fonts?: string[];
    fontSize?: number;
    lineHeight?: number;
    align?: 'left' | 'center' | 'right';
    direction?: 'auto' | 'ltr' | 'rtl';
    asset?: string;
    fit?: 'cover' | 'contain' | 'fill';
    sourceStart?: number;
}
export interface Asset {
    sha256: string;
    bytes: number;
    type: 'image' | 'font' | 'video' | 'audio';
}
export interface AudioTrack {
    asset: string;
    start: number;
    end: number;
    sourceStart: number;
    gain: number;
    fadeIn: number;
    fadeOut: number;
}
export interface Plan {
    version: typeof PROFILE;
    width: number;
    height: number;
    fps: Fps;
    frameCount: number;
    background: string;
    assets: Record<string, Asset>;
    nodes: Node[];
    audio: AudioTrack[];
}
export declare class RenderError extends Error {
    code: string;
    status: number;
    constructor(code: string, message: string, status?: number);
}
export declare function parsePlan(input: unknown): Plan;
export declare function evaluate(s: Scalar, frameIndex: number): number;
export declare const frameTime: (fps: Fps, index: number) => number;
export declare const sampleCount: (fps: Fps, frames: number) => number;
export declare const resolveLength: (value: Length | undefined, parent: number, frameIndex: number, fallback?: number) => number;
