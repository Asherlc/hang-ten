"""Editable hold-outline schema helpers and contour normalization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image


Point = tuple[float, float]
Bounds = tuple[float, float, float, float]

_KINDS = frozenset({"pocket", "edge", "rail", "jug", "sloper"})
_EPSILON = 1e-9


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _finite_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


def _point(value: object, field: str) -> Point:
    if not isinstance(value, Sequence) or isinstance(value, str) or len(value) != 2:
        raise ValueError(f"{field} must be a coordinate pair")
    return (
        _finite_float(value[0], f"{field}[0]"),
        _finite_float(value[1], f"{field}[1]"),
    )


def _bounds(value: object, field: str) -> Bounds:
    if not isinstance(value, Sequence) or isinstance(value, str) or len(value) != 4:
        raise ValueError(f"{field} must be a four-number bounds tuple")
    return (
        _finite_float(value[0], f"{field}[0]"),
        _finite_float(value[1], f"{field}[1]"),
        _finite_float(value[2], f"{field}[2]"),
        _finite_float(value[3], f"{field}[3]"),
    )


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise ValueError(f"{field} must be a list of strings")
    items = tuple(_string(item, field) for item in value)
    return items


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
        command = _string(root.get("command"), "outline command.command")
        controls = root.get("controls")
        parsed_controls: tuple[Point, Point] | None = None
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
        return cls(command=command, to=_point(root.get("to"), "to"), controls=parsed_controls)


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
    id: str
    label: str
    kind: str
    confidence: float
    bounds: Bounds
    path: OutlinePath
    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        _string(self.id, "id")
        _string(self.label, "label")
        if self.kind not in _KINDS:
            raise ValueError("kind is unsupported")
        if not 0.0 <= self.confidence <= 1.0 or not math.isfinite(self.confidence):
            raise ValueError("confidence must be finite and normalized")
        _bounds(self.bounds, "bounds")

    def to_json(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "confidence": self.confidence,
            "bounds": list(self.bounds),
            "path": self.path.to_json(),
            "notes": list(self.notes),
        }

    @classmethod
    def from_json(cls, payload: object) -> "HoldOutline":
        root = _mapping(payload, "outline")
        raw_notes = root.get("notes", ())
        return cls(
            id=_string(root.get("id"), "outline.id"),
            label=_string(root.get("label"), "outline.label"),
            kind=_string(root.get("kind"), "outline.kind"),
            confidence=_finite_float(root.get("confidence"), "outline.confidence"),
            bounds=_bounds(root.get("bounds"), "outline.bounds"),
            path=OutlinePath.from_json(root.get("path")),
            notes=_string_tuple(raw_notes, "outline.notes"),
        )


@dataclass(frozen=True, slots=True)
class CatalogOutlineDocument:
    schema_version: int
    source_image: str
    canvas_width: int
    canvas_height: int
    coordinate_space: str
    references: tuple[Mapping[str, object], ...]
    outlines: tuple[HoldOutline, ...]

    def __post_init__(self) -> None:
        _positive_int(self.schema_version, "schema_version")
        _string(self.source_image, "source_image")
        _positive_int(self.canvas_width, "canvas_width")
        _positive_int(self.canvas_height, "canvas_height")
        if self.coordinate_space != "normalized":
            raise ValueError('coordinate_space must be "normalized"')
        if not self.outlines:
            raise ValueError("outlines must not be empty")
        self._validate_references()

    def _validate_references(self) -> None:
        for index, reference in enumerate(self.references):
            if not isinstance(reference, Mapping):
                raise ValueError(f"references[{index}] must be an object")
            _string(reference.get("title"), f"references[{index}].title")
            _string(reference.get("url"), f"references[{index}].url")
            _string_tuple(reference.get("hints", ()), f"references[{index}].hints")

    def to_json(self) -> dict[str, object]:
        return {
            "schemaVersion": self.schema_version,
            "sourceImage": self.source_image,
            "canvas": {"width": self.canvas_width, "height": self.canvas_height},
            "coordinateSpace": self.coordinate_space,
            "references": [
                {
                    "title": str(reference["title"]),
                    "url": str(reference["url"]),
                    "hints": list(_string_tuple(reference.get("hints", ()), "reference.hints")),
                }
                for reference in self.references
            ],
            "outlines": [outline.to_json() for outline in self.outlines],
        }

    @classmethod
    def from_json(cls, payload: object) -> "CatalogOutlineDocument":
        root = _mapping(payload, "catalog outline document")
        canvas = _mapping(root.get("canvas"), "canvas")
        raw_references = root.get("references", ())
        if not isinstance(raw_references, Sequence) or isinstance(raw_references, str):
            raise ValueError("references must be a sequence")
        raw_outlines = root.get("outlines")
        if not isinstance(raw_outlines, Sequence) or isinstance(raw_outlines, str):
            raise ValueError("outlines must be a sequence")
        return cls(
            schema_version=_positive_int(root.get("schemaVersion"), "schemaVersion"),
            source_image=_string(root.get("sourceImage"), "sourceImage"),
            canvas_width=_positive_int(canvas.get("width"), "canvas.width"),
            canvas_height=_positive_int(canvas.get("height"), "canvas.height"),
            coordinate_space=_string(root.get("coordinateSpace"), "coordinateSpace"),
            references=tuple(
                {
                    "title": _string(_mapping(item, "reference").get("title"), "reference.title"),
                    "url": _string(_mapping(item, "reference").get("url"), "reference.url"),
                    "hints": _string_tuple(_mapping(item, "reference").get("hints", ()), "reference.hints"),
                }
                for item in raw_references
            ),
            outlines=tuple(HoldOutline.from_json(item) for item in raw_outlines),
        )


def path_bounds(path: OutlinePath) -> Bounds:
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
    if document.coordinate_space != "normalized":
        raise ValueError('coordinateSpace must be "normalized"')
    if document.canvas_width <= 0 or document.canvas_height <= 0:
        raise ValueError("source dimensions must be positive")
    seen_ids: set[str] = set()
    for outline in document.outlines:
        if outline.id in seen_ids:
            raise ValueError("outline IDs must be unique")
        seen_ids.add(outline.id)
        _validate_path(outline.path)
        _validate_bounds(outline.bounds, outline.path)
    if source_path is not None:
        try:
            with Image.open(source_path) as image:
                width, height = image.size
        except OSError as error:
            raise ValueError(f"source dimensions could not be read: {source_path}") from error
        if (width, height) != (document.canvas_width, document.canvas_height):
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
        if not math.isfinite(value):
            raise ValueError("outline coordinates must be finite")
        if not 0.0 <= value <= 1.0:
            raise ValueError("outline coordinates must stay in normalized space")
    if drawing_commands[-1].to != commands[0].to:
        raise ValueError("outline path must end where it started to stay closed")
    _, _, width, height = path_bounds(path)
    if width <= 0.0 or height <= 0.0:
        raise ValueError("outline path bounds must describe a non-degenerate closed shape")


def _validate_bounds(bounds: Bounds, path: OutlinePath) -> None:
    x, y, width, height = bounds
    for value in bounds:
        if not 0.0 <= value <= 1.0 or not math.isfinite(value):
            raise ValueError("outline bounds must stay in normalized space")
    if width <= 0.0 or height <= 0.0:
        raise ValueError("outline bounds must be non-degenerate")
    path_x, path_y, path_width, path_height = path_bounds(path)
    path_max_x = path_x + path_width
    path_max_y = path_y + path_height
    bounds_max_x = x + width
    bounds_max_y = y + height
    if (
        x > path_x + _EPSILON
        or y > path_y + _EPSILON
        or bounds_max_x + _EPSILON < path_max_x
        or bounds_max_y + _EPSILON < path_max_y
    ):
        raise ValueError("outline bounds must contain all normalized path coordinates")


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

    scale = np.array([width, height], dtype=np.float64)
    smaller_extent = float(max(min(np.ptp(points[:, 0]), np.ptp(points[:, 1])), 1.0))
    tolerance = smaller_extent * 0.12
    corner_indices = _persistent_corner_indices(points, tolerance)

    commands: list[OutlineCommand] = [OutlineCommand("M", _tuple_point(points[0] / scale))]
    for start_index, end_index in zip(
        corner_indices, corner_indices[1:] + corner_indices[:1], strict=False
    ):
        span = _span(points, start_index, end_index)
        if len(span) == 1:
            commands.append(OutlineCommand("L", _tuple_point(span[0] / scale)))
            continue

        smooth_points = span[:-1]
        corner_point = span[-1]
        smooth_end = smooth_points[-1]
        control_1, control_2 = _cubic_controls(points[start_index], smooth_end, corner_point)
        commands.append(
            OutlineCommand(
                "C",
                _tuple_point(smooth_end / scale),
                controls=(_tuple_point(control_1 / scale), _tuple_point(control_2 / scale)),
            )
        )
        commands.append(OutlineCommand("L", _tuple_point(corner_point / scale)))
    return OutlinePath(commands=tuple(commands), closed=True)


def _persistent_corner_indices(points: np.ndarray, tolerance: float) -> list[int]:
    angles = [_turn_angle(points, index) for index in range(len(points))]
    indices = [0]
    for index in range(1, len(points)):
        if angles[index] <= 100.0 and _point_distance(points[index], points[indices[-1]]) >= tolerance:
            indices.append(index)
    ranked = sorted(range(1, len(points)), key=lambda index: angles[index])
    for index in ranked:
        if index not in indices:
            indices.append(index)
        if len(indices) >= 4:
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


def _cubic_controls(start: np.ndarray, smooth_end: np.ndarray, corner_point: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    control_1 = start + (smooth_end - start) / 3.0
    control_2 = smooth_end + (corner_point - smooth_end) / 3.0
    return control_1, control_2


def _tuple_point(value: np.ndarray) -> Point:
    return (float(value[0]), float(value[1]))
