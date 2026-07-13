# Multi Style Image Generator

[中文说明](README.md)

A Codex skill for multi-style image generation. It turns style routing, structured prompting, uploaded-photo references, game UI modes, 360° panorama previews, spatial photo previews, and video generation into a repeatable workflow for producing coherent, recognizable, and easy-to-iterate visual concepts.

If this project is useful to you, please consider starring it on GitHub to support future updates.

## Generated Results

The examples below show representative output directions. Actual results vary by subject, reference images, and model behavior.

| Open-World Fantasy Adventure | Dark Chinese Myth |
|---|---|
| <img src="assets/examples/genshin-1.png" width="420" alt="Open-world fantasy example"> | <img src="assets/examples/dark-chinese-myth-1.png" width="420" alt="Dark Chinese myth example"> |

| Eastern Cultivation / Xianxia | Victorian Steam Occult Mystery |
|---|---|
| <img src="assets/examples/cultivation-2.png" width="420" alt="Eastern cultivation example"> | <img src="assets/examples/victorian-occult-1.png" width="420" alt="Victorian occult example"> |

| Colorful Creature-Collection Adventure | Cozy Pixel Farming |
|---|---|
| <img src="assets/examples/creature-collection-2.png" width="420" alt="Creature-collection example"> | <img src="assets/examples/pixel-farm-2.png" width="420" alt="Pixel farming example"> |

| Pixel Underwater Adventure | 360° Panorama Preview |
|---|---|
| <img src="assets/examples/pixel-underwater-2.png" width="420" alt="Pixel underwater example"> | <img src="assets/examples/cultivation-360-panorama.gif" width="420" alt="360° panorama animated GIF preview"> |

| Spatial Depth Preview | Dynamic 360° Panorama Video Preview |
|---|---|
| <img src="assets/examples/spatial-depth-preview.gif" width="420" alt="Spatial depth animated preview GIF"> | <img src="assets/examples/dynamic-360-panorama-preview.gif" width="420" alt="Dynamic 360° panorama video preview GIF"> |

## Core Capabilities

- Direct image generation from natural-language requests.
- Prompt-only mode when the user asks for a prompt instead of an image.
- Uploaded-photo references: accept any number of reference images and assign identity, scene, clothing/prop, composition, or style roles from the user's instructions or what is actually visible in each image. Any preserved feature must be something the user explicitly specifies or that is actually present; do not invent details.
- Unified style transfer: when a real-person photo is used, the person, face, clothing, props, and background are prompted to be redrawn into one coherent target style instead of pasted together.
- Lightweight, full, or no UI/HUD modes.
- Real landmark stylization while keeping the main subject recognizable.
- 360° panorama workflow: 360°×180° equirectangular prompting, 2:1 ratio normalization, static HTML previews, and dynamic-enhanced HTML previews.
- Spatial photo preview workflow: use `--spatial-mode displacement` or `--spatial-mode mesh` to generate local interactive HTML from an image and a depth map.
- BigModel/CogVideoX video workflow: supports text-to-video and image-to-video; on macOS the first secure entry is saved to Keychain and automatically reused without writing the key to files or chat.

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
Use $multi-style-image-generator to generate an eastern cultivation-style mountain sect entrance.
```

Prompt-only work, BigModel/CogVideoX video, image extraction, and the 360 HTML viewer scripts use only the Python standard library and need no extra Python packages. Spatial photo previews and 2:1 normalization need Pillow / NumPy; on the first launcher run, an isolated environment is created automatically at `multi-style-image-generator/.venv` and dependencies are downloaded from `requirements.txt`. Later runs reuse that environment.

To prepare the dependencies manually, first enter the Skill directory and run:

```bash
cd multi-style-image-generator
python3 scripts/run_with_deps.py create_spatial_preview.py --help
```

The first download requires network access. If installation fails because of network or proxy settings, fix the Python/pip proxy or certificate configuration and retry the same launcher command; do not switch to global `pip` or `sudo`. To reset, run `python3 scripts/run_with_deps.py --reset` from the Skill directory; it deletes only the Skill's own `.venv` and `.deps-state.json`, and the next run recreates them.

## How To Use

In everyday use, mention this skill in Codex and describe the style, scene, UI mode, and output type:

```text
Use $multi-style-image-generator to generate an open-world fantasy gameplay-style image of Beijing's Forbidden City with lightweight UI. Generate the image directly.
```

Common phrases:

| Desired Result | Recommended Phrase |
|---|---|
| Prompt only | `Return only the prompt; do not generate an image` |
| Normal image | `Generate the image directly` |
| Full game interface | `Full UI` |
| Small location UI | `Lightweight UI` |
| No text or HUD | `No UI` |
| 360° panorama | `360°×180° equirectangular panorama, 2:1 aspect ratio, seamless left and right edges` |
| Spatial photo effect | `Create a spatial photo preview with --spatial-mode displacement` |
| Depth mesh effect | `Create a spatial photo preview with --spatial-mode mesh` |
| Image-to-video | `Turn this image into a 5-second video` |
| 360° panorama image-to-video | `First generate a 2:1 panorama, then animate it and create a 360° panorama video preview HTML file` |

Video mode requires a BigModel/CogVideoX API key. On the first video generation on macOS, a native hidden-input dialog appears and saves the key securely in Keychain. Later requests automatically reuse it. Never paste a real key into Codex chat, the README, scripts, or commit history.

```bash
python3 multi-style-image-generator/scripts/create_bigmodel_video.py --prompt "candle flames moving gently" --image path/to/image.png
```

Replace or forget the saved key:

```bash
python3 multi-style-image-generator/scripts/create_bigmodel_video.py --replace-api-key
python3 multi-style-image-generator/scripts/create_bigmodel_video.py --forget-api-key
```

`BIGMODEL_API_KEY` or `ZHIPU_API_KEY` can still temporarily override the saved Keychain value. The repository ignores `.env`, key files, `*-submit.json`, `*-result.json`, and `output/` to reduce the chance of committing local keys, task responses, or generated artifacts.

## Example Requests

Generate a normal image:

```text
Use $multi-style-image-generator to generate a Victorian steam-occult version of the Forbidden City with lightweight UI. Generate the image directly.
```

Stylize uploaded photos:

```text
Use $multi-style-image-generator to transform my uploaded portrait into an eastern cultivation style. Preserve recognizable identity plus the clothing colors and pose that are actually present and that I explicitly ask to keep. Redraw the person and background coherently. Do not create a photo collage. Do not add accessories, clothing, or props that I did not request.
```

Prompt-only mode:

```text
Use $multi-style-image-generator to write a prompt for a dark Chinese-myth battle at an ancient temple. Do not generate an image.
```

Generate a 360° panorama and interactive preview:

```text
Use $multi-style-image-generator to generate an eastern cultivation-style 360°×180° equirectangular panorama with a 2:1 aspect ratio and seamless left and right edges, then create an interactive 360° panorama preview HTML file.
```

Generate a dynamic-enhanced 360 preview:

```text
Use $multi-style-image-generator to generate an eastern cultivation-style 360° panorama and a dynamic-enhanced preview HTML with mist, spirit particles, and automatic camera drift.
```

Generate a spatial photo preview:

```text
Use $multi-style-image-generator to create a spatial photo preview from this image with --spatial-mode displacement.
```

Generate a video:

```text
Use $multi-style-image-generator to turn this Dunhuang grotto image into a 5-second video with a slow camera push-in, gently moving candle flames, and drifting dust.
```

## 360° Panorama Notes

The preferred name is “360° panorama”; the complete technical term is “360°×180° equirectangular panorama.” It normally uses a 2:1 aspect ratio with seamless left and right edges. The skill still accepts informal Chinese aliases such as “环景” and “环景照.”

For 360° panorama requests, the skill asks the image generator for a 2:1 equirectangular panorama and then verifies the result. If the model returns a non-2:1 image, the helper script creates a `-2x1.png` normalized version before building the HTML panorama preview.

Normalization fixes the file ratio only. It cannot turn an ordinary wide image into a geometrically perfect seamless panorama. For best results, include these phrases in the user request:

```text
360°×180° equirectangular panorama, 2:1 aspect ratio, seamless left and right edges
```

The dynamic-enhanced viewer is not a video. It keeps the 2:1 panorama as a static base image and adds real-time WebGL / Canvas effects such as camera drift, mist, spirit particles, glow, and subtle FOV breathing.

The 360 example in this README is shown as a GIF so it can be viewed directly on the project homepage without opening a separate media file.

## Spatial Photo Preview Notes

Spatial photo preview is for ordinary images, not 360 panoramas. It uses a source image and a depth map. If no depth map is provided, the helper script creates a heuristic depth map, which is only suitable for quick previews.

Use `--spatial-mode` to choose between two modes:

- `displacement`: recommended default. It uses a full-screen WebGL shader to apply depth-driven spatial displacement, so the motion feels more like layered photo parallax. UI labels prefer terms such as spatial displacement, spatial feel, and motion strength.
- `mesh`: creates a subdivided mesh from the depth map and renders it with camera movement. It has a stronger 3D feel, but a single image is more likely to show edge stretching, broken surfaces, or fake-3D artifacts.

Create a spatial photo preview:

```bash
python3 multi-style-image-generator/scripts/run_with_deps.py create_spatial_preview.py path/to/image.png --depth path/to/depth.png --spatial-mode displacement
```

Without a depth map:

```bash
python3 multi-style-image-generator/scripts/run_with_deps.py create_spatial_preview.py path/to/image.png --spatial-mode displacement
```

## Video Mode Notes

Video mode uses the BigModel/CogVideoX API. According to the [BigModel video generation API](https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E8%A7%86%E9%A2%91%E7%94%9F%E6%88%90%E5%BC%82%E6%AD%A5), video duration defaults to 5 seconds and supports only 5 or 10 seconds; intermediate values such as 8 seconds are not supported. On macOS, the API key is handled securely through Keychain:

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

## Helper Scripts

Create a static interactive 360° panorama viewer:

```bash
python3 multi-style-image-generator/scripts/create_panorama_viewer.py path/to/panorama-2x1.png --embed-image
```

Create a dynamic-enhanced 360° panorama viewer:

```bash
python3 multi-style-image-generator/scripts/create_dynamic_panorama_viewer.py path/to/panorama-2x1.png
```

Create a spatial photo preview:

```bash
python3 multi-style-image-generator/scripts/run_with_deps.py create_spatial_preview.py path/to/image.png --spatial-mode displacement
```

Generate a BigModel/CogVideoX video:

```bash
python3 multi-style-image-generator/scripts/create_bigmodel_video.py --prompt "slow cinematic push-in" --image path/to/image.png
```

Normalize a generated image to 2:1:

```bash
python3 multi-style-image-generator/scripts/run_with_deps.py normalize_equirectangular_aspect.py path/to/image.png
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
- Prompting, BigModel/CogVideoX video, image extraction, and the 360 HTML viewer scripts require only the Python standard library
- The launcher automatically installs Pillow / NumPy for `normalize_equirectangular_aspect.py` and the spatial photo preview scripts into `multi-style-image-generator/.venv`
- A modern browser with WebGL support for the 360, dynamic-enhanced, and spatial preview HTML
- Frame-sequence previews can optionally use the system `ffmpeg`; detect it with `command -v ffmpeg` and install it yourself if missing (for example, `brew install ffmpeg` on macOS), because the Skill never installs system software automatically

The static and dynamic preview HTML files are standalone when generated with embedded image data.

BigModel/CogVideoX API keys are unrelated to Python package installation. On macOS, the default flow uses a native dialog and Keychain for secure storage and automatic reuse; environment variables remain available as temporary overrides. The Skill never writes the key to the repository, generated files, or chat.

## License

This project is released under the [PolyForm Noncommercial License 1.0.0](LICENSE). Personal, educational, research, and other noncommercial uses are permitted. Commercial use, commercial integration, commercial deployment, or redistribution for profit requires separate written permission.

## Author & Community

- Email: 247133278@qq.com
- WeChat: loonges
- QQ: 247133278
- Xiaohongshu / Bilibili: 好奇的小逸
