"""Image input and palette quantization."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import numpy as np
from PIL import Image, ImageOps


ImageSource = str | Path | bytes | bytearray | BinaryIO | Image.Image


def load_rgba(source: ImageSource) -> Image.Image:
    """Load an image, apply EXIF orientation and return an independent RGBA image."""
    if isinstance(source, Image.Image):
        image = source.copy()
    elif isinstance(source, (bytes, bytearray)):
        image = Image.open(BytesIO(source))
    else:
        image = Image.open(source)

    try:
        return ImageOps.exif_transpose(image).convert("RGBA").copy()
    finally:
        image.close()


def quantize_rgba(
    image: Image.Image, colors: int, transparent_threshold: int
) -> tuple[np.ndarray, np.ndarray, dict[int, tuple[int, int, int]]]:
    """Return palette indices, alpha channel and visible palette colors.

    Fully/near-transparent pixels are excluded from palette-frequency discovery so
    hidden RGB values in transparent pixels do not pollute the visible palette.
    """
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    alpha = rgba[:, :, 3].copy()
    rgb_image = Image.fromarray(rgba[:, :, :3], mode="RGB")
    try:
        quantized = rgb_image.quantize(
            colors=colors,
            method=Image.Quantize.MEDIANCUT,
            dither=Image.Dither.NONE,
        )
        indices = np.asarray(quantized, dtype=np.uint8).copy()
        raw_palette = quantized.getpalette()
    finally:
        rgb_image.close()

    visible = alpha > transparent_threshold
    visible_indices, counts = np.unique(indices[visible], return_counts=True)
    palette: dict[int, tuple[int, int, int]] = {}
    for palette_index, _count in sorted(
        zip(visible_indices.tolist(), counts.tolist()),
        key=lambda item: (-item[1], item[0]),
    ):
        offset = int(palette_index) * 3
        if raw_palette is None or offset + 2 >= len(raw_palette):
            continue
        palette[int(palette_index)] = (
            int(raw_palette[offset]),
            int(raw_palette[offset + 1]),
            int(raw_palette[offset + 2]),
        )

    quantized.close()
    return indices, alpha, palette
