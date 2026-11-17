from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from vectyz import VectorizerConfig, rasterize_svg, vectorize_image, write_vector


def make_test_artwork() -> Image.Image:
    image = Image.new("RGBA", (96, 72), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 44, 62), fill=(230, 30, 50, 255))
    draw.ellipse((50, 12, 86, 48), fill=(20, 90, 220, 220))
    draw.ellipse((60, 22, 76, 38), fill=(0, 0, 0, 0))
    return image


def test_vectorize_produces_paths_and_viewbox() -> None:
    image = make_test_artwork()
    result = vectorize_image(image, config=VectorizerConfig(colors=8))
    assert 'viewBox="0 0 96 72"' in result.svg
    assert "<path " in result.svg
    assert result.stats.width == 96
    assert result.stats.height == 72
    assert result.stats.paths > 0
    assert result.stats.colors_used > 0


def test_transparent_canvas_is_not_painted() -> None:
    image = Image.new("RGBA", (24, 24), (255, 0, 255, 0))
    result = vectorize_image(image)
    assert result.stats.paths == 0
    assert "<path " not in result.svg


def test_config_rejects_invalid_color_limit() -> None:
    with pytest.raises(ValueError):
        VectorizerConfig(colors=300)


def test_write_svg_and_eps(tmp_path: Path) -> None:
    result = vectorize_image(make_test_artwork())
    svg_path = tmp_path / "output.svg"
    eps_path = tmp_path / "output.eps"
    write_vector(result, svg_path)
    write_vector(result, eps_path)
    assert svg_path.read_text(encoding="utf-8").startswith('<?xml')
    assert eps_path.read_text(encoding="ascii").startswith("%!PS-Adobe-3.0 EPSF-3.0")
    assert "showpage" not in eps_path.read_text(encoding="ascii")


def test_polygon_mode_produces_line_segments() -> None:
    result = vectorize_image(
        make_test_artwork(),
        config=VectorizerConfig(colors=8, curve="polygon"),
    )
    assert "L " in result.svg
    assert " C " not in result.svg


def test_opacity_is_measured_per_palette_color() -> None:
    image = Image.new("RGBA", (40, 20))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 19, 19), fill=(240, 20, 30, 80))
    draw.rectangle((20, 0, 39, 19), fill=(20, 40, 240, 200))
    result = vectorize_image(
        image,
        config=VectorizerConfig(colors=2, alpha_bins=1, curve="polygon"),
    )
    opacities = {round(path.opacity, 2) for path in result.vector_paths}
    assert len(opacities) == 2
    assert min(opacities) < 0.4
    assert max(opacities) > 0.7


def test_rasterize_svg_to_png(tmp_path: Path) -> None:
    pytest.importorskip("cairosvg")
    svg_path = tmp_path / "source.svg"
    png_path = tmp_path / "rendered.png"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
        '<rect width="10" height="10" fill="#ff0000"/></svg>',
        encoding="utf-8",
    )
    rasterize_svg(svg_path, png_path, width=30, height=20)
    with Image.open(png_path) as rendered:
        assert rendered.size == (30, 20)
        assert rendered.convert("RGB").getpixel((10, 10)) == (255, 0, 0)


def test_transparent_hidden_colors_do_not_create_vector_regions() -> None:
    image = Image.new("RGBA", (24, 24), (255, 0, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((5, 5, 18, 18), fill=(20, 180, 70, 255))
    result = vectorize_image(image, config=VectorizerConfig(colors=4))
    assert result.stats.colors_used == 1
    assert result.stats.paths == 1
