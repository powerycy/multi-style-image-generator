#!/usr/bin/env python3
"""Create a lightweight Apple-style spatial photo viewer from image + depth."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from PIL import Image


def data_uri(path: Path) -> str:
    mime = "image/png"
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def write_viewer(image_path: Path, depth_path: Path, output_path: Path, grid: int) -> None:
    with Image.open(image_path) as image:
        width, height = image.size

    aspect = width / height
    cols = grid
    rows = max(40, round(grid / aspect))
    config = {
        "image": data_uri(image_path),
        "depth": data_uri(depth_path),
        "width": width,
        "height": height,
        "cols": cols,
        "rows": rows,
    }

    template = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Spatial Photo Preview</title>
  <style>
    html, body {
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      background: #101010;
      color: #f7f4ed;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", sans-serif;
    }
    .stage {
      position: fixed;
      inset: 0;
      display: grid;
      place-items: center;
      background:
        radial-gradient(circle at 50% 40%, rgba(255,255,255,.09), transparent 46%),
        #111;
    }
    canvas {
      width: min(100vw, calc(100vh * __ASPECT__));
      height: min(100vh, calc(100vw / __ASPECT__));
      display: block;
      background: #161616;
    }
    .hud {
      position: fixed;
      left: 16px;
      top: 14px;
      max-width: min(420px, calc(100vw - 32px));
      padding: 12px 14px;
      border: 1px solid rgba(255,255,255,.16);
      border-radius: 8px;
      background: rgba(8,8,8,.52);
      backdrop-filter: blur(18px);
      box-sizing: border-box;
      font-size: 13px;
      line-height: 1.45;
    }
    .hud strong {
      display: block;
      margin-bottom: 4px;
      font-size: 14px;
    }
    .controls {
      position: fixed;
      left: 50%;
      bottom: 16px;
      transform: translateX(-50%);
      width: min(760px, calc(100vw - 32px));
      display: grid;
      grid-template-columns: 1fr 1fr 1fr auto;
      gap: 12px;
      align-items: end;
      padding: 12px 14px;
      border: 1px solid rgba(255,255,255,.16);
      border-radius: 8px;
      background: rgba(8,8,8,.54);
      backdrop-filter: blur(18px);
      box-sizing: border-box;
      font-size: 12px;
    }
    label {
      display: grid;
      gap: 7px;
      color: rgba(255,255,255,.82);
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 38px;
      gap: 8px;
      align-items: center;
    }
    input[type="range"] {
      width: 100%;
      accent-color: #f2c46d;
    }
    button {
      height: 34px;
      padding: 0 14px;
      border: 0;
      border-radius: 7px;
      color: #111;
      background: #f2c46d;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
    }
    @media (max-width: 760px) {
      .controls {
        grid-template-columns: 1fr;
        bottom: 10px;
      }
      .hud {
        font-size: 12px;
      }
    }
  </style>
</head>
<body>
  <div class="stage"><canvas id="view"></canvas></div>
  <div class="hud">
    <strong>空间照片预览</strong>
    使用 Depth Anything V2 的深度图做轻微视差。移动鼠标或触控板会看到前景和背景产生错位，自动播放时会有很小幅度的摆动。
  </div>
  <div class="controls">
    <label>空间感
      <div class="row"><input id="depthScale" type="range" min="0" max="1.8" step="0.01" value="0.62"><span id="depthText">0.62</span></div>
    </label>
    <label>移动幅度
      <div class="row"><input id="motion" type="range" min="0" max="1.4" step="0.01" value="0.56"><span id="motionText">0.56</span></div>
    </label>
    <label>空间位移
      <div class="row"><input id="perspective" type="range" min="0.4" max="2.2" step="0.01" value="1.15"><span id="perspectiveText">1.15</span></div>
    </label>
    <button id="pause">暂停</button>
  </div>
  <script>
    const CONFIG = __CONFIG__;
    const canvas = document.getElementById('view');
    const gl = canvas.getContext('webgl', { antialias: true, preserveDrawingBuffer: true });
    if (!gl) document.body.innerHTML = '<p style="padding:20px">当前浏览器不支持 WebGL。</p>';

    const vertexSource = `
      attribute vec3 aPosition;
      attribute vec2 aUv;
      uniform mat4 uMatrix;
      uniform float uDepthScale;
      varying vec2 vUv;
      void main() {
        float z = aPosition.z * uDepthScale * 0.42;
        vec3 p = vec3(aPosition.xy, z);
        gl_Position = uMatrix * vec4(p, 1.0);
        vUv = aUv;
      }
    `;
    const fragmentSource = `
      precision mediump float;
      uniform sampler2D uImage;
      varying vec2 vUv;
      void main() {
        vec2 uv = clamp(vUv, vec2(0.001), vec2(0.999));
        gl_FragColor = texture2D(uImage, uv);
      }
    `;

    const state = {
      pointerX: 0,
      pointerY: 0,
      targetX: 0,
      targetY: 0,
      depthScale: 0.62,
      motion: 0.56,
      perspective: 1.15,
      paused: false,
      start: performance.now(),
    };

    function compile(type, source) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
      return shader;
    }

    const program = gl.createProgram();
    gl.attachShader(program, compile(gl.VERTEX_SHADER, vertexSource));
    gl.attachShader(program, compile(gl.FRAGMENT_SHADER, fragmentSource));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);

    const positionBuffer = gl.createBuffer();
    const uvBuffer = gl.createBuffer();
    const indexBuffer = gl.createBuffer();
    const aPosition = gl.getAttribLocation(program, 'aPosition');
    const aUv = gl.getAttribLocation(program, 'aUv');
    const uMatrix = gl.getUniformLocation(program, 'uMatrix');
    const uDepthScale = gl.getUniformLocation(program, 'uDepthScale');
    const uImage = gl.getUniformLocation(program, 'uImage');
    let indexCount = 0;

    function loadImage(src) {
      return new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = reject;
        image.src = src;
      });
    }

    function createTexture(image) {
      const texture = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
      return texture;
    }

    function buildMesh(depthImage) {
      const cols = CONFIG.cols;
      const rows = CONFIG.rows;
      const depthCanvas = document.createElement('canvas');
      depthCanvas.width = cols + 1;
      depthCanvas.height = rows + 1;
      const ctx = depthCanvas.getContext('2d', { willReadFrequently: true });
      ctx.drawImage(depthImage, 0, 0, depthCanvas.width, depthCanvas.height);
      const data = ctx.getImageData(0, 0, depthCanvas.width, depthCanvas.height).data;
      const aspect = CONFIG.width / CONFIG.height;
      const positions = [];
      const uvs = [];
      const indices = [];

      for (let y = 0; y <= rows; y++) {
        for (let x = 0; x <= cols; x++) {
          const i = (y * (cols + 1) + x) * 4;
          const d = data[i] / 255;
          const centeredDepth = (d - 0.48);
          const px = ((x / cols) - 0.5) * aspect * 2.0;
          const py = (0.5 - (y / rows)) * 2.0;
          positions.push(px, py, centeredDepth);
          uvs.push(x / cols, 1 - y / rows);
        }
      }

      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const a = y * (cols + 1) + x;
          const b = a + 1;
          const c = a + cols + 1;
          const d = c + 1;
          indices.push(a, c, b, b, c, d);
        }
      }

      indexCount = indices.length;
      gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.STATIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, uvBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(uvs), gl.STATIC_DRAW);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(indices), gl.STATIC_DRAW);
    }

    function mat4Identity() {
      return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);
    }

    function multiply(a, b) {
      const out = new Float32Array(16);
      for (let r = 0; r < 4; r++) {
        for (let c = 0; c < 4; c++) {
          out[c * 4 + r] =
            a[0 * 4 + r] * b[c * 4 + 0] +
            a[1 * 4 + r] * b[c * 4 + 1] +
            a[2 * 4 + r] * b[c * 4 + 2] +
            a[3 * 4 + r] * b[c * 4 + 3];
        }
      }
      return out;
    }

    function perspective(fovy, aspect, near, far) {
      const f = 1 / Math.tan(fovy / 2);
      const nf = 1 / (near - far);
      return new Float32Array([
        f / aspect, 0, 0, 0,
        0, f, 0, 0,
        0, 0, (far + near) * nf, -1,
        0, 0, (2 * far * near) * nf, 0
      ]);
    }

    function translate3(x, y, z) {
      return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, x,y,z,1]);
    }

    function rotateX(a) {
      const c = Math.cos(a), s = Math.sin(a);
      return new Float32Array([1,0,0,0, 0,c,s,0, 0,-s,c,0, 0,0,0,1]);
    }

    function rotateY(a) {
      const c = Math.cos(a), s = Math.sin(a);
      return new Float32Array([c,0,-s,0, 0,1,0,0, s,0,c,0, 0,0,0,1]);
    }

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = Math.floor(canvas.clientWidth * dpr);
      const h = Math.floor(canvas.clientHeight * dpr);
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      gl.viewport(0, 0, canvas.width, canvas.height);
    }

    function render(now) {
      resize();
      const t = (now - state.start) / 1000;
      if (!state.paused) {
        state.targetX = Math.sin(t * 0.42) * 0.36;
        state.targetY = Math.cos(t * 0.33) * 0.18;
      }
      state.pointerX += (state.targetX - state.pointerX) * 0.055;
      state.pointerY += (state.targetY - state.pointerY) * 0.055;

      gl.clearColor(0.06, 0.06, 0.06, 1);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST);
      gl.useProgram(program);
      gl.activeTexture(gl.TEXTURE0);
      gl.uniform1i(uImage, 0);

      const aspect = canvas.width / canvas.height;
      const cameraX = state.pointerX * state.motion * 0.24;
      const cameraY = state.pointerY * state.motion * 0.14;
      const matrix = multiply(
        perspective((38 / state.perspective) * Math.PI / 180, aspect, 0.01, 20),
        multiply(
          translate3(-cameraX, -cameraY, -3.25),
          multiply(rotateX(state.pointerY * 0.018), rotateY(state.pointerX * -0.028))
        )
      );

      gl.uniformMatrix4fv(uMatrix, false, matrix);
      gl.uniform1f(uDepthScale, state.depthScale);

      gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
      gl.enableVertexAttribArray(aPosition);
      gl.vertexAttribPointer(aPosition, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, uvBuffer);
      gl.enableVertexAttribArray(aUv);
      gl.vertexAttribPointer(aUv, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
      gl.drawElements(gl.TRIANGLES, indexCount, gl.UNSIGNED_SHORT, 0);
      requestAnimationFrame(render);
    }

    function bindSlider(id, key, textId) {
      const input = document.getElementById(id);
      const text = document.getElementById(textId);
      input.addEventListener('input', () => {
        state[key] = Number(input.value);
        text.textContent = Number(input.value).toFixed(2);
      });
    }
    bindSlider('depthScale', 'depthScale', 'depthText');
    bindSlider('motion', 'motion', 'motionText');
    bindSlider('perspective', 'perspective', 'perspectiveText');
    document.getElementById('pause').addEventListener('click', e => {
      state.paused = !state.paused;
      e.currentTarget.textContent = state.paused ? '播放' : '暂停';
    });

    window.addEventListener('pointermove', e => {
      if (!state.paused) return;
      state.targetX = ((e.clientX / window.innerWidth) - 0.5) * 1.0;
      state.targetY = ((e.clientY / window.innerHeight) - 0.5) * -0.55;
    });
    window.addEventListener('resize', resize);

    Promise.all([loadImage(CONFIG.image), loadImage(CONFIG.depth)]).then(([image, depth]) => {
      createTexture(image);
      buildMesh(depth);
      requestAnimationFrame(render);
    });
  </script>
</body>
</html>
"""
    document = (
        template
        .replace("__CONFIG__", json.dumps(config))
        .replace("__ASPECT__", f"{aspect:.8f}")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("depth", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--grid", type=int, default=150)
    args = parser.parse_args()
    write_viewer(args.image, args.depth, args.output, args.grid)
    print(f"Viewer: {args.output}")


if __name__ == "__main__":
    main()
