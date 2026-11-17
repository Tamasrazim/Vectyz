"""Vectyz command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .batch import vectorize_directory
from .engine import rasterize_svg, vectorize_image
from .models import VectorizerConfig


def _add_vectorizer_options(command: argparse.ArgumentParser) -> None:
    command.add_argument("--colors", type=int, default=16, help="Maximum palette colors (2–256).")
    command.add_argument("--detail", type=float, default=1.0, help="Contour simplification amount.")
    command.add_argument(
        "--min-area", type=float, default=2.0,
        help="Minimum component area in pixels.",
    )
    command.add_argument(
        "--curve", choices=("smooth", "polygon"), default="smooth",
        help="Cubic Bézier fitting or polygon-only paths.",
    )
    command.add_argument("--alpha-bins", type=int, default=4, help="Opacity bands (1–16).")
    command.add_argument(
        "--transparent-threshold", type=int, default=4,
        help="Alpha values at or below this value are ignored.",
    )
    command.add_argument(
        "--corner-angle", type=float, default=42.0,
        help="Turning angle in degrees above which a vertex is kept as a corner.",
    )


def _config_from_args(args: argparse.Namespace) -> VectorizerConfig:
    return VectorizerConfig(
        colors=args.colors,
        detail=args.detail,
        min_area=args.min_area,
        curve=args.curve,
        corner_angle=args.corner_angle,
        alpha_bins=args.alpha_bins,
        transparent_threshold=args.transparent_threshold,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vectyz",
        description="Convert raster images to editable vectors and rasterize SVG artwork.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    vector = subparsers.add_parser(
        "vectorize", aliases=["trace"], help="Trace a raster image into vector paths."
    )
    vector.add_argument("input", help="Raster input image.")
    vector.add_argument("output", help="Output .svg, .pdf or .eps file.")
    _add_vectorizer_options(vector)

    batch = subparsers.add_parser(
        "batch", help="Vectorize every supported raster image in a folder."
    )
    batch.add_argument("input_dir", help="Folder containing raster images.")
    batch.add_argument("output_dir", help="Folder for vector outputs and JSON report.")
    batch.add_argument(
        "--format", choices=("svg", "pdf", "eps"), default="svg",
        help="Vector output format (default: svg).",
    )
    batch.add_argument(
        "--recursive", action="store_true",
        help="Include images in nested folders and preserve their folder structure.",
    )
    _add_vectorizer_options(batch)

    raster = subparsers.add_parser(
        "rasterize", help="Rasterize an SVG file into a bitmap image."
    )
    raster.add_argument("input", help="SVG input file.")
    raster.add_argument("output", help="Output .png, .jpg, .webp, .tif or .bmp file.")
    raster.add_argument("--width", type=int, help="Output width in pixels.")
    raster.add_argument("--height", type=int, help="Output height in pixels.")
    raster.add_argument(
        "--background", help="Optional background color, for example '#ffffff'."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command in {"vectorize", "trace"}:
            result = vectorize_image(args.input, args.output, _config_from_args(args))
            print(json.dumps(asdict(result.stats), indent=2))
            return 0

        if args.command == "batch":
            report = vectorize_directory(
                args.input_dir,
                args.output_dir,
                config=_config_from_args(args),
                output_format=args.format,
                recursive=args.recursive,
            )
            print(json.dumps(report, indent=2))
            return 1 if report["failed"] else 0

        if args.command == "rasterize":
            rasterize_svg(
                args.input,
                args.output,
                width=args.width,
                height=args.height,
                background=args.background,
            )
            print(f"Rasterized: {args.output}")
            return 0

    except (OSError, ValueError, RuntimeError) as exc:
        print(f"vectyz: error: {exc}", file=sys.stderr)
        return 1

    parser.error("unknown command")
    return 2
