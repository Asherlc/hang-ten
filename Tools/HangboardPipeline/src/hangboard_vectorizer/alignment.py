"""Canonical alignment of a detected board to a product template."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

from .geometry import RectifiedBoard, rectify_board
from .models import ConversionError
from .templates import ProductTemplate


@dataclass(frozen=True, slots=True)
class AlignmentInfo:
    method: Literal["quadrilateral-frame", "minimum-area-frame"]
    aspect_ratio_error: float
    confidence: Literal["high", "low"]


@dataclass(frozen=True, slots=True)
class AlignedTemplate:
    board: RectifiedBoard
    info: AlignmentInfo


def align_board_to_template(
    rgb: np.ndarray,
    mask: np.ndarray,
    template: ProductTemplate,
    *,
    allow_low_confidence: bool = False,
) -> AlignedTemplate:
    """Rectify a board once, then fit it to the template's canonical frame."""
    rectified = rectify_board(rgb, mask)
    detected_ratio = rectified.width / rectified.height
    canonical_ratio = template.canonical_width / template.canonical_height
    aspect_ratio_error = abs(detected_ratio - canonical_ratio) / canonical_ratio
    threshold_epsilon = 1e-12
    if aspect_ratio_error > 0.15 + threshold_epsilon and not allow_low_confidence:
        raise ConversionError("detected board aspect ratio does not match product template")

    low_confidence = aspect_ratio_error > 0.05 + threshold_epsilon
    warnings = rectified.warnings
    if low_confidence:
        warnings += ("low alignment confidence",)
    method: Literal["quadrilateral-frame", "minimum-area-frame"]
    method = (
        "minimum-area-frame"
        if "minimum-area rectangle fallback" in rectified.warnings
        else "quadrilateral-frame"
    )
    resized_detected_mask = cv2.resize(
        rectified.mask.astype(np.uint8),
        (template.canonical_width, template.canonical_height),
        interpolation=cv2.INTER_NEAREST,
    ).astype(bool)
    if not resized_detected_mask.any():
        raise ConversionError("aligned detected mask is empty")
    aligned = RectifiedBoard(
        rgb=cv2.resize(
            rectified.rgb,
            (template.canonical_width, template.canonical_height),
            interpolation=cv2.INTER_LINEAR,
        ),
        mask=_rasterize_outline(template),
        width=template.canonical_width,
        height=template.canonical_height,
        warnings=warnings,
    )
    return AlignedTemplate(
        board=aligned,
        info=AlignmentInfo(
            method=method,
            aspect_ratio_error=aspect_ratio_error,
            confidence="low" if low_confidence else "high",
        ),
    )


def _rasterize_outline(template: ProductTemplate) -> np.ndarray:
    mask = np.zeros((template.canonical_height, template.canonical_width), dtype=np.uint8)
    polygons: list[np.ndarray] = []
    scale = np.array([template.canonical_width, template.canonical_height])
    for polygon in template.outline:
        transformed = polygon * scale
        if not np.isfinite(transformed).all():
            raise ConversionError("template outline contains non-finite coordinates")
        polygons.append(np.rint(transformed).astype(np.int32))
    cv2.fillPoly(mask, polygons, 1)
    return mask.astype(bool)
