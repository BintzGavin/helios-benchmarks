import { RendererOptions, RenderJobOptions } from './types.js';
export declare class Renderer {
    private options;
    constructor(options: RendererOptions);
    diagnose(): Promise<any>;
    render(compositionUrl: string, outputPath: string, jobOptions?: RenderJobOptions): Promise<void>;
}
