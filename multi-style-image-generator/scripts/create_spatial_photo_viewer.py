#!/usr/bin/env python3
"""Create a lightweight spatial-photo parallax HTML from one image."""

from __future__ import annotations

import argparse
import base64
import html
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def image_to_data_uri(path: Path) -> str:
    media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def save_depth_map(image_path: Path, output_path: Path) -> None:
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    small_width = min(1200, width)
    small_height = max(1, round(height * small_width / width))
    image_small = image.resize((small_width, small_height), Image.Resampling.LANCZOS)

    gray = ImageOps.grayscale(image_small)
    gray = ImageOps.autocontrast(gray)
    lum = np.asarray(gray, dtype=np.float32) / 255.0

    y = np.linspace(0.0, 1.0, small_height, dtype=np.float32)[:, None]
    vertical_near = np.power(y, 1.25)

    edges = gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.5))
    edges_arr = np.asarray(edges, dtype=np.float32) / 255.0
    edges_arr = np.clip(edges_arr * 1.8, 0.0, 1.0)

    # Heuristic for generated scene images:
    # lower pixels are usually closer, bright lamps/foreground objects tend to be closer,
    # and local edges should stay crisp enough for the displacement preview.
    depth = 0.68 * vertical_near + 0.22 * lum + 0.10 * edges_arr
    depth = np.clip(depth, 0.0, 1.0)
    depth = (depth - depth.min()) / max(1e-6, depth.max() - depth.min())

    depth_img = Image.fromarray((depth * 255).astype(np.uint8), mode="L")
    depth_img = depth_img.filter(ImageFilter.GaussianBlur(2.0))
    depth_img = ImageOps.autocontrast(depth_img)
    depth_img = depth_img.resize((width, height), Image.Resampling.BICUBIC)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    depth_img.save(output_path)


def build_html(image_uri: str, depth_uri: str, title: str, strength: float = 1.0) -> str:
    safe_title = html.escape(title)
    offset_strength = max(0.0, strength) * 0.075
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<style>
html, body {{
  margin: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #0b0b0b;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
canvas {{
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  display: block;
  touch-action: none;
}}
.hud {{
  position: fixed;
  left: 18px;
  bottom: 16px;
  padding: 10px 12px;
  border: 1px solid rgba(255,255,255,.14);
  border-radius: 8px;
  color: rgba(255,255,255,.72);
  background: rgba(0,0,0,.35);
  font-size: 12px;
  line-height: 1.45;
  backdrop-filter: blur(12px);
  user-select: none;
}}
</style>
</head>
<body>
<canvas id="view"></canvas>
<div class="hud">Spatial photo preview<br>move pointer or drag to tilt</div>
<script>
const imageSrc = {image_uri!r};
const depthSrc = {depth_uri!r};
const canvas = document.getElementById("view");
const gl = canvas.getContext("webgl", {{ antialias: true, alpha: false }});

if (!gl) {{
  document.body.innerHTML = "<p style='color:white;padding:24px'>WebGL is not available.</p>";
  throw new Error("WebGL unavailable");
}}

const vertexSource = `
attribute vec2 position;
varying vec2 uv;
void main() {{
  uv = position * 0.5 + 0.5;
  gl_Position = vec4(position, 0.0, 1.0);
}}
`;

const fragmentSource = `
precision mediump float;
varying vec2 uv;
uniform sampler2D colorTex;
uniform sampler2D depthTex;
uniform vec2 shift;
uniform vec2 imageScale;
uniform vec2 imageOffset;

vec2 fitUv(vec2 screenUv) {{
  return (screenUv - imageOffset) / imageScale;
}}

void main() {{
  vec2 sourceUv = fitUv(uv);
  if (sourceUv.x < 0.0 || sourceUv.x > 1.0 || sourceUv.y < 0.0 || sourceUv.y > 1.0) {{
    gl_FragColor = vec4(0.035, 0.034, 0.032, 1.0);
    return;
  }}

  float depth = texture2D(depthTex, sourceUv).r;
  float centered = depth - 0.42;
  vec2 offset = shift * centered * {offset_strength:.6f};

  vec2 chromaA = sourceUv + offset;
  vec2 chromaB = sourceUv + offset * 0.96;
  vec2 chromaC = sourceUv + offset * 1.04;
  chromaA = clamp(chromaA, 0.001, 0.999);
  chromaB = clamp(chromaB, 0.001, 0.999);
  chromaC = clamp(chromaC, 0.001, 0.999);

  vec3 color;
  color.r = texture2D(colorTex, chromaC).r;
  color.g = texture2D(colorTex, chromaB).g;
  color.b = texture2D(colorTex, chromaA).b;

  float vignette = smoothstep(0.0, 0.08, sourceUv.x) *
                   smoothstep(0.0, 0.08, sourceUv.y) *
                   smoothstep(0.0, 0.08, 1.0 - sourceUv.x) *
                   smoothstep(0.0, 0.08, 1.0 - sourceUv.y);
  gl_FragColor = vec4(color * mix(0.74, 1.0, vignette), 1.0);
}}
`;

function compile(type, source) {{
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {{
    throw new Error(gl.getShaderInfoLog(shader));
  }}
  return shader;
}}

const program = gl.createProgram();
gl.attachShader(program, compile(gl.VERTEX_SHADER, vertexSource));
gl.attachShader(program, compile(gl.FRAGMENT_SHADER, fragmentSource));
gl.linkProgram(program);
if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {{
  throw new Error(gl.getProgramInfoLog(program));
}}
gl.useProgram(program);

const buffer = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
  -1, -1, 1, -1, -1, 1,
  -1, 1, 1, -1, 1, 1
]), gl.STATIC_DRAW);

const posLoc = gl.getAttribLocation(program, "position");
gl.enableVertexAttribArray(posLoc);
gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

const shiftLoc = gl.getUniformLocation(program, "shift");
const imageScaleLoc = gl.getUniformLocation(program, "imageScale");
const imageOffsetLoc = gl.getUniformLocation(program, "imageOffset");
gl.uniform1i(gl.getUniformLocation(program, "colorTex"), 0);
gl.uniform1i(gl.getUniformLocation(program, "depthTex"), 1);

function loadTexture(src, unit) {{
  return new Promise((resolve) => {{
    const img = new Image();
    img.onload = () => {{
      const tex = gl.createTexture();
      gl.activeTexture(gl.TEXTURE0 + unit);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      resolve(img);
    }};
    img.src = src;
  }});
}}

let target = {{ x: 0, y: 0 }};
let current = {{ x: 0, y: 0 }};
let imageAspect = 1;

function setTarget(clientX, clientY) {{
  const rect = canvas.getBoundingClientRect();
  target.x = ((clientX - rect.left) / rect.width - 0.5) * 2.0;
  target.y = -(((clientY - rect.top) / rect.height - 0.5) * 2.0);
  target.x = Math.max(-1, Math.min(1, target.x));
  target.y = Math.max(-1, Math.min(1, target.y));
}}

window.addEventListener("pointermove", (event) => setTarget(event.clientX, event.clientY));
window.addEventListener("pointerdown", (event) => setTarget(event.clientX, event.clientY));
window.addEventListener("pointerleave", () => {{ target.x = 0; target.y = 0; }});

function resize() {{
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const width = Math.floor(window.innerWidth * dpr);
  const height = Math.floor(window.innerHeight * dpr);
  if (canvas.width !== width || canvas.height !== height) {{
    canvas.width = width;
    canvas.height = height;
  }}
  gl.viewport(0, 0, canvas.width, canvas.height);

  const screenAspect = canvas.width / canvas.height;
  let scaleX = 1;
  let scaleY = 1;
  let offsetX = 0;
  let offsetY = 0;
  if (screenAspect > imageAspect) {{
    scaleX = imageAspect / screenAspect;
    offsetX = (1 - scaleX) * 0.5;
  }} else {{
    scaleY = screenAspect / imageAspect;
    offsetY = (1 - scaleY) * 0.5;
  }}
  gl.uniform2f(imageScaleLoc, scaleX, scaleY);
  gl.uniform2f(imageOffsetLoc, offsetX, offsetY);
}}

function draw() {{
  current.x += (target.x - current.x) * 0.065;
  current.y += (target.y - current.y) * 0.065;
  gl.uniform2f(shiftLoc, current.x, current.y);
  gl.drawArrays(gl.TRIANGLES, 0, 6);
  requestAnimationFrame(draw);
}}

Promise.all([loadTexture(imageSrc, 0), loadTexture(depthSrc, 1)]).then(([img]) => {{
  imageAspect = img.width / img.height;
  resize();
  draw();
}});
window.addEventListener("resize", resize);
</script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--depth", type=Path, help="Optional external depth map. If omitted, a heuristic depth map is generated.")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strength", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_path = args.image.resolve()
    out_dir = args.out_dir or image_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = image_path.stem
    if args.depth:
        depth_path = args.depth.resolve()
        html_path = args.output or out_dir / f"{stem}-depth-spatial-viewer.html"
    else:
        depth_path = out_dir / f"{stem}-pseudo-depth.png"
        html_path = args.output or out_dir / f"{stem}-spatial-viewer.html"
        save_depth_map(image_path, depth_path)

    html_text = build_html(
        image_to_data_uri(image_path),
        image_to_data_uri(depth_path),
        f"{stem} spatial preview",
        strength=args.strength,
    )
    html_path.write_text(html_text, encoding="utf-8")
    print(depth_path)
    print(html_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
