"""Closed parser for normalized, package-owned hangboard artwork."""

from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Any, Mapping


_ROLES = frozenset({"topPlane", "faceLight", "separator", "bottomPlane", "topSeam", "shelf"})
_TREATMENTS = frozenset({"surface", "shelf", "recess"})
_DEPTHS = frozenset({"deep", "shallow"})


def _closed(payload: Mapping[str, Any], keys: set[str], source: str) -> None:
    unknown = set(payload) - keys
    missing = keys - set(payload)
    if unknown:
        raise ValueError(f"{source} has unknown keys: {sorted(unknown)}")
    if missing:
        raise ValueError(f"{source} is missing keys: {sorted(missing)}")


def _mapping(value: Any, source: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{source} must be an object")
    return value


def _string(value: Any, source: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{source} must be a non-empty string")
    return value


def _number(value: Any, source: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{source} must be finite")
    return float(value)


@dataclass(frozen=True)
class NormalizedFrame:
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_json(cls, value: Any, source: str) -> "NormalizedFrame":
        payload = _mapping(value, source)
        _closed(payload, {"x", "y", "width", "height"}, source)
        x, y = _number(payload["x"], f"{source}.x"), _number(payload["y"], f"{source}.y")
        width, height = _number(payload["width"], f"{source}.width"), _number(payload["height"], f"{source}.height")
        if width <= 0 or height <= 0 or x < 0 or y < 0 or x + width > 1 or y + height > 1:
            raise ValueError(f"{source} must stay inside the normalized 0...1 range")
        return cls(x, y, width, height)


@dataclass(frozen=True)
class PathCommand:
    command: str
    to: tuple[float, float] | None = None
    control: tuple[float, float] | None = None
    control1: tuple[float, float] | None = None
    control2: tuple[float, float] | None = None

    @classmethod
    def from_json(cls, value: Any, source: str) -> "PathCommand":
        payload = _mapping(value, source)
        command = _string(payload.get("command"), f"{source}.command")
        required = {
            "move": {"command", "to"}, "line": {"command", "to"},
            "quad": {"command", "to", "control"},
            "curve": {"command", "to", "control1", "control2"}, "close": {"command"},
        }
        if command not in required:
            raise ValueError(f"{source}.command is unsupported")
        _closed(payload, required[command], source)
        def point(key: str) -> tuple[float, float]:
            raw = payload[key]
            if not isinstance(raw, list) or len(raw) != 2:
                raise ValueError(f"{source}.{key} must be a two-element array")
            coordinates = tuple(_number(item, f"{source}.{key}[{index}]") for index, item in enumerate(raw))
            if any(coordinate < 0 or coordinate > 1 for coordinate in coordinates):
                raise ValueError(f"{source}.{key} must stay in the normalized 0...1 range")
            return coordinates  # type: ignore[return-value]
        return cls(command, point("to") if "to" in payload else None,
                   point("control") if "control" in payload else None,
                   point("control1") if "control1" in payload else None,
                   point("control2") if "control2" in payload else None)


@dataclass(frozen=True)
class BoardShapeDocument:
    type: str
    commands: tuple[PathCommand, ...] = ()
    corner_radius_fraction: float | None = None

    @classmethod
    def from_json(cls, value: Any, source: str) -> "BoardShapeDocument":
        payload = _mapping(value, source)
        shape_type = _string(payload.get("type"), f"{source}.type")
        if shape_type == "roundedRect":
            _closed(payload, {"type", "cornerRadiusFraction"}, source)
            radius = _number(payload["cornerRadiusFraction"], f"{source}.cornerRadiusFraction")
            if not 0 <= radius <= 0.5:
                raise ValueError(f"{source}.cornerRadiusFraction must be in 0...0.5")
            return cls(shape_type, corner_radius_fraction=radius)
        if shape_type == "path":
            _closed(payload, {"type", "commands"}, source)
            raw_commands = payload["commands"]
            if not isinstance(raw_commands, list) or not raw_commands:
                raise ValueError(f"{source}.commands must be a non-empty array")
            commands = tuple(PathCommand.from_json(command, f"{source}.commands[{index}]") for index, command in enumerate(raw_commands))
            if commands[0].command != "move" or commands[-1].command != "close":
                raise ValueError(f"{source}.commands must begin with move and end with close")
            return cls(shape_type, commands=commands)
        raise ValueError(f"{source}.type must be roundedRect or path")


@dataclass(frozen=True)
class BoardLayerDocument:
    id: str
    role: str
    frame: NormalizedFrame
    shape: BoardShapeDocument


@dataclass(frozen=True)
class BoardHoldPieceDocument:
    id: str
    hold_id: str
    frame: NormalizedFrame
    shape: BoardShapeDocument
    treatment: Mapping[str, Any]


@dataclass(frozen=True)
class BoardArtworkDocument:
    board_id: str
    canvas_frame: NormalizedFrame
    palette: str
    silhouette: BoardShapeDocument
    layers: tuple[BoardLayerDocument, ...]
    hold_pieces: tuple[BoardHoldPieceDocument, ...]
    schema_version: int = 1

    @property
    def hold_ids(self) -> frozenset[str]:
        return frozenset(piece.hold_id for piece in self.hold_pieces)

    @classmethod
    def from_json(cls, value: Any, source: str = "artwork.json") -> "BoardArtworkDocument":
        payload = _mapping(value, source)
        _closed(payload, {"schemaVersion", "boardID", "canvasFrame", "palette", "silhouette", "layers", "holdPieces"}, source)
        schema = payload["schemaVersion"]
        if isinstance(schema, bool) or schema != 1:
            raise ValueError(f"{source}.schemaVersion must be 1")
        board_id = _string(payload["boardID"], f"{source}.boardID")
        canvas = NormalizedFrame.from_json(payload["canvasFrame"], f"{source}.canvasFrame")
        palette = _string(payload["palette"], f"{source}.palette")
        if palette != "sculptedWood":
            raise ValueError(f"{source}.palette must be sculptedWood")
        silhouette = BoardShapeDocument.from_json(payload["silhouette"], f"{source}.silhouette")
        layers_raw = payload["layers"]
        pieces_raw = payload["holdPieces"]
        if not isinstance(layers_raw, list) or not isinstance(pieces_raw, list):
            raise ValueError(f"{source}.layers and {source}.holdPieces must be arrays")
        layers: list[BoardLayerDocument] = []
        for index, raw in enumerate(layers_raw):
            item_source = f"{source}.layers[{index}]"
            item = _mapping(raw, item_source)
            _closed(item, {"id", "role", "frame", "shape"}, item_source)
            role = _string(item["role"], f"{item_source}.role")
            if role not in _ROLES:
                raise ValueError(f"{item_source}.role is unsupported")
            layers.append(BoardLayerDocument(_string(item["id"], f"{item_source}.id"), role,
                                              NormalizedFrame.from_json(item["frame"], f"{item_source}.frame"),
                                              BoardShapeDocument.from_json(item["shape"], f"{item_source}.shape")))
        if len({layer.id for layer in layers}) != len(layers):
            raise ValueError("duplicate artwork layer id")
        pieces: list[BoardHoldPieceDocument] = []
        for index, raw in enumerate(pieces_raw):
            item_source = f"{source}.holdPieces[{index}]"
            item = _mapping(raw, item_source)
            _closed(item, {"id", "holdID", "frame", "shape", "treatment"}, item_source)
            treatment = _mapping(item["treatment"], f"{item_source}.treatment")
            treatment_type = _string(treatment.get("type"), f"{item_source}.treatment.type")
            if treatment_type not in _TREATMENTS:
                raise ValueError(f"{item_source}.treatment.type is unsupported")
            expected = {"type"} if treatment_type == "surface" else {"type", "rimInsetFraction"}
            if treatment_type == "recess":
                expected.add("depth")
            _closed(treatment, expected, f"{item_source}.treatment")
            if "rimInsetFraction" in treatment:
                inset = _number(treatment["rimInsetFraction"], f"{item_source}.treatment.rimInsetFraction")
                if not 0 <= inset <= 0.5:
                    raise ValueError(f"{item_source}.treatment.rimInsetFraction must be in 0...0.5")
            if treatment_type == "recess" and treatment["depth"] not in _DEPTHS:
                raise ValueError(f"{item_source}.treatment.depth is unsupported")
            pieces.append(BoardHoldPieceDocument(_string(item["id"], f"{item_source}.id"),
                                                  _string(item["holdID"], f"{item_source}.holdID"),
                                                  NormalizedFrame.from_json(item["frame"], f"{item_source}.frame"),
                                                  BoardShapeDocument.from_json(item["shape"], f"{item_source}.shape"),
                                                  MappingProxyType(dict(treatment))))
        if len({piece.id for piece in pieces}) != len(pieces):
            raise ValueError("duplicate artwork hold piece id")
        return cls(board_id, canvas, palette, silhouette, tuple(layers), tuple(pieces), schema)


def load_artwork(path: Any) -> BoardArtworkDocument:
    import json
    from pathlib import Path
    artwork_path = Path(path)
    if not artwork_path.is_file():
        raise ValueError(f"artwork.json does not exist: {artwork_path}")
    try:
        payload = json.loads(artwork_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"artwork.json is invalid JSON: {artwork_path}") from error
    return BoardArtworkDocument.from_json(payload, "artwork.json")
