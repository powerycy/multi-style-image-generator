# Multi Style Image Generator

[English README](README_en.md)

面向 Codex 的多风格图片生成 skill。它把常见的视觉风格路由、提示词结构、上传照片参考、游戏 UI 模式、360° 全景预览、空间照片预览和动态视频生成整理成一套稳定工作流，适合快速生成风格统一、主体清晰、可继续迭代的视觉方案。

如果这个项目对你有帮助，欢迎在 GitHub 上 Star ⭐️ 支持后续更新。

## 生成效果

以下示例展示不同视觉方向的生成效果。实际结果会随输入主体、参考图和模型状态变化。

| 开放世界奇幻冒险 | 暗黑中式神话 |
|---|---|
| <img src="assets/examples/genshin-1.png" width="420" alt="开放世界奇幻冒险示例"> | <img src="assets/examples/dark-chinese-myth-1.png" width="420" alt="暗黑中式神话示例"> |

| 东方修仙 / 仙侠 | 维多利亚蒸汽神秘学 |
|---|---|
| <img src="assets/examples/cultivation-2.png" width="420" alt="东方修仙示例"> | <img src="assets/examples/victorian-occult-1.png" width="420" alt="维多利亚蒸汽神秘学示例"> |

| 彩色怪物收集冒险 | 温暖像素农场 |
|---|---|
| <img src="assets/examples/creature-collection-2.png" width="420" alt="彩色怪物收集冒险示例"> | <img src="assets/examples/pixel-farm-2.png" width="420" alt="温暖像素农场示例"> |

| 像素海底冒险 | 360° 全景预览 |
|---|---|
| <img src="assets/examples/pixel-underwater-2.png" width="420" alt="像素海底冒险示例"> | <img src="assets/examples/cultivation-360-panorama.gif" width="420" alt="360° 全景动态预览 GIF"> |

| 空间景深预览 | 动态 360° 全景视频预览 |
|---|---|
| <img src="assets/examples/spatial-depth-preview.gif" width="420" alt="空间景深动态预览 GIF"> | <img src="assets/examples/dynamic-360-panorama-preview.gif" width="420" alt="动态 360° 全景视频预览 GIF"> |

## 核心能力

- 直接出图：根据自然语言请求生成目标风格图片。
- 只写提示词：在“不用出图 / 只写 prompt / 写提示词”场景下输出结构化提示词。
- 上传照片参考：支持任意数量的参考图，并按用户说明或图中实际可见内容分别用于身份、场景、服装/道具、构图或风格参考；需要保留的特征必须来自用户明确指定或参考图实际内容，不自行添加细节。
- 统一画风重绘：上传真人照片时，人物、脸、衣服、道具和背景会被要求统一转译成目标画风，避免照片脸贴背景或绿幕抠图感。
- UI 模式控制：支持轻量 UI、全量 UI、无 UI 三种模式。
- 真实地点风格化：尽量保留真实地点主体可识别度，同时加入目标风格元素。
- 360° 全景图工作流：支持 360°×180° 等距柱状投影提示、2:1 比例规格化、静态 HTML 预览和动态增强 HTML 预览。
- 空间照片预览：支持 `--spatial-mode displacement` 和 `--spatial-mode mesh` 两种模式，用原图和 depth map 生成本地可交互 HTML。
- 动态视频模式：支持 BigModel/CogVideoX 文生视频和图生视频；macOS 首次安全输入后保存到钥匙串，后续自动读取，不把 key 写进文件或对话。

## 支持风格

| 风格方向 | 适合内容 |
|---|---|
| 开放世界奇幻冒险 | 山水地标、探索场景、元素机关、明亮幻想地图 |
| 暗黑中式神话 | 古刹山林、石窟遗迹、妖怪对峙、厚重动作 RPG 氛围 |
| 东方修仙 / 仙侠 | 宗门山门、洞府修炼、炼丹炼器、飞剑遁光 |
| 维多利亚蒸汽神秘学 | 雾雨街巷、侦探调查、神秘仪式、教堂与齿轮机械 |
| 彩色怪物收集冒险 | 原创训练家、原创伙伴生物、草地道路、回合制遭遇 |
| 温暖像素农场 | 农场、小镇、作物、工具栏、季节生活 |
| 像素海底冒险 | 潜水、珊瑚、鱼群、深海遗迹、经营冒险 |

## 安装

把 skill 文件夹复制到 Codex 的 skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -R multi-style-image-generator ~/.codex/skills/
```

安装后重启 Codex，然后这样调用：

```text
使用 $multi-style-image-generator 生成一张东方修仙风格的宗门山门图。
```

纯提示词、BigModel/CogVideoX 视频、图片提取以及 360 HTML 查看器脚本只使用 Python 标准库，不需要额外安装 Python 包。空间照片预览和 2:1 图片规格化需要 Pillow / NumPy；首次通过启动器运行时，会在 `multi-style-image-generator/.venv` 自动创建隔离环境，并从 `requirements.txt` 下载依赖。后续运行会复用这个环境。

如果希望提前准备依赖，请先进入 Skill 目录，再手动运行：

```bash
cd multi-style-image-generator
python3 scripts/run_with_deps.py create_spatial_preview.py --help
```

首次下载需要网络。如果安装因网络或代理失败，请检查 Python/pip 的代理和证书配置后重试同一启动器命令；不要改用全局 `pip` 或 `sudo`。如需重置，请在 Skill 目录运行 `python3 scripts/run_with_deps.py --reset`；该命令只会删除 Skill 自己的 `.venv` 和 `.deps-state.json`，下一次运行会重新创建。

## 怎么用

日常使用时，直接在 Codex 里点名这个 skill，并把风格、场景、UI 模式和输出类型写清楚即可：

```text
使用 $multi-style-image-generator 生成一张原神开放世界游戏实况截图风格的北京故宫，轻量 UI，直接出图。
```

常用参数和说法：

| 你想要的结果 | 推荐写法 |
|---|---|
| 只要提示词 | `只给出 prompt` / `不用出图` |
| 普通图片 | `直接出图` |
| 带完整游戏界面 | `全量 UI` |
| 少量地点提示 | `轻量 UI` |
| 没有任何文字和界面 | `无 UI` |
| 360° 全景图 | `360°×180° 等距柱状投影全景图，2:1 宽高比，左右边缘无缝衔接` |
| 空间照片效果 | `生成空间照片预览，使用 --spatial-mode displacement` |
| 深度网格效果 | `生成空间照片预览，使用 --spatial-mode mesh` |
| 图生视频 | `把这张图变成 5 秒动态视频` |
| 360° 全景图生视频 | `先生成 2:1 全景图，再图生视频，并生成 360° 全景视频预览 HTML` |

视频模式需要 BigModel/CogVideoX API key。macOS 首次生成视频时会弹出隐藏输入的系统对话框，确认后安全保存到钥匙串；后续自动读取，不需要再次输入。不要把真实 key 粘贴到 Codex 对话、README、脚本或提交记录中。

```bash
python3 multi-style-image-generator/scripts/create_bigmodel_video.py --prompt "candle flames moving gently" --image path/to/image.png
```

更换或删除已保存的 SK：

```bash
python3 multi-style-image-generator/scripts/create_bigmodel_video.py --replace-api-key
python3 multi-style-image-generator/scripts/create_bigmodel_video.py --forget-api-key
```

如需临时切换账号，仍可使用 `BIGMODEL_API_KEY` 或 `ZHIPU_API_KEY` 环境变量覆盖钥匙串值。仓库已经忽略 `.env`、密钥文件、`*-submit.json`、`*-result.json` 和 `output/`，避免把本地 key、任务响应和生成产物误传到 GitHub。

## 示例请求

生成普通图片：

```text
使用 $multi-style-image-generator 生成一张维多利亚蒸汽神秘学风格的故宫，轻量 UI，直接出图。
```

上传照片参考并风格化：

```text
使用 $multi-style-image-generator 将我上传的人像照片转换成东方修仙风格。保留人物可识别身份，以及参考图中实际存在且我明确要求保留的服装配色和姿势；人物与背景统一重绘，不要照片拼贴，也不要自行添加配饰、服装或道具。
```

只写提示词：

```text
使用 $multi-style-image-generator 写一个暗黑中式神话古寺战斗场景的提示词，不用出图。
```

生成 360° 全景图和可交互预览：

```text
使用 $multi-style-image-generator 生成一张东方修仙风格的 360°×180° 等距柱状投影全景图，2:1 宽高比，左右边缘无缝衔接，直接出图，并生成可交互 360° 全景预览 HTML。
```

生成动态增强 360 预览：

```text
使用 $multi-style-image-generator 生成一张东方修仙风格的 360° 全景图，直接出图，并生成动态增强 360° 全景预览 HTML，有云雾、灵气粒子和自动巡游。
```

生成空间照片预览：

```text
使用 $multi-style-image-generator 根据这张图生成空间照片预览，使用 --spatial-mode displacement。
```

生成动态视频：

```text
使用 $multi-style-image-generator 把这张敦煌壁窟图变成 5 秒动态视频，镜头缓慢推进，烛火和尘埃轻微流动。
```

## 360° 全景图说明

这里的标准名称是“360° 全景图”，更完整的技术名称是“360°×180° 等距柱状投影全景图”。它通常使用 2:1 宽高比，并要求左右边缘无缝衔接。用户说“环景、环景照”时，skill 仍会识别为这一模式。

对于 360° 全景图请求，skill 会要求图像生成器输出 2:1 的等距柱状投影全景图，并在落盘后检查比例。如果模型返回的不是 2:1，辅助脚本会先生成一个 `-2x1.png` 规格化版本，再用它创建 HTML 全景预览。

规格化只能修正文件比例，不能把普通广角图真正变成几何无缝的 360° 全景图。为了提高结果质量，请在请求里明确写：

```text
360°×180° 等距柱状投影全景图，2:1 宽高比，左右边缘无缝衔接
```

动态增强预览不是视频。它使用静态 2:1 全景图作为底图，通过 WebGL / Canvas 增加自动巡游、雾气、灵气粒子、光晕和轻微镜头呼吸，让场景看起来更有动态感。

上方 README 中的 360 示例使用 GIF 展示，打开项目首页即可直接观看，不需要二次点击。

## 空间照片预览说明

空间照片预览用于普通图片，不用于 360° 全景图。它需要一张原图和一张 depth map；如果没有 depth map，脚本会生成启发式深度图，只适合快速预览。

两种模式用 `--spatial-mode` 区分：

- `displacement`：推荐默认值。用全屏 WebGL shader 根据深度图做空间位移，滑动时更像照片层次在移动，界面里使用“空间位移、空间感、移动幅度”等命名。
- `mesh`：用深度图生成细分网格，再用相机横移渲染。它的空间感更明显，但对单张图更容易出现边缘拉伸、破面和假 3D 感。

创建空间照片预览：

```bash
python3 multi-style-image-generator/scripts/run_with_deps.py create_spatial_preview.py path/to/image.png --depth path/to/depth.png --spatial-mode displacement
```

如果没有 depth map：

```bash
python3 multi-style-image-generator/scripts/run_with_deps.py create_spatial_preview.py path/to/image.png --spatial-mode displacement
```

## 视频模式说明

视频模式使用 BigModel/CogVideoX API。根据[智谱视频生成接口](https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E8%A7%86%E9%A2%91%E7%94%9F%E6%88%90%E5%BC%82%E6%AD%A5)，视频默认 5 秒，`duration` 只支持 5 秒或 10 秒，不支持 8 秒等中间时长。macOS 会通过钥匙串安全管理 API key：

```bash
python3 multi-style-image-generator/scripts/create_bigmodel_video.py \
  --prompt "slow cinematic push-in, candle flames moving, dust drifting" \
  --image path/to/image.png \
  --model cogvideox-3 \
  --quality quality \
  --size 1920x1080 \
  --fps 30 \
  --with-audio
```

## 辅助脚本

创建静态可交互 360° 全景预览：

```bash
python3 multi-style-image-generator/scripts/create_panorama_viewer.py path/to/panorama-2x1.png --embed-image
```

创建动态增强 360° 全景预览：

```bash
python3 multi-style-image-generator/scripts/create_dynamic_panorama_viewer.py path/to/panorama-2x1.png
```

创建空间照片预览：

```bash
python3 multi-style-image-generator/scripts/run_with_deps.py create_spatial_preview.py path/to/image.png --spatial-mode displacement
```

生成 BigModel/CogVideoX 视频：

```bash
python3 multi-style-image-generator/scripts/create_bigmodel_video.py --prompt "slow cinematic push-in" --image path/to/image.png
```

把生成图规格化为 2:1：

```bash
python3 multi-style-image-generator/scripts/run_with_deps.py normalize_equirectangular_aspect.py path/to/image.png
```

从 Codex session 日志中提取最近生成的图片：

```bash
python3 multi-style-image-generator/scripts/extract_latest_image_from_session.py --out-dir output/imagegen --name my-panorama
```

## 项目结构

```text
multi-style-image-generator/
├── README.md
├── README_en.md
├── assets/
│   └── examples/
└── multi-style-image-generator/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    ├── evals/
    │   └── evals.json
    ├── references/
    │   └── game-visual-styles.md
    └── scripts/
```

## 依赖

- Python 3.9+
- 提示词、BigModel/CogVideoX 视频、图片提取和 360 HTML 查看器脚本只需要 Python 标准库
- `normalize_equirectangular_aspect.py` 和空间照片预览脚本的 Pillow / NumPy 依赖由启动器自动安装到 `multi-style-image-generator/.venv`
- 360° 全景 HTML 预览、动态增强预览和空间照片预览需要支持 WebGL 的现代浏览器
- 视频抽帧预览可选用系统 `ffmpeg`；先用 `command -v ffmpeg` 检测，缺失时请自行安装（macOS 可使用 `brew install ffmpeg`），Skill 不会自动安装系统软件

静态和动态预览 HTML 在嵌入图片数据后都是单文件，可以直接打开。

BigModel/CogVideoX API key 与 Python 包安装无关。macOS 默认通过系统对话框和钥匙串安全保存、自动读取；环境变量仍可临时覆盖。Skill 不会把 key 写入仓库、生成文件或对话。

## 许可

本项目采用 [PolyForm Noncommercial License 1.0.0](LICENSE)。

## 作者与交流

- 邮箱：247133278@qq.com
- 微信：loonges
- QQ：247133278
- 小红书 / B站：好奇的小逸
