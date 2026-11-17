"""Vectyz command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .engine import rasterize_svg, vectorize_image
from .models import VectorizerConfig


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
    vector.add_argument("--colors", type=int, default=16, help="Maximum palette colors (2–256).")
    vector.add_argument("--detail", type=float, default=1.0, help="Contour simplification amount.")
    vector.add_argument("--min-area", type=float, default=2.0, help="Minimum component area in pixels.")
    vector.add_argument(
        "--curve", choices=("smooth", "polygon"), default="smooth",
        help="Cubic Bézier fitting or polygon-only paths.",
    )
    vector.add_argument("--alpha-bins", type=int, default=4, help="Opacity bands (1–16).")
    vector.add_argument(
        "--transparent-threshold", type=int, default=4,
        help="Alpha values at or below this value are ignored.",
    )
    vector.add_argument(
        "--corner-angle", type=float, default=42.0,
        help="Turning angle in degrees above which a vertex is kept as a corner.",
    )

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
            config = VectorizerConfig(
                colors=args.colors,
                detail=args.detail,
                min_area=args.min_area,
                curve=args.curve,
                corner_angle=args.corner_angle,
                alpha_bins=args.alpha_bins,
                transparent_threshold=args.transparent_threshold,
            )
            result = vectorize_image(args.input, args.output, config)
            print(json.dumps(asdict(result.stats), indent=2))
            return 0

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
