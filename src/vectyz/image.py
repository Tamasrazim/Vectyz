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
    """Learn a palette from visible pixels and map the full image to that palette."""
    rgba_image = image.convert("RGBA")
    try:
        rgba = np.asarray(rgba_image, dtype=np.uint8)
        alpha = rgba[:, :, 3].copy()
        visible = alpha > transparent_threshold
        if not visible.any():
            return np.zeros(alpha.shape, dtype=np.uint8), alpha, {}

        visible_pixels = rgba[:, :, :3][visible]
        # A deterministic sample bounds palette-learning memory on very large images.
        stride = max(1, len(visible_pixels) // 100_000)
        sample = visible_pixels[::stride]
        sample_image = Image.fromarray(sample.reshape(1, -1, 3))
        rgb_image = Image.fromarray(rgba[:, :, :3])
        palette_source = None
        quantized = None
        try:
            palette_source = sample_image.quantize(
                colors=colors,
                method=Image.Quantize.MEDIANCUT,
                dither=Image.Dither.NONE,
            )
            quantized = rgb_image.quantize(
                palette=palette_source,
                dither=Image.Dither.NONE,
            )
            indices = np.asarray(quantized, dtype=np.uint8).copy()
            raw_palette = palette_source.getpalette()
        finally:
            if quantized is not None:
                quantized.close()
            if palette_source is not None:
                palette_source.close()
            rgb_image.close()
            sample_image.close()

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
        return indices, alpha, palette
    finally:
        rgba_image.close()
