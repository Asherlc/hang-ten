"""Deterministic cleanup for the authoritative Beastmaker product photograph."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

import cv2
import numpy as np


_SOURCE_CROP = (35, 30, 1041, 289)
_AUTHORITATIVE_SOURCE_SHAPE = (318, 1080, 3)
# SHA-256 of source.jpg after deterministic Pillow conversion to RGB pixels.
_AUTHORITATIVE_SOURCE_RGB_SHA256 = (
    "e1429eefc16670169b032545fe1093272ca0fb9b5fdb67d7a85b1289b9f19dd3"
)
_CANONICAL_SIZE = (1000, 259)
_REVIEW_PADDING = 100
_REVIEW_BACKGROUND = np.array([248, 247, 244], dtype=np.uint8)
_SCREW_CENTERS = (
    (110, 75),
    (432, 75),
    (570, 75),
    (892, 74),
    (184, 211),
    (818, 211),
)
_BRANDING_RECTS = (
    (216, 84, 352, 113),
    (658, 84, 786, 113),
)


@dataclass(frozen=True, slots=True)
class PhotoCleanup:
    """Canonical transparent asset, review composite, and repaired-pixel mask."""

    rgba: np.ndarray
    review_rgb: np.ndarray
    repair_mask: np.ndarray


def clean_beastmaker_photo(source_rgb: np.ndarray) -> PhotoCleanup:
    """Clean the fixed real-product raster without changing its carved geometry."""
    if source_rgb.dtype != np.uint8 or source_rgb.ndim != 3:
        raise ValueError("source photograph must be an H x W x 3 uint8 RGB array")
    if source_rgb.shape[2] != 3:
        raise ValueError("source photograph must have exactly three RGB channels")
    _validate_source_registration(source_rgb)

    left, top, right, bottom = _SOURCE_CROP
    crop = source_rgb[top:bottom, left:right]
    canonical = cv2.resize(crop, _CANONICAL_SIZE, interpolation=cv2.INTER_LANCZOS4)
    alpha = _extract_board_alpha(canonical)
    repair_mask = _template_repair_mask()
    repaired = _repair_artifacts(canonical)
    finished = _normalize_wood(repaired, alpha, repair_mask)

    rgba = np.empty((259, 1000, 4), dtype=np.uint8)
    rgba[..., :3] = finished
    rgba[..., 3] = alpha
    rgba[alpha == 0, :3] = 0

    review_height = 259 + 2 * _REVIEW_PADDING
    review_width = 1000 + 2 * _REVIEW_PADDING
    review = np.empty((review_height, review_width, 3), dtype=np.uint8)
    review[...] = _REVIEW_BACKGROUND
    target = review[
        _REVIEW_PADDING : _REVIEW_PADDING + 259,
        _REVIEW_PADDING : _REVIEW_PADDING + 1000,
    ]
    coverage = alpha.astype(np.float32)[..., None] / 255.0
    composited = (
        finished.astype(np.float32) * coverage
        + _REVIEW_BACKGROUND.astype(np.float32) * (1.0 - coverage)
    )
    target[...] = np.rint(np.clip(composited, 0.0, 255.0)).astype(np.uint8)

    rgba.setflags(write=False)
    review.setflags(write=False)
    repair_mask.setflags(write=False)
    return PhotoCleanup(rgba=rgba, review_rgb=review, repair_mask=repair_mask)


def _validate_source_registration(source_rgb: np.ndarray) -> None:
    if source_rgb.shape != _AUTHORITATIVE_SOURCE_SHAPE:
        raise ValueError(
            "source registration requires the authoritative 1080 x 318 RGB raster"
        )
    fingerprint = sha256(source_rgb.tobytes()).hexdigest()
    if fingerprint != _AUTHORITATIVE_SOURCE_RGB_SHA256:
        raise ValueError("source registration fingerprint does not match source.jpg")


def _extract_board_alpha(rgb: np.ndarray) -> np.ndarray:
    maximum = np.max(rgb, axis=2).astype(np.int16)
    minimum = np.min(rgb, axis=2).astype(np.int16)
    chroma = maximum - minimum
    luminance = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    wood = (chroma >= 7) & (luminance < 253)
    row_coverage = np.count_nonzero(wood, axis=1)
    dense_threshold = max(1, int(np.max(row_coverage) * 0.25))
    dense_rows = np.flatnonzero(row_coverage >= dense_threshold)
    if dense_rows.size:
        wood[int(dense_rows[-1]) + 1 :] = False

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    padding = kernel.shape[0] // 2
    padded = np.pad(wood.astype(np.uint8), padding, mode="constant")
    padded_closed = cv2.morphologyEx(
        padded,
        cv2.MORPH_CLOSE,
        kernel,
        borderType=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    closed = padded_closed[padding:-padding, padding:-padding]
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError("source photograph does not contain a product silhouette")
    silhouette = np.zeros(closed.shape, dtype=np.uint8)
    cv2.drawContours(silhouette, [max(contours, key=cv2.contourArea)], -1, 255, -1)
    softened = cv2.GaussianBlur(
        silhouette.astype(np.float32), (0, 0), sigmaX=0.65, sigmaY=0.65
    )
    return np.rint(np.clip(softened, 0.0, 255.0)).astype(np.uint8)


def _template_repair_mask() -> np.ndarray:
    mask = np.zeros((259, 1000), dtype=np.uint8)
    for x1, y1, x2, y2 in _BRANDING_RECTS:
        cv2.rectangle(mask, (x1, y1), (x2 - 1, y2 - 1), 255, -1)
    for center in _SCREW_CENTERS:
        cv2.circle(mask, center, 10, 255, -1, lineType=cv2.LINE_AA)
    return mask


def _repair_artifacts(rgb: np.ndarray) -> np.ndarray:
    repaired = rgb.astype(np.float32).copy()
    donor = rgb[20:49, 430:566].astype(np.float32)
    donor_base = cv2.GaussianBlur(donor, (0, 0), sigmaX=10.0, sigmaY=1.8)
    donor_grain = donor - donor_base

    for x1, y1, x2, y2 in _BRANDING_RECTS:
        height = y2 - y1
        width = x2 - x1
        left = np.median(repaired[y1:y2, x1 - 8 : x1], axis=1)
        right = np.median(repaired[y1:y2, x2 : x2 + 8], axis=1)
        position = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :, None]
        fill = left[:, None, :] * (1.0 - position) + right[:, None, :] * position
        texture = cv2.resize(
            donor_grain, (width, height), interpolation=cv2.INTER_CUBIC
        )
        fill += 0.68 * texture

        yy, xx = np.mgrid[0:height, 0:width]
        edge_distance = np.minimum.reduce(
            (xx + 1, width - xx, yy + 1, height - yy)
        ).astype(np.float32)
        blend = np.clip(edge_distance / 3.0, 0.0, 1.0)[..., None]
        original = repaired[y1:y2, x1:x2]
        repaired[y1:y2, x1:x2] = original * (1.0 - blend) + fill * blend

    for x, y in _SCREW_CENTERS:
        radius = 10
        size = 2 * radius + 1
        donor_patch = repaired[
            y - radius : y + radius + 1,
            x - 3 * radius - 1 : x - radius,
        ]
        donor_patch = cv2.resize(
            donor_patch, (size, size), interpolation=cv2.INTER_CUBIC
        )
        yy, xx = np.mgrid[-radius : radius + 1, -radius : radius + 1]
        distance = np.sqrt(xx * xx + yy * yy)
        blend = np.clip((radius + 0.5 - distance) / 2.0, 0.0, 1.0)[..., None]
        original = repaired[
            y - radius : y + radius + 1,
            x - radius : x + radius + 1,
        ]
        repaired[
            y - radius : y + radius + 1,
            x - radius : x + radius + 1,
        ] = original * (1.0 - blend) + donor_patch * blend

    return np.rint(np.clip(repaired, 0.0, 255.0)).astype(np.uint8)


def _normalize_wood(
    rgb: np.ndarray, alpha: np.ndarray, repair_mask: np.ndarray
) -> np.ndarray:
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    surface = (alpha >= 245) & (lab[..., 0] >= 112.0) & (repair_mask == 0)

    light_profile = _smooth_column_median(lab[..., 0], surface, sigma=52.0)

    a_field = _smooth_surface_field(lab[..., 1], surface)
    b_field = _smooth_surface_field(lab[..., 2], surface)

    lab[..., 0] += 0.88 * (207.0 - light_profile[None, :])
    lab[..., 1] += 0.90 * (133.0 - a_field)
    lab[..., 2] += 0.90 * (151.0 - b_field)

    denoised_light = cv2.bilateralFilter(
        lab[..., 0], d=5, sigmaColor=5.0, sigmaSpace=3.0
    )
    lab[..., 0] = 0.82 * lab[..., 0] + 0.18 * denoised_light
    corrected = cv2.cvtColor(
        np.rint(np.clip(lab, 0.0, 255.0)).astype(np.uint8), cv2.COLOR_LAB2RGB
    )
    corrected[alpha == 0] = 0
    return corrected


def _smooth_surface_field(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    weights = valid.astype(np.float32)
    weighted_values = values * weights
    numerator = cv2.GaussianBlur(
        weighted_values, (0, 0), sigmaX=72.0, sigmaY=30.0
    )
    denominator = cv2.GaussianBlur(weights, (0, 0), sigmaX=72.0, sigmaY=30.0)
    return numerator / np.maximum(denominator, 1e-4)


def _smooth_column_median(
    values: np.ndarray, valid: np.ndarray, *, sigma: float
) -> np.ndarray:
    profile = np.full(values.shape[1], np.nan, dtype=np.float32)
    for x in range(values.shape[1]):
        column = values[:, x][valid[:, x]]
        if column.size >= 12:
            profile[x] = float(np.median(column))

    known = np.flatnonzero(np.isfinite(profile))
    if known.size < 2:
        raise ValueError("source photograph lacks enough clean surface for normalization")
    missing = np.flatnonzero(~np.isfinite(profile))
    profile[missing] = np.interp(missing, known, profile[known])
    smoothed = cv2.GaussianBlur(
        profile[None, :], (0, 0), sigmaX=sigma, sigmaY=0.0
    )
    return smoothed[0].astype(np.float32)
