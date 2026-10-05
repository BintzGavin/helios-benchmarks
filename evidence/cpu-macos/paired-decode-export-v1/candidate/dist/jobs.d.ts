import { ObjectStore, StoredObject, ByteSource } from './storage.js';
import { RenderBackend } from './backend.js';
export type JobState = 'queued' | 'preparing' | 'rendering' | 'finalizing' | 'succeeded' | 'failed' | 'canceled';
export interface JobView {
    id: string;
    state: JobState;
    completedChunks: number;
    totalChunks: number;
    progress: number;
    createdAt: number;
    updatedAt: number;
    error?: {
        code: string;
        message: string;
    };
    output?: {
        sha256: string;
        bytes: number;
    };
    engine: string;
}
export interface ServiceOptions {
    workspace: string;
    chunkFrames?: number;
    leaseMs?: number;
    pollMs?: number;
    maxAttempts?: number;
    maxConcurrent?: number;
    maxStepMs?: number;
    maxDurationSeconds?: number;
    maxWorkBytes?: number;
    now?: () => number;
}
export declare class RenderService {
    readonly store: ObjectStore;
    readonly backend: RenderBackend;
    readonly options: ServiceOptions;
    private controllers;
    private now;
    private leaseMs;
    private active;
    constructor(store: ObjectStore, backend: RenderBackend, options: ServiceOptions);
    upload(tenant: string, sha256: string, body: ByteSource, expectedBytes?: number): Promise<{
        sha256: string;
        bytes: number;
    }>;
    composeAsset(tenant: string, sha256: string, parts: string[], bytes: number): Promise<{
        sha256: string;
        bytes: number;
    }>;
    submit(tenant: string, idempotencyKey: string, input: unknown): Promise<JobView>;
    private load;
    get(tenant: string, id: string): Promise<JobView>;
    cancel(tenant: string, id: string): Promise<JobView>;
    artifact(tenant: string, id: string): Promise<StoredObject>;
    private materialize;
    private persist;
    private verifyObject;
    /** One bounded durable step. Safe to await inside a function invocation. */
    advance(tenant: string, id: string): Promise<JobView>;
    shutdown(): void;
    private advanceOwned;
    pending(): AsyncIterable<{
        tenant: string;
        id: string;
    }>;
}
