// Documented public circle scene, fframes f89cbd572524b70a709ba3569fa23b0bbc8a0d9c.
// MIT, copyright Dmitriy Kovalenko. Retain LICENSE.fframes.txt in source packages.
export const CIRCLES_SCENE = Object.freeze({width:3840,height:2160,frames:300,fps:30,sourceStart:3,circles:99000,texts:1000,panels:20});
export function createCircles(font: Uint8Array) {
  return {width:3840,height:2160,fps:{num:30,den:1},frameCount:303,background:'#18202c',fonts:{dm:font},draw(ctx:any,{index:f,fonts}:any) {
    ctx.scale(3840/1000,2160/1000);
    for(let panel=0;panel<20;panel++) {
      ctx.save();ctx.translate(panel%5*200,Math.floor(panel/5)*250);
      for(let slot=panel*5000;slot<(panel+1)*5000;slot++) {
        if(slot%100===0)continue;
        const id=(slot+f*37)%100000;
        let radius=16+slot%4*4;
        if(slot%10===1) {
          const phase=(slot+f)%60,progress=phase<=30?phase/30:(phase-30)/30;
          const amount=progress*progress*(3-2*progress);
          radius=phase<=30?16+12*amount:28-12*amount;
        }
        const rgb=[(id*13+f*17)%256,(id*7+f*29)%256,(id*3+f*43)%256];
        ctx.fillStyle='#'+rgb.map(x=>x.toString(16).padStart(2,'0')).join('');
        ctx.beginPath();ctx.arc(32+(slot*13+f*3)%128,32+(slot*17+f*5)%176,radius,0,2*Math.PI);ctx.fill();
      }
      ctx.restore();
    }
    ctx.font=`16px ${fonts.dm}`;ctx.textBaseline='alphabetic';ctx.fillStyle='#ffffff';
    for(let slot=0;slot<100000;slot+=100) {
      const panel=Math.floor(slot/5000),index=(slot%5000)/100,id=(slot+f*37)%100000;
      ctx.fillText(String((id+f)%10),panel%5*200+24+index%10*16,Math.floor(panel/5)*250+40+Math.floor(index/10)*40);
    }
  }};
}
