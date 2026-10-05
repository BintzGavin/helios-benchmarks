/** No shell, environment inspection, or unbounded diagnostic buffers. */
export declare function startProcess(command: string, args: string[], options?: {
    signal?: AbortSignal;
    timeoutMs?: number;
}): {
    child: import("node:child_process").ChildProcessWithoutNullStreams;
    done: Promise<void>;
    kill: () => void;
    diagnostic: () => string;
};
export declare function runProcess(command: string, args: string[], options?: {
    signal?: AbortSignal;
    timeoutMs?: number;
    maxBytes?: number;
}): Promise<Buffer>;
