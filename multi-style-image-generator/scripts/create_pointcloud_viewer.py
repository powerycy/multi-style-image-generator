#!/usr/bin/env python3
"""Build a self-contained colored point-cloud viewer from RGB and depth images."""

from __future__ import annotations

import argparse
import base64
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image


TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "pointcloud-template.html"


@dataclass(frozen=True)
class ViewerOptions:
    depth_scale: float = 1.25
    point_size: float = 2.1
    focus: float = 0.46
    yaw: float = -0.33
    pitch: float = 0.18
    zoom: float = 2.25
    provenance: str = "supplied-depth"


def data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def build_document(
    image_path: Path,
    depth_path: Path,
    grid: int = 250,
    options: ViewerOptions = ViewerOptions(),
) -> str:
    if grid < 32:
        raise ValueError("point-cloud grid must be at least 32 columns")
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
        "rows": max(24, round(grid / aspect)),
        "depthProvenance": options.provenance,
    }
    defaults = asdict(options)
    defaults.pop("provenance")
    defaults = {
        "depthScale": defaults.pop("depth_scale"),
        "pointSize": defaults.pop("point_size"),
        **defaults,
    }

    document = TEMPLATE.read_text(encoding="utf-8")
    for token in ("__CONFIG__", "__DEFAULTS__"):
        if token not in document:
            raise ValueError(f"point-cloud template contract missing: {token}")
    return document.replace(
        "__CONFIG__", json.dumps(config, ensure_ascii=False)
    ).replace(
        "__DEFAULTS__", json.dumps(defaults, ensure_ascii=False)
    )


def write_viewer(
    image_path: Path,
    depth_path: Path,
    output_path: Path,
    grid: int = 250,
    options: ViewerOptions = ViewerOptions(),
) -> None:
    document = build_document(image_path, depth_path, grid=grid, options=options)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("depth", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--grid", type=int, default=250)
    parser.add_argument("--depth-scale", type=float, default=1.25)
    parser.add_argument("--point-size", type=float, default=2.1)
    parser.add_argument("--focus", type=float, default=0.46)
    parser.add_argument("--yaw", type=float, default=-0.33)
    parser.add_argument("--pitch", type=float, default=0.18)
    parser.add_argument("--zoom", type=float, default=2.25)
    parser.add_argument("--provenance", default="supplied-depth")
    args = parser.parse_args()
    options = ViewerOptions(
        depth_scale=args.depth_scale,
        point_size=args.point_size,
        focus=args.focus,
        yaw=args.yaw,
        pitch=args.pitch,
        zoom=args.zoom,
        provenance=args.provenance,
    )
    write_viewer(
        args.image.expanduser().resolve(),
        args.depth.expanduser().resolve(),
        args.output.expanduser().resolve(),
        grid=args.grid,
        options=options,
    )
    print(args.output.expanduser().resolve())


if __name__ == "__main__":
    main()
