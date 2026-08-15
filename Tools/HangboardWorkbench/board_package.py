"""Direct canonical board-package tools owned by Hangboard Workbench."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
import fcntl
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from typing import Any, Iterator, Mapping
from urllib.parse import urlparse

from board_geometry import (
    GeometryError,
    NormalizedFrame,
    display_path_for_shape,
    normalized_frame_for_path,
    parse_closed_path,
    shape_for_path,
)


_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:[a-z0-9._-]*[a-z0-9])?$")
_SLUG = re.compile(r"^[a-z0-9]+(?:[a-z0-9-]*[a-z0-9])?$")
_SIDECARS = ("board.json", "artwork.json", "evidence.json", "semantics.json")
_ROOT_ITEMS = frozenset((*_SIDECARS, "assets"))
_HOLD_KINDS = frozenset({"jug", "edge", "pocket", "pinch", "sloper"})
_GRIP_TYPES = frozenset({"openHand", "halfCrimp", "fullCrimp", "fourFingerPocket", "threeFingerPocket", "twoFingerPocket", "sloper"})
_CUE_STYLES = frozenset({"outerJug", "slot", "pinch", "rounded"})
_TREATMENT_TYPES = frozenset({"surface", "shelf", "recess"})
_RECESS_DEPTHS = frozenset({"shallow", "deep"})
_ARTWORK_PALETTES = frozenset({"sculptedWood"})
_ARTWORK_LAYER_ROLES = frozenset({"topPlane", "separator", "bottomPlane", "topSeam"})
_FRAME_TOLERANCE = 0.0000005
_HOLD_FEATURES = frozenset({
    "jug", "roundSloper", "largeSlope", "largeEdge", "mediumEdge", "smallEdge",
    "pocket", "twoFingerPocket", "threeFingerPocket", "fourFingerPocket",
    "fourFingerFlatEdge", "fourFingerIncutEdge", "largeOpenHandRail",
    "deepTwoFingerPocket", "thinCrimp", "shallowThreeFingerSlot", "widePinch",
    "mediumPinch", "smallPinch",
})
_HOLD_FIELDS = frozenset({
    "id", "name", "shortLabel", "detail", "kind", "frame", "sizeMillimeters",
    "depthRangeMillimeters", "gripType", "fingerCapacity", "cueStyle", "features",
})
_FACT_FIELDS = frozenset({"manufacturer", "name", "subtitle", "productURL", "dimensions", "aspectRatio"})
_EVIDENCE_METHODS = frozenset({
    "manufacturer-measurement", "reviewed-human-authored-normalization", "external-generative-adaptation",
})
_CANONICAL_EVIDENCE_METHODS = _EVIDENCE_METHODS - {"external-generative-adaptation"}
_SOURCE_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".webp", ".heic"})


class BoardPackageError(ValueError):
    """Raised for invalid or unsafe direct board-package operations."""


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    board_id: str
    slug: str


@dataclass(frozen=True, slots=True)
class BoardPackage:
    root: Path
    board: dict[str, Any]
    artwork: dict[str, Any]
    evidence: dict[str, Any]
    semantics: dict[str, Any]

    @property
    def board_id(self) -> str:
        return self.board["id"]

    @property
    def hold_ids(self) -> tuple[str, ...]:
        return tuple(hold["id"] for hold in self.board["holds"])


def discover_packages(library_root: Path) -> tuple[CatalogEntry, ...]:
    """Read the direct board catalog and validate every registered package."""
    root = _library_root(library_root)
    with _library_lock(root, shared=True):
        entries = _load_catalog(root / "catalog.json")
        for entry in entries:
            package = load_board_package(root / entry.slug)
            if package.board_id != entry.board_id:
                raise BoardPackageError("catalog board ID does not match its package")
        return entries


def open_registered_package(library_root: Path, board_id: str) -> BoardPackage:
    """Load one catalogued package while holding a coherent library read lock."""
    root = _library_root(library_root)
    board_id = _identifier(board_id, "board ID")
    with _library_lock(root, shared=True):
        entry = next(
            (candidate for candidate in _load_catalog(root / "catalog.json") if candidate.board_id == board_id),
            None,
        )
        if entry is None:
            raise BoardPackageError("board is not registered")
        package = load_board_package(root / entry.slug)
        if package.board_id != entry.board_id:
            raise BoardPackageError("catalog board ID does not match its package")
        return package


def load_board_package(package_root: Path) -> BoardPackage:
    """Load one canonical package without accepting links or extra package files."""
    root = Path(package_root)
    if root.is_symlink():
        raise BoardPackageError("board package must not be a symlink")
    try:
        root = root.resolve(strict=True)
    except OSError as error:
        raise BoardPackageError("board package is not accessible") from error
    if not root.is_dir() or root.is_symlink():
        raise BoardPackageError("board package must be a directory")
    _reject_symlinks(root)
    if {item.name for item in root.iterdir()} != _ROOT_ITEMS:
        raise BoardPackageError("board package must contain only canonical sidecars and assets")
    documents = {name.removesuffix(".json"): _load_json(root / name, name) for name in _SIDECARS}
    board = documents["board"]
    artwork = documents["artwork"]
    evidence = documents["evidence"]
    semantics = documents["semantics"]
    _validate_board(board)
    _validate_sidecar_identity(artwork, "artwork.json")
    _validate_sidecar_identity(evidence, "evidence.json")
    _validate_sidecar_identity(semantics, "semantics.json")
    if {board["id"], artwork["boardID"], evidence["boardID"], semantics["boardID"]} != {board["id"]}:
        raise BoardPackageError("board package sidecar board IDs must match")
    assets = _validate_assets(root, board)
    _validate_semantics(semantics, set(hold["id"] for hold in board["holds"]))
    _validate_artwork(artwork, board)
    _validate_board_hold_frames(board, artwork, *_png_dimensions(root / "assets" / "primary.png"))
    _validate_evidence(evidence, board, semantics, artwork, assets)
    return BoardPackage(root, board, artwork, evidence, semantics)


def primary_image_path(package: BoardPackage) -> Path:
    """Return the one canonical package image after confinement validation."""
    image = _confined_path(package.root, "assets/primary.png", "primary image")
    if not image.is_file() or image.is_symlink():
        raise BoardPackageError("package primary image is missing")
    _png_dimensions(image)
    return image


def editor_document(package: BoardPackage) -> dict[str, object]:
    """Build the direct editable hold document from saved canonical package data."""
    width, height = _png_dimensions(primary_image_path(package))
    pieces = {piece["holdID"]: piece for piece in package.artwork["holdPieces"]}
    regions: list[dict[str, object]] = []
    for index, hold in enumerate(package.board["holds"], start=1):
        hold_id = hold["id"]
        try:
            path = display_path_for_shape(
                pieces[hold_id]["frame"], pieces[hold_id]["shape"], width, height, label=f"hold {hold_id}"
            )
        except (KeyError, GeometryError) as error:
            raise BoardPackageError(f"hold {hold_id} has invalid artwork geometry") from error
        regions.append(
            {
                "id": index,
                "key": hold_id,
                "type": hold["kind"],
                "displayPath": path.data,
                "metadata": {},
            }
        )
    return {"schemaVersion": 1, "canvas": {"width": width, "height": height}, "regions": regions}


def save_editor_document(library_root: Path, slug: str, document: Mapping[str, Any]) -> BoardPackage:
    """Validate edited hold paths and save their paths and derived frames together."""
    root = _library_root(library_root)
    slug = _slug(slug)
    with _library_lock(root):
        live = load_board_package(root / slug)
        width, height = _png_dimensions(primary_image_path(live))
        regions = _validate_editor_document(document, live.hold_ids, width, height)
        candidate_parent = Path(tempfile.mkdtemp(prefix=".workbench-edit-", dir=root))
        candidate = candidate_parent / slug
        try:
            shutil.copytree(live.root, candidate)
            artwork_path = candidate / "artwork.json"
            board_path = candidate / "board.json"
            artwork = _load_json(artwork_path, "artwork.json")
            board = _load_json(board_path, "board.json")
            pieces = {piece["holdID"]: piece for piece in artwork["holdPieces"]}
            holds = {hold["id"]: hold for hold in board["holds"]}
            for hold_id, path in regions.items():
                frame, shape = shape_for_path(path, width, height)
                pieces[hold_id]["frame"] = frame.to_json()
                pieces[hold_id]["shape"] = shape
                holds[hold_id]["frame"] = frame.to_json()
            _write_json(artwork_path, artwork)
            _write_json(board_path, board)
            _replace_package_locked(root, slug, candidate)
            return load_board_package(root / slug)
        finally:
            shutil.rmtree(candidate_parent, ignore_errors=True)


def replace_package(library_root: Path, slug: str, candidate_root: Path) -> None:
    """Replace one canonical package and catalog entry with rollback on failure."""
    root = _library_root(library_root)
    slug = _slug(slug)
    with _library_lock(root):
        _replace_package_locked(root, slug, candidate_root)


def _replace_package_locked(root: Path, slug: str, candidate_root: Path) -> None:
    """Perform every read, validation, and replacement under the library lock."""
    candidate = load_board_package(candidate_root)
    stage = Path(tempfile.mkdtemp(prefix=".workbench-save-", dir=root))
    staged_package = stage / slug
    staged_catalog = stage / "catalog.json"
    try:
        shutil.copytree(candidate.root, staged_package)
        candidate = load_board_package(staged_package)
        catalog = list(_load_catalog(root / "catalog.json"))
        previous = next((entry for entry in catalog if entry.slug == slug), None)
        if previous is not None and previous.board_id != candidate.board_id:
            raise BoardPackageError("replacement package must keep the registered board ID")
        replacement = CatalogEntry(candidate.board_id, slug)
        if previous is None:
            if any(entry.board_id == candidate.board_id for entry in catalog):
                raise BoardPackageError("catalog already registers this board ID")
            catalog.append(replacement)
        else:
            catalog[catalog.index(previous)] = replacement
        _write_json(staged_catalog, _catalog_json(catalog))
        _validate_staged_catalog(root, catalog, slug, staged_package)
        _replace_transaction(root, slug, staged_package, staged_catalog)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _validate_board(board: Mapping[str, Any]) -> None:
    _exact_keys(
        board,
        {"schemaVersion", "id", *_FACT_FIELDS, "holds", "presentation"},
        "board.json",
    )
    _schema_version_one(board.get("schemaVersion"), "board.json.schemaVersion")
    _identifier(board.get("id"), "board.json.id")
    for field in _FACT_FIELDS - {"aspectRatio", "productURL"}:
        _non_empty_string(board.get(field), f"board.json.{field}")
    _https_url(board.get("productURL"), "board.json.productURL")
    _positive_number(board.get("aspectRatio"), "board.json.aspectRatio")
    holds = board.get("holds")
    if not isinstance(holds, list) or not holds:
        raise BoardPackageError("board.json.holds must be a non-empty array")
    identifiers: set[str] = set()
    for index, hold in enumerate(holds):
        if not isinstance(hold, dict):
            raise BoardPackageError(f"board.json.holds[{index}] must be an object")
        _exact_keys(hold, _HOLD_FIELDS, f"board.json.holds[{index}]")
        hold_id = _identifier(hold.get("id"), f"board.json.holds[{index}].id")
        if hold_id in identifiers:
            raise BoardPackageError("duplicate hold ID")
        identifiers.add(hold_id)
        _enum(hold.get("kind"), _HOLD_KINDS, f"board.json.holds[{index}].kind")
        for field in ("name", "shortLabel", "detail"):
            _non_empty_string(hold.get(field), f"board.json.holds[{index}].{field}")
        try:
            NormalizedFrame.from_json(hold.get("frame"), f"board.json.holds[{index}].frame")
        except (GeometryError, TypeError) as error:
            raise BoardPackageError(f"board.json.holds[{index}].frame is invalid") from error
        _nullable_positive_integer(hold.get("sizeMillimeters"), f"board.json.holds[{index}].sizeMillimeters")
        _nullable_millimeter_range(hold.get("depthRangeMillimeters"), f"board.json.holds[{index}].depthRangeMillimeters")
        _enum(hold.get("gripType"), _GRIP_TYPES, f"board.json.holds[{index}].gripType")
        capacity = hold.get("fingerCapacity")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity not in range(1, 5):
            raise BoardPackageError(f"board.json.holds[{index}].fingerCapacity must be in 1...4")
        _enum(hold.get("cueStyle"), _CUE_STYLES, f"board.json.holds[{index}].cueStyle")
        features = hold.get("features")
        if not isinstance(features, list):
            raise BoardPackageError(f"board.json.holds[{index}].features must be an array")
        parsed_features = [_enum(feature, _HOLD_FEATURES, f"board.json.holds[{index}].features[{feature_index}]") for feature_index, feature in enumerate(features)]
        if len(parsed_features) != len(set(parsed_features)):
            raise BoardPackageError(f"board.json.holds[{index}].features must be unique")
    presentation = board.get("presentation")
    if not isinstance(presentation, dict) or presentation.get("assetPath") != "assets/primary.png" or set(presentation) != {"assetPath"}:
        raise BoardPackageError("board.json.presentation must declare assets/primary.png")


def _validate_artwork(artwork: Mapping[str, Any], board: Mapping[str, Any]) -> None:
    _exact_keys(artwork, {"schemaVersion", "boardID", "canvasFrame", "palette", "silhouette", "layers", "holdPieces"}, "artwork.json")
    _schema_version_one(artwork.get("schemaVersion"), "artwork.json.schemaVersion")
    if not isinstance(artwork.get("holdPieces"), list):
        raise BoardPackageError("artwork.json is invalid")
    try:
        NormalizedFrame.from_json(artwork["canvasFrame"], "artwork.json.canvasFrame")
        display_path_for_shape({"x": 0, "y": 0, "width": 1, "height": 1}, artwork["silhouette"], 1000, 1000, label="silhouette")
    except (GeometryError, KeyError, TypeError) as error:
        raise BoardPackageError("artwork.json is invalid") from error
    _enum(artwork["palette"], _ARTWORK_PALETTES, "artwork.json.palette")
    layers = artwork["layers"]
    if not isinstance(layers, list):
        raise BoardPackageError("artwork.json.layers must be an array")
    layer_ids: set[str] = set()
    for index, layer in enumerate(layers):
        if not isinstance(layer, Mapping):
            raise BoardPackageError(f"artwork.json.layers[{index}] must be an object")
        _exact_keys(layer, {"id", "role", "frame", "shape"}, f"artwork.json.layers[{index}]")
        layer_id = _identifier(layer.get("id"), f"artwork.json.layers[{index}].id")
        if layer_id in layer_ids:
            raise BoardPackageError("duplicate artwork layer ID")
        layer_ids.add(layer_id)
        _enum(layer.get("role"), _ARTWORK_LAYER_ROLES, f"artwork.json.layers[{index}].role")
        try:
            NormalizedFrame.from_json(layer["frame"], f"artwork.json.layers[{index}].frame")
            display_path_for_shape(
                layer["frame"], layer["shape"], 1000, 1000, label=f"layer {layer_id}"
            )
        except (KeyError, GeometryError, TypeError) as error:
            raise BoardPackageError(f"layer {layer_id} has invalid geometry") from error
    hold_ids = {hold["id"] for hold in board["holds"]}
    pieces: list[Mapping[str, Any]] = []
    seen_piece_ids: set[str] = set()
    seen_hold_ids: set[str] = set()
    for index, raw in enumerate(artwork["holdPieces"]):
        if not isinstance(raw, dict):
            raise BoardPackageError(f"artwork.json.holdPieces[{index}] must be an object")
        piece_label = f"artwork.json.holdPieces[{index}]"
        _exact_keys(raw, {"id", "holdID", "frame", "shape", "treatment"}, piece_label)
        _validate_artwork_treatment(raw["treatment"], f"{piece_label}.treatment")
        piece_id = _identifier(raw.get("id"), f"artwork.json.holdPieces[{index}].id")
        hold_id = _identifier(raw.get("holdID"), f"artwork.json.holdPieces[{index}].holdID")
        if piece_id in seen_piece_ids:
            raise BoardPackageError("duplicate artwork piece ID")
        if hold_id in seen_hold_ids:
            raise BoardPackageError("duplicate hold ID in artwork")
        seen_piece_ids.add(piece_id)
        seen_hold_ids.add(hold_id)
        pieces.append(raw)
    if seen_hold_ids != hold_ids:
        raise BoardPackageError("artwork hold IDs must exactly match board hold IDs")
    for piece in pieces:
        try:
            display_path_for_shape(piece["frame"], piece["shape"], 1000, 1000, label=f"hold {piece['holdID']}")
        except (KeyError, GeometryError) as error:
            raise BoardPackageError(f"hold {piece['holdID']} has invalid artwork geometry") from error


def _validate_board_hold_frames(
    board: Mapping[str, Any], artwork: Mapping[str, Any], width: int, height: int
) -> None:
    """Require each saved board frame to match the exact rendered hold outline.

    Frame values are normalized canvas coordinates.  They may differ from the
    derived floating-point value by at most half of one millionth (the direct
    package's six-decimal rounding precision).
    """
    pieces = {piece["holdID"]: piece for piece in artwork["holdPieces"]}
    for index, hold in enumerate(board["holds"]):
        hold_id = hold["id"]
        try:
            outline = display_path_for_shape(
                pieces[hold_id]["frame"],
                pieces[hold_id]["shape"],
                width,
                height,
                label=f"hold {hold_id}",
            )
            derived = NormalizedFrame.from_json(
                normalized_frame_for_path(outline, width, height).to_json(),
                f"hold {hold_id}.derivedFrame",
            )
            declared = NormalizedFrame.from_json(
                hold["frame"], f"board.json.holds[{index}].frame"
            )
        except (KeyError, GeometryError, TypeError) as error:
            raise BoardPackageError(f"hold {hold_id} has invalid artwork geometry") from error
        if not _frames_match(declared, derived):
            raise BoardPackageError(
                f"board.json.holds[{index}].frame must match its derived artwork outline"
            )


def _validate_artwork_treatment(value: object, label: str) -> None:
    """Validate optional decorative rendering data without treating it as hold geometry."""
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    treatment_type = _enum(value.get("type"), _TREATMENT_TYPES, f"{label}.type")
    if treatment_type == "surface":
        _exact_keys(value, {"type"}, label)
        return
    if treatment_type == "shelf":
        _exact_keys(value, {"type", "rimInsetFraction"}, label)
        _inclusive_fraction(value["rimInsetFraction"], f"{label}.rimInsetFraction")
        return
    _exact_keys(value, {"type", "rimInsetFraction", "depth"}, label)
    _inclusive_fraction(value["rimInsetFraction"], f"{label}.rimInsetFraction")
    _enum(value["depth"], _RECESS_DEPTHS, f"{label}.depth")


def _validate_semantics(semantics: Mapping[str, Any], hold_ids: set[str]) -> None:
    _exact_keys(semantics, {"schemaVersion", "boardID", "semanticHolds"}, "semantics.json")
    _schema_version_one(semantics.get("schemaVersion"), "semantics.json.schemaVersion")
    raw_holds = semantics.get("semanticHolds")
    if not isinstance(raw_holds, dict):
        raise BoardPackageError("semantics.json.semanticHolds must be an object")
    for semantic, value in raw_holds.items():
        _identifier(semantic, "semantics.json semantic ID")
        if not isinstance(value, dict):
            raise BoardPackageError("semantics.json contains an invalid hold mapping")
        _exact_keys(value, {"holdIDs"}, f"semantics.json.semanticHolds.{semantic}")
        if not isinstance(value["holdIDs"], list) or not value["holdIDs"]:
            raise BoardPackageError(f"semantics.json.semanticHolds.{semantic}.holdIDs must be non-empty")
        semantic_hold_ids: list[str] = []
        for hold_id in value["holdIDs"]:
            _identifier(hold_id, f"semantics.json.semanticHolds.{semantic}.holdIDs")
            if hold_id not in hold_ids:
                raise BoardPackageError(f"semantic {semantic!r} references an unknown hold")
            semantic_hold_ids.append(hold_id)
        if len(semantic_hold_ids) != len(set(semantic_hold_ids)):
            raise BoardPackageError(f"semantics.json.semanticHolds.{semantic}.holdIDs must be unique")


def _validate_evidence(
    evidence: Mapping[str, Any],
    board: Mapping[str, Any],
    semantics: Mapping[str, Any],
    artwork: Mapping[str, Any],
    assets: set[str],
) -> None:
    _exact_keys(
        evidence,
        {"schemaVersion", "boardID", "checkedAt", "sources", "fieldEvidence", "holdEvidence", "semanticEvidence", "artworkEvidence", "assetEvidence"},
        "evidence.json",
    )
    _schema_version_one(evidence.get("schemaVersion"), "evidence.json.schemaVersion")
    try:
        date.fromisoformat(_non_empty_string(evidence.get("checkedAt"), "evidence.json.checkedAt"))
    except ValueError as error:
        raise BoardPackageError("evidence.json.checkedAt must be an ISO calendar date") from error
    sources = evidence.get("sources")
    if not isinstance(sources, list) or not sources:
        raise BoardPackageError("evidence.json.sources must be non-empty")
    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            raise BoardPackageError(f"evidence.json.sources[{index}] must be an object")
        _exact_keys(source, {"id", "title", "url"}, f"evidence.json.sources[{index}]")
        source_id = _identifier(source.get("id"), f"evidence.json.sources[{index}].id")
        if source_id in source_ids:
            raise BoardPackageError("duplicate evidence source ID")
        source_ids.add(source_id)
        _non_empty_string(source.get("title"), f"evidence.json.sources[{index}].title")
        _https_url(source.get("url"), f"evidence.json.sources[{index}].url")

    expected_hold_evidence = {f"{hold['id']}.{field}" for hold in board["holds"] for field in _HOLD_FIELDS}
    expected_artwork_evidence = {
        "silhouette",
        *(f"layers.{layer['id']}" for layer in artwork["layers"]),
        *(f"holdPieces.{piece['id']}" for piece in artwork["holdPieces"]),
    }
    _validate_evidence_map(
        evidence.get("fieldEvidence"), _FACT_FIELDS, "fieldEvidence", source_ids, _CANONICAL_EVIDENCE_METHODS
    )
    _validate_evidence_map(
        evidence.get("holdEvidence"), expected_hold_evidence, "holdEvidence", source_ids, _CANONICAL_EVIDENCE_METHODS
    )
    _validate_evidence_map(
        evidence.get("semanticEvidence"), set(semantics["semanticHolds"]), "semanticEvidence", source_ids, _CANONICAL_EVIDENCE_METHODS
    )
    _validate_evidence_map(
        evidence.get("artworkEvidence"), expected_artwork_evidence, "artworkEvidence", source_ids, _CANONICAL_EVIDENCE_METHODS
    )
    _validate_evidence_map(
        evidence.get("assetEvidence"),
        assets,
        "assetEvidence",
        source_ids,
        _EVIDENCE_METHODS,
        external_generation_keys=frozenset({"assets/primary.png"}),
    )


def _validate_evidence_map(
    value: object,
    expected: set[str] | frozenset[str],
    label: str,
    source_ids: set[str],
    allowed_methods: frozenset[str],
    *,
    external_generation_keys: frozenset[str] = frozenset(),
) -> None:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"evidence.json.{label} must be an object")
    if set(value) != set(expected):
        raise BoardPackageError(f"evidence.json.{label} keys must exactly match canonical data")
    for key, mapping in value.items():
        if isinstance(mapping, Mapping):
            _exact_keys(mapping, {"sourceIDs", "method"}, f"evidence.json.{label}.{key}")
            raw_source_ids = mapping.get("sourceIDs")
            method = _enum(mapping.get("method"), _EVIDENCE_METHODS, f"evidence.json.{label}.{key}.method")
            if method not in allowed_methods:
                raise BoardPackageError(
                    f"evidence.json.{label}.{key}.method {method} is not permitted"
                )
            if (
                method == "external-generative-adaptation"
                and key not in external_generation_keys
            ):
                raise BoardPackageError(
                    f"evidence.json.{label}.{key}.method {method} is not permitted"
                )
        else:
            raise BoardPackageError(f"evidence.json.{label}.{key} must be an object")
        if not isinstance(raw_source_ids, list) or not raw_source_ids:
            raise BoardPackageError(f"evidence.json.{label}.{key}.sourceIDs must be non-empty")
        references = [_identifier(item, f"evidence.json.{label}.{key}.sourceIDs") for item in raw_source_ids]
        if len(references) != len(set(references)):
            raise BoardPackageError(f"evidence.json.{label}.{key}.sourceIDs must be unique")
        if unknown := set(references) - source_ids:
            raise BoardPackageError(f"evidence.json.{label}.{key} references unknown source ID {sorted(unknown)[0]!r}")


def _validate_assets(root: Path, board: Mapping[str, Any]) -> set[str]:
    _confined_path(root, board["presentation"]["assetPath"], "presentation asset")
    assets = root / "assets"
    if not assets.is_dir() or assets.is_symlink():
        raise BoardPackageError("package assets must be a directory")
    asset_paths: set[str] = set()
    source_count = 0
    for item in assets.iterdir():
        if not item.is_file() or item.is_symlink():
            raise BoardPackageError("package assets must be flat regular files")
        if item.name == "primary.png":
            asset_paths.add("assets/primary.png")
            continue
        if item.suffix.lower() not in _SOURCE_IMAGE_EXTENSIONS:
            raise BoardPackageError("package source asset must be a supported image")
        source_count += 1
        if source_count > 1:
            raise BoardPackageError("package may contain at most one original source image")
        asset_paths.add(f"assets/{item.name}")
    _png_dimensions(assets / "primary.png")
    return asset_paths


def _validate_sidecar_identity(document: Mapping[str, Any], name: str) -> None:
    _identifier(document.get("boardID"), f"{name}.boardID")


def _validate_editor_document(document: Mapping[str, Any], hold_ids: tuple[str, ...], width: int, height: int) -> dict[str, Any]:
    canvas = document.get("canvas") if isinstance(document, Mapping) else None
    if not isinstance(document, Mapping) or canvas != {"width": width, "height": height}:
        raise BoardPackageError("editor document canvas does not match the primary image")
    _schema_version_one(document.get("schemaVersion"), "editor document.schemaVersion")
    raw_regions = document.get("regions")
    if not isinstance(raw_regions, list):
        raise BoardPackageError("editor document regions must be an array")
    paths: dict[str, Any] = {}
    for region in raw_regions:
        if not isinstance(region, Mapping) or not isinstance(region.get("key"), str):
            raise BoardPackageError("editor document contains an invalid hold")
        hold_id = region["key"]
        if hold_id in paths:
            raise BoardPackageError("duplicate hold ID")
        try:
            paths[hold_id] = parse_closed_path(region.get("displayPath"), width, height, label=f"hold {hold_id}")
        except GeometryError as error:
            raise BoardPackageError(str(error)) from error
    if set(paths) != set(hold_ids):
        raise BoardPackageError("editor document hold IDs must exactly match board hold IDs")
    return paths


def _load_catalog(path: Path) -> tuple[CatalogEntry, ...]:
    raw = _load_json(path, "catalog.json")
    _exact_keys(raw, {"schemaVersion", "boards"}, "catalog.json")
    _schema_version_one(raw.get("schemaVersion"), "catalog.json.schemaVersion")
    if not isinstance(raw.get("boards"), list):
        raise BoardPackageError("catalog.json is invalid")
    entries: list[CatalogEntry] = []
    identifiers: set[str] = set()
    slugs: set[str] = set()
    for index, raw_entry in enumerate(raw["boards"]):
        if not isinstance(raw_entry, dict) or set(raw_entry) != {"id", "path"}:
            raise BoardPackageError(f"catalog.json.boards[{index}] is invalid")
        board_id = _identifier(raw_entry["id"], f"catalog.json.boards[{index}].id")
        slug = _slug(raw_entry["path"])
        if board_id in identifiers or slug in slugs:
            raise BoardPackageError("catalog.json contains duplicate board entries")
        identifiers.add(board_id)
        slugs.add(slug)
        entries.append(CatalogEntry(board_id, slug))
    return tuple(entries)


def _catalog_json(entries: list[CatalogEntry]) -> dict[str, object]:
    return {"schemaVersion": 1, "boards": [{"id": entry.board_id, "path": entry.slug} for entry in entries]}


def _validate_staged_catalog(root: Path, entries: list[CatalogEntry], staged_slug: str, staged_package: Path) -> None:
    for entry in entries:
        package = staged_package if entry.slug == staged_slug else root / entry.slug
        loaded = load_board_package(package)
        if loaded.board_id != entry.board_id:
            raise BoardPackageError("catalog board ID does not match its package")


def _replace_transaction(root: Path, slug: str, staged_package: Path, staged_catalog: Path) -> None:
    live_package = root / slug
    catalog = root / "catalog.json"
    package_backup = root / f".{slug}.workbench-backup"
    catalog_backup = root / ".catalog.workbench-backup.json"
    if package_backup.exists() or catalog_backup.exists():
        raise BoardPackageError("a previous board save needs recovery")
    package_moved = False
    package_installed = False
    catalog_moved = False
    try:
        if live_package.exists():
            os.replace(live_package, package_backup)
            package_moved = True
        os.replace(staged_package, live_package)
        package_installed = True
        os.replace(catalog, catalog_backup)
        catalog_moved = True
        os.replace(staged_catalog, catalog)
    except OSError as error:
        _restore_transaction(
            live_package,
            catalog,
            package_backup,
            catalog_backup,
            package_moved,
            package_installed,
            catalog_moved,
        )
        raise BoardPackageError("could not save board package") from error
    else:
        if package_backup.exists():
            shutil.rmtree(package_backup)
        if catalog_backup.exists():
            catalog_backup.unlink()


def _restore_transaction(
    live_package: Path,
    catalog: Path,
    package_backup: Path,
    catalog_backup: Path,
    package_moved: bool,
    package_installed: bool,
    catalog_moved: bool,
) -> None:
    try:
        if catalog_moved and catalog_backup.exists():
            if catalog.exists():
                catalog.unlink()
            os.replace(catalog_backup, catalog)
        if package_installed and live_package.exists():
            shutil.rmtree(live_package)
        if package_moved and package_backup.exists():
            os.replace(package_backup, live_package)
    except OSError as error:  # A persistent backup is safer than a partial hidden failure.
        raise BoardPackageError("could not restore the previous board package") from error


@contextmanager
def _library_lock(root: Path, *, shared: bool = False) -> Iterator[None]:
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        raise BoardPackageError("safe workbench lock opening is unavailable")
    try:
        descriptor = os.open(
            root / ".workbench.lock", os.O_CREAT | os.O_RDWR | no_follow, 0o600
        )
    except OSError as error:
        raise BoardPackageError("workbench lock must be a regular file") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise BoardPackageError("workbench lock must be a regular file")
        fcntl.flock(descriptor, fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _library_root(path: Path) -> Path:
    if Path(path).is_symlink():
        raise BoardPackageError("board library must not be a symlink")
    try:
        root = Path(path).resolve(strict=True)
    except OSError as error:
        raise BoardPackageError("board library is not accessible") from error
    if not root.is_dir() or root.is_symlink():
        raise BoardPackageError("board library must be a directory")
    return root


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise BoardPackageError(f"{label} is missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BoardPackageError(f"{label} is invalid JSON") from error
    if not isinstance(value, dict):
        raise BoardPackageError(f"{label} must be an object")
    return value


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _exact_keys(value: Mapping[str, Any], expected: set[str] | frozenset[str], label: str) -> None:
    unknown = set(value) - set(expected)
    missing = set(expected) - set(value)
    if unknown or missing:
        details: list[str] = []
        if unknown:
            details.append(f"unknown keys: {sorted(unknown)}")
        if missing:
            details.append(f"missing keys: {sorted(missing)}")
        raise BoardPackageError(f"{label} has " + "; ".join(details))


def _non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise BoardPackageError(f"{label} must be a non-empty string")
    return value


def _schema_version_one(value: object, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value != 1:
        raise BoardPackageError(f"{label} must be 1")


def _frames_match(declared: NormalizedFrame, derived: NormalizedFrame) -> bool:
    return all(
        abs(actual - expected) <= _FRAME_TOLERANCE
        for actual, expected in zip(
            (declared.x, declared.y, declared.width, declared.height),
            (derived.x, derived.y, derived.width, derived.height),
            strict=True,
        )
    )


def _positive_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise BoardPackageError(f"{label} must be a positive finite number")
    return float(value)


def _inclusive_fraction(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 0.5:
        raise BoardPackageError(f"{label} must be in 0...0.5")
    return float(value)


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BoardPackageError(f"{label} must be a positive integer")
    return value


def _nullable_positive_integer(value: object, label: str) -> int | None:
    return None if value is None else _positive_integer(value, label)


def _nullable_millimeter_range(value: object, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _exact_keys(value, {"lowerBound", "upperBound"}, label)
    lower = _positive_integer(value.get("lowerBound"), f"{label}.lowerBound")
    upper = _positive_integer(value.get("upperBound"), f"{label}.upperBound")
    if lower > upper:
        raise BoardPackageError(f"{label}.lowerBound must not exceed upperBound")


def _enum(value: object, allowed: frozenset[str], label: str) -> str:
    parsed = _non_empty_string(value, label)
    if parsed not in allowed:
        raise BoardPackageError(f"{label} must be one of {sorted(allowed)}")
    return parsed


def _https_url(value: object, label: str) -> str:
    url = _non_empty_string(value, label)
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise BoardPackageError(f"{label} must be an absolute HTTPS URL")
    return url


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise BoardPackageError(f"{label} must be identifier-shaped")
    return value


def _slug(value: object) -> str:
    if not isinstance(value, str) or not _SLUG.fullmatch(value):
        raise BoardPackageError("board package path must be a single board slug")
    return value


def _confined_path(root: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or "\\" in relative or ".." in Path(relative).parts:
        raise BoardPackageError(f"{label} must stay inside its board package")
    candidate = root / relative
    try:
        candidate.resolve(strict=False).relative_to(root)
    except ValueError as error:
        raise BoardPackageError(f"{label} must stay inside its board package") from error
    return candidate


def _reject_symlinks(root: Path) -> None:
    if root.is_symlink() or any(item.is_symlink() for item in root.rglob("*")):
        raise BoardPackageError("board package must not contain symlinks")


def _png_dimensions(path: Path) -> tuple[int, int]:
    try:
        header = path.read_bytes()[:24]
    except OSError as error:
        raise BoardPackageError("package primary image is not readable") from error
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise BoardPackageError("package primary image must be a PNG")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    if width <= 0 or height <= 0:
        raise BoardPackageError("package primary image has invalid dimensions")
    return width, height
