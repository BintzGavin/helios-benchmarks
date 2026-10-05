export interface ConcatOptions {
    /**
     * Path to the FFmpeg binary.
     * Defaults to the binary provided by @ffmpeg-installer/ffmpeg.
     */
    ffmpegPath?: string;
}
/**
 * Concatenates multiple video files into a single video file using FFmpeg's concat demuxer.
 * This performs a stream copy (no re-encoding), so all inputs must have the same codecs and streams.
 *
 * @param inputPaths Array of paths to input video files
 * @param outputPath Path to the output video file
 * @param options Configuration options
 */
export declare function concatenateVideos(inputPaths: string[], outputPath: string, options?: ConcatOptions): Promise<void>;
