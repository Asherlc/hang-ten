from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
import math
import re
from typing import Any

import cv2
import numpy as np

from .regions import GripRegion, RegionSource, RegionType


_SAFE_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]*\Z")
_REGION_TYPES = {"pocket", "edge", "rail", "jug", "sloper", "slot", "unknown"}
_WorkingRegion = tuple[str | None, GripRegion]


def apply_overrides(
    regions: tuple[GripRegion, ...],
    document: Mapping[str, object],
    board_width: int,
    board_height: int,
) -> tuple[GripRegion, ...]:
    """Apply a validated version-1 override document to grip regions."""
    if (
        not isinstance(document, Mapping)
        or type(document.get("version")) is not int
        or document.get("version") != 1
    ):
        raise ValueError("override document version must be 1")
    if board_width <= 0 or board_height <= 0:
        raise ValueError("board dimensions must be positive")

    working: list[_WorkingRegion] = [(region.id, region) for region in regions]
    source_index = _index_regions(regions)
    rename = _mapping(document.get("rename", {}), "rename")
    disable = _sequence(document.get("disable", ()), "disable")
    split = _mapping(document.get("split", {}), "split")
    merges = _sequence(document.get("merge", ()), "merge")
    additions = _sequence(document.get("add", ()), "add")

    targeted: set[str] = set()
    for selector in rename:
        _claim_selector(selector, source_index, targeted)
    for selector in disable:
        _claim_selector(selector, source_index, targeted)
    for selector in split:
        _claim_selector(selector, source_index, targeted)
    parsed_merges: list[tuple[list[str], str]] = []
    for merge in merges:
        entry = _mapping(merge, "merge entry")
        selectors = list(_sequence(entry.get("ids"), "merge ids"))
        if len(selectors) < 2:
            raise ValueError("merge ids must contain at least two region IDs")
        output_id = _validated_id(entry.get("id"))
        for selector in selectors:
            _claim_selector(selector, source_index, targeted)
        parsed_merges.append((selectors, output_id))

    for selector, output_id in rename.items():
        output_id = _validated_id(output_id)
        index = _find_source(working, selector)
        source_id, region = working[index]
        working[index] = (source_id, replace(region, id=output_id))

    for selector in disable:
        index = _find_source(working, selector)
        source_id, region = working[index]
        working[index] = (source_id, replace(region, disabled=True))

    for selector, pieces_value in split.items():
        pieces = _sequence(pieces_value, "split pieces")
        index = _find_source(working, selector)
        _, source = working.pop(index)
        parsed_pieces: list[tuple[str, float, float]] = []
        for piece in pieces:
            entry = _mapping(piece, "split entry")
            piece_id = _validated_id(entry.get("id"))
            start, end = _validated_range(entry.get("xRange"))
            parsed_pieces.append((piece_id, start, end))
        if not parsed_pieces:
            raise ValueError("split pieces must not be empty")
        replacements = [
            _split_region(source, piece_id, start, end, board_width, board_height)
            for piece_id, start, end in parsed_pieces
        ]
        working[index:index] = [(None, region) for region in replacements]

    for selectors, output_id in parsed_merges:
        selected = [source_index[selector] for selector in selectors]
        insertion_index = min(
            _find_source(working, selector) for selector in selectors
        )
        selector_set = set(selectors)
        working = [entry for entry in working if entry[0] not in selector_set]
        working.insert(
            insertion_index,
            (None, _merge_regions(selected, output_id, board_width, board_height)),
        )

    for addition in additions:
        entry = _mapping(addition, "add entry")
        region_id = _validated_id(entry.get("id"))
        region_type = entry.get("type")
        if region_type not in _REGION_TYPES:
            raise ValueError(
                "add type must be pocket, edge, rail, jug, sloper, slot, or unknown"
            )
        polygon = _validated_polygon(entry.get("polygon"))
        contour = np.array(
            [[x * board_width, y * board_height] for x, y in polygon], dtype=float
        )
        center, bbox = _contour_geometry(contour)
        working.append(
            (
                None,
                GripRegion(
                    id=region_id,
                    opening_id="",
                    type=region_type,
                    side=None,
                    contour=contour,
                    center=center,
                    bbox=bbox,
                    source="override",
                ),
            )
        )

    result = tuple(region for _, region in working)
    _index_regions(result)
    return result


def _index_regions(regions: Sequence[GripRegion]) -> dict[str, GripRegion]:
    index: dict[str, GripRegion] = {}
    for region in regions:
        region_id = _validated_id(region.id)
        if region_id in index:
            raise ValueError(f"duplicate region ID: {region_id}")
        index[region_id] = region
    return index


def _claim_selector(
    selector: object,
    source_index: Mapping[str, GripRegion],
    targeted: set[str],
) -> None:
    selector = _validated_id(selector)
    if selector not in source_index:
        raise ValueError(f"unknown region selector: {selector}")
    if selector in targeted:
        raise ValueError(f"region has multiple operations: {selector}")
    targeted.add(selector)


def _find_source(regions: Sequence[_WorkingRegion], selector: str) -> int:
    for index, (source_id, _) in enumerate(regions):
        if source_id == selector:
            return index
    raise ValueError(f"unknown region selector: {selector}")


def _split_region(
    region: GripRegion,
    output_id: str,
    start: float,
    end: float,
    board_width: int,
    board_height: int,
) -> GripRegion:
    mask = _region_mask(region, board_width, board_height)
    x, _, width, _ = region.bbox
    left = x + int(round(start * width))
    right = x + int(round(end * width))
    clipped = np.zeros_like(mask)
    clipped[:, max(0, left) : min(board_width, right)] = mask[
        :, max(0, left) : min(board_width, right)
    ]
    contours = _mask_contours(clipped, "split xRange produced an empty region")
    contour = _primary_contour(contours)
    center, bbox = _mask_geometry(clipped)
    return replace(
        region,
        id=output_id,
        contour=contour,
        center=center,
        bbox=bbox,
        contours=contours if len(contours) > 1 else (),
        source="override",
        template_region_id=None,
        display_path=None,
    )


def _merge_regions(
    regions: Sequence[GripRegion],
    output_id: str,
    board_width: int,
    board_height: int,
) -> GripRegion:
    mask = np.zeros((board_height, board_width), dtype=np.uint8)
    for region in regions:
        mask |= _region_mask(region, board_width, board_height)
    contours = _mask_contours(mask, "merge produced an empty region")
    contour = _primary_contour(contours)
    center, bbox = _mask_geometry(mask)
    first = regions[0]
    region_type: RegionType = (
        first.type if all(region.type == first.type for region in regions) else "unknown"
    )
    has_single_opening = bool(first.opening_id) and all(
        region.opening_id == first.opening_id for region in regions
    )
    opening_id = first.opening_id if has_single_opening else ""
    source: RegionSource = (
        first.source
        if has_single_opening
        and all(region.source == first.source for region in regions)
        else "override"
    )
    return GripRegion(
        id=output_id,
        opening_id=opening_id,
        type=region_type,
        side=None,
        contour=contour,
        center=center,
        bbox=bbox,
        disabled=all(region.disabled for region in regions),
        source=source,
        contours=contours if len(contours) > 1 else (),
        template_region_id=None,
        display_path=None,
    )


def _region_mask(region: GripRegion, board_width: int, board_height: int) -> np.ndarray:
    mask = np.zeros((board_height, board_width), dtype=np.uint8)
    contours = region.contours or (region.contour,)
    integer_contours = [
        np.rint(contour).astype(np.int32).reshape(-1, 1, 2)
        for contour in contours
    ]
    cv2.drawContours(mask, integer_contours, -1, 1, thickness=-1)
    return mask


def _primary_contour(contours: Sequence[np.ndarray]) -> np.ndarray:
    return max(
        contours,
        key=lambda contour: cv2.contourArea(contour.astype(np.float32)),
    )


def _mask_contours(mask: np.ndarray, empty_message: str) -> tuple[np.ndarray, ...]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError(empty_message)
    components = [contour.reshape(-1, 2).astype(float) for contour in contours]
    components.sort(key=lambda contour: cv2.boundingRect(contour.astype(np.int32))[:2])
    return tuple(components)


def _mask_geometry(
    mask: np.ndarray,
) -> tuple[tuple[float, float], tuple[int, int, int, int]]:
    points = cv2.findNonZero(mask)
    if points is None:
        raise ValueError("cannot measure an empty region mask")
    x, y, width, height = cv2.boundingRect(points)
    moments = cv2.moments(mask, binaryImage=True)
    center = (
        float(moments["m10"] / moments["m00"]),
        float(moments["m01"] / moments["m00"]),
    )
    return center, (x, y, width, height)


def _contour_geometry(
    contour: np.ndarray,
) -> tuple[tuple[float, float], tuple[int, int, int, int]]:
    integer_contour = np.rint(contour).astype(np.int32)
    x, y, width, height = cv2.boundingRect(integer_contour)
    moments = cv2.moments(integer_contour)
    if moments["m00"]:
        center = (
            float(moments["m10"] / moments["m00"]),
            float(moments["m01"] / moments["m00"]),
        )
    else:
        center = (x + width / 2, y + height / 2)
    return center, (x, y, width, height)


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _sequence(value: object, name: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be an array")
    return value


def _validated_id(value: object) -> str:
    if not isinstance(value, str) or _SAFE_ID.fullmatch(value) is None:
        raise ValueError(f"invalid region ID: {value!r}")
    return value


def _validated_range(value: object) -> tuple[float, float]:
    values = _sequence(value, "split xRange")
    if len(values) != 2 or not all(_is_number(item) for item in values):
        raise ValueError("split xRange must contain two numbers")
    start, end = (float(item) for item in values)
    if not 0.0 <= start < end <= 1.0:
        raise ValueError("split xRange must satisfy 0 <= start < end <= 1")
    return start, end


def _validated_polygon(value: object) -> list[tuple[float, float]]:
    points = _sequence(value, "add polygon")
    if len(points) < 3:
        raise ValueError("add polygon must have at least three points")
    polygon: list[tuple[float, float]] = []
    for point in points:
        coordinates = _sequence(point, "add polygon point")
        if len(coordinates) != 2 or not all(_is_number(item) for item in coordinates):
            raise ValueError("add polygon points must contain two numbers")
        x, y = (float(item) for item in coordinates)
        if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0:
            raise ValueError("add polygon coordinates must be within 0..1")
        polygon.append((x, y))
    if len(set(polygon)) != len(polygon):
        raise ValueError("add polygon must not repeat vertices")
    twice_area = sum(
        x * next_y - next_x * y
        for (x, y), (next_x, next_y) in zip(
            polygon, polygon[1:] + polygon[:1], strict=True
        )
    )
    if math.isclose(twice_area, 0.0, abs_tol=1e-12):
        raise ValueError("add polygon must have non-zero area")
    return polygon


def _is_number(value: object) -> bool:
    return (
        isinstance(value, (int, float, np.integer, np.floating))
        and not isinstance(value, (bool, np.bool_))
        and math.isfinite(float(value))
    )
