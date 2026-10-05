export interface FFmpegDiagnostics {
    path: string;
    present: boolean;
    version?: string;
    encoders: string[];
    filters: string[];
    hwaccels: string[];
    error?: string;
}
export declare class FFmpegInspector {
    static inspect(ffmpegPath: string): FFmpegDiagnostics;
}
