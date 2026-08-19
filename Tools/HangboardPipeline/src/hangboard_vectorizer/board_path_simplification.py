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
_MAX_EXACT_HAUSDORFF_WORK = 1_000_000
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
    complexity_capped: bool
    eligible_candidates: int
    evaluated_candidates: int
    rejected_candidates: int
    unsupported_pieces: int


@dataclass(frozen=True)
class HoldPathSimplificationResult:
    package_root: Path
    board_id: str
    pieces: tuple[HoldPieceSimplification, ...]

    @property
    def changed(self) -> bool:
        return any(piece.changed for piece in self.pieces)


@dataclass(frozen=True)
class NativeContourError:
    maximum_boundary_deviation_pixels: float
    symmetric_difference_ratio: float

    @property
    def passes(self) -> bool:
        return (
            self.maximum_boundary_deviation_pixels
            <= _MAX_BOUNDARY_DEVIATION_PIXELS
            and self.symmetric_difference_ratio
            <= _MAX_SYMMETRIC_DIFFERENCE_RATIO
        )


def measure_native_contour_error(
    before: Sequence[Point],
    after: Sequence[Point],
    *,
    width: int,
    height: int,
) -> NativeContourError:
    """Measure two native-pixel contours with the package simplifier gates."""
    first, second = list(before), list(after)
    if not _is_simple_polygon(first) or not _is_simple_polygon(second):
        raise ValueError("native contours must be simple nonzero polygons")
    if len(first) == len(second) and all(
        _same_point(first_point, second_point)
        for first_point, second_point in zip(first, second, strict=True)
    ):
        return NativeContourError(0.0, 0.0)
    if not _within_exact_hausdorff_work_cap(first, second):
        raise ValueError("native contour comparison exceeds exact complexity cap")
    return NativeContourError(
        maximum_boundary_deviation_pixels=_boundary_deviation(first, second),
        symmetric_difference_ratio=_symmetric_difference_ratio(
            first, second, width=width, height=height
        ),
    )


def simplify_native_contour(
    points: Sequence[Point], *, width: int, height: int
) -> tuple[Point, ...]:
    """Apply the existing exact reduction loop to one native-pixel contour."""
    original = list(points)
    if not _is_simple_polygon(original):
        raise ValueError("native contour must be a simple nonzero polygon")
    minimum_x = min(point[0] for point in original)
    maximum_x = max(point[0] for point in original)
    minimum_y = min(point[1] for point in original)
    maximum_y = max(point[1] for point in original)
    frame_width = maximum_x - minimum_x
    frame_height = maximum_y - minimum_y
    if frame_width <= _EPSILON or frame_height <= _EPSILON:
        raise ValueError("native contour must have positive bounds")
    frame = {
        "x": minimum_x / width,
        "y": minimum_y / height,
        "width": frame_width / width,
        "height": frame_height / height,
    }
    local = [
        (
            (point[0] - minimum_x) / frame_width,
            (point[1] - minimum_y) / frame_height,
        )
        for point in original
    ]
    simplified, complexity_capped, _statistics = _reduce_line_polygon(
        local, frame, width=width, height=height
    )
    if complexity_capped:
        return tuple(original)
    return tuple(_position(simplified, frame, width=width, height=height))


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
        return _unchanged(before, unsupported_pieces=1), None

    commands = _mixed_commands(shape)
    if commands is None:
        return _unchanged(before, unsupported_pieces=1), None
    if any(command["command"] in {"quad", "curve"} for command in commands):
        simplified, statistics = _reduce_mixed_commands(commands)
        after = _editable_point_count({"commands": simplified})
        if after >= before:
            return _unchanged(before, **statistics), None
        return {
            "before_editable_points": before,
            "after_editable_points": after,
            "maximum_boundary_deviation_pixels": 0.0,
            "symmetric_difference_ratio": 0.0,
            "changed": True,
            "complexity_capped": False,
            **statistics,
        }, {"type": "path", "commands": simplified}

    points = _line_contour(shape)
    if points is None or not _is_simple_polygon(points):
        return _unchanged(before), None

    frame = piece["frame"]
    positioned = _position(points, frame, width=width, height=height)
    simplified, complexity_capped, statistics = _reduce_line_polygon(
        points, frame, width=width, height=height
    )
    if complexity_capped:
        return _unchanged(before, complexity_capped=True, **statistics), None
    candidate = _position(simplified, frame, width=width, height=height)
    replacement = _path_shape(simplified)
    after = _editable_point_count(replacement)
    if after >= before or not _is_simple_polygon(simplified):
        return _unchanged(before, **statistics), None

    deviation = _boundary_deviation(positioned, candidate)
    difference = _symmetric_difference_ratio(positioned, candidate, width=width, height=height)
    if (
        deviation > _MAX_BOUNDARY_DEVIATION_PIXELS
        or difference > _MAX_SYMMETRIC_DIFFERENCE_RATIO
    ):
        return _unchanged(before, **statistics), None
    return {
        "before_editable_points": before,
        "after_editable_points": after,
        "maximum_boundary_deviation_pixels": deviation,
        "symmetric_difference_ratio": difference,
        "changed": True,
        "complexity_capped": False,
        **statistics,
        "unsupported_pieces": 0,
    }, replacement


def _unchanged(
    points: int,
    *,
    complexity_capped: bool = False,
    eligible_candidates: int = 0,
    evaluated_candidates: int = 0,
    rejected_candidates: int = 0,
    unsupported_pieces: int = 0,
) -> dict[str, Any]:
    return {
        "before_editable_points": points,
        "after_editable_points": points,
        "maximum_boundary_deviation_pixels": 0.0,
        "symmetric_difference_ratio": 0.0,
        "changed": False,
        "complexity_capped": complexity_capped,
        "eligible_candidates": eligible_candidates,
        "evaluated_candidates": evaluated_candidates,
        "rejected_candidates": rejected_candidates,
        "unsupported_pieces": unsupported_pieces,
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
    if sum(command.get("command") == "move" for command in commands) != 1:
        return None
    if sum(command.get("command") == "close" for command in commands) != 1:
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


def _mixed_commands(shape: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    commands = shape.get("commands")
    if not isinstance(commands, list) or len(commands) < 4:
        return None
    if commands[0].get("command") != "move" or commands[-1].get("command") != "close":
        return None
    if sum(command.get("command") == "move" for command in commands) != 1:
        return None
    if sum(command.get("command") == "close" for command in commands) != 1:
        return None
    if any(command.get("command") not in {"move", "line", "quad", "curve", "close"} for command in commands):
        return None
    return [dict(command) for command in commands]


def _reduce_mixed_commands(commands: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    current = commands
    statistics = {"eligible_candidates": 0, "evaluated_candidates": 0, "rejected_candidates": 0, "unsupported_pieces": 0}
    while True:
        changed = False
        for index in range(1, len(current) - 1):
            command = current[index]
            next_command = current[index + 1]
            start = _point(current[index - 1]["to"])
            end = _point(command["to"])
            if command["command"] == "line" and next_command["command"] == "line":
                next_end = _point(next_command["to"])
                if _point_is_between(start, end, next_end):
                    statistics["eligible_candidates"] += 1
                    statistics["evaluated_candidates"] += 1
                    del current[index]
                    changed = True
                    break
            if command["command"] in {"quad", "curve"} and _is_monotonic_line_curve(start, command, end):
                statistics["eligible_candidates"] += 1
                statistics["evaluated_candidates"] += 1
                current[index] = {"command": "line", "to": command["to"]}
                changed = True
                break
        if not changed:
            return current, statistics


def _point_is_between(start: Point, middle: Point, end: Point) -> bool:
    direction = _subtract(end, start)
    length_squared = _dot(direction, direction)
    if length_squared <= _EPSILON or abs(_cross(_subtract(middle, start), direction)) > _EPSILON:
        return False
    fraction = _dot(_subtract(middle, start), direction) / length_squared
    return _EPSILON < fraction < 1.0 - _EPSILON


def _is_monotonic_line_curve(start: Point, command: Mapping[str, Any], end: Point) -> bool:
    direction = _subtract(end, start)
    length_squared = _dot(direction, direction)
    if length_squared <= _EPSILON:
        return False
    control_names = ("control",) if command["command"] == "quad" else ("control1", "control2")
    fractions = []
    for name in control_names:
        control = _point(command[name])
        if abs(_cross(_subtract(control, start), direction)) > _EPSILON:
            return False
        fraction = _dot(_subtract(control, start), direction) / length_squared
        if not 0.0 <= fraction <= 1.0:
            return False
        fractions.append(fraction)
    return fractions == sorted(fractions)


def _point(value: Sequence[object]) -> Point:
    if len(value) != 2:
        raise ValueError("point must contain two values")
    return float(value[0]), float(value[1])


def _reduce_line_polygon(
    original: list[Point], frame: Mapping[str, Any], *, width: int, height: int
) -> tuple[list[Point], bool, dict[str, int]]:
    current = list(original)
    statistics = {"eligible_candidates": 0, "evaluated_candidates": 0, "rejected_candidates": 0}
    before = _position(original, frame, width=width, height=height)
    while len(current) > 3:
        removed = False
        for index in range(len(current)):
            candidate = current[:index] + current[index + 1 :]
            if not _is_simple_polygon(candidate) or not _same_winding(candidate, original):
                continue
            statistics["eligible_candidates"] += 1
            after = _position(candidate, frame, width=width, height=height)
            if not _within_exact_hausdorff_work_cap(before, after):
                return original, True, statistics
            statistics["evaluated_candidates"] += 1
            if (
                _boundary_deviation(before, after) <= _MAX_BOUNDARY_DEVIATION_PIXELS
                and _symmetric_difference_ratio(before, after, width=width, height=height)
                <= _MAX_SYMMETRIC_DIFFERENCE_RATIO
            ):
                current = candidate
                removed = True
                break
            statistics["rejected_candidates"] += 1
        if not removed:
            break
    return current, False, statistics


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


def _within_exact_hausdorff_work_cap(before: list[Point], after: list[Point]) -> bool:
    """Bound exact lower-envelope work before evaluating a candidate.

    The exact solver considers each source segment, every target projection
    interval, pairwise target-quadratic intersections, and target distances at
    each candidate location. This product is a conservative upper bound, so
    rejected paths never enter the potentially superlinear routine.
    """
    return (
        _directed_hausdorff_work(len(before), len(after))
        + _directed_hausdorff_work(len(after), len(before))
        <= _MAX_EXACT_HAUSDORFF_WORK
    )


def _directed_hausdorff_work(source_segments: int, target_segments: int) -> int:
    projection_intervals = 2 * target_segments + 1
    quadratic_pairs = target_segments * (target_segments - 1) // 2
    candidate_locations = 2 + 2 * quadratic_pairs
    return source_segments * projection_intervals * candidate_locations * target_segments


def _maximum_distance_to_segments(source: list[Point], target: list[Point]) -> float:
    target_segments = list(_segments(target))
    maximum = 0.0
    for start, end in _segments(source):
        maximum = max(maximum, _directed_segment_hausdorff(start, end, target_segments))
    return maximum


def _directed_segment_hausdorff(
    start: Point, end: Point, target_segments: list[tuple[Point, Point]]
) -> float:
    """Return the exact maximum distance from one segment to a segment union.

    On a source segment, squared distance to each target segment is piecewise
    quadratic. Its minimum can reach a maximum only at a projection-region
    boundary, an intersection between two such quadratics, or a source endpoint.
    Evaluating those finite candidates yields the directed Hausdorff distance
    without an unsafe sample interval.
    """
    breakpoints = {0.0, 1.0}
    vector = _subtract(end, start)
    for target_start, target_end in target_segments:
        target_vector = _subtract(target_end, target_start)
        target_length_squared = _dot(target_vector, target_vector)
        if target_length_squared <= _EPSILON:
            continue
        offset = _subtract(start, target_start)
        projection_start = _dot(offset, target_vector) / target_length_squared
        projection_slope = _dot(vector, target_vector) / target_length_squared
        if abs(projection_slope) <= _EPSILON:
            continue
        for target_projection in (0.0, 1.0):
            location = (target_projection - projection_start) / projection_slope
            if _EPSILON < location < 1.0 - _EPSILON:
                breakpoints.add(location)

    locations = sorted(breakpoints)
    maximum_squared = 0.0
    for lower, upper in zip(locations, locations[1:]):
        midpoint = (lower + upper) / 2
        quadratics = [
            _squared_distance_quadratic(start, vector, segment, midpoint)
            for segment in target_segments
        ]
        candidates = {lower, upper}
        for first_index, first in enumerate(quadratics):
            for second in quadratics[first_index + 1 :]:
                candidates.update(
                    root
                    for root in _quadratic_roots(
                        first[0] - second[0],
                        first[1] - second[1],
                        first[2] - second[2],
                    )
                    if lower < root < upper
                )
        for location in candidates:
            point = _add(start, _scale(vector, location))
            maximum_squared = max(
                maximum_squared,
                min(_squared_point_to_segment_distance(point, *segment) for segment in target_segments),
            )
    return math.sqrt(maximum_squared)


def _squared_distance_quadratic(
    start: Point, vector: Point, target: tuple[Point, Point], sample_location: float
) -> tuple[float, float, float]:
    target_start, target_end = target
    target_vector = _subtract(target_end, target_start)
    target_length_squared = _dot(target_vector, target_vector)
    offset = _subtract(start, target_start)
    projection = _dot(_add(offset, _scale(vector, sample_location)), target_vector) / target_length_squared
    if projection <= 0.0:
        return _squared_length_quadratic(offset, vector)
    if projection >= 1.0:
        return _squared_length_quadratic(_subtract(start, target_end), vector)
    cross_start = _cross(offset, target_vector)
    cross_vector = _cross(vector, target_vector)
    return (
        cross_vector * cross_vector / target_length_squared,
        2 * cross_start * cross_vector / target_length_squared,
        cross_start * cross_start / target_length_squared,
    )


def _squared_length_quadratic(offset: Point, vector: Point) -> tuple[float, float, float]:
    return _dot(vector, vector), 2 * _dot(offset, vector), _dot(offset, offset)


def _quadratic_roots(first: float, second: float, third: float) -> tuple[float, ...]:
    if abs(first) <= _EPSILON:
        if abs(second) <= _EPSILON:
            return ()
        return (-third / second,)
    discriminant = second * second - 4 * first * third
    if discriminant < -_EPSILON:
        return ()
    root = math.sqrt(max(0.0, discriminant))
    return ((-second - root) / (2 * first), (-second + root) / (2 * first))


def _point_to_segment_distance(point: Point, start: Point, end: Point) -> float:
    return math.sqrt(_squared_point_to_segment_distance(point, start, end))


def _squared_point_to_segment_distance(point: Point, start: Point, end: Point) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared <= _EPSILON:
        return _dot(_subtract(point, start), _subtract(point, start))
    fraction = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_squared))
    offset = (point[0] - start[0] - dx * fraction, point[1] - start[1] - dy * fraction)
    return _dot(offset, offset)


def _add(first: Point, second: Point) -> Point:
    return first[0] + second[0], first[1] + second[1]


def _subtract(first: Point, second: Point) -> Point:
    return first[0] - second[0], first[1] - second[1]


def _scale(point: Point, scalar: float) -> Point:
    return point[0] * scalar, point[1] * scalar


def _dot(first: Point, second: Point) -> float:
    return first[0] * second[0] + first[1] * second[1]


def _cross(first: Point, second: Point) -> float:
    return first[0] * second[1] - first[1] * second[0]


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
