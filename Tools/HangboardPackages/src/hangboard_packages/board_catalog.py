"""Fail-closed discovery and validation for single-file hangboard packages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
from types import MappingProxyType
from typing import Any, Mapping
import zlib

try:  # Standard package import, plus direct-file loading used by staging tests.
    from .board_geometry_schema import (
        BoardShapeDocument,
        NormalizedFrame,
        NormalizedPoint,
    )
except ImportError:  # pragma: no cover - exercised by direct module consumers
    _schema_path = Path(__file__).with_name("board_geometry_schema.py")
    _spec = importlib.util.spec_from_file_location(
        "hangboard_board_geometry_schema", _schema_path
    )
    assert _spec and _spec.loader
    _module = importlib.util.module_from_spec(_spec)
    import sys

    sys.modules[_spec.name] = _module
    _spec.loader.exec_module(_module)
    BoardShapeDocument = _module.BoardShapeDocument
    NormalizedFrame = _module.NormalizedFrame
    NormalizedPoint = _module.NormalizedPoint


_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:[a-z0-9._-]*[a-z0-9])?$")
_PACKAGE_SLUG = re.compile(r"^[a-z0-9]+(?:[a-z0-9-]*[a-z0-9])?$")
_PACKAGE_ENTRIES = frozenset({"board.json", "assets"})
_HOLD_KINDS = frozenset({"jug", "edge", "pocket", "pinch", "sloper", "gaston"})
_SLOPER_TYPES = frozenset({"flat", "round"})
_GRIP_TYPES = frozenset(
    {
        "openHand",
        "halfCrimp",
        "fullCrimp",
        "fourFingerPocket",
        "threeFingerPocket",
        "twoFingerPocket",
        "sloper",
    }
)
_HOLD_FEATURES = frozenset(
    {
        "jug",
        "roundSloper",
        "largeSlope",
        "largeEdge",
        "mediumEdge",
        "smallEdge",
        "pocket",
        "flatEdge",
        "incutEdge",
        "largeOpenHandRail",
        "thinCrimp",
        "slot",
        "widePinch",
        "mediumPinch",
        "smallPinch",
    }
)
_TREATMENTS = frozenset({"surface", "shelf", "recess"})
_DEPTHS = frozenset({"deep", "shallow"})
_SHAPE_CONSTRAINTS = frozenset(
    {"oval", "circle", "pill", "roundedRectangle", "rectangle"}
)
_ASPECT_RATIO_RELATIVE_TOLERANCE = 0.001
_FRAME_EDGE_TOLERANCE = 0.0000005
# Alias images may compute their ratio independently before serializing it.
# One part per billion accepts harmless decimal/binary rounding without
# admitting a materially different canvas shape.
_ALIAS_ASPECT_RATIO_RELATIVE_TOLERANCE = 1e-9
_ALIAS_ASPECT_RATIO_ABSOLUTE_TOLERANCE = 1e-12
# A projected boundary such as 2 * 0.15 - (0.1 + 0.2) can be a few ulps below
# zero even though it is mathematically exact. Keep this far below meaningful
# normalized geometry overflow.
_PROJECTED_FRAME_EDGE_TOLERANCE = 1e-12
_CORD_PULL_EXIT_HALF_SPACING = 22.0
_CORD_SUPPORT_MIN_X_OFFSET = -30.0
_CORD_SUPPORT_MAX_X_OFFSET = 31.0
_CORD_SUPPORT_MIN_Y_OFFSET = -177.0
_CORD_SUPPORT_MAX_Y_OFFSET = 0.0
_CORD_SHADOW_X_MARGIN = 35.0 / 2 + 4.0 + 2.3
_CORD_SHADOW_Y_MARGIN = 35.0 / 2 + 5.0 + 2.3


def _closed(
    payload: Mapping[str, Any],
    required: set[str],
    source: str,
    *,
    optional: set[str] | None = None,
) -> None:
    allowed = required | (optional or set())
    unknown = set(payload) - allowed
    missing = required - set(payload)
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


def _identifier(value: Any, source: str) -> str:
    result = _string(value, source)
    if not is_board_identifier(result):
        raise ValueError(f"{source} must be identifier-shaped")
    return result


def is_board_identifier(value: object) -> bool:
    """Return whether *value* follows the canonical board/hold ID grammar."""
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def is_board_package_slug(value: object) -> bool:
    """Return whether *value* is a flat canonical package directory slug."""
    return isinstance(value, str) and _PACKAGE_SLUG.fullmatch(value) is not None


def _number(value: Any, source: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{source} must be finite")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f"{source} must be finite") from error
    if not math.isfinite(result):
        raise ValueError(f"{source} must be finite")
    return result


def _positive_integer(value: Any, source: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{source} must be a positive integer")
    return value


def _positive_number(value: Any, source: str) -> float:
    number = _number(value, source)
    if number <= 0:
        raise ValueError(f"{source} must be a positive number")
    return number


def _presentation_rotation_degrees(value: Any, source: str) -> float:
    degrees = _number(value, source)
    if not 0 <= degrees < 360:
        raise ValueError(f"{source} must be normalized to [0, 360)")
    return degrees


def _boolean(value: Any, source: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{source} must be a boolean")
    return value


def _asset_path(value: Any, source: str) -> str:
    asset_path = _string(value, source)
    path = PurePosixPath(asset_path)
    if (
        path.is_absolute()
        or path.parts[:1] != ("assets",)
        or len(path.parts) < 2
        or any(part in {".", ".."} for part in path.parts)
        or path.as_posix() != asset_path
        or path.suffix != ".png"
    ):
        raise ValueError(f"{source} must name a PNG beneath assets/")
    return asset_path


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} does not exist as a regular file: {path}")
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is invalid JSON: {path}") from error


def _require_no_symlinks(root: Path) -> None:
    if root.is_symlink():
        raise ValueError(f"package contains symlink: {root}")
    for item in root.rglob("*"):
        if item.is_symlink():
            raise ValueError(f"package contains symlink: {item}")


@dataclass(frozen=True)
class MillimeterRange:
    lower_bound: float
    upper_bound: float

    @classmethod
    def from_json(cls, value: Any, source: str) -> "MillimeterRange":
        payload = _mapping(value, source)
        _closed(payload, {"lowerBound", "upperBound"}, source)
        lower = _positive_number(payload["lowerBound"], f"{source}.lowerBound")
        upper = _positive_number(payload["upperBound"], f"{source}.upperBound")
        if lower > upper:
            raise ValueError(f"{source}.lowerBound must not exceed upperBound")
        return cls(lower, upper)


@dataclass(frozen=True)
class SloperMetadata:
    type: str
    angle_degrees: float | None

    @classmethod
    def from_json(cls, value: Any, source: str) -> "SloperMetadata":
        payload = _mapping(value, source)
        sloper_type = _string(payload.get("type"), f"{source}.type")
        if sloper_type not in _SLOPER_TYPES:
            raise ValueError(f"{source}.type must be one of {sorted(_SLOPER_TYPES)}")
        if sloper_type == "flat":
            _closed(payload, {"type", "angleDegrees"} & set(payload), source)
            angle_degrees = None
            if "angleDegrees" in payload:
                angle_degrees = _number(payload["angleDegrees"], f"{source}.angleDegrees")
                if not 0 <= angle_degrees <= 90:
                    raise ValueError(f"{source}.angleDegrees must be in 0...90")
            return cls(sloper_type, angle_degrees)
        _closed(payload, {"type"}, source)
        return cls(sloper_type, None)


@dataclass(frozen=True)
class BoardShapeConstraint:
    shape: str
    rotation_degrees: float

    @classmethod
    def from_json(cls, value: Any, source: str) -> BoardShapeConstraint:
        payload = _mapping(value, source)
        _closed(payload, {"shape", "rotationDegrees"}, source)
        shape = _string(payload["shape"], f"{source}.shape")
        if shape not in _SHAPE_CONSTRAINTS:
            raise ValueError(f"{source}.shape is unsupported")
        rotation_degrees = _number(
            payload["rotationDegrees"], f"{source}.rotationDegrees"
        )
        if not -180 <= rotation_degrees < 180:
            raise ValueError(f"{source}.rotationDegrees must be in [-180, 180)")
        return cls(shape, rotation_degrees)


def _path_fills_declared_frame(shape: BoardShapeDocument) -> bool:
    if shape.type == "roundedRect":
        return True

    xs: list[float] = []
    ys: list[float] = []
    current: tuple[float, float] | None = None
    for command in shape.commands:
        if command.command in {"move", "line"}:
            assert command.to is not None
            current = command.to
            xs.append(current[0])
            ys.append(current[1])
        elif command.command == "quad":
            assert current is not None and command.control is not None and command.to is not None
            control = command.control
            end = command.to
            for step in range(1, 33):
                t = step / 32
                inverse = 1 - t
                xs.append(
                    inverse * inverse * current[0]
                    + 2 * inverse * t * control[0]
                    + t * t * end[0]
                )
                ys.append(
                    inverse * inverse * current[1]
                    + 2 * inverse * t * control[1]
                    + t * t * end[1]
                )
            current = end
        elif command.command == "curve":
            assert (
                current is not None
                and command.control1 is not None
                and command.control2 is not None
                and command.to is not None
            )
            control1 = command.control1
            control2 = command.control2
            end = command.to
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

    minimum_x, maximum_x = min(xs), max(xs)
    minimum_y, maximum_y = min(ys), max(ys)
    return (
        minimum_x <= _FRAME_EDGE_TOLERANCE
        and minimum_y <= _FRAME_EDGE_TOLERANCE
        and maximum_x >= 1 - _FRAME_EDGE_TOLERANCE
        and maximum_y >= 1 - _FRAME_EDGE_TOLERANCE
    )


@dataclass(frozen=True)
class BoardGeometryPiece:
    frame: NormalizedFrame
    shape: BoardShapeDocument
    treatment: Mapping[str, Any] | None
    shape_constraint: BoardShapeConstraint | None

    @classmethod
    def from_json(cls, value: Any, source: str) -> "BoardGeometryPiece":
        payload = _mapping(value, source)
        _closed(
            payload,
            {"frame", "shape"},
            source,
            optional={"treatment", "shapeConstraint"},
        )
        treatment = None
        if "treatment" in payload:
            treatment_payload = _mapping(payload["treatment"], f"{source}.treatment")
            treatment_type = _string(
                treatment_payload.get("type"), f"{source}.treatment.type"
            )
            if treatment_type not in _TREATMENTS:
                raise ValueError(f"{source}.treatment.type is unsupported")
            expected = {"type"}
            if treatment_type in {"shelf", "recess"}:
                expected.add("rimInsetFraction")
            if treatment_type == "recess":
                expected.add("depth")
            _closed(treatment_payload, expected, f"{source}.treatment")
            if "rimInsetFraction" in treatment_payload:
                inset = _number(
                    treatment_payload["rimInsetFraction"],
                    f"{source}.treatment.rimInsetFraction",
                )
                if not 0 <= inset <= 0.5:
                    raise ValueError(
                        f"{source}.treatment.rimInsetFraction must be in 0...0.5"
                    )
            if treatment_type == "recess" and treatment_payload["depth"] not in _DEPTHS:
                raise ValueError(f"{source}.treatment.depth is unsupported")
            treatment = MappingProxyType(dict(treatment_payload))
        frame = NormalizedFrame.from_json(payload["frame"], f"{source}.frame")
        shape = BoardShapeDocument.from_json(payload["shape"], f"{source}.shape")
        if not _path_fills_declared_frame(shape):
            raise ValueError(f"{source}.frame must match its derived shape bounds")
        return cls(
            frame,
            shape,
            treatment,
            BoardShapeConstraint.from_json(
                payload["shapeConstraint"], f"{source}.shapeConstraint"
            )
            if "shapeConstraint" in payload
            else None,
        )


@dataclass(frozen=True)
class CordPoint:
    x: float
    y: float

    @classmethod
    def from_json(cls, value: Any, source: str) -> "CordPoint":
        payload = _mapping(value, source)
        _closed(payload, {"x", "y"}, source)
        return cls(
            _number(payload["x"], f"{source}.x"),
            _number(payload["y"], f"{source}.y"),
        )


@dataclass(frozen=True)
class CordSize:
    width: float
    height: float

    @classmethod
    def from_json(cls, value: Any, source: str) -> "CordSize":
        payload = _mapping(value, source)
        _closed(payload, {"width", "height"}, source)
        return cls(
            _positive_number(payload["width"], f"{source}.width"),
            _positive_number(payload["height"], f"{source}.height"),
        )


@dataclass(frozen=True)
class CordRect:
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_json(cls, value: Any, source: str) -> "CordRect":
        payload = _mapping(value, source)
        _closed(payload, {"x", "y", "width", "height"}, source)
        return cls(
            _number(payload["x"], f"{source}.x"),
            _number(payload["y"], f"{source}.y"),
            _positive_number(payload["width"], f"{source}.width"),
            _positive_number(payload["height"], f"{source}.height"),
        )


@dataclass(frozen=True)
class DirectTwoAnchorCordRig:
    scene_size: CordSize
    source_frame: CordRect
    inner_face_frame: CordRect
    attachment_points: tuple[CordPoint, CordPoint]
    pull_point: CordPoint
    eyelet_radius: float

    @classmethod
    def from_json(cls, value: Any, source: str) -> "DirectTwoAnchorCordRig":
        payload = _mapping(value, source)
        _closed(
            payload,
            {
                "type",
                "sceneSize",
                "sourceFrame",
                "innerFaceFrame",
                "attachmentPoints",
                "pullPoint",
                "eyeletRadius",
            },
            source,
        )
        rig_type = _string(payload["type"], f"{source}.type")
        if rig_type != "directTwoAnchor":
            raise ValueError(f"{source}.type is unsupported")
        raw_attachment_points = payload["attachmentPoints"]
        if not isinstance(raw_attachment_points, list) or len(raw_attachment_points) != 2:
            raise ValueError(f"{source}.attachmentPoints must contain exactly two points")
        attachment_points = tuple(
            CordPoint.from_json(point, f"{source}.attachmentPoints[{index}]")
            for index, point in enumerate(raw_attachment_points)
        )
        if attachment_points[0] == attachment_points[1]:
            raise ValueError(f"{source}.attachmentPoints must be distinct")
        return cls(
            scene_size=CordSize.from_json(payload["sceneSize"], f"{source}.sceneSize"),
            source_frame=CordRect.from_json(
                payload["sourceFrame"], f"{source}.sourceFrame"
            ),
            inner_face_frame=CordRect.from_json(
                payload["innerFaceFrame"], f"{source}.innerFaceFrame"
            ),
            attachment_points=attachment_points,
            pull_point=CordPoint.from_json(payload["pullPoint"], f"{source}.pullPoint"),
            eyelet_radius=_positive_number(
                payload["eyeletRadius"], f"{source}.eyeletRadius"
            ),
        )


@dataclass(frozen=True)
class BoardPresentation:
    id: str
    name: str
    asset_path: str
    aspect_ratio: float
    is_default: bool
    source_presentation_id: str | None = None
    is_inverted: bool = False
    rotation_degrees: float | None = None
    geometry_rotation_anchor: NormalizedPoint | None = None
    cord_rig: DirectTwoAnchorCordRig | None = None
    available_hold_ids: tuple[str, ...] | None = None

    @property
    def resolved_rotation_degrees(self) -> float:
        return self.rotation_degrees if self.rotation_degrees is not None else (
            180.0 if self.is_inverted else 0.0
        )

    @classmethod
    def from_json(cls, value: Any, source: str) -> "BoardPresentation":
        payload = _mapping(value, source)
        _closed(
            payload,
            {"id", "name", "assetPath", "aspectRatio", "default"},
            source,
            optional={
                "sourcePresentationID",
                "availableHoldIDs",
                "isInverted",
                "rotationDegrees",
                "geometryRotationAnchor",
                "cordRig",
            },
        )
        if "isInverted" in payload and "rotationDegrees" in payload:
            raise ValueError(
                f"{source} must not declare both isInverted and rotationDegrees"
            )
        aspect_ratio = _number(payload["aspectRatio"], f"{source}.aspectRatio")
        if aspect_ratio <= 0:
            raise ValueError(f"{source}.aspectRatio must be positive")
        available_hold_ids: tuple[str, ...] | None = None
        if "availableHoldIDs" in payload:
            raw_available_hold_ids = payload["availableHoldIDs"]
            if not isinstance(raw_available_hold_ids, list) or not raw_available_hold_ids:
                raise ValueError(f"{source}.availableHoldIDs must be a non-empty array")
            available_hold_ids = tuple(
                _identifier(item, f"{source}.availableHoldIDs[{index}]")
                for index, item in enumerate(raw_available_hold_ids)
            )
            if len(set(available_hold_ids)) != len(available_hold_ids):
                raise ValueError(f"{source}.availableHoldIDs must be unique")
        return cls(
            _identifier(payload["id"], f"{source}.id"),
            _string(payload["name"], f"{source}.name"),
            _asset_path(payload["assetPath"], f"{source}.assetPath"),
            aspect_ratio,
            _boolean(payload["default"], f"{source}.default"),
            (
                _identifier(payload["sourcePresentationID"], f"{source}.sourcePresentationID")
                if "sourcePresentationID" in payload
                else None
            ),
            _boolean(payload["isInverted"], f"{source}.isInverted")
            if "isInverted" in payload
            else False,
            _presentation_rotation_degrees(
                payload["rotationDegrees"], f"{source}.rotationDegrees"
            )
            if "rotationDegrees" in payload
            else None,
            NormalizedPoint.from_json(
                payload["geometryRotationAnchor"],
                f"{source}.geometryRotationAnchor",
            )
            if "geometryRotationAnchor" in payload
            else None,
            DirectTwoAnchorCordRig.from_json(payload["cordRig"], f"{source}.cordRig")
            if "cordRig" in payload
            else None,
            available_hold_ids,
        )


@dataclass(frozen=True)
class BoardPosition:
    id: str
    presentation_id: str

    @classmethod
    def from_json(cls, value: Any, source: str) -> "BoardPosition":
        payload = _mapping(value, source)
        _closed(payload, {"id", "presentationID"}, source)
        return cls(
            _identifier(payload["id"], f"{source}.id"),
            _identifier(payload["presentationID"], f"{source}.presentationID"),
        )


class BoardPositionTransitionKind(StrEnum):
    SEAMLESS = "seamless"
    SETUP_REQUIRED = "setupRequired"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class BoardPositionTransition:
    from_position_id: str
    to_position_id: str
    kind: BoardPositionTransitionKind

    @classmethod
    def from_json(cls, value: Any, source: str) -> "BoardPositionTransition":
        payload = _mapping(value, source)
        _closed(payload, {"fromPositionID", "toPositionID", "kind"}, source)
        kind = _string(payload["kind"], f"{source}.kind")
        try:
            transition_kind = BoardPositionTransitionKind(kind)
        except ValueError as error:
            raise ValueError(f"{source}.kind is unsupported") from error
        return cls(
            _identifier(payload["fromPositionID"], f"{source}.fromPositionID"),
            _identifier(payload["toPositionID"], f"{source}.toPositionID"),
            transition_kind,
        )


@dataclass(frozen=True)
class BoardHold:
    id: str
    equipment_object_id: str
    name: str
    kind: str
    sloper: SloperMetadata | None
    geometry: tuple[BoardGeometryPiece, ...]
    size_millimeters: float | None
    depth_range_millimeters: MillimeterRange | None
    grip_type: str | None
    finger_capacity: int | None
    hand_capacity: int | None
    features: tuple[str, ...] | None
    paired_hold_id: str | None
    presentation_id: str

    @property
    def frame(self) -> NormalizedFrame:
        min_x = min(piece.frame.x for piece in self.geometry)
        min_y = min(piece.frame.y for piece in self.geometry)
        max_x = max(piece.frame.x + piece.frame.width for piece in self.geometry)
        max_y = max(piece.frame.y + piece.frame.height for piece in self.geometry)
        return NormalizedFrame(min_x, min_y, max_x - min_x, max_y - min_y)


@dataclass(frozen=True)
class BoardDocument:
    id: str
    facts: Mapping[str, Any]
    equipment_objects: tuple[str, ...]
    holds: tuple[BoardHold, ...]
    presentations: tuple[BoardPresentation, ...]
    positions: tuple[BoardPosition, ...]
    position_transitions: tuple[BoardPositionTransition, ...]

    @property
    def manufacturer(self) -> str:
        return self.facts["manufacturer"]

    @property
    def name(self) -> str:
        return self.facts["name"]

    @property
    def presentation_asset_path(self) -> str:
        """Return the default surface's asset path."""
        return next(
            presentation.asset_path
            for presentation in self.presentations
            if presentation.is_default
        )

    def hold_ids_for_position(self, position_id: str) -> tuple[str, ...]:
        position = next(
            (candidate for candidate in self.positions if candidate.id == position_id),
            None,
        )
        if position is None:
            raise ValueError(f"unknown position id: {position_id}")
        presentation = next(
            candidate
            for candidate in self.presentations
            if candidate.id == position.presentation_id
        )
        canonical_presentation_id = (
            presentation.source_presentation_id or presentation.id
        )
        available_hold_ids = (
            set(presentation.available_hold_ids)
            if presentation.available_hold_ids is not None
            else None
        )
        return tuple(
            hold.id
            for hold in self.holds
            if hold.presentation_id == canonical_presentation_id
            and (available_hold_ids is None or hold.id in available_hold_ids)
        )

    def transition_kind(self, from_id: str, to_id: str) -> str:
        position_ids = {position.id for position in self.positions}
        if from_id not in position_ids:
            raise ValueError(f"unknown position id: {from_id}")
        if to_id not in position_ids:
            raise ValueError(f"unknown position id: {to_id}")
        if from_id == to_id:
            return "same"
        transition = next(
            (
                candidate
                for candidate in self.position_transitions
                if candidate.from_position_id == from_id
                and candidate.to_position_id == to_id
            ),
            None,
        )
        if transition is None:
            return BoardPositionTransitionKind.SETUP_REQUIRED.value
        return transition.kind.value


@dataclass(frozen=True)
class BoardPackage:
    root: Path
    board: BoardDocument


@dataclass(frozen=True)
class BoardInventory:
    packages: tuple[BoardPackage, ...]
    drafts: tuple[Path, ...]


def _load_geometry(value: Any, source: str) -> tuple[BoardGeometryPiece, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{source} must be a non-empty array")
    return tuple(
        BoardGeometryPiece.from_json(item, f"{source}[{index}]")
        for index, item in enumerate(value)
    )


def _load_hold(
    value: Any,
    source: str,
    *,
    presentation_id: str,
) -> BoardHold:
    payload = _mapping(value, source)
    _closed(
        payload,
        {"id", "name", "kind", "geometry"},
        source,
        optional={
            "equipmentObjectID",
            "sizeMillimeters",
            "depthRangeMillimeters",
            "gripType",
            "fingerCapacity",
            "handCapacity",
            "features",
            "sloper",
            "pairedHoldID",
        }
        | {"presentationID"},
    )
    kind = _string(payload["kind"], f"{source}.kind")
    if kind not in _HOLD_KINDS:
        raise ValueError(f"{source}.kind must be one of {sorted(_HOLD_KINDS)}")
    if kind == "sloper":
        sloper = (
            SloperMetadata.from_json(payload["sloper"], f"{source}.sloper")
            if "sloper" in payload
            else None
        )
    else:
        if "sloper" in payload:
            raise ValueError(f"{source}.sloper is only allowed for sloper holds")
        sloper = None
    if kind == "gaston":
        paired_hold_id = _identifier(payload.get("pairedHoldID"), f"{source}.pairedHoldID")
    else:
        if "pairedHoldID" in payload:
            raise ValueError(f"{source}.pairedHoldID is only allowed for gaston holds")
        paired_hold_id = None
    if "sizeMillimeters" in payload and "depthRangeMillimeters" in payload:
        raise ValueError(f"{source} must not specify both a size and depth range")
    size = None
    if "sizeMillimeters" in payload:
        size = _positive_number(payload["sizeMillimeters"], f"{source}.sizeMillimeters")
    depth_range = None
    if "depthRangeMillimeters" in payload:
        depth_range = MillimeterRange.from_json(
            payload["depthRangeMillimeters"], f"{source}.depthRangeMillimeters"
        )
    grip_type = None
    if "gripType" in payload:
        grip_type = _string(payload["gripType"], f"{source}.gripType")
        if grip_type not in _GRIP_TYPES:
            raise ValueError(f"{source}.gripType must be one of {sorted(_GRIP_TYPES)}")
    finger_capacity = None
    if "fingerCapacity" in payload:
        finger_capacity = _positive_integer(
            payload["fingerCapacity"], f"{source}.fingerCapacity"
        )
        if finger_capacity not in range(1, 5):
            raise ValueError(f"{source}.fingerCapacity must be in 1...4")
    hand_capacity = None
    if "handCapacity" in payload:
        hand_capacity = _positive_integer(
            payload["handCapacity"], f"{source}.handCapacity"
        )
        if hand_capacity not in range(1, 3):
            raise ValueError(f"{source}.handCapacity must be in 1...2")
    features = None
    if "features" in payload:
        raw_features = payload["features"]
        if not isinstance(raw_features, list):
            raise ValueError(f"{source}.features must be an array")
        features = tuple(
            _string(feature, f"{source}.features[{index}]")
            for index, feature in enumerate(raw_features)
        )
        if any(feature not in _HOLD_FEATURES for feature in features):
            raise ValueError(f"{source}.features contains an unsupported feature")
        if len(features) != len(set(features)):
            raise ValueError(f"{source}.features must be unique")
    return BoardHold(
        _identifier(payload["id"], f"{source}.id"),
        _identifier(
            payload.get("equipmentObjectID", "primary"),
            f"{source}.equipmentObjectID",
        ),
        _string(payload["name"], f"{source}.name"),
        kind,
        sloper,
        _load_geometry(payload["geometry"], f"{source}.geometry"),
        size,
        depth_range,
        grip_type,
        finger_capacity,
        hand_capacity,
        features,
        paired_hold_id,
        presentation_id,
    )


def _load_presentations(value: Any, source: str) -> tuple[BoardPresentation, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{source} must be a non-empty array")
    presentations = tuple(
        BoardPresentation.from_json(item, f"{source}[{index}]")
        for index, item in enumerate(value)
    )
    if len({presentation.id for presentation in presentations}) != len(presentations):
        raise ValueError("duplicate presentation id")
    if sum(presentation.is_default for presentation in presentations) != 1:
        raise ValueError("board.json.presentations must have exactly one default presentation")
    return presentations


def project_normalized_point(
    point: NormalizedPoint, anchor: NormalizedPoint
) -> tuple[float, float]:
    return (2 * anchor.x - point.x, 2 * anchor.y - point.y)


def _rotate_point(
    x: float,
    y: float,
    *,
    anchor_x: float,
    anchor_y: float,
    rotation_degrees: float,
) -> tuple[float, float]:
    radians = math.radians(rotation_degrees)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    delta_x = x - anchor_x
    delta_y = y - anchor_y
    return (
        anchor_x + cosine * delta_x - sine * delta_y,
        anchor_y + sine * delta_x + cosine * delta_y,
    )


def _validate_direct_two_anchor_cord_presentation(
    rig: DirectTwoAnchorCordRig,
    *,
    presentation_id: str,
    rotation_degrees: float,
    rotation_anchor: NormalizedPoint,
) -> None:
    pull_x = rig.source_frame.x + rig.pull_point.x
    pull_y = rig.source_frame.y + rig.pull_point.y
    anchor_x = rotation_anchor.x * rig.scene_size.width
    anchor_y = rotation_anchor.y * rig.scene_size.height
    attachments = tuple(
        _rotate_point(
            rig.source_frame.x + point.x,
            rig.source_frame.y + point.y,
            anchor_x=anchor_x,
            anchor_y=anchor_y,
            rotation_degrees=rotation_degrees,
        )
        for point in rig.attachment_points
    )
    centerline_x = (
        pull_x + _CORD_SUPPORT_MIN_X_OFFSET,
        pull_x + _CORD_SUPPORT_MAX_X_OFFSET,
        pull_x - _CORD_PULL_EXIT_HALF_SPACING,
        pull_x + _CORD_PULL_EXIT_HALF_SPACING,
        *(point[0] for point in attachments),
    )
    centerline_y = (
        pull_y + _CORD_SUPPORT_MIN_Y_OFFSET,
        pull_y + _CORD_SUPPORT_MAX_Y_OFFSET,
        *(point[1] for point in attachments),
    )
    tolerance = max(rig.scene_size.width, rig.scene_size.height) * 1e-9
    if (
        min(centerline_x) - _CORD_SHADOW_X_MARGIN < -tolerance
        or max(centerline_x) + _CORD_SHADOW_X_MARGIN
        > rig.scene_size.width + tolerance
        or min(centerline_y) - _CORD_SHADOW_Y_MARGIN < -tolerance
        or max(centerline_y) + _CORD_SHADOW_Y_MARGIN
        > rig.scene_size.height + tolerance
    ):
        raise ValueError(
            f"presentation {presentation_id} cord drawing must remain inside sceneSize"
        )
    if any(point[1] <= pull_y + tolerance for point in attachments):
        raise ValueError(
            f"presentation {presentation_id} cord pull exits must remain above "
            "both attachment points"
        )


def _rigged_alias_frame_is_inside_canvas(
    frame: NormalizedFrame,
    rig: DirectTwoAnchorCordRig,
    anchor: NormalizedPoint,
    rotation_degrees: float,
) -> bool:
    face_min_x = rig.source_frame.x + rig.inner_face_frame.x
    face_min_y = rig.source_frame.y + rig.inner_face_frame.y
    pivot_x = anchor.x * rig.scene_size.width
    pivot_y = anchor.y * rig.scene_size.height
    corners = (
        (frame.x, frame.y),
        (frame.x + frame.width, frame.y),
        (frame.x, frame.y + frame.height),
        (frame.x + frame.width, frame.y + frame.height),
    )
    tolerance = max(rig.scene_size.width, rig.scene_size.height) * 1e-12
    for normalized_x, normalized_y in corners:
        face_x = face_min_x + normalized_x * rig.inner_face_frame.width
        face_y = face_min_y + normalized_y * rig.inner_face_frame.height
        projected_x, projected_y = _rotate_point(
            face_x,
            face_y,
            anchor_x=pivot_x,
            anchor_y=pivot_y,
            rotation_degrees=rotation_degrees,
        )
        if (
            projected_x < -tolerance
            or projected_y < -tolerance
            or projected_x > rig.scene_size.width + tolerance
            or projected_y > rig.scene_size.height + tolerance
        ):
            return False
    return True


def _validate_alias_presentations(
    presentations: tuple[BoardPresentation, ...], holds: tuple[BoardHold, ...]
) -> None:
    presentations_by_id = {presentation.id: presentation for presentation in presentations}
    for presentation in presentations:
        if presentation.cord_rig is not None:
            if (
                presentation.source_presentation_id is not None
                or presentation.resolved_rotation_degrees != 0
            ):
                raise ValueError(
                    f"presentation {presentation.id}.cordRig must be owned by a "
                    "canonical non-inverted presentation"
                )
            scene_aspect_ratio = (
                presentation.cord_rig.scene_size.width
                / presentation.cord_rig.scene_size.height
            )
            scene_aspect_error = (
                f"presentation {presentation.id}.aspectRatio must match "
                "cordRig.sceneSize within 0.1%"
            )
            if not math.isfinite(scene_aspect_ratio) or scene_aspect_ratio <= 0:
                raise ValueError(scene_aspect_error)
            relative_error = (
                abs(presentation.aspect_ratio - scene_aspect_ratio)
                / scene_aspect_ratio
            )
            if relative_error > _ASPECT_RATIO_RELATIVE_TOLERANCE:
                raise ValueError(scene_aspect_error)
        if (
            presentation.rotation_degrees is not None
            and presentation.source_presentation_id is None
        ):
            raise ValueError(
                f"presentation {presentation.id}.rotationDegrees requires sourcePresentationID"
            )
        if presentation.geometry_rotation_anchor is not None:
            if presentation.source_presentation_id is None:
                raise ValueError(
                    f"presentation {presentation.id}.geometryRotationAnchor requires sourcePresentationID"
                )
            if presentation.resolved_rotation_degrees == 0:
                raise ValueError(
                    f"presentation {presentation.id}.geometryRotationAnchor requires isInverted true or nonzero rotationDegrees"
                )
        if presentation.source_presentation_id is None:
            if presentation.cord_rig is not None:
                _validate_direct_two_anchor_cord_presentation(
                    presentation.cord_rig,
                    presentation_id=presentation.id,
                    rotation_degrees=presentation.resolved_rotation_degrees,
                    rotation_anchor=presentation.geometry_rotation_anchor
                    or NormalizedPoint(0.5, 0.5),
                )
            continue

        source = presentations_by_id.get(presentation.source_presentation_id)
        if (
            source is None
            or source.source_presentation_id is not None
            or source.id == presentation.id
        ):
            raise ValueError(
                f"presentation {presentation.id} must reference a canonical presentation"
            )
        if not math.isclose(
            presentation.aspect_ratio,
            source.aspect_ratio,
            rel_tol=_ALIAS_ASPECT_RATIO_RELATIVE_TOLERANCE,
            abs_tol=_ALIAS_ASPECT_RATIO_ABSOLUTE_TOLERANCE,
        ):
            raise ValueError(
                f"presentation {presentation.id}.aspectRatio must match source presentation aspectRatio"
            )
        if presentation.rotation_degrees is not None:
            if presentation.asset_path != source.asset_path:
                raise ValueError(
                    f"presentation {presentation.id}.assetPath must reuse source "
                    "presentation assetPath for an explicit rotation"
                )
            if presentation.rotation_degrees not in (0, 180) and source.cord_rig is None:
                raise ValueError(
                    f"presentation {presentation.id} non-180 rotation requires a "
                    "canonical cordRig to prevent artwork clipping"
                )
        rotation_degrees = presentation.resolved_rotation_degrees
        if source.cord_rig is not None:
            _validate_direct_two_anchor_cord_presentation(
                source.cord_rig,
                presentation_id=presentation.id,
                rotation_degrees=rotation_degrees,
                rotation_anchor=presentation.geometry_rotation_anchor
                or NormalizedPoint(0.5, 0.5),
            )
        if rotation_degrees == 0:
            continue

        anchor = presentation.geometry_rotation_anchor or NormalizedPoint(0.5, 0.5)
        resolved_cord_rig = source.cord_rig
        available_hold_ids = (
            set(presentation.available_hold_ids)
            if presentation.available_hold_ids is not None
            else None
        )
        for hold in holds:
            if hold.presentation_id != source.id:
                continue
            if available_hold_ids is not None and hold.id not in available_hold_ids:
                continue
            for piece in hold.geometry:
                frame = piece.frame
                if resolved_cord_rig is not None:
                    if not _rigged_alias_frame_is_inside_canvas(
                        frame, resolved_cord_rig, anchor, rotation_degrees
                    ):
                        raise ValueError(
                            f"presentation {presentation.id} projects source hold "
                            "geometry outside the normalized canvas"
                        )
                    continue
                corners = (
                    (frame.x, frame.y),
                    (frame.x + frame.width, frame.y),
                    (frame.x, frame.y + frame.height),
                    (frame.x + frame.width, frame.y + frame.height),
                )
                projected_corners = (
                    _rotate_point(
                        x,
                        y,
                        anchor_x=anchor.x,
                        anchor_y=anchor.y,
                        rotation_degrees=rotation_degrees,
                    )
                    for x, y in corners
                )
                if any(
                    projected_x < -_PROJECTED_FRAME_EDGE_TOLERANCE
                    or projected_y < -_PROJECTED_FRAME_EDGE_TOLERANCE
                    or projected_x > 1 + _PROJECTED_FRAME_EDGE_TOLERANCE
                    or projected_y > 1 + _PROJECTED_FRAME_EDGE_TOLERANCE
                    for projected_x, projected_y in projected_corners
                ):
                    raise ValueError(
                        f"presentation {presentation.id} projects source hold geometry outside the normalized canvas"
                    )


def _load_positions(
    value: Any,
    source: str,
    *,
    presentations: tuple[BoardPresentation, ...],
) -> tuple[BoardPosition, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{source} must be a non-empty array")
    positions = tuple(
        BoardPosition.from_json(item, f"{source}[{index}]")
        for index, item in enumerate(value)
    )
    if len({position.id for position in positions}) != len(positions):
        raise ValueError("duplicate position id")
    presentation_ids = {presentation.id for presentation in presentations}
    for position in positions:
        if position.presentation_id not in presentation_ids:
            raise ValueError(
                f"position {position.id} references unknown presentationID"
            )
    return positions


def _load_position_transitions(
    value: Any,
    source: str,
    *,
    positions: tuple[BoardPosition, ...],
) -> tuple[BoardPositionTransition, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{source} must be an array")
    transitions = tuple(
        BoardPositionTransition.from_json(item, f"{source}[{index}]")
        for index, item in enumerate(value)
    )
    position_ids = {position.id for position in positions}
    for transition in transitions:
        if transition.from_position_id not in position_ids:
            raise ValueError("position transition references unknown fromPositionID")
        if transition.to_position_id not in position_ids:
            raise ValueError("position transition references unknown toPositionID")
        if transition.from_position_id == transition.to_position_id:
            raise ValueError("position transition must not be self-edge")
    if len(
        {
            (transition.from_position_id, transition.to_position_id)
            for transition in transitions
        }
    ) != len(transitions):
        raise ValueError("duplicate position transition")
    return transitions


def _load_board(value: Mapping[str, Any]) -> BoardDocument:
    required = {
        "id",
        "manufacturer",
        "name",
        "subtitle",
        "productURL",
        "aspectRatio",
        "presentations",
        "holds",
    }
    _closed(
        value,
        required,
        "board.json",
        optional={"dimensions", "equipmentObjects", "positions", "positionTransitions"},
    )
    facts: dict[str, Any] = {}
    for key in ("manufacturer", "name", "subtitle", "productURL"):
        facts[key] = _string(value[key], f"board.json.{key}")
    if "dimensions" in value:
        facts["dimensions"] = _string(value["dimensions"], "board.json.dimensions")
    facts["aspectRatio"] = _number(value["aspectRatio"], "board.json.aspectRatio")
    if facts["aspectRatio"] <= 0:
        raise ValueError("board.json.aspectRatio must be positive")
    raw_equipment_objects = value.get("equipmentObjects", [{"id": "primary"}])
    if not isinstance(raw_equipment_objects, list) or not raw_equipment_objects:
        raise ValueError("board.json.equipmentObjects must be a non-empty array")
    equipment_objects = tuple(
        _identifier(
            _mapping(item, f"board.json.equipmentObjects[{index}]").get("id"),
            f"board.json.equipmentObjects[{index}].id",
        )
        for index, item in enumerate(raw_equipment_objects)
    )
    for index, item in enumerate(raw_equipment_objects):
        source = f"board.json.equipmentObjects[{index}]"
        equipment_object = _mapping(item, source)
        _closed(
            equipment_object,
            {"id"},
            source,
            optional={"missingHandCapacityPolicy"},
        )
        if "missingHandCapacityPolicy" in equipment_object:
            policy = _string(
                equipment_object["missingHandCapacityPolicy"],
                f"{source}.missingHandCapacityPolicy",
            )
            if policy not in {"legacyBilateral", "unavailable"}:
                raise ValueError(
                    f"{source}.missingHandCapacityPolicy must be legacyBilateral or unavailable"
                )
    if len(set(equipment_objects)) != len(equipment_objects):
        raise ValueError("duplicate equipment object id")
    presentations = _load_presentations(value["presentations"], "board.json.presentations")
    positions = (
        _load_positions(
            value["positions"],
            "board.json.positions",
            presentations=presentations,
        )
        if "positions" in value
        else tuple(
            BoardPosition(presentation.id, presentation.id)
            for presentation in presentations
        )
    )
    position_transitions = (
        _load_position_transitions(
            value["positionTransitions"],
            "board.json.positionTransitions",
            positions=positions,
        )
        if "positionTransitions" in value
        else ()
    )
    raw_holds = value["holds"]
    if not isinstance(raw_holds, list) or not raw_holds:
        raise ValueError("board.json.holds must be a non-empty array")
    presentation_ids = {presentation.id for presentation in presentations}
    canonical_presentation_ids = {
        presentation.id
        for presentation in presentations
        if presentation.source_presentation_id is None
    }
    holds: list[BoardHold] = []
    for index, item in enumerate(raw_holds):
        source = f"board.json.holds[{index}]"
        payload = _mapping(item, source)
        presentation_id = _identifier(
            payload.get("presentationID"), f"{source}.presentationID"
        )
        if presentation_id not in presentation_ids:
            raise ValueError(f"{source}.presentationID is an unknown presentationID")
        if presentation_id not in canonical_presentation_ids:
            raise ValueError(
                f"{source}.presentationID must be owned by a canonical presentation"
            )
        holds.append(
            _load_hold(
                payload,
                source,
                presentation_id=presentation_id,
            )
        )
    holds_tuple = tuple(holds)
    if len({hold.id for hold in holds_tuple}) != len(holds_tuple):
        raise ValueError("duplicate physical hold id")
    holds_by_id = {hold.id: hold for hold in holds_tuple}
    for presentation in presentations:
        if presentation.available_hold_ids is None:
            continue
        canonical_presentation_id = (
            presentation.source_presentation_id or presentation.id
        )
        for hold_id in presentation.available_hold_ids:
            hold = holds_by_id.get(hold_id)
            if hold is None:
                raise ValueError(
                    f"presentation {presentation.id}.availableHoldIDs references "
                    f"unknown hold {hold_id}"
                )
            if hold.presentation_id != canonical_presentation_id:
                raise ValueError(
                    f"presentation {presentation.id}.availableHoldIDs hold {hold_id} "
                    f"must belong to canonical presentation {canonical_presentation_id}"
                )
    _validate_alias_presentations(presentations, holds_tuple)
    equipment_object_ids = set(equipment_objects)
    for hold in holds_tuple:
        if hold.equipment_object_id not in equipment_object_ids:
            raise ValueError(
                f"hold {hold.id} references unknown equipment object {hold.equipment_object_id}"
            )
    owned_equipment_object_ids = {hold.equipment_object_id for hold in holds_tuple}
    for equipment_object_id in equipment_objects:
        if equipment_object_id not in owned_equipment_object_ids:
            raise ValueError(
                f"equipment object {equipment_object_id} must own at least one hold"
            )
    for hold in holds_tuple:
        if hold.kind != "gaston":
            continue
        if hold.paired_hold_id == hold.id or hold.paired_hold_id not in holds_by_id:
            raise ValueError(f"gaston hold {hold.id} must pair with a distinct existing hold")
        paired_hold = holds_by_id[hold.paired_hold_id]
        if paired_hold.kind != "gaston" or paired_hold.paired_hold_id != hold.id:
            raise ValueError(f"gaston hold {hold.id} must have a reciprocal gaston pair")
    presentations_by_id = {presentation.id: presentation for presentation in presentations}
    canonical_presentation_ids_with_holds = {hold.presentation_id for hold in holds_tuple}
    for position in positions:
        presentation = presentations_by_id[position.presentation_id]
        canonical_presentation_id = presentation.source_presentation_id or presentation.id
        if canonical_presentation_id not in canonical_presentation_ids_with_holds:
            raise ValueError(
                f"position {position.id} canonical presentation "
                f"{canonical_presentation_id} must own at least one hold"
            )
    return BoardDocument(
        _identifier(value["id"], "board.json.id"),
        MappingProxyType(facts),
        equipment_objects,
        holds_tuple,
        presentations,
        positions,
        position_transitions,
    )


def _validate_finished_shape(root: Path, board: BoardDocument) -> None:
    _require_no_symlinks(root)
    entries = {item.name for item in root.iterdir()}
    unknown = entries - _PACKAGE_ENTRIES
    missing = _PACKAGE_ENTRIES - entries
    if unknown:
        raise ValueError(f"unknown package entry: {sorted(unknown)[0]}")
    if missing:
        raise ValueError(f"board package is missing: {sorted(missing)[0]}")
    board_path = root / "board.json"
    assets = root / "assets"
    if board_path.is_symlink() or not board_path.is_file():
        raise ValueError("board.json must be a regular non-symlink file")
    if assets.is_symlink() or not assets.is_dir():
        raise ValueError("assets must be a regular non-symlink directory")
    expected_assets = {presentation.asset_path for presentation in board.presentations}
    actual_assets = {
        item.relative_to(root).as_posix() for item in assets.rglob("*") if item.is_file()
    }
    unknown_assets = actual_assets - expected_assets
    missing_assets = expected_assets - actual_assets
    if unknown_assets:
        raise ValueError(f"undeclared presentation asset: {sorted(unknown_assets)[0]}")
    if missing_assets:
        raise ValueError(
            f"missing declared presentation asset: {sorted(missing_assets)[0]}"
        )
    image_dimensions: dict[str, tuple[int, int]] = {}
    for asset_path in sorted(expected_assets):
        asset = root / asset_path
        if asset.is_symlink() or not asset.is_file():
            raise ValueError(f"{asset_path} must be a regular non-symlink file")
        image_dimensions[asset_path] = _validate_png_structure(asset, asset_path)
    presentations_by_id = {
        presentation.id: presentation for presentation in board.presentations
    }
    for presentation in board.presentations:
        width, height = image_dimensions[presentation.asset_path]
        image_aspect_ratio = width / height
        canonical = (
            presentations_by_id[presentation.source_presentation_id]
            if presentation.source_presentation_id is not None
            else presentation
        )
        expected_image_aspect_ratio = presentation.aspect_ratio
        aspect_source = f"board.json.presentations[{presentation.id}].aspectRatio"
        if canonical.cord_rig is not None:
            expected_image_aspect_ratio = (
                canonical.cord_rig.inner_face_frame.width
                / canonical.cord_rig.inner_face_frame.height
            )
            aspect_source = (
                f"board.json.presentations[{canonical.id}].cordRig.innerFaceFrame "
                "aspect ratio"
            )
        relative_error = (
            abs(expected_image_aspect_ratio - image_aspect_ratio) / image_aspect_ratio
        )
        if relative_error > _ASPECT_RATIO_RELATIVE_TOLERANCE:
            raise ValueError(
                f"{aspect_source} must match its image width/height within 0.1%"
            )


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _validate_png_structure(path: Path, asset_path: str) -> tuple[int, int]:
    """Validate PNG framing without depending on a third-party image library.

    This module is loaded by a bare system interpreter during Xcode's board
    staging build phase, which installs no dependencies, so validation stays
    within the standard library rather than requiring Pillow.
    """
    try:
        data = path.read_bytes()
    except OSError as error:
        raise ValueError(f"{asset_path} must be a readable file") from error

    if data[:8] != _PNG_SIGNATURE:
        raise ValueError(f"{asset_path} must be a PNG image")

    offset = 8
    seen_ihdr = False
    seen_idat = False
    width = height = None
    bit_depth = color_type = interlace_method = None
    idat_parts: list[bytes] = []
    transparency: bytes | None = None
    try:
        while offset < len(data):
            if offset + 8 > len(data):
                raise ValueError(f"{asset_path} has a truncated chunk header")
            length, chunk_type = struct.unpack_from(">I4s", data, offset)
            body_start = offset + 8
            body_end = body_start + length
            crc_end = body_end + 4
            if crc_end > len(data):
                raise ValueError(f"{asset_path} has a truncated chunk body")
            body = data[body_start:body_end]
            (declared_crc,) = struct.unpack_from(">I", data, body_end)
            actual_crc = zlib.crc32(chunk_type + body) & 0xFFFFFFFF
            if declared_crc != actual_crc:
                raise ValueError(f"{asset_path} has a corrupt chunk checksum")
            if not seen_ihdr:
                if chunk_type != b"IHDR":
                    raise ValueError(f"{asset_path} must start with an IHDR chunk")
                if len(body) != 13:
                    raise ValueError(f"{asset_path} has a malformed IHDR chunk")
                (
                    width,
                    height,
                    bit_depth,
                    color_type,
                    _compression_method,
                    _filter_method,
                    interlace_method,
                ) = struct.unpack(">IIBBBBB", body)
                seen_ihdr = True
            if chunk_type == b"IDAT":
                seen_idat = True
                idat_parts.append(body)
            if chunk_type == b"tRNS":
                transparency = body
            if chunk_type == b"IEND":
                if body:
                    raise ValueError(f"{asset_path} has a malformed IEND chunk")
                if not seen_idat:
                    raise ValueError(f"{asset_path} must contain image data")
                if crc_end != len(data):
                    raise ValueError(f"{asset_path} has trailing data after IEND")
                if width is None or height is None or width <= 0 or height <= 0:
                    raise ValueError(f"{asset_path} must declare positive dimensions")
                if asset_path == "assets/primary.png":
                    _validate_primary_png_decoding(
                        width=width,
                        height=height,
                        bit_depth=bit_depth,
                        color_type=color_type,
                        interlace_method=interlace_method,
                        idat_parts=idat_parts,
                        transparency=transparency,
                        asset_path=asset_path,
                    )
                return width, height
            offset = crc_end
    except struct.error as error:
        raise ValueError(f"{asset_path} must be a decodable PNG image") from error

    raise ValueError(f"{asset_path} is missing its IEND chunk")


def _validate_primary_png_decoding(
    *,
    width: int,
    height: int,
    bit_depth: int | None,
    color_type: int | None,
    interlace_method: int | None,
    idat_parts: list[bytes],
    transparency: bytes | None,
    asset_path: str,
) -> None:
    """Validate decoded primary PNG image data using only the stdlib."""
    channels_by_color_type = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    channels = channels_by_color_type.get(color_type)
    if channels is None or bit_depth not in {1, 2, 4, 8, 16}:
        raise ValueError(f"{asset_path} has an unsupported PNG color format")
    if color_type in {2, 4, 6} and bit_depth not in {8, 16}:
        raise ValueError(f"{asset_path} has an unsupported PNG bit depth")
    if interlace_method != 0:
        raise ValueError(f"{asset_path} must be non-interlaced for PNG validation")

    bits_per_pixel = channels * bit_depth
    stride = (width * bits_per_pixel + 7) // 8
    filter_bytes_per_pixel = max(1, (bits_per_pixel + 7) // 8)
    expected_size = height * (stride + 1)
    decompressor = zlib.decompressobj()
    pending = bytearray()
    previous = bytes(stride)
    row_count = 0
    decoded_size = 0
    transparent_pixel_found = False

    def consume(decoded: bytes) -> None:
        nonlocal decoded_size, pending, previous, row_count, transparent_pixel_found
        decoded_size += len(decoded)
        pending.extend(decoded)
        offset = 0
        while len(pending) - offset >= stride + 1:
            if row_count >= height:
                raise ValueError(f"{asset_path} has malformed image data")
            filter_type = pending[offset]
            row_start = offset + 1
            row_end = row_start + stride
            if filter_type not in {0, 1, 2, 3, 4}:
                raise ValueError(f"{asset_path} has an invalid PNG row filter")
            if not transparent_pixel_found:
                row = _unfilter_png_row(
                    bytes(pending[row_start:row_end]),
                    previous,
                    filter_type,
                    filter_bytes_per_pixel,
                    asset_path,
                )
                transparent_pixel_found = _row_has_alpha_zero(
                    row=row,
                    width=width,
                    bit_depth=bit_depth,
                    color_type=color_type,
                    transparency=transparency,
                )
                previous = row
            row_count += 1
            offset = row_end
        if offset:
            del pending[:offset]

    try:
        for idat_part in idat_parts:
            consume(decompressor.decompress(idat_part))
        consume(decompressor.flush())
    except zlib.error as error:
        raise ValueError(f"{asset_path} must contain decodable image data") from error

    if (
        not decompressor.eof
        or decompressor.unused_data
        or decoded_size != expected_size
        or row_count != height
        or pending
    ):
        raise ValueError(f"{asset_path} has malformed image data")


def _row_has_alpha_zero(
    *,
    row: bytes,
    width: int,
    bit_depth: int,
    color_type: int,
    transparency: bytes | None,
) -> bool:
    if color_type == 6:
        sample_bytes = bit_depth // 8
        pixel_bytes = 4 * sample_bytes
        alpha_offset = 3 * sample_bytes
        return any(
            all(row[index + alpha_offset + byte] == 0 for byte in range(sample_bytes))
            for index in range(0, len(row), pixel_bytes)
        )
    if color_type == 4:
        sample_bytes = bit_depth // 8
        pixel_bytes = 2 * sample_bytes
        alpha_offset = sample_bytes
        return any(
            all(row[index + alpha_offset + byte] == 0 for byte in range(sample_bytes))
            for index in range(0, len(row), pixel_bytes)
        )
    if transparency is None:
        return False
    if color_type == 3:
        transparent_indices = {
            index for index, alpha in enumerate(transparency) if alpha == 0
        }
        return any(
            sample in transparent_indices
            for sample in _unpack_png_samples(row, bit_depth, width)
        )
    if color_type == 0 and len(transparency) == 2:
        (transparent_gray,) = struct.unpack(">H", transparency)
        return any(
            sample == transparent_gray
            for sample in _unpack_png_samples(row, bit_depth, width)
        )
    if color_type == 2 and len(transparency) == 6:
        transparent_rgb = struct.unpack(">HHH", transparency)
        sample_bytes = bit_depth // 8
        return any(
            tuple(
                int.from_bytes(
                    row[index + channel * sample_bytes : index + (channel + 1) * sample_bytes],
                    "big",
                )
                for channel in range(3)
            )
            == transparent_rgb
            for index in range(0, len(row), 3 * sample_bytes)
        )
    return False


def _unfilter_png_row(
    filtered: bytes,
    previous: bytes,
    filter_type: int,
    bytes_per_pixel: int,
    asset_path: str,
) -> bytes:
    row = bytearray(len(filtered))
    for index, value in enumerate(filtered):
        left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        above = previous[index]
        upper_left = (
            previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        )
        if filter_type == 0:
            predictor = 0
        elif filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = above
        elif filter_type == 3:
            predictor = (left + above) // 2
        elif filter_type == 4:
            predictor = _paeth_predictor(left, above, upper_left)
        else:
            raise ValueError(f"{asset_path} has an invalid PNG row filter")
        row[index] = (value + predictor) & 0xFF
    return bytes(row)


def _paeth_predictor(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    left_distance = abs(estimate - left)
    above_distance = abs(estimate - above)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def _unpack_png_samples(row: bytes, bit_depth: int, width: int) -> tuple[int, ...]:
    if bit_depth == 8:
        return tuple(row[:width])
    if bit_depth == 16:
        return tuple(
            int.from_bytes(row[index : index + 2], "big")
            for index in range(0, width * 2, 2)
        )
    mask = (1 << bit_depth) - 1
    return tuple(
        (row[(index * bit_depth) // 8] >> (8 - bit_depth - (index * bit_depth) % 8))
        & mask
        for index in range(width)
    )


def load_board_package(package_root: Path) -> BoardPackage:
    root = Path(package_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"board package does not exist as a regular directory: {root}")
    _require_no_symlinks(root)
    board = _load_board(_load_json(root / "board.json", "board.json"))
    _validate_finished_shape(root, board)
    return BoardPackage(root.resolve(), board)


def is_primary_only_draft(root: Path) -> bool:
    """Return whether *root* has exactly ``assets/primary.png`` and no manifest.

    Raises ``ValueError`` when the sole primary PNG is malformed.
    """
    _require_no_symlinks(root)
    if {item.name for item in root.iterdir()} != {"assets"}:
        return False
    assets = root / "assets"
    if assets.is_symlink() or not assets.is_dir():
        return False
    if {item.name for item in assets.iterdir()} != {"primary.png"}:
        return False
    primary = assets / "primary.png"
    if not primary.is_file() or primary.is_symlink():
        return False
    _validate_png_structure(primary, "assets/primary.png")
    return True


def _sort_key(package: BoardPackage) -> tuple[str, str, str, str, str, str]:
    board = package.board
    return (
        board.manufacturer.casefold(),
        board.manufacturer,
        board.name.casefold(),
        board.name,
        board.id.casefold(),
        board.id,
    )


def discover_board_packages(
    hangboards_root: Path,
    *,
    require_complete_inventory: bool = False,
) -> BoardInventory:
    root = Path(hangboards_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"Hangboards root must be a regular non-symlink directory: {root}")
    packages: list[BoardPackage] = []
    drafts: list[Path] = []
    identifiers: set[str] = set()
    for entry in sorted(root.iterdir(), key=lambda path: path.name):
        if entry.is_symlink():
            raise ValueError(f"Hangboards direct child must not be a symlink: {entry}")
        if not entry.is_dir():
            continue
        if not is_board_package_slug(entry.name):
            raise ValueError(f"Hangboards directory name is invalid: {entry.name}")
        board_path = entry / "board.json"
        if board_path.exists() or board_path.is_symlink():
            package = load_board_package(entry)
            if package.board.id in identifiers:
                raise ValueError(f"duplicate board id: {package.board.id}")
            identifiers.add(package.board.id)
            packages.append(package)
            continue
        if is_primary_only_draft(entry):
            if require_complete_inventory:
                raise ValueError(f"Hangboards/{entry.name} is missing board.json")
            drafts.append(entry.resolve())
            continue
        raise ValueError(f"Hangboards/{entry.name} is missing board.json")
    packages.sort(key=_sort_key)
    drafts.sort(key=lambda path: path.name)
    return BoardInventory(tuple(packages), tuple(drafts))
