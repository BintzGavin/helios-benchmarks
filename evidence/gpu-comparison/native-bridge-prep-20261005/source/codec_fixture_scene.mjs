// Retained small-scene shape semantics, used for CPU packet generation only.
export function createFixtureScene(font) {
 return {width:256,height:128,fps:{num:30000,den:1001},frameCount:300,fonts:{pinned:font},background:'#000000',draw(ctx,{index}){
  for(const [color,x,y] of [['#ff0000',0,0],['#00ff00',128,0],['#0000ff',0,64],['#ffffff',128,64]]){ctx.fillStyle=color;ctx.fillRect(x,y,128,64);}
  ctx.save();ctx.translate(128,64);ctx.rotate(index/300);ctx.fillStyle='#ffff00';ctx.beginPath();ctx.arc(24*Math.sin(index/11),0,15,0,Math.PI*2);ctx.fill();ctx.restore();
  ctx.fillStyle='#000000';ctx.font='15px pinned';ctx.fillText('Vulkan '+String(index).padStart(3,'0'),150,110);
 }};
}
