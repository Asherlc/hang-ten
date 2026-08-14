"""Fail-closed registry and board-package validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlparse
import zlib

_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:[a-z0-9._-]*[a-z0-9])?$")
_PACKAGE_SLUG = re.compile(r"^[a-z0-9]+(?:[a-z0-9-]*[a-z0-9])?$")
_SIDECARS = ("board.json", "evidence.json", "semantics.json")
_PACKAGE_ROOT_FILES = frozenset((*_SIDECARS, "assets"))
_SOURCE_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".webp", ".heic"})
_EVIDENCE_METHODS = frozenset({"manufacturer-measurement", "reviewed-human-authored-normalization", "external-generative-adaptation"})
_HOLD_KINDS = frozenset({"jug", "edge", "pocket", "pinch", "sloper"})
_GRIP_TYPES = frozenset({"openHand", "halfCrimp", "fullCrimp", "fourFingerPocket", "threeFingerPocket", "twoFingerPocket", "sloper"})
_CUE_STYLES = frozenset({"outerJug", "slot", "pinch", "rounded"})
_HOLD_FEATURES = frozenset({
    "jug", "roundSloper", "largeSlope", "largeEdge", "mediumEdge", "smallEdge",
    "pocket", "twoFingerPocket", "threeFingerPocket", "fourFingerPocket",
    "fourFingerFlatEdge", "fourFingerIncutEdge", "largeOpenHandRail",
    "deepTwoFingerPocket", "thinCrimp", "shallowThreeFingerSlot", "widePinch",
    "mediumPinch", "smallPinch",
})
_HOLD_FIELD_KEYS = frozenset({
    "id", "name", "shortLabel", "detail", "kind", "frame", "sizeMillimeters",
    "depthRangeMillimeters", "gripType", "fingerCapacity", "cueStyle", "features",
})


def _closed(payload: Mapping[str, Any], keys: set[str], source: str) -> None:
    unknown, missing = set(payload) - keys, keys - set(payload)
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
    if not _IDENTIFIER.fullmatch(result):
        raise ValueError(f"{source} must be identifier-shaped")
    return result


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


def _positive_integer(value: Any, source: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{source} must be a positive integer")
    return value


def _finger_capacity(value: Any, source: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value not in range(1, 5):
        raise ValueError(f"{source} must be in 1...4")
    return value


def _enum_string(value: Any, allowed: frozenset[str], source: str) -> str:
    result = _string(value, source)
    if result not in allowed:
        raise ValueError(f"{source} must be one of {sorted(allowed)}")
    return result


def _relative_path(value: Any, root: Path, source: str, *, container: str) -> Path:
    raw = _string(value, source)
    path = Path(raw)
    if path.is_absolute() or "\\" in raw or raw in {".", ""} or ".." in path.parts:
        raise ValueError(f"{source} must be a relative path inside the {container}")
    candidate = root / path
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as error:
        raise ValueError(f"{source} must be a relative path inside the {container}") from error
    return path


def _package_slug_path(value: Any, root: Path, source: str) -> Path:
    path = _relative_path(value, root, source, container="catalog")
    if len(path.parts) != 1 or not _PACKAGE_SLUG.fullmatch(path.name):
        raise ValueError(f"{source} must be a single board-slug directory")
    return path


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is invalid JSON: {path}") from error
    return _mapping(payload, label)


def _require_no_symlinks(root: Path) -> None:
    if root.is_symlink():
        raise ValueError(f"package contains symlink: {root}")
    for item in root.rglob("*"):
        if item.is_symlink():
            raise ValueError(f"package contains symlink: {item}")


@dataclass(frozen=True)
class CatalogEntry:
    id: str
    path: str

    @classmethod
    def from_json(cls, value: Any, source: str) -> "CatalogEntry":
        payload = _mapping(value, source)
        _closed(payload, {"id", "path"}, source)
        return cls(_identifier(payload["id"], f"{source}.id"), _string(payload["path"], f"{source}.path"))


@dataclass(frozen=True)
class CatalogDocument:
    entries: tuple[CatalogEntry, ...]
    schema_version: int = 1

    @property
    def boards(self) -> tuple[CatalogEntry, ...]:
        return self.entries

    @classmethod
    def from_json(cls, value: Any, source: str = "catalog") -> "CatalogDocument":
        payload = _mapping(value, source)
        _closed(payload, {"schemaVersion", "boards"}, source)
        if isinstance(payload["schemaVersion"], bool) or payload["schemaVersion"] != 1:
            raise ValueError(f"{source}.schemaVersion must be 1")
        raw_entries = payload["boards"]
        if not isinstance(raw_entries, list):
            raise ValueError(f"{source}.boards must be an array")
        return cls(tuple(CatalogEntry.from_json(item, f"{source}.boards[{index}]") for index, item in enumerate(raw_entries)))


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
class BoardHold:
    id: str
    name: str
    short_label: str
    detail: str
    kind: str
    frame: NormalizedFrame
    size_millimeters: int | None
    depth_range_millimeters: MillimeterRange | None
    grip_type: str
    finger_capacity: int
    cue_style: str
    features: tuple[str, ...]


@dataclass(frozen=True)
class BoardDocument:
    id: str
    facts: Mapping[str, Any]
    holds: tuple[BoardHold, ...]
    presentation_asset_path: str | None


@dataclass(frozen=True)
class BoardSemanticsDocument:
    board_id: str
    semantic_holds: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class EvidenceMapping:
    source_ids: tuple[str, ...]
    method: str | None


@dataclass(frozen=True)
class BoardEvidenceDocument:
    board_id: str
    field_evidence: Mapping[str, EvidenceMapping]
    hold_evidence: Mapping[str, EvidenceMapping]
    semantic_evidence: Mapping[str, EvidenceMapping]
    asset_evidence: Mapping[str, EvidenceMapping]


@dataclass(frozen=True)
class BoardPackage:
    root: Path
    board: BoardDocument
    evidence: BoardEvidenceDocument
    semantics: BoardSemanticsDocument


def _load_board(value: Mapping[str, Any], root: Path) -> BoardDocument:
    required_keys = {"schemaVersion", "id", "manufacturer", "name", "subtitle", "productURL", "dimensions", "aspectRatio", "holds"}
    allowed_keys = required_keys | {"presentation"}
    unknown, missing = set(value) - allowed_keys, required_keys - set(value)
    if unknown:
        raise ValueError(f"board.json has unknown keys: {sorted(unknown)}")
    if missing:
        raise ValueError(f"board.json is missing keys: {sorted(missing)}")
    if isinstance(value["schemaVersion"], bool) or value["schemaVersion"] != 1:
        raise ValueError("board.json.schemaVersion must be 1")
    board_id = _identifier(value["id"], "board.json.id")
    fact_keys = {"manufacturer", "name", "subtitle", "productURL", "dimensions", "aspectRatio"}
    facts: dict[str, Any] = {}
    for key in fact_keys:
        if key == "aspectRatio":
            facts[key] = _number(value[key], f"board.json.{key}")
        else:
            facts[key] = _string(value[key], f"board.json.{key}")
    presentation_asset_path: str | None = None
    if "presentation" in value:
        presentation = _mapping(value["presentation"], "board.json.presentation")
        if set(presentation) == {"assetPath"}:
            asset_path = presentation["assetPath"]
        elif set(presentation) == {"photoAsset"}:
            photo_asset = _mapping(presentation["photoAsset"], "board.json.presentation.photoAsset")
            _closed(photo_asset, {"name", "path"}, "board.json.presentation.photoAsset")
            _string(photo_asset["name"], "board.json.presentation.photoAsset.name")
            asset_path = photo_asset["path"]
        else:
            raise ValueError("board.json.presentation must declare assetPath or photoAsset")
        presentation_asset_path = _relative_path(asset_path, root, "board.json.presentation asset path", container="package").as_posix()
    raw_holds = value["holds"]
    if not isinstance(raw_holds, list) or not raw_holds:
        raise ValueError("board.json.holds must be a non-empty array")
    holds: list[BoardHold] = []
    for index, raw in enumerate(raw_holds):
        source = f"board.json.holds[{index}]"
        item = _mapping(raw, source)
        _closed(item, set(_HOLD_FIELD_KEYS), source)
        raw_size = item["sizeMillimeters"]
        size = None if raw_size is None else _positive_integer(raw_size, f"{source}.sizeMillimeters")
        raw_range = item["depthRangeMillimeters"]
        depth_range = None if raw_range is None else MillimeterRange.from_json(raw_range, f"{source}.depthRangeMillimeters")
        raw_features = item["features"]
        if not isinstance(raw_features, list):
            raise ValueError(f"{source}.features must be an array")
        features = tuple(
            _enum_string(feature, _HOLD_FEATURES, f"{source}.features[{feature_index}]")
            for feature_index, feature in enumerate(raw_features)
        )
        if len(features) != len(set(features)):
            raise ValueError(f"{source}.features must be unique")
        holds.append(
            BoardHold(
                id=_identifier(item["id"], f"{source}.id"),
                name=_string(item["name"], f"{source}.name"),
                short_label=_string(item["shortLabel"], f"{source}.shortLabel"),
                detail=_string(item["detail"], f"{source}.detail"),
                kind=_enum_string(item["kind"], _HOLD_KINDS, f"{source}.kind"),
                frame=NormalizedFrame.from_json(item["frame"], f"{source}.frame"),
                size_millimeters=size,
                depth_range_millimeters=depth_range,
                grip_type=_enum_string(item["gripType"], _GRIP_TYPES, f"{source}.gripType"),
                finger_capacity=_finger_capacity(item["fingerCapacity"], f"{source}.fingerCapacity"),
                cue_style=_enum_string(item["cueStyle"], _CUE_STYLES, f"{source}.cueStyle"),
                features=features,
            )
        )
    if len({hold.id for hold in holds}) != len(holds):
        raise ValueError("duplicate physical hold id")
    return BoardDocument(board_id, MappingProxyType(facts), tuple(holds), presentation_asset_path)


def _load_semantics(value: Mapping[str, Any]) -> BoardSemanticsDocument:
    _closed(value, {"schemaVersion", "boardID", "semanticHolds"}, "semantics.json")
    if isinstance(value["schemaVersion"], bool) or value["schemaVersion"] != 1:
        raise ValueError("semantics.json.schemaVersion must be 1")
    raw_semantics = _mapping(value["semanticHolds"], "semantics.json.semanticHolds")
    parsed: dict[str, tuple[str, ...]] = {}
    for semantic_id, raw in raw_semantics.items():
        semantic = _identifier(semantic_id, "semantics.json semantic id")
        item = _mapping(raw, f"semantics.json.semanticHolds.{semantic}")
        _closed(item, {"holdIDs"}, f"semantics.json.semanticHolds.{semantic}")
        raw_holds = item["holdIDs"]
        if not isinstance(raw_holds, list) or not raw_holds:
            raise ValueError(f"semantics.json.semanticHolds.{semantic}.holdIDs must be non-empty")
        holds = tuple(_identifier(hold, f"semantics.json.semanticHolds.{semantic}.holdIDs") for hold in raw_holds)
        if len(set(holds)) != len(holds):
            raise ValueError(f"semantics.json.semanticHolds.{semantic}.holdIDs must be unique")
        parsed[semantic] = holds
    return BoardSemanticsDocument(_identifier(value["boardID"], "semantics.json.boardID"), MappingProxyType(parsed))


def _mapping_evidence(value: Any, source: str, declared_sources: set[str]) -> EvidenceMapping:
    if isinstance(value, list):
        source_ids = tuple(_identifier(item, source) for item in value)
        method = None
    else:
        payload = _mapping(value, source)
        _closed(payload, {"sourceIDs", "method"}, source)
        raw_ids = payload["sourceIDs"]
        if not isinstance(raw_ids, list):
            raise ValueError(f"{source}.sourceIDs must be an array")
        source_ids = tuple(_identifier(item, f"{source}.sourceIDs") for item in raw_ids)
        method = _string(payload["method"], f"{source}.method")
        if method not in _EVIDENCE_METHODS:
            raise ValueError(f"{source}.method is unsupported")
    if not source_ids or len(source_ids) != len(set(source_ids)):
        raise ValueError(f"{source} must contain unique non-empty source IDs")
    if unknown := set(source_ids) - declared_sources:
        raise ValueError(f"{source} references unknown source id {sorted(unknown)[0]!r}")
    return EvidenceMapping(source_ids, method)


def _load_evidence(value: Mapping[str, Any]) -> BoardEvidenceDocument:
    required = {"schemaVersion", "boardID", "checkedAt", "sources", "fieldEvidence", "holdEvidence", "semanticEvidence", "assetEvidence"}
    _closed(value, required, "evidence.json")
    if isinstance(value["schemaVersion"], bool) or value["schemaVersion"] != 1:
        raise ValueError("evidence.json.schemaVersion must be 1")
    try:
        date.fromisoformat(_string(value["checkedAt"], "evidence.json.checkedAt"))
    except ValueError as error:
        raise ValueError("evidence.json.checkedAt must be an ISO calendar date") from error
    raw_sources = value["sources"]
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("evidence.json.sources must be non-empty")
    source_ids: set[str] = set()
    for index, raw in enumerate(raw_sources):
        item = _mapping(raw, f"evidence.json.sources[{index}]")
        _closed(item, {"id", "title", "url"}, f"evidence.json.sources[{index}]")
        source_id = _identifier(item["id"], f"evidence.json.sources[{index}].id")
        if source_id in source_ids:
            raise ValueError("duplicate evidence source id")
        source_ids.add(source_id)
        _string(item["title"], f"evidence.json.sources[{index}].title")
        url = _string(item["url"], f"evidence.json.sources[{index}].url")
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError(f"evidence.json.sources[{index}].url must be an absolute HTTPS URL")
    def parse_map(key: str) -> Mapping[str, EvidenceMapping]:
        raw_map = _mapping(value[key], f"evidence.json.{key}")
        return MappingProxyType({str(name): _mapping_evidence(raw, f"evidence.json.{key}.{name}", source_ids) for name, raw in raw_map.items()})
    return BoardEvidenceDocument(_identifier(value["boardID"], "evidence.json.boardID"), parse_map("fieldEvidence"), parse_map("holdEvidence"), parse_map("semanticEvidence"), parse_map("assetEvidence"))


def _exact_keys(actual: Mapping[str, Any], expected: set[str], message: str) -> None:
    if set(actual) != expected:
        raise ValueError(message)


def _package_assets(root: Path) -> set[str]:
    assets_root = root / "assets"
    if not assets_root.exists():
        return set()
    if not assets_root.is_dir() or assets_root.is_symlink():
        raise ValueError("package assets must be a non-symlink directory")
    assets: set[str] = set()
    source_photo_count = 0
    for item in assets_root.iterdir():
        if item.is_symlink():
            raise ValueError(f"package contains symlink: {item}")
        if not item.is_file():
            raise ValueError("package assets must be flat regular files")
        relative_path = item.relative_to(root).as_posix()
        if item.name == "primary.png":
            assets.add(relative_path)
            continue
        if item.suffix.lower() == ".png":
            raise ValueError("only assets/primary.png may be a PNG")
        if item.suffix.lower() not in _SOURCE_IMAGE_EXTENSIONS:
            raise ValueError("package source asset must be a .jpg, .jpeg, .webp, or .heic image")
        source_photo_count += 1
        if source_photo_count > 1:
            raise ValueError("package may contain at most one original source photo")
        assets.add(relative_path)
    return assets


def _is_png(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False

    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return False

    offset = 8
    has_ihdr = False
    has_idat = False
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset:offset + 4], "big")
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 8 + length
        if chunk_end + 4 > len(data):
            return False
        chunk_data = data[offset + 8:chunk_end]
        expected_crc = int.from_bytes(data[chunk_end:chunk_end + 4], "big")
        if (zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF) != expected_crc:
            return False
        if not has_ihdr:
            if chunk_type != b"IHDR" or length != 13:
                return False
            has_ihdr = True
        if chunk_type == b"IDAT":
            has_idat = True
        if chunk_type == b"IEND":
            return has_ihdr and has_idat and length == 0 and chunk_end + 4 == len(data)
        offset = chunk_end + 4
    return False


def load_board_package(package_root: Path) -> BoardPackage:
    root = Path(package_root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"board package does not exist or is not a directory: {root}")
    _require_no_symlinks(root)
    for item in root.iterdir():
        if item.name not in _PACKAGE_ROOT_FILES:
            raise ValueError(f"unknown package file: {item.name}")
    for sidecar in _SIDECARS:
        if not (root / sidecar).is_file():
            raise ValueError(f"board package {root} {sidecar} does not exist")
    board = _load_board(_load_json(root / "board.json", "board.json"), root)
    evidence = _load_evidence(_load_json(root / "evidence.json", "evidence.json"))
    semantics = _load_semantics(_load_json(root / "semantics.json", "semantics.json"))
    if len({board.id, evidence.board_id, semantics.board_id}) != 1:
        raise ValueError("board package sidecar board IDs must match")
    hold_ids = {hold.id for hold in board.holds}
    for semantic, mapped_holds in semantics.semantic_holds.items():
        for hold_id in mapped_holds:
            if hold_id not in hold_ids:
                raise ValueError(f"semantic {semantic!r} references unknown physical hold {hold_id!r}")
    _exact_keys(evidence.field_evidence, set(board.facts), "fieldEvidence keys must equal board factual fields")
    hold_evidence_keys = {
        f"{hold.id}.{field}"
        for hold in board.holds
        for field in _HOLD_FIELD_KEYS
    }
    _exact_keys(evidence.hold_evidence, hold_evidence_keys, "holdEvidence keys must equal physical hold field paths")
    _exact_keys(evidence.semantic_evidence, set(semantics.semantic_holds), "semanticEvidence keys must equal semantic IDs")
    assets = _package_assets(root)
    _exact_keys(evidence.asset_evidence, assets, "assetEvidence keys must equal package assets")
    if board.presentation_asset_path is not None and board.presentation_asset_path not in assets:
        raise ValueError("board presentation asset must resolve to a package asset")
    return BoardPackage(root.resolve(), board, evidence, semantics)


def load_catalog(path: Path) -> CatalogDocument:
    return CatalogDocument.from_json(_load_json(Path(path), "catalog"))


def validate_catalog(catalog_path: Path) -> CatalogDocument:
    catalog_path = Path(catalog_path)
    catalog = load_catalog(catalog_path)
    root = catalog_path.parent.resolve(strict=False)
    identifiers: set[str] = set()
    paths: set[Path] = set()
    for index, entry in enumerate(catalog.entries):
        if entry.id in identifiers:
            raise ValueError(f"duplicate board id: {entry.id}")
        identifiers.add(entry.id)
        relative = _package_slug_path(entry.path, root, f"catalog.boards[{index}].path")
        package_root = root / relative
        if package_root in paths:
            raise ValueError(f"duplicate board package path: {entry.path}")
        paths.add(package_root)
        if not package_root.is_dir() or package_root.is_symlink():
            raise ValueError(f"catalog package directory does not exist: {package_root}")
        package = load_board_package(package_root)
        if package.board.id != entry.id:
            raise ValueError(f"board package ID {package.board.id!r} does not match catalog id {entry.id!r}")
        if package.board.presentation_asset_path != "assets/primary.png":
            raise ValueError("registered board package must present assets/primary.png")
        primary_asset = package.root / "assets/primary.png"
        if not primary_asset.is_file():
            raise ValueError("registered board package assets/primary.png does not exist")
        if not _is_png(primary_asset):
            raise ValueError("registered board package assets/primary.png must contain PNG image data")
    return catalog
