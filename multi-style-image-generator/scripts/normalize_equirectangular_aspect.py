#!/usr/bin/env python3
"""Normalize a panorama-like image to a 2:1 equirectangular canvas."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageFilter


def default_out_path(image_path: Path) -> Path:
    return image_path.with_name(f"{image_path.stem}-2x1.png")


def is_close_to_2x1(width: int, height: int, tolerance: float) -> bool:
    if height <= 0:
        return False
    return abs((width / height) - 2.0) <= tolerance


def normalize_stretch(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    return image.resize((target_width, target_height), Image.Resampling.LANCZOS)


def normalize_crop(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    width, height = image.size
    source_aspect = width / height
    target_aspect = target_width / target_height
    if source_aspect > target_aspect:
        crop_width = round(height * target_aspect)
        left = (width - crop_width) // 2
        image = image.crop((left, 0, left + crop_width, height))
    else:
        crop_height = round(width / target_aspect)
        top = (height - crop_height) // 2
        image = image.crop((0, top, width, top + crop_height))
    return image.resize((target_width, target_height), Image.Resampling.LANCZOS)


def normalize_pad(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    width, height = image.size
    scale = min(target_width / width, target_height / height)
    fitted_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    fitted = image.resize(fitted_size, Image.Resampling.LANCZOS)

    background = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(radius=max(8, target_height // 80)))
    left = (target_width - fitted.width) // 2
    top = (target_height - fitted.height) // 2
    background.paste(fitted, (left, top))
    return background


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a 2:1 equirectangular PNG from an input image.")
    parser.add_argument("image", type=Path, help="Input image path.")
    parser.add_argument("--out", type=Path, help="Output PNG path. Defaults to <image>-2x1.png.")
    parser.add_argument(
        "--mode",
        choices=("stretch", "crop", "pad"),
        default="stretch",
        help="How to convert non-2:1 images. stretch preserves all content and fills the canvas.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.02,
        help="Aspect ratio tolerance for treating an image as already 2:1.",
    )
    parser.add_argument(
        "--copy-if-2x1",
        action="store_true",
        help="Still write a sibling output when the input is already close to 2:1.",
    )
    args = parser.parse_args()

    image_path = args.image.expanduser().resolve()
    if not image_path.exists():
        raise SystemExit(f"Image not found: {image_path}")

    out_path = args.out.expanduser().resolve() if args.out else default_out_path(image_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as opened:
        image = opened.convert("RGB")

    width, height = image.size
    target_width = height * 2
    target_height = height

    if is_close_to_2x1(width, height, args.tolerance):
        if args.copy_if_2x1 or out_path.resolve() != image_path:
            image.save(out_path, format="PNG")
            print(out_path)
        else:
            print(image_path)
        return 0

    if args.mode == "stretch":
        normalized = normalize_stretch(image, target_width, target_height)
    elif args.mode == "crop":
        normalized = normalize_crop(image, target_width, target_height)
    else:
        normalized = normalize_pad(image, target_width, target_height)

    normalized.save(out_path, format="PNG")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
