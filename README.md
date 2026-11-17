# Vectyz

**A deterministic raster-to-vector and vector-to-raster conversion engine.**

Vectyz turns raster images into editable vector paths using palette quantization, connected-region tracing, contour simplification and corner-aware cubic Bézier fitting. It can also rasterize SVG artwork into common bitmap formats.

The project is an engine and command-line tool. It is not a drawing application, and it does not embed a bitmap in an SVG as a substitute for vectorization.

## Current capabilities

### Raster to vector
- Input: PNG, JPEG, WebP, BMP, TIFF and other formats supported by Pillow.
- Deterministic palette reduction with a configurable limit of 2–256 colors.
- Per-color region masks and contour extraction.
- Interior-hole preservation with even-odd fill rules.
- Small-component filtering to reduce isolated noise.
- Polygon or corner-aware cubic Bézier path output.
- Transparent input support, with configurable alpha quantization.
- Output: SVG, PDF and EPS.

### Vector to raster
- SVG input rasterized through CairoSVG.
- PNG, JPEG, WebP, TIFF and BMP output.
- Optional output dimensions and background compositing.

## Install

Python 3.10 or newer is required.

```bash
python -m pip install -e .
```

Install the optional SVG rasterizer dependency when using the `rasterize` command or PDF export:

```bash
python -m pip install -e ".[render]"
```

For development and tests:

```bash
python -m pip install -e ".[dev,render]"
pytest
```

## Usage

Vectorize a raster image:

```bash
vectyz vectorize input.png output.svg
```

Use a limited palette and smoother curves:

```bash
vectyz vectorize input.jpg output.svg --colors 24 --detail 0.8 --curve smooth
```

Export to PDF or EPS by changing the output extension:

```bash
vectyz vectorize input.png output.pdf --colors 16
vectyz vectorize input.png output.eps --colors 16
```

Rasterize an SVG:

```bash
vectyz rasterize artwork.svg output.png --width 2400
vectyz rasterize artwork.svg output.webp --width 1600 --height 1600 --background "#ffffff"
```

See `vectyz --help`, `vectyz vectorize --help` and `vectyz rasterize --help` for all options.

## Vectorization controls

| Option | Default | Meaning |
| --- | ---: | --- |
| `--colors` | 16 | Maximum number of palette colors (2–256). |
| `--detail` | 1.0 | Contour simplification tolerance. Lower values retain more points. |
| `--min-area` | 2.0 | Ignore outer components smaller than this many source pixels. |
| `--curve` | smooth | Use corner-aware cubic Bézier segments or straight polygon segments. |
| `--alpha-bins` | 4 | Number of opacity bands used to approximate partial transparency. |
| `--corner-angle` | 42 | Preserve vertices whose turning angle exceeds this value. |
| `--transparent-threshold` | 4 | Alpha values at or below this value are treated as transparent. |

## Architecture

- `image.py`: safe image loading, EXIF orientation and palette quantization.
- `tracing.py`: color/alpha masks, connected contours, hole relationships and path fitting.
- `engine.py`: public conversion pipeline and statistics.
- `exporters.py`: SVG, PDF, EPS and raster output.
- `cli.py`: command-line interface.

The tracing pipeline is deterministic for the same input, Pillow/OpenCV versions and settings. It is classical image processing, not a machine-learning model: it does not infer semantic objects or recover hidden details from a photograph.

## Current limitations

- Photographs can produce many small regions and are not guaranteed to become compact, hand-editable illustrations.
- Palette quantization approximates gradients; it does not reconstruct continuous vector gradients.
- The smooth curve fitter is geometry-based and can still need a lower `--detail` value for intricate artwork.
- EPS has no native alpha support, so translucent fills are composited against white.
- SVG rasterization requires the optional `render` extra.

Vectyz is under active development. The current implementation provides the first end-to-end conversion pipeline and test suite; advanced geometry recognition, gradient reconstruction, and performance work remain future engineering tasks.
