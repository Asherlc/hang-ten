"""Editable hold-outline schema helpers and deterministic catalog detection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import tempfile
from types import MappingProxyType

import cv2
import numpy as np
from PIL import Image


Point = tuple[float, float]
Bounds = tuple[float, float, float, float]

_KINDS = frozenset({"pocket", "edge", "rail", "jug", "sloper"})
_EPSILON = 1e-9
_APPROXIMATE_CONFIDENCE = "approximate"


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


def _reference(value: object, field: str) -> Mapping[str, object]:
    root = _mapping(value, field)
    return MappingProxyType(
        {
            "title": _string(root.get("title"), f"{field}.title"),
            "url": _string(root.get("url"), f"{field}.url"),
            "hints": _string_tuple(root.get("hints", ()), f"{field}.hints"),
        }
    )


@dataclass(frozen=True, slots=True)
class OutlineCommand:
    command: str
    to: Point
    controls: tuple[Point, Point] | None = None

    def __post_init__(self) -> None:
        if self.command not in {"M", "L", "C"}:
            raise ValueError("outline command must be M, L, or C")
        object.__setattr__(self, "to", _point(self.to, "to"))
        if self.command == "C":
            if (
                self.controls is None
                or not isinstance(self.controls, Sequence)
                or isinstance(self.controls, str)
                or len(self.controls) != 2
            ):
                raise ValueError("cubic outline commands require two control points")
            object.__setattr__(
                self,
                "controls",
                (
                    _point(self.controls[0], "controls[0]"),
                    _point(self.controls[1], "controls[1]"),
                ),
            )
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

    def __post_init__(self) -> None:
        if not isinstance(self.commands, Sequence) or isinstance(self.commands, str):
            raise ValueError("outline path commands must be a sequence")
        if not all(isinstance(command, OutlineCommand) for command in self.commands):
            raise ValueError("outline path commands must be outline commands")
        if not isinstance(self.closed, bool):
            raise ValueError("outline path closed flag must be a boolean")
        object.__setattr__(self, "commands", tuple(self.commands))

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
    confidence: float | str
    bounds: Bounds
    path: OutlinePath
    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        _string(self.id, "id")
        _string(self.label, "label")
        if self.kind not in _KINDS:
            raise ValueError("kind is unsupported")
        if isinstance(self.confidence, str):
            if self.confidence != _APPROXIMATE_CONFIDENCE:
                raise ValueError('string confidence must be "approximate"')
        elif not 0.0 <= self.confidence <= 1.0 or not math.isfinite(self.confidence):
            raise ValueError("confidence must be finite and normalized")
        object.__setattr__(self, "bounds", _bounds(self.bounds, "bounds"))
        if not isinstance(self.path, OutlinePath):
            raise ValueError("path must be an outline path")
        object.__setattr__(self, "notes", _string_tuple(self.notes, "notes"))

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
            confidence=_confidence(root.get("confidence"), "outline.confidence"),
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
        if not isinstance(self.references, Sequence) or isinstance(self.references, str):
            raise ValueError("references must be a sequence")
        object.__setattr__(
            self,
            "references",
            tuple(_reference(reference, f"references[{index}]") for index, reference in enumerate(self.references)),
        )
        if not isinstance(self.outlines, Sequence) or isinstance(self.outlines, str):
            raise ValueError("outlines must be a sequence")
        if not all(isinstance(outline, HoldOutline) for outline in self.outlines):
            raise ValueError("outlines must contain hold outlines")
        object.__setattr__(self, "outlines", tuple(self.outlines))
        if not self.outlines:
            raise ValueError("outlines must not be empty")
        self._validate_references()

    def _validate_references(self) -> None:
        for index, reference in enumerate(self.references):
            _reference(reference, f"references[{index}]")

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
    if x + width > 1.0 + _EPSILON or y + height > 1.0 + _EPSILON:
        raise ValueError("outline bounds must stay in normalized space")
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


def load_catalog_source_hints(path: Path | None = None) -> Mapping[str, object]:
    source_path = path or Path(__file__).with_name("catalog_outline_sources.json")
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    root = _mapping(payload, "catalog outline sources")
    for product, entry in root.items():
        _string(product, "catalog outline sources product")
        reference_root = _mapping(entry, f"catalog outline sources.{product}")
        references = reference_root.get("references", ())
        if not isinstance(references, Sequence) or isinstance(references, str):
            raise ValueError(f"catalog outline sources.{product}.references must be a sequence")
        for index, reference in enumerate(references):
            reference_mapping = _mapping(reference, f"catalog outline sources.{product}.references[{index}]")
            _string(reference_mapping.get("title"), "reference.title")
            _string(reference_mapping.get("url"), "reference.url")
            _string_tuple(reference_mapping.get("hints", ()), "reference.hints")
    return root


def detect_board_mask(image: np.ndarray) -> np.ndarray:
    rgb = _rgb_image(image)
    grayscale = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    border = np.concatenate(
        (
            rgb[0, :, :],
            rgb[-1, :, :],
            rgb[:, 0, :],
            rgb[:, -1, :],
        ),
        axis=0,
    )
    background = np.median(border.astype(np.float32), axis=0)
    distance = np.linalg.norm(rgb.astype(np.float32) - background, axis=2)
    threshold = max(18.0, float(np.percentile(distance, 82)))
    candidate = np.where(distance >= threshold, 255, 0).astype(np.uint8)
    if not np.any(candidate):
        local = cv2.adaptiveThreshold(
            grayscale,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            31,
            6,
        )
        candidate = local
    kernel = np.ones((5, 5), dtype=np.uint8)
    cleaned = cv2.morphologyEx(candidate, cv2.MORPH_CLOSE, kernel, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    component = _largest_component(cleaned)
    if component is None:
        raise ValueError("board mask could not be determined")
    return component


def detect_hold_candidates(
    image: np.ndarray, board_mask: np.ndarray
) -> tuple[tuple[np.ndarray, str, str], ...]:
    rgb = _rgb_image(image)
    if board_mask.shape != rgb.shape[:2]:
        raise ValueError("board mask must match image dimensions")
    board = np.where(board_mask > 0, 255, 0).astype(np.uint8)
    board_area = int(np.count_nonzero(board))
    if board_area == 0:
        raise ValueError("board mask must not be empty")
    grayscale = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    board_pixels = grayscale[board > 0]
    median = float(np.median(board_pixels))
    threshold = max(0.0, median - max(10.0, float(np.std(board_pixels)) * 0.5))
    darker = np.where((board > 0) & (grayscale <= threshold), 255, 0).astype(np.uint8)
    edge_map = cv2.Canny(grayscale, 40, 120)
    contrast = cv2.bitwise_and(edge_map, edge_map, mask=board)
    candidates = cv2.bitwise_or(darker, contrast)
    kernel = np.ones((3, 3), dtype=np.uint8)
    candidates = cv2.morphologyEx(candidates, cv2.MORPH_CLOSE, kernel, iterations=2)
    candidates = cv2.morphologyEx(candidates, cv2.MORPH_OPEN, kernel, iterations=1)

    component_stats = cv2.connectedComponentsWithStats(candidates, 8)
    _, labels, stats, _ = component_stats
    outlines: list[tuple[np.ndarray, str, str, tuple[int, int, int, int]]] = []
    min_area = max(18, board_area // 500)
    max_area = max(min_area + 1, board_area // 3)
    for label in range(1, stats.shape[0]):
        x, y, width, height, area = stats[label]
        if area < min_area or area > max_area:
            continue
        component = np.where(labels == label, 255, 0).astype(np.uint8)
        component = cv2.bitwise_and(component, board)
        contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(contour) <= 1.0:
            continue
        simplified = cv2.approxPolyDP(contour, epsilon=max(1.0, cv2.arcLength(contour, True) * 0.02), closed=True)
        points = simplified.reshape(-1, 2)
        points = _unique_points(points)
        if len(points) < 3:
            hull = cv2.convexHull(contour).reshape(-1, 2)
            points = _unique_points(hull)
        if len(points) < 3:
            continue
        kind = _candidate_kind(width, height)
        outlines.append(
            (
                points.astype(np.float64),
                kind,
                "approximate catalog contrast candidate; verify against visible board geometry",
                (int(y), int(x), int(height), int(width)),
            )
        )
    outlines.sort(key=lambda item: item[3])
    return tuple((points, kind, note) for points, kind, note, _ in outlines)


def vectorize_catalog_image(source_path: Path) -> CatalogOutlineDocument:
    with Image.open(source_path) as image:
        rgba = image.convert("RGBA")
        pixel_data = np.array(rgba, dtype=np.uint8)
        canvas_width, canvas_height = rgba.size
    board_mask = detect_board_mask(pixel_data)
    candidates = detect_hold_candidates(pixel_data, board_mask)
    if not candidates:
        raise ValueError(f"no hold candidates detected for {source_path.name}")
    references = _references_for_stem(source_path.stem)
    outlines: list[HoldOutline] = []
    for index, (contour, kind, note) in enumerate(candidates, start=1):
        clipped = _clip_contour_to_mask(contour, board_mask)
        if len(clipped) < 3 or _polygon_area(clipped) <= 0.0:
            continue
        path = normalize_contour(clipped, canvas_width, canvas_height)
        outlines.append(
            HoldOutline(
                id=f"hold-{index:02d}",
                label=f"Approximate {kind} {index}",
                kind=kind,
                confidence=_APPROXIMATE_CONFIDENCE,
                bounds=path_bounds(path),
                path=path,
                notes=(note,),
            )
        )
    if not outlines:
        raise ValueError(f"no valid hold outlines detected for {source_path.name}")
    document = CatalogOutlineDocument(
        schema_version=1,
        source_image=source_path.name,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        coordinate_space="normalized",
        references=references,
        outlines=tuple(outlines),
    )
    validate_catalog_document(document, source_path=source_path)
    return document


def render_catalog_review_overlay(source_path: Path, document: CatalogOutlineDocument, output_path: Path) -> None:
    with Image.open(source_path) as image:
        review = image.convert("RGBA")
    canvas = np.array(review, dtype=np.uint8)
    overlay = canvas.copy()
    for outline in document.outlines:
        contour = _outline_path_to_pixels(
            outline.path, document.canvas_width, document.canvas_height
        ).reshape((-1, 1, 2))
        color = (255, 0, 64, 255)
        cv2.polylines(overlay, [contour], True, color, thickness=2, lineType=cv2.LINE_AA)
        x, y, _, _ = cv2.boundingRect(contour)
        cv2.putText(
            overlay,
            outline.id,
            (x, max(14, y + 14)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            overlay,
            outline.id,
            (x, max(14, y + 14)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(overlay, mode="RGBA").save(output_path)


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


def _confidence(value: object, field: str) -> float | str:
    if isinstance(value, str):
        if value != _APPROXIMATE_CONFIDENCE:
            raise ValueError(f'{field} must be "approximate" when using string confidence')
        return value
    return _finite_float(value, field)


def _rgb_image(image: np.ndarray) -> np.ndarray:
    pixels = np.asarray(image, dtype=np.uint8)
    if pixels.ndim != 3 or pixels.shape[2] not in {3, 4}:
        raise ValueError("image must be RGB or RGBA")
    if pixels.shape[2] == 4:
        return cv2.cvtColor(pixels, cv2.COLOR_RGBA2RGB)
    return pixels.copy()


def _largest_component(mask: np.ndarray) -> np.ndarray | None:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if count <= 1:
        return None
    best_index = max(range(1, count), key=lambda index: int(stats[index, cv2.CC_STAT_AREA]))
    component = np.where(labels == best_index, 255, 0).astype(np.uint8)
    if not np.any(component):
        return None
    return component


def _unique_points(points: np.ndarray) -> np.ndarray:
    unique: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for point in points:
        pair = (int(point[0]), int(point[1]))
        if pair not in seen:
            seen.add(pair)
            unique.append(pair)
    return np.array(unique, dtype=np.int32)


def _candidate_kind(width: int, height: int) -> str:
    aspect_ratio = width / max(height, 1)
    if aspect_ratio >= 2.2:
        return "rail"
    if aspect_ratio >= 1.3:
        return "edge"
    return "pocket"


def _references_for_stem(stem: str) -> tuple[Mapping[str, object], ...]:
    payload = load_catalog_source_hints()
    entry = payload.get(stem)
    if not isinstance(entry, Mapping):
        return ()
    references = entry.get("references", ())
    if not isinstance(references, Sequence) or isinstance(references, str):
        return ()
    return tuple(
        {
            "title": str(_mapping(reference, "reference")["title"]),
            "url": str(_mapping(reference, "reference")["url"]),
            "hints": _string_tuple(_mapping(reference, "reference").get("hints", ()), "reference.hints"),
        }
        for reference in references
    )


def _clip_contour_to_mask(contour: np.ndarray, board_mask: np.ndarray) -> np.ndarray:
    points = np.asarray(contour, dtype=np.int32)
    contour_mask = np.zeros_like(board_mask, dtype=np.uint8)
    cv2.fillPoly(contour_mask, [points.reshape((-1, 1, 2))], 255)
    clipped_mask = cv2.bitwise_and(contour_mask, board_mask)
    contours, _ = cv2.findContours(clipped_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return np.empty((0, 2), dtype=np.float64)
    clipped = max(contours, key=cv2.contourArea).reshape(-1, 2)
    return _unique_points(clipped).astype(np.float64)


def _polygon_area(points: np.ndarray) -> float:
    if len(points) < 3:
        return 0.0
    x = points[:, 0]
    y = points[:, 1]
    return abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))) / 2.0


def _outline_path_to_pixels(path: OutlinePath, width: int, height: int) -> np.ndarray:
    contour: list[tuple[int, int]] = []
    current: Point | None = None
    for command in path.commands:
        if command.command == "C":
            if current is None or command.controls is None:
                raise ValueError("cubic outline command requires a starting point and controls")
            control_1, control_2 = command.controls
            for t in np.linspace(0.0, 1.0, 17)[1:]:
                inverse_t = 1.0 - t
                point = (
                    inverse_t**3 * current[0]
                    + 3.0 * inverse_t**2 * t * control_1[0]
                    + 3.0 * inverse_t * t**2 * control_2[0]
                    + t**3 * command.to[0],
                    inverse_t**3 * current[1]
                    + 3.0 * inverse_t**2 * t * control_1[1]
                    + 3.0 * inverse_t * t**2 * control_2[1]
                    + t**3 * command.to[1],
                )
                contour.append(_normalized_point_to_pixel(point, width, height))
        else:
            contour.append(_normalized_point_to_pixel(command.to, width, height))
        current = command.to
    unique = list(dict.fromkeys(contour))
    if len(unique) < 3:
        raise ValueError("outline path must yield at least three drawable points")
    return np.array(unique, dtype=np.int32)


def _normalized_point_to_pixel(point: Point, width: int, height: int) -> tuple[int, int]:
    return (
        min(width - 1, max(0, int(round(point[0] * width)))),
        min(height - 1, max(0, int(round(point[1] * height)))),
    )
