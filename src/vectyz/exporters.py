"""Vector and raster format writers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from PIL import Image

from .models import VectorPath, VectorizationResult


def build_svg(
    width: int, height: int, vector_paths: Iterable[VectorPath]
) -> str:
    paths = tuple(vector_paths)
    body: list[str] = []
    for path in paths:
        red, green, blue = path.color
        color = f"#{red:02x}{green:02x}{blue:02x}"
        body.append(
            f'<path d="{path.data}" fill="{color}" '
            f'fill-opacity="{path.opacity:.5f}" fill-rule="evenodd"/>'
        )

    contents = "\n  ".join(body)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}px" height="{height}px" '
        f'viewBox="0 0 {width} {height}" '
        'shape-rendering="geometricPrecision">\n'
        f"  {contents}\n"
        "</svg>\n"
    )


_TOKEN_RE = re.compile(r"[MLCZ]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def _path_to_postscript(data: str) -> str:
    tokens = _TOKEN_RE.findall(data)
    output: list[str] = []
    index = 0
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command == "Z":
            output.append("closepath")
            continue

        if command == "M" or command == "L":
            if index + 1 >= len(tokens):
                raise ValueError("Malformed vector path: coordinate pair is incomplete")
            x, y = tokens[index], tokens[index + 1]
            index += 2
            output.append(f"{x} {y} {'moveto' if command == 'M' else 'lineto'}")
            continue

        if command == "C":
            if index + 5 >= len(tokens):
                raise ValueError("Malformed vector path: cubic segment is incomplete")
            values = tokens[index : index + 6]
            index += 6
            output.append(" ".join(values) + " curveto")
            continue

        raise ValueError(f"Unsupported path command: {command}")

    return " ".join(output)


def write_eps(result: VectorizationResult, output_path: str | Path) -> None:
    """Write a vector EPS file. Transparency is composited against white."""
    width = result.stats.width
    height = result.stats.height
    lines = [
        "%!PS-Adobe-3.0 EPSF-3.0",
        f"%%BoundingBox: 0 0 {width} {height}",
        "%%LanguageLevel: 2",
        "%%Pages: 1",
        "%%EndComments",
        "gsave",
        f"0 {height} translate 1 -1 scale",
    ]

    for path in result.vector_paths:
        opacity = max(0.0, min(1.0, path.opacity))
        red, green, blue = (component / 255.0 for component in path.color)
        red = red * opacity + (1.0 - opacity)
        green = green * opacity + (1.0 - opacity)
        blue = blue * opacity + (1.0 - opacity)
        lines.extend(
            [
                f"{red:.6f} {green:.6f} {blue:.6f} setrgbcolor",
                f"newpath {_path_to_postscript(path.data)}",
                "eofill",
            ]
        )

    lines.extend(["grestore", "showpage", "%%EOF", ""])
    Path(output_path).write_text("\n".join(lines), encoding="ascii")


def write_vector(result: VectorizationResult, output_path: str | Path) -> None:
    """Write SVG, PDF or EPS based on the destination extension."""
    destination = Path(output_path)
    extension = destination.suffix.lower()

    if extension == ".svg":
        destination.write_text(result.svg, encoding="utf-8")
        return
    if extension == ".eps":
        write_eps(result, destination)
        return
    if extension == ".pdf":
        try:
            import cairosvg
        except ImportError as exc:
            raise RuntimeError(
                "PDF export requires CairoSVG. Install with: pip install 'vectyz[render]'"
            ) from exc
        cairosvg.svg2pdf(bytestring=result.svg.encode("utf-8"), write_to=str(destination))
        return

    raise ValueError("Vector output must use .svg, .pdf or .eps")


def rasterize_svg(
    source: str | Path,
    output_path: str | Path,
    width: int | None = None,
    height: int | None = None,
    background: str | None = None,
) -> None:
    """Rasterize SVG to a Pillow-supported bitmap format."""
    if width is not None and width < 1:
        raise ValueError("width must be a positive integer")
    if height is not None and height < 1:
        raise ValueError("height must be a positive integer")

    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError(
            "SVG rasterization requires CairoSVG. Install with: pip install 'vectyz[render]'"
        ) from exc

    png_bytes = cairosvg.svg2png(
        url=str(source),
        output_width=width,
        output_height=height,
    )
    from io import BytesIO

    image = Image.open(BytesIO(png_bytes)).convert("RGBA")
    if background:
        canvas = Image.new("RGBA", image.size, background)
        canvas.alpha_composite(image)
        image.close()
        image = canvas

    destination = Path(output_path)
    output_format = destination.suffix.lower().lstrip(".")
    format_aliases = {"jpg": "JPEG", "jpeg": "JPEG", "tif": "TIFF"}
    output_format = format_aliases.get(output_format, output_format.upper())
    supported = {"PNG", "JPEG", "WEBP", "TIFF", "BMP"}
    if output_format not in supported:
        image.close()
        raise ValueError("Raster output must use .png, .jpg, .webp, .tif/.tiff or .bmp")

    if output_format == "JPEG":
        if image.getchannel("A").getextrema()[0] < 255:
            matte = Image.new("RGBA", image.size, "white")
            matte.alpha_composite(image)
            image.close()
            image = matte
        image = image.convert("RGB")
    elif output_format == "BMP":
        image = image.convert("RGB")

    image.save(destination, format=output_format)
    image.close()
