const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const file = path.resolve(process.argv[2]);
const shotDir = path.resolve(process.argv[3] || 'work/spatial-v18-qa');
fs.mkdirSync(shotDir, { recursive: true });

async function sampleCanvas(page) {
  return page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    const gl = canvas && canvas.getContext('webgl');
    if (!gl) return { visibleRatio: 0, sample: [], width: 0, height: 0 };
    const pixels = new Uint8Array(canvas.width * canvas.height * 4);
    gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    const stride = Math.max(4, Math.floor(pixels.length / 18000 / 4) * 4);
    const sample = [];
    let visible = 0;
    for (let i = 0; i < pixels.length; i += stride) {
      sample.push(pixels[i], pixels[i + 1], pixels[i + 2]);
      if (pixels[i] + pixels[i + 1] + pixels[i + 2] > 30) visible += 1;
    }
    return { visibleRatio: visible / (sample.length / 3), sample, width: canvas.width, height: canvas.height };
  });
}

function difference(a, b) {
  let sum = 0;
  const length = Math.min(a.length, b.length);
  for (let i = 0; i < length; i++) sum += Math.abs(a[i] - b[i]);
  return length ? sum / length : 0;
}

async function openViewer(browser, viewport) {
  const page = await browser.newPage({ viewport });
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.goto(`file://${file}`);
  await page.waitForFunction(
    () => window.__spatialDebug && window.__spatialDebug.getState().indexCount > 0,
    null,
    { timeout: 30000 }
  );
  return { page, errors };
}

(async () => {
  if (!process.argv[2]) throw new Error('usage: node qa_spatial_v18.js VIEWER.html [SCREENSHOT_DIR]');
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROME_PATH || undefined,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
  });
  const desktop = await openViewer(browser, { width: 1440, height: 900 });
  const samples = {};
  for (const [name, x, y] of [['left', -0.5, 0], ['center', 0, 0], ['right', 0.5, 0]]) {
    await desktop.page.evaluate(([vx, vy]) => window.__spatialDebug.setView(vx, vy), [x, y]);
    await desktop.page.waitForTimeout(250);
    await desktop.page.screenshot({ path: path.join(shotDir, `desktop-${name}.png`) });
    samples[name] = await sampleCanvas(desktop.page);
  }
  const layout = await desktop.page.evaluate(() => ({
    controls: document.querySelectorAll('.controls').length,
    sliders: document.querySelectorAll('.controls input[type="range"]').length,
    buttons: document.querySelectorAll('.controls button').length,
    overflowX: document.documentElement.scrollWidth > innerWidth,
    overflowY: document.documentElement.scrollHeight > innerHeight,
    webgl: Boolean(document.querySelector('canvas').getContext('webgl')),
  }));
  const leftRight = difference(samples.left.sample, samples.right.sample);
  const controlsWork = await desktop.page.evaluate(() => {
    const depth = document.getElementById('depthScale');
    const motion = document.getElementById('motion');
    const perspective = document.getElementById('perspective');
    depth.value = '0.62';
    motion.value = '0.56';
    perspective.value = '1.35';
    depth.dispatchEvent(new Event('input', { bubbles: true }));
    motion.dispatchEvent(new Event('input', { bubbles: true }));
    perspective.dispatchEvent(new Event('input', { bubbles: true }));
    document.getElementById('autoToggle').click();
    const state = window.__spatialDebug.getState();
    return {
      depthScale: state.depthScale,
      motion: state.motion,
      perspective: state.perspective,
      auto: state.auto,
    };
  });
  Object.values(samples).forEach(sample => delete sample.sample);
  await desktop.page.close();

  const mobile = await openViewer(browser, { width: 390, height: 844 });
  await mobile.page.evaluate(() => window.__spatialDebug.setView(0.42, -0.18));
  await mobile.page.waitForTimeout(250);
  await mobile.page.screenshot({ path: path.join(shotDir, 'mobile.png') });
  const mobileSample = await sampleCanvas(mobile.page);
  delete mobileSample.sample;
  const mobileLayout = await mobile.page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth > innerWidth,
    overflowY: document.documentElement.scrollHeight > innerHeight,
  }));
  await mobile.page.close();
  await browser.close();

  const result = {
    desktop: { layout, samples, leftRight, controlsWork, errors: desktop.errors },
    mobile: { sample: mobileSample, layout: mobileLayout, errors: mobile.errors },
  };
  console.log(JSON.stringify(result, null, 2));
  const failures = [];
  if (!layout.webgl) failures.push('WebGL unavailable');
  if (layout.controls !== 1 || layout.sliders !== 3 || layout.buttons !== 1) failures.push('expected spatial controls not found');
  if (controlsWork.depthScale !== 0.62 || controlsWork.motion !== 0.56 || controlsWork.perspective !== 1.35 || controlsWork.auto !== false) failures.push('spatial controls did not update viewer state');
  if (layout.overflowX || layout.overflowY || mobileLayout.overflowX || mobileLayout.overflowY) failures.push('layout overflow');
  if (samples.center.visibleRatio < 0.2 || mobileSample.visibleRatio < 0.2) failures.push('canvas mostly empty');
  if (leftRight < 0.25) failures.push(`left/right pixel difference too small: ${leftRight}`);
  if (desktop.errors.length || mobile.errors.length) failures.push('JavaScript/WebGL console errors');
  if (failures.length) throw new Error(failures.join('; '));
})().catch(error => {
  console.error(error);
  process.exit(1);
});
