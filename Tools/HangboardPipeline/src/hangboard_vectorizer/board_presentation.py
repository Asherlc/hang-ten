"""Deterministically tighten complete board-package presentation canvases."""

from __future__ import annotations

import ctypes
import io
import json
import math
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import cv2
import numpy as np
from PIL import Image

from .board_catalog import load_board_package

_PADDING_FRACTION = 0.01
_OPAQUE_BACKGROUND_MINIMUM_TOLERANCE = 12.0
_BACKGROUND_COLOR_QUANTUM = 16
_AT_FDCWD = -2
_RENAME_EXCHANGE = 0x2
_PIXEL_ROUNDING_EPSILON = 1e-9

Crop = tuple[int, int, int, int]


@dataclass(frozen=True)
class PresentationNormalizationResult:
    package_root: Path
    board_id: str
    original_width: int
    original_height: int
    width: int
    height: int
    crop: Crop
    hold_count: int
    changed: bool


def normalize_package_presentation(
    package_root: Path, *, write: bool
) -> PresentationNormalizationResult:
    """Return, and optionally commit, a tight presentation crop for one package.

    The crop is determined by foreground pixels and by all hold-piece frames in
    native presentation pixels.  Only the presentation aspect ratio and piece
    frames are reprojected; source geometry and hold metadata remain intact.
    """
    package = load_board_package(package_root)
    board_path = package.root / "board.json"
    primary_path = package.root / "assets" / "primary.png"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    image = _load_image(primary_path)
    original_width, original_height = image.size
    geometry_bounds = _geometry_bounds(document, original_width, original_height)
    crop = _crop_bounds(
        _visible_bounds(image), geometry_bounds, original_width, original_height
    )
    width, height = crop[2] - crop[0], crop[3] - crop[1]
    changed = crop != (0, 0, original_width, original_height)
    candidate_document = _reproject_document(
        document,
        crop=crop,
        original_width=original_width,
        original_height=original_height,
    )
    result = PresentationNormalizationResult(
        package_root=package.root,
        board_id=package.board.id,
        original_width=original_width,
        original_height=original_height,
        width=width,
        height=height,
        crop=crop,
        hold_count=len(document["holds"]),
        changed=changed,
    )
    if changed and write:
        candidate_png = _crop_png(image, crop)
        _validate_and_replace_package(package.root, candidate_document, candidate_png)
    return result


def _load_image(path: Path) -> Image.Image:
    try:
        with Image.open(path) as opened:
            opened.load()
            return opened.convert("RGBA")
    except (OSError, ValueError) as error:
        raise ValueError(f"assets/primary.png must be a decodable PNG image: {error}") from error


def _visible_bounds(image: Image.Image) -> Crop | None:
    pixels = np.asarray(image)
    alpha = pixels[:, :, 3]
    if np.any(alpha == 0):
        foreground = alpha > 0
    else:
        foreground = ~_opaque_background_mask(pixels[:, :, :3])
    return _mask_bounds(foreground)


def _opaque_background_mask(rgb: np.ndarray) -> np.ndarray:
    """Classify a border-connected opaque background without board identity.

    The dominant quantized border-color cluster supplies both the reference and
    spread.  Minority foreground pixels that touch an edge therefore cannot
    broaden the background tolerance.
    """
    border = np.concatenate((rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]))
    clusters, membership, counts = np.unique(
        border // _BACKGROUND_COLOR_QUANTUM,
        axis=0,
        return_inverse=True,
        return_counts=True,
    )
    del clusters
    background_samples = border[membership == int(np.argmax(counts))]
    reference = np.median(background_samples, axis=0)
    background_distance = np.linalg.norm(
        background_samples.astype(float) - reference,
        axis=1,
    )
    tolerance = max(
        _OPAQUE_BACKGROUND_MINIMUM_TOLERANCE,
        float(np.percentile(background_distance, 95)),
    )
    comparable = np.linalg.norm(rgb.astype(float) - reference, axis=2) <= tolerance
    return _border_connected(comparable)


def _border_connected(mask: np.ndarray) -> np.ndarray:
    _, labels = cv2.connectedComponents(mask.astype(np.uint8), connectivity=4)
    edge_labels = np.unique(
        np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1]))
    )
    return mask & np.isin(labels, edge_labels[edge_labels != 0])


def _mask_bounds(mask: np.ndarray) -> Crop | None:
    rows, columns = np.nonzero(mask)
    if not len(rows):
        return None
    return int(columns.min()), int(rows.min()), int(columns.max()) + 1, int(rows.max()) + 1


def _geometry_bounds(document: Mapping[str, Any], width: int, height: int) -> Crop:
    bounds: list[Crop] = []
    for hold in document["holds"]:
        for piece in hold["geometry"]:
            frame = piece["frame"]
            x, y, frame_width, frame_height = (
                _finite_frame_value(frame, "x"),
                _finite_frame_value(frame, "y"),
                _finite_frame_value(frame, "width"),
                _finite_frame_value(frame, "height"),
            )
            right, bottom = x + frame_width, y + frame_height
            if (
                x < 0
                or y < 0
                or frame_width <= 0
                or frame_height <= 0
                or right > 1
                or bottom > 1
            ):
                raise ValueError("geometry frame must be finite, positive, and within 0...1")
            bounds.append(
                (
                    _pixel_floor(x * width),
                    _pixel_floor(y * height),
                    _pixel_ceil(right * width),
                    _pixel_ceil(bottom * height),
                )
            )
    if not bounds:
        raise ValueError("board package has no geometry bounds")
    return (
        min(bound[0] for bound in bounds),
        min(bound[1] for bound in bounds),
        max(bound[2] for bound in bounds),
        max(bound[3] for bound in bounds),
    )


def _pixel_floor(value: float) -> int:
    return math.floor(value + _PIXEL_ROUNDING_EPSILON)


def _pixel_ceil(value: float) -> int:
    return math.ceil(value - _PIXEL_ROUNDING_EPSILON)


def _finite_frame_value(frame: Mapping[str, Any], key: str) -> float:
    value = float(frame[key])
    if not math.isfinite(value):
        raise ValueError("geometry frame must contain finite values")
    return value


def _crop_bounds(
    visible: Crop | None, geometry: Crop, width: int, height: int
) -> Crop:
    candidates = [geometry]
    if visible is not None:
        candidates.append(visible)
    content = (
        min(bound[0] for bound in candidates),
        min(bound[1] for bound in candidates),
        max(bound[2] for bound in candidates),
        max(bound[3] for bound in candidates),
    )
    padding = _fixed_point_padding(content)
    left = max(0, content[0] - padding)
    top = max(0, content[1] - padding)
    right = min(width, content[2] + padding)
    bottom = min(height, content[3] + padding)
    if left >= right or top >= bottom:
        raise ValueError("presentation crop must have positive dimensions")
    if _within_fixed_point_rounding(left, top, right, bottom, width, height):
        return 0, 0, width, height
    return left, top, right, bottom


def _fixed_point_padding(content: Crop) -> int:
    """Return the integer 1%-of-canvas margin that remains stable on rerun."""
    longest_content_dimension = max(content[2] - content[0], content[3] - content[1])
    padding = 0
    for _ in range(32):
        next_padding = math.ceil(
            _PADDING_FRACTION * (longest_content_dimension + 2 * padding)
        )
        if next_padding == padding:
            return padding
        padding = next_padding
    raise ValueError("presentation padding did not converge")


def _within_fixed_point_rounding(
    left: int, top: int, right: int, bottom: int, width: int, height: int
) -> bool:
    """Keep a canvas stable when raster bounding rounds by one edge pixel."""
    return left + top + (width - right) + (height - bottom) <= 1


def _reproject_document(
    document: dict[str, Any],
    *,
    crop: Crop,
    original_width: int,
    original_height: int,
) -> dict[str, Any]:
    left, top, right, bottom = crop
    width, height = right - left, bottom - top
    candidate = json.loads(json.dumps(document))
    candidate["aspectRatio"] = width / height
    for hold in candidate["holds"]:
        for piece in hold["geometry"]:
            frame = piece["frame"]
            original_x = _finite_frame_value(frame, "x") * original_width
            original_y = _finite_frame_value(frame, "y") * original_height
            original_frame_width = _finite_frame_value(frame, "width") * original_width
            original_frame_height = _finite_frame_value(frame, "height") * original_height
            transformed = {
                "x": (original_x - left) / width,
                "y": (original_y - top) / height,
                "width": original_frame_width / width,
                "height": original_frame_height / height,
            }
            if not _valid_transformed_frame(transformed):
                raise ValueError("presentation crop would create an invalid geometry frame")
            frame.clear()
            frame.update(transformed)
    return candidate


def _valid_transformed_frame(frame: Mapping[str, float]) -> bool:
    x, y, width, height = frame["x"], frame["y"], frame["width"], frame["height"]
    return (
        all(math.isfinite(value) for value in frame.values())
        and width > 0
        and height > 0
        and x >= 0
        and y >= 0
        and x + width <= 1
        and y + height <= 1
    )


def _crop_png(image: Image.Image, crop: Crop) -> bytes:
    output = io.BytesIO()
    image.crop(crop).save(output, format="PNG")
    return output.getvalue()


def _validate_and_replace_package(root: Path, document: Mapping[str, Any], png: bytes) -> None:
    parent = root.parent
    candidate = Path(tempfile.mkdtemp(prefix=f".{root.name}.presentation-", dir=parent))
    try:
        (candidate / "assets").mkdir()
        (candidate / "board.json").write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8"
        )
        (candidate / "assets" / "primary.png").write_bytes(png)
        load_board_package(candidate)
        _atomic_directory_exchange(root, candidate)
    finally:
        if candidate.exists():
            shutil.rmtree(candidate)


def _atomic_directory_exchange(root: Path, candidate: Path) -> None:
    """Atomically exchange two sibling directories or fail without writing.

    A pair of ordinary renames can leave the canonical package absent between
    operations.  Darwin and Linux expose an exchange primitive that changes
    both directory names in one filesystem operation.  Other platforms are
    deliberately unsupported rather than risking a mixed or missing package.
    """
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        operation = getattr(library, "renameatx_np", None)
    elif sys.platform.startswith("linux"):
        operation = getattr(library, "renameat2", None)
    else:
        operation = None
    if operation is None:
        raise OSError("atomic directory exchange is unavailable")
    operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    operation.restype = ctypes.c_int
    if operation(
        _AT_FDCWD,
        os.fsencode(root),
        _AT_FDCWD,
        os.fsencode(candidate),
        _RENAME_EXCHANGE,
    ) != 0:
        error = ctypes.get_errno()
        raise OSError(error, f"atomic directory exchange failed: {os.strerror(error)}")
