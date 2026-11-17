"""Public conversion pipeline."""

from __future__ import annotations

import time
from pathlib import Path

from .exporters import build_svg
from .exporters import rasterize_svg as _rasterize_svg
from .exporters import write_vector as _write_vector
from .image import ImageSource, load_rgba, quantize_rgba
from .models import VectorizationResult, VectorizationStats, VectorizerConfig
from .tracing import trace_palette_layer


def vectorize_image(
    source: ImageSource,
    output_path: str | Path | None = None,
    config: VectorizerConfig | None = None,
) -> VectorizationResult:
    """Convert a raster image into editable SVG paths.

    The same result can optionally be written to SVG, PDF or EPS by supplying an
    output path with the corresponding extension.
    """
    started = time.perf_counter()
    settings = config or VectorizerConfig()
    image = load_rgba(source)
    try:
        width, height = image.size
        indices, alpha, palette = quantize_rgba(
            image,
            settings.colors,
            settings.transparent_threshold,
            settings.quantizer,
        )

        vector_paths = []
        components_removed = 0
        for palette_index, color in palette.items():
            for alpha_bin in range(settings.alpha_bins - 1, -1, -1):
                traced, removed = trace_palette_layer(
                    indices,
                    alpha,
                    palette_index,
                    color,
                    alpha_bin,
                    settings,
                )
                vector_paths.extend(traced)
                components_removed += removed

        svg = build_svg(width, height, vector_paths)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        result = VectorizationResult(
            svg=svg,
            stats=VectorizationStats(
                width=width,
                height=height,
                colors_used=len(palette),
                paths=len(vector_paths),
                components_removed=components_removed,
                elapsed_ms=round(elapsed_ms, 3),
            ),
            vector_paths=tuple(vector_paths),
        )
    finally:
        image.close()

    if output_path is not None:
        _write_vector(result, output_path)
    return result


def write_vector(result: VectorizationResult, output_path: str | Path) -> None:
    """Write an existing vectorization result to SVG, PDF or EPS."""
    _write_vector(result, output_path)


def rasterize_svg(
    source: str | Path,
    output_path: str | Path,
    width: int | None = None,
    height: int | None = None,
    background: str | None = None,
) -> None:
    """Render an SVG file into a raster image."""
    _rasterize_svg(source, output_path, width, height, background)
