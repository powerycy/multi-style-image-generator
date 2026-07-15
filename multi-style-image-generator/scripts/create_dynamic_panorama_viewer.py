#!/usr/bin/env python3
"""Create a standalone animated 360 panorama viewer.

The source image remains static. Motion is added in the viewer through camera
drift, FOV breathing, mist bands, spirit particles, and subtle light glints.
"""

from __future__ import annotations

import argparse
import base64
import html
import mimetypes
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
    #view, #fx {{
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100vh;
      display: block;
    }}
    #view {{
      cursor: grab;
      touch-action: none;
    }}
    #view:active {{ cursor: grabbing; }}
    #fx {{
      pointer-events: none;
      mix-blend-mode: screen;
    }}
    .shade {{
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at 52% 48%, transparent 0%, transparent 54%, rgba(0,0,0,.34) 100%),
        linear-gradient(to bottom, rgba(0,0,0,.16), transparent 32%, rgba(0,0,0,.24));
    }}
    .hud {{
      position: fixed;
      left: 16px;
      bottom: 14px;
      padding: 8px 10px;
      border: 1px solid rgba(255,255,255,.18);
      border-radius: 8px;
      background: rgba(0,0,0,.34);
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
  <canvas id="fx"></canvas>
  <div class="shade"></div>
  <div class="hud">自动巡游 · 拖拽旋转 · 滚轮缩放 · 双击复位</div>
  <script>
  const imageUrl = {image_url};
  const canvas = document.getElementById("view");
  const fx = document.getElementById("fx");
  const fxCtx = fx.getContext("2d");
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
    uniform float time;
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
      vec3 color = texture2D(pano, vec2(u, 1.0 - v)).rgb;

      float pulse = 0.5 + 0.5 * sin(time * 0.8 + u * 18.0);
      float upperGlow = smoothstep(0.35, 0.82, v) * 0.045 * pulse;
      float lowerMist = smoothstep(0.18, 0.0, v) * 0.06;
      color += vec3(0.42, 0.72, 0.62) * upperGlow;
      color += vec3(0.22, 0.42, 0.38) * lowerMist;

      gl_FragColor = vec4(color, 1.0);
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

  const quadVertices = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
  const vertexBuffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, quadVertices, gl.STATIC_DRAW);

  const position = gl.getAttribLocation(program, "position");
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

  const uniforms = {{
    yaw: gl.getUniformLocation(program, "yaw"),
    pitch: gl.getUniformLocation(program, "pitch"),
    fov: gl.getUniformLocation(program, "fov"),
    aspect: gl.getUniformLocation(program, "aspect"),
    time: gl.getUniformLocation(program, "time")
  }};

  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);

  let textureReady = false;
  const image = new Image();
  image.onload = () => {{
    const sourceAspect = image.width / image.height;
    if (Math.abs(sourceAspect - 2) > 0.08) {{
      document.querySelector(".hud").textContent = "自动巡游 · 源图非 2:1，会有纵向变形";
    }}
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
    textureReady = true;
  }};
  image.src = imageUrl;

  let yaw = 0;
  let pitch = 0;
  let targetFov = Math.PI / 2.45;
  let dragging = false;
  let lastX = 0;
  let lastY = 0;
  let lastTime = 0;
  let idleDelay = 0;

  const particles = Array.from({{ length: 96 }}, (_, i) => ({{
    x: ((i * 37) % 100) / 100,
    y: ((i * 61) % 100) / 100,
    r: 0.8 + ((i * 19) % 22) / 10,
    s: 0.018 + ((i * 13) % 27) / 1000,
    phase: i * 0.73,
    hue: i % 3
  }}));

  canvas.addEventListener("pointerdown", (event) => {{
    dragging = true;
    idleDelay = 2.5;
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
  }});
  canvas.addEventListener("pointerup", () => dragging = false);
  canvas.addEventListener("pointercancel", () => dragging = false);
  canvas.addEventListener("wheel", (event) => {{
    event.preventDefault();
    idleDelay = 2.5;
    targetFov = Math.max(0.55, Math.min(1.75, targetFov + event.deltaY * 0.0008));
  }}, {{ passive: false }});
  canvas.addEventListener("dblclick", () => {{
    yaw = 0;
    pitch = 0;
    targetFov = Math.PI / 2.45;
    idleDelay = 1.2;
  }});
  window.addEventListener("resize", resizeAll);

  function resizeAll() {{
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.floor(canvas.clientWidth * dpr);
    const height = Math.floor(canvas.clientHeight * dpr);
    if (canvas.width !== width || canvas.height !== height) {{
      canvas.width = width;
      canvas.height = height;
      fx.width = width;
      fx.height = height;
    }}
    gl.viewport(0, 0, canvas.width, canvas.height);
  }}

  function drawFx(time) {{
    const w = fx.width;
    const h = fx.height;
    if (!w || !h) return;
    fxCtx.clearRect(0, 0, w, h);

    for (let layer = 0; layer < 3; layer++) {{
      const y = h * (0.24 + layer * 0.18 + Math.sin(time * 0.11 + layer) * 0.025);
      const offset = ((time * (18 + layer * 8)) % (w * 1.35)) - w * 0.35;
      const grad = fxCtx.createLinearGradient(offset, y, offset + w * 0.85, y + h * 0.04);
      grad.addColorStop(0, "rgba(92, 160, 150, 0)");
      grad.addColorStop(0.5, `rgba(120, 210, 185, ${{0.030 + layer * 0.012}})`);
      grad.addColorStop(1, "rgba(92, 160, 150, 0)");
      fxCtx.fillStyle = grad;
      fxCtx.beginPath();
      fxCtx.ellipse(offset + w * 0.42, y, w * 0.46, h * (0.055 + layer * 0.012), Math.sin(time * 0.08) * 0.08, 0, Math.PI * 2);
      fxCtx.fill();
      fxCtx.beginPath();
      fxCtx.ellipse(offset - w * 0.18, y + h * 0.08, w * 0.38, h * 0.045, -0.08, 0, Math.PI * 2);
      fxCtx.fill();
    }}

    for (const p of particles) {{
      const driftX = (p.x + time * p.s * 0.045) % 1;
      const wave = Math.sin(time * (0.55 + p.s * 9.0) + p.phase);
      const x = driftX * w;
      const y = (p.y + wave * 0.018) * h;
      const alpha = 0.18 + 0.22 * Math.max(0, Math.sin(time * 1.2 + p.phase));
      const color = p.hue === 0 ? "124, 238, 195" : p.hue === 1 ? "194, 230, 166" : "150, 210, 255";
      fxCtx.beginPath();
      fxCtx.fillStyle = `rgba(${{color}}, ${{alpha}})`;
      fxCtx.shadowColor = `rgba(${{color}}, 0.55)`;
      fxCtx.shadowBlur = 9;
      fxCtx.arc(x, y, p.r * Math.min(window.devicePixelRatio || 1, 2), 0, Math.PI * 2);
      fxCtx.fill();
    }}
    fxCtx.shadowBlur = 0;

    const pulse = 0.5 + 0.5 * Math.sin(time * 0.7);
    const glow = fxCtx.createRadialGradient(w * 0.62, h * 0.38, 0, w * 0.62, h * 0.38, Math.max(w, h) * 0.36);
    glow.addColorStop(0, `rgba(180, 245, 210, ${{0.045 + pulse * 0.035}})`);
    glow.addColorStop(1, "rgba(180, 245, 210, 0)");
    fxCtx.fillStyle = glow;
    fxCtx.fillRect(0, 0, w, h);
  }}

  function frame(now) {{
    const time = now * 0.001;
    const dt = lastTime ? Math.min(0.05, time - lastTime) : 0;
    lastTime = time;

    if (!dragging) {{
      idleDelay = Math.max(0, idleDelay - dt);
      if (idleDelay === 0) {{
        yaw += dt * 0.055;
        pitch += (Math.sin(time * 0.22) * 0.035 - pitch) * dt * 0.45;
      }}
    }}
    const fov = targetFov + Math.sin(time * 0.32) * 0.018;

    resizeAll();
    if (textureReady) {{
      gl.clearColor(0, 0, 0, 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform1f(uniforms.yaw, yaw);
      gl.uniform1f(uniforms.pitch, pitch);
      gl.uniform1f(uniforms.fov, fov);
      gl.uniform1f(uniforms.aspect, canvas.width / canvas.height);
      gl.uniform1f(uniforms.time, time);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }}
    drawFx(time);
    requestAnimationFrame(frame);
  }}

  resizeAll();
  requestAnimationFrame(frame);
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an animated standalone 360 panorama viewer HTML.")
    parser.add_argument("image", type=Path, help="Path to a 2:1 equirectangular panorama image.")
    parser.add_argument("--out", type=Path, help="Output HTML path. Defaults to <image>-dynamic-360-viewer.html.")
    parser.add_argument("--title", default="Dynamic 360 Panorama Preview", help="HTML title.")
    args = parser.parse_args()

    image_path = args.image.expanduser().resolve()
    if not image_path.exists():
      raise SystemExit(f"Image not found: {image_path}")

    out_path = args.out.expanduser().resolve() if args.out else image_path.with_name(f"{image_path.stem}-dynamic-360-viewer.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
    image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    image_url = f"data:{mime};base64,{image_data}"

    html_text = HTML_TEMPLATE.format(
        title=html.escape(args.title, quote=True),
        image_url=repr(image_url),
    )
    out_path.write_text(html_text, encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
