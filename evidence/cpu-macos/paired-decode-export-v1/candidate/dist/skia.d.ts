import { type Canvas } from './skia-binding.js';
import { Plan } from './plan.js';
import type { PreparedScene } from './render.js';
/** Retained CPU Skia surfaces: no browser, DOM, system fonts or executable input. */
export declare class SkiaRasterizer {
    private plan;
    private prepared;
    private canvas;
    private images;
    private video;
    private paths;
    private text;
    private layers;
    private textLayers;
    private geometry;
    private prefix?;
    private prefixCount;
    constructor(plan: Plan, prepared: PreparedScene);
    prepare(): Promise<void>;
    setVideo(id: string, rgba: Buffer, width: number, height: number): void;
    retainVideos(ids: Set<string>): void;
    private path;
    private fill;
    private compileText;
    draw(index: number): Canvas;
    render(index: number, encodePng?: boolean): {
        pixels: Buffer;
        png: Buffer;
    };
}
