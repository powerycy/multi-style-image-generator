#!/usr/bin/env python3
"""Create a file:// friendly 360 viewer from an image frame sequence."""

from __future__ import annotations

import argparse
import base64
import html
from pathlib import Path


def data_url(path: Path) -> str:
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def build_html(frame_paths: list[Path], fps: float, title: str) -> str:
    frames = ",\n".join(f"    \"{data_url(path)}\"" for path in frame_paths)
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: #050403; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; }}
    canvas {{ position: fixed; inset: 0; width: 100vw; height: 100vh; display: block; cursor: grab; touch-action: none; }}
    canvas:active {{ cursor: grabbing; }}
    .hud {{ position: fixed; left: 16px; bottom: 14px; padding: 10px 12px; border: 1px solid rgba(255,255,255,.16); border-radius: 8px; color: rgba(255,255,255,.78); background: rgba(0,0,0,.42); backdrop-filter: blur(12px); font-size: 12px; line-height: 1.45; user-select: none; }}
    .status {{ position: fixed; left: 50%; top: 50%; transform: translate(-50%, -50%); padding: 10px 14px; border-radius: 8px; color: rgba(255,255,255,.86); background: rgba(0,0,0,.48); font-size: 13px; user-select: none; }}
    button {{ margin-top: 8px; height: 30px; border: 0; border-radius: 6px; padding: 0 12px; color: #16110b; background: #d8b56e; font-weight: 700; cursor: pointer; }}
  </style>
</head>
<body>
  <canvas id="view"></canvas>
  <div class="hud">360 环景动画预览<br>拖拽查看，滚轮缩放<br><button id="toggle">暂停</button></div>
  <div class="status" id="status">正在加载帧...</div>
<script>
const frameUrls = [
{frames}
];
const fps = {fps:.6f};
const canvas = document.getElementById("view");
const toggle = document.getElementById("toggle");
const status = document.getElementById("status");
const gl = canvas.getContext("webgl", {{ antialias: true, alpha: false }});
if (!gl) {{
  document.body.innerHTML = "<p style='color:white;padding:24px'>当前浏览器不支持 WebGL。</p>";
  throw new Error("WebGL unavailable");
}}

const vertexSource = `
attribute vec2 position;
varying vec2 uv;
void main() {{
  uv = position * 0.5 + 0.5;
  gl_Position = vec4(position, 0.0, 1.0);
}}`;

const fragmentSource = `
precision mediump float;
varying vec2 uv;
uniform sampler2D frameTex;
uniform float yaw;
uniform float pitch;
uniform float fov;
uniform float aspect;
const float PI = 3.141592653589793;
mat3 rotY(float a) {{
  float s = sin(a), c = cos(a);
  return mat3(c, 0.0, -s, 0.0, 1.0, 0.0, s, 0.0, c);
}}
mat3 rotX(float a) {{
  float s = sin(a), c = cos(a);
  return mat3(1.0, 0.0, 0.0, 0.0, c, s, 0.0, -s, c);
}}
void main() {{
  vec2 p = uv * 2.0 - 1.0;
  p.x *= aspect;
  float z = 1.0 / tan(fov * 0.5);
  vec3 dir = normalize(vec3(p.x, -p.y, z));
  dir = rotY(yaw) * rotX(pitch) * dir;
  float lon = atan(dir.x, dir.z);
  float lat = asin(clamp(dir.y, -1.0, 1.0));
  vec2 texUv = vec2(lon / (2.0 * PI) + 0.5, lat / PI + 0.5);
  gl_FragColor = texture2D(frameTex, texUv);
}}`;

function compile(type, source) {{
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
  return shader;
}}

const program = gl.createProgram();
gl.attachShader(program, compile(gl.VERTEX_SHADER, vertexSource));
gl.attachShader(program, compile(gl.FRAGMENT_SHADER, fragmentSource));
gl.linkProgram(program);
if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
gl.useProgram(program);

const buffer = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
const posLoc = gl.getAttribLocation(program, "position");
gl.enableVertexAttribArray(posLoc);
gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

const texture = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, texture);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([8, 6, 4, 255]));

const yawLoc = gl.getUniformLocation(program, "yaw");
const pitchLoc = gl.getUniformLocation(program, "pitch");
const fovLoc = gl.getUniformLocation(program, "fov");
const aspectLoc = gl.getUniformLocation(program, "aspect");
gl.uniform1i(gl.getUniformLocation(program, "frameTex"), 0);

let yaw = 0.0, pitch = 0.0, fov = Math.PI / 2.15;
let dragging = false, lastX = 0, lastY = 0;
let playing = true, startTime = performance.now(), pauseOffset = 0;
let currentFrame = -1;
const images = [];

function resize() {{
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = Math.floor(window.innerWidth * dpr);
  canvas.height = Math.floor(window.innerHeight * dpr);
  gl.viewport(0, 0, canvas.width, canvas.height);
}}
window.addEventListener("resize", resize);
resize();

function loadFrames() {{
  let loaded = 0;
  return Promise.all(frameUrls.map((url, index) => new Promise((resolve, reject) => {{
    const img = new Image();
    img.onload = () => {{
      images[index] = img;
      loaded += 1;
      status.textContent = `正在加载帧... ${{loaded}}/${{frameUrls.length}}`;
      resolve(img);
    }};
    img.onerror = reject;
    img.src = url;
  }})));
}}

function uploadFrame(index) {{
  if (!images[index] || currentFrame === index) return;
  currentFrame = index;
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, images[index]);
}}

canvas.addEventListener("pointerdown", (event) => {{
  dragging = true;
  lastX = event.clientX;
  lastY = event.clientY;
  canvas.setPointerCapture(event.pointerId);
}});
canvas.addEventListener("pointermove", (event) => {{
  if (!dragging) return;
  const dx = event.clientX - lastX;
  const dy = event.clientY - lastY;
  lastX = event.clientX;
  lastY = event.clientY;
  yaw -= dx * 0.004;
  pitch = Math.max(-1.25, Math.min(1.25, pitch + dy * 0.004));
}});
canvas.addEventListener("pointerup", () => dragging = false);
canvas.addEventListener("wheel", (event) => {{
  event.preventDefault();
  fov = Math.max(0.72, Math.min(1.55, fov + event.deltaY * 0.0007));
}}, {{ passive: false }});

toggle.addEventListener("click", () => {{
  playing = !playing;
  if (playing) startTime = performance.now() - pauseOffset;
  else pauseOffset = performance.now() - startTime;
  toggle.textContent = playing ? "暂停" : "播放";
}});

function draw(now) {{
  if (images.length) {{
    const elapsed = playing ? now - startTime : pauseOffset;
    const frame = Math.floor((elapsed / 1000) * fps) % images.length;
    uploadFrame(frame);
  }}
  gl.uniform1f(yawLoc, yaw);
  gl.uniform1f(pitchLoc, pitch);
  gl.uniform1f(fovLoc, fov);
  gl.uniform1f(aspectLoc, canvas.width / Math.max(1, canvas.height));
  gl.drawArrays(gl.TRIANGLES, 0, 6);
  requestAnimationFrame(draw);
}}

loadFrames().then(() => {{
  status.style.display = "none";
  startTime = performance.now();
  uploadFrame(0);
  requestAnimationFrame(draw);
}}).catch(() => {{
  status.textContent = "帧加载失败";
}});
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a looping 360 viewer from extracted frames.")
    parser.add_argument("frames", type=Path, help="Frame directory.")
    parser.add_argument("--pattern", default="*.jpg", help="Frame filename glob.")
    parser.add_argument("--fps", type=float, default=12.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", default="360 Frame Sequence Viewer")
    args = parser.parse_args()

    frame_paths = sorted(args.frames.expanduser().resolve().glob(args.pattern))
    if not frame_paths:
        raise SystemExit(f"No frames found: {args.frames} / {args.pattern}")
    args.output.write_text(build_html(frame_paths, args.fps, args.title), encoding="utf-8")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
