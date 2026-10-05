import { HeadObjectCommand, GetObjectCommand, PutObjectCommand, ListObjectsV2Command } from '@aws-sdk/client-s3';
import { Readable } from 'node:stream';
import { safeKey } from './storage.js';
import { RenderError } from './plan.js';
/** Inject a configured client; credentials remain with the host's provider. */
export class S3Store {
    client;
    bucket;
    prefix;
    constructor(client, bucket, prefix = 'helios/') {
        this.client = client;
        this.bucket = bucket;
        this.prefix = prefix;
        if (!bucket || !/^[a-zA-Z0-9/_-]*$/.test(prefix))
            throw new Error('Invalid S3 store configuration');
    }
    key(key) { return this.prefix + safeKey(key); }
    async get(key) {
        const input = { Bucket: this.bucket, Key: this.key(key) };
        let head;
        try {
            head = await this.client.send(new HeadObjectCommand(input));
        }
        catch (error) {
            if (error.$metadata?.httpStatusCode === 404)
                return undefined;
            throw error;
        }
        if (!head.ETag || head.ContentLength === undefined)
            throw new RenderError('STORAGE_ERROR', 'Object store omitted required metadata', 503);
        if (head.ContentLength <= 8 * 1024 * 1024) {
            const result = await this.client.send(new GetObjectCommand(input));
            if (!result.Body || !result.ETag)
                throw new RenderError('STORAGE_ERROR', 'Object store returned no body', 503);
            const bytes = await result.Body.transformToByteArray();
            if (bytes.length > 8 * 1024 * 1024)
                throw new RenderError('RESOURCE_LIMIT', 'Small object changed beyond its size bound');
            return { version: result.ETag, size: bytes.length, stream: async function* (range) { yield range ? bytes.subarray(range.start, range.end + 1) : bytes; } };
        }
        const client = this.client, version = head.ETag;
        return { version, size: head.ContentLength, stream: async function* (range) {
                const result = await client.send(new GetObjectCommand({ ...input, IfMatch: version, ...(range ? { Range: `bytes=${range.start}-${range.end}` } : {}) }));
                if (!result.Body)
                    throw new RenderError('STORAGE_ERROR', 'Object store returned no body', 503);
                yield* result.Body;
            } };
    }
    async put(key, body, expected, bytes) {
        const length = body instanceof Uint8Array ? body.length : bytes;
        if (length === undefined || !Number.isSafeInteger(length) || length < 0)
            throw new RenderError('STORAGE_ERROR', 'Streaming uploads require a known content length', 500);
        try {
            await this.client.send(new PutObjectCommand({ Bucket: this.bucket, Key: this.key(key), Body: body instanceof Uint8Array ? body : Readable.from(body), ContentLength: length, ...(expected === null ? { IfNoneMatch: '*' } : { IfMatch: expected }) }));
            return true;
        }
        catch (error) {
            const status = error.$metadata?.httpStatusCode;
            if (status === 409 || status === 412)
                return false;
            throw error;
        }
    }
    async *list(prefix) {
        let cursor;
        do {
            const page = await this.client.send(new ListObjectsV2Command({ Bucket: this.bucket, Prefix: this.prefix + prefix, ContinuationToken: cursor }));
            for (const object of page.Contents ?? [])
                if (object.Key)
                    yield object.Key.slice(this.prefix.length);
            cursor = page.IsTruncated ? page.NextContinuationToken : undefined;
            if (page.IsTruncated && !cursor)
                throw new RenderError('STORAGE_ERROR', 'Object listing omitted a continuation token', 503);
        } while (cursor);
    }
}
