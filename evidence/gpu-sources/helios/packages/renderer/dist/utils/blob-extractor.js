export async function extractBlobTracks(page, tracks) {
    const updatedTracks = [];
    for (const track of tracks) {
        if (track.path && track.path.startsWith('blob:')) {
            console.log(`[BlobExtractor] Extracting audio from blob: ${track.path}`);
            // Fetch blob content as base64 and type
            const extraction = await page.evaluate(async (blobUrl) => {
                try {
                    const response = await fetch(blobUrl);
                    const blob = await response.blob();
                    return new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onloadend = () => {
                            const result = reader.result;
                            // result format: "data:application/octet-stream;base64,ABC..."
                            const base64 = result.split(',')[1];
                            resolve({ base64, type: blob.type });
                        };
                        reader.onerror = () => resolve({ error: 'Failed to read blob' });
                        reader.readAsDataURL(blob);
                    });
                }
                catch (e) {
                    return { error: e.message };
                }
            }, track.path);
            if ('error' in extraction) {
                console.warn(`[BlobExtractor] Failed to extract blob ${track.path}: ${extraction.error}`);
                // Do not add the track to updatedTracks if extraction fails.
                // Passing a raw 'blob:' URL to FFmpeg will cause it to crash.
                continue;
            }
            const buffer = Buffer.from(extraction.base64, 'base64');
            console.log(`[BlobExtractor] Extracted blob content to memory (${buffer.length} bytes)`);
            updatedTracks.push({
                ...track,
                buffer: buffer,
                path: 'blob-memory' // Placeholder, will be replaced by pipe path in FFmpegBuilder
            });
        }
        else {
            updatedTracks.push(track);
        }
    }
    const cleanup = async () => {
        // No temp files to clean up
        return Promise.resolve();
    };
    return {
        tracks: updatedTracks,
        cleanup
    };
}
