import { RenderStrategy } from '../strategies/RenderStrategy.js';
import { TimeDriver } from '../drivers/TimeDriver.js';
import { RendererOptions, RenderJobOptions } from '../types.js';
export interface WorkerInfo {
    browser: import('playwright').Browser;
    context: import('playwright').BrowserContext;
    page: import('playwright').Page;
    strategy: RenderStrategy;
    timeDriver: TimeDriver;
}
export declare class BrowserPool {
    private options;
    workers: WorkerInfo[];
    capturedErrors: Error[];
    constructor(options: RendererOptions);
    getLaunchOptions(): {
        headless: boolean;
        executablePath: string | undefined;
        args: string[];
        pipe: boolean;
    };
    init(compositionUrl: string, jobOptions?: RenderJobOptions): Promise<void>;
    close(jobOptions?: RenderJobOptions): Promise<void>;
    cleanupStrategies(): Promise<void>;
}
