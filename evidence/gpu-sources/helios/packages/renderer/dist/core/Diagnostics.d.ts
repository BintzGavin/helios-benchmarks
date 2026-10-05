import { RendererOptions } from '../types.js';
export declare class Diagnostics {
    private options;
    constructor(options: RendererOptions);
    run(): Promise<any>;
    validateHardwareAcceleration(): void;
}
