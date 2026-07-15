#!/usr/bin/env python3
"""Generate a video with BigModel CogVideoX and download the result."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


GENERATE_URL = "https://open.bigmodel.cn/api/paas/v4/videos/generations"
ASYNC_RESULT_URL = "https://open.bigmodel.cn/api/paas/v4/async-result/{task_id}"
VIDEO_URL_RE = re.compile(r"https?://[^\s\"']+\.(?:mp4|mov|webm)(?:\?[^\s\"']*)?", re.IGNORECASE)
SUCCESS_STATUSES = {"success", "succeeded", "completed", "complete", "done"}
RUNNING_STATUSES = {"submitted", "pending", "running", "processing", "in_progress", "queueing", "queued"}
FAILED_STATUSES = {"failed", "fail", "error", "cancelled", "canceled", "timeout"}
KEYCHAIN_SERVICE = "multi-style-image-generator.bigmodel"
KEYCHAIN_ACCOUNT = "api-key"
SECURITY = "/usr/bin/security"
OSASCRIPT = "/usr/bin/osascript"


def _keychain_item_missing(result: subprocess.CompletedProcess) -> bool:
    message = f"{result.stdout}\n{result.stderr}".lower()
    return result.returncode == 44 or "could not be found" in message or "not found" in message


def keychain_read(run=subprocess.run):
    try:
        result = run(
            [
                SECURITY,
                "find-generic-password",
                "-a",
                KEYCHAIN_ACCOUNT,
                "-s",
                KEYCHAIN_SERVICE,
                "-w",
            ],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise SystemExit("无法访问 macOS 钥匙串，请改用 BIGMODEL_API_KEY 环境变量。") from exc
    if result.returncode == 0:
        return result.stdout.strip() or None
    if _keychain_item_missing(result):
        return None
    raise SystemExit(f"读取 macOS 钥匙串失败（状态码 {result.returncode}）。")


def prompt_api_key(run=subprocess.run) -> str:
    script = (
        'text returned of (display dialog "请输入 BigModel/CogVideoX API Key（SK）" '
        'default answer "" with hidden answer buttons {"取消", "保存"} '
        'default button "保存" cancel button "取消" with title "Multi Style Image Generator")'
    )
    try:
        result = run([OSASCRIPT, "-e", script], capture_output=True, text=True)
    except OSError as exc:
        raise SystemExit("无法打开安全输入框，请改用 BIGMODEL_API_KEY 环境变量。") from exc
    if result.returncode != 0:
        raise SystemExit("已取消输入，未保存 API Key，也未生成视频。")
    api_key = result.stdout.strip()
    if not api_key:
        raise SystemExit("API Key 为空，未保存，也未生成视频。")
    return api_key


def keychain_write(api_key: str, run=subprocess.run) -> None:
    encoded_key = api_key.encode("utf-8").hex()
    command = (
        f"add-generic-password -U -a {KEYCHAIN_ACCOUNT} "
        f"-s {KEYCHAIN_SERVICE} -X {encoded_key}\n"
    )
    try:
        result = run(
            [SECURITY, "-i"],
            input=command,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise SystemExit("无法写入 macOS 钥匙串，请改用 BIGMODEL_API_KEY 环境变量。") from exc
    if result.returncode != 0:
        raise SystemExit(f"保存 API Key 到 macOS 钥匙串失败（状态码 {result.returncode}）。")
    if keychain_read(run) != api_key:
        raise SystemExit("保存后验证 macOS 钥匙串失败，API Key 未确认写入。")


def keychain_delete(run=subprocess.run) -> bool:
    try:
        result = run(
            [
                SECURITY,
                "delete-generic-password",
                "-a",
                KEYCHAIN_ACCOUNT,
                "-s",
                KEYCHAIN_SERVICE,
            ],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise SystemExit("无法访问 macOS 钥匙串。") from exc
    if result.returncode == 0:
        return True
    if _keychain_item_missing(result):
        return False
    raise SystemExit(f"删除 macOS 钥匙串项目失败（状态码 {result.returncode}）。")


def resolve_api_key(environ, api_key_env: str, platform_name: str, run=subprocess.run) -> str:
    api_key = environ.get(api_key_env) or environ.get("ZHIPU_API_KEY")
    if api_key:
        return api_key
    if platform_name != "darwin":
        raise SystemExit(
            f"Missing API key. Set {api_key_env} or ZHIPU_API_KEY in the environment. "
            "Automatic secure storage is currently available only on macOS."
        )
    api_key = keychain_read(run)
    if api_key:
        return api_key
    api_key = prompt_api_key(run)
    keychain_write(api_key, run)
    return api_key


def request_json(method: str, url: str, api_key: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code in {401, 403}:
            raise RuntimeError(
                f"HTTP {exc.code}: API credential rejected. "
                "On macOS, replace the saved key with --replace-api-key."
            ) from exc
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc


def walk(value: Any) -> list[Any]:
    values = [value]
    if isinstance(value, dict):
        for item in value.values():
            values.extend(walk(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(walk(item))
    return values


def first_string_by_key(value: Any, keys: set[str]) -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, str) and item.strip():
                return item
        for item in value.values():
            found = first_string_by_key(item, keys)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = first_string_by_key(item, keys)
            if found:
                return found
    return None


def extract_task_id(response: dict[str, Any]) -> str | None:
    for key in ("task_id", "taskId", "id", "request_id", "requestId"):
        found = first_string_by_key(response, {key})
        if found:
            return found
    return None


def extract_status(response: dict[str, Any]) -> str | None:
    status = first_string_by_key(response, {"task_status", "taskStatus", "status", "state"})
    return status.lower() if status else None


def extract_video_url(response: dict[str, Any]) -> str | None:
    direct = first_string_by_key(response, {"video_url", "videoUrl", "url"})
    if direct and direct.startswith(("http://", "https://")):
        return direct
    for value in walk(response):
        if isinstance(value, str):
            match = VIDEO_URL_RE.search(value)
            if match:
                return match.group(0)
    return None


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", text.strip()).strip("-")
    return (slug[:48] or "bigmodel-video").lower()


def download_file(url: str, output_path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "CodexSkill/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response:
        output_path.write_bytes(response.read())


def image_to_data_url(path: Path) -> str:
    image_path = path.expanduser().resolve()
    if not image_path.exists():
        raise SystemExit(f"Image not found: {image_path}")
    if image_path.stat().st_size > 5 * 1024 * 1024:
        raise SystemExit(f"Image is larger than 5MB: {image_path}")
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
    if mime_type not in {"image/png", "image/jpeg", "image/jpg"}:
        raise SystemExit(f"Unsupported image MIME type {mime_type}. Use PNG or JPEG.")
    import base64

    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and download a BigModel CogVideoX video.")
    parser.add_argument("--prompt", help="Video generation prompt.")
    parser.add_argument("--image", type=Path, help="Optional local PNG/JPEG image for image-to-video.")
    parser.add_argument("--image-url", help="Optional image URL or data URL for image-to-video.")
    parser.add_argument("--model", default="cogvideox-3")
    parser.add_argument("--quality", default="quality")
    parser.add_argument("--size", default="1920x1080")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--duration", type=int, choices=[5, 10], help="Optional duration in seconds.")
    audio = parser.add_mutually_exclusive_group()
    audio.add_argument("--with-audio", dest="with_audio", action="store_true", default=True)
    audio.add_argument("--no-audio", dest="with_audio", action="store_false")
    parser.add_argument("--output-dir", type=Path, default=Path("output/imagegen/videos"))
    parser.add_argument("--name", help="Output base name. Defaults to a slug from the prompt.")
    parser.add_argument("--api-key-env", default="BIGMODEL_API_KEY", help="Environment variable containing the API key.")
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--dry-run", action="store_true", help="Print payload only; do not call the API.")
    key_management = parser.add_mutually_exclusive_group()
    key_management.add_argument(
        "--replace-api-key",
        action="store_true",
        help="Prompt securely and replace the API key saved in macOS Keychain.",
    )
    key_management.add_argument(
        "--forget-api-key",
        action="store_true",
        help="Delete the API key saved in macOS Keychain.",
    )
    return parser


def main(argv=None, environ=None, platform_name=None, run=subprocess.run) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    environ = os.environ if environ is None else environ
    platform_name = sys.platform if platform_name is None else platform_name

    if args.replace_api_key:
        if platform_name != "darwin":
            raise SystemExit("安全对话框和自动保存目前只支持 macOS 钥匙串。")
        keychain_write(prompt_api_key(run), run)
        print("新的 API Key 已保存到 macOS 钥匙串（安全存储）。")
        return 0
    if args.forget_api_key:
        if platform_name != "darwin":
            raise SystemExit("自动保存目前只支持 macOS 钥匙串。")
        deleted = keychain_delete(run)
        print("已删除 macOS 钥匙串中的 API Key。" if deleted else "macOS 钥匙串中没有已保存的 API Key。")
        return 0
    if not args.prompt:
        parser.error("--prompt is required unless managing the saved API key")

    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "quality": args.quality,
        "with_audio": args.with_audio,
        "size": args.size,
        "fps": args.fps,
    }
    if args.duration:
        payload["duration"] = args.duration
    if args.image and args.image_url:
        raise SystemExit("Use only one of --image or --image-url.")
    if args.image:
        payload["image_url"] = image_to_data_url(args.image)
    elif args.image_url:
        payload["image_url"] = args.image_url

    if args.dry_run:
        printable_payload = dict(payload)
        if args.image and "image_url" in printable_payload:
            printable_payload["image_url"] = "<local-image-data-url-redacted>"
        print(json.dumps({"url": GENERATE_URL, "payload": printable_payload}, ensure_ascii=False, indent=2))
        return 0
    api_key = resolve_api_key(environ, args.api_key_env, platform_name, run)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_name = f"{args.name or safe_slug(args.prompt)}-{stamp}"
    submit_path = args.output_dir / f"{base_name}-submit.json"
    result_path = args.output_dir / f"{base_name}-result.json"
    video_path = args.output_dir / f"{base_name}.mp4"

    submit_response = request_json("POST", GENERATE_URL, api_key, payload)
    write_json(submit_path, submit_response)

    video_url = extract_video_url(submit_response)
    task_id = extract_task_id(submit_response)
    final_response = submit_response

    if not video_url:
        if not task_id:
            raise SystemExit(f"Could not find task id or video URL in submit response: {submit_path}")
        deadline = time.time() + args.timeout
        result_url = ASYNC_RESULT_URL.format(task_id=urllib.parse.quote(task_id, safe=""))
        while time.time() < deadline:
            final_response = request_json("GET", result_url, api_key)
            write_json(result_path, final_response)
            video_url = extract_video_url(final_response)
            status = extract_status(final_response)
            if video_url and (not status or status in SUCCESS_STATUSES):
                break
            if status in FAILED_STATUSES:
                raise SystemExit(f"Video task failed with status {status}. See {result_path}")
            time.sleep(args.poll_interval)
        else:
            raise SystemExit(f"Timed out waiting for video task {task_id}. See {result_path}")
    else:
        write_json(result_path, final_response)

    if not video_url:
        raise SystemExit(f"No video URL found in final response. See {result_path}")

    download_file(video_url, video_path)
    print(video_path.resolve())
    print(result_path.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(130)
