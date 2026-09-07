// Offline interaction checks for the generated panorama point-cloud viewer.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {pathToFileURL}=require('node:url');
(async()=>{
  const output=path.resolve(process.argv[3] || 'work/panorama-cloud-qa');
  fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({executablePath:process.env.CHROME_PATH || undefined,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  try {
    for(const mobile of [false,true]){
      const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1100,height:760},hasTouch:mobile});
      const page=await context.newPage(), errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.goto(pathToFileURL(path.resolve(process.argv[2])).href);
      await page.waitForFunction(()=>window.__sceneDebug?.getState().pointCount>10000);
      const state=()=>page.evaluate(()=>window.__sceneDebug.getState());
      const initial=await state();
      await page.mouse.move(100,250);await page.mouse.down();await page.mouse.move(1000,260,{steps:12});await page.mouse.up();
      assert.notEqual((await state()).yaw,initial.yaw);
      await page.evaluate(()=>{window.__sceneDebug.setView(Math.PI*4,.2);window.__sceneDebug.render();});
      assert.equal((await state()).yaw,Math.PI*4);
      await page.locator('canvas').focus();
      await page.keyboard.down('w');await page.waitForTimeout(350);await page.keyboard.up('w');
      const moved=await state();assert(Math.hypot(...moved.position)>0.2);
      await page.waitForTimeout(100);assert.deepEqual((await state()).position,moved.position);
      if(mobile){
        const button=await page.locator('[data-key="e"]').boundingBox();
        await page.mouse.move(button.x+button.width/2,button.y+button.height/2);
        await page.mouse.down();
        await page.waitForTimeout(200);
        await page.mouse.up();
        assert((await state()).position[1]>moved.position[1]);
      }
      const beforeReload=await state();
      await page.reload();await page.waitForFunction(()=>window.__sceneDebug);
      assert.deepEqual((await state()).position,beforeReload.position);
      assert.equal((await state()).yaw,beforeReload.yaw);
      await page.locator('#size').fill('0.8');assert.equal((await state()).size,.8);
      assert.equal(await page.locator('#reset,#demo').count(),0);
      assert(await page.locator('.controls').evaluate(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight;}));
      await page.screenshot({path:path.join(output,mobile?'mobile.png':'desktop.png')});
      assert.deepEqual(errors,[]);console.log(`${mobile?'mobile':'desktop'} panorama controls passed`);
      await context.close();
    }
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
