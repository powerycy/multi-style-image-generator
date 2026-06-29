# Multi Style Image Generator

[中文说明](README.md)

A Codex skill for multi-style image generation. It turns style routing, structured prompting, uploaded-photo references, game UI modes, and 360 panorama previews into a repeatable workflow for producing coherent, recognizable, and easy-to-iterate visual concepts.

If this project is useful to you, please consider starring it on GitHub to support future updates.

## Author & Community

- WeChat: loonges
- Xiaohongshu / Douyin: 好奇的小逸

## Generated Results

The examples below show representative output directions. Actual results vary by subject, reference images, and model behavior.

| Open-World Fantasy Adventure | Dark Chinese Myth |
|---|---|
| <img src="assets/examples/genshin-1.png" width="420" alt="Open-world fantasy example"> | <img src="assets/examples/dark-chinese-myth-1.png" width="420" alt="Dark Chinese myth example"> |

| Eastern Cultivation / Xianxia | Victorian Steam Occult Mystery |
|---|---|
| <img src="assets/examples/cultivation-1.png" width="420" alt="Eastern cultivation example"> | <img src="assets/examples/victorian-occult-1.png" width="420" alt="Victorian occult example"> |

| Colorful Creature-Collection Adventure | Cozy Pixel Farming |
|---|---|
| <img src="assets/examples/creature-collection-1.png" width="420" alt="Creature-collection example"> | <img src="assets/examples/pixel-farm-1.png" width="420" alt="Pixel farming example"> |

| Pixel Underwater Adventure | 360 Panorama Preview |
|---|---|
| <img src="assets/examples/pixel-underwater-1.png" width="420" alt="Pixel underwater example"> | [View dynamic 360 panorama example](assets/examples/cultivation-360-panorama.mov) |

## Core Capabilities

- Direct image generation from Chinese user requests.
- Prompt-only mode when the user asks for a prompt instead of an image.
- Uploaded-photo references: use one image for the scene and another for identity, while preserving specified outfit, sunglasses, hat, props, and pose.
- Unified style transfer: when a real-person photo is used, the person, face, clothing, props, and background are prompted to be redrawn into one coherent target style instead of pasted together.
- Lightweight, full, or no UI/HUD modes.
- Real landmark stylization while keeping the main subject recognizable.
- 360 panorama workflow: 2:1 equirectangular prompting, ratio normalization, static HTML previews, and dynamic-enhanced HTML previews.

## Supported Style Directions

| Style Direction | Best For |
|---|---|
| Open-world fantasy adventure | Landmarks, exploration scenes, elemental mechanisms, bright fantasy maps |
| Dark Chinese myth | Ancient temples, stone grottoes, forest paths, action RPG atmosphere |
| Eastern cultivation / xianxia | Mountain sects, cave cultivation, alchemy, flying sword light |
| Victorian steam occult mystery | Foggy alleys, detective scenes, rituals, churches, brass machinery |
| Colorful creature-collection adventure | Original trainers, original companion creatures, routes, turn-based encounters |
| Cozy pixel farming | Farms, towns, crops, tools, seasonal life |
| Pixel underwater adventure | Diving, coral reefs, fish schools, ruins, light management adventure |

## Installation

Copy the skill folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R multi-style-image-generator ~/.codex/skills/
```

Restart Codex after installation, then invoke it with:

```text
使用 $multi-style-image-generator 生成一张东方修仙风格的宗门山门图。
```

## Example Requests

Generate a normal image:

```text
使用 $multi-style-image-generator 生成一张维多利亚蒸汽神秘学风格的故宫，轻量 UI，直接出图。
```

Stylize uploaded photos:

```text
使用 $multi-style-image-generator 把我上传的照片改成 7 种风格。第一张参考场景和穿着，第二张参考我的脸，要能看出来是我；墨镜戴上，人物和背景都要统一成对应画风，不要像抠图贴背景。
```

Prompt-only mode:

```text
使用 $multi-style-image-generator 写一个暗黑中式神话古寺战斗场景的提示词，不用出图。
```

Generate a 360 panorama and interactive preview:

```text
使用 $multi-style-image-generator 生成一张东方修仙风格的 360 度环景照，等距柱状投影，2:1 宽高比，直接出图，并生成可交互 360 预览 HTML。
```

Generate a dynamic-enhanced 360 preview:

```text
使用 $multi-style-image-generator 生成一张东方修仙风格的 360 度环景照，直接出图，并生成动态增强 360 预览 HTML，有云雾、灵气粒子和自动巡游。
```

## 360 Panorama Notes

For 360 panorama requests, the skill asks the image generator for a 2:1 equirectangular image and then verifies the result. If the model returns a non-2:1 image, the helper script creates a `-2x1.png` normalized version before building the HTML preview.

Normalization fixes the file ratio only. It cannot turn an ordinary wide image into a geometrically perfect seamless panorama. For best results, include these phrases in the user request:

```text
360 度环景照，等距柱状投影，2:1 宽高比，左右边缘无缝衔接
```

The dynamic-enhanced viewer is not a video. It keeps the 2:1 panorama as a static base image and adds real-time WebGL / Canvas effects such as camera drift, mist, spirit particles, glow, and subtle FOV breathing.

## Helper Scripts

Create a static interactive 360 viewer:

```bash
python3 multi-style-image-generator/scripts/create_panorama_viewer.py path/to/panorama-2x1.png --embed-image
```

Create a dynamic-enhanced 360 viewer:

```bash
python3 multi-style-image-generator/scripts/create_dynamic_panorama_viewer.py path/to/panorama-2x1.png
```

Normalize a generated image to 2:1:

```bash
python3 multi-style-image-generator/scripts/normalize_equirectangular_aspect.py path/to/image.png
```

Extract the latest generated image from a Codex session log:

```bash
python3 multi-style-image-generator/scripts/extract_latest_image_from_session.py --out-dir output/imagegen --name my-panorama
```

## Repository Layout

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

## Requirements

- Python 3.9+
- Pillow for `normalize_equirectangular_aspect.py`
- A modern browser with WebGL support for the preview HTML

The static and dynamic preview HTML files are standalone when generated with embedded image data.

## License

This project is released under the [PolyForm Noncommercial License 1.0.0](LICENSE). Personal, educational, research, and other noncommercial uses are permitted. Commercial use, commercial integration, commercial deployment, or redistribution for profit requires separate written permission.
