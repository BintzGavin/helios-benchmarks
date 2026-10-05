import assert from 'node:assert/strict';
import {createCircles,CIRCLES_SCENE} from './circles-scene.mts';
const near=(a:number,b:number)=>assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
async function inspect(index:number) {
  let state={a:1,d:1,e:0,f:0},stack:any[]=[],path:any,firstCircle:any,lastCircle:any,firstText:any,lastText:any,circles=0,texts=0,textStarted=false;
  const ctx:any={fillStyle:'',font:'',textBaseline:'',scale(a:number,d:number){state.a*=a;state.d*=d},save(){stack.push({...state})},restore(){state=stack.pop()},translate(x:number,y:number){state.e+=state.a*x;state.f+=state.d*y},beginPath(){path=undefined},arc(x:number,y:number,r:number,start:number,end:number){assert.equal(textStarted,false);assert.equal(start,0);assert.equal(end,2*Math.PI);assert.ok(r>=16&&r<=28);path={x:state.a*x+state.e,y:state.d*y+state.f,r,fill:ctx.fillStyle}},fill(){assert.ok(path);circles++;firstCircle??={...path};lastCircle={...path}},fillText(text:string,x:number,y:number){textStarted=true;assert.match(text,/^\d$/);assert.equal(ctx.font,'16px dm');assert.equal(ctx.textBaseline,'alphabetic');assert.equal(ctx.fillStyle,'#ffffff');const t={text,x:state.a*x+state.e,y:state.d*y+state.f};firstText??=t;lastText=t;texts++}};
  const scene=createCircles(new Uint8Array());await scene.draw(ctx,{index,fonts:{dm:'dm'}});
  assert.equal(circles,99000);assert.equal(texts,1000);assert.equal(stack.length,0);assert.equal(scene.frameCount,303);
  return {firstCircle,lastCircle,firstText,lastText};
}
const f3=await inspect(3);near(f3.firstCircle.x,207.36);near(f3.firstCircle.y,138.24);near(f3.firstCircle.r,16.58311111111111);assert.equal(f3.firstCircle.fill,'#e367d1');near(f3.lastCircle.x,3302.4);near(f3.lastCircle.y,1719.36);assert.equal(f3.lastCircle.r,28);assert.equal(f3.firstText.text,'4');near(f3.firstText.x,92.16);near(f3.firstText.y,86.4);near(f3.lastText.x,3717.12);near(f3.lastText.y,2052);
const f302=await inspect(302);near(f302.firstCircle.x,211.2);near(f302.firstCircle.y,326.16);near(f302.firstCircle.r,16.336);assert.equal(f302.firstCircle.fill,'#89c7af');assert.equal(f302.firstText.text,'6');
const f3Again=await inspect(3);assert.deepEqual(f3Again,f3);assert.equal(CIRCLES_SCENE.sourceStart+CIRCLES_SCENE.frames,303);
console.log(JSON.stringify({passed:true,counts:'99000 circles then1000 digits',goldenSourceFrames:[3,302],shuffledReplay:true,nonuniformScale:[3.84,2.16]}));
