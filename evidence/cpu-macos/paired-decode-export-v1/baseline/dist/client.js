import { sha256 as sha256Hash } from '@noble/hashes/sha2.js';
export class RenderClientError extends Error {
    code;
    status;
    constructor(code, message, status) {
        super(message);
        this.code = code;
        this.status = status;
    }
}
/** Workflow-friendly SDK. Host authentication is supplied by the caller. */
export class RenderClient {
    baseUrl;
    options;
    constructor(baseUrl, options = {}) {
        this.baseUrl = baseUrl;
        this.options = options;
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }
    async request(path, init = {}) {
        for (let attempt = 0;; attempt++) {
            init.signal?.throwIfAborted();
            try {
                const headers = new Headers(typeof this.options.headers === 'function' ? await this.options.headers() : this.options.headers);
                new Headers(init.headers).forEach((value, key) => headers.set(key, value));
                const response = await (this.options.fetch ?? fetch)(`${this.baseUrl}${path}`, { ...init, headers, redirect: 'error' });
                if (response.ok)
                    return response;
                const body = await response.json().catch(() => ({}));
                throw new RenderClientError(body.error?.code ?? 'HTTP_ERROR', body.error?.message ?? 'Render request failed', response.status);
            }
            catch (error) {
                if (init.signal?.aborted)
                    throw init.signal.reason;
                if (attempt >= (this.options.retries ?? 2) || (error instanceof RenderClientError && ![408, 429, 500, 502, 503, 504].includes(error.status)))
                    throw error;
                await delay((this.options.retryMs ?? 250) * 2 ** attempt, init.signal ?? undefined);
            }
        }
    }
    async upload(bytes, signal) {
        const data = new Uint8Array(bytes), hash = await crypto.subtle.digest('SHA-256', data);
        const sha256 = Array.from(new Uint8Array(hash), n => n.toString(16).padStart(2, '0')).join('');
        if (data.length > 2 * 1024 * 1024) {
            const parts = [];
            for (let offset = 0; offset < data.length; offset += 2 * 1024 * 1024)
                parts.push((await this.upload(data.subarray(offset, offset + 2 * 1024 * 1024), signal)).sha256);
            return (await this.request(`/v1/assets/${sha256}/compose`, { method: 'POST', signal, headers: { 'content-type': 'application/json' }, body: JSON.stringify({ parts, bytes: data.length }) })).json();
        }
        return (await this.request(`/v1/assets/${sha256}`, { method: 'PUT', body: data, signal, headers: { 'content-type': 'application/octet-stream' } })).json();
    }
    async submit(plan, idempotencyKey, signal) { return (await this.request('/v1/renders', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ idempotencyKey, plan }), signal })).json(); }
    async get(id, signal) { return (await this.request(`/v1/renders/${encodeURIComponent(id)}`, { signal })).json(); }
    async advance(id, signal) { return (await this.request(`/v1/renders/${encodeURIComponent(id)}/advance`, { method: 'POST', signal })).json(); }
    async cancel(id, signal) { return (await this.request(`/v1/renders/${encodeURIComponent(id)}/cancel`, { method: 'POST', signal })).json(); }
    async download(id, signal) {
        const job = await this.get(id, signal);
        if (job.state !== 'succeeded' || !job.output)
            throw new RenderClientError('NOT_READY', 'No completed artifact is available', 409);
        const client = this, size = job.output.bytes, hash = sha256Hash.create(), expected = job.output.sha256;
        let offset = 0;
        const stream = new ReadableStream({
            async pull(controller) {
                try {
                    if (offset >= size) {
                        const actual = Array.from(hash.digest(), value => value.toString(16).padStart(2, '0')).join('');
                        if (actual !== expected)
                            throw new RenderClientError('CORRUPT_ARTIFACT', 'Downloaded video failed its checksum integrity check', 502);
                        controller.close();
                        return;
                    }
                    const response = await client.request(`/v1/renders/${encodeURIComponent(id)}/artifact`, { signal, headers: { range: `bytes=${offset}-${Math.min(size - 1, offset + 2 * 1024 * 1024 - 1)}` } });
                    if (response.status !== 206)
                        throw new RenderClientError('INVALID_RANGE', 'Server did not honor the artifact range', 502);
                    const bytes = new Uint8Array(await response.arrayBuffer());
                    if (!bytes.length || bytes.length > 2 * 1024 * 1024 || offset + bytes.length > size)
                        throw new RenderClientError('INVALID_RANGE', 'Server returned an invalid artifact range', 502);
                    if (response.headers.get('content-range') !== `bytes ${offset}-${offset + bytes.length - 1}/${size}`)
                        throw new RenderClientError('INVALID_RANGE', 'Server returned a mismatched artifact range', 502);
                    hash.update(bytes);
                    offset += bytes.length;
                    controller.enqueue(bytes);
                }
                catch (error) {
                    controller.error(error);
                }
            },
        });
        return new Response(stream, { headers: { 'content-type': 'video/mp4', 'content-length': String(size) } });
    }
    async wait(id, options = {}) {
        const timeout = new AbortController(), signal = options.signal ? AbortSignal.any([options.signal, timeout.signal]) : timeout.signal;
        const timer = setTimeout(() => timeout.abort(new RenderClientError('WAIT_TIMEOUT', 'Waiting timed out; the durable render job can be reattached', 408)), options.timeoutMs ?? 30 * 60 * 1000);
        try {
            for (;;) {
                signal.throwIfAborted();
                const job = options.drive === false ? await this.get(id, signal) : await this.advance(id, signal);
                await options.onProgress?.(job);
                if (job.state === 'succeeded')
                    return job;
                if (job.state === 'failed' || job.state === 'canceled')
                    throw new RenderClientError(job.error?.code ?? job.state.toUpperCase(), job.error?.message ?? `Render ${job.state}`, 409);
                await delay(this.options.pollMs ?? 500, signal);
            }
        }
        finally {
            clearTimeout(timer);
        }
    }
    async render(plan, options) {
        const job = await this.submit(plan, options.idempotencyKey, options.signal);
        return this.wait(job.id, options);
    }
}
function delay(ms, signal) {
    signal?.throwIfAborted();
    return new Promise((resolve, reject) => {
        const timer = setTimeout(done, ms);
        function done() { signal?.removeEventListener('abort', abort); resolve(); }
        function abort() { clearTimeout(timer); reject(signal?.reason); }
        signal?.addEventListener('abort', abort, { once: true });
    });
}
