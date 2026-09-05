#!/usr/bin/env python3
"""Preserve 16-bit depth through resampling and embedded geometry."""
import numpy as np
from PIL import Image


def read_depth(path):
    with Image.open(path) as image:
        high_precision = image.mode in ("I", "I;16", "I;16B", "F")
        values = np.asarray(image if high_precision else image.convert("L"), dtype=np.float32)
        scale = 65535.0 if high_precision and image.mode != "F" else (1.0 if image.mode == "F" else 255.0)
    if not np.isfinite(values).all():
        raise ValueError("depth contains non-finite values")
    return np.clip(values / scale, 0, 1)


def resize_depth(values, size):
    # Nearest preserves discontinuities; smoothing belongs before geometry sampling.
    return np.asarray(Image.fromarray(values).resize(size, Image.Resampling.NEAREST), dtype=np.float32)


def save_depth(values, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.round(np.clip(values, 0, 1) * 65535).astype(np.uint16)).save(path)
    return path


def sampled_depth(path, size):
    values = resize_depth(read_depth(path), size)
    return np.round(values.ravel(), 6).tolist()
