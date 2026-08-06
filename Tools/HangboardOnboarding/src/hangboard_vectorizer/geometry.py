from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .models import ConversionError


@dataclass(frozen=True, slots=True)
class RectifiedBoard:
    rgb: np.ndarray
    mask: np.ndarray
    width: int
    height: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Opening:
    contour: np.ndarray
    center: tuple[float, float]
    bbox: tuple[int, int, int, int]
    area: float
    aspect_ratio: float
    id: str = ""


def isolate_board(
    rgb: np.ndarray, *, background_tolerance: float = 18.0
) -> np.ndarray:
    """Return the dominant non-background component as a boolean mask."""
    if rgb.ndim != 3 or rgb.shape[2] != 3 or min(rgb.shape[:2]) == 0:
        raise ConversionError("could not isolate board")

    height, width = rgb.shape[:2]
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    border_width = max(1, round(min(height, width) * 0.03))
    border = np.concatenate(
        (
            lab[:border_width].reshape(-1, 3),
            lab[-border_width:].reshape(-1, 3),
            lab[:, :border_width].reshape(-1, 3),
            lab[:, -border_width:].reshape(-1, 3),
        )
    )
    background = np.median(border, axis=0)
    distance = np.linalg.norm(lab - background, axis=2)
    foreground = (distance > background_tolerance).astype(np.uint8)

    kernel_size = max(3, round(min(height, width) * 0.008))
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel)

    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground)
    if component_count <= 1:
        raise ConversionError("could not isolate board")
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    area = int(stats[largest_label, cv2.CC_STAT_AREA])
    if not 0.03 * height * width <= area <= 0.95 * height * width:
        raise ConversionError("could not isolate board")
    return labels == largest_label


def rectify_board(rgb: np.ndarray, mask: np.ndarray) -> RectifiedBoard:
    """Warp a detected board mask into a front-facing rectangular image."""
    if (
        rgb.ndim != 3
        or rgb.shape[2] != 3
        or mask.ndim != 2
        or min(rgb.shape[:2]) == 0
        or min(mask.shape) == 0
        or rgb.shape[:2] != mask.shape
    ):
        raise ConversionError("could not rectify board")
    contours, _ = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        raise ConversionError("could not rectify board")

    contour = max(contours, key=cv2.contourArea)
    approximation = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
    warnings: tuple[str, ...] = ()
    if len(approximation) == 4 and cv2.isContourConvex(approximation):
        corners = approximation.reshape(4, 2).astype(np.float32)
    else:
        corners = cv2.boxPoints(cv2.minAreaRect(contour)).astype(np.float32)
        warnings = ("minimum-area rectangle fallback",)
    corners = _order_corners(corners)

    top = np.linalg.norm(corners[1] - corners[0])
    bottom = np.linalg.norm(corners[2] - corners[3])
    right = np.linalg.norm(corners[2] - corners[1])
    left = np.linalg.norm(corners[3] - corners[0])
    width = max(1, int(round(max(top, bottom))))
    height = max(1, int(round(max(right, left))))
    target = np.float32(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]]
    )
    transform = cv2.getPerspectiveTransform(corners, target)
    transformed_contours = cv2.perspectiveTransform(
        np.vstack(contours).astype(np.float32), transform
    ).reshape(-1, 2)
    left = min(0, int(np.floor(transformed_contours[:, 0].min())))
    top = min(0, int(np.floor(transformed_contours[:, 1].min())))
    right = max(width - 1, int(np.ceil(transformed_contours[:, 0].max())))
    bottom = max(height - 1, int(np.ceil(transformed_contours[:, 1].max())))
    transform = np.array(
        ((1.0, 0.0, -left), (0.0, 1.0, -top), (0.0, 0.0, 1.0)),
        dtype=np.float64,
    ) @ transform
    width = right - left + 1
    height = bottom - top + 1
    rectified_rgb = cv2.warpPerspective(rgb, transform, (width, height))
    rectified_mask = cv2.warpPerspective(
        mask.astype(np.uint8), transform, (width, height), flags=cv2.INTER_NEAREST
    ).astype(bool)
    return RectifiedBoard(
        rgb=rectified_rgb,
        mask=rectified_mask,
        width=width,
        height=height,
        warnings=warnings,
    )


def _order_corners(points: np.ndarray) -> np.ndarray:
    """Return unique TL/TR/BR/BL corners with the longer axis as width."""
    points = np.asarray(points, dtype=np.float32).reshape(4, 2)
    if len(np.unique(points, axis=0)) != 4:
        raise ConversionError("could not rectify board")

    center = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])
    cyclic = points[np.argsort(angles)]
    edges = np.roll(cyclic, -1, axis=0) - cyclic
    edge_lengths = np.linalg.norm(edges, axis=1)

    # Opposite edges have the same parity in cyclic order. Rotate once when the
    # longer pair currently occupies the left/right slots so it becomes the
    # target's top/bottom pair.
    if edge_lengths[1] + edge_lengths[3] > edge_lengths[0] + edge_lengths[2]:
        cyclic = np.roll(cyclic, -1, axis=0)

    # The two long edges run in opposite directions around the quadrilateral.
    # Averaging their aligned directions gives a stable board axis under mild
    # perspective. Its sign is deterministic across a full in-plane rotation.
    long_axis = (cyclic[1] - cyclic[0]) + (cyclic[2] - cyclic[3])
    norm = float(np.linalg.norm(long_axis))
    if norm == 0.0:
        raise ConversionError("could not rectify board")
    long_axis /= norm
    if long_axis[0] < 0 or (long_axis[0] == 0 and long_axis[1] < 0):
        long_axis *= -1
    short_axis = np.array([-long_axis[1], long_axis[0]], dtype=np.float32)

    long_edges = ((cyclic[0], cyclic[1]), (cyclic[2], cyclic[3]))
    top, bottom = sorted(
        long_edges,
        key=lambda edge: float(((edge[0] + edge[1]) / 2) @ short_axis),
    )
    top_left, top_right = sorted(top, key=lambda point: float(point @ long_axis))
    bottom_left, bottom_right = sorted(
        bottom, key=lambda point: float(point @ long_axis)
    )
    return np.float32([top_left, top_right, bottom_right, bottom_left])


def detect_openings(
    board: RectifiedBoard,
    *,
    contrast_threshold: float = 25.0,
    min_area_ratio: float = 0.0005,
) -> tuple[Opening, ...]:
    """Find dark board features that differ from their local background."""
    if (
        board.rgb.ndim != 3
        or board.rgb.shape[2] != 3
        or board.mask.ndim != 2
        or min(board.rgb.shape[:2]) == 0
        or min(board.mask.shape) == 0
        or board.rgb.shape[:2] != board.mask.shape
        or (board.width, board.height) != (board.rgb.shape[1], board.rgb.shape[0])
    ):
        raise ConversionError("could not detect openings")
    gray = cv2.cvtColor(board.rgb, cv2.COLOR_RGB2GRAY)
    local_background = cv2.GaussianBlur(
        gray, (0, 0), sigmaX=max(3, board.width / 80)
    )
    contrast = local_background.astype(np.float32) - gray.astype(np.float32)
    eroded_mask = cv2.erode(
        board.mask.astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )
    candidates = ((contrast >= contrast_threshold) & eroded_mask.astype(bool)).astype(
        np.uint8
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    candidates = cv2.morphologyEx(candidates, cv2.MORPH_OPEN, kernel)
    candidates = cv2.morphologyEx(candidates, cv2.MORPH_CLOSE, kernel)

    _, labels, stats, _ = cv2.connectedComponentsWithStats(candidates)
    minimum_area = min_area_ratio * int(board.mask.sum())
    openings: list[Opening] = []
    for label in range(1, len(stats)):
        if stats[label, cv2.CC_STAT_AREA] < minimum_area:
            continue
        component = (labels == label).astype(np.uint8)
        contours, _ = cv2.findContours(
            component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(contour))
        x, y, width, height = cv2.boundingRect(contour)
        moments = cv2.moments(contour)
        if moments["m00"]:
            center = (
                float(moments["m10"] / moments["m00"]),
                float(moments["m01"] / moments["m00"]),
            )
        else:
            center = (x + width / 2, y + height / 2)
        openings.append(
            Opening(
                contour=contour.reshape(-1, 2).astype(float),
                center=center,
                bbox=(x, y, width, height),
                area=area,
                aspect_ratio=width / height,
            )
        )
    if not openings:
        raise ConversionError("no openings detected")
    return tuple(openings)
