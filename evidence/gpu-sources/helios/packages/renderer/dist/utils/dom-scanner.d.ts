import { Page } from 'playwright';
import { AudioTrackConfig } from '../types.js';
export declare function scanForAudioTracks(page: Page, timeout?: number): Promise<AudioTrackConfig[]>;
