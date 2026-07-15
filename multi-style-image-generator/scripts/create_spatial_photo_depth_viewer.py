#!/usr/bin/env python3
"""Build the accepted v18 single-mesh spatial-photo viewer."""

from __future__ import annotations

import argparse
import base64
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "spatial-v18-template.html"


@dataclass(frozen=True)
class ViewerOptions:
    depth_scale: float = 1.80
    motion: float = 1.40
    perspective: float = 1.15
    auto_x: float = 0.42
    auto_y: float = 0.22
    blur_near: float = 0.14
    blur_far: float = 0.30
    blur_radius: float = 2.25
    blur_strength: float = 0.52
    blur: str = "depth"
    interaction: str = "mixed"
    provenance: str = "supplied-depth"


def data_uri(path: Path) -> str:
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _number(value: float) -> str:
    return f"{value:.2f}"


def build_document(
    image_path: Path,
    depth_path: Path,
    grid: int = 150,
    options: ViewerOptions = ViewerOptions(),
) -> str:
    with Image.open(image_path) as image:
        width, height = image.size
    with Image.open(depth_path) as depth:
        if depth.size != (width, height):
            raise ValueError(
                f"depth dimensions {depth.size} do not match RGB dimensions {(width, height)}"
            )

    aspect = width / height
    config = {
        "image": data_uri(image_path),
        "depth": data_uri(depth_path),
        "width": width,
        "height": height,
        "cols": grid,
        "rows": max(40, round(grid / aspect)),
        "depthProvenance": options.provenance,
        "interaction": options.interaction,
    }
    document = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "__CONFIG__": json.dumps(config, ensure_ascii=False),
        "1.77683316": f"{aspect:.8f}",
        "depthScale: 1.80": f"depthScale: {_number(options.depth_scale)}",
        "motion: 1.40": f"motion: {_number(options.motion)}",
        "perspective: 1.15": f"perspective: {_number(options.perspective)}",
        "Math.sin(t * 0.42) * 0.42": f"Math.sin(t * 0.42) * {_number(options.auto_x)}",
        "Math.cos(t * 0.33) * 0.22": f"Math.cos(t * 0.33) * {_number(options.auto_y)}",
        "smoothstep(0.14, 0.30, depthValue)": (
            f"smoothstep({_number(options.blur_near)}, {_number(options.blur_far)}, depthValue)"
        ),
        "uTexelSize * 2.25": f"uTexelSize * {_number(options.blur_radius)}",
        "farMask * 0.52": f"farMask * {_number(options.blur_strength)}",
    }
    for old, new in replacements.items():
        if old not in document:
            raise ValueError(f"v18 template contract missing: {old}")
        document = document.replace(old, new)
    if options.blur == "none":
        document = document.replace(
            f"float farMask = 1.0 - smoothstep({_number(options.blur_near)}, {_number(options.blur_far)}, depthValue);",
            "float farMask = 0.0;",
        )
    if options.interaction == "auto":
        document = document.replace("canvas.addEventListener('pointermove'", "false && canvas.addEventListener('pointermove'")
        document = document.replace("canvas.addEventListener('pointerdown'", "false && canvas.addEventListener('pointerdown'")
        document = document.replace("if (window.DeviceOrientationEvent", "if (false && window.DeviceOrientationEvent")
    elif options.interaction == "pointer":
        document = document.replace("if (window.DeviceOrientationEvent", "if (false && window.DeviceOrientationEvent")
    return document


def write_viewer(
    image_path: Path,
    depth_path: Path,
    output_path: Path,
    grid: int = 150,
    options: ViewerOptions = ViewerOptions(),
) -> None:
    document = build_document(image_path, depth_path, grid, options)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("depth", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--grid", type=int, default=150)
    parser.add_argument("--depth-scale", type=float, default=1.80)
    parser.add_argument("--motion", type=float, default=1.40)
    parser.add_argument("--perspective", type=float, default=1.15)
    parser.add_argument("--auto-x", type=float, default=0.42)
    parser.add_argument("--auto-y", type=float, default=0.22)
    parser.add_argument("--blur-near", type=float, default=0.14)
    parser.add_argument("--blur-far", type=float, default=0.30)
    parser.add_argument("--blur-radius", type=float, default=2.25)
    parser.add_argument("--blur-strength", type=float, default=0.52)
    parser.add_argument("--blur", choices=("depth", "none"), default="depth")
    parser.add_argument("--interaction", choices=("mixed", "pointer", "auto"), default="mixed")
    parser.add_argument("--provenance", default="supplied-depth")
    args = parser.parse_args()
    options = ViewerOptions(
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
        provenance=args.provenance,
    )
    write_viewer(args.image.resolve(), args.depth.resolve(), args.output.resolve(), args.grid, options)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
