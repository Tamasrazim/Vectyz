"""Shared configuration and result models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VectorizerConfig:
    """Controls raster-to-vector conversion.

    `detail` is a normalized contour tolerance multiplier. Smaller values retain
    more contour vertices; larger values create simpler paths.
    """

    colors: int = 16
    detail: float = 1.0
    min_area: float = 2.0
    curve: str = "smooth"
    corner_angle: float = 65.0
    alpha_bins: int = 4
    transparent_threshold: int = 4
    quantizer: str = "mediancut"

    def __post_init__(self) -> None:
        if not 2 <= self.colors <= 256:
            raise ValueError("colors must be between 2 and 256")
        if not 0.05 <= self.detail <= 20:
            raise ValueError("detail must be between 0.05 and 20")
        if self.min_area < 0:
            raise ValueError("min_area cannot be negative")
        if self.curve not in {"smooth", "polygon"}:
            raise ValueError("curve must be 'smooth' or 'polygon'")
        if not 5 <= self.corner_angle <= 120:
            raise ValueError("corner_angle must be between 5 and 120 degrees")
        if not 1 <= self.alpha_bins <= 16:
            raise ValueError("alpha_bins must be between 1 and 16")
        if not 0 <= self.transparent_threshold <= 254:
            raise ValueError("transparent_threshold must be between 0 and 254")
        if self.quantizer not in {"mediancut", "maxcoverage", "fastoctree"}:
            raise ValueError(
                "quantizer must be 'mediancut', 'maxcoverage' or 'fastoctree'"
            )


@dataclass(frozen=True, slots=True)
class VectorizationStats:
    width: int
    height: int
    colors_used: int
    paths: int
    components_removed: int
    elapsed_ms: float


@dataclass(frozen=True, slots=True)
class VectorPath:
    data: str
    color: tuple[int, int, int]
    opacity: float


@dataclass(frozen=True, slots=True)
class VectorizationResult:
    svg: str
    stats: VectorizationStats
    vector_paths: tuple[VectorPath, ...]
