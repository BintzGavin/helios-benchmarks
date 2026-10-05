import { Renderer } from '../Renderer.js';
export class LocalExecutor {
    async render(compositionUrl, outputPath, options, jobOptions) {
        const renderer = new Renderer(options);
        await renderer.render(compositionUrl, outputPath, jobOptions);
    }
}
