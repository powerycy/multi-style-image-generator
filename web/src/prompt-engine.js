export const STYLE_PRESETS = {
  fantasy: {
    name: '开放世界奇幻',
    visual: '明亮通透的动画 3D 渲染、干净色彩、柔和环境光',
    anchors: '原创旅行者、元素机关、山水地标、探索路径',
    elements: '云海、遗迹机关、晶蝶、元素微光',
    avoid: '写实摄影、电影 CG、品牌角色、厚重油画质感',
  },
  myth: {
    name: '暗黑中式神话',
    visual: '厚重山林雾气、古刹残垣、低饱和金褐灰色调、高质感风格化 3D',
    anchors: '原创持棍行者、石窟造像、古刹、符箓',
    elements: '松柏、香炉、残破经幡、金色法术火花',
    avoid: '现代摄影、欧美魔幻、赛博朋克、卡通可爱风',
  },
  cultivation: {
    name: '东方修仙',
    visual: '克制的国风 3D 动画质感、古风山水、宗门楼阁、云雾灵气',
    anchors: '原创修士、宗门山门、飞剑遁光、阵法',
    elements: '青山云海、石阶、牌楼、灵气微光',
    avoid: '页游广告感、夸张神装、满屏金光、现代摄影',
  },
  occult: {
    name: '蒸汽神秘学',
    visual: '维多利亚蒸汽神秘学悬疑镜头、低饱和蓝灰棕色调、克制阴郁',
    anchors: '原创侦探、煤气灯、黄铜机械、仪式符号',
    elements: '雾雨街巷、旧报纸、怀表、教堂阴影',
    avoid: '现代都市、赛博朋克、血腥恐怖、明亮童话风',
  },
  creature: {
    name: '生物伙伴冒险',
    visual: '明亮可爱的风格化游戏画面、清晰轮廓、圆润角色、干净色块',
    anchors: '原创训练家、原创生物伙伴、草地道路、回合制遭遇',
    elements: '小镇入口、高草丛、伙伴球、捕捉光效',
    avoid: '官方角色复制、写实动物、暗黑恐怖、复杂电影 CG',
  },
  farm: {
    name: '温暖像素农场',
    visual: '统一像素网格、俯视或 3/4 视角、柔和季节色彩、舒适乡村氛围',
    anchors: '原创农夫、作物田、木屋、小镇生活',
    elements: '木栅栏、作物、工具栏、像素小动物',
    avoid: '高清 3D、写实摄影、复杂透视、电影景深',
  },
  underwater: {
    name: '像素海底冒险',
    visual: '横向 2.5D 像素画面、清澈分层海水、明亮海洋色彩、轻松冒险氛围',
    anchors: '原创潜水员、珊瑚、鱼群、海底遗迹',
    elements: '气泡、海龟、宝箱、发光水母',
    avoid: '真实水下摄影、阴森恐怖、电影 CG、鱼群遮挡主体',
  },
}

export const UI_LABELS = {
  light: '轻量 UI',
  full: '全量 UI',
  none: '无 UI',
}

export const VIEW_LABELS = {
  image: '普通视图',
  panorama: '360° 全景图模式',
  spatial: '空间景深预览模式',
}

export function generatePrompt({ styleId, scene, uiMode, viewMode, hasReference = false }) {
  const style = STYLE_PRESETS[styleId] || STYLE_PRESETS.cultivation
  const safeScene = String(scene || '').trim() || '云海中的宗门山门，原创修士沿石阶进入主场景'
  const isPanorama = viewMode === 'panorama'
  const referenceLine = hasReference
    ? '上传图片作为场景与构图参考；保留可见空间关系，整张图统一重绘，禁止照片贴背景和光照割裂'
    : '无上传参考图；使用原创人物、原创生物与泛化世界观元素'
  const uiLine = uiMode === 'none'
    ? '无 HUD、无 UI、无任何可读文字'
    : `${UI_LABELS[uiMode]}；界面元素克制、清晰，不堆满画面`
  const viewLine = isPanorama
    ? '360°×180° 等距柱状投影全景图。2:1 宽高比，左右边缘无缝衔接。'
    : viewMode === 'spatial'
      ? '普通横向视图；前中后景层次清楚，主体完整，便于后续生成深度预览'
      : '普通横向游戏实况视图；主体完整，叙事动作清晰'

  return [
    `${style.name}游戏实况截图风格`,
    `画风：${style.visual}；不要${style.avoid}`,
    `风格锚点：${style.anchors}，仅使用原创角色与原创生物`,
    `场景主题：${safeScene}`,
    `画面要素：${style.elements}`,
    '玩法时刻：角色正在探索环境并与空间中的线索发生自然互动',
    `参考图处理：${referenceLine}`,
    `UI 模式：${uiLine}`,
    `视图模式：${viewLine}`,
    '画面要求：主体可识别，构图可继续编辑；不要现代广告、水印、二维码、乱码和无关角色',
  ].join('\n')
}

export function createExportPayload(state) {
  return {
    product: '空间视觉工坊',
    version: '1.0.0',
    generatedAt: new Date().toISOString(),
    input: {
      source: state.sourceName,
      style: STYLE_PRESETS[state.styleId]?.name,
      scene: state.scene,
      uiMode: UI_LABELS[state.uiMode],
      viewMode: VIEW_LABELS[state.viewMode],
    },
    prompt: state.prompt,
    provenance: state.viewMode === 'panorama'
      ? '内置 2:1 等距柱状投影示例图；浏览器端拖拽预览'
      : state.viewMode === 'spatial'
        ? '浏览器端近似深度位移预览；不冒充模型深度推理'
        : '仓库可验证示例图或用户本机上传图',
  }
}
