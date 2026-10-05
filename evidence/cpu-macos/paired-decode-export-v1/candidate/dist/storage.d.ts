export type ByteSource = Uint8Array | AsyncIterable<Uint8Array>;
export interface StoredObject {
    version: string;
    size: number;
    stream(range?: {
        start: number;
        end: number;
    }): AsyncIterable<Uint8Array>;
}
export interface ObjectStore {
    get(key: string): Promise<StoredObject | undefined>;
    /** null means create only; an observed version means compare-and-swap. */
    put(key: string, body: ByteSource, expected: string | null, bytes?: number): Promise<boolean>;
    list(prefix: string): AsyncIterable<string>;
}
export declare const digest: (data: string | Uint8Array) => string;
export declare function safeKey(key: string): string;
export declare function byteChunks(body: ByteSource): AsyncIterable<Uint8Array>;
export declare function readBytes(object: StoredObject, limit: number): Promise<Buffer>;
export declare const jsonBytes: (value: unknown) => Uint8Array;
export declare function readJson<T>(object: StoredObject, limit?: number): Promise<T>;
/**
 * Each immutable numbered revision is committed by an exclusive hard link.
 * Competing writers for revision n+1 cannot both win; no expiring filesystem
 * lock can let a stale writer overwrite newer state. Requires a local filesystem
 * with atomic hard links and fsync, not an object-store/FUSE mount.
 */
export declare class FileStore implements ObjectStore {
    private root;
    constructor(directory: string);
    private directory;
    get(key: string): Promise<StoredObject | undefined>;
    put(key: string, body: ByteSource, expected: string | null): Promise<boolean>;
    list(prefix: string): AsyncIterable<string>;
}
