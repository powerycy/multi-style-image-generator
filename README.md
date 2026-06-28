# Multi Style Image Generator

[English README](README_en.md)

一个 Codex skill，用于按游戏、动画、小说改编或幻想作品的视觉风格生成图片、提示词、2:1 等距柱状投影 360 环景图，以及本地可交互 360 预览 HTML。

## 功能

- 根据中文请求直接生成图片。
- 在用户要求“不用出图 / 只写 prompt / 写提示词”时，只输出结构化提示词。
- 支持多种视觉风格路由：
  - 原神式开放世界奇幻冒险
  - 黑神话悟空式暗黑中式神话
  - 凡人修仙传式东方修仙 / 仙侠
  - 诡秘之主式维多利亚蒸汽神秘学
  - 宝可梦式彩色怪物收集冒险
  - 星露谷物语式温暖像素农场
  - 潜水员戴夫式像素海底冒险
- 支持轻量 UI、全量 UI、无 UI 三种界面模式。
- 支持真实地点风格化，同时尽量保留主体可识别度。
- 支持 360 环景工作流：
  - 在 prompt 中强制加入 `360 度等距柱状投影图像`
  - 要求或规格化为 2:1 宽高比
  - 必要时从 Codex session 日志里提取图片载荷
  - 生成静态可交互 360 HTML 预览
  - 生成动态增强 360 HTML 预览，包含自动巡游、雾气、灵气粒子和光晕效果

## 仓库结构

```text
multi-style-image-generator/
├── README.md
├── README_en.md
└── multi-style-image-generator/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    ├── evals/
    │   └── evals.json
    ├── references/
    │   └── game-visual-styles.md
    └── scripts/
        ├── create_dynamic_panorama_viewer.py
        ├── create_panorama_viewer.py
        ├── extract_latest_image_from_session.py
        └── normalize_equirectangular_aspect.py
```

## 安装

把 skill 文件夹复制到 Codex 的 skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -R multi-style-image-generator ~/.codex/skills/
```

安装后可以在 Codex 里这样调用：

```text
使用 $multi-style-image-generator 生成一张凡人修仙传风格的宗门山门图。
```

## 示例请求

生成普通图片：

```text
使用 $multi-style-image-generator 生成一张诡秘之主风格的故宫，轻量 UI，直接出图。
```

生成 360 环景图和可交互预览：

```text
使用 $multi-style-image-generator 生成一张凡人修仙传风格的 360 度环景照，等距柱状投影，2:1 宽高比，直接出图，并生成可交互 360 预览 HTML。
```

生成动态增强 360 预览：

```text
使用 $multi-style-image-generator 生成一张凡人修仙传风格的 360 度环景照，直接出图，并生成动态增强 360 预览 HTML，有云雾、灵气粒子和自动巡游。
```

只写提示词：

```text
使用 $multi-style-image-generator 写一个黑神话悟空风格古寺战斗场景的提示词，不用出图。
```

## 360 环景说明

对于 360 环景请求，skill 会要求图像生成器输出 2:1 的等距柱状投影图，并在落盘后检查比例。如果模型返回的不是 2:1，辅助脚本会先生成一个 `-2x1.png` 规格化版本，再用它创建 HTML 预览。

规格化只能修正文件比例，不能把普通广角图真正变成几何无缝的 360 环景。为了提高结果质量，请在请求里明确写：

```text
360 度环景照，等距柱状投影，2:1 宽高比，左右边缘无缝衔接
```

动态增强预览不是视频。它使用静态 2:1 环景图作为底图，通过 WebGL / Canvas 增加自动巡游、雾气、灵气粒子、光晕和轻微镜头呼吸，让场景看起来更有动态感。

## 辅助脚本

创建静态可交互 360 预览：

```bash
python3 multi-style-image-generator/scripts/create_panorama_viewer.py path/to/panorama-2x1.png --embed-image
```

创建动态增强 360 预览：

```bash
python3 multi-style-image-generator/scripts/create_dynamic_panorama_viewer.py path/to/panorama-2x1.png
```

把生成图规格化为 2:1：

```bash
python3 multi-style-image-generator/scripts/normalize_equirectangular_aspect.py path/to/image.png
```

从 Codex session 日志中提取最近生成的图片：

```bash
python3 multi-style-image-generator/scripts/extract_latest_image_from_session.py --out-dir output/imagegen --name my-panorama
```

## 依赖

- Python 3.9+
- `normalize_equirectangular_aspect.py` 需要 Pillow
- 360 HTML 预览需要支持 WebGL 的现代浏览器

静态和动态预览 HTML 在嵌入图片数据后都是单文件，可以直接打开。

## 许可证

当前还没有选择许可证。公开发布前建议添加明确的开源许可证。
