---
name: multi-style-image-generator
description: Generate or stylize images and prompts in game, fantasy, pixel or crochet/yarn styles; derive spatial depth, single-image point clouds, 360° panoramas and CogVideoX videos. Use for 出图、照片风格化、毛线编织、空间景深图、点云、360° 全景图 or video requests.
---

# 多风格图片生成

按“画风 × 来源 × 表现形式”独立判断，可以组合，不要把点云或景深当成一种画风。

## 正交路由

| 维度 | 判断与操作 |
| --- | --- |
| 画风 | 原神、黑神话、修仙、诡秘、宝可梦、星露谷、潜水员戴夫、毛线编织/钩针等；只有需要生成或改造画风时，读取 [画风参考](references/game-visual-styles.md) 与 [生图流程](references/generation-workflow.md)。 |
| 来源 | 已有底图、人物/场景参考，或没有底图。已有底图直接派生时保留主体、身份、构图和环境；不要重新生图。人物照片风格化保留身份锚点，默认重设计衣着、动作与光照，具体约束见生图流程。 |
| 表现形式 | 普通图片、空间景深、单图深度点云、360° 全景、视频；按下面入口加载对应流程。 |

**组合顺序**：例如“生成黑神话风格的敦煌点云/景深”且没有底图，先生成并检查底图，再用底图派生对应表现形式。已有底图则复用；只有明确要求先改造画风时才先风格化并检查。不要因缺底图把生成请求误判为只处理已有图片，也不要无必要重新付费生图。

**已有图片直接做景深/点云**：只读 [空间与点云流程](references/spatial-workflow.md)，不强制读取大型画风参考或人物生图规则。空间景深默认 mesh；只有明确要求点云才选 pointcloud。两者都不臆造物体背面，不称作完整真 3D。

## 执行入口与渐进披露

- **直接出图**：“生成、画一张、做一个”表示执行生图，组装 prompt 后调用可用图像生成工具；不要只交付提示词。按生图流程检查候选再交付。
- **只写提示词**：明确要求 prompt/不用出图时，只返回 [生图流程](references/generation-workflow.md) 中的结构化提示词代码块，不调用生图。
- **空间景深 / 单图深度点云**：读取 [空间与点云流程](references/spatial-workflow.md)，统一运行 `python3 scripts/run_with_deps.py create_spatial_preview.py <image> --out-dir <directory>`；点云加 `--spatial-mode pointcloud`。
- **360° 全景图**：读取 [全景流程](references/panorama-workflow.md)，从 2:1 等距柱状投影源图制作预览；需要比例规格化时运行 `scripts/run_with_deps.py normalize_equirectangular_aspect.py`。人物生成或人物全景 QA 再读 [人物全景质检](references/portrait-panorama-qa.md)。
- **动态增强全景**：没有明确要求真视频时，可用 `scripts/create_dynamic_panorama_viewer.py` 的静图实时特效；说明这不是视频。
- **视频 / 360° 全景图生视频模式**：只读 [视频流程](references/video-workflow.md)。`scripts/create_bigmodel_video.py` 默认 5 秒，只支持 5 秒或 10 秒。全景视频从 2:1 图片生成 2:1 视频；`file://` 交付统一优先 `scripts/create_panorama_frame_sequence_viewer.py` 内嵌帧序列，先检测 ffmpeg；原始视频纹理 viewer 只用于确定的 HTTP 访问。缺少 ffmpeg 时报告，不自动安装系统软件。

## 共有约束

- 需要 Pillow、NumPy、PyTorch 或 Transformers 的脚本一律通过 `scripts/run_with_deps.py`；启动器管理 Skill 内 `.venv` 和依赖，模型复用缓存。不得用全局 pip 或系统安装替代。
- 真实深度默认 Depth Anything V2 Small；失败报告 backend、错误与阶段，不静默降级。只有用户明确接受非模型预览才用 heuristic，并标记 `heuristic-fallback`。
- 景深默认显示“空间感、移动幅度、透视”三条滑杆与自动巡游开关：`0.62 / 0.56 / 1.15`，自动 X/Y `0.36 / 0.18`。只有明确要求无控制条时才加 `--controls hidden`；“底图无 UI/HUD”不代表隐藏交互控件。
- 点云默认保留深度、点大小、焦平面及重置，侧面演示可开关。准确称作“单图深度点云”。HTML 自包含，可用 `file://` 打开。
- 视频凭据保存在 macOS 钥匙串；不要要求用户在对话中粘贴 API Key。更换/删除分别用 `--replace-api-key` / `--forget-api-key`，详情按需读视频流程。
- 衍生交付附 HTML 与 stable depth，推理或复用 raw 时附 raw depth，并准确标注来源。图像生成结果没有可落盘数据时如实说明，不声称已创建 HTML。

## 功能介绍模式

用户要求“介绍功能、怎么使用、支持什么、给示例，但不要出图”时，只介绍能力和示例，不调用图像、视频或预览工具。介绍必须遵守以下契约：

- 标准名称使用“360° 全景图”；需要技术解释时写“360°×180° 等距柱状投影全景图”。“环景、环景照”只作为用户可能使用的触发别名，不作为功能标题。
- 照片风格化默认介绍为“保留身份锚点，并将人物造型、动作和光照重新设计到目标世界观中”。只有用户明确要求保留原服装、原姿势或原道具时，才把这些作为保留项；不要自行举出具体服装、配饰或道具。
- CogVideoX-3 视频默认 5 秒，只支持 5 秒或 10 秒。不要写“5–10 秒”、8 秒或其他连续时长。
- 明确区分“只写提示词”和“直接出图”：前者只返回结构化提示词代码块，后者调用图像生成工具；用户只要求功能介绍时两者都不执行。
