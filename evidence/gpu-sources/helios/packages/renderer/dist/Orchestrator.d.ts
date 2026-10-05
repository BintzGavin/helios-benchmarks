import { RendererOptions, RenderJobOptions, RenderPlan } from './types.js';
import { RenderExecutor } from './executors/RenderExecutor.js';
export interface DistributedRenderOptions extends RendererOptions {
    concurrency?: number;
    executor?: RenderExecutor;
}
export declare class RenderOrchestrator {
    static plan(compositionUrl: string, outputPath: string, options: DistributedRenderOptions): RenderPlan;
    static render(compositionUrl: string, outputPath: string, options: DistributedRenderOptions, jobOptions?: RenderJobOptions): Promise<void>;
}
