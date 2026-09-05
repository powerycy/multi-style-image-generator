#!/usr/bin/env python3
"""Normalize and gently denoise a raw depth map for stable spatial rendering."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from depth_geometry import read_depth, resize_depth, save_depth


def stabilize_depth(
    raw_path: Path,
    output_path: Path,
    size: Optional[Tuple[int, int]] = None,
    low_percentile: float = 1.0,
    high_percentile: float = 99.0,
    smooth_radius: float = 1.15,
    smooth_mix: float = 0.22,
) -> Path:
    values = read_depth(raw_path)
    if not 0 <= smooth_mix <= 1 or not 0 <= smooth_radius <= 4:
        raise ValueError("smooth mix must be 0..1 and radius 0..4")
    if not 0 <= low_percentile < high_percentile <= 100:
        raise ValueError("invalid normalization percentiles")
    low, high = np.percentile(values, [low_percentile, high_percentile])
    if high <= low:
        raise ValueError("raw depth map has no usable dynamic range")
    normalized = np.clip((values - low) / (high - low), 0.0, 1.0)
    # Bilateral filter: only similar depths contribute across an edge.
    radius = int(np.ceil(smooth_radius * 2))
    weighted = np.zeros_like(normalized)
    weights = np.zeros_like(normalized)
    padded = np.pad(normalized, radius, mode="edge")
    height, width = normalized.shape
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            neighbor = padded[radius+dy:radius+dy+height, radius+dx:radius+dx+width]
            spatial = np.exp(-(dx*dx + dy*dy) / (2 * max(smooth_radius, 0.01)**2))
            weight = spatial * np.exp(-((neighbor - normalized) / 0.035)**2 / 2)
            weighted += weight * neighbor
            weights += weight
    stable = normalized * (1 - smooth_mix) + weighted / weights * smooth_mix
    if size and stable.shape[::-1] != size:
        stable = resize_depth(stable, size)
    save_depth(stable, output_path)
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
