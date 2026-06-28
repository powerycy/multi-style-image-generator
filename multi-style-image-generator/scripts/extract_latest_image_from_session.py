#!/usr/bin/env python3
"""Extract the latest image payload from a Codex session JSONL log."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


DATA_URI_RE = re.compile(r"data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+)")
BASE64_IMAGE_PREFIXES = ("iVBORw0KGgo", "/9j/", "UklGR", "R0lGOD")
MIN_BARE_BASE64_CHARS = 200


def default_sessions_root() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"


def latest_session(root: Path) -> Path:
    sessions = [path for path in root.rglob("*.jsonl") if path.is_file()]
    if not sessions:
        raise SystemExit(f"No Codex session JSONL files found under {root}")
    return max(sessions, key=lambda path: path.stat().st_mtime)


def walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(walk_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(walk_strings(item))
        return strings
    return []


def image_extension(mime_subtype: str, data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"
    raise ValueError("decoded data does not look like a supported image")


def candidate_from_encoded(
    encoded: str,
    mime_subtype: str,
    line_number: int,
    timestamp: str | None,
    payload_type: str | None,
    source: str,
) -> dict[str, Any] | None:
    compact = re.sub(r"\s+", "", encoded)
    try:
        image_bytes = base64.b64decode(compact, validate=True)
        extension = image_extension(mime_subtype, image_bytes)
    except Exception:
        return None
    return {
        "line_number": line_number,
        "timestamp": timestamp,
        "payload_type": payload_type,
        "extension": extension,
        "bytes": image_bytes,
        "source": source,
    }


def looks_like_bare_image_base64(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < MIN_BARE_BASE64_CHARS:
        return False
    return any(stripped.startswith(prefix) for prefix in BASE64_IMAGE_PREFIXES)


def safe_timestamp(raw: str | None) -> str:
    if not raw:
        return datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%Y%m%d-%H%M%S")
    except ValueError:
        return datetime.now().strftime("%Y%m%d-%H%M%S")


def extract_candidates(session_path: Path, include_tool_outputs: bool) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    with session_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if "data:image/" not in line and not any(prefix in line for prefix in BASE64_IMAGE_PREFIXES):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            payload = record.get("payload", {})
            payload_type = payload.get("type")
            if not include_tool_outputs and payload_type in {"function_call", "function_call_output"}:
                continue

            for text in walk_strings(record):
                for match in DATA_URI_RE.finditer(text):
                    candidate = candidate_from_encoded(
                        encoded=match.group(2),
                        mime_subtype=match.group(1),
                        line_number=line_number,
                        timestamp=record.get("timestamp"),
                        payload_type=payload_type,
                        source="data-uri",
                    )
                    if candidate:
                        candidates.append(candidate)
                if looks_like_bare_image_base64(text):
                    candidate = candidate_from_encoded(
                        encoded=text,
                        mime_subtype="unknown",
                        line_number=line_number,
                        timestamp=record.get("timestamp"),
                        payload_type=payload_type,
                        source="bare-base64",
                    )
                    if candidate:
                        candidates.append(candidate)
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract the latest inline Codex image to a local file.")
    parser.add_argument("--session", type=Path, help="Codex session JSONL path. Defaults to latest session.")
    parser.add_argument("--sessions-root", type=Path, default=default_sessions_root(), help="Root containing Codex session JSONL files.")
    parser.add_argument("--out-dir", type=Path, default=Path("output/imagegen"), help="Directory for the extracted image.")
    parser.add_argument("--name", default="latest-codex-image", help="Base filename without extension.")
    parser.add_argument(
        "--include-tool-outputs",
        action="store_true",
        help="Also scan tool call and tool output records.",
    )
    args = parser.parse_args()

    session_path = args.session.expanduser().resolve() if args.session else latest_session(args.sessions_root.expanduser())
    candidates = extract_candidates(session_path, args.include_tool_outputs)
    if not candidates:
        raise SystemExit(f"No inline image payloads found in {session_path}")

    selected = candidates[-1]
    out_dir = args.out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = safe_timestamp(selected["timestamp"])
    out_path = out_dir / f"{args.name}-{timestamp}.{selected['extension']}"
    suffix = 2
    while out_path.exists():
        out_path = out_dir / f"{args.name}-{timestamp}-{suffix}.{selected['extension']}"
        suffix += 1
    out_path.write_bytes(selected["bytes"])
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
