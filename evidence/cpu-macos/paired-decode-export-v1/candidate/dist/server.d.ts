import { IncomingMessage, ServerResponse } from 'node:http';
import { RenderService } from './jobs.js';
export interface HandlerOptions {
    authorize(request: Request): Promise<string | null>;
    maxUploadBytes?: number;
    maxDownloadBytes?: number;
}
/** Web-standard handler; authentication/tenant lookup is supplied by the host. */
export declare function createRenderHandler(service: RenderService, options: HandlerOptions): (request: Request) => Promise<Response>;
export declare function nodeHandler(handler: (request: Request) => Promise<Response>): (incoming: IncomingMessage, outgoing: ServerResponse) => Promise<void>;
export declare function createRenderServer(service: RenderService, options: HandlerOptions): import("node:http").Server<typeof IncomingMessage, typeof ServerResponse>;
/** Durable state drives this loop; a restart resumes jobs through expiring leases. */
export declare function runWorker(service: RenderService, signal: AbortSignal, intervalMs?: number): Promise<void>;
