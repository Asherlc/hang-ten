"""Deterministically reduce safe, low-point line hold paths."""

from __future__ import annotations

import json
import math
import os
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image, ImageChops, ImageDraw

from .board_catalog import load_board_package

_SUPER_SAMPLE = 4
_MAX_BOUNDARY_DEVIATION_PIXELS = 1.0
_MAX_SYMMETRIC_DIFFERENCE_RATIO = 0.0025
_EPSILON = 1e-9

Point = tuple[float, float]


@dataclass(frozen=True)
class HoldPieceSimplification:
    hold_id: str
    piece_index: int
    before_editable_points: int
    after_editable_points: int
    maximum_boundary_deviation_pixels: float
    symmetric_difference_ratio: float
    changed: bool


@dataclass(frozen=True)
class HoldPathSimplificationResult:
    package_root: Path
    board_id: str
    pieces: tuple[HoldPieceSimplification, ...]

    @property
    def changed(self) -> bool:
        return any(piece.changed for piece in self.pieces)


def simplify_package_hold_paths(
    package_root: Path, *, write: bool
) -> HoldPathSimplificationResult:
    """Safely simplify one complete board package's line-only hold paths.

    Every candidate is measured after mapping its piece frame to the native
    presentation pixels.  Curves and rounded rectangles deliberately remain
    untouched: a polygon is accepted only when it strictly lowers the number
    of editable endpoints and controls.
    """
    package = load_board_package(package_root)
    board_path = package.root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    width, height = _png_dimensions(package.root / "assets" / "primary.png")

    reports: list[HoldPieceSimplification] = []
    for hold in document["holds"]:
        for piece_index, piece in enumerate(hold["geometry"]):
            report, replacement = _simplify_piece(piece, width=width, height=height)
            reports.append(
                HoldPieceSimplification(
                    hold_id=hold["id"],
                    piece_index=piece_index,
                    **report,
                )
            )
            if replacement is not None:
                piece["shape"] = replacement

    result = HoldPathSimplificationResult(
        package_root=package.root,
        board_id=package.board.id,
        pieces=tuple(reports),
    )
    if write and result.changed:
        _write_json_atomically(board_path, document)
    return result


def _simplify_piece(
    piece: Mapping[str, Any], *, width: int, height: int
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    shape = piece["shape"]
    before = _editable_point_count(shape)
    if shape.get("type") != "path":
        return _unchanged(before), None

    points = _line_contour(shape)
    if points is None or not _is_simple_polygon(points):
        return _unchanged(before), None

    frame = piece["frame"]
    positioned = _position(points, frame, width=width, height=height)
    simplified = _reduce_line_polygon(points, frame, width=width, height=height)
    candidate = _position(simplified, frame, width=width, height=height)
    replacement = _path_shape(simplified)
    after = _editable_point_count(replacement)
    if after >= before or not _is_simple_polygon(simplified):
        return _unchanged(before), None

    deviation = _boundary_deviation(positioned, candidate)
    difference = _symmetric_difference_ratio(positioned, candidate, width=width, height=height)
    if (
        deviation > _MAX_BOUNDARY_DEVIATION_PIXELS
        or difference > _MAX_SYMMETRIC_DIFFERENCE_RATIO
    ):
        return _unchanged(before), None
    return {
        "before_editable_points": before,
        "after_editable_points": after,
        "maximum_boundary_deviation_pixels": deviation,
        "symmetric_difference_ratio": difference,
        "changed": True,
    }, replacement


def _unchanged(points: int) -> dict[str, Any]:
    return {
        "before_editable_points": points,
        "after_editable_points": points,
        "maximum_boundary_deviation_pixels": 0.0,
        "symmetric_difference_ratio": 0.0,
        "changed": False,
    }


def _editable_point_count(shape: Mapping[str, Any]) -> int:
    return sum(
        int("to" in command)
        + int("control" in command)
        + int("control1" in command)
        + int("control2" in command)
        for command in shape.get("commands", ())
    )


def _line_contour(shape: Mapping[str, Any]) -> list[Point] | None:
    commands = shape.get("commands")
    if not isinstance(commands, list) or len(commands) < 4:
        return None
    if commands[0].get("command") != "move" or commands[-1].get("command") != "close":
        return None
    if any(command.get("command") not in {"move", "line", "close"} for command in commands):
        return None
    if any(command.get("command") == "close" for command in commands[1:-1]):
        return None
    try:
        points = [_point(commands[0]["to"])]
        points.extend(_point(command["to"]) for command in commands[1:-1])
    except (KeyError, TypeError, ValueError):
        return None
    normalized: list[Point] = []
    for point in points:
        if not normalized or not _same_point(point, normalized[-1]):
            normalized.append(point)
    if len(normalized) > 1 and _same_point(normalized[0], normalized[-1]):
        normalized.pop()
    return normalized if len(normalized) >= 3 else None


def _point(value: Sequence[object]) -> Point:
    if len(value) != 2:
        raise ValueError("point must contain two values")
    return float(value[0]), float(value[1])


def _reduce_line_polygon(
    original: list[Point], frame: Mapping[str, Any], *, width: int, height: int
) -> list[Point]:
    current = list(original)
    while len(current) > 3:
        removed = False
        for index in range(len(current)):
            candidate = current[:index] + current[index + 1 :]
            if not _is_simple_polygon(candidate) or not _same_winding(candidate, original):
                continue
            before = _position(original, frame, width=width, height=height)
            after = _position(candidate, frame, width=width, height=height)
            if (
                _boundary_deviation(before, after) <= _MAX_BOUNDARY_DEVIATION_PIXELS
                and _symmetric_difference_ratio(before, after, width=width, height=height)
                <= _MAX_SYMMETRIC_DIFFERENCE_RATIO
            ):
                current = candidate
                removed = True
                break
        if not removed:
            break
    return current


def _path_shape(points: Iterable[Point]) -> dict[str, Any]:
    anchors = list(points)
    return {
        "type": "path",
        "commands": [
            {"command": "move", "to": list(anchors[0])},
            *({"command": "line", "to": list(point)} for point in anchors[1:]),
            {"command": "close"},
        ],
    }


def _position(
    points: Iterable[Point], frame: Mapping[str, Any], *, width: int, height: int
) -> list[Point]:
    x, y = float(frame["x"]), float(frame["y"])
    frame_width, frame_height = float(frame["width"]), float(frame["height"])
    return [
        ((x + point_x * frame_width) * width, (y + point_y * frame_height) * height)
        for point_x, point_y in points
    ]


def _is_simple_polygon(points: list[Point]) -> bool:
    if len(points) < 3 or abs(_winding(points)) <= _EPSILON:
        return False
    segments = list(_segments(points))
    for first_index, (first_start, first_end) in enumerate(segments):
        for second_index in range(first_index + 1, len(segments)):
            if second_index in {first_index + 1, (first_index - 1) % len(segments)}:
                continue
            if first_index == 0 and second_index == len(segments) - 1:
                continue
            if _segments_intersect(first_start, first_end, *segments[second_index]):
                return False
    return True


def _segments(points: list[Point]) -> Iterable[tuple[Point, Point]]:
    return zip(points, points[1:] + points[:1])


def _segments_intersect(first_start: Point, first_end: Point, second_start: Point, second_end: Point) -> bool:
    def orientation(a: Point, b: Point, c: Point) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    first = orientation(first_start, first_end, second_start)
    second = orientation(first_start, first_end, second_end)
    third = orientation(second_start, second_end, first_start)
    fourth = orientation(second_start, second_end, first_end)
    return first * second <= _EPSILON and third * fourth <= _EPSILON


def _winding(points: list[Point]) -> float:
    return sum(
        start[0] * end[1] - end[0] * start[1]
        for start, end in _segments(points)
    ) / 2


def _same_winding(first: list[Point], second: list[Point]) -> bool:
    return _winding(first) * _winding(second) > _EPSILON


def _boundary_deviation(before: list[Point], after: list[Point]) -> float:
    return max(
        _maximum_distance_to_segments(before, after),
        _maximum_distance_to_segments(after, before),
    )


def _maximum_distance_to_segments(source: list[Point], target: list[Point]) -> float:
    maximum = 0.0
    target_segments = list(_segments(target))
    for start, end in _segments(source):
        length = math.dist(start, end)
        for sample in range(max(1, math.ceil(length * _SUPER_SAMPLE)) + 1):
            fraction = sample / max(1, math.ceil(length * _SUPER_SAMPLE))
            point = (start[0] + (end[0] - start[0]) * fraction, start[1] + (end[1] - start[1]) * fraction)
            maximum = max(maximum, min(_point_to_segment_distance(point, *segment) for segment in target_segments))
    return maximum


def _point_to_segment_distance(point: Point, start: Point, end: Point) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared <= _EPSILON:
        return math.dist(point, start)
    fraction = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_squared))
    return math.dist(point, (start[0] + dx * fraction, start[1] + dy * fraction))


def _symmetric_difference_ratio(before: list[Point], after: list[Point], *, width: int, height: int) -> float:
    raster_size = (width * _SUPER_SAMPLE, height * _SUPER_SAMPLE)
    difference = ImageChops.logical_xor(_rasterize(before, raster_size), _rasterize(after, raster_size))
    return difference.histogram()[255] / (raster_size[0] * raster_size[1])


def _rasterize(points: list[Point], size: tuple[int, int]) -> Image.Image:
    image = Image.new("1", size, 0)
    ImageDraw.Draw(image).polygon(
        [(round(x * _SUPER_SAMPLE), round(y * _SUPER_SAMPLE)) for x, y in points], fill=1
    )
    return image


def _same_point(first: Point, second: Point) -> bool:
    return math.dist(first, second) <= _EPSILON


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        header = file.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"invalid primary PNG: {path}")
    return struct.unpack(">II", header[16:24])


def _write_json_atomically(path: Path, document: Mapping[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(document, file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
