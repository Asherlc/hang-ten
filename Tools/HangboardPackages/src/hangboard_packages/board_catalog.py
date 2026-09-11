"""Fail-closed discovery and validation for single-file hangboard packages."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
import hashlib
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
    from .board_geometry_schema import BoardShapeDocument, NormalizedFrame
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


def _canonical_member_order(
    payload: Mapping[str, Any], expected: tuple[str, ...], source: str
) -> None:
    if tuple(payload) != expected:
        raise ValueError(f"{source} must use canonical member order")


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


def _boolean(value: Any, source: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{source} must be a boolean")
    return value


def _asset_path(value: Any, source: str) -> str:
    return _typed_asset_path(value, source, ".png", "a PNG")


def _typed_asset_path(value: Any, source: str, suffix: str, label: str) -> str:
    asset_path = _string(value, source)
    path = PurePosixPath(asset_path)
    if (
        path.is_absolute()
        or path.parts[:1] != ("assets",)
        or len(path.parts) < 2
        or any(part in {".", ".."} for part in path.parts)
        or path.as_posix() != asset_path
        or not asset_path.endswith(suffix)
    ):
        raise ValueError(f"{source} must name {label} beneath assets/")
    return asset_path


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} does not exist as a regular file: {path}")
    try:
        return _mapping(
            json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_json_keys,
            ),
            label,
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"{label} is invalid JSON: {path}") from error


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


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
class PresentationMediaRaster:
    asset_path: str
    hold_geometry: Mapping[str, tuple[BoardGeometryPiece, ...]]


@dataclass(frozen=True)
class PresentationMediaModel:
    asset_path: str
    descriptor_path: str
    display: Mapping[str, Any]
    suspension: "BoardModelSuspension | None" = None


PresentationMedia = PresentationMediaRaster | PresentationMediaModel


@dataclass(frozen=True)
class BoardModelAttachment:
    node_id: str
    point_in_model: tuple[float, float, float]
    provenance: str


@dataclass(frozen=True)
class BoardModelInvisibleAnchor:
    offset_from_board_bounds: tuple[float, float, float]
    visibility: str
    provenance: str


@dataclass(frozen=True)
class BoardModelCord:
    rest_length: float
    radius: float
    material: str
    provenance: str


@dataclass(frozen=True)
class BoardModelCanonicalPose:
    rotation: tuple[float, float, float, float]
    translation: tuple[float, float, float]
    camera: Mapping[str, Any]


@dataclass(frozen=True)
class BoardModelSingleCordSuspension:
    attachment: BoardModelAttachment
    anchor: BoardModelInvisibleAnchor
    cord: BoardModelCord
    canonical_poses: Mapping[str, BoardModelCanonicalPose]


@dataclass(frozen=True)
class BoardModelPassage:
    id: str
    node_id: str
    point_in_model: tuple[float, float, float]
    provenance: str


@dataclass(frozen=True)
class BoardModelPassagePairs:
    left: tuple[BoardModelPassage, BoardModelPassage]
    right: tuple[BoardModelPassage, BoardModelPassage]


@dataclass(frozen=True)
class BoardModelCordBranch:
    id: str
    passage_ids: tuple[str, str]
    rest_length: float
    radius: float
    material: str
    provenance: str


@dataclass(frozen=True)
class BoardModelTwoBranchSuspension:
    passages: BoardModelPassagePairs
    branches: tuple[BoardModelCordBranch, BoardModelCordBranch]
    anchor: BoardModelInvisibleAnchor
    canonical_poses: Mapping[str, BoardModelCanonicalPose]


BoardModelSuspension = BoardModelSingleCordSuspension | BoardModelTwoBranchSuspension


@dataclass(frozen=True)
class BoardPresentation:
    id: str
    name: str
    asset_path: str
    aspect_ratio: float
    is_default: bool
    source_presentation_id: str | None = None
    is_inverted: bool = False
    media: PresentationMedia | None = None

def _load_v2_derivation(
    value: Any, source: str
) -> tuple[str | None, bool]:
    payload = _mapping(value, source)
    derivation_type = _string(payload.get("type"), f"{source}.type")
    if derivation_type == "original":
        _closed(payload, {"type"}, source)
        return None, False
    if derivation_type != "derived":
        raise ValueError(f"{source}.type must be original or derived")
    _closed(payload, {"type", "sourcePresentationID", "isInverted"}, source)
    return (
        _identifier(payload["sourcePresentationID"], f"{source}.sourcePresentationID"),
        _boolean(payload["isInverted"], f"{source}.isInverted"),
    )


def _vector3(value: Any, source: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{source} must contain exactly three coordinates")
    result = tuple(_number(item, f"{source}[{index}]") for index, item in enumerate(value))
    if result == (0.0, 0.0, 0.0):
        raise ValueError(f"{source} must be non-zero")
    return result  # type: ignore[return-value]


def _unit_vector(value: Any, source: str) -> tuple[float, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{source} must be an array")
    return tuple(_number(item, f"{source}[{index}]") for index, item in enumerate(value))


def _finite_vector3(value: Any, source: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{source} must contain exactly three coordinates")
    result = tuple(_number(item, f"{source}[{index}]") for index, item in enumerate(value))
    return result  # type: ignore[return-value]


def _load_model_anchor(value: Any, source: str) -> BoardModelInvisibleAnchor:
    anchor_payload = _mapping(value, source)
    _closed(anchor_payload, {"offsetFromBoardBounds", "visibility", "provenance"}, source)
    visibility = _string(anchor_payload["visibility"], f"{source}.visibility")
    if visibility != "invisible":
        raise ValueError(f"{source}.visibility must be invisible")
    return BoardModelInvisibleAnchor(
        _finite_vector3(anchor_payload["offsetFromBoardBounds"], f"{source}.offsetFromBoardBounds"),
        visibility,
        _string(anchor_payload["provenance"], f"{source}.provenance"),
    )


def _load_model_poses(
    value: Any, source: str, *, canonical_order: bool = False
) -> Mapping[str, BoardModelCanonicalPose]:
    poses_payload = _mapping(value, source)
    if not poses_payload:
        raise ValueError(f"{source} must not be empty")
    poses: dict[str, BoardModelCanonicalPose] = {}
    for position_id, raw_pose in poses_payload.items():
        position_source = f"{source}[{position_id}]"
        position_id = _identifier(position_id, f"{position_source} positionID")
        pose_payload = _mapping(raw_pose, position_source)
        _closed(pose_payload, {"rotation", "translation", "camera"}, position_source)
        if canonical_order:
            _canonical_member_order(
                pose_payload, ("rotation", "translation", "camera"), position_source
            )
        rotation = _unit_vector(pose_payload["rotation"], f"{position_source}.rotation")
        if len(rotation) != 4:
            raise ValueError(f"{position_source}.rotation must contain exactly four coordinates")
        norm = math.sqrt(sum(value * value for value in rotation))
        if not math.isfinite(norm) or abs(norm - 1.0) > 1e-6:
            raise ValueError(f"{position_source}.rotation must be normalized")
        translation = _finite_vector3(pose_payload["translation"], f"{position_source}.translation")
        camera_source = f"{position_source}.camera"
        camera_payload = _mapping(pose_payload["camera"], camera_source)
        _closed(camera_payload, {"viewDirection", "fitPadding"}, camera_source)
        if canonical_order:
            _canonical_member_order(
                camera_payload, ("viewDirection", "fitPadding"), camera_source
            )
        view_direction = _vector3(camera_payload["viewDirection"], f"{camera_source}.viewDirection")
        fit_padding = _positive_number(camera_payload["fitPadding"], f"{camera_source}.fitPadding")
        poses[position_id] = BoardModelCanonicalPose(
            tuple(rotation),
            translation,
            MappingProxyType({"viewDirection": view_direction, "fitPadding": fit_padding}),
        )
    return MappingProxyType(poses)


def _load_model_suspension(value: Any, source: str) -> BoardModelSuspension:
    payload = _mapping(value, source)
    suspension_type = _string(payload.get("type"), f"{source}.type")
    if suspension_type == "twoBranchCord":
        _closed(payload, {"type", "passages", "branches", "anchor", "canonicalPoses"}, source)
        _canonical_member_order(
            payload, ("type", "passages", "branches", "anchor", "canonicalPoses"), source
        )
        passages_source = f"{source}.passages"
        passages_payload = _mapping(payload["passages"], passages_source)
        _closed(passages_payload, {"left", "right"}, passages_source)
        _canonical_member_order(passages_payload, ("left", "right"), passages_source)
        parsed_pairs: dict[str, tuple[BoardModelPassage, BoardModelPassage]] = {}
        all_passage_ids: set[str] = set()
        all_passage_node_ids: set[str] = set()
        for side in ("left", "right"):
            side_source = f"{passages_source}.{side}"
            raw_passages = passages_payload[side]
            if not isinstance(raw_passages, list) or len(raw_passages) != 2:
                raise ValueError(f"{side_source} must contain exactly two passages")
            passages: list[BoardModelPassage] = []
            for index, raw_passage in enumerate(raw_passages):
                passage_source = f"{side_source}[{index}]"
                passage_payload = _mapping(raw_passage, passage_source)
                _closed(passage_payload, {"id", "nodeID", "pointInModel", "provenance"}, passage_source)
                _canonical_member_order(
                    passage_payload, ("id", "nodeID", "pointInModel", "provenance"), passage_source
                )
                passage_id = _identifier(passage_payload["id"], f"{passage_source}.id")
                if passage_id in all_passage_ids:
                    raise ValueError(f"duplicate suspension passage ID: {passage_id}")
                all_passage_ids.add(passage_id)
                node_id = _string(passage_payload["nodeID"], f"{passage_source}.nodeID")
                if node_id in all_passage_node_ids:
                    raise ValueError(f"duplicate suspension passage node ID: {node_id}")
                all_passage_node_ids.add(node_id)
                passages.append(BoardModelPassage(
                    passage_id,
                    node_id,
                    _finite_vector3(passage_payload["pointInModel"], f"{passage_source}.pointInModel"),
                    _string(passage_payload["provenance"], f"{passage_source}.provenance"),
                ))
            parsed_pairs[side] = (passages[0], passages[1])
        passage_pairs = BoardModelPassagePairs(parsed_pairs["left"], parsed_pairs["right"])

        branches_source = f"{source}.branches"
        raw_branches = payload["branches"]
        if not isinstance(raw_branches, list) or len(raw_branches) != 2:
            raise ValueError(f"{branches_source} must contain exactly two branches")
        branches: list[BoardModelCordBranch] = []
        expected_pairs = (
            tuple(passage.id for passage in passage_pairs.left),
            tuple(passage.id for passage in passage_pairs.right),
        )
        branch_ids: set[str] = set()
        for index, raw_branch in enumerate(raw_branches):
            branch_source = f"{branches_source}[{index}]"
            branch_payload = _mapping(raw_branch, branch_source)
            _closed(branch_payload, {"id", "passageIDs", "restLength", "radius", "material", "provenance"}, branch_source)
            _canonical_member_order(
                branch_payload,
                ("id", "passageIDs", "restLength", "radius", "material", "provenance"),
                branch_source,
            )
            branch_id = _identifier(branch_payload["id"], f"{branch_source}.id")
            if branch_id in branch_ids:
                raise ValueError(f"duplicate suspension branch ID: {branch_id}")
            branch_ids.add(branch_id)
            passage_ids_value = branch_payload["passageIDs"]
            if not isinstance(passage_ids_value, list) or len(passage_ids_value) != 2:
                raise ValueError(f"{branch_source}.passageIDs must contain exactly two IDs")
            passage_ids = tuple(_identifier(item, f"{branch_source}.passageIDs[{item_index}]") for item_index, item in enumerate(passage_ids_value))
            if passage_ids != expected_pairs[index]:
                raise ValueError(f"{branch_source}.passageIDs must match its ordered passage pair")
            branches.append(BoardModelCordBranch(
                branch_id,
                passage_ids,  # type: ignore[arg-type]
                _positive_number(branch_payload["restLength"], f"{branch_source}.restLength"),
                _positive_number(branch_payload["radius"], f"{branch_source}.radius"),
                _string(branch_payload["material"], f"{branch_source}.material"),
                _string(branch_payload["provenance"], f"{branch_source}.provenance"),
            ))
        anchor_source = f"{source}.anchor"
        anchor_payload = _mapping(payload["anchor"], anchor_source)
        _closed(anchor_payload, {"offsetFromBoardBounds", "visibility", "provenance"}, anchor_source)
        _canonical_member_order(
            anchor_payload, ("offsetFromBoardBounds", "visibility", "provenance"), anchor_source
        )
        return BoardModelTwoBranchSuspension(
            passage_pairs,
            (branches[0], branches[1]),
            _load_model_anchor(anchor_payload, anchor_source),
            _load_model_poses(
                payload["canonicalPoses"], f"{source}.canonicalPoses", canonical_order=True
            ),
        )

    if suspension_type != "singleCord":
        raise ValueError(f"{source}.type must be singleCord or twoBranchCord")
    _closed(payload, {"type", "attachment", "anchor", "cord", "canonicalPoses"}, source)

    attachment_source = f"{source}.attachment"
    attachment_payload = _mapping(payload["attachment"], attachment_source)
    _closed(attachment_payload, {"nodeID", "pointInModel", "provenance"}, attachment_source)
    attachment = BoardModelAttachment(
        _string(attachment_payload["nodeID"], f"{attachment_source}.nodeID"),
        _finite_vector3(attachment_payload["pointInModel"], f"{attachment_source}.pointInModel"),
        _string(attachment_payload["provenance"], f"{attachment_source}.provenance"),
    )

    anchor = _load_model_anchor(payload["anchor"], f"{source}.anchor")

    cord_source = f"{source}.cord"
    cord_payload = _mapping(payload["cord"], cord_source)
    _closed(cord_payload, {"restLength", "radius", "material", "provenance"}, cord_source)
    cord = BoardModelCord(
        _positive_number(cord_payload["restLength"], f"{cord_source}.restLength"),
        _positive_number(cord_payload["radius"], f"{cord_source}.radius"),
        _string(cord_payload["material"], f"{cord_source}.material"),
        _string(cord_payload["provenance"], f"{cord_source}.provenance"),
    )

    return BoardModelSingleCordSuspension(
        attachment, anchor, cord, _load_model_poses(payload["canonicalPoses"], f"{source}.canonicalPoses")
    )


def _load_model_display(value: Any, source: str) -> Mapping[str, Any]:
    payload = _mapping(value, source)
    _closed(payload, {"camera"}, source)
    camera_source = f"{source}.camera"
    camera = _mapping(payload["camera"], camera_source)
    _closed(camera, {"type", "viewDirection", "up", "fitPadding"}, camera_source)
    if camera["type"] != "orthographic":
        raise ValueError(f"{camera_source}.type must be orthographic")
    view_direction = _vector3(camera["viewDirection"], f"{camera_source}.viewDirection")
    up = _vector3(camera["up"], f"{camera_source}.up")
    fit_padding = _positive_number(camera["fitPadding"], f"{camera_source}.fitPadding")
    return MappingProxyType(
        {
            "camera": MappingProxyType(
                {
                    "type": "orthographic",
                    "viewDirection": view_direction,
                    "up": up,
                    "fitPadding": fit_padding,
                }
            )
        }
    )


def _load_v2_media(value: Any, source: str) -> PresentationMedia:
    payload = _mapping(value, source)
    media_type = _string(payload.get("type"), f"{source}.type")
    if media_type == "raster":
        _closed(payload, {"type", "assetPath", "holdGeometry"}, source)
        raw_geometry = _mapping(payload["holdGeometry"], f"{source}.holdGeometry")
        hold_geometry = {
            _identifier(hold_id, f"{source}.holdGeometry hold ID"): _load_geometry(
                pieces, f"{source}.holdGeometry[{hold_id}]"
            )
            for hold_id, pieces in raw_geometry.items()
        }
        return PresentationMediaRaster(
            _asset_path(payload["assetPath"], f"{source}.assetPath"),
            MappingProxyType(hold_geometry),
        )
    if media_type == "model":
        _closed(payload, {"type", "assetPath", "descriptorPath", "display"}, source, optional={"suspension"})
        return PresentationMediaModel(
            _typed_asset_path(
                payload["assetPath"], f"{source}.assetPath", ".usdz", "a USDZ"
            ),
            _typed_asset_path(
                payload["descriptorPath"],
                f"{source}.descriptorPath",
                ".model.json",
                "a .model.json descriptor",
            ),
            _load_model_display(payload["display"], f"{source}.display"),
            _load_model_suspension(payload["suspension"], f"{source}.suspension")
            if "suspension" in payload
            else None,
        )
    raise ValueError(f"{source}.type must be raster or model")


def _load_v2_presentation(value: Any, source: str) -> BoardPresentation:
    payload = _mapping(value, source)
    _closed(
        payload,
        {"id", "name", "aspectRatio", "isDefault", "derivation", "media"},
        source,
    )
    aspect_ratio = _positive_number(payload["aspectRatio"], f"{source}.aspectRatio")
    source_presentation_id, is_inverted = _load_v2_derivation(
        payload["derivation"], f"{source}.derivation"
    )
    media = _load_v2_media(payload["media"], f"{source}.media")
    if isinstance(media, PresentationMediaModel) and source_presentation_id is not None:
        raise ValueError(f"{source} model media may not be derived or inverted")
    return BoardPresentation(
        _identifier(payload["id"], f"{source}.id"),
        _string(payload["name"], f"{source}.name"),
        media.asset_path,
        aspect_ratio,
        _boolean(payload["isDefault"], f"{source}.isDefault"),
        source_presentation_id,
        is_inverted,
        media,
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
    size_millimeters: float | None
    depth_range_millimeters: MillimeterRange | None
    grip_type: str | None
    finger_capacity: int | None
    hand_capacity: int | None
    features: tuple[str, ...] | None
    paired_hold_id: str | None


@dataclass(frozen=True)
class BoardDocument:
    id: str
    facts: Mapping[str, Any]
    equipment_objects: tuple[str, ...]
    holds: tuple[BoardHold, ...]
    presentations: tuple[BoardPresentation, ...]
    positions: tuple[BoardPosition, ...]
    position_transitions: tuple[BoardPositionTransition, ...]
    model_hold_frames: Mapping[tuple[str, str], NormalizedFrame] = field(
        default_factory=lambda: MappingProxyType({}), repr=False
    )

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

    def hold_frame(self, hold_id: str, presentation_id: str) -> NormalizedFrame:
        if hold_id not in {hold.id for hold in self.holds}:
            raise ValueError(f"unknown hold id: {hold_id}")
        presentation = next(
            (candidate for candidate in self.presentations if candidate.id == presentation_id),
            None,
        )
        if presentation is None:
            raise ValueError(f"unknown presentation id: {presentation_id}")
        if isinstance(presentation.media, PresentationMediaRaster):
            pieces = presentation.media.hold_geometry.get(hold_id)
            if not pieces:
                raise ValueError(
                    f"presentation {presentation_id} has no geometry for hold {hold_id}"
                )
            return _union_frames(piece.frame for piece in pieces)
        if isinstance(presentation.media, PresentationMediaModel):
            try:
                return self.model_hold_frames[(presentation_id, hold_id)]
            except KeyError as error:
                raise ValueError(
                    f"presentation {presentation_id} has no descriptor frame for hold {hold_id}"
                ) from error
        raise ValueError(f"presentation {presentation_id} has no typed media")

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
        if isinstance(presentation.media, PresentationMediaRaster):
            owned = set(presentation.media.hold_geometry)
            return tuple(hold.id for hold in self.holds if hold.id in owned)
        if isinstance(presentation.media, PresentationMediaModel):
            return tuple(hold.id for hold in self.holds)
        raise ValueError(f"presentation {presentation.id} has no typed media")

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


def _union_frames(frames: Any) -> NormalizedFrame:
    values = tuple(frames)
    min_x = min(frame.x for frame in values)
    min_y = min(frame.y for frame in values)
    max_x = max(frame.x + frame.width for frame in values)
    max_y = max(frame.y + frame.height for frame in values)
    return NormalizedFrame(
        min_x,
        min_y,
        round(max_x - min_x, 9),
        round(max_y - min_y, 9),
    )


def _load_geometry(value: Any, source: str) -> tuple[BoardGeometryPiece, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{source} must be a non-empty array")
    return tuple(
        BoardGeometryPiece.from_json(item, f"{source}[{index}]")
        for index, item in enumerate(value)
    )


def _load_hold(value: Any, source: str) -> BoardHold:
    payload = _mapping(value, source)
    _closed(
        payload,
        {"id", "name", "kind"},
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
        },
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
    common = {
        "id": _identifier(payload["id"], f"{source}.id"),
        "equipment_object_id": _identifier(
            payload.get("equipmentObjectID", "primary"),
            f"{source}.equipmentObjectID",
        ),
        "name": _string(payload["name"], f"{source}.name"),
        "kind": kind,
        "sloper": sloper,
        "size_millimeters": size,
        "depth_range_millimeters": depth_range,
        "grip_type": grip_type,
        "finger_capacity": finger_capacity,
        "hand_capacity": hand_capacity,
        "features": features,
        "paired_hold_id": paired_hold_id,
    }
    return BoardHold(**common)


def _load_presentations(value: Any, source: str) -> tuple[BoardPresentation, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{source} must be a non-empty array")
    presentations = tuple(
        _load_v2_presentation(item, f"{source}[{index}]")
        for index, item in enumerate(value)
    )
    if len({presentation.id for presentation in presentations}) != len(presentations):
        raise ValueError("duplicate presentation id")
    if sum(presentation.is_default for presentation in presentations) != 1:
        raise ValueError("board.json.presentations must have exactly one default presentation")
    presentation_ids = {presentation.id for presentation in presentations}
    for presentation in presentations:
        if presentation.source_presentation_id is not None:
            source = next(
                (
                    candidate
                    for candidate in presentations
                    if candidate.id == presentation.source_presentation_id
                ),
                None,
            )
            if source is None or source.source_presentation_id is not None:
                raise ValueError(
                    f"presentation {presentation.id} must reference a canonical presentation"
                )
            if presentation.source_presentation_id == presentation.id:
                raise ValueError(
                    f"presentation {presentation.id} must reference a canonical presentation"
                )
    return presentations


def _validate_v2_presentation_compatibility(
    presentations: tuple[BoardPresentation, ...],
) -> None:
    presentations_by_id = {
        presentation.id: presentation for presentation in presentations
    }
    for presentation in presentations:
        if presentation.source_presentation_id is None:
            continue
        source = presentations_by_id[presentation.source_presentation_id]
        if not isinstance(
            presentation.media, PresentationMediaRaster
        ) or not isinstance(source.media, PresentationMediaRaster):
            raise ValueError(
                "v2 derived presentation relationships must be raster to raster"
            )
    has_model = any(
        isinstance(presentation.media, PresentationMediaModel)
        for presentation in presentations
    )
    if sum(isinstance(presentation.media, PresentationMediaModel) for presentation in presentations) > 1:
        raise ValueError("v2 packages may contain only one model presentation")
    has_raster = any(
        isinstance(presentation.media, PresentationMediaRaster)
        for presentation in presentations
    )
    if has_model and has_raster:
        raise ValueError("v2 packages may not mix model and raster presentations")


def _json_values_are_exactly_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without erasing member order or numeric scalar type."""

    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(
            _json_values_are_exactly_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _json_values_are_exactly_equal(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    return left == right


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
    schema_version = value.get("schemaVersion")
    if schema_version != 2 or isinstance(schema_version, bool):
        raise ValueError("board.json.schemaVersion must be 2 when present")
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
    required.add("schemaVersion")
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
    _validate_v2_presentation_compatibility(presentations)
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
    holds: list[BoardHold] = []
    for index, item in enumerate(raw_holds):
        source = f"board.json.holds[{index}]"
        holds.append(_load_hold(item, source))
    holds_tuple = tuple(holds)
    if len({hold.id for hold in holds_tuple}) != len(holds_tuple):
        raise ValueError("duplicate physical hold id")
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
    holds_by_id = {hold.id: hold for hold in holds_tuple}
    for hold in holds_tuple:
        if hold.kind != "gaston":
            continue
        if hold.paired_hold_id == hold.id or hold.paired_hold_id not in holds_by_id:
            raise ValueError(f"gaston hold {hold.id} must pair with a distinct existing hold")
        paired_hold = holds_by_id[hold.paired_hold_id]
        if paired_hold.kind != "gaston" or paired_hold.paired_hold_id != hold.id:
            raise ValueError(f"gaston hold {hold.id} must have a reciprocal gaston pair")
    logical_hold_ids = {hold.id for hold in holds_tuple}
    raw_presentations = value["presentations"]
    raw_presentations_by_id = {
        presentation.id: raw_presentations[index]
        for index, presentation in enumerate(presentations)
    }
    original_raster_ownership_counts = {
        hold_id: 0 for hold_id in logical_hold_ids
    }
    derived_raster_presentations: list[tuple[int, BoardPresentation]] = []
    has_raster = False
    for index, presentation in enumerate(presentations):
        if isinstance(presentation.media, PresentationMediaRaster):
            has_raster = True
            presentation_hold_ids = set(presentation.media.hold_geometry)
            if not presentation_hold_ids:
                raise ValueError(
                    f"presentation {presentation.id} media.holdGeometry must "
                    "own at least one logical hold"
                )
            if not presentation_hold_ids <= logical_hold_ids:
                raise ValueError(
                    f"presentation {presentation.id} media.holdGeometry must "
                    "only own logical holds"
                )
            if presentation.source_presentation_id is None:
                for hold_id in presentation_hold_ids:
                    original_raster_ownership_counts[hold_id] += 1
            else:
                derived_raster_presentations.append((index, presentation))
    if has_raster and any(
        ownership_count != 1
        for ownership_count in original_raster_ownership_counts.values()
    ):
        raise ValueError(
            "v2 original raster media.holdGeometry must own every logical hold "
            "exactly once"
        )
    for index, presentation in derived_raster_presentations:
        raw_media = raw_presentations[index]["media"]
        raw_source_media = raw_presentations_by_id[
            presentation.source_presentation_id
        ]["media"]
        if not _json_values_are_exactly_equal(
            raw_media["holdGeometry"], raw_source_media["holdGeometry"]
        ):
            raise ValueError(
                f"derived presentation {presentation.id} media.holdGeometry "
                "must exactly equal its source geometry"
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


def _descriptor_vector(
    value: Any, length: int, source: str
) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{source} must contain exactly {length} coordinates")
    coordinates = tuple(
        _number(item, f"{source}[{index}]") for index, item in enumerate(value)
    )
    if any(round(coordinate, 9) != coordinate for coordinate in coordinates):
        raise ValueError(f"{source} must be rounded to nine decimals")
    return coordinates


def _validate_model_suspension(
    suspension: BoardModelSuspension,
    *,
    model_bounds: tuple[tuple[float, ...], tuple[float, ...]],
    nodes: Mapping[str, str],
    position_ids: set[str],
) -> None:
    minimum, maximum = model_bounds
    if set(suspension.canonical_poses) != position_ids:
        raise ValueError("suspension canonical poses must exactly match position IDs")

    # The anchor is evaluated once from the unposed model: the center of the
    # top (+Y) bounds face plus the authored display offset. It never follows
    # a canonical pose.
    offset = suspension.anchor.offset_from_board_bounds
    anchor = (
        (minimum[0] + maximum[0]) / 2 + offset[0],
        maximum[1] + offset[1],
        (minimum[2] + maximum[2]) / 2 + offset[2],
    )
    if not all(math.isfinite(value) for value in anchor):
        raise ValueError("suspension anchor must be finite")
    if isinstance(suspension, BoardModelSingleCordSuspension):
        passages = (suspension.attachment,)
    else:
        passages = tuple(
            passage
            for side in (suspension.passages.left, suspension.passages.right)
            for passage in side
        )
        if len(passages) != 4 or len({passage.id for passage in passages}) != 4:
            raise ValueError("twoBranchCord suspension requires four distinct passages")
        for passage in passages:
            role = nodes.get(passage.node_id)
            if role not in {"body", "attachment"}:
                raise ValueError("suspension passage node must be a body or attachment node")
            if any(
                coordinate < minimum[index] or coordinate > maximum[index]
                for index, coordinate in enumerate(passage.point_in_model)
            ):
                raise ValueError("suspension passage point must be inside model bounds")
    if isinstance(suspension, BoardModelSingleCordSuspension):
        role = nodes.get(suspension.attachment.node_id)
        if role not in {"body", "attachment"}:
            raise ValueError("suspension attachment node must be a body or attachment node")
        if any(
            coordinate < minimum[index] or coordinate > maximum[index]
            for index, coordinate in enumerate(suspension.attachment.point_in_model)
        ):
            raise ValueError("suspension attachment point must be inside model bounds")
    for position_id, pose in suspension.canonical_poses.items():
        qx, qy, qz, qw = pose.rotation
        endpoints_by_branch = (
            (((suspension.attachment,), (suspension.cord.rest_length,)),)
            if isinstance(suspension, BoardModelSingleCordSuspension)
            else (
                (suspension.passages.left, (suspension.branches[0].rest_length,)),
                (suspension.passages.right, (suspension.branches[1].rest_length,)),
            )
        )
        for branch_endpoints, branch_lengths in endpoints_by_branch:
            transformed_endpoints: list[tuple[float, float, float]] = []
            for endpoint in branch_endpoints:
                px, py, pz = endpoint.point_in_model
                # Quaternion rotation followed by canonical translation.
                tx = 2 * (qy * pz - qz * py)
                ty = 2 * (qz * px - qx * pz)
                tz = 2 * (qx * py - qy * px)
                transformed = (
                    px + qw * tx + (qy * tz - qz * ty) + pose.translation[0],
                    py + qw * ty + (qz * tx - qx * tz) + pose.translation[1],
                    pz + qw * tz + (qx * ty - qy * tx) + pose.translation[2],
                )
                transformed_endpoints.append(transformed)
                distance = math.sqrt(sum((transformed[index] - anchor[index]) ** 2 for index in range(3)))
                if not math.isfinite(distance):
                    raise ValueError(f"suspension pose {position_id} endpoint distance must be finite")
            if len(transformed_endpoints) == 1:
                rest_length = branch_lengths[0]
                distance = math.sqrt(
                    sum((transformed_endpoints[0][index] - anchor[index]) ** 2 for index in range(3))
                )
                if rest_length < distance - 1e-5:
                    raise ValueError(f"suspension pose {position_id} restLength is shorter than endpoint distance")
            if len(transformed_endpoints) == 2:
                passage_distance = math.sqrt(
                    sum(
                        (transformed_endpoints[0][index] - transformed_endpoints[1][index]) ** 2
                        for index in range(3)
                    )
                )
                if not math.isfinite(passage_distance):
                    raise ValueError(f"suspension pose {position_id} passage-to-passage distance must be finite")
                endpoint_distances = tuple(
                    math.sqrt(sum((endpoint[index] - anchor[index]) ** 2 for index in range(3)))
                    for endpoint in transformed_endpoints
                )
                minimum_route_length = sum(endpoint_distances) + passage_distance
                if not all(math.isfinite(distance) for distance in endpoint_distances) or not math.isfinite(minimum_route_length):
                    raise ValueError(f"suspension pose {position_id} closed route length must be finite")
                if passage_distance <= 1e-7:
                    raise ValueError(f"suspension pose {position_id} must have distinct passage endpoints")
                if any(distance <= 1e-7 for distance in endpoint_distances):
                    raise ValueError(f"suspension pose {position_id} passage endpoints must not coincide with the anchor")
                if branch_lengths[0] < minimum_route_length - 1e-5:
                    raise ValueError(f"suspension pose {position_id} restLength is shorter than the closed route")


def _load_model_descriptor(
    path: Path,
    asset_path: Path,
    logical_hold_ids: set[str],
    *,
    suspension: BoardModelSuspension | None = None,
    position_ids: set[str] | None = None,
) -> Mapping[str, NormalizedFrame]:
    descriptor = _load_json(path, "model descriptor")
    _closed(
        descriptor,
        {
            "schemaVersion",
            "coordinateFrame",
            "modelSHA256",
            "modelBounds",
            "nodes",
            "holds",
        },
        "model descriptor",
    )
    if descriptor["schemaVersion"] != 1 or isinstance(
        descriptor["schemaVersion"], bool
    ):
        raise ValueError("model descriptor schemaVersion must be 1")
    if descriptor["coordinateFrame"] != "hang-ten-board-v1":
        raise ValueError(
            "model descriptor coordinateFrame must be hang-ten-board-v1"
        )
    declared_hash = _string(descriptor["modelSHA256"], "model descriptor modelSHA256")
    if not re.fullmatch(r"[0-9a-f]{64}", declared_hash):
        raise ValueError("model descriptor modelSHA256 must be a lowercase SHA-256")
    try:
        actual_hash = hashlib.sha256(asset_path.read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError("model asset must be readable for SHA-256 validation") from error
    if declared_hash != actual_hash:
        raise ValueError("model descriptor SHA-256 does not match USDZ bytes")

    bounds = _mapping(descriptor["modelBounds"], "model descriptor modelBounds")
    _closed(bounds, {"min", "max"}, "model descriptor modelBounds")
    minimum = _descriptor_vector(bounds["min"], 3, "model descriptor modelBounds.min")
    maximum = _descriptor_vector(bounds["max"], 3, "model descriptor modelBounds.max")
    if any(minimum[index] > maximum[index] for index in range(3)):
        raise ValueError("model descriptor modelBounds minimum exceeds maximum")
    face_spans = tuple(maximum[index] - minimum[index] for index in range(2))
    if any(not math.isfinite(span) for span in face_spans):
        raise ValueError("model descriptor modelBounds face span must be finite")
    if any(span <= 0 for span in face_spans):
        raise ValueError("model descriptor modelBounds face span must be positive")

    raw_nodes = descriptor["nodes"]
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError("model descriptor nodes must be a non-empty array")
    node_ids: set[str] = set()
    node_ids_by_hold: dict[str, list[str]] = {}
    body_count = 0
    attachment_count = 0
    ordered_node_ids: list[str] = []
    for index, raw_node in enumerate(raw_nodes):
        source = f"model descriptor nodes[{index}]"
        node = _mapping(raw_node, source)
        role = node.get("role")
        expected = {"nodeID", "role", "holdID"} if role == "hold" else {"nodeID", "role"}
        _closed(node, expected, source)
        node_id = _string(node["nodeID"], f"{source}.nodeID")
        if node_id in node_ids:
            raise ValueError(f"model descriptor has duplicate nodeID: {node_id}")
        node_ids.add(node_id)
        ordered_node_ids.append(node_id)
        if role == "body":
            body_count += 1
        elif role == "hold":
            hold_id = _identifier(node["holdID"], f"{source}.holdID")
            node_ids_by_hold.setdefault(hold_id, []).append(node_id)
        elif role == "attachment":
            attachment_count += 1
            max_attachments = 4 if isinstance(suspension, BoardModelTwoBranchSuspension) else 1
            if attachment_count > max_attachments:
                raise ValueError("model descriptor has too many attachment nodes")
        else:
            raise ValueError(f"{source}.role must be body, hold, or attachment")
    if body_count < 1:
        raise ValueError("model descriptor requires one or more body nodes")
    if ordered_node_ids != sorted(ordered_node_ids):
        raise ValueError("model descriptor nodes must be sorted by nodeID")
    if set(node_ids_by_hold) != logical_hold_ids:
        raise ValueError("model descriptor node hold IDs must equal logical holds")

    raw_holds = _mapping(descriptor["holds"], "model descriptor holds")
    if list(raw_holds) != sorted(raw_holds):
        raise ValueError("model descriptor holds must be sorted by holdID")
    if set(raw_holds) != logical_hold_ids:
        raise ValueError("model descriptor holds must equal logical holds")
    frames: dict[str, NormalizedFrame] = {}
    for hold_id, raw_hold in raw_holds.items():
        source = f"model descriptor holds[{hold_id}]"
        hold = _mapping(raw_hold, source)
        _closed(hold, {"nodeIDs", "facePlaneAABB", "center"}, source)
        hold_node_ids = hold["nodeIDs"]
        if (
            not isinstance(hold_node_ids, list)
            or any(not isinstance(node_id, str) or not node_id for node_id in hold_node_ids)
            or hold_node_ids != sorted(node_ids_by_hold[hold_id])
        ):
            raise ValueError(f"{source}.nodeIDs must exactly match bound nodes")
        face_bounds = _mapping(hold["facePlaneAABB"], f"{source}.facePlaneAABB")
        _closed(face_bounds, {"min", "max"}, f"{source}.facePlaneAABB")
        face_min = _descriptor_vector(
            face_bounds["min"], 2, f"{source}.facePlaneAABB.min"
        )
        face_max = _descriptor_vector(
            face_bounds["max"], 2, f"{source}.facePlaneAABB.max"
        )
        if any(
            face_min[index] > face_max[index]
            or face_min[index] < 0
            or face_max[index] > 1
            for index in range(2)
        ):
            raise ValueError(f"{source}.facePlaneAABB must be normalized")
        center = _descriptor_vector(hold["center"], 2, f"{source}.center")
        expected_center = tuple(
            round(face_min[index] + (face_max[index] - face_min[index]) / 2, 9)
            for index in range(2)
        )
        if center != expected_center:
            raise ValueError(f"{source}.center must derive from facePlaneAABB")
        frames[hold_id] = NormalizedFrame(
            face_min[0],
            face_min[1],
            round(face_max[0] - face_min[0], 9),
            round(face_max[1] - face_min[1], 9),
        )
    if suspension is not None:
        _validate_model_suspension(
            suspension,
            model_bounds=(minimum, maximum),
            nodes={
                node["nodeID"]: node["role"]
                for node in raw_nodes
                if isinstance(node, Mapping)
            },
            position_ids=position_ids or set(),
        )
    return MappingProxyType(frames)


def _validate_finished_shape(
    root: Path, board: BoardDocument
) -> Mapping[tuple[str, str], NormalizedFrame]:
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
    expected_assets: set[str] = set()
    for presentation in board.presentations:
        expected_assets.add(presentation.asset_path)
        if isinstance(presentation.media, PresentationMediaModel):
            expected_assets.add(presentation.media.descriptor_path)
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
    raster_asset_paths = {
        presentation.asset_path
        for presentation in board.presentations
        if presentation.media is None
        or isinstance(presentation.media, PresentationMediaRaster)
    }
    image_dimensions: dict[str, tuple[int, int]] = {}
    for asset_path in sorted(raster_asset_paths):
        asset = root / asset_path
        if asset.is_symlink() or not asset.is_file():
            raise ValueError(f"{asset_path} must be a regular non-symlink file")
        image_dimensions[asset_path] = _validate_png_structure(asset, asset_path)
    for presentation in board.presentations:
        if presentation.asset_path not in image_dimensions:
            continue
        width, height = image_dimensions[presentation.asset_path]
        image_aspect_ratio = width / height
        relative_error = (
            abs(presentation.aspect_ratio - image_aspect_ratio) / image_aspect_ratio
        )
        if relative_error > _ASPECT_RATIO_RELATIVE_TOLERANCE:
            raise ValueError(
                f"board.json.presentations[{presentation.id}].aspectRatio must match "
                "its image width/height within 0.1%"
            )
    model_frames: dict[tuple[str, str], NormalizedFrame] = {}
    logical_hold_ids = {hold.id for hold in board.holds}
    for presentation in board.presentations:
        if not isinstance(presentation.media, PresentationMediaModel):
            continue
        frames = _load_model_descriptor(
            root / presentation.media.descriptor_path,
            root / presentation.media.asset_path,
            logical_hold_ids,
            suspension=presentation.media.suspension,
            position_ids={position.id for position in board.positions
                          if position.presentation_id == presentation.id},
        )
        model_frames.update(
            ((presentation.id, hold_id), frame) for hold_id, frame in frames.items()
        )
    return MappingProxyType(model_frames)


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
    board = replace(
        board,
        model_hold_frames=_validate_finished_shape(root, board),
    )
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
