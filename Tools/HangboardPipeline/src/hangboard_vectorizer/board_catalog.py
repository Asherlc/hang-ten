"""Fail-closed registry and approved board-package validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import importlib.util
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlparse

try:  # Standard package import, plus direct-file loading used by pipeline tests.
    from .board_artwork import BoardArtworkDocument, load_artwork
except ImportError:  # pragma: no cover - exercised by direct module consumers
    _artwork_path = Path(__file__).with_name("board_artwork.py")
    _spec = importlib.util.spec_from_file_location("hangboard_board_artwork", _artwork_path)
    assert _spec and _spec.loader
    _module = importlib.util.module_from_spec(_spec)
    import sys
    sys.modules[_spec.name] = _module
    _spec.loader.exec_module(_module)
    BoardArtworkDocument = _module.BoardArtworkDocument
    load_artwork = _module.load_artwork


_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:[a-z0-9._-]*[a-z0-9])?$")
_STATUSES = frozenset({"draft", "approved"})
_SIDECARS = ("board.json", "evidence.json", "semantics.json", "artwork.json")
_EVIDENCE_METHODS = frozenset({"manufacturer-measurement", "reviewed-human-authored-normalization", "external-generative-adaptation"})


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
    status: str

    @classmethod
    def from_json(cls, value: Any, source: str) -> "CatalogEntry":
        payload = _mapping(value, source)
        _closed(payload, {"id", "path", "status"}, source)
        status = _string(payload["status"], f"{source}.status")
        if status not in _STATUSES:
            raise ValueError(f"{source}.status must be one of ('draft', 'approved')")
        return cls(_identifier(payload["id"], f"{source}.id"), _string(payload["path"], f"{source}.path"), status)


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
class BoardHold:
    id: str
    name: str


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
    artwork_evidence: Mapping[str, EvidenceMapping]
    asset_evidence: Mapping[str, EvidenceMapping]


@dataclass(frozen=True)
class BoardPackage:
    root: Path
    board: BoardDocument
    evidence: BoardEvidenceDocument
    semantics: BoardSemanticsDocument
    artwork: BoardArtworkDocument


def _load_board(value: Mapping[str, Any], root: Path) -> BoardDocument:
    _closed(value, {"schemaVersion", "id", "manufacturer", "name", "productURL", "dimensions", "aspectRatio", "presentation", "holds"}, "board.json")
    if isinstance(value["schemaVersion"], bool) or value["schemaVersion"] != 1:
        raise ValueError("board.json.schemaVersion must be 1")
    board_id = _identifier(value["id"], "board.json.id")
    fact_keys = {"manufacturer", "name", "productURL", "dimensions", "aspectRatio"}
    facts: dict[str, Any] = {}
    for key in fact_keys:
        if key == "aspectRatio":
            facts[key] = _number(value[key], f"board.json.{key}")
        else:
            facts[key] = _string(value[key], f"board.json.{key}")
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
        item = _mapping(raw, f"board.json.holds[{index}]")
        _closed(item, {"id", "name"}, f"board.json.holds[{index}]")
        holds.append(BoardHold(_identifier(item["id"], f"board.json.holds[{index}].id"), _string(item["name"], f"board.json.holds[{index}].name")))
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
    required = {"schemaVersion", "boardID", "checkedAt", "sources", "fieldEvidence", "holdEvidence", "semanticEvidence", "artworkEvidence", "assetEvidence"}
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
    return BoardEvidenceDocument(_identifier(value["boardID"], "evidence.json.boardID"), parse_map("fieldEvidence"), parse_map("holdEvidence"), parse_map("semanticEvidence"), parse_map("artworkEvidence"), parse_map("assetEvidence"))


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
    for item in assets_root.rglob("*"):
        if item.is_symlink():
            raise ValueError(f"package contains symlink: {item}")
        if item.is_file():
            assets.add(item.relative_to(root).as_posix())
    return assets


def load_approved_package(package_root: Path) -> BoardPackage:
    root = Path(package_root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"approved package does not exist or is not a directory: {root}")
    _require_no_symlinks(root)
    for sidecar in _SIDECARS:
        if not (root / sidecar).is_file():
            raise ValueError(f"approved package {root} {sidecar} does not exist")
    extra_json = {path.name for path in root.glob("*.json")} - set(_SIDECARS)
    if extra_json:
        raise ValueError(f"approved package has unknown JSON sidecars: {sorted(extra_json)}")
    board = _load_board(_load_json(root / "board.json", "board.json"), root)
    evidence = _load_evidence(_load_json(root / "evidence.json", "evidence.json"))
    semantics = _load_semantics(_load_json(root / "semantics.json", "semantics.json"))
    artwork = load_artwork(root / "artwork.json")
    if len({board.id, evidence.board_id, semantics.board_id, artwork.board_id}) != 1:
        raise ValueError("approved package sidecar board IDs must match")
    hold_ids = {hold.id for hold in board.holds}
    for semantic, mapped_holds in semantics.semantic_holds.items():
        for hold_id in mapped_holds:
            if hold_id not in hold_ids:
                raise ValueError(f"semantic {semantic!r} references unknown physical hold {hold_id!r}")
    if artwork.hold_ids != hold_ids:
        raise ValueError("artwork hold IDs must exactly match board physical hold IDs")
    for piece in artwork.hold_pieces:
        if piece.hold_id not in hold_ids:
            raise ValueError(f"artwork piece references unknown physical hold {piece.hold_id!r}")
    _exact_keys(evidence.field_evidence, set(board.facts), "fieldEvidence keys must equal board factual fields")
    _exact_keys(evidence.hold_evidence, hold_ids, "holdEvidence keys must equal physical hold IDs")
    _exact_keys(evidence.semantic_evidence, set(semantics.semantic_holds), "semanticEvidence keys must equal semantic IDs")
    artwork_keys = {"silhouette", *(f"layers.{layer.id}" for layer in artwork.layers), *(f"holdPieces.{piece.id}" for piece in artwork.hold_pieces)}
    _exact_keys(evidence.artwork_evidence, artwork_keys, "artworkEvidence keys must equal artwork elements")
    assets = _package_assets(root)
    _exact_keys(evidence.asset_evidence, assets, "assetEvidence keys must equal package assets")
    if board.presentation_asset_path not in assets:
        raise ValueError("board presentation asset must resolve to a package asset")
    return BoardPackage(root.resolve(), board, evidence, semantics, artwork)


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
        relative = _relative_path(entry.path, root, f"catalog.boards[{index}].path", container="catalog")
        package_root = root / relative
        if package_root in paths:
            raise ValueError(f"duplicate board package path: {entry.path}")
        paths.add(package_root)
        if not package_root.is_dir() or package_root.is_symlink():
            raise ValueError(f"catalog package directory does not exist: {package_root}")
        if entry.status == "approved":
            package = load_approved_package(package_root)
            if package.board.id != entry.id:
                raise ValueError(f"approved package board ID {package.board.id!r} does not match catalog id {entry.id!r}")
    return catalog
