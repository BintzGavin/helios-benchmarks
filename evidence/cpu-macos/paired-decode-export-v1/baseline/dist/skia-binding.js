import { createRequire } from 'node:module';
// Pinned binding entry point avoids the package wrapper's implicit system/user
// font-directory scan. All rendered text already consists of explicit glyph paths.
const binding = createRequire(import.meta.url)('@napi-rs/canvas/js-binding.js');
export const GlobalFonts = binding.GlobalFonts;
export const Path2D = binding.Path;
export const ImageData = binding.ImageData;
export function createCanvas(width, height) { return new binding.CanvasElement(width, height); }
export async function loadImage(bytes) {
    const image = new binding.Image();
    const loaded = new Promise((resolve, reject) => { image.onload = () => resolve(image); image.onerror = reject; });
    image.src = bytes;
    return loaded;
}
