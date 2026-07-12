#!/usr/bin/env python3
"""Create one of the supported spatial photo preview HTML modes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import create_spatial_photo_depth_viewer as mesh_viewer  # noqa: E402
import create_spatial_photo_viewer as displacement_viewer  # noqa: E402


def default_output(image: Path, mode: str, out_dir: Path) -> Path:
    suffix = "spatial-displacement-viewer" if mode == "displacement" else "spatial-mesh-viewer"
    return out_dir / f"{image.stem}-{suffix}.html"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a spatial photo preview HTML.")
    parser.add_argument("image", type=Path, help="Source RGB image.")
    parser.add_argument("--depth", type=Path, help="Optional depth map. If omitted, a heuristic depth map is generated.")
    parser.add_argument(
        "--spatial-mode",
        choices=("displacement", "mesh"),
        default="displacement",
        help="displacement = shader parallax, mesh = depth mesh perspective.",
    )
    parser.add_argument("--output", type=Path, help="Output HTML path.")
    parser.add_argument("--out-dir", type=Path, help="Output directory when --output is omitted.")
    parser.add_argument("--strength", type=float, default=1.0, help="Displacement-mode parallax strength.")
    parser.add_argument("--grid", type=int, default=150, help="Mesh-mode grid columns.")
    args = parser.parse_args()

    image = args.image.expanduser().resolve()
    out_dir = (args.out_dir.expanduser().resolve() if args.out_dir else image.parent)
    out_dir.mkdir(parents=True, exist_ok=True)
    output = args.output.expanduser().resolve() if args.output else default_output(image, args.spatial_mode, out_dir)

    depth = args.depth.expanduser().resolve() if args.depth else out_dir / f"{image.stem}-spatial-depth.png"
    if not args.depth:
        displacement_viewer.save_depth_map(image, depth)

    if args.spatial_mode == "displacement":
        output.write_text(
            displacement_viewer.build_html(
                displacement_viewer.image_to_data_uri(image),
                displacement_viewer.image_to_data_uri(depth),
                f"{image.stem} spatial displacement preview",
                strength=args.strength,
            ),
            encoding="utf-8",
        )
    else:
        mesh_viewer.write_viewer(image, depth, output, args.grid)

    print(depth)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
