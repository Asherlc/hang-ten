"""Validation and immutable storage for safe smooth product display paths."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import NoReturn

import numpy as np

from .models import ConversionError


_ARITY = {"M": 2, "L": 2, "Q": 4, "C": 6, "Z": 0}
_TOKEN = re.compile(r"[MLQCZ]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


@dataclass(frozen=True, slots=True)
class DisplayPath:
    data: str
    commands: tuple[str, ...]
    coordinates: tuple[tuple[float, float], ...]

    def scaled(self, scale: float) -> str:
        if not math.isfinite(scale) or scale <= 0:
            raise ValueError("display-path scale must be positive and finite")
        tokens = self.data.split()
        output: list[str] = []
        for token in tokens:
            if token in _ARITY:
                output.append(token)
            else:
                output.append(f"{float(token) * scale:.12g}")
        return " ".join(output)


def flatten_display_path(
    path: DisplayPath, *, scale: float = 1.0, curve_steps: int = 32
) -> np.ndarray:
    """Flatten one absolute closed display path into a scaled float64 contour."""
    contours = flatten_display_subpaths(
        path, scale=scale, curve_steps=curve_steps
    )
    if len(contours) != 1:
        raise ValueError("display path must contain one contour")
    return contours[0]


def flatten_display_subpaths(
    path: DisplayPath, *, scale: float = 1.0, curve_steps: int = 32
) -> tuple[np.ndarray, ...]:
    """Flatten every closed subpath into an independently scaled contour."""
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("display-path scale must be positive and finite")
    if (
        isinstance(curve_steps, bool)
        or not isinstance(curve_steps, int)
        or curve_steps < 2
    ):
        raise ValueError("display-path curve_steps must be an integer of at least 2")

    tokens = path.data.split()
    contours: list[np.ndarray] = []
    points: list[np.ndarray] | None = None
    current: np.ndarray | None = None
    start: np.ndarray | None = None
    index = 0

    def read_point() -> np.ndarray:
        nonlocal index
        if index + 2 > len(tokens):
            raise ValueError("display path has incomplete coordinates")
        try:
            point = np.asarray(
                (float(tokens[index]), float(tokens[index + 1])), dtype=np.float64
            )
        except ValueError as error:
            raise ValueError("display path has invalid coordinates") from error
        index += 2
        if not np.isfinite(point).all():
            raise ValueError("display path coordinates must be finite")
        return point

    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command == "M":
            if points is not None:
                raise ValueError("display path subpath must close before the next M")
            current = read_point()
            start = current.copy()
            points = [current.copy()]
        elif command == "L":
            if current is None or points is None:
                raise ValueError("display path must start with M")
            current = read_point()
            points.append(current.copy())
        elif command == "Q":
            if current is None or points is None:
                raise ValueError("display path must start with M")
            control = read_point()
            end = read_point()
            p0 = current
            for step in range(1, curve_steps + 1):
                t = step / curve_steps
                point = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * control + t**2 * end
                points.append(point)
            current = end
        elif command == "C":
            if current is None or points is None:
                raise ValueError("display path must start with M")
            control_1 = read_point()
            control_2 = read_point()
            end = read_point()
            p0 = current
            for step in range(1, curve_steps + 1):
                t = step / curve_steps
                point = (
                    (1 - t) ** 3 * p0
                    + 3 * (1 - t) ** 2 * t * control_1
                    + 3 * (1 - t) * t**2 * control_2
                    + t**3 * end
                )
                points.append(point)
            current = end
        elif command == "Z":
            if current is None or start is None or points is None:
                raise ValueError("display path must contain closed subpaths")
            points.append(start.copy())
            contour = np.asarray(points, dtype=np.float64)
            if (
                contour.ndim != 2
                or contour.shape[1] != 2
                or not np.isfinite(contour).all()
            ):
                raise ValueError(
                    "display path must produce finite two-dimensional points"
                )
            if not np.array_equal(contour[0], contour[-1]):
                raise ValueError("display path contour must be closed")
            if np.unique(contour[:-1], axis=0).shape[0] < 3:
                raise ValueError(
                    "display path contour must contain at least three unique points"
                )
            contours.append(contour * scale)
            current, start, points = None, None, None
        else:
            raise ValueError("display path contains an unsupported command")

    if points is not None or not contours:
        raise ValueError("display path must contain closed subpaths")
    return tuple(contours)


def parse_display_path(
    value: object,
    field: str,
    width: int,
    height: int,
    *,
    allow_linear_segments: bool = False,
) -> DisplayPath | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        _invalid(field, "must be a non-empty string")

    raw = value.strip()
    matches = list(_TOKEN.finditer(raw))
    cursor = 0
    tokens: list[str] = []
    for match in matches:
        if raw[cursor : match.start()].strip(" ,"):
            _invalid(field, "contains an unsupported command or token")
        tokens.append(match.group())
        cursor = match.end()
    if raw[cursor:].strip(" ,"):
        _invalid(field, "contains an unsupported command or token")
    if not tokens or tokens[0] != "M":
        _invalid(field, "must start with M")
    if tokens[-1] != "Z":
        _invalid(field, "must close with Z")

    commands: list[str] = []
    coordinates: list[tuple[float, float]] = []
    normalized: list[str] = []
    index = 0
    while index < len(tokens):
        command = tokens[index]
        if command not in _ARITY:
            _invalid(field, "requires an explicit command before coordinates")
        commands.append(command)
        normalized.append(command)
        index += 1
        arity = _ARITY[command]
        if index + arity > len(tokens):
            _invalid(field, f"has incomplete {command} coordinates")
        values: list[float] = []
        for token in tokens[index : index + arity]:
            if token in _ARITY:
                _invalid(field, f"has incomplete {command} coordinates")
            number = float(token)
            if not math.isfinite(number):
                _invalid(field, "coordinates must be finite")
            values.append(number)
            normalized.append(f"{number:.12g}")
        for x, y in zip(values[::2], values[1::2], strict=True):
            if not 0 <= x <= width or not 0 <= y <= height:
                _invalid(field, "coordinates must stay inside the canonical view box")
            coordinates.append((x, y))
        index += arity

    subpath_open = False
    subpath_count = 0
    for command in commands:
        if command == "M":
            if subpath_open:
                _invalid(field, "must close each subpath before the next M")
            subpath_open = True
            subpath_count += 1
        elif command == "Z":
            if not subpath_open:
                _invalid(field, "contains a Z without an open subpath")
            subpath_open = False
        elif not subpath_open:
            _invalid(field, "must start each subpath with M")
    if subpath_open or not subpath_count or commands.count("Z") != subpath_count:
        _invalid(field, "must contain closed subpaths")
    if not allow_linear_segments and not any(
        command in ("Q", "C") for command in commands
    ):
        _invalid(field, "must contain a curved segment")
    return DisplayPath(" ".join(normalized), tuple(commands), tuple(coordinates))


def _invalid(field: str, message: str) -> NoReturn:
    raise ConversionError(f"invalid product template: {field} {message}")
