import { spawn } from 'child_process';
import ffmpeg from '@ffmpeg-installer/ffmpeg';
export class FFmpegManager {
    options;
    jobOptions;
    process = null;
    startPromise = null;
    ffmpegPath;
    constructor(options, jobOptions) {
        this.options = options;
        this.jobOptions = jobOptions;
        this.ffmpegPath = this.options.ffmpegPath || ffmpeg.path;
    }
    spawn(args, inputBuffers) {
        const stdio = ['pipe', 'pipe', 'pipe'];
        const maxPipeIndex = Math.max(...inputBuffers.map(b => b.index), 2);
        while (stdio.length <= maxPipeIndex) {
            stdio.push('pipe');
        }
        this.process = spawn(this.ffmpegPath, args, { stdio });
        this.startPromise = new Promise((resolve, reject) => {
            this.process.once('spawn', resolve);
            this.process.once('error', reject);
        });
        console.log(`Spawning FFmpeg: ${this.ffmpegPath} ${args.join(' ')}`);
        if (this.process.stdin) {
            this.process.stdin.on('error', (err) => {
                if (err && err.code === 'EPIPE') {
                    console.warn('FFmpeg stdin closed prematurely (EPIPE). Ignoring error to allow graceful exit.');
                }
                else {
                    console.error('Error writing to FFmpeg stdin:', err);
                }
            });
        }
        inputBuffers.forEach(({ index, buffer }) => {
            const pipe = this.process.stdio[index];
            if (pipe) {
                pipe.on('error', (err) => {
                    if (err && err.code === 'EPIPE') {
                        console.warn(`Pipe ${index} closed prematurely (EPIPE). Ignoring.`);
                    }
                    else {
                        console.error(`Error writing to pipe ${index}:`, err);
                    }
                });
                pipe.write(buffer);
                pipe.end();
            }
            else {
                console.error(`Failed to get pipe ${index} from FFmpeg process`);
            }
        });
        this.process.stderr.on('data', (data) => {
            console.error(`ffmpeg: ${data.toString()}`);
        });
        return this.process;
    }
    waitUntilStarted() {
        if (!this.startPromise) {
            return Promise.reject(new Error('FFmpeg process not spawned'));
        }
        return this.startPromise;
    }
    getExitPromise(capturedErrors) {
        if (!this.process)
            return Promise.reject(new Error('FFmpeg process not spawned'));
        return new Promise((resolve, reject) => {
            this.process.on('close', (code) => {
                if (code === 0) {
                    resolve();
                }
                else {
                    if (this.jobOptions?.signal?.aborted || capturedErrors.length > 0) {
                        resolve();
                    }
                    else {
                        reject(new Error(`FFmpeg process exited with code ${code}`));
                    }
                }
            });
            this.process.on('error', (err) => {
                if (this.jobOptions?.signal?.aborted || capturedErrors.length > 0) {
                    resolve();
                }
                else {
                    reject(err);
                }
            });
        });
    }
    kill() {
        if (this.process) {
            for (const stream of this.process.stdio) {
                if (stream && typeof stream.destroy === 'function') {
                    stream.destroy();
                }
            }
            if (this.process.exitCode === null && this.process.signalCode === null) {
                this.process.kill('SIGKILL');
            }
        }
    }
    get stdin() {
        return this.process?.stdin;
    }
    emitError(err) {
        this.process?.emit('error', err);
    }
}
