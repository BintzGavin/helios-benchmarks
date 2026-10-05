import { Page } from 'playwright';
import { AudioTrackConfig } from '../types.js';
export interface BlobExtractionResult {
    tracks: AudioTrackConfig[];
    cleanup: () => Promise<void>;
}
export declare function extractBlobTracks(page: Page, tracks: AudioTrackConfig[]): Promise<BlobExtractionResult>;
