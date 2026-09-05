#!/usr/bin/env python3
"""Infer real monocular depth with Depth Anything V2 Small or optional Depth Pro."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image


DEFAULT_MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
REQUIRED_MODEL_FILES = ("config.json", "preprocessor_config.json", "model.safetensors")


def find_cached_snapshot(
    model_id: str, cache_dir: Optional[Path] = None
) -> Optional[Path]:
    """Return a complete cached snapshot without making a network request."""
    try:
        from huggingface_hub import snapshot_download

        snapshot = Path(
            snapshot_download(
                repo_id=model_id,
                cache_dir=str(cache_dir) if cache_dir else None,
                local_files_only=True,
            )
        )
    except Exception:
        return None
    if all((snapshot / name).is_file() for name in REQUIRED_MODEL_FILES):
        return snapshot
    return None


def _normalize_depth(values: np.ndarray, invert: bool = False) -> Image.Image:
    values = np.asarray(values, dtype=np.float32)
    finite = np.isfinite(values)
    if not finite.any():
        raise RuntimeError("depth model returned no finite values")
    low, high = np.percentile(values[finite], [0.5, 99.5])
    if high <= low:
        raise RuntimeError("depth model returned a constant depth map")
    values = np.where(finite, values, low)
    normalized = np.clip((values - low) / (high - low), 0.0, 1.0)
    if invert:
        normalized = 1.0 - normalized
    return Image.fromarray(np.uint16(np.round(normalized * 65535)))


def infer_depth_anything_v2(
    image_path: Path,
    output_path: Path,
    model_id: str = DEFAULT_MODEL,
    cache_dir: Optional[Path] = None,
) -> Path:
    try:
        import torch
        import torch.nn.functional as functional
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation
    except ImportError as error:
        raise RuntimeError(
            "Depth Anything V2 dependencies are unavailable. Run this script through "
            "scripts/run_with_deps.py; no heuristic fallback was used."
        ) from error

    image = Image.open(image_path).convert("RGB")
    cache = str(cache_dir) if cache_dir else None
    cached_snapshot = find_cached_snapshot(model_id, cache_dir)
    model_source = str(cached_snapshot) if cached_snapshot else model_id
    processor = AutoImageProcessor.from_pretrained(
        model_source,
        cache_dir=cache,
        local_files_only=bool(cached_snapshot),
        use_fast=False,
    )
    model = AutoModelForDepthEstimation.from_pretrained(
        model_source, cache_dir=cache, local_files_only=bool(cached_snapshot)
    )
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model.to(device).eval()
    inputs = {key: value.to(device) for key, value in processor(images=image, return_tensors="pt").items()}
    with torch.inference_mode():
        predicted = model(**inputs).predicted_depth
    resized = functional.interpolate(
        predicted.unsqueeze(1), size=(image.height, image.width), mode="bicubic", align_corners=False
    ).squeeze().detach().float().cpu().numpy()
    depth = _normalize_depth(resized, invert=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    depth.save(output_path)
    return output_path


def infer_apple_depth_pro(image_path: Path, output_path: Path) -> Path:
    try:
        import depth_pro
    except ImportError as error:
        raise RuntimeError(
            "Apple Depth Pro is optional and is not installed in this skill environment. "
            "Install it explicitly or use the default depth-anything-v2-small backend; "
            "no heuristic fallback was used."
        ) from error
    model, transform = depth_pro.create_model_and_transforms()
    model.eval()
    image, _, focal_px = depth_pro.load_rgb(image_path)
    prediction = model.infer(transform(image), f_px=focal_px)
    metric_depth = prediction["depth"].detach().float().cpu().numpy()
    depth = _normalize_depth(metric_depth, invert=True)
    with Image.open(image_path) as rgb:
        depth = Image.fromarray(np.uint16(np.clip(np.asarray(
            depth.convert("F").resize(rgb.size, Image.Resampling.BICUBIC)
        ), 0, 65535)))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    depth.save(output_path)
    return output_path


def infer_depth(
    image_path: Path,
    output_path: Path,
    backend: str = "depth-anything-v2-small",
    model_id: str = DEFAULT_MODEL,
    cache_dir: Optional[Path] = None,
) -> Path:
    if backend == "depth-anything-v2-small":
        return infer_depth_anything_v2(image_path, output_path, model_id, cache_dir)
    if backend == "apple-depth-pro":
        return infer_apple_depth_pro(image_path, output_path)
    raise ValueError(f"unsupported real depth backend: {backend}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--backend",
        choices=("depth-anything-v2-small", "apple-depth-pro"),
        default="depth-anything-v2-small",
    )
    parser.add_argument("--model-id", default=DEFAULT_MODEL)
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    print(
        infer_depth(
            args.image.resolve(),
            args.output.resolve(),
            backend=args.backend,
            model_id=args.model_id,
            cache_dir=args.cache_dir.expanduser().resolve() if args.cache_dir else None,
        )
    )


if __name__ == "__main__":
    main()
