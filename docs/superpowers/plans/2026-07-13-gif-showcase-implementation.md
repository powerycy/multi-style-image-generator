# GIF Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the spatial-depth and dynamic 360° panorama HTML demos with directly embedded looping GIFs in both READMEs.

**Architecture:** Generate two committed GIF assets from the image data already embedded in the HTML demos. Lock their dimensions, animation, size, README embedding, and HTML removal with repository-contract tests.

**Tech Stack:** Python 3.9+, Pillow, NumPy, `unittest`, Markdown.

## Global Constraints

- Output names are `assets/examples/spatial-depth-preview.gif` and `assets/examples/dynamic-360-panorama-preview.gif`.
- Both GIFs are exactly 520×292, loop forever, last 3–4 seconds, and stay below 5 MB.
- The spatial GIF shows foreground/background parallax.
- The dynamic panorama GIF shows source-frame motion plus a changing viewing direction.
- Remove both superseded HTML files and all README links to them.

---

### Task 1: Lock the final repository contract

**Files:**
- Modify: `tests/test_repository_contract.py`
- Test: `tests/test_repository_contract.py`

**Interfaces:**
- Consumes: repository files under `assets/examples/` and README text loaded by `RepositoryContractTests.setUpClass`.
- Produces: `test_readme_showcase_gifs_are_directly_embedded` and `test_showcase_gifs_are_animated_and_bounded`.

- [ ] **Step 1: Replace the HTML demo tests with failing GIF tests**

```python
import struct

def test_readme_showcase_gifs_are_directly_embedded(self):
    gif_paths = (
        "assets/examples/spatial-depth-preview.gif",
        "assets/examples/dynamic-360-panorama-preview.gif",
    )
    for path in gif_paths:
        self.assertIn(f'<img src="{path}"', self.readme_zh)
        self.assertIn(f'<img src="{path}"', self.readme_en)
    self.assertNotIn("spatial-depth-preview.html", self.readme_zh + self.readme_en)
    self.assertNotIn("dynamic-360-panorama-preview.html", self.readme_zh + self.readme_en)

def test_showcase_gifs_are_animated_and_bounded(self):
    for name in ("spatial-depth-preview.gif", "dynamic-360-panorama-preview.gif"):
        path = ROOT / "assets" / "examples" / name
        self.assertTrue(path.is_file())
        self.assertLessEqual(path.stat().st_size, 5 * 1024 * 1024)
        payload = path.read_bytes()
        self.assertIn(payload[:6], (b"GIF87a", b"GIF89a"))
        self.assertEqual(struct.unpack("<HH", payload[6:10]), (520, 292))
        controls = [
            index for index in range(len(payload) - 7)
            if payload[index:index + 3] == b"\x21\xf9\x04"
        ]
        self.assertGreaterEqual(len(controls), 20)
        duration_ms = sum(
            int.from_bytes(payload[index + 4:index + 6], "little") * 10
            for index in controls
        )
        self.assertGreaterEqual(duration_ms, 3000)
        self.assertLessEqual(duration_ms, 4000)
        self.assertIn(b"NETSCAPE2.0", payload)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python3 -m unittest tests.test_repository_contract.RepositoryContractTests.test_readme_showcase_gifs_are_directly_embedded tests.test_repository_contract.RepositoryContractTests.test_showcase_gifs_are_animated_and_bounded -v`

Expected: FAIL because both GIF files and README `<img>` tags are absent.

### Task 2: Generate the two GIF assets

**Files:**
- Read: `assets/examples/spatial-depth-preview.html`
- Read: `assets/examples/dynamic-360-panorama-preview.html`
- Create: `assets/examples/spatial-depth-preview.gif`
- Create: `assets/examples/dynamic-360-panorama-preview.gif`

**Interfaces:**
- Consumes: base64 PNG image/depth-map pair and base64 JPEG panorama-frame sequence.
- Produces: two 520×292, 27-frame, 120 ms/frame looping GIFs.

- [ ] **Step 1: Decode the embedded sources**

Use Python regex `data:image/(?:png|jpeg);base64,([A-Za-z0-9+/=]+)` and `base64.b64decode`. Assert exactly two PNGs for the spatial source and at least 20 JPEGs for the panorama source.

- [ ] **Step 2: Render spatial parallax frames**

Resize image and depth map to 520×292. For frame angle `t = 2πi/27`, sample the source with depth-weighted offsets `dx = sin(t) * 14 * (depth - 0.5)` and `dy = cos(t) * 6 * (depth - 0.5)` using NumPy bilinear interpolation.

- [ ] **Step 3: Render panorama viewport frames**

Select 27 source frames evenly across the embedded sequence. Render an 84° perspective viewport with equirectangular lookup and `yaw = sin(2πi/27) * 0.30` radians so source animation and camera direction both change.

- [ ] **Step 4: Quantize and save**

Create a shared 96-color adaptive palette per animation, quantize every frame against it, and save with `duration=120`, `loop=0`, `optimize=True`, and `disposal=2`. If an output exceeds 5 MB, retry with 72 colors before changing dimensions or frame count.

- [ ] **Step 5: Inspect metadata**

Run a Pillow metadata check and expect 520×292, 27 frames, 3.24 seconds, `loop=0`, and each file at or below 5 MB.

### Task 3: Embed GIFs and remove HTML demos

**Files:**
- Modify: `README.md`
- Modify: `README_en.md`
- Delete: `assets/examples/spatial-depth-preview.html`
- Delete: `assets/examples/dynamic-360-panorama-preview.html`

**Interfaces:**
- Consumes: GIF assets from Task 2.
- Produces: direct README rendering with no interaction links.

- [ ] **Step 1: Replace the interactive table in Chinese README**

```html
| 空间景深预览 | 动态 360° 全景视频预览 |
|---|---|
| <img src="assets/examples/spatial-depth-preview.gif" width="420" alt="空间景深动态预览 GIF"> | <img src="assets/examples/dynamic-360-panorama-preview.gif" width="420" alt="动态 360° 全景视频预览 GIF"> |
```

- [ ] **Step 2: Replace the interactive table in English README**

```html
| Spatial Depth Preview | Dynamic 360° Panorama Video Preview |
|---|---|
| <img src="assets/examples/spatial-depth-preview.gif" width="420" alt="Spatial depth animated preview GIF"> | <img src="assets/examples/dynamic-360-panorama-preview.gif" width="420" alt="Dynamic 360° panorama video preview GIF"> |
```

- [ ] **Step 3: Delete the HTML demos**

Delete only the two superseded files listed above; preserve the skill's HTML-generation scripts.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the two focused tests from Task 1.

Expected: PASS.

### Task 4: Visual and full-suite verification

**Files:**
- Modify only if verification exposes a GIF or copy defect.

**Interfaces:**
- Consumes: final GIFs and README markup.
- Produces: verified committed showcase.

- [ ] **Step 1: Visually inspect both GIFs**

Use the local image viewer at original detail. Confirm recognizable subject matter, visible parallax/panorama motion, no severe palette flicker, and a smooth loop.

- [ ] **Step 2: Run all tests**

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add README.md README_en.md tests/test_repository_contract.py assets/examples/spatial-depth-preview.gif assets/examples/dynamic-360-panorama-preview.gif
git add -u assets/examples
git commit -m "docs: show spatial and panorama demos as GIFs"
```
