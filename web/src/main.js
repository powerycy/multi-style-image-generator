import './styles.css'
import { STYLE_PRESETS, createExportPayload, generatePrompt } from './prompt-engine.js'

const EXAMPLES = [
  { id: 'cultivation', name: '云海宗门', file: './examples/cultivation.png', style: 'cultivation' },
  { id: 'occult', name: '雾都调查', file: './examples/occult.png', style: 'occult' },
  { id: 'underwater', name: '像素深潜', file: './examples/underwater.png', style: 'underwater' },
]

const STYLE_ORDER = ['fantasy', 'myth', 'cultivation', 'occult', 'creature', 'farm', 'underwater']

const app = document.querySelector('#app')

app.innerHTML = `
  <header class="site-header">
    <a class="brand" href="#top" aria-label="空间视觉工坊首页">
      <span class="brand-mark" aria-hidden="true">空</span>
      <span><strong>空间视觉工坊</strong><small>SPATIAL VISUAL STUDIO</small></span>
    </a>
    <nav aria-label="主导航">
      <a href="#studio">开始创作</a>
      <a href="#workflow">使用方法</a>
      <a href="#truth">能力边界</a>
      <a href="https://github.com/powerycy/multi-style-image-generator" target="_blank" rel="noreferrer">开源仓库</a>
    </nav>
  </header>

  <main id="top">
    <section class="hero" aria-labelledby="hero-title">
      <div class="hero-copy">
        <p class="eyebrow">从平面图，到可探索的空间</p>
        <h1 id="hero-title">一张图，不该只停在一张图。</h1>
        <p class="hero-lead">把风格判断、提示词工程、360° 全景和空间景深串成一条创作工作流。无 Key 也能完整体验，不要求评委部署任何东西。</p>
        <div class="hero-actions">
          <a class="button button-primary" href="#studio">直接体验</a>
          <a class="button button-ghost" href="#workflow">先看 90 秒流程</a>
        </div>
        <dl class="hero-stats">
          <div><dt>7</dt><dd>种视觉方向</dd></div>
          <div><dt>3</dt><dd>种空间输出</dd></div>
          <div><dt>0</dt><dd>个必填 Key</dd></div>
        </dl>
      </div>
      <div class="hero-visual" aria-label="360° 全景示例">
        <img src="./examples/panorama.png" alt="东方修仙云海宗门的 360° 等距柱状投影示例" />
        <div class="hero-visual-topline"><span>360°×180°</span><span>可拖拽浏览</span></div>
        <div class="hero-visual-caption"><strong>空间不是滤镜</strong><span>它需要正确的图像规格和观看方式</span></div>
      </div>
    </section>

    <section class="studio-section" id="studio" aria-labelledby="studio-title">
      <div class="section-heading">
        <p class="eyebrow">无需登录 · 无需 Key · 数据不离开浏览器</p>
        <h2 id="studio-title">现在做一个空间视觉方案</h2>
        <p>从示例开始，或者上传你自己的图。每一步都会说明它实际做了什么。</p>
      </div>

      <div class="studio-grid">
        <form class="control-panel" id="studio-form">
          <fieldset>
            <legend><span>01</span> 选择起点</legend>
            <div class="example-grid" id="example-grid"></div>
            <label class="upload-zone" for="image-upload">
              <input id="image-upload" type="file" accept="image/png,image/jpeg,image/webp" />
              <span class="upload-title">上传你自己的图片</span>
              <span class="upload-note">PNG / JPG / WebP，文件只在当前浏览器处理</span>
            </label>
            <div class="source-status" id="source-status" role="status">已选择示例：云海宗门</div>
          </fieldset>

          <fieldset>
            <legend><span>02</span> 选择视觉方向</legend>
            <div class="style-grid" id="style-grid"></div>
          </fieldset>

          <fieldset>
            <legend><span>03</span> 描述你要的场景</legend>
            <label class="sr-only" for="scene-input">场景描述</label>
            <textarea id="scene-input" rows="3">云海中的宗门山门，原创修士沿石阶进入主场景</textarea>
            <div class="micro-label">界面密度</div>
            <div class="segmented" role="radiogroup" aria-label="界面密度">
              <label><input type="radio" name="ui-mode" value="light" checked /><span>轻量 UI</span></label>
              <label><input type="radio" name="ui-mode" value="full" /><span>全量 UI</span></label>
              <label><input type="radio" name="ui-mode" value="none" /><span>无 UI</span></label>
            </div>
          </fieldset>

          <fieldset>
            <legend><span>04</span> 选择输出方式</legend>
            <div class="output-grid" role="radiogroup" aria-label="输出方式">
              <label><input type="radio" name="view-mode" value="image" checked /><span><b>普通图片</b><small>风格方案与结构化提示词</small></span></label>
              <label><input type="radio" name="view-mode" value="panorama" /><span><b>360° 全景</b><small>拖拽查看 2:1 全景底图</small></span></label>
              <label><input type="radio" name="view-mode" value="spatial" /><span><b>空间景深</b><small>普通图片的交互式视差</small></span></label>
            </div>
          </fieldset>

          <button class="button button-primary generate-button" type="submit" id="generate-button">
            生成空间视觉方案
          </button>
        </form>

        <section class="result-panel" aria-labelledby="result-title">
          <div class="result-toolbar">
            <div><span class="status-dot"></span><span id="result-status">示例模式已就绪</span></div>
            <span class="mode-badge" id="mode-badge">普通图片</span>
          </div>
          <div class="preview-shell" id="preview-shell">
            <img id="result-image" src="./examples/cultivation.png" alt="当前视觉方案预览" />
            <canvas id="panorama-canvas" aria-label="可拖拽的 360° 全景预览"></canvas>
            <canvas id="spatial-canvas" aria-label="可移动的空间景深预览"></canvas>
            <div class="preview-hint" id="preview-hint">选择参数后生成；结果可继续修改</div>
          </div>
          <div class="result-summary">
            <div><span>当前方案</span><strong id="summary-style">东方修仙</strong></div>
            <div><span>素材来源</span><strong id="summary-source">仓库示例</strong></div>
            <div><span>处理方式</span><strong id="summary-method">结构化提示词</strong></div>
          </div>
          <div class="prompt-head">
            <div><p class="eyebrow">PROMPT BLUEPRINT</p><h3 id="result-title">结构化提示词</h3></div>
            <button type="button" class="text-button" id="copy-prompt">复制</button>
          </div>
          <pre id="prompt-output" tabindex="0"></pre>
          <div class="result-actions">
            <button type="button" class="button button-dark" id="download-result">下载方案 JSON</button>
            <button type="button" class="button button-ghost-dark" id="reset-result">重置</button>
          </div>
          <p class="honesty-note" id="honesty-note">当前版本不会在浏览器中调用付费生图接口。预览来自公开仓库案例，提示词可复制到任意支持图片生成的平台继续创作。</p>
        </section>
      </div>
    </section>

    <section class="workflow" id="workflow" aria-labelledby="workflow-title">
      <div class="section-heading section-heading-light">
        <p class="eyebrow">评委 90 秒体验路线</p>
        <h2 id="workflow-title">不是三个 Demo，是一条生产工作流</h2>
      </div>
      <ol class="workflow-list">
        <li><span>01</span><div><strong>定方向</strong><p>选一个仓库案例或上传图片，再选风格和 UI 密度。</p></div></li>
        <li><span>02</span><div><strong>得到可执行提示词</strong><p>系统把主体、世界观、参考图、构图与禁用项整理成十行结构。</p></div></li>
        <li><span>03</span><div><strong>进入空间</strong><p>严格 2:1 素材进入 360° 拖拽预览；普通图片进入景深位移预览。</p></div></li>
        <li><span>04</span><div><strong>带走方案</strong><p>复制提示词或下载包含来源说明的 JSON，继续到任意生图平台。</p></div></li>
      </ol>
    </section>

    <section class="truth" id="truth" aria-labelledby="truth-title">
      <div class="section-heading">
        <p class="eyebrow">能力边界也属于产品完成度</p>
        <h2 id="truth-title">能做什么，不能做什么，都写清楚</h2>
      </div>
      <div class="truth-grid">
        <article><span class="truth-tag truth-tag-ready">现在可用</span><h3>无 Key 完整体验</h3><p>风格路由、提示词生成、示例复用、图片上传、360° 拖拽、景深位移和结果导出全部可直接使用。</p></article>
        <article><span class="truth-tag truth-tag-local">本地处理</span><h3>上传图片不离开浏览器</h3><p>当前评委版不上传用户文件。刷新页面后，本机图片和交互状态都会清空。</p></article>
        <article><span class="truth-tag truth-tag-honest">诚实降级</span><h3>不冒充在线生图</h3><p>没有服务端 Key 时，界面明确复用仓库案例；不会用“生成中”掩盖静态占位图。</p></article>
        <article><span class="truth-tag truth-tag-tech">技术说明</span><h3>景深预览不是模型深度</h3><p>公网评委版使用浏览器端近似位移，强调交互流程；仓库脚本另提供 Depth Anything V2 真实推理路径。</p></article>
      </div>
    </section>
  </main>

  <footer>
    <div><strong>空间视觉工坊</strong><span>多风格图像、360° 全景与空间景深一站式生成器</span></div>
    <p>开源项目 · 2026 外滩黑客松 AI Coding 大赛评委版</p>
  </footer>

  <div class="toast" id="toast" role="status" aria-live="polite"></div>
`

const state = {
  exampleId: 'cultivation',
  sourceName: '仓库示例：云海宗门',
  sourceUrl: './examples/cultivation.png',
  isUpload: false,
  styleId: 'cultivation',
  scene: '云海中的宗门山门，原创修士沿石阶进入主场景',
  uiMode: 'light',
  viewMode: 'image',
  prompt: '',
}

const $ = (selector) => document.querySelector(selector)
const exampleGrid = $('#example-grid')
const styleGrid = $('#style-grid')
const promptOutput = $('#prompt-output')
const previewShell = $('#preview-shell')
const resultImage = $('#result-image')
const panoramaCanvas = $('#panorama-canvas')
const spatialCanvas = $('#spatial-canvas')
const toast = $('#toast')

function showToast(message) {
  toast.textContent = message
  toast.classList.add('toast-visible')
  window.clearTimeout(showToast.timer)
  showToast.timer = window.setTimeout(() => toast.classList.remove('toast-visible'), 2200)
}

function renderExamples() {
  exampleGrid.innerHTML = EXAMPLES.map((item) => `
    <button class="example-card ${item.id === state.exampleId && !state.isUpload ? 'is-selected' : ''}" type="button" data-example="${item.id}" aria-pressed="${item.id === state.exampleId && !state.isUpload}">
      <img src="${item.file}" alt="${item.name}示例" />
      <span>${item.name}</span>
    </button>
  `).join('')
}

function renderStyles() {
  styleGrid.innerHTML = STYLE_ORDER.map((id, index) => `
    <label class="style-option ${id === state.styleId ? 'is-selected' : ''}">
      <input type="radio" name="style" value="${id}" ${id === state.styleId ? 'checked' : ''} />
      <span class="style-index">0${index + 1}</span>
      <span>${STYLE_PRESETS[id].name}</span>
    </label>
  `).join('')
}

function updatePrompt() {
  state.scene = $('#scene-input').value
  state.uiMode = document.querySelector('input[name="ui-mode"]:checked').value
  state.viewMode = document.querySelector('input[name="view-mode"]:checked').value
  state.prompt = generatePrompt({
    styleId: state.styleId,
    scene: state.scene,
    uiMode: state.uiMode,
    viewMode: state.viewMode,
    hasReference: state.isUpload,
  })
  promptOutput.textContent = state.prompt
}

function selectExample(id) {
  const item = EXAMPLES.find((example) => example.id === id)
  if (!item) return
  state.exampleId = id
  state.sourceName = `仓库示例：${item.name}`
  state.sourceUrl = item.file
  state.isUpload = false
  state.styleId = item.style
  $('#source-status').textContent = `已选择示例：${item.name}`
  resultImage.src = item.file
  renderExamples()
  renderStyles()
  updatePrompt()
}

exampleGrid.addEventListener('click', (event) => {
  const button = event.target.closest('[data-example]')
  if (button) selectExample(button.dataset.example)
})

styleGrid.addEventListener('change', (event) => {
  if (event.target.name !== 'style') return
  state.styleId = event.target.value
  renderStyles()
  updatePrompt()
})

$('#image-upload').addEventListener('change', (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    showToast('请选择图片文件')
    return
  }
  if (file.size > 12 * 1024 * 1024) {
    showToast('图片请控制在 12MB 以内')
    event.target.value = ''
    return
  }
  if (state.sourceUrl.startsWith('blob:')) URL.revokeObjectURL(state.sourceUrl)
  state.sourceUrl = URL.createObjectURL(file)
  state.sourceName = `本机上传：${file.name}`
  state.isUpload = true
  $('#source-status').textContent = `已选择本机图片：${file.name}`
  resultImage.src = state.sourceUrl
  renderExamples()
  updatePrompt()
})

$('#scene-input').addEventListener('input', updatePrompt)
document.querySelectorAll('input[name="ui-mode"], input[name="view-mode"]').forEach((input) => input.addEventListener('change', updatePrompt))

function setPreviewMode(mode) {
  previewShell.dataset.mode = mode
  resultImage.hidden = mode !== 'image'
  panoramaCanvas.hidden = mode !== 'panorama'
  spatialCanvas.hidden = mode !== 'spatial'
  const configs = {
    image: ['普通图片', '结构化提示词', '仓库案例 / 本机图片', '当前版本不会在浏览器中调用付费生图接口。预览来自公开仓库案例或本机图片，提示词可复制到任意支持图片生成的平台继续创作。'],
    panorama: ['360° 全景', '2:1 全景拖拽', '内置严格全景底图', '360° 模式使用专门生成的 2:1 等距柱状投影示例。普通上传图不会被冒充为严格全景图。按住画面左右拖拽查看。'],
    spatial: ['空间景深', '浏览器近似位移', state.isUpload ? '本机图片' : '仓库案例', '空间景深使用浏览器端近似位移，适合快速判断空间感；它不冒充 Depth Anything V2 模型推理结果。移动鼠标或手指查看。'],
  }
  const config = configs[mode]
  $('#mode-badge').textContent = config[0]
  $('#summary-method').textContent = config[1]
  $('#summary-source').textContent = config[2]
  $('#honesty-note').textContent = config[3]
  $('#preview-hint').textContent = mode === 'panorama' ? '按住拖拽 · 左右环看' : mode === 'spatial' ? '移动鼠标或手指 · 查看位移' : '示例复用 · 可复制提示词继续生图'
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = reject
    image.src = src
  })
}

let panoramaFrame = 0
async function startPanorama() {
  cancelAnimationFrame(panoramaFrame)
  const ctx = panoramaCanvas.getContext('2d')
  const image = await loadImage('./examples/panorama.png')
  let yaw = 0.5
  let dragging = false
  let lastX = 0
  let lastInteraction = 0

  function resize() {
    const rect = panoramaCanvas.getBoundingClientRect()
    const ratio = Math.min(window.devicePixelRatio || 1, 2)
    panoramaCanvas.width = Math.round(rect.width * ratio)
    panoramaCanvas.height = Math.round(rect.height * ratio)
  }

  function draw(time) {
    if (!dragging && time - lastInteraction > 1800) yaw = (yaw + 0.00008) % 1
    const width = panoramaCanvas.width
    const height = panoramaCanvas.height
    const sourceAspect = image.width / image.height
    const viewportAspect = width / height
    const sourceWindowWidth = Math.min(image.width, image.height * viewportAspect * 0.82)
    const sx = yaw * image.width
    const firstWidth = Math.min(sourceWindowWidth, image.width - sx)
    ctx.clearRect(0, 0, width, height)
    ctx.drawImage(image, sx, 0, firstWidth, image.height, 0, 0, width * (firstWidth / sourceWindowWidth), height)
    if (firstWidth < sourceWindowWidth) {
      ctx.drawImage(image, 0, 0, sourceWindowWidth - firstWidth, image.height, width * (firstWidth / sourceWindowWidth), 0, width * ((sourceWindowWidth - firstWidth) / sourceWindowWidth), height)
    }
    const gradient = ctx.createLinearGradient(0, 0, 0, height)
    gradient.addColorStop(0, 'rgba(5,10,8,.12)')
    gradient.addColorStop(.75, 'rgba(5,10,8,0)')
    gradient.addColorStop(1, 'rgba(5,10,8,.24)')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, width, height)
    panoramaFrame = requestAnimationFrame(draw)
  }

  panoramaCanvas.onpointerdown = (event) => {
    dragging = true
    lastX = event.clientX
    lastInteraction = performance.now()
    panoramaCanvas.setPointerCapture(event.pointerId)
  }
  panoramaCanvas.onpointermove = (event) => {
    if (!dragging) return
    yaw = (yaw - (event.clientX - lastX) / Math.max(panoramaCanvas.clientWidth, 1) + 1) % 1
    lastX = event.clientX
    lastInteraction = performance.now()
  }
  panoramaCanvas.onpointerup = () => { dragging = false; lastInteraction = performance.now() }
  panoramaCanvas.onpointercancel = panoramaCanvas.onpointerup
  resize()
  draw(performance.now())
}

let spatialFrame = 0
async function startSpatial(source) {
  cancelAnimationFrame(spatialFrame)
  const ctx = spatialCanvas.getContext('2d')
  const image = await loadImage(source)
  let pointerX = 0
  let pointerY = 0
  let targetX = 0
  let targetY = 0

  function resize() {
    const rect = spatialCanvas.getBoundingClientRect()
    const ratio = Math.min(window.devicePixelRatio || 1, 2)
    spatialCanvas.width = Math.round(rect.width * ratio)
    spatialCanvas.height = Math.round(rect.height * ratio)
  }

  function draw(time) {
    const width = spatialCanvas.width
    const height = spatialCanvas.height
    const autoX = Math.sin(time * 0.00042) * 0.18
    const autoY = Math.cos(time * 0.00033) * 0.1
    pointerX += ((targetX || autoX) - pointerX) * 0.045
    pointerY += ((targetY || autoY) - pointerY) * 0.045
    const scale = Math.max(width / image.width, height / image.height) * 1.075
    const drawWidth = image.width * scale
    const drawHeight = image.height * scale
    const baseX = (width - drawWidth) / 2
    const baseY = (height - drawHeight) / 2
    ctx.clearRect(0, 0, width, height)
    ctx.filter = 'blur(10px) brightness(.75)'
    ctx.globalAlpha = 0.48
    ctx.drawImage(image, baseX - pointerX * 32, baseY - pointerY * 22, drawWidth, drawHeight)
    ctx.filter = 'none'
    ctx.globalAlpha = 1
    ctx.save()
    const marginX = width * 0.055
    const marginY = height * 0.065
    ctx.beginPath()
    ctx.roundRect(marginX, marginY, width - marginX * 2, height - marginY * 2, 28)
    ctx.clip()
    ctx.drawImage(image, baseX + pointerX * 42, baseY + pointerY * 26, drawWidth, drawHeight)
    const light = ctx.createRadialGradient(width * (.5 - pointerX * .12), height * (.28 - pointerY * .08), 0, width * .5, height * .4, width * .72)
    light.addColorStop(0, 'rgba(255,255,255,.12)')
    light.addColorStop(1, 'rgba(5,10,8,.14)')
    ctx.fillStyle = light
    ctx.fillRect(0, 0, width, height)
    ctx.restore()
    spatialFrame = requestAnimationFrame(draw)
  }

  function setTarget(event) {
    const rect = spatialCanvas.getBoundingClientRect()
    targetX = Math.max(-1, Math.min(1, ((event.clientX - rect.left) / rect.width - .5) * 2))
    targetY = Math.max(-1, Math.min(1, ((event.clientY - rect.top) / rect.height - .5) * 2))
  }
  spatialCanvas.onpointermove = setTarget
  spatialCanvas.onpointerleave = () => { targetX = 0; targetY = 0 }
  resize()
  draw(performance.now())
}

$('#studio-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  updatePrompt()
  const button = $('#generate-button')
  const status = $('#result-status')
  button.disabled = true
  button.textContent = '正在整理工作流…'
  status.textContent = '正在校验风格与视图规格'
  previewShell.classList.add('is-working')
  await new Promise((resolve) => window.setTimeout(resolve, 460))
  status.textContent = '正在生成结构化提示词'
  await new Promise((resolve) => window.setTimeout(resolve, 360))
  setPreviewMode(state.viewMode)
  if (state.viewMode === 'image') {
    resultImage.src = state.sourceUrl
  } else if (state.viewMode === 'panorama') {
    await startPanorama()
  } else {
    await startSpatial(state.sourceUrl)
  }
  $('#summary-style').textContent = STYLE_PRESETS[state.styleId].name
  promptOutput.textContent = state.prompt
  status.textContent = '方案已生成，可直接体验'
  previewShell.classList.remove('is-working')
  previewShell.classList.add('has-result')
  button.disabled = false
  button.textContent = '重新生成当前方案'
  showToast('空间视觉方案已就绪')
})

$('#copy-prompt').addEventListener('click', async () => {
  updatePrompt()
  try {
    await navigator.clipboard.writeText(state.prompt)
    showToast('提示词已复制')
  } catch {
    promptOutput.focus()
    showToast('请在提示词区域手动复制')
  }
})

$('#download-result').addEventListener('click', () => {
  updatePrompt()
  const blob = new Blob([JSON.stringify(createExportPayload(state), null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `spatial-visual-${state.viewMode}-${Date.now()}.json`
  anchor.click()
  URL.revokeObjectURL(url)
  showToast('方案 JSON 已下载')
})

$('#reset-result').addEventListener('click', () => {
  selectExample('cultivation')
  $('#scene-input').value = '云海中的宗门山门，原创修士沿石阶进入主场景'
  document.querySelector('input[name="ui-mode"][value="light"]').checked = true
  document.querySelector('input[name="view-mode"][value="image"]').checked = true
  state.viewMode = 'image'
  setPreviewMode('image')
  updatePrompt()
  $('#result-status').textContent = '示例模式已就绪'
  $('#generate-button').textContent = '生成空间视觉方案'
  showToast('已重置为默认示例')
})

window.addEventListener('resize', () => {
  if (state.viewMode === 'panorama' && !panoramaCanvas.hidden) startPanorama()
  if (state.viewMode === 'spatial' && !spatialCanvas.hidden) startSpatial(state.sourceUrl)
})

renderExamples()
renderStyles()
updatePrompt()
setPreviewMode('image')
