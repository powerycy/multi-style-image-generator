## 空间照片预览模式

用户提供或刚生成一张图片并要求“空间景深图、空间照片、景深交互”时，直接运行统一入口，不询问参数：

```bash
python3 scripts/run_with_deps.py create_spatial_preview.py \
  <image-path> \
  --out-dir <output-directory>
```

默认 `immersive` preset 必须保持以下交付契约：

- 使用 `depth-anything-v2-small` 真实模型推理 raw depth，再输出稳定化 depth；Apple Depth Pro 只在用户显式要求 `--depth-backend apple-depth-pro` 且已安装时使用。
- 使用单层、单次 `gl.drawElements` 的 depth mesh；不得自动选择双层人物蒙版、前景抠图、补洞纹理或卡片分层。
- 以历史 demo 的镜头手感为默认基准：`depthScale=0.62`、`motion=0.56`、`perspective=1.15`；自动巡游 X/Y 振幅为 `0.36/0.18`。不要为了增强立体感擅自放大空间感或移动幅度，二者会相乘并造成透视拉扯。
- 同时支持鼠标、触摸与 `deviceorientation`；手动输入后平滑回到自动巡游。
- 不生成额外 HUD；默认在底部显示“空间感、移动幅度、透视”三条实时滑动条，以及“暂停巡游 / 自动巡游”按钮。控件需兼容桌面与手机窄屏，且不影响鼠标、触摸和 `deviceorientation` 交互。
- 默认不增加景深虚化，以保持历史 demo 的清晰度和空间观感；只有用户明确要求虚化时才启用 `--blur depth`。启用后使用 `1-smoothstep(0.14,0.30,depth)`、五点采样半径 `2.25px`、混合强度 `0.52`，保持人物和近景清晰。
- 在 HTML 中内嵌 RGB 与稳定 depth，保持原图宽高比，允许直接 `file://` 打开；最终至少交付稳定 depth PNG 与 HTML。

深度输入和兼容模式：

- 已有稳定深度图使用 `--depth <stable.png>`；已有模型原始深度使用 `--raw-depth <raw.png>`，不得混淆两者。
- 只有用户明确接受非模型预览时才使用 `--depth-backend heuristic`。结果必须标记 `heuristic-fallback`，不得称为 Depth Anything V2 或真实模型深度。
- `--spatial-mode displacement` 只作为显式兼容模式；`--spatial-mode mesh` 是默认。`--blur`、`--interaction`、`--depth-scale`、`--motion` 等参数只在用户明确要求偏离历史 demo 基准时调整。
- `--spatial-mode pointcloud` 仅在用户明确要求点云时使用；它是独立渲染模式，不受单层 mesh 的 `gl.drawElements` 约束。
- 真实 backend 不可用时停止并准确报告；不要捕获错误后静默降级。
- 最终回复给出 `raw_depth`（本次推理时）、`stable_depth` 和 `html` 路径，并准确说明 `depth_provenance`。
- 不要把空间照片与 360° 全景预览混用。

## 单图深度点云预览模式

对已有普通图片生成点云时，使用统一入口，让它生成或复用真实深度图：

```bash
python3 scripts/run_with_deps.py create_spatial_preview.py \
  <image-path> \
  --spatial-mode pointcloud \
  --out-dir <output-directory>
```

- 默认点云参数：深度 `1.25`、点大小 `2.1`、焦平面 `0.46`、初始水平/垂直旋转 `-0.42/0.18`、镜头距离 `2.25`，横向最多采样 `250` 点（不超过源图宽度），平坦区域交错减采样、细节区域加密，剔除断层中间值与孤立深度尖点。
- HTML 内嵌 RGB 与稳定 depth，可直接 `file://` 打开；支持鼠标或触摸拖拽旋转、滚轮缩放，以及“深度、点大小、焦平面”三条滑动条；支持水平与垂直自由 360° 旋转，松手后保持视角，不提供演示或重置按钮。
- 默认使用 Depth Anything V2 Small；已有稳定深度图用 `--depth <stable.png>`，已有原始模型深度用 `--raw-depth <raw.png>`。不得静默改用启发式深度。
- 最终准确说明这是“单图深度点云”而非完整 3D 重建，并交付 raw depth（本次推理时）、stable depth 与 point-cloud HTML。


## 控件、精度与兼容参数

- 默认 `--controls visible`。只有明确要求“不要控制条、无按钮、无滑杆”才用 `--controls hidden`，点云也同时隐藏说明浮层。生图的“无 HUD/无文字”只约束底图，不自动隐藏预览控件。
- 点云水平与垂直拖拽均不限制转角，可连续 360° 旋转；松手后保持当前视角。不要添加自动演示或重置视角按钮。点大小按距离调整并用柔边 splat 抗锯齿，手机自动适配完整画幅。旋转到背面显示同一组点，不补造隐藏表面。
- raw depth 与 stable depth 输出为 16-bit PNG；边缘感知平滑完成后才量化，几何采样内嵌数值以避免浏览器 canvas 的 8-bit 降精度。旧 8-bit PNG 仍兼容，但不能恢复已丢失精度。稳定深度仅表示相对远近，不是米制距离。
- mesh 剔除归一化深度跨度超过 0.28 的三角形；真实遮挡缺口可以留空，不补画背面。默认移动手感保持不变。
- `--preset` 只保留有效的 `immersive`。删除原来只改元数据的 `v18/legacy`；兼容位移模式需显式 `--spatial-mode displacement --controls hidden`，其渲染器没有滑杆。
- 用户明确要求拉满空间感/位移时可用 `--depth-scale 1.8 --motion 1.4`，不连带增大自动巡游幅度。明确要求背景虚化再加 `--blur depth`。
- 复用深度时如实标注 `supplied-stable-depth` 或 `supplied-raw-depth`；不能仅凭文件名声称本次运行了模型。
