import type { JobView } from './jobs.js';
export declare class RenderClientError extends Error {
    code: string;
    status: number;
    constructor(code: string, message: string, status: number);
}
export interface ClientOptions {
    fetch?: typeof fetch;
    headers?: HeadersInit | (() => Promise<HeadersInit>);
    pollMs?: number;
    retryMs?: number;
    retries?: number;
}
export interface WaitOptions {
    signal?: AbortSignal;
    drive?: boolean;
    timeoutMs?: number;
    onProgress?: (job: JobView) => void | Promise<void>;
}
/** Workflow-friendly SDK. Host authentication is supplied by the caller. */
export declare class RenderClient {
    private baseUrl;
    private options;
    constructor(baseUrl: string, options?: ClientOptions);
    private request;
    upload(bytes: Uint8Array, signal?: AbortSignal): Promise<{
        sha256: string;
        bytes: number;
    }>;
    submit(plan: unknown, idempotencyKey: string, signal?: AbortSignal): Promise<JobView>;
    get(id: string, signal?: AbortSignal): Promise<JobView>;
    advance(id: string, signal?: AbortSignal): Promise<JobView>;
    cancel(id: string, signal?: AbortSignal): Promise<JobView>;
    download(id: string, signal?: AbortSignal): Promise<Response>;
    wait(id: string, options?: WaitOptions): Promise<JobView>;
    render(plan: unknown, options: WaitOptions & {
        idempotencyKey: string;
    }): Promise<JobView>;
}
