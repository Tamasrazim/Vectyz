"""Vectyz raster/vector conversion engine."""

from .engine import rasterize_svg, vectorize_image, write_vector
from .models import VectorizationResult, VectorizationStats, VectorizerConfig

__all__ = [
    "VectorizationResult",
    "VectorizationStats",
    "VectorizerConfig",
    "rasterize_svg",
    "vectorize_image",
    "write_vector",
]

__version__ = "0.1.0"
