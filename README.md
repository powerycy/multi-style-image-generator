# Multi Style Image Generator

Codex skill for generating game, animation, novel-adaptation, and fantasy-style images. It can produce direct images, structured prompts, 2:1 equirectangular 360 panorama assets, and local interactive 360 preview HTML.

## What It Supports

- Direct image generation from Chinese user requests.
- Prompt-only mode when the user asks for a prompt.
- Style routing for:
  - Genshin-like open-world fantasy
  - Black Myth Wukong-like dark Chinese myth
  - Eastern cultivation / xianxia
  - Lord of the Mysteries-like Victorian steam occult mystery
  - Pokemon-like colorful creature adventure
  - Stardew Valley-like cozy pixel farming
  - Dave the Diver-like pixel underwater adventure
- Lightweight, full, or no UI/HUD modes.
- Real landmark stylization while preserving recognizability.
- 360 panorama workflow:
  - prompts for `360 度等距柱状投影图像`
  - enforces or normalizes to 2:1 aspect ratio
  - extracts image payloads from Codex session logs when needed
  - creates static interactive 360 HTML previews
  - creates dynamic-enhanced 360 HTML previews with camera drift, mist, spirit particles, and glow effects

## Repository Layout

```text
multi-style-image-generator/
├── README.md
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

## Installation

Copy the skill folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R multi-style-image-generator ~/.codex/skills/
```

After installation, invoke it in Codex with:

```text
使用 $multi-style-image-generator 生成一张凡人修仙传风格的宗门山门图。
```

## Example Requests

Generate a normal image:

```text
使用 $multi-style-image-generator 生成一张诡秘之主风格的故宫，轻量 UI，直接出图。
```

Generate a 360 panorama and interactive preview:

```text
使用 $multi-style-image-generator 生成一张凡人修仙传风格的 360 度环景照，等距柱状投影，2:1 宽高比，直接出图，并生成可交互 360 预览 HTML。
```

Generate a dynamic-enhanced 360 preview:

```text
使用 $multi-style-image-generator 生成一张凡人修仙传风格的 360 度环景照，直接出图，并生成动态增强 360 预览 HTML，有云雾、灵气粒子和自动巡游。
```

Prompt-only mode:

```text
使用 $multi-style-image-generator 写一个黑神话悟空风格古寺战斗场景的提示词，不用出图。
```

## 360 Panorama Notes

For 360 panorama requests, the skill asks the image generator for a 2:1 equirectangular image and then verifies the result. If the model returns a non-2:1 image, the helper script creates a `-2x1.png` normalized version before building the HTML preview.

Normalization fixes the file ratio only. It cannot turn an ordinary wide image into a geometrically perfect seamless panorama. For best results, include these phrases in the user request:

```text
360 度环景照，等距柱状投影，2:1 宽高比，左右边缘无缝衔接
```

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

## Requirements

- Python 3.9+
- Pillow for `normalize_equirectangular_aspect.py`
- A modern browser with WebGL support for the preview HTML

The static and dynamic preview HTML files are standalone when generated with embedded image data.

## License

No license has been selected yet. Add a license before publishing this repository for public reuse.
