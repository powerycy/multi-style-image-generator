#!/usr/bin/env python3
"""Normalize and gently denoise a raw depth map for stable spatial rendering."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter


def stabilize_depth(
    raw_path: Path,
    output_path: Path,
    size: Optional[Tuple[int, int]] = None,
    low_percentile: float = 1.0,
    high_percentile: float = 99.0,
    smooth_radius: float = 1.15,
    smooth_mix: float = 0.22,
) -> Path:
    with Image.open(raw_path) as source:
        image = source.convert("L")
    if size and image.size != size:
        image = image.resize(size, Image.Resampling.BICUBIC)

    values = np.asarray(image, dtype=np.float32)
    low, high = np.percentile(values, [low_percentile, high_percentile])
    if high <= low:
        raise ValueError("raw depth map has no usable dynamic range")
    normalized = np.clip((values - low) / (high - low), 0.0, 1.0)
    base = Image.fromarray(np.uint8(np.round(normalized * 255)), mode="L")
    smooth = base.filter(ImageFilter.GaussianBlur(radius=smooth_radius))
    stable = Image.blend(base, smooth, smooth_mix)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stable.save(output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_depth", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--low-percentile", type=float, default=1.0)
    parser.add_argument("--high-percentile", type=float, default=99.0)
    parser.add_argument("--smooth-radius", type=float, default=1.15)
    parser.add_argument("--smooth-mix", type=float, default=0.22)
    args = parser.parse_args()
    if (args.width is None) != (args.height is None):
        parser.error("--width and --height must be used together")
    size = (args.width, args.height) if args.width else None
    print(
        stabilize_depth(
            args.raw_depth.resolve(),
            args.output.resolve(),
            size=size,
            low_percentile=args.low_percentile,
            high_percentile=args.high_percentile,
            smooth_radius=args.smooth_radius,
            smooth_mix=args.smooth_mix,
        )
    )


if __name__ == "__main__":
    main()
