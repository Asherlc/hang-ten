"""Fail-closed discovery and validation for single-file hangboard packages."""

from __future__ import annotations

from dataclasses import dataclass
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
_HOLD_KINDS = frozenset({"jug", "edge", "pocket", "pinch", "sloper"})
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
class BoardPresentation:
    id: str
    name: str
    asset_path: str
    aspect_ratio: float
    is_default: bool
    source_presentation_id: str | None = None
    is_inverted: bool = False

    @classmethod
    def from_json(cls, value: Any, source: str) -> "BoardPresentation":
        payload = _mapping(value, source)
        _closed(
            payload,
            {"id", "name", "assetPath", "aspectRatio", "default"},
            source,
            optional={"sourcePresentationID", "isInverted"},
        )
        aspect_ratio = _number(payload["aspectRatio"], f"{source}.aspectRatio")
        if aspect_ratio <= 0:
            raise ValueError(f"{source}.aspectRatio must be positive")
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
        )


@dataclass(frozen=True)
class BoardHold:
    id: str
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
    holds: tuple[BoardHold, ...]
    presentations: tuple[BoardPresentation, ...]

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
            "sizeMillimeters",
            "depthRangeMillimeters",
            "gripType",
            "fingerCapacity",
            "handCapacity",
            "features",
            "sloper",
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
    _closed(value, required, "board.json", optional={"dimensions"})
    facts: dict[str, Any] = {}
    for key in ("manufacturer", "name", "subtitle", "productURL"):
        facts[key] = _string(value[key], f"board.json.{key}")
    if "dimensions" in value:
        facts["dimensions"] = _string(value["dimensions"], "board.json.dimensions")
    facts["aspectRatio"] = _number(value["aspectRatio"], "board.json.aspectRatio")
    if facts["aspectRatio"] <= 0:
        raise ValueError("board.json.aspectRatio must be positive")
    presentations = _load_presentations(value["presentations"], "board.json.presentations")
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
    return BoardDocument(
        _identifier(value["id"], "board.json.id"),
        MappingProxyType(facts),
        holds_tuple,
        presentations,
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
    for presentation in board.presentations:
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
                if asset_path == "assets/primary.png" and not _png_has_alpha_zero(
                    width=width,
                    height=height,
                    bit_depth=bit_depth,
                    color_type=color_type,
                    interlace_method=interlace_method,
                    idat_parts=idat_parts,
                    transparency=transparency,
                    asset_path=asset_path,
                ):
                    raise ValueError(
                        f"{asset_path} must contain at least one fully transparent pixel"
                    )
                return width, height
            offset = crc_end
    except struct.error as error:
        raise ValueError(f"{asset_path} must be a decodable PNG image") from error

    raise ValueError(f"{asset_path} is missing its IEND chunk")


def _png_has_alpha_zero(
    *,
    width: int,
    height: int,
    bit_depth: int | None,
    color_type: int | None,
    interlace_method: int | None,
    idat_parts: list[bytes],
    transparency: bytes | None,
    asset_path: str,
) -> bool:
    """Inspect decoded PNG samples for alpha zero using only the stdlib."""
    channels_by_color_type = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    channels = channels_by_color_type.get(color_type)
    if channels is None or bit_depth not in {1, 2, 4, 8, 16}:
        raise ValueError(f"{asset_path} has an unsupported PNG color format")
    if color_type in {2, 4, 6} and bit_depth not in {8, 16}:
        raise ValueError(f"{asset_path} has an unsupported PNG bit depth")
    if interlace_method != 0:
        raise ValueError(
            f"{asset_path} must be non-interlaced for transparency validation"
        )

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
    return transparent_pixel_found


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

    Raises ``ValueError`` when the sole primary PNG is malformed or fully opaque.
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
