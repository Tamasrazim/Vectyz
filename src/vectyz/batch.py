"""Memory-bounded batch conversion for raster directories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .engine import vectorize_image
from .models import VectorizerConfig

RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
VECTOR_EXTENSIONS = {".svg", ".pdf", ".eps"}


def vectorize_directory(
    input_dir: str | Path,
    output_dir: str | Path,
    config: VectorizerConfig | None = None,
    output_format: str = "svg",
    recursive: bool = False,
) -> dict[str, Any]:
    """Vectorize every supported raster image in a directory, one file at a time.

    Processing is intentionally sequential so peak memory stays predictable.
    Relative folder structure is retained when recursive mode is enabled.
    A JSON report is written even when individual files fail.
    """
    source_root = Path(input_dir).expanduser().resolve()
    destination_root = Path(output_dir).expanduser().resolve()
    extension = output_format.lower().lstrip(".")
    if extension not in {item.lstrip(".") for item in VECTOR_EXTENSIONS}:
        raise ValueError("output_format must be svg, pdf or eps")
    if not source_root.exists() or not source_root.is_dir():
        raise ValueError(f"Input directory does not exist or is not a directory: {source_root}")
    if source_root == destination_root:
        raise ValueError("Input and output directories must be different")

    iterator = source_root.rglob("*") if recursive else source_root.iterdir()
    sources = sorted(
        (
            path
            for path in iterator
            if path.is_file()
            and path.suffix.lower() in RASTER_EXTENSIONS
            and not (
                destination_root.is_relative_to(source_root)
                and path.is_relative_to(destination_root)
            )
        ),
        key=lambda path: path.relative_to(source_root).as_posix().casefold(),
    )
    if not sources:
        raise ValueError(f"No supported raster images found in: {source_root}")

    destination_root.mkdir(parents=True, exist_ok=True)
    settings = config or VectorizerConfig()
    results: list[dict[str, Any]] = []

    for source in sources:
        relative = source.relative_to(source_root)
        destination = (destination_root / relative).with_suffix(f".{extension}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            converted = vectorize_image(source, destination, settings)
            results.append(
                {
                    "input": relative.as_posix(),
                    "output": destination.relative_to(destination_root).as_posix(),
                    "status": "success",
                    "width": converted.stats.width,
                    "height": converted.stats.height,
                    "colors_used": converted.stats.colors_used,
                    "paths": converted.stats.paths,
                    "components_removed": converted.stats.components_removed,
                    "elapsed_ms": converted.stats.elapsed_ms,
                }
            )
        except (OSError, ValueError, RuntimeError) as exc:
            results.append(
                {
                    "input": relative.as_posix(),
                    "output": destination.relative_to(destination_root).as_posix(),
                    "status": "failed",
                    "error": str(exc),
                }
            )

    succeeded = sum(item["status"] == "success" for item in results)
    failed = len(results) - succeeded
    report: dict[str, Any] = {
        "engine": "Vectyz",
        "version": "0.1.0",
        "input_directory": str(source_root),
        "output_directory": str(destination_root),
        "output_format": extension,
        "recursive": recursive,
        "settings": {
            "colors": settings.colors,
            "detail": settings.detail,
            "min_area": settings.min_area,
            "curve": settings.curve,
            "corner_angle": settings.corner_angle,
            "alpha_bins": settings.alpha_bins,
            "transparent_threshold": settings.transparent_threshold,
            "quantizer": settings.quantizer,
        },
        "total": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "files": results,
    }
    (destination_root / "vectyz-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report
