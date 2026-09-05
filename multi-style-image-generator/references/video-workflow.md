## 动态视频模式

使用 BigModel/CogVideoX 生成动态效果时走独立脚本：

```bash
python3 scripts/create_bigmodel_video.py \
  --prompt "<video prompt>" \
  --image "<optional-local-image.png>" \
  --model cogvideox-3 \
  --quality quality \
  --size 1920x1080 \
  --fps 30 \
  --with-audio \
  --output-dir output/imagegen/videos
```

规则：

- 不要把 API Key 写入 skill 文件、脚本、README、对话或输出产物，也不要要求用户在对话中粘贴 API Key。
- macOS 首次生成视频且没有环境变量时，脚本会弹出隐藏输入的系统对话框，并把 API Key 保存到 macOS 钥匙串；后续自动读取，不再重复询问。环境变量 `BIGMODEL_API_KEY` 或 `ZHIPU_API_KEY` 仍可作为临时覆盖，且优先于钥匙串。
- 用户说“更换视频生成 SK”时，运行 `python3 scripts/create_bigmodel_video.py --replace-api-key`；用户说“删除已保存的视频生成 SK”时，运行 `python3 scripts/create_bigmodel_video.py --forget-api-key`。不要在命令参数中传入 SK。
- 用户给本地图片并要求“把这个变成视频/让这张图动起来”时，传 `--image <local-path>`。脚本会把 PNG/JPEG 转为 `image_url` 的 data URL；图片必须不超过 5MB。
- 视频 prompt 应描述镜头运动、主体运动、环境动态和节奏，例如“slow cinematic push-in, cloth and dust moving, magical particles drifting”。避免写静态构图词过多。
- 如果用户要求“动态效果”但没有指定时长，默认生成 5 秒横版视频；仅当用户明确要求时使用 10 秒。`duration` 只支持 `5` 或 `10`；参数默认 `model=cogvideox-3`、`quality=quality`、`size=1920x1080`、`fps=30`、`with_audio=true`。
- 脚本会提交任务、轮询异步结果并下载视频；最终回复给出本地视频文件链接和任务 JSON 链接。
- 如果用户要求“360 全景视频、360 环景视频、360 图生视频、环景图动起来”，从源头保持两步走：先生成 2:1 等距柱状投影全景图，再把该 2:1 图片作为 `--image` 输入生成 2:1 视频，最后生成 360° 全景视频预览 HTML。`file://` 本地打开时优先用 `scripts/create_panorama_frame_sequence_viewer.py`：先运行 `command -v ffmpeg` 检测 ffmpeg，再从视频抽帧并把帧内嵌进 HTML 循环播放，避免浏览器把本地 `<video>` 上传到 WebGL 纹理时出现黑屏。如果检测不到 ffmpeg，说明它是可选的系统依赖并给出由用户自行安装的提示（macOS 可举例 `brew install ffmpeg`）；不要自动运行系统安装、`sudo` 或包管理器。只有在确定通过 HTTP 服务访问时，才使用 `scripts/create_panorama_video_viewer.py <video.mp4>` 的原始视频纹理方案。不要只把普通 16:9 视频塞进 360° 全景预览。
