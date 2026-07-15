#!/usr/bin/env python3
"""Create a one-shot spatial photo preview with explicit depth provenance."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import create_spatial_photo_depth_viewer as mesh_viewer  # noqa: E402
import create_spatial_photo_viewer as displacement_viewer  # noqa: E402
import infer_depth_anything_v2  # noqa: E402
import stabilize_depth_map  # noqa: E402


REAL_BACKENDS = ("depth-anything-v2-small", "apple-depth-pro")


def _copy_stable_depth(source: Path, destination: Path, size: tuple[int, int]) -> Path:
    with Image.open(source) as depth:
        converted = depth.convert("L")
        if converted.size != size:
            converted = converted.resize(size, Image.Resampling.BICUBIC)
        destination.parent.mkdir(parents=True, exist_ok=True)
        converted.save(destination)
    return destination


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("image", type=Path, help="Source RGB image; it is never regenerated.")
    depth_inputs = result.add_mutually_exclusive_group()
    depth_inputs.add_argument("--depth", type=Path, help="Supplied stable depth map; skips inference.")
    depth_inputs.add_argument("--raw-depth", type=Path, help="Supplied raw model depth to stabilize.")
    result.add_argument(
        "--depth-backend",
        choices=(*REAL_BACKENDS, "heuristic"),
        default="depth-anything-v2-small",
        help="Real Depth Anything V2 is default. Heuristic is explicit fallback only.",
    )
    result.add_argument("--model-id", default=infer_depth_anything_v2.DEFAULT_MODEL)
    result.add_argument("--cache-dir", type=Path, help="Optional Hugging Face model cache directory.")
    result.add_argument("--preset", choices=("immersive", "v18", "legacy"), default="immersive")
    result.add_argument("--spatial-mode", choices=("mesh", "displacement"), default="mesh")
    result.add_argument("--output", type=Path)
    result.add_argument("--out-dir", type=Path)
    result.add_argument("--raw-depth-output", type=Path)
    result.add_argument("--stable-depth-output", type=Path)
    result.add_argument("--grid", type=int, default=150)
    result.add_argument("--strength", type=float, default=1.0, help="Legacy displacement strength.")
    result.add_argument("--depth-scale", type=float, default=1.80)
    result.add_argument("--motion", type=float, default=1.40)
    result.add_argument("--perspective", type=float, default=1.15)
    result.add_argument("--auto-x", type=float, default=0.42)
    result.add_argument("--auto-y", type=float, default=0.22)
    result.add_argument("--blur", choices=("depth", "none"), default="depth")
    result.add_argument("--blur-near", type=float, default=0.14)
    result.add_argument("--blur-far", type=float, default=0.30)
    result.add_argument("--blur-radius", type=float, default=2.25)
    result.add_argument("--blur-strength", type=float, default=0.52)
    result.add_argument("--interaction", choices=("mixed", "pointer", "auto"), default="mixed")
    return result


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    image = args.image.expanduser().resolve()
    if not image.is_file():
        raise FileNotFoundError(f"source image not found: {image}")
    out_dir = args.out_dir.expanduser().resolve() if args.out_dir else image.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    output = (
        args.output.expanduser().resolve()
        if args.output
        else out_dir / f"{image.stem}-spatial-v18.html"
    )
    raw_output = (
        args.raw_depth_output.expanduser().resolve()
        if args.raw_depth_output
        else out_dir / f"{image.stem}-{args.depth_backend}-raw.png"
    )
    stable_output = (
        args.stable_depth_output.expanduser().resolve()
        if args.stable_depth_output
        else out_dir / f"{image.stem}-depth-stable.png"
    )
    with Image.open(image) as rgb:
        size = rgb.size

    raw_result: Optional[Path] = None
    if args.depth:
        source_depth = args.depth.expanduser().resolve()
        stable = _copy_stable_depth(source_depth, stable_output, size)
        provenance = "supplied-stable-depth"
    else:
        if args.raw_depth:
            raw_result = args.raw_depth.expanduser().resolve()
            provenance = "supplied-raw-depth"
        elif args.depth_backend == "heuristic":
            displacement_viewer.save_depth_map(image, raw_output)
            raw_result = raw_output
            provenance = "heuristic-fallback"
        else:
            raw_result = infer_depth_anything_v2.infer_depth(
                image,
                raw_output,
                backend=args.depth_backend,
                model_id=args.model_id,
                cache_dir=args.cache_dir.expanduser().resolve() if args.cache_dir else None,
            )
            provenance = args.depth_backend
        stable = stabilize_depth_map.stabilize_depth(raw_result, stable_output, size=size)

    if args.spatial_mode == "displacement":
        output.write_text(
            displacement_viewer.build_html(
                displacement_viewer.image_to_data_uri(image),
                displacement_viewer.image_to_data_uri(stable),
                f"{image.stem} spatial displacement preview ({provenance})",
                strength=args.strength,
            ),
            encoding="utf-8",
        )
    else:
        options = mesh_viewer.ViewerOptions(
            depth_scale=args.depth_scale,
            motion=args.motion,
            perspective=args.perspective,
            auto_x=args.auto_x,
            auto_y=args.auto_y,
            blur_near=args.blur_near,
            blur_far=args.blur_far,
            blur_radius=args.blur_radius,
            blur_strength=args.blur_strength,
            blur=args.blur,
            interaction=args.interaction,
            provenance=provenance,
        )
        mesh_viewer.write_viewer(image, stable, output, args.grid, options)

    result = {
        "source": str(image),
        "raw_depth": str(raw_result) if raw_result else None,
        "stable_depth": str(stable),
        "html": str(output),
        "depth_provenance": provenance,
        "preset": "immersive-v18" if args.preset in {"immersive", "v18"} else "legacy-explicit",
        "spatial_mode": args.spatial_mode,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Spatial preview failed: {error}", file=sys.stderr)
        raise SystemExit(1)
