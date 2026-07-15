#!/usr/bin/env python3
"""Create a local 360 equirectangular video viewer HTML."""

from __future__ import annotations

import argparse
import html
from pathlib import Path


def build_html(video_path: Path) -> str:
    video_name = html.escape(video_path.name, quote=True)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>360 Video Viewer</title>
  <style>
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: #050403; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; }}
    canvas {{ position: fixed; inset: 0; width: 100vw; height: 100vh; display: block; cursor: grab; touch-action: none; }}
    canvas:active {{ cursor: grabbing; }}
    video {{ position: fixed; width: 1px; height: 1px; opacity: 0; pointer-events: none; }}
    .hud {{ position: fixed; left: 16px; bottom: 14px; padding: 10px 12px; border: 1px solid rgba(255,255,255,.16); border-radius: 8px; color: rgba(255,255,255,.78); background: rgba(0,0,0,.42); backdrop-filter: blur(12px); font-size: 12px; line-height: 1.45; user-select: none; }}
    .status {{ position: fixed; left: 50%; top: 50%; transform: translate(-50%, -50%); padding: 10px 14px; border-radius: 8px; color: rgba(255,255,255,.86); background: rgba(0,0,0,.48); font-size: 13px; user-select: none; }}
    button {{ margin-top: 8px; height: 30px; border: 0; border-radius: 6px; padding: 0 12px; color: #16110b; background: #d8b56e; font-weight: 700; cursor: pointer; }}
  </style>
</head>
<body>
  <canvas id="view"></canvas>
  <video id="video" src="{video_name}" muted loop playsinline autoplay preload="auto"></video>
  <div class="hud">360 视频预览<br>拖拽查看，滚轮缩放<br><button id="toggle">暂停</button></div>
  <div class="status" id="status">正在加载 360 视频...</div>
<script>
const canvas = document.getElementById("view");
const video = document.getElementById("video");
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
uniform sampler2D videoTex;
uniform float yaw;
uniform float pitch;
uniform float fov;
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
  p.x *= 16.0 / 9.0;
  float z = 1.0 / tan(fov * 0.5);
  vec3 dir = normalize(vec3(p.x, -p.y, z));
  dir = rotY(yaw) * rotX(pitch) * dir;
  float lon = atan(dir.x, dir.z);
  float lat = asin(clamp(dir.y, -1.0, 1.0));
  vec2 texUv = vec2(lon / (2.0 * PI) + 0.5, lat / PI + 0.5);
  gl_FragColor = texture2D(videoTex, texUv);
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
gl.uniform1i(gl.getUniformLocation(program, "videoTex"), 0);

let yaw = 0.0, pitch = 0.0, fov = Math.PI / 2.15;
let dragging = false, lastX = 0, lastY = 0;

function resize() {{
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = Math.floor(window.innerWidth * dpr);
  canvas.height = Math.floor(window.innerHeight * dpr);
  gl.viewport(0, 0, canvas.width, canvas.height);
}}
window.addEventListener("resize", resize);
resize();

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

video.muted = true;
video.loop = true;
video.playsInline = true;

async function playVideo() {{
  try {{
    await video.play();
    status.style.display = video.readyState >= 2 ? "none" : "block";
    toggle.textContent = "暂停";
    return true;
  }} catch (_) {{
    status.textContent = "点击画面开始播放";
    status.style.display = "block";
    toggle.textContent = "播放";
    return false;
  }}
}}

function uploadVideoFrame() {{
  if (video.readyState < 2) return false;
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, texture);
  try {{
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, video);
    return true;
  }} catch (_) {{
    return false;
  }}
}}

video.addEventListener("loadeddata", () => {{ status.style.display = "none"; uploadVideoFrame(); }});
video.addEventListener("canplay", () => {{ status.style.display = "none"; uploadVideoFrame(); }});
video.addEventListener("ended", async () => {{ video.currentTime = 0; await playVideo(); }});
video.addEventListener("stalled", () => {{ status.textContent = "视频加载中，点击画面可继续播放"; status.style.display = "block"; }});
video.addEventListener("error", () => {{ status.textContent = "视频加载失败，请确认 mp4 与 HTML 在同一文件夹"; status.style.display = "block"; }});
canvas.addEventListener("click", async () => {{ await playVideo(); }});
toggle.addEventListener("click", async () => {{
  if (video.paused) await playVideo();
  else {{
    video.pause();
    toggle.textContent = "播放";
  }}
}});

function draw() {{
  if (video.ended || video.currentTime >= Math.max(0.1, video.duration - 0.08)) {{
    video.currentTime = 0;
    if (!video.paused) playVideo();
  }}
  uploadVideoFrame();
  gl.uniform1f(yawLoc, yaw);
  gl.uniform1f(pitchLoc, pitch);
  gl.uniform1f(fovLoc, fov);
  gl.drawArrays(gl.TRIANGLES, 0, 6);
  requestAnimationFrame(draw);
}}

playVideo();
requestAnimationFrame(draw);
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a 360 equirectangular video viewer HTML.")
    parser.add_argument("video", type=Path, help="A local 2:1 equirectangular MP4 video.")
    parser.add_argument("--output", type=Path, help="Output HTML path.")
    args = parser.parse_args()

    video = args.video.expanduser().resolve()
    if not video.exists():
        raise SystemExit(f"Video not found: {video}")
    output = args.output or video.with_name(f"{video.stem}-360-video-viewer.html")
    output.write_text(build_html(video), encoding="utf-8")
    print(output.resolve())


if __name__ == "__main__":
    main()
