"""Fail-closed discovery and validation for single-file hangboard packages."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
import math
from pathlib import Path
import re
import struct
from types import MappingProxyType
from typing import Any, Mapping
import zlib

try:  # Standard package import, plus direct-file loading used by pipeline tests.
    from .board_artwork import BoardShapeDocument, NormalizedFrame
except ImportError:  # pragma: no cover - exercised by direct module consumers
    _artwork_path = Path(__file__).with_name("board_artwork.py")
    _spec = importlib.util.spec_from_file_location("hangboard_board_artwork", _artwork_path)
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
_ASSET_ENTRIES = frozenset({"primary.png"})
_HOLD_KINDS = frozenset({"jug", "edge", "pocket", "pinch", "sloper"})
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
    lower_bound: int
    upper_bound: int

    @classmethod
    def from_json(cls, value: Any, source: str) -> "MillimeterRange":
        payload = _mapping(value, source)
        _closed(payload, {"lowerBound", "upperBound"}, source)
        lower = _positive_integer(payload["lowerBound"], f"{source}.lowerBound")
        upper = _positive_integer(payload["upperBound"], f"{source}.upperBound")
        if lower > upper:
            raise ValueError(f"{source}.lowerBound must not exceed upperBound")
        return cls(lower, upper)


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
        return cls(
            NormalizedFrame.from_json(payload["frame"], f"{source}.frame"),
            BoardShapeDocument.from_json(payload["shape"], f"{source}.shape"),
            treatment,
            BoardShapeConstraint.from_json(
                payload["shapeConstraint"], f"{source}.shapeConstraint"
            )
            if "shapeConstraint" in payload
            else None,
        )


@dataclass(frozen=True)
class BoardHold:
    id: str
    name: str
    kind: str
    geometry: tuple[BoardGeometryPiece, ...]
    size_millimeters: int | None
    depth_range_millimeters: MillimeterRange | None
    grip_type: str | None
    finger_capacity: int | None
    features: tuple[str, ...] | None

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
    presentation_asset_path: str | None

    @property
    def manufacturer(self) -> str:
        return self.facts["manufacturer"]

    @property
    def name(self) -> str:
        return self.facts["name"]


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


def _load_hold(value: Any, source: str) -> BoardHold:
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
            "features",
        },
    )
    kind = _string(payload["kind"], f"{source}.kind")
    if kind not in _HOLD_KINDS:
        raise ValueError(f"{source}.kind must be one of {sorted(_HOLD_KINDS)}")
    size = None
    if "sizeMillimeters" in payload:
        size = _positive_integer(payload["sizeMillimeters"], f"{source}.sizeMillimeters")
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
        _load_geometry(payload["geometry"], f"{source}.geometry"),
        size,
        depth_range,
        grip_type,
        finger_capacity,
        features,
    )


def _load_board(value: Mapping[str, Any]) -> BoardDocument:
    required = {
        "schemaVersion",
        "id",
        "manufacturer",
        "name",
        "subtitle",
        "productURL",
        "dimensions",
        "aspectRatio",
        "holds",
    }
    _closed(value, required, "board.json", optional={"presentation"})
    if isinstance(value["schemaVersion"], bool) or value["schemaVersion"] != 1:
        raise ValueError("board.json.schemaVersion must be 1")
    facts: dict[str, Any] = {}
    for key in ("manufacturer", "name", "subtitle", "productURL", "dimensions"):
        facts[key] = _string(value[key], f"board.json.{key}")
    facts["aspectRatio"] = _number(value["aspectRatio"], "board.json.aspectRatio")
    if facts["aspectRatio"] <= 0:
        raise ValueError("board.json.aspectRatio must be positive")
    presentation_asset_path = None
    if "presentation" in value:
        presentation = _mapping(value["presentation"], "board.json.presentation")
        _closed(presentation, {"assetPath"}, "board.json.presentation")
        presentation_asset_path = _string(
            presentation["assetPath"], "board.json.presentation.assetPath"
        )
        if presentation_asset_path != "assets/primary.png":
            raise ValueError("board.json.presentation.assetPath must be assets/primary.png")
    raw_holds = value["holds"]
    if not isinstance(raw_holds, list) or not raw_holds:
        raise ValueError("board.json.holds must be a non-empty array")
    holds = tuple(
        _load_hold(item, f"board.json.holds[{index}]")
        for index, item in enumerate(raw_holds)
    )
    if len({hold.id for hold in holds}) != len(holds):
        raise ValueError("duplicate physical hold id")
    return BoardDocument(
        _identifier(value["id"], "board.json.id"),
        MappingProxyType(facts),
        holds,
        presentation_asset_path,
    )


def _validate_finished_shape(root: Path) -> None:
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
    asset_entries = {item.name for item in assets.iterdir()}
    unknown_assets = asset_entries - _ASSET_ENTRIES
    missing_assets = _ASSET_ENTRIES - asset_entries
    if unknown_assets:
        raise ValueError(f"unknown asset: {sorted(unknown_assets)[0]}")
    if missing_assets:
        raise ValueError("board package is missing assets/primary.png")
    primary = assets / "primary.png"
    if primary.is_symlink() or not primary.is_file():
        raise ValueError("assets/primary.png must be a regular non-symlink file")
    _validate_png_structure(primary)


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _validate_png_structure(path: Path) -> None:
    """Validate PNG framing without depending on a third-party image library.

    This module is loaded by a bare system interpreter during Xcode's board
    staging build phase, which installs no dependencies, so validation stays
    within the standard library rather than requiring Pillow.
    """
    try:
        data = path.read_bytes()
    except OSError as error:
        raise ValueError("assets/primary.png must be a readable file") from error

    if data[:8] != _PNG_SIGNATURE:
        raise ValueError("assets/primary.png must be a PNG image")

    offset = 8
    seen_ihdr = False
    seen_idat = False
    width = height = None
    try:
        while offset < len(data):
            if offset + 8 > len(data):
                raise ValueError("assets/primary.png has a truncated chunk header")
            length, chunk_type = struct.unpack_from(">I4s", data, offset)
            body_start = offset + 8
            body_end = body_start + length
            crc_end = body_end + 4
            if crc_end > len(data):
                raise ValueError("assets/primary.png has a truncated chunk body")
            body = data[body_start:body_end]
            (declared_crc,) = struct.unpack_from(">I", data, body_end)
            actual_crc = zlib.crc32(chunk_type + body) & 0xFFFFFFFF
            if declared_crc != actual_crc:
                raise ValueError("assets/primary.png has a corrupt chunk checksum")
            if not seen_ihdr:
                if chunk_type != b"IHDR":
                    raise ValueError("assets/primary.png must start with an IHDR chunk")
                if len(body) != 13:
                    raise ValueError("assets/primary.png has a malformed IHDR chunk")
                width, height = struct.unpack_from(">II", body, 0)
                seen_ihdr = True
            if chunk_type == b"IDAT":
                seen_idat = True
            if chunk_type == b"IEND":
                if body:
                    raise ValueError("assets/primary.png has a malformed IEND chunk")
                if not seen_idat:
                    raise ValueError("assets/primary.png must contain image data")
                if crc_end != len(data):
                    raise ValueError("assets/primary.png has trailing data after IEND")
                if width is None or height is None or width <= 0 or height <= 0:
                    raise ValueError("assets/primary.png must declare positive dimensions")
                return
            offset = crc_end
    except struct.error as error:
        raise ValueError("assets/primary.png must be a decodable PNG image") from error

    raise ValueError("assets/primary.png is missing its IEND chunk")


def load_board_package(package_root: Path) -> BoardPackage:
    root = Path(package_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"board package does not exist as a regular directory: {root}")
    _validate_finished_shape(root)
    board = _load_board(_load_json(root / "board.json", "board.json"))
    return BoardPackage(root.resolve(), board)


def is_primary_only_draft(root: Path) -> bool:
    """Return whether *root* has exactly ``assets/primary.png`` and no manifest."""
    _require_no_symlinks(root)
    if {item.name for item in root.iterdir()} != {"assets"}:
        return False
    assets = root / "assets"
    if assets.is_symlink() or not assets.is_dir():
        return False
    if {item.name for item in assets.iterdir()} != {"primary.png"}:
        return False
    primary = assets / "primary.png"
    return primary.is_file() and not primary.is_symlink()


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
