from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

import cv2
import numpy as np

from .display_paths import DisplayPath
from .geometry import Opening
from .models import ConversionError


RegionType = Literal["pocket", "edge", "rail", "jug", "sloper", "slot", "unknown"]
RegionSide = Literal["left", "right"] | None
RegionSource = Literal["automatic", "override", "template"]
RegionMetadataValue = str | int | float | bool


@dataclass(frozen=True, slots=True)
class GripRegion:
    """A grip polygon, plus optional disconnected component contours.

    ``contour`` remains the primary contour for existing consumers. When
    ``contours`` is non-empty it contains every component, including the primary.
    """

    id: str
    opening_id: str
    type: RegionType
    side: RegionSide
    contour: np.ndarray
    center: tuple[float, float]
    bbox: tuple[int, int, int, int]
    disabled: bool = False
    source: RegionSource = "automatic"
    contours: tuple[np.ndarray, ...] = ()
    label: str | None = None
    metadata: tuple[tuple[str, RegionMetadataValue], ...] = ()
    template_region_id: str | None = None
    display_path: DisplayPath | None = None


@dataclass(frozen=True, slots=True)
class RegionLayout:
    openings: tuple[Opening, ...]
    regions: tuple[GripRegion, ...]


def build_regions(
    openings: tuple[Opening, ...],
    board_width: int,
    board_height: int,
    *,
    rail_aspect_ratio: float = 3.0,
    rail_width_ratio: float = 0.18,
    row_tolerance_ratio: float = 0.06,
) -> RegionLayout:
    """Classify detected openings and give their grip regions stable row-major IDs."""
    identified = _identify_openings(openings, board_height, row_tolerance_ratio)
    regions: list[GripRegion] = []
    for opening in identified:
        region_type = _classify(
            opening, board_width, rail_aspect_ratio, rail_width_ratio
        )
        if region_type == "rail":
            for side, contour in _split_rail(opening):
                center, bbox = _contour_geometry(contour)
                regions.append(
                    GripRegion(
                        id=f"{opening.id}-rail-{side}",
                        opening_id=opening.id,
                        type="rail",
                        side=side,
                        contour=contour,
                        center=center,
                        bbox=bbox,
                    )
                )
        else:
            regions.append(
                GripRegion(
                    id=f"{opening.id}-{region_type}",
                    opening_id=opening.id,
                    type=region_type,
                    side=None,
                    contour=opening.contour,
                    center=opening.center,
                    bbox=opening.bbox,
                )
            )
    return RegionLayout(openings=identified, regions=tuple(regions))


def _identify_openings(
    openings: tuple[Opening, ...], board_height: int, row_tolerance_ratio: float
) -> tuple[Opening, ...]:
    rows: list[list[Opening]] = []
    means: list[float] = []
    tolerance = row_tolerance_ratio * board_height
    for opening in sorted(openings, key=lambda item: (item.center[1], item.center[0])):
        if rows and abs(opening.center[1] - means[-1]) <= tolerance:
            row = rows[-1]
            row.append(opening)
            means[-1] = sum(item.center[1] for item in row) / len(row)
        else:
            rows.append([opening])
            means.append(opening.center[1])

    identified: list[Opening] = []
    for row_number, row in enumerate(rows, start=1):
        for hole_number, opening in enumerate(
            sorted(row, key=lambda item: item.center[0]), start=1
        ):
            identified.append(
                replace(opening, id=f"r{row_number:02d}-h{hole_number:02d}")
            )
    return tuple(identified)


def _classify(
    opening: Opening,
    board_width: int,
    rail_aspect_ratio: float,
    rail_width_ratio: float,
) -> RegionType:
    _, _, width, height = opening.bbox
    if opening.area <= 0 or width <= 0 or height <= 0:
        return "unknown"
    aspect_ratio = width / height
    if aspect_ratio < 1.6:
        return "pocket"
    if aspect_ratio < rail_aspect_ratio:
        return "slot"
    if board_width > 0 and width / board_width >= rail_width_ratio:
        return "rail"
    return "slot"


def _split_rail(
    opening: Opening,
) -> tuple[tuple[Literal["left", "right"], np.ndarray], ...]:
    x, y, width, height = opening.bbox
    mask = np.zeros((height, width), dtype=np.uint8)
    local_contour = np.rint(opening.contour - np.array([x, y])).astype(np.int32)
    cv2.drawContours(mask, [local_contour], -1, 1, thickness=-1)
    split = width // 2
    halves = (("left", mask[:, :split], 0), ("right", mask[:, split:], split))
    pieces: list[tuple[Literal["left", "right"], np.ndarray]] = []
    for side, half, offset in halves:
        contours, _ = cv2.findContours(half, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise ConversionError(f"rail opening {opening.id} has no {side} component")
        contour = max(contours, key=cv2.contourArea).reshape(-1, 2).astype(float)
        contour += np.array([x + offset, y])
        pieces.append((side, contour))
    return tuple(pieces)


def _contour_geometry(
    contour: np.ndarray,
) -> tuple[tuple[float, float], tuple[int, int, int, int]]:
    integer_contour = np.rint(contour).astype(np.int32)
    x, y, width, height = cv2.boundingRect(integer_contour)
    moments = cv2.moments(integer_contour)
    if moments["m00"]:
        center = (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])
    else:
        center = (x + width / 2, y + height / 2)
    return center, (x, y, width, height)
