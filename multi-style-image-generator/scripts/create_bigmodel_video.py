#!/usr/bin/env python3
"""Generate a video with BigModel CogVideoX and download the result."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and download a BigModel CogVideoX video.")
    parser.add_argument("--prompt", required=True, help="Video generation prompt.")
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
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env) or os.environ.get("ZHIPU_API_KEY")
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
    if not api_key:
        raise SystemExit(f"Missing API key. Set {args.api_key_env} or ZHIPU_API_KEY in the environment.")

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
