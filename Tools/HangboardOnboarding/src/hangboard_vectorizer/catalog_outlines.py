"""Editable hold-outline schema helpers and contour normalization."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image


Point = tuple[float, float]


def _point(value: object, field: str) -> Point:
    if not isinstance(value, Sequence) or isinstance(value, str) or len(value) != 2:
        raise ValueError(f"{field} must be a coordinate pair")
    x = _finite_float(value[0], f"{field}[0]")
    y = _finite_float(value[1], f"{field}[1]")
    return (x, y)


def _finite_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


@dataclass(frozen=True, slots=True)
class OutlineCommand:
    command: str
    to: Point
    controls: tuple[Point, Point] | None = None

    def __post_init__(self) -> None:
        if self.command not in {"M", "L", "C"}:
            raise ValueError("outline command must be M, L, or C")
        _point(self.to, "to")
        if self.command == "C":
            if self.controls is None or len(self.controls) != 2:
                raise ValueError("cubic outline commands require two control points")
            _point(self.controls[0], "controls[0]")
            _point(self.controls[1], "controls[1]")
        elif self.controls is not None:
            raise ValueError("only cubic outline commands accept control points")

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {"command": self.command, "to": list(self.to)}
        if self.controls is not None:
            payload["controls"] = [list(control) for control in self.controls]
        return payload

    @classmethod
    def from_json(cls, payload: object) -> "OutlineCommand":
        root = _mapping(payload, "outline command")
        controls = root.get("controls")
        parsed_controls = None
        if controls is not None:
            if (
                not isinstance(controls, Sequence)
                or isinstance(controls, str)
                or len(controls) != 2
            ):
                raise ValueError("outline command controls must contain two points")
            parsed_controls = (
                _point(controls[0], "controls[0]"),
                _point(controls[1], "controls[1]"),
            )
        return cls(
            command=str(root.get("command")),
            to=_point(root.get("to"), "to"),
            controls=parsed_controls,
        )


@dataclass(frozen=True, slots=True)
class OutlinePath:
    commands: tuple[OutlineCommand, ...]
    closed: bool

    def to_json(self) -> dict[str, object]:
        return {
            "closed": self.closed,
            "commands": [command.to_json() for command in self.commands],
        }

    @classmethod
    def from_json(cls, payload: object) -> "OutlinePath":
        root = _mapping(payload, "outline path")
        raw_commands = root.get("commands")
        if not isinstance(raw_commands, Sequence) or isinstance(raw_commands, str):
            raise ValueError("outline path commands must be a sequence")
        closed = root.get("closed")
        if not isinstance(closed, bool):
            raise ValueError("outline path closed flag must be a boolean")
        return cls(
            commands=tuple(OutlineCommand.from_json(item) for item in raw_commands),
            closed=closed,
        )

    def all_coordinates(self) -> tuple[float, ...]:
        values: list[float] = []
        for command in self.commands:
            if command.controls is not None:
                for control in command.controls:
                    values.extend(control)
            values.extend(command.to)
        return tuple(values)


@dataclass(frozen=True, slots=True)
class HoldOutline:
    hold_id: str
    path: OutlinePath

    def __post_init__(self) -> None:
        if not self.hold_id:
            raise ValueError("hold_id must be non-empty")

    def to_json(self) -> dict[str, object]:
        return {"holdId": self.hold_id, "path": self.path.to_json()}

    @classmethod
    def from_json(cls, payload: object) -> "HoldOutline":
        root = _mapping(payload, "hold outline")
        hold_id = root.get("holdId")
        if not isinstance(hold_id, str) or not hold_id:
            raise ValueError("holdId must be a non-empty string")
        return cls(hold_id=hold_id, path=OutlinePath.from_json(root.get("path")))


@dataclass(frozen=True, slots=True)
class CatalogOutlineDocument:
    schema_version: int
    source_image: str
    source_width: int
    source_height: int
    holds: tuple[HoldOutline, ...]

    def __post_init__(self) -> None:
        _positive_int(self.schema_version, "schema_version")
        if not self.source_image:
            raise ValueError("source_image must be non-empty")
        _positive_int(self.source_width, "source_width")
        _positive_int(self.source_height, "source_height")
        if not self.holds:
            raise ValueError("holds must not be empty")

    def to_json(self) -> dict[str, object]:
        return {
            "schemaVersion": self.schema_version,
            "sourceImage": self.source_image,
            "sourceWidth": self.source_width,
            "sourceHeight": self.source_height,
            "holds": [hold.to_json() for hold in self.holds],
        }

    @classmethod
    def from_json(cls, payload: object) -> "CatalogOutlineDocument":
        root = _mapping(payload, "catalog outline document")
        raw_holds = root.get("holds")
        if not isinstance(raw_holds, Sequence) or isinstance(raw_holds, str):
            raise ValueError("holds must be a sequence")
        source_image = root.get("sourceImage")
        if not isinstance(source_image, str) or not source_image:
            raise ValueError("sourceImage must be a non-empty string")
        return cls(
            schema_version=_positive_int(root.get("schemaVersion"), "schemaVersion"),
            source_image=source_image,
            source_width=_positive_int(root.get("sourceWidth"), "sourceWidth"),
            source_height=_positive_int(root.get("sourceHeight"), "sourceHeight"),
            holds=tuple(HoldOutline.from_json(item) for item in raw_holds),
        )


def path_bounds(path: OutlinePath) -> tuple[float, float, float, float]:
    if not path.commands:
        raise ValueError("outline path must not be empty")
    xs: list[float] = []
    ys: list[float] = []
    for command in path.commands:
        if command.controls is not None:
            for control in command.controls:
                xs.append(control[0])
                ys.append(control[1])
        xs.append(command.to[0])
        ys.append(command.to[1])
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


def validate_catalog_document(
    document: CatalogOutlineDocument, source_path: Path | None = None
) -> None:
    if document.schema_version != 1:
        raise ValueError("schemaVersion must be 1")
    if document.source_width <= 0 or document.source_height <= 0:
        raise ValueError("source dimensions must be positive")
    seen_ids: set[str] = set()
    for hold in document.holds:
        if hold.hold_id in seen_ids:
            raise ValueError("hold IDs must be unique")
        seen_ids.add(hold.hold_id)
        _validate_path(hold.path)
    if source_path is not None:
        try:
            with Image.open(source_path) as image:
                width, height = image.size
        except OSError as error:
            raise ValueError(f"source dimensions could not be read: {source_path}") from error
        if (width, height) != (document.source_width, document.source_height):
            raise ValueError("source dimensions do not match the source image")


def _validate_path(path: OutlinePath) -> None:
    if not path.closed:
        raise ValueError("outline path must be closed")
    commands = path.commands
    if not commands or commands[0].command != "M":
        raise ValueError("outline path must begin with a single M command")
    if sum(command.command == "M" for command in commands) != 1:
        raise ValueError("outline path must contain exactly one M command")
    drawing_commands = commands[1:]
    if len(drawing_commands) < 2:
        raise ValueError("outline path must be closed with at least two drawing segments")
    if any(command.command == "M" for command in drawing_commands):
        raise ValueError("outline path may only move once")
    for value in path.all_coordinates():
        if not 0.0 <= value <= 1.0:
            raise ValueError("outline coordinates must stay on the normalized canvas")
        if not math.isfinite(value):
            raise ValueError("outline coordinates must be finite")
    start = commands[0].to
    if drawing_commands[-1].to != start:
        raise ValueError("outline path must end where it started to stay closed")
    _, _, width, height = path_bounds(path)
    if width <= 0.0 or height <= 0.0:
        raise ValueError("outline path bounds must describe a non-degenerate closed shape")


def write_catalog_document(document: CatalogOutlineDocument, output_path: Path) -> None:
    validate_catalog_document(document)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(document.to_json(), indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(output_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def normalize_contour(contour: np.ndarray, width: int, height: int) -> OutlinePath:
    points = np.asarray(contour, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3:
        raise ValueError("contour must be an Nx2 array with at least three points")
    if not np.isfinite(points).all():
        raise ValueError("contour points must be finite")
    _positive_int(width, "width")
    _positive_int(height, "height")
    if np.allclose(points[0], points[-1]):
        points = points[:-1]
    if len(points) < 3:
        raise ValueError("contour must contain at least three unique points")

    smaller_extent = float(max(min(np.ptp(points[:, 0]), np.ptp(points[:, 1])), 1.0))
    tolerance = smaller_extent * 0.12
    corner_indices = _persistent_corner_indices(points, tolerance)
    normalized = points / np.array([width, height], dtype=np.float64)

    commands: list[OutlineCommand] = [OutlineCommand("M", _tuple_point(normalized[0]))]
    for start_index, end_index in zip(
        corner_indices, corner_indices[1:] + corner_indices[:1], strict=False
    ):
        span = _span(points, start_index, end_index)
        destination = _tuple_point(span[-1] / np.array([width, height], dtype=np.float64))
        if len(span) <= 2:
            commands.append(OutlineCommand("L", destination))
            continue
        control_1 = _tuple_point(span[1] / np.array([width, height], dtype=np.float64))
        control_2 = _tuple_point(span[-2] / np.array([width, height], dtype=np.float64))
        commands.append(
            OutlineCommand("C", destination, controls=(control_1, control_2))
        )
    return OutlinePath(commands=tuple(commands), closed=True)


def _tuple_point(value: np.ndarray) -> Point:
    return (float(value[0]), float(value[1]))


def _persistent_corner_indices(points: np.ndarray, tolerance: float) -> list[int]:
    angles = [_turn_angle(points, index) for index in range(len(points))]
    indices = [0]
    for index in range(1, len(points)):
        if angles[index] >= 135.0 and _point_distance(points[index], points[indices[-1]]) >= tolerance:
            indices.append(index)
    ranked = sorted(range(1, len(points)), key=lambda index: angles[index], reverse=True)
    for index in ranked:
        if index not in indices:
            indices.append(index)
        if len(indices) >= 3:
            break
    return sorted(set(indices))


def _turn_angle(points: np.ndarray, index: int) -> float:
    previous = points[index - 1]
    current = points[index]
    following = points[(index + 1) % len(points)]
    incoming = previous - current
    outgoing = following - current
    denominator = float(np.linalg.norm(incoming) * np.linalg.norm(outgoing))
    if denominator == 0.0:
        return 180.0
    cosine = float(np.clip(np.dot(incoming, outgoing) / denominator, -1.0, 1.0))
    return math.degrees(math.acos(cosine))


def _point_distance(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right))


def _span(points: np.ndarray, start_index: int, end_index: int) -> np.ndarray:
    if start_index < end_index:
        return points[start_index + 1 : end_index + 1]
    if start_index > end_index:
        return np.vstack((points[start_index + 1 :], points[: end_index + 1]))
    raise ValueError("contour span requires distinct corner indices")
