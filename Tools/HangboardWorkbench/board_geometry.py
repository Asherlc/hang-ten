"""Exact, single-contour geometry used by the direct Workbench hold editor."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Iterable, Mapping


_ARITY = {"M": 2, "L": 2, "Q": 4, "C": 6, "Z": 0}
_TOKEN = re.compile(r"[MLQCZ]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
_EPSILON = 1e-9


class GeometryError(ValueError):
    """Raised when hold geometry is not one safe contiguous outline."""


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
        if (
            numbers["x"] < 0
            or numbers["y"] < 0
            or numbers["width"] <= 0
            or numbers["height"] <= 0
            or numbers["x"] + numbers["width"] > 1
            or numbers["y"] + numbers["height"] > 1
        ):
            raise GeometryError(f"{label} must stay inside the normalized canvas")
        return cls(**numbers)

    def to_json(self) -> dict[str, float]:
        return {
            "x": round(self.x, 12),
            "y": round(self.y, 12),
            "width": round(self.width, 12),
            "height": round(self.height, 12),
        }


@dataclass(frozen=True, slots=True)
class ClosedPath:
    data: str
    commands: tuple[tuple[str, tuple[float, ...]], ...]
    contour: tuple[tuple[float, float], ...]


def parse_closed_path(value: object, width: int, height: int, *, label: str = "hold path") -> ClosedPath:
    """Parse one absolute SVG-like closed path and enforce a simple outline."""
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
        raise GeometryError("canvas width must be a positive integer")
    if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
        raise GeometryError("canvas height must be a positive integer")
    if not isinstance(value, str) or not value.strip():
        raise GeometryError(f"{label} must be a non-empty string")

    raw = value.strip()
    tokens = _tokenize(raw, label)
    parsed: list[tuple[str, tuple[float, ...]]] = []
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
        for x, y in zip(values[::2], values[1::2], strict=True):
            if not 0 <= x <= width or not 0 <= y <= height:
                raise GeometryError(f"{label} coordinates must stay inside the canvas")
        parsed.append((command, tuple(values)))
        index += arity

    if not parsed or parsed[0][0] != "M" or parsed[-1][0] != "Z":
        raise GeometryError(f"{label} must be exactly one closed contour")
    if sum(command == "M" for command, _ in parsed) != 1 or sum(command == "Z" for command, _ in parsed) != 1:
        raise GeometryError(f"{label} must be exactly one closed contour")
    if any(command == "Z" for command, _ in parsed[:-1]):
        raise GeometryError(f"{label} must be exactly one closed contour")

    contour = _flatten(parsed, label)
    _validate_simple_contour(contour, label)
    return ClosedPath(
        " ".join(_render(command, values) for command, values in parsed),
        tuple(parsed),
        tuple((float(point[0]), float(point[1])) for point in contour),
    )


def normalized_frame_for_path(path: ClosedPath, width: int, height: int) -> NormalizedFrame:
    """Return the normalized frame that can serialize every path control point."""
    if width <= 0 or height <= 0:
        raise GeometryError("canvas dimensions must be positive")
    points = [
        (values[index], values[index + 1])
        for command, values in path.commands
        if command != "Z"
        for index in range(0, len(values), 2)
    ]
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
            commands.append({"command": "quad", "control": points[0], "to": points[1]})
        else:
            commands.append({"command": "curve", "control1": points[0], "control2": points[1], "to": points[2]})
    return frame, {"type": "path", "commands": commands}


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
            current = (values[0], values[1])
            points.append(current)
        elif command == "Q":
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
                points.append(start)
        else:  # The parser only leaves M, L, Q, C, Z here.
            raise GeometryError(f"{label} contains an unsupported command")
    return points


def _validate_simple_contour(points: list[tuple[float, float]], label: str) -> None:
    if len(points) < 4 or points[0] != points[-1]:
        raise GeometryError(f"{label} must be a closed contour")
    if len({(round(x, 12), round(y, 12)) for x, y in points[:-1]}) < 3:
        raise GeometryError(f"{label} must contain at least three unique points")
    segment_count = len(points) - 1
    for first in range(segment_count):
        if _same_point(points[first], points[first + 1]):
            raise GeometryError(f"{label} contains a zero-length segment")
        for second in range(first + 1, segment_count):
            if second == first + 1 or (first == 0 and second == segment_count - 1):
                continue
            if _segments_intersect(points[first], points[first + 1], points[second], points[second + 1]):
                raise GeometryError(f"{label} must not self-intersect")
    if abs(_signed_area(points)) <= _EPSILON:
        raise GeometryError(f"{label} must enclose area")


def _signed_area(points: list[tuple[float, float]]) -> float:
    return sum(
        points[index][0] * points[index + 1][1] - points[index + 1][0] * points[index][1]
        for index in range(len(points) - 1)
    ) / 2


def _segments_intersect(first: tuple[float, float], second: tuple[float, float], third: tuple[float, float], fourth: tuple[float, float]) -> bool:
    def orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    first_third = orientation(first, second, third)
    first_fourth = orientation(first, second, fourth)
    third_first = orientation(third, fourth, first)
    third_second = orientation(third, fourth, second)
    if ((first_third > _EPSILON and first_fourth < -_EPSILON) or (first_third < -_EPSILON and first_fourth > _EPSILON)) and ((third_first > _EPSILON and third_second < -_EPSILON) or (third_first < -_EPSILON and third_second > _EPSILON)):
        return True
    return any(
        abs(value) <= _EPSILON and _on_segment(a, b, point)
        for value, a, b, point in (
            (first_third, first, second, third),
            (first_fourth, first, second, fourth),
            (third_first, third, fourth, first),
            (third_second, third, fourth, second),
        )
    )


def _on_segment(first: tuple[float, float], second: tuple[float, float], point: tuple[float, float]) -> bool:
    return min(first[0], second[0]) - _EPSILON <= point[0] <= max(first[0], second[0]) + _EPSILON and min(first[1], second[1]) - _EPSILON <= point[1] <= max(first[1], second[1]) + _EPSILON


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
            if not 0 <= local_x <= 1 or not 0 <= local_y <= 1:
                raise GeometryError(f"{label}.shape commands must stay inside their frame")
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
