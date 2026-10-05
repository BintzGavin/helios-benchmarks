import { RenderExecutor } from './RenderExecutor.js';
import { RendererOptions, RenderJobOptions } from '../types.js';
export declare class LocalExecutor implements RenderExecutor {
    render(compositionUrl: string, outputPath: string, options: RendererOptions, jobOptions?: RenderJobOptions): Promise<void>;
}
