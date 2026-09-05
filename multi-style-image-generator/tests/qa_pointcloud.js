// Offline WebGL behavior and tolerance-based visual regression, no external resources.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('url');
const input = path.resolve(process.argv[2]);
const output = path.resolve(process.argv[3] || 'work/pointcloud-qa');
const fixture = !input.endsWith('.html');
const update = process.argv.includes('--update-baselines');
const baselinePath = path.join(__dirname, 'pointcloud-baselines.json');
const baselines = fs.existsSync(baselinePath) ? JSON.parse(fs.readFileSync(baselinePath)) : {};
const collected = {};
fs.mkdirSync(output, {recursive: true});
const diff = (a,b) => a.reduce((s,v,i) => s+Math.abs(v-b[i]),0)/a.length;
async function pixels(page) {
  return page.evaluate(() => {
    const c=document.querySelector('canvas'), gl=c.getContext('webgl');
    const data=new Uint8Array(c.width*c.height*4);
    gl.readPixels(0,0,c.width,c.height,gl.RGBA,gl.UNSIGNED_BYTE,data);
    const sample=[]; let visible=0;
    for(let by=0;by<27;by++) for(let bx=0;bx<48;bx++) {
      let sums=[0,0,0], n=0;
      for(let y=Math.floor(by*c.height/27);y<Math.floor((by+1)*c.height/27);y+=2)
        for(let x=Math.floor(bx*c.width/48);x<Math.floor((bx+1)*c.width/48);x+=2) {
          const i=(y*c.width+x)*4; for(let j=0;j<3;j++) sums[j]+=data[i+j]; n++;
          if(data[i]+data[i+1]+data[i+2]>90) visible++;
        }
      sample.push(...sums.map(v=>Math.round(v/n)));
    }
    return {sample, visible, glError:gl.getError()};
  });
}
(async()=>{
  const browser=await chromium.launch({headless:true, executablePath:process.env.CHROME_PATH || undefined,
    args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  try {
    for(const [device,viewport] of [['desktop',{width:960,height:640}],['mobile',{width:390,height:844}]]) {
      const page=await browser.newPage({viewport,hasTouch:device==='mobile'}), errors=[], requests=[];
      page.on('pageerror',e=>errors.push(String(e)));
      page.on('console',m=>{if(m.type()==='error') errors.push(m.text());});
      page.on('request',r=>{if(/^https?:/.test(r.url())) requests.push(r.url());});
      await page.goto(pathToFileURL(fixture?path.join(input,'pointcloud-visible.html'):input).href);
      await page.waitForFunction(()=>window.__pointcloudDebug?.getState().pointCount>0);
      const initial=await page.evaluate(()=>window.__pointcloudDebug.getState());
      assert(initial.pointCount>0 && initial.pointCount<initial.candidateCount,'adaptive density');
      assert.equal(await page.locator('input[type=range]:visible').count(),3);
      const samples={};
      for(const [name,seconds] of [['side-a',0],['front',3],['side-b',6]]) {
        await page.evaluate(s=>{window.__pointcloudDebug.setView(-0.48*Math.cos(s*Math.PI/6),0.12);},seconds);
        samples[name]=await pixels(page);
        assert.equal(samples[name].glError,0);
        assert(samples[name].visible>300,'empty point cloud');
        await page.screenshot({path:path.join(output,`${device}-${name}.png`)});
        const key=`${device}-${name}`;
        collected[key]=samples[name].sample;
        if(fixture&&!update) {
          assert(baselines[key],`missing baseline ${key}; review screenshots before --update-baselines`);
          assert(diff(baselines[key],collected[key])<4,`visual regression ${key}`);
        }
      }
      assert(diff(samples['side-a'].sample,samples['side-b'].sample)>1,'orbit does not change image');
      await page.evaluate(()=>window.__pointcloudDebug.setView(Math.PI*2,0.12));
      assert(diff(samples.front.sample,(await pixels(page)).sample)<.1,'full turn does not return to front');
      await page.evaluate(()=>window.__pointcloudDebug.setView(.48,0.12));
      for(const [id,value,key] of [['depthScale','1.8','depthScale'],['pointSize','3.5','pointSize'],['focus','0.3','focus']]) {
        const before=await pixels(page);
        await page.locator(`#${id}`).evaluate((e,v)=>{e.value=v;e.dispatchEvent(new Event('input'));},value);
        assert.equal((await page.evaluate(()=>window.__pointcloudDebug.getState()))[key],Number(value));
        assert(diff(before.sample,(await pixels(page)).sample)>.03,`${id} has no visual effect`);
      }
      assert.equal(await page.locator('#demo, #reset').count(),0);
      // Drag freely through multiple full turns on both axes.
      await page.locator('canvas').dispatchEvent('pointerdown',{pointerId:1,pointerType:device==='mobile'?'touch':'mouse',clientX:80,clientY:250});
      await page.locator('canvas').dispatchEvent('pointermove',{pointerId:1,clientX:10000,clientY:10000});
      await page.locator('canvas').dispatchEvent('pointerup',{pointerId:1});
      const dragged=await page.evaluate(()=>window.__pointcloudDebug.getState());
      assert(dragged.yaw>Math.PI*2);assert(dragged.pitch>Math.PI*2);
      await page.waitForTimeout(200);
      const held=await page.evaluate(()=>window.__pointcloudDebug.getState());
      assert.equal(held.yaw,dragged.yaw);assert.equal(held.pitch,dragged.pitch);
      await page.evaluate(()=>window.__pointcloudDebug.setView(Math.PI,0.12));
      assert((await pixels(page)).visible>300,"back view missing");
      await page.screenshot({path:path.join(output,`${device}-back.png`)});
      await page.evaluate(()=>window.__pointcloudDebug.setView(Math.PI*2,0.12));
      await page.locator('canvas').dispatchEvent('wheel',{deltaY:100});
      assert((await page.evaluate(()=>window.__pointcloudDebug.getState())).zoom>initial.zoom);
      assert(await page.evaluate(()=>{const r=document.querySelector('.controls').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight;}),'controls overflow');
      assert.deepEqual(requests,[],'external requests in file viewer');
      assert.deepEqual(errors,[]);
      await page.close();
    }
    if(fixture) {
      const page=await browser.newPage({viewport:{width:960,height:640}});
      for(const mode of ['mesh','pointcloud']) {
        await page.goto(pathToFileURL(path.join(input,`${mode}-hidden.html`)).href);
        await page.waitForFunction(m=>m==='mesh'?window.__spatialDebug?.getState().indexCount>0:window.__pointcloudDebug?.getState().pointCount>0,mode);
        assert.equal(await page.locator('input:visible, button:visible, .hud:visible').count(),0);
        if(mode==='mesh') {
          const count=await page.evaluate(()=>window.__spatialDebug.getState().indexCount);
          assert(count<150*84*6 && count>150*84*3,'mesh must reject discontinuity triangles only');
          await page.evaluate(()=>window.__spatialDebug.setView(.4,.1));
          assert((await pixels(page)).visible>1000);
        } else {
          await page.evaluate(()=>window.__pointcloudDebug.setView(Math.PI*2,Math.PI*2));
          assert.equal((await page.evaluate(()=>window.__pointcloudDebug.getState())).yaw,Math.PI*2);
        }
      }
      await page.close();
    }
    if(fixture&&update) fs.writeFileSync(baselinePath,JSON.stringify(collected)+'\n');
    console.log(JSON.stringify({passed:true,fixture,views:Object.keys(collected),offline:true}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
