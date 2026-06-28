#!/usr/bin/env python3
"""Create a standalone WebGL viewer for a 360 equirectangular image."""

from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import os
import shutil
from pathlib import Path


HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #050507;
      color: #f5f1e8;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    canvas {{
      display: block;
      width: 100vw;
      height: 100vh;
      cursor: grab;
      touch-action: none;
    }}
    canvas:active {{ cursor: grabbing; }}
    .hud {{
      position: fixed;
      left: 16px;
      bottom: 14px;
      padding: 8px 10px;
      border: 1px solid rgba(255,255,255,.18);
      border-radius: 8px;
      background: rgba(0,0,0,.36);
      color: rgba(255,255,255,.82);
      font-size: 12px;
      line-height: 1.4;
      user-select: none;
      backdrop-filter: blur(8px);
    }}
  </style>
</head>
<body>
  <canvas id="view"></canvas>
  <div class="hud">拖拽旋转 · 滚轮缩放 · 双击复位</div>
  <script>
  const imageUrl = {image_url};
  const canvas = document.getElementById("view");
  const gl = canvas.getContext("webgl", {{ antialias: true }});
  if (!gl) {{
    document.body.innerHTML = "<p style='padding:20px'>当前浏览器不支持 WebGL。</p>";
    throw new Error("WebGL unavailable");
  }}

  const vertexSource = `
    attribute vec2 position;
    varying vec2 vUv;
    void main() {{
      vUv = position * 0.5 + 0.5;
      gl_Position = vec4(position, 0.0, 1.0);
    }}
  `;
  const fragmentSource = `
    precision mediump float;
    varying vec2 vUv;
    uniform sampler2D pano;
    uniform float yaw;
    uniform float pitch;
    uniform float fov;
    uniform float aspect;
    const float PI = 3.141592653589793;

    mat3 rotateY(float a) {{
      float c = cos(a), s = sin(a);
      return mat3(c,0.0,-s, 0.0,1.0,0.0, s,0.0,c);
    }}

    mat3 rotateX(float a) {{
      float c = cos(a), s = sin(a);
      return mat3(1.0,0.0,0.0, 0.0,c,s, 0.0,-s,c);
    }}

    void main() {{
      vec2 screen = vUv * 2.0 - 1.0;
      screen.x *= aspect;
      float z = -1.0 / tan(fov * 0.5);
      vec3 d = normalize(vec3(screen.x, screen.y, z));
      d = rotateY(yaw) * rotateX(pitch) * d;
      float u = atan(d.z, d.x) / (2.0 * PI) + 0.5;
      float v = asin(clamp(d.y, -1.0, 1.0)) / PI + 0.5;
      gl_FragColor = texture2D(pano, vec2(u, 1.0 - v));
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

  const quadVertices = new Float32Array([
    -1, -1,
     1, -1,
    -1,  1,
     1,  1
  ]);
  const vertexBuffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, quadVertices, gl.STATIC_DRAW);

  const position = gl.getAttribLocation(program, "position");
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);

  const image = new Image();
  image.onload = () => {{
    const sourceAspect = image.width / image.height;
    if (Math.abs(sourceAspect - 2) > 0.08) {{
      document.querySelector(".hud").textContent = "拖拽旋转 · 滚轮缩放 · 双击复位 · 源图非 2:1，会有纵向变形";
    }}
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
    render();
  }};
  image.src = imageUrl;

  let yaw = 0;
  let pitch = 0;
  let fov = Math.PI / 2.4;
  let dragging = false;
  let lastX = 0;
  let lastY = 0;

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
    yaw += dx * 0.004;
    pitch = Math.max(-1.45, Math.min(1.45, pitch + dy * 0.004));
    render();
  }});
  canvas.addEventListener("pointerup", () => dragging = false);
  canvas.addEventListener("wheel", (event) => {{
    event.preventDefault();
    fov = Math.max(0.55, Math.min(1.75, fov + event.deltaY * 0.0008));
    render();
  }}, {{ passive: false }});
  canvas.addEventListener("dblclick", () => {{
    yaw = 0;
    pitch = 0;
    fov = Math.PI / 2.4;
    render();
  }});
  window.addEventListener("resize", render);

  function resize() {{
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.floor(canvas.clientWidth * dpr);
    const height = Math.floor(canvas.clientHeight * dpr);
    if (canvas.width !== width || canvas.height !== height) {{
      canvas.width = width;
      canvas.height = height;
    }}
    gl.viewport(0, 0, canvas.width, canvas.height);
  }}

  function render() {{
    resize();
    gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    const aspect = canvas.width / canvas.height;
    gl.uniform1f(gl.getUniformLocation(program, "yaw"), yaw);
    gl.uniform1f(gl.getUniformLocation(program, "pitch"), pitch);
    gl.uniform1f(gl.getUniformLocation(program, "fov"), fov);
    gl.uniform1f(gl.getUniformLocation(program, "aspect"), aspect);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }}
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a standalone 360 panorama viewer HTML.")
    parser.add_argument("image", type=Path, help="Path to a 2:1 equirectangular panorama image.")
    parser.add_argument("--out", type=Path, help="Output HTML path. Defaults to <image>-360-viewer.html.")
    parser.add_argument("--title", default="360 Panorama Preview", help="HTML title.")
    parser.add_argument("--embed-image", action="store_true", help="Embed the image as a data URI for file:// viewing.")
    parser.add_argument("--copy-image", action="store_true", help="Copy image next to HTML for portable viewing.")
    args = parser.parse_args()

    image_path = args.image.expanduser().resolve()
    if not image_path.exists():
        raise SystemExit(f"Image not found: {image_path}")

    out_path = args.out.expanduser().resolve() if args.out else image_path.with_name(f"{image_path.stem}-360-viewer.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.embed_image:
        mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
        image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
        image_url = f"data:{mime};base64,{image_data}"
    else:
        viewer_image_path = image_path
        if args.copy_image and image_path.parent != out_path.parent:
            viewer_image_path = out_path.with_name(image_path.name)
            if viewer_image_path.resolve() != image_path:
                shutil.copy2(image_path, viewer_image_path)
        image_url = os.path.relpath(viewer_image_path, out_path.parent)
        image_url = image_url.replace(os.sep, "/")

    html_text = HTML_TEMPLATE.format(
        title=html.escape(args.title, quote=True),
        image_url=repr(image_url),
    )
    out_path.write_text(html_text, encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
