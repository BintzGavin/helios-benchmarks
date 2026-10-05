import { S3Client } from '@aws-sdk/client-s3';
import { ObjectStore, StoredObject, ByteSource } from './storage.js';
/** Inject a configured client; credentials remain with the host's provider. */
export declare class S3Store implements ObjectStore {
    private client;
    private bucket;
    private prefix;
    constructor(client: S3Client, bucket: string, prefix?: string);
    private key;
    get(key: string): Promise<StoredObject | undefined>;
    put(key: string, body: ByteSource, expected: string | null, bytes?: number): Promise<boolean>;
    list(prefix: string): AsyncIterable<string>;
}
