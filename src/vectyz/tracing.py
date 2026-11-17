"""Contour extraction and SVG path fitting."""

from __future__ import annotations

import math

import cv2
import numpy as np

from .models import VectorPath, VectorizerConfig


def _fmt(value: float) -> str:
    rounded = round(float(value), 2)
    if rounded == 0:
        rounded = 0.0
    return f"{rounded:g}"


def _turn_angle(previous: np.ndarray, current: np.ndarray, following: np.ndarray) -> float:
    incoming = current.astype(np.float64) - previous.astype(np.float64)
    outgoing = following.astype(np.float64) - current.astype(np.float64)
    in_length = float(np.linalg.norm(incoming))
    out_length = float(np.linalg.norm(outgoing))
    if in_length < 1e-9 or out_length < 1e-9:
        return 180.0
    cosine = float(np.dot(incoming, outgoing) / (in_length * out_length))
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def contour_to_path(
    contour: np.ndarray, perimeter: float, config: VectorizerConfig
) -> str | None:
    """Approximate one closed contour with lines and corner-aware cubic segments."""
    epsilon = max(0.35, perimeter * config.detail / 1000.0)
    approximation = cv2.approxPolyDP(contour, epsilon, True)
    points = approximation.reshape(-1, 2).astype(np.float64)
    if len(points) < 3:
        return None

    count = len(points)
    commands = [f"M {_fmt(points[0, 0])} {_fmt(points[0, 1])}"]
    corners: list[bool] = []
    tangents: list[np.ndarray] = []

    for index in range(count):
        previous = points[(index - 1) % count]
        current = points[index]
        following = points[(index + 1) % count]
        turn = _turn_angle(previous, current, following)
        corners.append(turn >= config.corner_angle)

        tangent = following - previous
        length = float(np.linalg.norm(tangent))
        if length > 1e-9:
            tangent = tangent / length
        else:
            tangent = np.array([0.0, 0.0], dtype=np.float64)
        tangents.append(tangent)

    for index in range(count):
        following_index = (index + 1) % count
        start = points[index]
        end = points[following_index]
        chord = float(np.linalg.norm(end - start))

        if (
            config.curve == "smooth"
            and not corners[index]
            and not corners[following_index]
            and chord > 1e-6
        ):
            handle = chord / 3.0
            control_1 = start + tangents[index] * handle
            control_2 = end - tangents[following_index] * handle
            commands.append(
                "C "
                f"{_fmt(control_1[0])} {_fmt(control_1[1])} "
                f"{_fmt(control_2[0])} {_fmt(control_2[1])} "
                f"{_fmt(end[0])} {_fmt(end[1])}"
            )
        else:
            commands.append(f"L {_fmt(end[0])} {_fmt(end[1])}")

    commands.append("Z")
    return " ".join(commands)


def trace_mask(
    mask: np.ndarray, config: VectorizerConfig
) -> tuple[list[str], int]:
    """Trace a binary region mask and preserve holes using even-odd subpaths."""
    binary = np.ascontiguousarray(mask.astype(np.uint8) * 255)
    contours, hierarchy = cv2.findContours(
        binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    if hierarchy is None or not contours:
        return [], 0

    hierarchy = hierarchy[0]
    paths: list[str] = []
    removed = 0

    for index, contour in enumerate(contours):
        if int(hierarchy[index][3]) != -1:
            continue

        area = abs(float(cv2.contourArea(contour)))
        if area < config.min_area:
            removed += 1
            continue

        perimeter = float(cv2.arcLength(contour, True))
        outer_path = contour_to_path(contour, perimeter, config)
        if outer_path is None:
            removed += 1
            continue

        subpaths = [outer_path]
        child = int(hierarchy[index][2])
        while child != -1:
            hole_area = abs(float(cv2.contourArea(contours[child])))
            if hole_area >= max(0.5, config.min_area * 0.25):
                hole_perimeter = float(cv2.arcLength(contours[child], True))
                hole_path = contour_to_path(contours[child], hole_perimeter, config)
                if hole_path is not None:
                    subpaths.append(hole_path)
            child = int(hierarchy[child][0])

        paths.append(" ".join(subpaths))

    return paths, removed


def trace_palette_layer(
    indices: np.ndarray,
    alpha: np.ndarray,
    palette_index: int,
    color: tuple[int, int, int],
    alpha_bin: int,
    config: VectorizerConfig,
) -> tuple[list[VectorPath], int]:
    """Trace one palette color at one quantized opacity level."""
    if config.alpha_bins == 1:
        opacity_mask = alpha > config.transparent_threshold
        opacity = float(alpha[opacity_mask].mean() / 255.0) if opacity_mask.any() else 1.0
    else:
        bucket = np.minimum(
            (alpha.astype(np.uint16) * config.alpha_bins) // 256,
            config.alpha_bins - 1,
        )
        opacity_mask = (bucket == alpha_bin) & (alpha > config.transparent_threshold)
        opacity = float(alpha[opacity_mask].mean() / 255.0) if opacity_mask.any() else 0.0

    mask = (indices == palette_index) & opacity_mask
    if not mask.any():
        return [], 0

    paths, removed = trace_mask(mask, config)
    vector_paths = [
        VectorPath(data=path, color=color, opacity=opacity) for path in paths
    ]
    return vector_paths, removed
