import { Page } from 'playwright';
import { TimeDriver } from './TimeDriver.js';
export declare class CdpTimeDriver implements TimeDriver {
    private timePromise;
    private client;
    private currentTime;
    private timeout;
    private setVirtualTimePolicyParams;
    private executionContextIds;
    private singleFrameSyncMediaParams;
    private multiFrameSyncMediaParams;
    private hasMedia;
    private syncMediaFn;
    private mode;
    private handleSyncMediaError;
    private handleVirtualTimeBudgetExpired;
    private waitUntilStable;
    private setCanvasTime;
    private setDomTime;
    constructor(timeout?: number, mode?: string);
    init(page: Page, seed?: number): Promise<void>;
    private handleExecutionContextCreated;
    prepare(page: Page): Promise<void>;
    setTime(page: Page, timeInSeconds: number): Promise<void> | void;
}
