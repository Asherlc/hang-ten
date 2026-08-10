"""Editable hold-outline schema helpers and deterministic catalog detection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import tempfile

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
    root = _mapping(value, field)
    return (
        _finite_float(root.get("x"), f"{field}.x"),
        _finite_float(root.get("y"), f"{field}.y"),
        _finite_float(root.get("width"), f"{field}.width"),
        _finite_float(root.get("height"), f"{field}.height"),
    )


def _bounds_tuple(value: object, field: str) -> Bounds:
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
    confidence: float | str
    bounds: Bounds
    path: OutlinePath
    notes: str

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
        _bounds_tuple(self.bounds, "bounds")
        _string(self.notes, "notes")

    def to_json(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "confidence": self.confidence,
            "bounds": {
                "x": self.bounds[0],
                "y": self.bounds[1],
                "width": self.bounds[2],
                "height": self.bounds[3],
            },
            "path": self.path.to_json(),
            "notes": self.notes,
        }

    @classmethod
    def from_json(cls, payload: object) -> "HoldOutline":
        root = _mapping(payload, "outline")
        return cls(
            id=_string(root.get("id"), "outline.id"),
            label=_string(root.get("label"), "outline.label"),
            kind=_string(root.get("kind"), "outline.kind"),
            confidence=_confidence(root.get("confidence"), "outline.confidence"),
            bounds=_bounds(root.get("bounds"), "outline.bounds"),
            path=OutlinePath.from_json(root.get("path")),
            notes=_string(root.get("notes"), "outline.notes"),
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
        if not self.source_image.startswith("../"):
            raise ValueError('source_image must be a relative "../<basename>.png" path')
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
        expected_source_image = f"../{source_path.name}"
        if document.source_image != expected_source_image:
            raise ValueError(
                f"sourceImage must be {expected_source_image} for {source_path.name}"
            )
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
    _validate_normalized_bounds(bounds, "outline bounds")
    x, y, width, height = bounds
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


def _validate_normalized_bounds(bounds: Bounds, field: str) -> None:
    x, y, width, height = bounds
    for value in bounds:
        if not 0.0 <= value <= 1.0 or not math.isfinite(value):
            raise ValueError(f"{field} must stay in normalized space")
    if width <= 0.0 or height <= 0.0:
        raise ValueError(f"{field} must be non-degenerate")
    if x + width > 1.0 + _EPSILON or y + height > 1.0 + _EPSILON:
        raise ValueError(f"{field} must stay within normalized space")


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


@lru_cache(maxsize=1)
def _load_default_catalog_source_hints() -> Mapping[str, object]:
    return _load_catalog_source_hints(Path(__file__).with_name("catalog_outline_sources.json"))


def load_catalog_source_hints(path: Path | None = None) -> Mapping[str, object]:
    if path is None:
        return _load_default_catalog_source_hints()
    return _load_catalog_source_hints(path)


def _load_catalog_source_hints(source_path: Path) -> Mapping[str, object]:
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
        guidance = _mapping(
            reference_root.get("outlineGuidance"),
            f"catalog outline sources.{product}.outlineGuidance",
        )
        _positive_int(
            guidance.get("approximateHoldCount"),
            "outlineGuidance.approximateHoldCount",
        )
        _positive_int(guidance.get("minimumContours"), "outlineGuidance.minimumContours")
        _string(guidance.get("layout"), "outlineGuidance.layout")
        if not isinstance(guidance.get("symmetric"), bool):
            raise ValueError("outlineGuidance.symmetric must be a boolean")
        if not isinstance(guidance.get("allowsLongRails"), bool):
            raise ValueError("outlineGuidance.allowsLongRails must be a boolean")
        raw_contours = guidance.get("manualContours")
        if not isinstance(raw_contours, Sequence) or isinstance(raw_contours, str):
            raise ValueError("outlineGuidance.manualContours must be a sequence")
        for index, raw_contour in enumerate(raw_contours):
            contour = _mapping(raw_contour, f"outlineGuidance.manualContours[{index}]")
            kind = _string(contour.get("kind"), "manual contour.kind")
            if kind not in _KINDS:
                raise ValueError("manual contour.kind is unsupported")
            bounds = _bounds_tuple(
                contour.get("bounds"),
                "manual contour.bounds",
            )
            _validate_normalized_bounds(bounds, "manual contour.bounds")
            mirror = contour.get("mirror", False)
            if not isinstance(mirror, bool):
                raise ValueError("manual contour.mirror must be a boolean")
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
    min_height = max(4, rgb.shape[0] // 36)
    max_strip_width = rgb.shape[1] * 0.75
    max_strip_height = rgb.shape[0] * 0.12
    for label in range(1, stats.shape[0]):
        x, y, width, height, area = stats[label]
        if area < min_area or area > max_area:
            continue
        if height < min_height:
            continue
        if width > max_strip_width and height < max_strip_height:
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
        point_width = int(np.ptp(points[:, 0])) if len(points) else 0
        point_height = int(np.ptp(points[:, 1])) if len(points) else 0
        if point_height < min_height:
            continue
        if point_width > max_strip_width and point_height < max_strip_height:
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
    if outlines:
        return tuple((points, kind, note) for points, kind, note, _ in outlines)
    return _fallback_horizontal_rail_candidates(rgb, board)


def _fallback_horizontal_rail_candidates(
    image: np.ndarray, board_mask: np.ndarray
) -> tuple[tuple[np.ndarray, str, str], ...]:
    board = np.where(board_mask > 0, 255, 0).astype(np.uint8)
    grayscale = cv2.cvtColor(_rgb_image(image), cv2.COLOR_RGB2GRAY).astype(np.float32)
    row_counts = np.count_nonzero(board, axis=1)
    valid_rows = row_counts >= max(8, board.shape[1] // 4)
    if not np.any(valid_rows):
        return ()

    row_profile = np.full(grayscale.shape[0], np.nan, dtype=np.float32)
    for row in np.flatnonzero(valid_rows):
        row_profile[row] = float(np.mean(grayscale[row][board[row] > 0]))
    valid_indices = np.flatnonzero(valid_rows)
    row_profile = np.interp(
        np.arange(len(row_profile)), valid_indices, row_profile[valid_indices]
    ).astype(np.float32)
    smoothing_sigma = max(1.0, grayscale.shape[0] / 100.0)
    smooth_profile = cv2.GaussianBlur(
        row_profile.reshape((-1, 1)), (1, 0), sigmaX=0, sigmaY=smoothing_sigma
    ).reshape(-1)
    deviation = np.abs(row_profile - smooth_profile)
    threshold = max(0.8, float(np.percentile(deviation[valid_rows], 75)))
    selected_rows = valid_rows & (deviation >= threshold)
    if not np.any(selected_rows):
        return ()

    band_mask = np.where(
        selected_rows[:, np.newaxis] & (board > 0), 255, 0
    ).astype(np.uint8)
    vertical_kernel_size = max(9, min(15, grayscale.shape[0] // 30))
    if vertical_kernel_size % 2 == 0:
        vertical_kernel_size += 1
    band_mask = cv2.morphologyEx(
        band_mask,
        cv2.MORPH_CLOSE,
        np.ones((vertical_kernel_size, 1), dtype=np.uint8),
        iterations=1,
    )
    horizontal_kernel = np.ones(
        (1, max(9, grayscale.shape[1] // 48)), dtype=np.uint8
    )
    band_mask = cv2.morphologyEx(
        band_mask, cv2.MORPH_CLOSE, horizontal_kernel, iterations=1
    )
    band_mask = cv2.morphologyEx(
        band_mask, cv2.MORPH_OPEN, np.ones((3, 3), dtype=np.uint8), iterations=1
    )
    band_mask = cv2.bitwise_and(band_mask, board)

    _, labels, stats, _ = cv2.connectedComponentsWithStats(band_mask, 8)
    min_width = max(20, grayscale.shape[1] // 3)
    max_height = max(8, grayscale.shape[0] // 5)
    outlines: list[tuple[np.ndarray, str, str, tuple[int, int, int, int]]] = []
    for label in range(1, stats.shape[0]):
        x, y, width, height, area = stats[label]
        if width < min_width or height < 3 or height > max_height or area <= 0:
            continue
        component = np.where(labels == label, 255, 0).astype(np.uint8)
        contours, _ = cv2.findContours(
            component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        simplified = cv2.approxPolyDP(
            contour,
            epsilon=max(1.0, cv2.arcLength(contour, True) * 0.02),
            closed=True,
        )
        points = _unique_points(simplified.reshape(-1, 2))
        if len(points) < 3:
            points = _unique_points(cv2.convexHull(contour).reshape(-1, 2))
        if len(points) < 3:
            continue
        outlines.append(
            (
                points.astype(np.float64),
                "edge"
                if width >= grayscale.shape[1] * 0.75
                else "rail",
                "approximate low-contrast horizontal rail band; verify against visible board geometry",
                (int(y), int(x), int(height), int(width)),
            )
        )
    outlines.sort(key=lambda item: item[3])
    if len(outlines) < 3:
        return ()
    return tuple((points, kind, note) for points, kind, note, _ in outlines)


def vectorize_catalog_image(source_path: Path) -> CatalogOutlineDocument:
    with Image.open(source_path) as image:
        rgba = image.convert("RGBA")
        pixel_data = np.array(rgba, dtype=np.uint8)
        canvas_width, canvas_height = rgba.size
    board_mask = detect_board_mask(pixel_data)
    source_support = _manual_source_board_mask(pixel_data, board_mask)
    raw_manual = _manual_candidates_for_stem(source_path.stem, canvas_width, canvas_height)
    supported_manual = tuple(
        candidate
        for candidate in raw_manual
        if _manual_contour_is_supported(candidate[0], candidate[1], pixel_data, source_support)
    )
    manual_candidates = tuple(
        candidate
        for candidate in raw_manual
        if any(candidate is supported for supported in supported_manual)
        or any(_manual_candidates_are_mirrors(candidate, supported) for supported in supported_manual)
    )
    candidates: list[tuple[np.ndarray, str, str, bool]] = [
        (*candidate, True) for candidate in manual_candidates
    ]
    if not candidates:
        candidates.extend(
            (*candidate, False)
            for candidate in detect_hold_candidates(pixel_data, board_mask)
        )
    clip_mask = board_mask
    if not candidates:
        clip_mask = _broad_board_mask(_rgb_image(pixel_data))
        candidates.extend(
            (*candidate, False) for candidate in _fallback_hold_candidates(pixel_data)
        )
    if not candidates:
        raise ValueError(f"no hold candidates detected for {source_path.name}")
    references = _references_for_stem(source_path.stem)
    outlines: list[HoldOutline] = []
    for index, (contour, kind, note, is_manual) in enumerate(candidates, start=1):
        clipped = (
            contour
            if is_manual
            else _clip_contour_to_mask(contour, clip_mask)
        )
        if len(clipped) < 3 or _polygon_area(clipped) <= 0.0:
            continue
        source_supported = is_manual
        path = normalize_contour(clipped, canvas_width, canvas_height)
        bounds = path_bounds(path)
        if not _candidate_is_plausible(clipped, kind, canvas_width, canvas_height):
            _, _, normalized_width, normalized_height = bounds
            if not (
                source_supported
                and kind in {"edge", "rail"}
                and normalized_width <= 0.82
                and normalized_height >= 0.03
            ):
                continue
        if kind == "rail" and bounds[3] < 0.025:
            continue
        if (
            kind == "rail"
            and not _allows_long_rails_for_stem(source_path.stem)
            and bounds[2] > 0.75
            and bounds[3] < 0.12
        ):
            continue
        outlines.append(
            HoldOutline(
                id=f"hold-{index:02d}",
                label=(f"Manual {kind} {index}" if is_manual else f"Approximate {kind} {index}"),
                kind=kind,
                confidence=_APPROXIMATE_CONFIDENCE,
                bounds=bounds,
                path=path,
                notes=(
                    "Manually traced from the source PNG; cavity paths follow the inner usable boundary and raised paths follow the full outer silhouette."
                    if is_manual
                    else note
                ),
            )
        )
    if not outlines:
        raise ValueError(f"no valid hold outlines detected for {source_path.name}")
    document = CatalogOutlineDocument(
        schema_version=1,
        source_image=f"../{source_path.name}",
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        coordinate_space="normalized",
        references=references,
        outlines=tuple(outlines),
    )
    validate_catalog_document(document, source_path=source_path)
    return document


def _minimum_contours_for_stem(stem: str) -> int:
    payload = load_catalog_source_hints()
    entry = payload.get(stem)
    if not isinstance(entry, Mapping):
        return 1
    guidance = entry.get("outlineGuidance")
    if not isinstance(guidance, Mapping):
        return 1
    value = guidance.get("minimumContours", 1)
    return int(value) if isinstance(value, int) and value > 0 else 1


def _allows_long_rails_for_stem(stem: str) -> bool:
    payload = load_catalog_source_hints()
    entry = payload.get(stem)
    if not isinstance(entry, Mapping):
        return False
    guidance = entry.get("outlineGuidance")
    return isinstance(guidance, Mapping) and guidance.get("allowsLongRails") is True


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


def _fallback_hold_candidates(image: np.ndarray) -> tuple[tuple[np.ndarray, str, str], ...]:
    rgb = _rgb_image(image)
    grayscale = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    board_mask = _broad_board_mask(rgb)
    image_area = int(grayscale.shape[0] * grayscale.shape[1])
    min_area = max(150, image_area // 6000)
    max_width = grayscale.shape[1] * 0.65
    max_height = grayscale.shape[0] * 0.18

    sigma = max(9.0, min(grayscale.shape[:2]) / 90.0)
    blurred = cv2.GaussianBlur(grayscale, (0, 0), sigmaX=sigma, sigmaY=sigma)
    local_contrast = cv2.subtract(blurred, grayscale)
    _, contrast_mask = cv2.threshold(local_contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contrast_mask = cv2.bitwise_and(contrast_mask, board_mask)
    contrast_mask = cv2.morphologyEx(contrast_mask, cv2.MORPH_CLOSE, np.ones((5, 5), dtype=np.uint8), iterations=2)
    contrast_mask = cv2.morphologyEx(contrast_mask, cv2.MORPH_OPEN, np.ones((3, 3), dtype=np.uint8), iterations=1)

    board_pixels = grayscale[board_mask > 0]
    threshold = float(np.median(board_pixels) - max(15.0, float(np.std(board_pixels)) * 0.7))
    dark_mask = np.where((board_mask > 0) & (grayscale <= threshold), 255, 0).astype(np.uint8)
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_CLOSE, np.ones((3, 3), dtype=np.uint8), iterations=2)
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, np.ones((3, 3), dtype=np.uint8), iterations=1)

    outlines = _collect_mask_candidates(
        contrast_mask,
        min_area=min_area,
        max_width=max_width,
        max_height=max_height,
        note="approximate local-contrast recess candidate; verify against visible board geometry",
    )
    outlines.extend(
        _collect_mask_candidates(
            dark_mask,
            min_area=min_area,
            max_width=max_width,
            max_height=max_height,
            note="approximate dark recess candidate; verify against visible board geometry",
        )
    )
    deduped = _dedupe_candidate_outlines(outlines)
    deduped.sort(key=lambda item: item[3])
    return tuple((points, kind, note) for points, kind, note, _ in deduped)


def _broad_board_mask(rgb: np.ndarray) -> np.ndarray:
    candidate = _board_mask_candidate(rgb)
    component = _largest_component(candidate)
    if component is None:
        raise ValueError("broad board mask could not be determined")
    return component


def _board_mask_candidate(rgb: np.ndarray) -> np.ndarray:
    border = np.concatenate((rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]), axis=0)
    background = np.median(border.astype(np.float32), axis=0)
    distance = np.linalg.norm(rgb.astype(np.float32) - background, axis=2)
    threshold = max(12.0, float(np.percentile(distance, 60)))
    candidate = np.where(distance >= threshold, 255, 0).astype(np.uint8)
    candidate = cv2.morphologyEx(candidate, cv2.MORPH_CLOSE, np.ones((5, 5), dtype=np.uint8), iterations=2)
    candidate = cv2.morphologyEx(candidate, cv2.MORPH_OPEN, np.ones((5, 5), dtype=np.uint8), iterations=1)
    return candidate


def _collect_mask_candidates(
    mask: np.ndarray,
    *,
    min_area: int,
    max_width: float,
    max_height: float,
    note: str,
) -> list[tuple[np.ndarray, str, str, tuple[int, int, int, int]]]:
    _, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    outlines: list[tuple[np.ndarray, str, str, tuple[int, int, int, int]]] = []
    for label in range(1, stats.shape[0]):
        x, y, width, height, area = stats[label]
        if area < min_area:
            continue
        if width > max_width or height > max_height:
            continue
        component = np.where(labels == label, 255, 0).astype(np.uint8)
        contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(contour) <= 1.0:
            continue
        simplified = cv2.approxPolyDP(contour, epsilon=max(1.0, cv2.arcLength(contour, True) * 0.02), closed=True)
        points = _unique_points(simplified.reshape(-1, 2))
        if len(points) < 3:
            continue
        outlines.append(
            (
                points.astype(np.float64),
                _candidate_kind(width, height),
                note,
                (int(y), int(x), int(height), int(width)),
            )
        )
    return outlines


def _dedupe_candidate_outlines(
    outlines: list[tuple[np.ndarray, str, str, tuple[int, int, int, int]]]
) -> list[tuple[np.ndarray, str, str, tuple[int, int, int, int]]]:
    deduped: list[tuple[np.ndarray, str, str, tuple[int, int, int, int]]] = []
    for outline in sorted(outlines, key=lambda item: (item[3][0], item[3][1], item[3][2] * item[3][3])):
        _, _, _, bounds = outline
        if any(_bounds_iou(bounds, existing[3]) >= 0.5 for existing in deduped):
            continue
        deduped.append(outline)
    return deduped


def _bounds_iou(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> float:
    left_y, left_x, left_h, left_w = left
    right_y, right_x, right_h, right_w = right
    left_x2 = left_x + left_w
    left_y2 = left_y + left_h
    right_x2 = right_x + right_w
    right_y2 = right_y + right_h
    overlap_x1 = max(left_x, right_x)
    overlap_y1 = max(left_y, right_y)
    overlap_x2 = min(left_x2, right_x2)
    overlap_y2 = min(left_y2, right_y2)
    overlap_w = max(0, overlap_x2 - overlap_x1)
    overlap_h = max(0, overlap_y2 - overlap_y1)
    intersection = overlap_w * overlap_h
    if intersection == 0:
        return 0.0
    left_area = left_w * left_h
    right_area = right_w * right_h
    union = left_area + right_area - intersection
    if union <= 0:
        return 0.0
    return intersection / union


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


def _manual_candidates_for_stem(
    stem: str, width: int, height: int
) -> tuple[tuple[np.ndarray, str, str], ...]:
    payload = load_catalog_source_hints()
    entry = payload.get(stem)
    if not isinstance(entry, Mapping):
        return ()
    guidance = entry.get("outlineGuidance")
    if not isinstance(guidance, Mapping):
        return ()
    raw_contours = guidance.get("manualContours", ())
    if not isinstance(raw_contours, Sequence) or isinstance(raw_contours, str):
        return ()
    candidates: list[tuple[np.ndarray, str, str, tuple[float, float, float, float]]] = []
    for raw_contour in raw_contours:
        contour = _mapping(raw_contour, "manual contour")
        bounds = _bounds_tuple(contour.get("bounds"), "manual contour.bounds")
        kind = _string(contour.get("kind"), "manual contour.kind")
        mirror = contour.get("mirror", False)
        variants = (bounds, _mirror_bounds(bounds)) if mirror else (bounds,)
        for variant in variants:
            points = _rounded_rectangle_contour(variant, width, height)
            candidates.append(
                (
                    points,
                    kind,
                    "hand-edited approximate internal contour guided by visible source layout",
                    variant,
                )
            )
    candidates.sort(key=lambda item: (item[3][1], item[3][0], item[3][2], item[3][3]))
    return tuple((points, kind, note) for points, kind, note, _ in candidates)


def _manual_source_board_mask(image: np.ndarray, board_mask: np.ndarray) -> np.ndarray:
    """Recover separated board pieces for source alignment without changing detection."""

    rgb = _rgb_image(image)
    candidate = _board_mask_candidate(rgb)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, 8)
    largest_area = max(
        (int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, count)),
        default=0,
    )
    minimum_area = max(64, int(largest_area * 0.05))
    separated_boards = np.zeros_like(candidate)
    for index in range(1, count):
        if int(stats[index, cv2.CC_STAT_AREA]) >= minimum_area:
            separated_boards[labels == index] = 255
    return cv2.bitwise_or(board_mask, separated_boards)


def _manual_candidates_are_mirrors(
    first: tuple[np.ndarray, str, str], second: tuple[np.ndarray, str, str]
) -> bool:
    if first[1] != second[1]:
        return False
    first_points, second_points = first[0], second[0]
    first_min = np.min(first_points, axis=0)
    first_max = np.max(first_points, axis=0)
    second_min = np.min(second_points, axis=0)
    second_max = np.max(second_points, axis=0)
    width = max(float(first_max[0]), float(second_max[0])) + min(
        float(first_min[0]), float(second_min[0])
    )
    return (
        not np.array_equal(first_points, second_points)
        and np.isclose(first_min[1], second_min[1])
        and np.isclose(first_max[1], second_max[1])
        and np.isclose(first_min[0] + second_max[0], width)
        and np.isclose(first_max[0] + second_min[0], width)
    )


def _manual_contour_is_supported(
    contour: np.ndarray,
    kind: str,
    image: np.ndarray,
    board_mask: np.ndarray,
) -> bool:
    """Require board placement plus local boundary evidence for manual boxes."""

    rgb = _rgb_image(image)
    grayscale = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = grayscale.shape
    points = np.rint(np.asarray(contour, dtype=np.float64)).astype(np.int32)
    if points.ndim != 2 or len(points) < 3:
        return False
    contour_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(contour_mask, [points.reshape((-1, 1, 2))], 255)
    area = int(np.count_nonzero(contour_mask))
    if area == 0:
        return False
    board_overlap = np.count_nonzero((contour_mask > 0) & (board_mask > 0)) / area
    if board_overlap < 0.35:
        return False

    boundary = np.zeros_like(contour_mask)
    cv2.polylines(
        boundary,
        [points.reshape((-1, 1, 2))],
        isClosed=True,
        color=255,
        thickness=max(2, min(7, int(min(width, height) * 0.004))),
    )
    radius = max(5, min(24, int(min(width, height) * 0.018)))
    ring_kernel = np.ones((radius * 2 + 1, radius * 2 + 1), dtype=np.uint8)
    boundary_band = cv2.dilate(boundary, ring_kernel, iterations=1) > 0
    inner = cv2.erode(contour_mask, ring_kernel, iterations=1) > 0
    outer = (
        (cv2.dilate(contour_mask, ring_kernel, iterations=1) > 0)
        & (contour_mask == 0)
        & (board_mask > 0)
    )
    if not inner.any() or not outer.any():
        return False

    contrast = abs(float(np.mean(grayscale[inner])) - float(np.mean(grayscale[outer])))
    gradient_x = cv2.Sobel(grayscale, cv2.CV_32F, 1, 0)
    gradient_y = cv2.Sobel(grayscale, cv2.CV_32F, 0, 1)
    gradient = cv2.magnitude(gradient_x, gradient_y)
    board_gradient = gradient[board_mask > 0]
    if board_gradient.size == 0:
        return False
    local_gradient = float(np.percentile(gradient[boundary_band], 75))
    board_baseline = max(1.0, float(np.percentile(board_gradient, 65)))
    edge_ratio = local_gradient / board_baseline

    # A quiet flat patch can have photographic texture, but it should not have
    # both a weak luminance step and a boundary gradient stronger than the board.
    if contrast < 3.0:
        return False
    if kind == "rail":
        return contrast >= 7.0 or edge_ratio >= 1.18
    return contrast >= 5.0 or edge_ratio >= 1.22


def _mirror_bounds(bounds: Bounds) -> Bounds:
    x, y, width, height = bounds
    return (1.0 - x - width, y, width, height)


def _rounded_rectangle_contour(
    bounds: Bounds, width: int, height: int
) -> np.ndarray:
    x, y, box_width, box_height = bounds
    radius = min(box_width, box_height) * 0.22
    points = np.array(
        [
            (x + radius, y),
            (x + box_width - radius, y),
            (x + box_width, y + radius),
            (x + box_width, y + box_height - radius),
            (x + box_width - radius, y + box_height),
            (x + radius, y + box_height),
            (x, y + box_height - radius),
            (x, y + radius),
        ],
        dtype=np.float64,
    )
    return points * np.array([width, height], dtype=np.float64)


def _candidate_is_plausible(
    contour: np.ndarray, kind: str, width: int, height: int
) -> bool:
    x, y, box_width, box_height = cv2.boundingRect(
        np.asarray(contour, dtype=np.float64).astype(np.int32)
    )
    normalized = (x / width, y / height, box_width / width, box_height / height)
    left, top, normalized_width, normalized_height = normalized
    if (
        left <= 0.005
        or top <= 0.005
        or left + normalized_width >= 0.995
        or top + normalized_height >= 0.995
    ):
        return False
    if normalized_width < 0.012 or normalized_height < 0.012:
        return False
    if normalized_width > 0.88 and normalized_height < 0.18:
        return False
    if kind != "rail" and normalized_width > 0.70 and normalized_height < 0.16:
        return False
    if len(contour) <= 4 and normalized_width > 0.30 and normalized_height > 0.12:
        return False
    bounding_area = max(1.0, float(box_width * box_height))
    if _polygon_area(contour) / bounding_area < 0.18:
        return False
    return True


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
    """Flatten an editable path into a deterministic pixel polyline for review."""

    contour: list[tuple[int, int]] = []
    current: Point | None = None
    subpath_start: Point | None = None

    def append(point: Point) -> None:
        pixel = _point_to_pixel(point, width, height)
        if not contour or contour[-1] != pixel:
            contour.append(pixel)

    for command in path.commands:
        if command.command == "M":
            if current is not None:
                raise ValueError("outline path review renderer supports one subpath")
            current = command.to
            subpath_start = command.to
            append(command.to)
            continue
        if current is None:
            raise ValueError("outline path must begin with a move command")
        if command.command == "L":
            current = command.to
            append(command.to)
            continue
        if command.controls is None:
            raise ValueError("cubic outline command is missing controls")

        control_1, control_2 = command.controls
        # A fixed subdivision count keeps review overlays reproducible while
        # retaining the actual curve shape instead of drawing its controls.
        for step in range(1, 17):
            t = step / 16.0
            inverse = 1.0 - t
            point = (
                inverse**3 * current[0]
                + 3.0 * inverse**2 * t * control_1[0]
                + 3.0 * inverse * t**2 * control_2[0]
                + t**3 * command.to[0],
                inverse**3 * current[1]
                + 3.0 * inverse**2 * t * control_1[1]
                + 3.0 * inverse * t**2 * control_2[1]
                + t**3 * command.to[1],
            )
            append(point)
        current = command.to

    if path.closed and subpath_start is not None:
        append(subpath_start)
    if len(contour) < 3:
        raise ValueError("outline path must yield at least three drawable points")
    return np.array(contour, dtype=np.int32)


def _point_to_pixel(point: Point, width: int, height: int) -> tuple[int, int]:
    return (
        min(width - 1, max(0, int(round(point[0] * width)))),
        min(height - 1, max(0, int(round(point[1] * height)))),
    )
