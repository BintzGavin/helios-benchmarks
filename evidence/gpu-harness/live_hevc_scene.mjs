// Bounded live-only acceptance scene; source indices3..38. Painted chroma
// control is predetermined: each2x2 cell has3red pixels and1blue pixel.
import {createFixtureScene} from './codec_fixture_scene.mjs';
export function createLiveHevcScene(font){
 const base=createFixtureScene(font);
 return {...base,fps:{num:30,den:1},frameCount:303,draw(ctx,info){
  base.draw(ctx,info);
  for(let y=96;y<112;y++)for(let x=16;x<80;x++){
   ctx.fillStyle=(x%2===1&&y%2===1)?'#0000ff':'#ff0000';ctx.fillRect(x,y,1,1);
  }
 }};
}
