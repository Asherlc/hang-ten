"""Exact, single-contour geometry used by the direct Workbench hold editor."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import math
import re
from typing import Any


_ARITY = {"M": 2, "L": 2, "Q": 4, "C": 6, "Z": 0}
_TOKEN = re.compile(r"[MLQCZ]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
_EPSILON = 1e-9
_MAX_FLATTENED_SEGMENTS = 1_024

# The app quantizes flattened contour coordinates into an Int64 by scaling
# by 1e12 (see BoardPackageStore.swift's QuantizedBoardPoint), which traps
# outside Int64's range (roughly +/-9.2e6 once scaled back down). A control
# point only needs to be finite, but a pathologically thin declared frame can
# still blow up its frame-local coordinate here, so reject it well inside
# that margin before it reaches board.json.
_MAX_CONTROL_COORDINATE = 1_000_000.0


class GeometryError(ValueError):
    """Raised when hold geometry is not one safe contiguous contour."""


@dataclass(frozen=True, slots=True)
class NormalizedFrame:
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_json(cls, value: Mapping[str, Any], label: str = "frame") -> "NormalizedFrame":
        if set(value) != {"x", "y", "width", "height"}:
            raise GeometryError(f"{label} must contain x, y, width, and height")
        numbers: dict[str, float] = {}
        for key in ("x", "y", "width", "height"):
            raw = value[key]
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
                raise GeometryError(f"{label}.{key} must be finite")
            numbers[key] = float(raw)
        if numbers["width"] <= 0 or numbers["height"] <= 0:
            raise GeometryError(f"{label} width and height must be positive")
        return cls(**numbers)

    def to_json(self) -> dict[str, float]:
        precision = 12
        minimum_dimension = 10**-precision
        if not all(math.isfinite(value) for value in (self.x, self.y, self.width, self.height)):
            raise GeometryError("frame coordinates must be finite")
        if self.width <= 0 or self.height <= 0:
            raise GeometryError("frame width and height must be positive")
        x = round(self.x, precision)
        y = round(self.y, precision)
        width = max(round(self.width, precision), minimum_dimension)
        height = max(round(self.height, precision), minimum_dimension)
        return {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        }


@dataclass(frozen=True, slots=True)
class ClosedPath:
    data: str
    commands: tuple[tuple[str, tuple[float, ...]], ...]
    contour: tuple[tuple[float, float], ...]


def parse_closed_path(value: object, width: int, height: int, *, label: str = "hold path") -> ClosedPath:
    """Parse one absolute SVG-like closed path and enforce valid contour geometry."""
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
        raise GeometryError("canvas width must be a positive integer")
    if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
        raise GeometryError("canvas height must be a positive integer")
    if not isinstance(value, str) or not value.strip():
        raise GeometryError(f"{label} must be a non-empty string")

    raw = value.strip()
    tokens = _tokenize(raw, label)
    parsed: list[tuple[str, tuple[float, ...]]] = []
    projected_segments = 0
    start: tuple[float, float] | None = None
    current: tuple[float, float] | None = None
    index = 0
    while index < len(tokens):
        command = tokens[index]
        if command not in _ARITY:
            raise GeometryError(f"{label} requires an explicit command before coordinates")
        index += 1
        arity = _ARITY[command]
        if index + arity > len(tokens) or any(token in _ARITY for token in tokens[index : index + arity]):
            raise GeometryError(f"{label} has incomplete {command} coordinates")
        values: list[float] = []
        for token in tokens[index : index + arity]:
            number = float(token)
            if not math.isfinite(number):
                raise GeometryError(f"{label} coordinates must be finite")
            values.append(number)

        if command == "M":
            current = (values[0], values[1])
            if start is None:
                start = current
        elif command == "L":
            projected_segments += 1
            current = (values[0], values[1])
        elif command == "Q":
            projected_segments += 32
            current = (values[2], values[3])
        elif command == "C":
            projected_segments += 32
            current = (values[4], values[5])
        elif command == "Z" and start is not None and current is not None:
            projected_segments += not _same_point(current, start)
            current = start
        if projected_segments > _MAX_FLATTENED_SEGMENTS:
            raise GeometryError(
                f"{label} must contain no more than {_MAX_FLATTENED_SEGMENTS} flattened segments"
            )
        parsed.append((command, tuple(values)))
        index += arity

    if not parsed or parsed[0][0] != "M" or parsed[-1][0] != "Z":
        raise GeometryError(f"{label} must be exactly one closed contour")
    if sum(command == "M" for command, _ in parsed) != 1 or sum(command == "Z" for command, _ in parsed) != 1:
        raise GeometryError(f"{label} must be exactly one closed contour")
    if any(command == "Z" for command, _ in parsed[:-1]):
        raise GeometryError(f"{label} must be exactly one closed contour")

    contour = _flatten(parsed, label)
    _validate_contour(contour, label)
    return ClosedPath(
        " ".join(_render(command, values) for command, values in parsed),
        tuple(parsed),
        tuple((float(point[0]), float(point[1])) for point in contour),
    )


def normalized_frame_for_path(path: ClosedPath, width: int, height: int) -> NormalizedFrame:
    """Return the normalized frame tightly bounding the path's rendered contour.

    Uses the flattened curve, not raw control points: a Bezier control point
    routinely falls outside the curve it shapes, so a frame sized to contain
    every control point would not tightly bound what actually renders.
    """
    if width <= 0 or height <= 0:
        raise GeometryError("canvas dimensions must be positive")
    points = path.contour
    minimum_x = min(point[0] for point in points)
    maximum_x = max(point[0] for point in points)
    minimum_y = min(point[1] for point in points)
    maximum_y = max(point[1] for point in points)
    return NormalizedFrame(
        minimum_x / width,
        minimum_y / height,
        (maximum_x - minimum_x) / width,
        (maximum_y - minimum_y) / height,
    )


def union_normalized_frames(frames: Iterable[NormalizedFrame]) -> NormalizedFrame:
    """Return the normalized bounds containing every physical piece frame."""
    values = tuple(frames)
    if not values:
        raise GeometryError("hold geometry must be non-empty")
    minimum_x = min(frame.x for frame in values)
    minimum_y = min(frame.y for frame in values)
    maximum_x = max(frame.x + frame.width for frame in values)
    maximum_y = max(frame.y + frame.height for frame in values)
    return NormalizedFrame(
        minimum_x,
        minimum_y,
        maximum_x - minimum_x,
        maximum_y - minimum_y,
    )


def flattened_shape_bounds(commands: list[Any]) -> tuple[float, float, float, float]:
    """Return (min_x, max_x, min_y, max_y) of the rendered curve in a path
    shape's own normalized [0, 1] local coordinate space.

    Mirrors the Swift app's flattening exactly (32 samples per curve
    segment) so a piece's declared frame can be checked against what
    actually renders, not against its control points.
    """
    xs: list[float] = []
    ys: list[float] = []
    current: tuple[float, float] | None = None
    for raw in commands:
        name = raw.get("command") if isinstance(raw, Mapping) else None
        if name == "move":
            current = (raw["to"][0], raw["to"][1])
            xs.append(current[0])
            ys.append(current[1])
        elif name == "line":
            current = (raw["to"][0], raw["to"][1])
            xs.append(current[0])
            ys.append(current[1])
        elif name == "quad":
            control = (raw["control"][0], raw["control"][1])
            end = (raw["to"][0], raw["to"][1])
            for step in range(1, 33):
                t = step / 32
                inverse = 1 - t
                xs.append(inverse * inverse * current[0] + 2 * inverse * t * control[0] + t * t * end[0])
                ys.append(inverse * inverse * current[1] + 2 * inverse * t * control[1] + t * t * end[1])
            current = end
        elif name == "curve":
            control1 = (raw["control1"][0], raw["control1"][1])
            control2 = (raw["control2"][0], raw["control2"][1])
            end = (raw["to"][0], raw["to"][1])
            for step in range(1, 33):
                t = step / 32
                inverse = 1 - t
                xs.append(
                    inverse ** 3 * current[0]
                    + 3 * inverse * inverse * t * control1[0]
                    + 3 * inverse * t * t * control2[0]
                    + t ** 3 * end[0]
                )
                ys.append(
                    inverse ** 3 * current[1]
                    + 3 * inverse * inverse * t * control1[1]
                    + 3 * inverse * t * t * control2[1]
                    + t ** 3 * end[1]
                )
            current = end
        # "close" contributes no point beyond the start already recorded.
    return min(xs), max(xs), min(ys), max(ys)


def display_path_for_shape(
    frame: Mapping[str, Any], shape: Mapping[str, Any], width: int, height: int, *, label: str
) -> ClosedPath:
    """Translate canonical normalized physical geometry into editor pixels."""
    normalized = NormalizedFrame.from_json(frame, f"{label}.frame")
    shape_type = shape.get("type") if isinstance(shape, Mapping) else None
    if shape_type == "roundedRect":
        if set(shape) != {"type", "cornerRadiusFraction"}:
            raise GeometryError(f"{label}.shape is invalid")
        radius = _finite_number(shape["cornerRadiusFraction"], f"{label}.shape.cornerRadiusFraction")
        if not 0 <= radius <= 0.5:
            raise GeometryError(f"{label}.shape.cornerRadiusFraction must be in 0...0.5")
        commands = _rounded_rectangle(normalized, radius, width, height)
    elif shape_type == "path":
        if set(shape) != {"type", "commands"} or not isinstance(shape["commands"], list):
            raise GeometryError(f"{label}.shape is invalid")
        commands = _shape_commands(normalized, shape["commands"], width, height, label)
    else:
        raise GeometryError(f"{label}.shape.type is unsupported")
    return parse_closed_path(" ".join(_render(command, values) for command, values in commands), width, height, label=label)


def shape_for_path(path: ClosedPath, width: int, height: int) -> tuple[NormalizedFrame, dict[str, object]]:
    """Convert editor pixels back to a canonical frame-local path shape."""
    frame = normalized_frame_for_path(path, width, height)
    commands: list[dict[str, object]] = []
    for command, values in path.commands:
        if command == "Z":
            commands.append({"command": "close"})
            continue
        points = [
            [
                _local_coordinate(values[index], width, frame.x, frame.width),
                _local_coordinate(values[index + 1], height, frame.y, frame.height),
            ]
            for index in range(0, len(values), 2)
        ]
        if command in {"M", "L"}:
            commands.append({"command": "move" if command == "M" else "line", "to": points[0]})
        elif command == "Q":
            commands.append({"command": "quad", "control": _bounded_control(points[0]), "to": points[1]})
        else:
            commands.append({
                "command": "curve",
                "control1": _bounded_control(points[0]),
                "control2": _bounded_control(points[1]),
                "to": points[2],
            })
    return frame, {"type": "path", "commands": commands}


def _bounded_control(point: list[float]) -> list[float]:
    if any(abs(value) > _MAX_CONTROL_COORDINATE for value in point):
        raise GeometryError("shape control point is too far outside its frame")
    return point


def _tokenize(raw: str, label: str) -> list[str]:
    matches = list(_TOKEN.finditer(raw))
    cursor = 0
    tokens: list[str] = []
    for match in matches:
        if raw[cursor : match.start()].strip(" ,"):
            raise GeometryError(f"{label} contains an unsupported command or token")
        tokens.append(match.group())
        cursor = match.end()
    if raw[cursor:].strip(" ,") or not tokens:
        raise GeometryError(f"{label} contains an unsupported command or token")
    return tokens


def _flatten(commands: list[tuple[str, tuple[float, ...]]], label: str) -> list[tuple[float, float]]:
    start = (commands[0][1][0], commands[0][1][1])
    current = start
    points = [start]
    for command, values in commands[1:]:
        if command == "L":
            _ensure_flattened_budget(points, 1, label)
            current = (values[0], values[1])
            points.append(current)
        elif command == "Q":
            _ensure_flattened_budget(points, 32, label)
            control, end = (values[0], values[1]), (values[2], values[3])
            previous = current
            for step in range(1, 33):
                t = step / 32
                point = (
                    (1 - t) ** 2 * previous[0] + 2 * (1 - t) * t * control[0] + t**2 * end[0],
                    (1 - t) ** 2 * previous[1] + 2 * (1 - t) * t * control[1] + t**2 * end[1],
                )
                points.append(point)
            current = end
        elif command == "C":
            _ensure_flattened_budget(points, 32, label)
            control1, control2, end = (values[0], values[1]), (values[2], values[3]), (values[4], values[5])
            previous = current
            for step in range(1, 33):
                t = step / 32
                point = (
                    (1 - t) ** 3 * previous[0] + 3 * (1 - t) ** 2 * t * control1[0] + 3 * (1 - t) * t**2 * control2[0] + t**3 * end[0],
                    (1 - t) ** 3 * previous[1] + 3 * (1 - t) ** 2 * t * control1[1] + 3 * (1 - t) * t**2 * control2[1] + t**3 * end[1],
                )
                points.append(point)
            current = end
        elif command == "Z":
            if not _same_point(current, start):
                _ensure_flattened_budget(points, 1, label)
                points.append(start)
        else:  # The parser only leaves M, L, Q, C, Z here.
            raise GeometryError(f"{label} contains an unsupported command")
    return points


def _ensure_flattened_budget(
    points: list[tuple[float, float]], additional_segments: int, label: str
) -> None:
    if len(points) - 1 + additional_segments > _MAX_FLATTENED_SEGMENTS:
        raise GeometryError(
            f"{label} must contain no more than {_MAX_FLATTENED_SEGMENTS} flattened segments"
        )


def _validate_contour(points: list[tuple[float, float]], label: str) -> None:
    if len(points) < 4 or points[0] != points[-1]:
        raise GeometryError(f"{label} must be a closed contour")
    if len(points) - 1 > _MAX_FLATTENED_SEGMENTS:
        raise GeometryError(
            f"{label} must contain no more than {_MAX_FLATTENED_SEGMENTS} flattened segments"
        )
    canonical_points = _canonical_contour(points, label)
    if len({_quantized_point(point) for point in canonical_points[:-1]}) < 3:
        raise GeometryError(f"{label} must contain at least three unique points")
    segment_count = len(canonical_points) - 1
    for first in range(segment_count):
        if _same_point(canonical_points[first], canonical_points[first + 1]):
            raise GeometryError(f"{label} contains a zero-length segment")
    if not _has_filled_span(canonical_points):
        raise GeometryError(f"{label} must enclose area")


def _canonical_contour(
    points: list[tuple[float, float]],
    label: str,
) -> list[tuple[float, float]]:
    """Remove translation and independent axis scale from contour validation."""
    minimum_x = min(point[0] for point in points)
    maximum_x = max(point[0] for point in points)
    minimum_y = min(point[1] for point in points)
    maximum_y = max(point[1] for point in points)
    width = maximum_x - minimum_x
    height = maximum_y - minimum_y
    if not math.isfinite(width) or not math.isfinite(height):
        raise GeometryError(f"{label} coordinates are too large to represent")
    canonical = [
        (
            (point[0] - minimum_x) / width if width > 0 else 0.0,
            (point[1] - minimum_y) / height if height > 0 else 0.0,
        )
        for point in points
    ]
    if not all(math.isfinite(value) for point in canonical for value in point):
        raise GeometryError(f"{label} coordinates are too large to represent")
    return canonical


def _quantized_point(point: tuple[float, float]) -> tuple[int, int]:
    scale = 1_000_000_000_000
    return (
        math.floor(point[0] * scale + 0.5),
        math.floor(point[1] * scale + 0.5),
    )


def _has_filled_span(points: list[tuple[float, float]]) -> bool:
    """Return whether the contour has a non-zero-winding filled region.

    Shoelace area is the net signed area, which cancels for a symmetric
    bow-tie even though its two lobes visibly enclose area. Sweep between
    every vertex and segment-intersection height instead, where crossings
    have a stable order, and look for a span with non-zero winding.
    """
    segments = list(zip(points, points[1:]))
    if _segments_cancel_in_reverse_pairs(segments):
        return False

    vertex_heights = sorted({point[1] for point in points})
    intersection_heights: set[float] = set()
    for first_index, (first, second) in enumerate(segments):
        for third, fourth in segments[first_index + 1 :]:
            intersection_y = _segment_intersection_y(first, second, third, fourth)
            if intersection_y is not None:
                intersection_heights.add(intersection_y)

    sorted_intersections = sorted(intersection_heights)
    for lower, upper in zip(vertex_heights, vertex_heights[1:]):
        if upper - lower <= _EPSILON:
            continue
        first_event = bisect_right(sorted_intersections, lower)
        last_event = bisect_left(sorted_intersections, upper)
        previous = lower
        widest_gap = (lower, lower)
        for event in sorted_intersections[first_event:last_event]:
            if event - previous > widest_gap[1] - widest_gap[0]:
                widest_gap = (previous, event)
            previous = event
        if upper - previous > widest_gap[1] - widest_gap[0]:
            widest_gap = (previous, upper)
        if widest_gap[1] - widest_gap[0] <= _EPSILON:
            continue
        if _has_filled_span_at_height(segments, sum(widest_gap) / 2):
            return True
    return False


def _segments_cancel_in_reverse_pairs(
    segments: list[tuple[tuple[float, float], tuple[float, float]]],
) -> bool:
    balances: dict[tuple[tuple[int, int], tuple[int, int]], int] = {}
    for first, second in segments:
        quantized_first = _quantized_point(first)
        quantized_second = _quantized_point(second)
        if quantized_first < quantized_second:
            key = (quantized_first, quantized_second)
            direction = 1
        else:
            key = (quantized_second, quantized_first)
            direction = -1
        balances[key] = balances.get(key, 0) + direction
    return all(balance == 0 for balance in balances.values())


def _has_filled_span_at_height(
    segments: list[tuple[tuple[float, float], tuple[float, float]]],
    scan_y: float,
) -> bool:
    crossings: list[tuple[float, int]] = []
    for first, second in segments:
        if (first[1] <= scan_y < second[1]) or (second[1] <= scan_y < first[1]):
            x = first[0] + (scan_y - first[1]) * (second[0] - first[0]) / (second[1] - first[1])
            crossings.append((x, 1 if second[1] > first[1] else -1))
    crossings.sort()

    index = 0
    winding = 0
    while index < len(crossings):
        x = crossings[index][0]
        while index < len(crossings) and abs(crossings[index][0] - x) <= _EPSILON:
            winding += crossings[index][1]
            index += 1
        if index < len(crossings) and winding and crossings[index][0] - x > _EPSILON:
            return True
    return False


def _segment_intersection_y(
    first: tuple[float, float],
    second: tuple[float, float],
    third: tuple[float, float],
    fourth: tuple[float, float],
) -> float | None:
    first_delta = (second[0] - first[0], second[1] - first[1])
    second_delta = (fourth[0] - third[0], fourth[1] - third[1])
    denominator = first_delta[0] * second_delta[1] - first_delta[1] * second_delta[0]
    if abs(denominator) <= _EPSILON:
        return None
    origin_delta = (third[0] - first[0], third[1] - first[1])
    first_parameter = (origin_delta[0] * second_delta[1] - origin_delta[1] * second_delta[0]) / denominator
    second_parameter = (origin_delta[0] * first_delta[1] - origin_delta[1] * first_delta[0]) / denominator
    if not (-_EPSILON <= first_parameter <= 1 + _EPSILON and -_EPSILON <= second_parameter <= 1 + _EPSILON):
        return None
    return first[1] + first_parameter * first_delta[1]


def _same_point(first: tuple[float, float], second: tuple[float, float]) -> bool:
    return abs(first[0] - second[0]) <= _EPSILON and abs(first[1] - second[1]) <= _EPSILON


def _shape_commands(frame: NormalizedFrame, raw_commands: list[Any], width: int, height: int, label: str) -> list[tuple[str, tuple[float, ...]]]:
    commands: list[tuple[str, tuple[float, ...]]] = []
    for index, raw in enumerate(raw_commands):
        if not isinstance(raw, Mapping) or not isinstance(raw.get("command"), str):
            raise GeometryError(f"{label}.shape.commands[{index}] is invalid")
        name = raw["command"]
        fields = {
            "move": ("M", ("to",)),
            "line": ("L", ("to",)),
            "quad": ("Q", ("control", "to")),
            "curve": ("C", ("control1", "control2", "to")),
            "close": ("Z", ()),
        }
        if name not in fields or set(raw) != {"command", *fields[name][1]}:
            raise GeometryError(f"{label}.shape.commands[{index}] is invalid")
        command, point_keys = fields[name]
        values: list[float] = []
        for key in point_keys:
            point = raw[key]
            if not isinstance(point, list) or len(point) != 2:
                raise GeometryError(f"{label}.shape.commands[{index}].{key} is invalid")
            local_x = _finite_number(point[0], f"{label}.shape.commands[{index}].{key}[0]")
            local_y = _finite_number(point[1], f"{label}.shape.commands[{index}].{key}[1]")
            # Only a point the curve actually passes through ("to") must lie
            # within the frame; a Bezier control point only shapes the curve
            # between two such points and routinely falls outside it, but it
            # still must stay within the app's Int64 quantization range.
            if key == "to":
                if not 0 <= local_x <= 1 or not 0 <= local_y <= 1:
                    raise GeometryError(f"{label}.shape commands must stay inside their frame")
            elif abs(local_x) > _MAX_CONTROL_COORDINATE or abs(local_y) > _MAX_CONTROL_COORDINATE:
                raise GeometryError(f"{label}.shape control point is too far outside its frame")
            values.extend(((frame.x + local_x * frame.width) * width, (frame.y + local_y * frame.height) * height))
        commands.append((command, tuple(values)))
    return commands


def _rounded_rectangle(frame: NormalizedFrame, radius: float, width: int, height: int) -> list[tuple[str, tuple[float, ...]]]:
    x, y, horizontal, vertical = frame.x * width, frame.y * height, frame.width * width, frame.height * height
    corner = min(horizontal, vertical) * radius
    if corner <= _EPSILON:
        return [
            ("M", (x, y)),
            ("L", (x + horizontal, y)),
            ("L", (x + horizontal, y + vertical)),
            ("L", (x, y + vertical)),
            ("Z", ()),
        ]
    return _without_zero_length_lines([
        ("M", (x + corner, y)),
        ("L", (x + horizontal - corner, y)),
        ("Q", (x + horizontal, y, x + horizontal, y + corner)),
        ("L", (x + horizontal, y + vertical - corner)),
        ("Q", (x + horizontal, y + vertical, x + horizontal - corner, y + vertical)),
        ("L", (x + corner, y + vertical)),
        ("Q", (x, y + vertical, x, y + vertical - corner)),
        ("L", (x, y + corner)),
        ("Q", (x, y, x + corner, y)),
        ("Z", ()),
    ])


def _without_zero_length_lines(
    commands: list[tuple[str, tuple[float, ...]]]
) -> list[tuple[str, tuple[float, ...]]]:
    """Omit redundant straight spans from fully rounded pill and circle shapes."""
    result = [commands[0]]
    current = commands[0][1][-2:]
    for command, values in commands[1:]:
        if command == "L" and _same_point(current, values[-2:]):
            continue
        result.append((command, values))
        if command != "Z":
            current = values[-2:]
    return result


def _render(command: str, values: tuple[float, ...]) -> str:
    return " ".join((command, *(f"{value:.12g}" for value in values)))


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise GeometryError(f"{label} must be finite")
    return float(value)


def _local_coordinate(value: float, dimension: int, origin: float, size: float) -> float:
    coordinate = (value / dimension - origin) / size
    if abs(coordinate) <= _EPSILON:
        return 0.0
    if abs(coordinate - 1) <= _EPSILON:
        return 1.0
    return coordinate
