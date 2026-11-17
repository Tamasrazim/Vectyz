# Vectyz

**A deterministic raster-to-vector and vector-to-raster conversion engine.**

Vectyz turns raster images into editable vector paths using palette quantization, connected-region tracing, contour simplification and corner-aware cubic Bézier fitting. It can also rasterize SVG artwork into common bitmap formats.

Vectyz is an engine and command-line tool, not a drawing application. It traces the image into real vector paths; it does not place the original bitmap inside an SVG.

## Install on Windows

Install Python 3.10 or newer, then open PowerShell:

```powershell
git clone https://github.com/Tamasrazim/Vectyz.git
cd Vectyz
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[render]"
```

The `render` extra installs CairoSVG, which enables SVG-to-raster conversion and PDF export. Raster-to-SVG and EPS conversion work with the base package.

If PowerShell blocks activation, run this once in the current terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Use it

### 1. Convert one image to SVG

```powershell
vectyz vectorize "C:\Images\logo.png" "C:\Images\logo.svg"
```

### 2. Tune the vector result

```powershell
vectyz vectorize "C:\Images\illustration.png" "C:\Images\illustration.svg" --colors 24 --detail 0.7 --curve smooth --quantizer maxcoverage
```

Useful controls:

| Option | Default | Effect |
| --- | ---: | --- |
| `--colors` | 16 | Maximum number of color regions (2–256). |
| `--detail` | 1.0 | Contour simplification; lower retains more detail. |
| `--min-area` | 2.0 | Remove tiny outer regions smaller than this area in source pixels. |
| `--curve` | smooth | Use fitted cubic curves; choose `polygon` for straight segments. |
| `--quantizer` | mediancut | Choose `mediancut`, `maxcoverage` or `fastoctree` for palette learning. |
| `--alpha-bins` | 4 | Opacity bands used to approximate translucent pixels (1–16). |
| `--corner-angle` | 65 | Preserve sharper turns as corners. |
| `--transparent-threshold` | 4 | Ignore pixels whose alpha is at or below this value. |

A sensible first pass for flat artwork is `--colors 16 --detail 0.8`. Logos with crisp edges may look better with `--curve polygon`. Photographs generally need more colors and can still create many paths. Try a different quantizer when the palette loses important colors.

### 3. Export PDF or EPS

```powershell
vectyz vectorize "C:\Images\logo.png" "C:\Images\logo.pdf"
vectyz vectorize "C:\Images\logo.png" "C:\Images\logo.eps"
```

PDF export needs the `render` extra. EPS does not support alpha, so translucent regions are composited against white.

### 4. Convert a whole folder

```powershell
vectyz batch "C:\Images\input" "C:\Images\vectors"
```

Include subfolders and preserve their structure:

```powershell
vectyz batch "C:\Images\input" "C:\Images\vectors" --recursive --format svg --colors 24 --detail 0.8
```

Batch mode processes one file at a time to keep memory use predictable. It writes a `vectyz-report.json` containing per-file statistics and failures. A failed image does not stop the remaining batch.

### 5. Convert SVG back to a raster image

```powershell
vectyz rasterize "C:\Images\logo.svg" "C:\Images\logo.png" --width 2400
vectyz rasterize "C:\Images\logo.svg" "C:\Images\logo.webp" --width 1600 --height 1600 --background "#ffffff"
```

Supported raster outputs: PNG, JPEG, WebP, TIFF and BMP. Omit `--background` to keep transparency where the target format supports it.

### 6. Run without activating the environment

From the repository folder:

```powershell
.\.venv\Scripts\python.exe -m vectyz --help
.\.venv\Scripts\python.exe -m vectyz vectorize "C:\Images\logo.png" "C:\Images\logo.svg"
```

## Python API

```python
from vectyz import VectorizerConfig, vectorize_image

settings = VectorizerConfig(
    colors=24,
    detail=0.7,
    curve="smooth",
    quantizer="maxcoverage",
    alpha_bins=4,
)

result = vectorize_image("input.png", "output.svg", settings)
print(result.stats)
```

To vectorize a directory from Python:

```python
from vectyz import VectorizerConfig, vectorize_directory

report = vectorize_directory(
    "input_images",
    "output_vectors",
    config=VectorizerConfig(colors=24, detail=0.8),
    output_format="svg",
    recursive=True,
)
print(f"Converted {report['succeeded']} of {report['total']} files")
```

## Architecture

- `image.py`: image loading, EXIF orientation and palette quantization.
- `tracing.py`: color/alpha masks, contour extraction, hole relationships and path fitting.
- `engine.py`: single-image conversion pipeline and statistics.
- `batch.py`: sequential folder conversion and machine-readable reports.
- `exporters.py`: SVG, PDF, EPS and raster output.
- `cli.py`: command-line interface.
- `models.py`: validated conversion settings and result types.

The pipeline is deterministic for the same input, dependency versions and settings. It uses classical image processing, not machine learning: it does not infer semantic objects or recover details hidden in a photograph.

## Current limitations

- Photographs can produce many small regions and are not guaranteed to become compact, hand-editable illustrations.
- Palette quantization approximates gradients; continuous vector-gradient reconstruction is not implemented.
- The current smooth curve fitter is geometry-based and may need a lower `--detail` value for intricate artwork.
- EPS has no native alpha support; translucent fills are composited against white.
- SVG-to-raster conversion and PDF export require CairoSVG.

## Development

```powershell
python -m pip install -e ".[dev,render]"
pytest
ruff check src tests
```
