import { Font } from 'fontkit';
import { Node } from './plan.js';
export interface TextLayout {
    width: number;
    lines: string[];
    svg: string;
    glyphIds: number[][];
    paths: {
        d: string;
        x: number;
        y: number;
        scale: number;
    }[];
}
export declare function loadFont(bytes: Uint8Array): Font;
export declare function layoutText(node: Node, width: number, fonts: Map<string, Font>): TextLayout;
