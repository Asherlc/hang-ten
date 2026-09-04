"""Direct, single-file hangboard packages owned by Hangboard Workbench."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace as _dataclass_replace
import fcntl
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
from typing import Any, Iterator, Mapping, Protocol
from urllib.parse import urlparse
import uuid
import zlib

from board_geometry import (
    ClosedPath,
    GeometryError,
    NormalizedFrame,
    display_path_for_shape,
    flattened_shape_bounds,
    parse_closed_path,
    shape_for_path,
    union_normalized_frames,
)


_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:[a-z0-9._-]*[a-z0-9])?$")
_SLUG = re.compile(r"^[a-z0-9]+(?:[a-z0-9-]*[a-z0-9])?$")
_ASPECT_RATIO_RELATIVE_TOLERANCE = 0.001
_ALIAS_ASPECT_RATIO_RELATIVE_TOLERANCE = 1e-9
_ALIAS_ASPECT_RATIO_ABSOLUTE_TOLERANCE = 1e-12
_PROJECTED_FRAME_EDGE_TOLERANCE = 1e-12
_BOARD_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "manufacturer",
        "name",
        "subtitle",
        "productURL",
        "aspectRatio",
        "presentations",
        "holds",
    }
)
_BOARD_OPTIONAL_FIELDS = frozenset({"dimensions", "equipmentObjects"})
_HOLD_REQUIRED_FIELDS = frozenset({"id", "name", "kind", "geometry"})
_HOLD_OPTIONAL_FIELDS = frozenset(
    {
        "sloper",
        "sizeMillimeters",
        "depthRangeMillimeters",
        "gripType",
        "fingerCapacity",
        "handCapacity",
        "features",
        "pairedHoldID",
        "equipmentObjectID",
    }
)
_HOLD_KINDS = frozenset({"jug", "edge", "pocket", "pinch", "sloper", "gaston"})
_SLOPER_TYPES = frozenset({"flat", "round"})
_MISSING_HAND_CAPACITY_POLICIES = frozenset({"legacyBilateral", "unavailable"})
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
_TREATMENT_TYPES = frozenset({"surface", "shelf", "recess"})
_RECESS_DEPTHS = frozenset({"shallow", "deep"})
_SHAPE_CONSTRAINTS = frozenset(
    {"oval", "circle", "pill", "roundedRectangle", "rectangle"}
)
_FRAME_EDGE_TOLERANCE = 0.0000005
_RECOVERY_DIRECTORY_NAME = ".workbench-recovery"
_STAGING_DIRECTORY_PREFIXES = (
    ".workbench-delete-",
    ".workbench-edit-",
    ".workbench-save-",
)


class BoardPackageError(ValueError):
    """Raised for invalid or unsafe direct board-package operations."""


class BoardSaveConflictError(BoardPackageError):
    """Raised when a hosted board save cannot be applied safely."""


class BoardNotAvailableError(BoardPackageError):
    """Raised when a valid board ID is not present in the library."""


@dataclass(frozen=True, slots=True)
class CordPoint:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class CordSize:
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class CordRect:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class DirectTwoAnchorCordRig:
    scene_size: CordSize
    source_frame: CordRect
    inner_face_frame: CordRect
    attachment_points: tuple[CordPoint, CordPoint]
    pull_point: CordPoint
    eyelet_radius: float


@dataclass(frozen=True, slots=True)
class BoardPresentation:
    id: str
    name: str
    asset_path: str
    aspect_ratio: float
    is_default: bool
    image_width: int
    image_height: int
    source_presentation_id: str | None = None
    is_inverted: bool = False
    geometry_rotation_anchor: tuple[float, float] | None = None
    cord_rig: DirectTwoAnchorCordRig | None = None
    rotation_degrees: float | None = None
    available_hold_ids: tuple[str, ...] | None = None

    @property
    def resolved_rotation_degrees(self) -> float:
        return self.rotation_degrees if self.rotation_degrees is not None else (
            180.0 if self.is_inverted else 0.0
        )


@dataclass(frozen=True, slots=True)
class BoardPackage:
    root: Path
    board: dict[str, Any]
    image_width: int
    image_height: int
    presentations: tuple[BoardPresentation, ...]

    @property
    def board_id(self) -> str:
        return self.board["id"]

    @property
    def hold_ids(self) -> tuple[str, ...]:
        return tuple(hold["id"] for hold in self.board["holds"])

    def presentation(self, presentation_id: str | None = None) -> BoardPresentation:
        selected = (
            next(
                (item for item in self.presentations if item.id == presentation_id),
                None,
            )
            if presentation_id is not None
            else next((item for item in self.presentations if item.is_default), None)
        )
        if selected is None:
            raise BoardPackageError("presentation is not available")
        return selected

    def hold_frame(self, hold_id: str) -> NormalizedFrame:
        """Derive one physical hold's interaction bounds from all of its pieces."""
        hold = next(
            (candidate for candidate in self.board["holds"] if candidate["id"] == hold_id),
            None,
        )
        if hold is None:
            raise BoardPackageError("hold is not available")
        try:
            return union_normalized_frames(
                NormalizedFrame.from_json(piece["frame"], f"hold {hold_id}.geometry")
                for piece in hold["geometry"]
            )
        except (GeometryError, KeyError, TypeError) as error:
            raise BoardPackageError(f"hold {hold_id} has invalid geometry") from error


class _EditorDocumentPackage(Protocol):
    board: dict[str, Any]
    image_width: int
    image_height: int
    presentations: tuple[BoardPresentation, ...]

    def presentation(self, presentation_id: str | None = None) -> BoardPresentation: ...


_EditorPiece = tuple[
    int,
    str | None,
    dict[str, object] | None,
    Any,
    dict[str, object] | None,
    tuple[int, ...],
    tuple[int, ...],
    int | None,
    int | float | None,
    dict[str, int | float] | None,
    int | None,
    str | None,
    str,
]

_ParsedBoardPresentation = tuple[
    str,
    str,
    str,
    float,
    bool,
    str | None,
    bool,
    tuple[str, ...] | None,
]


class _EditorPiecesByHold(dict[str, list[_EditorPiece]]):
    """Editor pieces with paths already derived from an equivalent live board."""

    def __init__(
        self,
        pieces: Mapping[
            str, list[_EditorPiece]
        ],
        current_paths: Mapping[tuple[str, int], ClosedPath],
    ) -> None:
        super().__init__(pieces)
        self.current_paths = current_paths


def discover_packages(
    library_root: Path, *, final_inventory: bool = False
) -> tuple[BoardPackage, ...]:
    """Discover completed packages using lightweight primary-image inspection."""
    root = _library_root(library_root)
    with _library_lock(root, shared=True):
        return _discover_packages_unlocked(root, final_inventory=final_inventory)


def open_package(library_root: Path, board_id: str) -> BoardPackage:
    """Open one discovered board by stable ID under a coherent library lock."""
    root = _library_root(library_root)
    board_id = _identifier(board_id, "board ID")
    with _library_lock(root, shared=True):
        package = next(
            (
                candidate
                for candidate in _discover_packages_unlocked(root)
                if candidate.board_id == board_id
            ),
            None,
        )
        if package is None:
            raise BoardNotAvailableError("board is not available")
        return load_board_package(package.root)


def load_board_package(package_root: Path) -> BoardPackage:
    """Load one completed package without accepting links or extra files."""
    return _load_board_package(package_root, inspect_png_header_only=False)


def _load_board_package(
    package_root: Path, *, inspect_png_header_only: bool
) -> BoardPackage:
    raw_root = Path(package_root)
    if raw_root.is_symlink():
        raise BoardPackageError("board package must not be a symlink")
    try:
        root = raw_root.resolve(strict=True)
    except OSError as error:
        raise BoardPackageError("board package is not accessible") from error
    if not root.is_dir():
        raise BoardPackageError("board package must be a directory")
    _reject_symlinks(root)
    if {item.name for item in root.iterdir()} != {"board.json", "assets"}:
        raise BoardPackageError(
            "board package must contain only board.json and assets/"
        )
    assets = root / "assets"
    if not assets.is_dir() or assets.is_symlink():
        raise BoardPackageError("board package assets must be a directory")
    dimensions: dict[str, tuple[int, int]] = {}
    primary = assets / "primary.png"
    if primary.is_file() and not primary.is_symlink():
        dimensions["assets/primary.png"] = (
            _png_header_dimensions(primary)
            if inspect_png_header_only
            else _png_dimensions(primary)
        )
    board = _load_json(root / "board.json", "board.json")
    presentation_values = _parse_board_presentations(board)
    expected_assets = {item[2] for item in presentation_values}
    actual_assets = {
        item.relative_to(root).as_posix()
        for item in assets.rglob("*")
        if item.is_file()
    }
    if actual_assets != expected_assets:
        raise BoardPackageError("board package assets must exactly match its presentations")
    for asset_path in sorted(expected_assets):
        if asset_path in dimensions:
            continue
        image = root / asset_path
        if not image.is_file() or image.is_symlink():
            raise BoardPackageError("package presentation image is missing")
        dimensions[asset_path] = (
            _png_header_dimensions(image)
            if inspect_png_header_only
            else _png_dimensions(image)
        )
    presentations = tuple(
        BoardPresentation(
            presentation_id,
            name,
            asset_path,
            aspect_ratio,
            is_default,
            *dimensions[asset_path],
            source_presentation_id,
            is_inverted,
            _raw_presentation_geometry_rotation_anchor(board, presentation_id),
            _raw_presentation_cord_rig(board, presentation_id),
            _raw_presentation_rotation_degrees(board, presentation_id),
            available_hold_ids,
        )
        for (
            presentation_id,
            name,
            asset_path,
            aspect_ratio,
            is_default,
            source_presentation_id,
            is_inverted,
            available_hold_ids,
        ) in presentation_values
    )
    default = next(item for item in presentations if item.is_default)
    # Discovery (header-only PNG inspection) only needs enough validation to
    # list a board safely -- it doesn't read hold geometry, so skip the full
    # geometry check there too. The specific board a caller opens or saves is
    # always reloaded through this function with inspect_png_header_only=False,
    # which still validates its geometry in full before anyone reads or writes
    # it.
    _validate_board(
        board,
        default.image_width,
        default.image_height,
        presentations=presentations,
        validate_geometry=not inspect_png_header_only,
        allow_missing_kind=True,
    )
    return BoardPackage(
        root,
        board,
        default.image_width,
        default.image_height,
        presentations,
    )


def primary_image_path(package: BoardPackage) -> Path:
    """Return the one canonical package image after confinement validation."""
    image = package.root / "assets" / "primary.png"
    if not image.is_file() or image.is_symlink():
        raise BoardPackageError("package primary image is missing")
    _png_dimensions(image)
    return image


def presentation_image_path(
    package: BoardPackage, presentation_id: str | None = None
) -> Path:
    """Return one validated presentation image confined to its package."""
    presentation = package.presentation(presentation_id)
    image = package.root / presentation.asset_path
    if not image.is_file() or image.is_symlink():
        raise BoardPackageError("package presentation image is missing")
    _png_dimensions(image)
    return image


def editor_document(
    package: _EditorDocumentPackage, presentation_id: str | None = None
) -> dict[str, object]:
    """Expose every geometry piece as an independently keyed editable region."""
    presentation = package.presentation(presentation_id)
    source_presentation_id = presentation.source_presentation_id or presentation.id
    available_hold_ids = (
        set(presentation.available_hold_ids)
        if presentation.available_hold_ids is not None
        else None
    )
    width, height = presentation.image_width, presentation.image_height
    regions: list[dict[str, object]] = []
    region_id = 1
    for hold in package.board["holds"]:
        hold_presentation_id = hold["presentationID"]
        if hold_presentation_id != source_presentation_id:
            continue
        hold_id = hold["id"]
        if available_hold_ids is not None and hold_id not in available_hold_ids:
            continue
        for piece_index, piece in enumerate(hold["geometry"]):
            key = _piece_key(hold_id, piece_index)
            try:
                path = display_path_for_shape(
                    piece["frame"],
                    piece["shape"],
                    width,
                    height,
                    label=f"hold {key}",
                )
                if presentation.resolved_rotation_degrees != 0:
                    path = _rotated_display_path(
                        path,
                        width,
                        height,
                        presentation_geometry_rotation_anchor(
                            package.board, presentation
                        )
                        or (0.5, 0.5),
                        presentation.resolved_rotation_degrees,
                        label=f"hold {key}",
                    )
            except (GeometryError, KeyError, TypeError) as error:
                raise BoardPackageError(f"hold {key} has invalid geometry") from error
            region: dict[str, object] = {
                "id": region_id,
                "key": key,
                "displayPath": path.data,
                "metadata": {
                    "holdID": hold_id,
                    "pieceIndex": piece_index,
                    "presentationID": presentation.id,
                },
                "equipmentObjectID": hold.get("equipmentObjectID", "primary"),
            }
            if "kind" in hold:
                region["type"] = hold["kind"]
            if "pairedHoldID" in hold:
                region["pairedHoldID"] = hold["pairedHoldID"]
            if "sloper" in hold:
                region["sloper"] = dict(hold["sloper"])
            if "shapeConstraint" in piece:
                region["shapeConstraint"] = _parse_shape_constraint(
                    piece["shapeConstraint"], f"hold {key}.shapeConstraint"
                )
            bendable_command_indexes = _bendable_command_indexes(piece)
            if bendable_command_indexes:
                region["bendableCommandIndexes"] = bendable_command_indexes
            smooth_anchor_indexes = _smooth_anchor_indexes(piece)
            if smooth_anchor_indexes:
                region["smoothAnchorIndexes"] = smooth_anchor_indexes
            if "fingerCapacity" in hold:
                region["fingerCapacity"] = hold["fingerCapacity"]
            if "sizeMillimeters" in hold:
                region["sizeMillimeters"] = hold["sizeMillimeters"]
            if "depthRangeMillimeters" in hold:
                region["depthRangeMillimeters"] = dict(hold["depthRangeMillimeters"])
            if "handCapacity" in hold:
                region["handCapacity"] = hold["handCapacity"]
            regions.append(region)
            region_id += 1
    return {
        "presentationID": presentation.id,
        "equipmentObjects": [
            item["id"] for item in package.board.get("equipmentObjects", [{"id": "primary"}])
        ],
        "canvas": {"width": width, "height": height},
        "regions": regions,
    }


def _inverted_display_path(
    path: ClosedPath,
    width: int,
    height: int,
    anchor: tuple[float, float],
    *,
    label: str,
) -> ClosedPath:
    """Rotate a source-owned display path 180 degrees for an inverted alias."""
    return _rotated_display_path(path, width, height, anchor, 180, label=label)


def _rotated_display_path(
    path: ClosedPath,
    width: int,
    height: int,
    anchor: tuple[float, float],
    rotation_degrees: float,
    *,
    label: str,
) -> ClosedPath:
    """Rotate a source-owned display path clockwise around its canvas anchor."""
    anchor_x, anchor_y = anchor
    pivot_x = anchor_x * width
    pivot_y = anchor_y * height
    radians = math.radians(rotation_degrees)
    cosine = math.cos(radians)
    sine = math.sin(radians)

    def rotate(x: float, y: float) -> tuple[float, float]:
        delta_x = x - pivot_x
        delta_y = y - pivot_y
        return (
            pivot_x + cosine * delta_x - sine * delta_y,
            pivot_y + sine * delta_x + cosine * delta_y,
        )

    commands: list[str] = []
    for command, values in path.commands:
        if command == "Z":
            commands.append(command)
            continue
        rotated_values: list[float] = []
        for index in range(0, len(values), 2):
            x, y = rotate(values[index], values[index + 1])
            rotated_values.extend((x, y))
        commands.append(
            " ".join((command, *(format(value, ".12g") for value in rotated_values)))
        )
    return parse_closed_path(" ".join(commands), width, height, label=label)


def presentation_geometry_rotation_anchor(
    board: Mapping[str, Any], presentation: BoardPresentation
) -> tuple[float, float] | None:
    """Return the validated alias anchor declared by the package model."""
    return presentation.geometry_rotation_anchor


def _raw_presentation_geometry_rotation_anchor(
    board: Mapping[str, Any], presentation_id: str
) -> tuple[float, float] | None:
    raw_presentations = board.get("presentations")
    if not isinstance(raw_presentations, list):
        return None
    raw_presentation = next(
        (
            value
            for value in raw_presentations
            if isinstance(value, Mapping) and value.get("id") == presentation_id
        ),
        None,
    )
    if raw_presentation is None or "geometryRotationAnchor" not in raw_presentation:
        return None
    return _normalized_point(
        raw_presentation["geometryRotationAnchor"],
        f"presentation {presentation_id}.geometryRotationAnchor",
    )


def save_editor_document(
    library_root: Path, slug: str, document: Mapping[str, Any]
) -> BoardPackage:
    """Atomically save added, removed, recategorized, or reshaped holds back
    into the package's board.json."""
    root = _library_root(library_root)
    slug = _slug(slug)
    with _library_lock(root):
        inventory = _discover_packages_unlocked(root)
        live = next(
            (package for package in inventory if package.root.name == slug), None
        )
        if live is None:
            raise BoardPackageError("board package is not available")
        live = load_board_package(live.root)
        requested_presentation_id = document.get("presentationID")
        presentation = live.presentation(
            requested_presentation_id if isinstance(requested_presentation_id, str) else None
        )
        if presentation.source_presentation_id is not None:
            raise BoardPackageError("alias presentations cannot be edited")
        width, height = presentation.image_width, presentation.image_height
        expected_equipment_objects = [
            item["id"] for item in live.board.get("equipmentObjects", [{"id": "primary"}])
        ]
        if document.get("equipmentObjects", ["primary"]) != expected_equipment_objects:
            raise BoardPackageError(
                "editor document equipment objects do not match the board package"
            )
        parsed_regions = _validate_editor_document(
            document,
            width,
            height,
            presentation.id,
            require_presentation_id=True,
        )

        pieces_by_hold: dict[
            str, list[_EditorPiece]
        ] = {}
        for (
            hold_id,
            piece_index,
            kind,
            sloper,
            path,
            shape_constraint,
            bendable_command_indexes,
            smooth_anchor_indexes,
            finger_capacity,
            size_millimeters,
            depth_range,
            hand_capacity,
            paired_hold_id,
            equipment_object_id,
        ) in parsed_regions.values():
            pieces_by_hold.setdefault(hold_id, []).append(
                (
                    piece_index,
                    kind,
                    sloper,
                    path,
                    shape_constraint,
                    bendable_command_indexes,
                    smooth_anchor_indexes,
                    finger_capacity,
                    size_millimeters,
                    depth_range,
                    hand_capacity,
                    paired_hold_id,
                    equipment_object_id,
                )
            )
        for pieces in pieces_by_hold.values():
            pieces.sort(key=lambda item: item[0])

        current_holds = {
            hold["id"]: hold
            for hold in live.board["holds"]
            if hold["presentationID"] == presentation.id
            and (
                presentation.available_hold_ids is None
                or hold["id"] in presentation.available_hold_ids
            )
        }
        # Derive current display paths before staging a candidate so unchanged
        # editor documents avoid an unnecessary package rewrite.
        current_paths = _current_display_paths(pieces_by_hold, current_holds, width, height)
        if not _editor_document_is_dirty(pieces_by_hold, current_holds, current_paths):
            return live

        candidate_parent = Path(tempfile.mkdtemp(prefix=".workbench-edit-", dir=root))
        candidate = candidate_parent / slug
        try:
            shutil.copytree(live.root, candidate)
            board_path = candidate / "board.json"
            board = _load_json(board_path, "board.json")
            board = _apply_editor_document(
                board,
                _EditorPiecesByHold(pieces_by_hold, current_paths),
                width,
                height,
                presentation_id=presentation.id,
                available_hold_ids=presentation.available_hold_ids,
            )
            _write_json(board_path, board)
            # _replace_package_locked already fully validates `candidate` (the
            # PNG included) before installing it, and returns that validated
            # package -- re-decoding the same never-modified PNG here or after
            # install would just repeat that work for no additional safety.
            return _replace_package_locked(root, slug, candidate, inventory=inventory)
        finally:
            shutil.rmtree(candidate_parent, ignore_errors=True)


def delete_presentation(
    library_root: Path, slug: str, presentation_id: str
) -> BoardPackage:
    """Atomically remove one canonical presentation and the holds it owns."""
    root = _library_root(library_root)
    slug = _slug(slug)
    with _library_lock(root):
        inventory = _discover_packages_unlocked(root)
        live = next(
            (package for package in inventory if package.root.name == slug), None
        )
        if live is None:
            raise BoardPackageError("board package is not available")
        live = load_board_package(live.root)
        board, removed_assets = _delete_presentation_from_board(
            live.board, presentation_id
        )
        candidate_parent = Path(tempfile.mkdtemp(prefix=".workbench-delete-", dir=root))
        candidate = candidate_parent / slug
        try:
            shutil.copytree(live.root, candidate)
            _write_json(candidate / "board.json", board)
            for asset_path in removed_assets:
                (candidate / asset_path).unlink()
            return _replace_package_locked(root, slug, candidate, inventory=inventory)
        finally:
            shutil.rmtree(candidate_parent, ignore_errors=True)


def _delete_presentation_from_board(
    board: Mapping[str, Any], presentation_id: str
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Build a valid board after removing one canonical presentation.

    Alias presentations are projections of their source canonical presentation,
    so aliases of the deleted source must disappear with it as well.
    """
    presentation_id = _identifier(presentation_id, "presentation ID")
    copied = json.loads(json.dumps(board))
    presentations = copied["presentations"]
    assert isinstance(presentations, list)
    selected = next(
        (item for item in presentations if item.get("id") == presentation_id),
        None,
    )
    if selected is None:
        raise BoardPackageError("presentation is not available")
    if "sourcePresentationID" in selected:
        raise BoardPackageError("only canonical presentations can be deleted")
    canonical = [item for item in presentations if "sourcePresentationID" not in item]
    if len(canonical) == 1:
        raise BoardPackageError("cannot delete the only canonical presentation")

    removed_ids = {
        item["id"]
        for item in presentations
        if item["id"] == presentation_id
        or item.get("sourcePresentationID") == presentation_id
    }
    remaining = [item for item in presentations if item["id"] not in removed_ids]
    removed_default = any(item["default"] for item in presentations if item["id"] in removed_ids)
    next_default = (
        next(item["id"] for item in remaining if "sourcePresentationID" not in item)
        if removed_default
        else next(item["id"] for item in remaining if item["default"])
    )
    for item in remaining:
        item["default"] = item["id"] == next_default
    copied["presentations"] = remaining
    if removed_default:
        copied["aspectRatio"] = next(
            item["aspectRatio"] for item in remaining if item["id"] == next_default
        )

    removed_assets = {
        item["assetPath"]
        for item in presentations
        if item["id"] in removed_ids
        and item["assetPath"] not in {remaining_item["assetPath"] for remaining_item in remaining}
    }
    copied["holds"] = [
        hold for hold in copied["holds"] if hold["presentationID"] not in removed_ids
    ]
    if not copied["holds"]:
        raise BoardPackageError("cannot delete a surface because the board needs at least one hold")
    remaining_hold_ids = {hold["id"] for hold in copied["holds"]}
    copied["holds"] = [
        hold
        for hold in copied["holds"]
        if hold.get("kind") != "gaston"
        or hold.get("pairedHoldID") in remaining_hold_ids
    ]
    if not copied["holds"]:
        raise BoardPackageError("cannot delete a surface because the board needs at least one hold")
    if "equipmentObjects" in copied:
        used_equipment_objects = {
            hold.get("equipmentObjectID", "primary") for hold in copied["holds"]
        }
        copied["equipmentObjects"] = [
            item for item in copied["equipmentObjects"]
            if item["id"] in used_equipment_objects
        ]
    return copied, tuple(sorted(removed_assets))


def _apply_editor_document(
    board: dict[str, Any],
    pieces_by_hold: Mapping[
        str, list[_EditorPiece]
    ],
    width: int,
    height: int,
    *,
    presentation_id: str | None = None,
    available_hold_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Return a board with editable regions merged into its holds."""
    copied_board = json.loads(json.dumps(board))
    available_hold_id_set = (
        set(available_hold_ids) if available_hold_ids is not None else None
    )
    existing_by_id = {
        hold["id"]: hold
        for hold in copied_board["holds"]
        if presentation_id is None
            or hold["presentationID"] == presentation_id
        if available_hold_id_set is None
            or hold["id"] in available_hold_id_set
    }
    current_paths = (
        pieces_by_hold.current_paths
        if isinstance(pieces_by_hold, _EditorPiecesByHold)
        else _current_display_paths(pieces_by_hold, existing_by_id, width, height)
    )
    order = [
        hold_id for hold_id in existing_by_id if hold_id in pieces_by_hold
    ] + [hold_id for hold_id in pieces_by_hold if hold_id not in existing_by_id]
    updated_holds: list[dict[str, Any]] = []
    for hold_id in order:
        pieces = pieces_by_hold[hold_id]
        existing = existing_by_id.get(hold_id)
        geometry: list[dict[str, Any]] = []
        for (
            piece_index,
            _kind,
            _sloper,
            path,
            shape_constraint,
            bendable_command_indexes,
            smooth_anchor_indexes,
            _finger_capacity,
            _size_millimeters,
            _depth_range,
            _hand_capacity,
            _paired_hold_id,
            _equipment_object_id,
        ) in pieces:
            existing_geometry = existing["geometry"] if existing is not None else []
            if piece_index < len(existing_geometry):
                piece = existing_geometry[piece_index]
                current_path = current_paths.get((hold_id, piece_index))
                if current_path is None or path.data != current_path.data:
                    frame, shape = shape_for_path(path, width, height)
                    piece["frame"] = frame.to_json()
                    piece["shape"] = _rounded_json(shape)
                if shape_constraint is None:
                    piece.pop("shapeConstraint", None)
                else:
                    piece["shapeConstraint"] = dict(shape_constraint)
                _apply_bendable_command_indexes(piece, bendable_command_indexes)
                _apply_smooth_anchor_indexes(piece, smooth_anchor_indexes)
                geometry.append(piece)
            else:
                frame, shape = shape_for_path(path, width, height)
                piece = {"frame": frame.to_json(), "shape": _rounded_json(shape)}
                if shape_constraint is not None:
                    piece["shapeConstraint"] = dict(shape_constraint)
                _apply_bendable_command_indexes(piece, bendable_command_indexes)
                _apply_smooth_anchor_indexes(piece, smooth_anchor_indexes)
                geometry.append(piece)
        hold_json = (
            existing
            if existing is not None
            else {"id": hold_id, "name": _default_hold_name(hold_id)}
        )
        if pieces[0][1] is None:
            hold_json.pop("kind", None)
        else:
            hold_json["kind"] = pieces[0][1]
        if pieces[0][2] is None:
            hold_json.pop("sloper", None)
        else:
            hold_json["sloper"] = dict(pieces[0][2])
        if pieces[0][7] is None:
            hold_json.pop("fingerCapacity", None)
        else:
            hold_json["fingerCapacity"] = pieces[0][7]
        if pieces[0][8] is None:
            hold_json.pop("sizeMillimeters", None)
        else:
            hold_json["sizeMillimeters"] = pieces[0][8]
            hold_json.pop("depthRangeMillimeters", None)
        if pieces[0][9] is None:
            hold_json.pop("depthRangeMillimeters", None)
        else:
            hold_json["depthRangeMillimeters"] = dict(pieces[0][9])
            hold_json.pop("sizeMillimeters", None)
        if pieces[0][10] is None:
            hold_json.pop("handCapacity", None)
        else:
            hold_json["handCapacity"] = pieces[0][10]
        if pieces[0][11] is None:
            hold_json.pop("pairedHoldID", None)
        else:
            hold_json["pairedHoldID"] = pieces[0][11]
        hold_json["equipmentObjectID"] = pieces[0][12]
        hold_json["geometry"] = geometry
        if presentation_id is not None:
            hold_json["presentationID"] = presentation_id
        updated_holds.append(hold_json)
    if presentation_id is None:
        copied_board["holds"] = updated_holds
    else:
        updated_by_id = {hold["id"]: hold for hold in updated_holds}
        merged_holds: list[dict[str, Any]] = []
        emitted: set[str] = set()
        for hold in copied_board["holds"]:
            if hold["presentationID"] != presentation_id:
                merged_holds.append(hold)
                continue
            if (
                available_hold_id_set is not None
                and hold["id"] not in available_hold_id_set
            ):
                merged_holds.append(hold)
                continue
            replacement = updated_by_id.get(hold["id"])
            if replacement is not None:
                merged_holds.append(replacement)
                emitted.add(hold["id"])
        merged_holds.extend(
            hold for hold in updated_holds if hold["id"] not in emitted
        )
        copied_board["holds"] = merged_holds
    return copied_board


def _current_display_paths(
    pieces_by_hold: Mapping[
        str, list[_EditorPiece]
    ],
    current_holds: Mapping[str, Any],
    width: int,
    height: int,
) -> dict[tuple[str, int], ClosedPath]:
    """Derive each currently-saved piece's display path exactly once, keyed
    by (holdID, pieceIndex), for both the dirty check and the update loop."""
    paths: dict[tuple[str, int], ClosedPath] = {}
    for hold_id, pieces in pieces_by_hold.items():
        hold = current_holds.get(hold_id)
        geometry = hold["geometry"] if hold is not None else []
        for (
            piece_index,
            _kind,
            _sloper,
            _path,
            _shape_constraint,
            _bendable_command_indexes,
            _smooth_anchor_indexes,
            _finger_capacity,
            _size_millimeters,
            _depth_range,
            _hand_capacity,
            _paired_hold_id,
            _equipment_object_id,
        ) in pieces:
            if piece_index < len(geometry):
                piece = geometry[piece_index]
                paths[(hold_id, piece_index)] = display_path_for_shape(
                    piece["frame"], piece["shape"], width, height,
                    label=f"hold {_piece_key(hold_id, piece_index)}",
                )
    return paths


def _editor_document_is_dirty(
    pieces_by_hold: Mapping[
        str, list[_EditorPiece]
    ],
    current_holds: Mapping[str, Any],
    current_paths: Mapping[tuple[str, int], ClosedPath],
) -> bool:
    if set(pieces_by_hold) != set(current_holds):
        return True
    for hold_id, pieces in pieces_by_hold.items():
        hold = current_holds[hold_id]
        if (hold.get("kind") != pieces[0][1]
            or hold.get("sloper") != pieces[0][2]
            or len(hold["geometry"]) != len(pieces)
            or hold.get("fingerCapacity") != pieces[0][7]
            or hold.get("sizeMillimeters") != pieces[0][8]
            or hold.get("depthRangeMillimeters") != pieces[0][9]
            or hold.get("handCapacity") != pieces[0][10]
            or hold.get("equipmentObjectID", "primary") != pieces[0][12]):
            return True
        if hold.get("pairedHoldID") != pieces[0][11]:
            return True
        for (
            piece_index,
            _kind,
            _sloper,
            path,
            shape_constraint,
            bendable_command_indexes,
            smooth_anchor_indexes,
            _finger_capacity,
            _size_millimeters,
            _depth_range,
            _hand_capacity,
            _paired_hold_id,
            _equipment_object_id,
        ) in pieces:
            current_path = current_paths.get((hold_id, piece_index))
            if current_path is None or path.data != current_path.data:
                return True
            piece = hold["geometry"][piece_index]
            current_constraint = (
                _parse_shape_constraint(
                    piece["shapeConstraint"],
                    f"hold {_piece_key(hold_id, piece_index)}.shapeConstraint",
                )
                if "shapeConstraint" in piece
                else None
            )
            if current_constraint != shape_constraint:
                return True
            if _bendable_command_indexes(piece) != list(bendable_command_indexes):
                return True
            if _smooth_anchor_indexes(piece) != list(smooth_anchor_indexes):
                return True
    return False


def _default_hold_name(hold_id: str) -> str:
    words = [word for word in re.split(r"[-_.]+", hold_id) if word]
    return " ".join(word.capitalize() for word in words) or hold_id


def replace_package(library_root: Path, slug: str, candidate_root: Path) -> None:
    """Atomically replace one completed package with rollback on failure."""
    root = _library_root(library_root)
    slug = _slug(slug)
    with _library_lock(root):
        _replace_package_locked(root, slug, candidate_root)


def _discover_packages_unlocked(
    root: Path, *, final_inventory: bool = False
) -> tuple[BoardPackage, ...]:
    packages: list[BoardPackage] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        if child.name == ".workbench.lock":
            if child.is_symlink() or not child.is_file():
                raise BoardPackageError("workbench lock must be a regular file")
            continue
        if child.name == _RECOVERY_DIRECTORY_NAME:
            _validate_recovery_directory(child)
            continue
        if child.is_symlink():
            raise BoardPackageError("board library direct children must not be symlinks")
        if not child.is_dir():
            raise BoardPackageError("board library must contain only direct child directories")
        if child.name.startswith(_STAGING_DIRECTORY_PREFIXES):
            continue
        _slug(child.name)
        names = {item.name for item in child.iterdir()}
        if "board.json" in names:
            packages.append(
                _load_board_package(child, inspect_png_header_only=True)
            )
            continue
        if _is_primary_only_draft(child):
            if final_inventory:
                raise BoardPackageError(
                    f"{child.name} must contain board.json in the final inventory"
                )
            continue
        raise BoardPackageError(
            f"{child.name} must be a completed package or exact primary-only draft"
        )

    identifiers: set[str] = set()
    for package in packages:
        if package.board_id in identifiers:
            raise BoardPackageError(f"duplicate board ID: {package.board_id}")
        identifiers.add(package.board_id)
    packages.sort(
        key=lambda package: (
            package.board["manufacturer"].lower(),
            package.board["manufacturer"],
            package.board["name"].lower(),
            package.board["name"],
            package.board_id.lower(),
            package.board_id,
        )
    )
    return tuple(packages)


def _is_primary_only_draft(root: Path) -> bool:
    if {item.name for item in root.iterdir()} != {"assets"}:
        return False
    assets = root / "assets"
    if assets.is_symlink() or not assets.is_dir():
        raise BoardPackageError(f"{root.name} draft assets must not be a symlink")
    if {item.name for item in assets.iterdir()} != {"primary.png"}:
        return False
    image = assets / "primary.png"
    if image.is_symlink() or not image.is_file():
        raise BoardPackageError(f"{root.name} draft primary image must be regular")
    _png_header_dimensions(image)
    return True


def _replace_package_locked(
    root: Path,
    slug: str,
    candidate_root: Path,
    *,
    inventory: tuple[BoardPackage, ...] | None = None,
) -> BoardPackage:
    candidate = load_board_package(candidate_root)
    packages = inventory if inventory is not None else _discover_packages_unlocked(root)
    previous = next((package for package in packages if package.root.name == slug), None)
    if previous is not None and previous.board_id != candidate.board_id:
        raise BoardPackageError("replacement package must keep the existing board ID")
    if any(
        package.root.name != slug and package.board_id == candidate.board_id
        for package in packages
    ):
        raise BoardPackageError("duplicate board ID")

    stage = Path(tempfile.mkdtemp(prefix=".workbench-save-", dir=root))
    staged_package = stage / slug
    try:
        shutil.copytree(candidate.root, staged_package)
        # `staged_package` is a byte-for-byte copy of `candidate_root`, which
        # was just fully validated above (PNG included); re-decoding it here
        # would only repeat that work, not catch anything new.
        _replace_transaction(root, slug, staged_package)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return _dataclass_replace(candidate, root=root / slug)


def _replace_transaction(root: Path, slug: str, staged_package: Path) -> None:
    live_package = root / slug
    recovery: Path | None = None
    backup: Path | None = None
    moved_live = False
    installed = False
    try:
        if live_package.exists():
            if live_package.is_symlink() or not live_package.is_dir():
                raise BoardPackageError("existing board package is unsafe")
            recovery = _prepare_recovery_directory(root)
            backup = recovery / f"{slug}-previous-{uuid.uuid4().hex}"
            os.replace(live_package, backup)
            moved_live = True
        os.replace(staged_package, live_package)
        installed = True
    except BoardPackageError:
        raise
    except OSError as error:
        try:
            if installed and live_package.exists():
                shutil.rmtree(live_package)
            if moved_live and backup is not None and backup.exists():
                os.replace(backup, live_package)
        except OSError as restore_error:
            raise BoardPackageError(
                "could not restore the previous board package"
            ) from restore_error
        _remove_empty_recovery_directory(recovery)
        raise BoardPackageError("could not save board package") from error
    # Installing the staged package is the commit point. A failed best-effort
    # cleanup must not report rollback semantics or hide the committed package;
    # the internal backup remains recoverable outside direct package discovery.
    if moved_live and backup is not None:
        try:
            shutil.rmtree(backup)
        except OSError:
            pass
    _remove_empty_recovery_directory(recovery)


def _prepare_recovery_directory(root: Path) -> Path:
    recovery = root / _RECOVERY_DIRECTORY_NAME
    try:
        recovery.mkdir(mode=0o700)
    except FileExistsError:
        pass
    except OSError as error:
        raise BoardPackageError("workbench recovery directory is not accessible") from error
    _validate_recovery_directory(recovery)
    return recovery


def _validate_recovery_directory(recovery: Path) -> None:
    try:
        mode = recovery.lstat().st_mode
    except OSError as error:
        raise BoardPackageError("workbench recovery directory is not accessible") from error
    if not stat.S_ISDIR(mode):
        raise BoardPackageError("workbench recovery path must be a directory")


def _remove_empty_recovery_directory(recovery: Path | None) -> None:
    if recovery is None:
        return
    try:
        recovery.rmdir()
    except OSError:
        pass


def _cord_point(value: object, label: str) -> CordPoint:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _exact_keys(value, {"x", "y"}, label)
    return CordPoint(
        _finite_number(value["x"], f"{label}.x"),
        _finite_number(value["y"], f"{label}.y"),
    )


def _cord_size(value: object, label: str) -> CordSize:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _exact_keys(value, {"width", "height"}, label)
    return CordSize(
        _positive_number(value["width"], f"{label}.width"),
        _positive_number(value["height"], f"{label}.height"),
    )


def _cord_rect(value: object, label: str) -> CordRect:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _exact_keys(value, {"x", "y", "width", "height"}, label)
    return CordRect(
        _finite_number(value["x"], f"{label}.x"),
        _finite_number(value["y"], f"{label}.y"),
        _positive_number(value["width"], f"{label}.width"),
        _positive_number(value["height"], f"{label}.height"),
    )


def _direct_two_anchor_cord_rig(
    value: object, label: str
) -> DirectTwoAnchorCordRig:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _exact_keys(
        value,
        {
            "type",
            "sceneSize",
            "sourceFrame",
            "innerFaceFrame",
            "attachmentPoints",
            "pullPoint",
            "eyeletRadius",
        },
        label,
    )
    if value["type"] != "directTwoAnchor":
        raise BoardPackageError(f"{label}.type is unsupported")
    raw_attachment_points = value["attachmentPoints"]
    if not isinstance(raw_attachment_points, list) or len(raw_attachment_points) != 2:
        raise BoardPackageError(
            f"{label}.attachmentPoints must contain exactly two points"
        )
    attachment_points = tuple(
        _cord_point(point, f"{label}.attachmentPoints[{index}]")
        for index, point in enumerate(raw_attachment_points)
    )
    if attachment_points[0] == attachment_points[1]:
        raise BoardPackageError(f"{label}.attachmentPoints must be distinct")
    scene_size = _cord_size(value["sceneSize"], f"{label}.sceneSize")
    source_frame = _cord_rect(value["sourceFrame"], f"{label}.sourceFrame")
    pull_point = _cord_point(value["pullPoint"], f"{label}.pullPoint")
    scene_pull_x = source_frame.x + pull_point.x
    scene_pull_y = source_frame.y + pull_point.y
    if not (
        0 <= scene_pull_x <= scene_size.width
        and 0 <= scene_pull_y <= scene_size.height
    ):
        raise BoardPackageError(f"{label}.pullPoint must be inside sceneSize")
    return DirectTwoAnchorCordRig(
        scene_size=scene_size,
        source_frame=source_frame,
        inner_face_frame=_cord_rect(
            value["innerFaceFrame"], f"{label}.innerFaceFrame"
        ),
        attachment_points=(attachment_points[0], attachment_points[1]),
        pull_point=pull_point,
        eyelet_radius=_positive_number(
            value["eyeletRadius"], f"{label}.eyeletRadius"
        ),
    )


def _raw_presentation_cord_rig(
    board: Mapping[str, Any], presentation_id: str
) -> DirectTwoAnchorCordRig | None:
    raw_presentations = board.get("presentations")
    if not isinstance(raw_presentations, list):
        return None
    for index, value in enumerate(raw_presentations):
        if isinstance(value, Mapping) and value.get("id") == presentation_id:
            return (
                _direct_two_anchor_cord_rig(
                    value["cordRig"],
                    f"board.json.presentations[{index}].cordRig",
                )
                if "cordRig" in value
                else None
            )
    return None


def _raw_presentation_rotation_degrees(
    board: Mapping[str, Any], presentation_id: str
) -> float | None:
    raw_presentations = board.get("presentations")
    if not isinstance(raw_presentations, list):
        return None
    for index, value in enumerate(raw_presentations):
        if isinstance(value, Mapping) and value.get("id") == presentation_id:
            if "rotationDegrees" not in value:
                return None
            degrees = _finite_number(
                value["rotationDegrees"],
                f"board.json.presentations[{index}].rotationDegrees",
            )
            if not 0 <= degrees < 360:
                raise BoardPackageError(
                    f"board.json.presentations[{index}].rotationDegrees must be normalized to [0, 360)"
                )
            return degrees
    return None


def _parse_board_presentations(
    board: Mapping[str, Any],
) -> tuple[_ParsedBoardPresentation, ...]:
    _required_and_allowed_keys(
        board,
        _BOARD_REQUIRED_FIELDS,
        _BOARD_REQUIRED_FIELDS | _BOARD_OPTIONAL_FIELDS,
        "board.json",
    )
    raw_presentations = board.get("presentations")
    if not isinstance(raw_presentations, list) or not raw_presentations:
        raise BoardPackageError("board.json.presentations must be a non-empty array")
    presentations: list[_ParsedBoardPresentation] = []
    geometry_rotation_anchors: dict[str, tuple[float, float] | None] = {}
    cord_rigs: dict[str, DirectTwoAnchorCordRig | None] = {}
    rotation_degrees_by_id: dict[str, float | None] = {}
    identifiers: set[str] = set()
    defaults = 0
    for index, value in enumerate(raw_presentations):
        label = f"board.json.presentations[{index}]"
        if not isinstance(value, Mapping):
            raise BoardPackageError(f"{label} must be an object")
        _required_and_allowed_keys(
            value,
            {
                "id", "name", "assetPath", "aspectRatio", "default"
            },
            {
                "id", "name", "assetPath", "aspectRatio", "default",
                "sourcePresentationID", "isInverted", "geometryRotationAnchor",
                "rotationDegrees", "cordRig", "availableHoldIDs",
            },
            label,
        )
        presentation_id = _identifier(value.get("id"), f"{label}.id")
        if presentation_id in identifiers:
            raise BoardPackageError("duplicate presentation ID")
        identifiers.add(presentation_id)
        name = _non_empty_string(value.get("name"), f"{label}.name")
        asset_path = _presentation_asset_path(value.get("assetPath"), f"{label}.assetPath")
        aspect_ratio = _positive_number(value.get("aspectRatio"), f"{label}.aspectRatio")
        is_default = value.get("default")
        if not isinstance(is_default, bool):
            raise BoardPackageError(f"{label}.default must be a boolean")
        defaults += int(is_default)
        source_presentation_id = (
            _identifier(value["sourcePresentationID"], f"{label}.sourcePresentationID")
            if "sourcePresentationID" in value
            else None
        )
        available_hold_ids: tuple[str, ...] | None = None
        if "availableHoldIDs" in value:
            raw_available_hold_ids = value["availableHoldIDs"]
            if not isinstance(raw_available_hold_ids, list) or not raw_available_hold_ids:
                raise BoardPackageError(
                    f"{label}.availableHoldIDs must be a non-empty array"
                )
            available_hold_ids = tuple(
                _identifier(item, f"{label}.availableHoldIDs[{item_index}]")
                for item_index, item in enumerate(raw_available_hold_ids)
            )
            if len(set(available_hold_ids)) != len(available_hold_ids):
                raise BoardPackageError(f"{label}.availableHoldIDs must be unique")
        is_inverted = value.get("isInverted", False)
        if not isinstance(is_inverted, bool):
            raise BoardPackageError(f"{label}.isInverted must be a boolean")
        if "isInverted" in value and "rotationDegrees" in value:
            raise BoardPackageError(
                f"{label} must not declare both isInverted and rotationDegrees"
            )
        rotation_degrees = (
            _finite_number(value["rotationDegrees"], f"{label}.rotationDegrees")
            if "rotationDegrees" in value
            else None
        )
        if rotation_degrees is not None and not 0 <= rotation_degrees < 360:
            raise BoardPackageError(
                f"{label}.rotationDegrees must be normalized to [0, 360)"
            )
        rotation_degrees_by_id[presentation_id] = rotation_degrees
        geometry_rotation_anchor = (
            _normalized_point(
                value["geometryRotationAnchor"],
                f"{label}.geometryRotationAnchor",
            )
            if "geometryRotationAnchor" in value
            else None
        )
        geometry_rotation_anchors[presentation_id] = geometry_rotation_anchor
        cord_rigs[presentation_id] = (
            _direct_two_anchor_cord_rig(value["cordRig"], f"{label}.cordRig")
            if "cordRig" in value
            else None
        )
        presentations.append(
            (
                presentation_id,
                name,
                asset_path,
                aspect_ratio,
                is_default,
                source_presentation_id,
                is_inverted,
                available_hold_ids,
            )
        )
    if defaults != 1:
        raise BoardPackageError("board.json.presentations must have exactly one default")
    presentations_by_id = {item[0]: item for item in presentations}
    for (
        presentation_id,
        _,
        _,
        aspect_ratio,
        _,
        source_presentation_id,
        is_inverted,
        _available_hold_ids,
    ) in presentations:
        geometry_rotation_anchor = geometry_rotation_anchors[presentation_id]
        cord_rig = cord_rigs[presentation_id]
        rotation_degrees = rotation_degrees_by_id[presentation_id]
        resolved_rotation_degrees = (
            rotation_degrees if rotation_degrees is not None else (180 if is_inverted else 0)
        )
        if cord_rig is not None:
            if source_presentation_id is not None or resolved_rotation_degrees != 0:
                raise BoardPackageError(
                    f"presentation {presentation_id}.cordRig must be owned by a "
                    "canonical non-inverted presentation"
                )
            scene_aspect_ratio = cord_rig.scene_size.width / cord_rig.scene_size.height
            if (
                not math.isfinite(scene_aspect_ratio)
                or scene_aspect_ratio <= 0
                or abs(aspect_ratio - scene_aspect_ratio) / scene_aspect_ratio
                > _ASPECT_RATIO_RELATIVE_TOLERANCE
            ):
                raise BoardPackageError(
                    f"presentation {presentation_id}.aspectRatio must match "
                    "cordRig.sceneSize within 0.1%"
                )
        if rotation_degrees is not None and source_presentation_id is None:
            raise BoardPackageError(
                f"presentation {presentation_id}.rotationDegrees requires sourcePresentationID"
            )
        if geometry_rotation_anchor is not None:
            if source_presentation_id is None:
                raise BoardPackageError(
                    f"presentation {presentation_id}.geometryRotationAnchor requires sourcePresentationID"
                )
            if resolved_rotation_degrees == 0:
                raise BoardPackageError(
                    f"presentation {presentation_id}.geometryRotationAnchor requires isInverted true or nonzero rotationDegrees"
                )
        if source_presentation_id is not None and (
            source_presentation_id == presentation_id
            or source_presentation_id not in presentations_by_id
            or presentations_by_id[source_presentation_id][5] is not None
        ):
            raise BoardPackageError(
                f"presentation {presentation_id} must reference another declared presentation and a canonical presentation"
            )
        if source_presentation_id is not None and not math.isclose(
            aspect_ratio,
            presentations_by_id[source_presentation_id][3],
            rel_tol=_ALIAS_ASPECT_RATIO_RELATIVE_TOLERANCE,
            abs_tol=_ALIAS_ASPECT_RATIO_ABSOLUTE_TOLERANCE,
        ):
            raise BoardPackageError(
                f"presentation {presentation_id}.aspectRatio must match source presentation aspectRatio"
            )
    return tuple(presentations)


def _validate_board(
    board: Mapping[str, Any],
    width: int,
    height: int,
    *,
    presentations: tuple[BoardPresentation, ...] | None = None,
    validate_geometry: bool = True,
    allow_missing_kind: bool = False,
) -> None:
    parsed_presentations = _parse_board_presentations(board)
    equipment_object_ids = _validate_equipment_objects(board)
    _identifier(board.get("id"), "board.json.id")
    for field in ("manufacturer", "name", "subtitle"):
        _non_empty_string(board.get(field), f"board.json.{field}")
    if "dimensions" in board:
        _non_empty_string(board["dimensions"], "board.json.dimensions")
    _https_url(board.get("productURL"), "board.json.productURL")
    aspect_ratio = _positive_number(
        board.get("aspectRatio"), "board.json.aspectRatio"
    )
    default_presentation = next(item for item in parsed_presentations if item[4])
    default_canonical_id = default_presentation[5] or default_presentation[0]
    default_cord_rig = _raw_presentation_cord_rig(board, default_canonical_id)
    expected_board_aspect_ratio = (
        default_presentation[3] if default_cord_rig is not None else width / height
    )
    relative_error = (
        abs(aspect_ratio - expected_board_aspect_ratio) / expected_board_aspect_ratio
    )
    if relative_error > _ASPECT_RATIO_RELATIVE_TOLERANCE:
        raise BoardPackageError(
            "board.json.aspectRatio must match the primary image width/height within 0.1%"
        )
    if presentations is not None:
        presentations_by_id = {item.id: item for item in presentations}
        for presentation in presentations:
            image_aspect_ratio = presentation.image_width / presentation.image_height
            canonical = (
                presentations_by_id[presentation.source_presentation_id]
                if presentation.source_presentation_id is not None
                else presentation
            )
            expected_image_aspect_ratio = presentation.aspect_ratio
            aspect_source = f"presentation {presentation.id}.aspectRatio"
            if canonical.cord_rig is not None:
                expected_image_aspect_ratio = (
                    canonical.cord_rig.inner_face_frame.width
                    / canonical.cord_rig.inner_face_frame.height
                )
                aspect_source = (
                    f"presentation {canonical.id}.cordRig.innerFaceFrame aspect ratio"
                )
            relative_error = (
                abs(expected_image_aspect_ratio - image_aspect_ratio)
                / image_aspect_ratio
            )
            if relative_error > _ASPECT_RATIO_RELATIVE_TOLERANCE:
                raise BoardPackageError(
                    f"{aspect_source} must match its image width/height within 0.1%"
                )
    holds = board.get("holds")
    if not isinstance(holds, list) or not holds:
        raise BoardPackageError("board.json.holds must be a non-empty array")
    identifiers: set[str] = set()
    owned_equipment_object_ids: set[str] = set()
    presentation_ids = {item[0] for item in parsed_presentations}
    canonical_presentation_ids = {
        item[0] for item in parsed_presentations if item[5] is None
    }
    dimensions_by_id = {
        item.id: (item.image_width, item.image_height)
        for item in presentations or ()
    }
    for index, hold in enumerate(holds):
        label = f"board.json.holds[{index}]"
        hold_presentation_id = _identifier(
            hold.get("presentationID") if isinstance(hold, Mapping) else None,
            f"{label}.presentationID",
        )
        if hold_presentation_id not in presentation_ids:
            raise BoardPackageError(f"{label}.presentationID is unknown")
        if hold_presentation_id not in canonical_presentation_ids:
            raise BoardPackageError(
                f"{label}.presentationID must be owned by a canonical presentation"
            )
        hold_width, hold_height = dimensions_by_id.get(hold_presentation_id, (width, height))
        equipment_object_id = _identifier(
            hold.get("equipmentObjectID", "primary") if isinstance(hold, Mapping) else None,
            f"{label}.equipmentObjectID",
        )
        if equipment_object_id not in equipment_object_ids:
            raise BoardPackageError(
                f"{label} references unknown equipment object {equipment_object_id}"
            )
        owned_equipment_object_ids.add(equipment_object_id)
        hold_id = _validate_hold(
            hold,
            hold_width,
            hold_height,
            label,
            requires_presentation_id=True,
            validate_geometry=validate_geometry,
            allow_missing_kind=allow_missing_kind,
        )
        if hold_id in identifiers:
            raise BoardPackageError("duplicate hold ID")
        identifiers.add(hold_id)
    _validate_available_hold_ids(parsed_presentations, holds)
    _validate_equipment_object_ownership(equipment_object_ids, owned_equipment_object_ids)
    _validate_inverted_alias_projection(board, parsed_presentations, holds)
    _validate_gaston_pairs(holds)


def validate_catalog_board(
    board: Mapping[str, Any], *, allow_missing_kind: bool = False
) -> None:
    """Validate board metadata that does not depend on decoding its primary image."""
    parsed_presentations = _parse_board_presentations(board)
    equipment_object_ids = _validate_equipment_objects(board)
    _identifier(board.get("id"), "board.json.id")
    for field in ("manufacturer", "name", "subtitle"):
        _non_empty_string(board.get(field), f"board.json.{field}")
    if "dimensions" in board:
        _non_empty_string(board["dimensions"], "board.json.dimensions")
    _https_url(board.get("productURL"), "board.json.productURL")
    _positive_number(board.get("aspectRatio"), "board.json.aspectRatio")
    holds = board.get("holds")
    if not isinstance(holds, list) or not holds:
        raise BoardPackageError("board.json.holds must be a non-empty array")
    identifiers: set[str] = set()
    owned_equipment_object_ids: set[str] = set()
    presentation_ids = {item[0] for item in parsed_presentations}
    canonical_presentation_ids = {
        item[0] for item in parsed_presentations if item[5] is None
    }
    for index, hold in enumerate(holds):
        label = f"board.json.holds[{index}]"
        hold_presentation_id = _identifier(
            hold.get("presentationID") if isinstance(hold, Mapping) else None,
            f"{label}.presentationID",
        )
        if hold_presentation_id not in presentation_ids:
            raise BoardPackageError(f"{label}.presentationID is unknown")
        if hold_presentation_id not in canonical_presentation_ids:
            raise BoardPackageError(
                f"{label}.presentationID must be owned by a canonical presentation"
            )
        equipment_object_id = _identifier(
            hold.get("equipmentObjectID", "primary") if isinstance(hold, Mapping) else None,
            f"{label}.equipmentObjectID",
        )
        if equipment_object_id not in equipment_object_ids:
            raise BoardPackageError(
                f"{label} references unknown equipment object {equipment_object_id}"
            )
        owned_equipment_object_ids.add(equipment_object_id)
        hold_id = _validate_hold(
            hold,
            1,
            1,
            label,
            requires_presentation_id=True,
            validate_geometry=False,
            allow_missing_kind=allow_missing_kind,
        )
        if hold_id in identifiers:
            raise BoardPackageError("duplicate hold ID")
        identifiers.add(hold_id)
    _validate_available_hold_ids(parsed_presentations, holds)
    _validate_equipment_object_ownership(equipment_object_ids, owned_equipment_object_ids)
    _validate_inverted_alias_projection(board, parsed_presentations, holds)
    _validate_gaston_pairs(holds)


def _validate_available_hold_ids(
    presentations: tuple[_ParsedBoardPresentation, ...],
    holds: list[Any],
) -> None:
    holds_by_id = {
        hold["id"]: hold
        for hold in holds
        if isinstance(hold, Mapping) and isinstance(hold.get("id"), str)
    }
    for presentation in presentations:
        presentation_id = presentation[0]
        canonical_presentation_id = presentation[5] or presentation_id
        available_hold_ids = presentation[7]
        if available_hold_ids is None:
            continue
        for hold_id in available_hold_ids:
            hold = holds_by_id.get(hold_id)
            if hold is None:
                raise BoardPackageError(
                    f"presentation {presentation_id}.availableHoldIDs references "
                    f"unknown hold {hold_id}"
                )
            if hold.get("presentationID") != canonical_presentation_id:
                raise BoardPackageError(
                    f"presentation {presentation_id}.availableHoldIDs hold {hold_id} "
                    f"must belong to canonical presentation {canonical_presentation_id}"
                )


def _validate_inverted_alias_projection(
    board: Mapping[str, Any],
    presentations: tuple[_ParsedBoardPresentation, ...],
    holds: list[Any],
) -> None:
    for presentation in presentations:
        presentation_id = presentation[0]
        source_presentation_id = presentation[5]
        explicit_rotation = _raw_presentation_rotation_degrees(
            board, presentation_id
        )
        rotation_degrees = (
            explicit_rotation
            if explicit_rotation is not None
            else (180.0 if presentation[6] else 0.0)
        )
        if source_presentation_id is None or rotation_degrees == 0:
            continue
        anchor_x, anchor_y = (
            _raw_presentation_geometry_rotation_anchor(board, presentation_id)
            or (0.5, 0.5)
        )
        cord_rig = _raw_presentation_cord_rig(board, source_presentation_id)
        available_hold_ids = (
            set(presentation[7]) if presentation[7] is not None else None
        )
        for hold in holds:
            if not isinstance(hold, Mapping) or hold.get("presentationID") != source_presentation_id:
                continue
            if available_hold_ids is not None and hold.get("id") not in available_hold_ids:
                continue
            geometry = hold.get("geometry")
            if not isinstance(geometry, list):
                continue
            for piece in geometry:
                if not isinstance(piece, Mapping) or not isinstance(piece.get("frame"), Mapping):
                    continue
                try:
                    frame = NormalizedFrame.from_json(
                        piece["frame"],
                        f"hold {hold.get('id', 'unknown')}.geometry",
                    )
                except GeometryError as error:
                    raise BoardPackageError(str(error)) from error
                if cord_rig is not None:
                    if not _rigged_alias_frame_is_inside_canvas(
                        frame, cord_rig, (anchor_x, anchor_y), rotation_degrees
                    ):
                        raise BoardPackageError(
                            f"presentation {presentation_id} projects source hold geometry outside the normalized canvas"
                        )
                    continue
                corners = (
                    (frame.x, frame.y),
                    (frame.x + frame.width, frame.y),
                    (frame.x, frame.y + frame.height),
                    (frame.x + frame.width, frame.y + frame.height),
                )
                if any(
                    projected_x < -_PROJECTED_FRAME_EDGE_TOLERANCE
                    or projected_y < -_PROJECTED_FRAME_EDGE_TOLERANCE
                    or projected_x > 1 + _PROJECTED_FRAME_EDGE_TOLERANCE
                    or projected_y > 1 + _PROJECTED_FRAME_EDGE_TOLERANCE
                    for projected_x, projected_y in (
                        _rotate_canvas_point(
                            x,
                            y,
                            anchor_x,
                            anchor_y,
                            rotation_degrees,
                        )
                        for x, y in corners
                    )
                ):
                    raise BoardPackageError(
                        f"presentation {presentation_id} projects source hold geometry outside the normalized canvas"
                    )


def _rigged_alias_frame_is_inside_canvas(
    frame: NormalizedFrame,
    rig: DirectTwoAnchorCordRig,
    anchor: tuple[float, float],
    rotation_degrees: float,
) -> bool:
    face_min_x = rig.source_frame.x + rig.inner_face_frame.x
    face_min_y = rig.source_frame.y + rig.inner_face_frame.y
    pivot_x = anchor[0] * rig.scene_size.width
    pivot_y = anchor[1] * rig.scene_size.height
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
        projected_x, projected_y = _rotate_canvas_point(
            face_x,
            face_y,
            pivot_x,
            pivot_y,
            rotation_degrees,
        )
        if (
            projected_x < -tolerance
            or projected_y < -tolerance
            or projected_x > rig.scene_size.width + tolerance
            or projected_y > rig.scene_size.height + tolerance
        ):
            return False
    return True


def _rotate_canvas_point(
    x: float,
    y: float,
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


def _validate_equipment_objects(board: Mapping[str, Any]) -> set[str]:
    raw_objects = board.get("equipmentObjects", [{"id": "primary"}])
    if not isinstance(raw_objects, list) or not raw_objects:
        raise BoardPackageError("board.json.equipmentObjects must be a non-empty array")
    object_ids: set[str] = set()
    for index, value in enumerate(raw_objects):
        label = f"board.json.equipmentObjects[{index}]"
        if not isinstance(value, Mapping):
            raise BoardPackageError(f"{label} must be an object")
        _required_and_allowed_keys(
            value,
            {"id"},
            {"id", "missingHandCapacityPolicy"},
            label,
        )
        object_id = _identifier(value.get("id"), f"{label}.id")
        if "missingHandCapacityPolicy" in value:
            _enum(
                value["missingHandCapacityPolicy"],
                _MISSING_HAND_CAPACITY_POLICIES,
                f"{label}.missingHandCapacityPolicy",
            )
        if object_id in object_ids:
            raise BoardPackageError(f"duplicate equipment object ID {object_id}")
        object_ids.add(object_id)
    return object_ids


def _validate_equipment_object_ownership(
    equipment_object_ids: set[str], owned_equipment_object_ids: set[str]
) -> None:
    for object_id in equipment_object_ids:
        if object_id not in owned_equipment_object_ids:
            raise BoardPackageError(
                f"equipment object {object_id} must own at least one hold"
            )


def _validate_hold(
    hold: object,
    width: int,
    height: int,
    label: str,
    *,
    requires_presentation_id: bool = False,
    validate_geometry: bool = True,
    allow_missing_kind: bool = False,
) -> str:
    if not isinstance(hold, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _required_and_allowed_keys(
        hold,
        _HOLD_REQUIRED_FIELDS - ({"kind"} if allow_missing_kind else set()),
        _HOLD_REQUIRED_FIELDS
        | _HOLD_OPTIONAL_FIELDS
        | ({"presentationID"} if requires_presentation_id else set()),
        label,
    )
    hold_id = _identifier(hold.get("id"), f"{label}.id")
    _non_empty_string(hold.get("name"), f"{label}.name")
    kind = (
        _enum(hold["kind"], _HOLD_KINDS, f"{label}.kind")
        if "kind" in hold
        else None
    )
    if kind == "gaston":
        _identifier(hold.get("pairedHoldID"), f"{label}.pairedHoldID")
    elif "pairedHoldID" in hold:
        raise BoardPackageError(f"{label}.pairedHoldID is only allowed for gaston holds")
    if "sloper" in hold:
        if kind != "sloper":
            raise BoardPackageError(
                f"{label}.sloper is only allowed for sloper holds"
            )
        _parse_sloper_metadata(hold["sloper"], f"{label}.sloper")
    geometry = hold.get("geometry")
    if not isinstance(geometry, list) or not geometry:
        raise BoardPackageError(f"{label}.geometry must be non-empty")
    for piece_index, piece in enumerate(geometry):
        _validate_piece(
            piece,
            width,
            height,
            f"{label}.geometry[{piece_index}]",
            validate_geometry=validate_geometry,
        )
    if "sizeMillimeters" in hold and "depthRangeMillimeters" in hold:
        raise BoardPackageError(
            f"{label} must not specify both a size and depth range"
        )
    if "sizeMillimeters" in hold:
        _positive_number(hold["sizeMillimeters"], f"{label}.sizeMillimeters")
    if "depthRangeMillimeters" in hold:
        _millimeter_range(
            hold["depthRangeMillimeters"], f"{label}.depthRangeMillimeters"
        )
    if "gripType" in hold:
        _enum(hold["gripType"], _GRIP_TYPES, f"{label}.gripType")
    if "fingerCapacity" in hold:
        capacity = hold["fingerCapacity"]
        if (
            isinstance(capacity, bool)
            or not isinstance(capacity, int)
            or capacity not in range(1, 5)
        ):
            raise BoardPackageError(f"{label}.fingerCapacity must be in 1...4")
    if "handCapacity" in hold:
        capacity = hold["handCapacity"]
        if (
            isinstance(capacity, bool)
            or not isinstance(capacity, int)
            or capacity not in range(1, 3)
        ):
            raise BoardPackageError(f"{label}.handCapacity must be in 1...2")
    if "features" in hold:
        features = hold["features"]
        if not isinstance(features, list):
            raise BoardPackageError(f"{label}.features must be an array")
        parsed = [
            _enum(feature, _HOLD_FEATURES, f"{label}.features[{feature_index}]")
            for feature_index, feature in enumerate(features)
        ]
        if len(parsed) != len(set(parsed)):
            raise BoardPackageError(f"{label}.features must be unique")
    return hold_id


def _validate_gaston_pairs(holds: list[object]) -> None:
    holds_by_id = {
        hold["id"]: hold
        for hold in holds
        if isinstance(hold, Mapping) and isinstance(hold.get("id"), str)
    }
    for hold in holds_by_id.values():
        if hold.get("kind") != "gaston":
            continue
        hold_id = hold["id"]
        paired_hold_id = hold["pairedHoldID"]
        paired_hold = holds_by_id.get(paired_hold_id)
        if paired_hold is None or paired_hold_id == hold_id:
            raise BoardPackageError(
                f"gaston hold {hold_id} must pair with a distinct existing hold"
            )
        if (
            paired_hold.get("kind") != "gaston"
            or paired_hold.get("pairedHoldID") != hold_id
        ):
            raise BoardPackageError(
                f"gaston hold {hold_id} must have a reciprocal gaston pair"
            )


def _validate_piece(
    piece: object, width: int, height: int, label: str, *, validate_geometry: bool = True
) -> None:
    if not isinstance(piece, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _required_and_allowed_keys(
        piece,
        {"frame", "shape"},
        {"frame", "shape", "treatment", "shapeConstraint"},
        label,
    )
    try:
        NormalizedFrame.from_json(piece["frame"], f"{label}.frame")
        if validate_geometry:
            display_path_for_shape(
                piece["frame"], piece["shape"], width, height, label=label
            )
    except (GeometryError, KeyError, TypeError) as error:
        raise BoardPackageError(str(error)) from error
    if not _shape_fills_declared_frame(piece["shape"]):
        raise BoardPackageError(f"{label}.frame must match its derived shape bounds")
    if "treatment" in piece:
        _validate_treatment(piece["treatment"], f"{label}.treatment")
    if "shapeConstraint" in piece:
        _parse_shape_constraint(piece["shapeConstraint"], f"{label}.shapeConstraint")


def _shape_fills_declared_frame(shape: object) -> bool:
    if not isinstance(shape, Mapping) or shape.get("type") == "roundedRect":
        return True
    if shape.get("type") != "path" or not isinstance(shape.get("commands"), list):
        return False
    for command in shape["commands"]:
        if not isinstance(command, Mapping):
            return False
    if not shape["commands"]:
        return False
    # Bounds of the rendered curve, not of its (routinely wider) control
    # points, must stay within and reach every edge of the declared frame.
    try:
        min_x, max_x, min_y, max_y = flattened_shape_bounds(shape["commands"])
        return (
            abs(min_x) <= _FRAME_EDGE_TOLERANCE
            and abs(min_y) <= _FRAME_EDGE_TOLERANCE
            and abs(max_x - 1) <= _FRAME_EDGE_TOLERANCE
            and abs(max_y - 1) <= _FRAME_EDGE_TOLERANCE
        )
    except (IndexError, KeyError, TypeError, ValueError):
        return False


def _validate_treatment(value: object, label: str) -> None:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    treatment_type = _enum(value.get("type"), _TREATMENT_TYPES, f"{label}.type")
    if treatment_type == "surface":
        _exact_keys(value, {"type"}, label)
    elif treatment_type == "shelf":
        _exact_keys(value, {"type", "rimInsetFraction"}, label)
        _inclusive_fraction(value["rimInsetFraction"], f"{label}.rimInsetFraction")
    else:
        _exact_keys(value, {"type", "rimInsetFraction", "depth"}, label)
        _inclusive_fraction(value["rimInsetFraction"], f"{label}.rimInsetFraction")
        _enum(value["depth"], _RECESS_DEPTHS, f"{label}.depth")


def _parse_sloper_metadata(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    sloper_type = _enum(value.get("type"), _SLOPER_TYPES, f"{label}.type")
    if sloper_type == "round":
        _exact_keys(value, {"type"}, label)
        return {"type": sloper_type}
    _required_and_allowed_keys(value, {"type"}, {"type", "angleDegrees"}, label)
    parsed: dict[str, object] = {"type": sloper_type}
    if "angleDegrees" in value:
        angle = value["angleDegrees"]
        if isinstance(angle, bool) or not isinstance(angle, (int, float)):
            raise BoardPackageError(f"{label}.angleDegrees must be finite and in 0...90")
        try:
            is_valid_angle = math.isfinite(angle) and 0 <= angle <= 90
        except OverflowError as error:
            raise BoardPackageError(
                f"{label}.angleDegrees must be finite and in 0...90"
            ) from error
        if not is_valid_angle:
            raise BoardPackageError(f"{label}.angleDegrees must be finite and in 0...90")
        parsed["angleDegrees"] = angle
    return parsed


def _parse_shape_constraint(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _exact_keys(value, {"shape", "rotationDegrees"}, label)
    shape = _enum(value.get("shape"), _SHAPE_CONSTRAINTS, f"{label}.shape")
    rotation = value.get("rotationDegrees")
    if (
        isinstance(rotation, bool)
        or not isinstance(rotation, (int, float))
        or not -180 <= rotation < 180
        or not math.isfinite(rotation)
    ):
        raise BoardPackageError(
            f"{label}.rotationDegrees must be finite and in [-180, 180)"
        )
    return {"shape": shape, "rotationDegrees": float(rotation)}


def _validate_editor_document(
    document: Mapping[str, Any],
    width: int,
    height: int,
    presentation_id: str | None = None,
    *,
    require_presentation_id: bool = False,
) -> dict[
    str,
    tuple[
        str,
        int,
        str | None,
        dict[str, object] | None,
        Any,
        dict[str, object] | None,
        tuple[int, ...],
        tuple[int, ...],
        int | None,
        int | float | None,
        dict[str, int | float] | None,
        int | None,
        str | None,
        str,
    ],
]:
    """Parse and cross-validate an editor document, allowing added/removed/
    recategorized holds. Returns key -> (holdID, pieceIndex, kind, sloper
    metadata, parsed path, shape constraint, bendable command indexes, smooth
    anchor indexes, finger capacity, fixed depth, depth range, hand capacity,
    paired hold, equipment object ID)."""
    if not isinstance(document, Mapping):
        raise BoardPackageError("editor document must be an object")
    _required_and_allowed_keys(
        document,
        {"canvas", "regions"},
        {"presentationID", "equipmentObjects", "canvas", "regions"},
        "editor document",
    )
    raw_equipment_objects = document.get("equipmentObjects", ["primary"])
    if not isinstance(raw_equipment_objects, list) or not raw_equipment_objects:
        raise BoardPackageError("editor document equipmentObjects must be a non-empty array")
    equipment_object_ids = [
        _identifier(item, f"editor document.equipmentObjects[{index}]")
        for index, item in enumerate(raw_equipment_objects)
    ]
    if len(set(equipment_object_ids)) != len(equipment_object_ids):
        raise BoardPackageError("editor document equipmentObjects must be unique")
    document_presentation_id = document.get("presentationID")
    if document_presentation_id is not None:
        document_presentation_id = _identifier(
            document_presentation_id, "editor document.presentationID"
        )
    if presentation_id is not None and document_presentation_id != presentation_id:
        raise BoardPackageError("editor document presentation does not match the selected surface")
    if document.get("canvas") != {"width": width, "height": height}:
        raise BoardPackageError("editor document canvas does not match the primary image")
    regions = document.get("regions")
    if not isinstance(regions, list) or not regions:
        raise BoardPackageError("editor document regions must be a non-empty array")

    parsed: dict[
        str,
        tuple[
            str,
            int,
            str | None,
            dict[str, object] | None,
            Any,
            dict[str, object] | None,
            tuple[int, ...],
            tuple[int, ...],
            int | None,
            int | float | None,
            dict[str, int | float] | None,
            int | None,
            str | None,
            str,
        ],
    ] = {}
    pieces_by_hold: dict[str, dict[int, str]] = {}
    kind_by_hold: dict[str, str | None] = {}
    sloper_by_hold: dict[str, dict[str, object] | None] = {}
    finger_capacity_by_hold: dict[str, int | None] = {}
    size_millimeters_by_hold: dict[str, int | float | None] = {}
    depth_range_by_hold: dict[str, dict[str, int | float] | None] = {}
    depth_representation_by_hold: dict[str, str] = {}
    hand_capacity_by_hold: dict[str, int | None] = {}
    paired_hold_id_by_hold: dict[str, str | None] = {}
    equipment_object_id_by_hold: dict[str, str] = {}
    for region in regions:
        if not isinstance(region, Mapping):
            raise BoardPackageError("editor document contains an invalid hold piece")
        _required_and_allowed_keys(
            region,
            {"id", "key", "displayPath", "metadata"},
            {
                "id",
                "key",
                "type",
                "pairedHoldID",
                "sloper",
                "displayPath",
                "metadata",
                "shapeConstraint",
            "bendableCommandIndexes",
            "smoothAnchorIndexes",
                "fingerCapacity",
                "sizeMillimeters",
                "depthRangeMillimeters",
                "handCapacity",
                "equipmentObjectID",
            },
            "editor region",
        )
        key = region.get("key")
        if not isinstance(key, str) or not key:
            raise BoardPackageError("editor document contains an invalid hold piece")
        if key in parsed:
            raise BoardPackageError("duplicate hold piece key")
        if isinstance(region.get("id"), bool) or not isinstance(region.get("id"), int):
            raise BoardPackageError(f"editor region {key}.id must be an integer")
        kind = (
            _enum(region["type"], _HOLD_KINDS, f"editor region {key}.type")
            if "type" in region
            else None
        )
        if "pairedHoldID" in region:
            if kind != "gaston":
                raise BoardPackageError(
                    f"editor region {key}.pairedHoldID is only allowed for gaston holds"
                )
            paired_hold_id = _identifier(
                region["pairedHoldID"], f"editor region {key}.pairedHoldID"
            )
        else:
            paired_hold_id = None
        if "sloper" in region:
            if kind != "sloper":
                raise BoardPackageError(
                    f"editor region {key}.sloper is only allowed for sloper holds"
                )
            sloper = _parse_sloper_metadata(
                region["sloper"], f"editor region {key}.sloper"
            )
        else:
            sloper = None
        metadata = region.get("metadata")
        if not isinstance(metadata, Mapping):
            raise BoardPackageError(f"editor region {key}.metadata must be an object")
        _required_and_allowed_keys(
            metadata,
            {"holdID", "pieceIndex"},
            {"holdID", "pieceIndex", "presentationID"},
            f"editor region {key}.metadata",
        )
        region_presentation_id = metadata.get("presentationID")
        if region_presentation_id is not None:
            region_presentation_id = _identifier(
                region_presentation_id,
                f"editor region {key}.metadata.presentationID",
            )
        if presentation_id is not None and (
            region_presentation_id != presentation_id
            and (require_presentation_id or region_presentation_id is not None)
        ):
            raise BoardPackageError(
                f"editor region {key} presentation does not match the selected surface"
            )
        hold_id = _identifier(metadata.get("holdID"), f"editor region {key}.metadata.holdID")
        piece_index = metadata.get("pieceIndex")
        if (
            isinstance(piece_index, bool)
            or not isinstance(piece_index, int)
            or piece_index < 0
        ):
            raise BoardPackageError(
                f"editor region {key}.metadata.pieceIndex must be a non-negative integer"
            )
        try:
            parsed_path = parse_closed_path(
                region.get("displayPath"), width, height, label=f"hold {key}"
            )
        except GeometryError as error:
            raise BoardPackageError(str(error)) from error
        shape_constraint = (
            _parse_shape_constraint(
                region["shapeConstraint"], f"editor region {key}.shapeConstraint"
            )
            if "shapeConstraint" in region
            else None
        )
        bendable_command_indexes = (
            _parse_bendable_command_indexes(
                region["bendableCommandIndexes"],
                f"editor region {key}.bendableCommandIndexes",
                parsed_path,
                shape_constraint,
            )
            if "bendableCommandIndexes" in region
            else ()
        )
        smooth_anchor_indexes = (
            _parse_smooth_anchor_indexes(
                region["smoothAnchorIndexes"],
                f"editor region {key}.smoothAnchorIndexes",
                parsed_path,
                shape_constraint,
            )
            if "smoothAnchorIndexes" in region
            else ()
        )
        if "fingerCapacity" in region:
            finger_capacity = region["fingerCapacity"]
            if (
                isinstance(finger_capacity, bool)
                or not isinstance(finger_capacity, int)
                or finger_capacity not in range(1, 5)
            ):
                raise BoardPackageError(
                    f"editor region {key}.fingerCapacity must be in 1...4"
                )
        else:
            finger_capacity = None
        if "sizeMillimeters" in region and "depthRangeMillimeters" in region:
            raise BoardPackageError(
                f"editor region {key} must not specify both a size and depth range"
            )
        if "sizeMillimeters" in region:
            _positive_number(
                region["sizeMillimeters"],
                f"editor region {key}.sizeMillimeters",
            )
            size_millimeters = region["sizeMillimeters"]
            depth_representation = "fixed"
        else:
            size_millimeters = None
            depth_representation = (
                "variable" if "depthRangeMillimeters" in region else "unset"
            )
        if "depthRangeMillimeters" in region:
            _millimeter_range(
                region["depthRangeMillimeters"],
                f"editor region {key}.depthRangeMillimeters",
            )
            depth_range = {
                "lowerBound": region["depthRangeMillimeters"]["lowerBound"],
                "upperBound": region["depthRangeMillimeters"]["upperBound"],
            }
        else:
            depth_range = None
        if "handCapacity" in region:
            hand_capacity = region["handCapacity"]
            if (
                isinstance(hand_capacity, bool)
                or not isinstance(hand_capacity, int)
                or hand_capacity not in range(1, 3)
            ):
                raise BoardPackageError(
                    f"editor region {key}.handCapacity must be in 1...2"
                )
        else:
            hand_capacity = None
        equipment_object_id = _identifier(
            region.get("equipmentObjectID", "primary"),
            f"editor region {key}.equipmentObjectID",
        )
        if equipment_object_id not in equipment_object_ids:
            raise BoardPackageError(
                f"editor region {key} references unknown equipment object {equipment_object_id}"
            )

        pieces = pieces_by_hold.setdefault(hold_id, {})
        if piece_index in pieces:
            raise BoardPackageError(f"hold {hold_id} has duplicate piece index {piece_index}")
        pieces[piece_index] = key
        if hold_id in kind_by_hold and kind_by_hold[hold_id] != kind:
            raise BoardPackageError(f"hold {hold_id} pieces must share one kind")
        kind_by_hold[hold_id] = kind
        if hold_id in sloper_by_hold and sloper_by_hold[hold_id] != sloper:
            raise BoardPackageError(
                f"hold {hold_id} pieces must share one sloper metadata value"
            )
        sloper_by_hold[hold_id] = sloper
        if hold_id in finger_capacity_by_hold and finger_capacity_by_hold[hold_id] != finger_capacity:
            raise BoardPackageError(f"hold {hold_id} pieces must share one finger capacity")
        finger_capacity_by_hold[hold_id] = finger_capacity
        if (hold_id in depth_representation_by_hold
            and depth_representation_by_hold[hold_id] != depth_representation):
            raise BoardPackageError(
                f"hold {hold_id} pieces must share one depth representation"
            )
        depth_representation_by_hold[hold_id] = depth_representation
        if (hold_id in size_millimeters_by_hold
            and size_millimeters_by_hold[hold_id] != size_millimeters):
            raise BoardPackageError(f"hold {hold_id} pieces must share one fixed depth")
        size_millimeters_by_hold[hold_id] = size_millimeters
        if hold_id in depth_range_by_hold and depth_range_by_hold[hold_id] != depth_range:
            raise BoardPackageError(f"hold {hold_id} pieces must share one depth range")
        depth_range_by_hold[hold_id] = depth_range
        if hold_id in hand_capacity_by_hold and hand_capacity_by_hold[hold_id] != hand_capacity:
            raise BoardPackageError(f"hold {hold_id} pieces must share one hand capacity")
        hand_capacity_by_hold[hold_id] = hand_capacity
        if (hold_id in paired_hold_id_by_hold
            and paired_hold_id_by_hold[hold_id] != paired_hold_id):
            raise BoardPackageError(f"hold {hold_id} pieces must share one paired hold")
        paired_hold_id_by_hold[hold_id] = paired_hold_id
        if (hold_id in equipment_object_id_by_hold
            and equipment_object_id_by_hold[hold_id] != equipment_object_id):
            raise BoardPackageError(
                f"hold {hold_id} pieces must share one equipment object"
            )
        equipment_object_id_by_hold[hold_id] = equipment_object_id
        parsed[key] = (
            hold_id,
            piece_index,
            kind,
            sloper,
            parsed_path,
            shape_constraint,
            bendable_command_indexes,
            smooth_anchor_indexes,
            finger_capacity,
            size_millimeters,
            depth_range,
            hand_capacity,
            paired_hold_id,
            equipment_object_id,
        )

    for hold_id, pieces in pieces_by_hold.items():
        if set(pieces) != set(range(len(pieces))):
            raise BoardPackageError(
                f"hold {hold_id} pieces must be indexed contiguously from 0"
            )

    return parsed


def _bendable_command_indexes(piece: Mapping[str, Any]) -> list[int]:
    if "shapeConstraint" in piece:
        return []
    shape = piece.get("shape")
    commands = shape.get("commands") if isinstance(shape, Mapping) else None
    if not isinstance(commands, list):
        return []
    return [
        index
        for index, command in enumerate(commands)
        if isinstance(command, Mapping)
        and command.get("command") == "curve"
        and command.get("bendable") is True
    ]


def _smooth_anchor_indexes(piece: Mapping[str, Any]) -> list[int]:
    if "shapeConstraint" in piece:
        return []
    shape = piece.get("shape")
    commands = shape.get("commands") if isinstance(shape, Mapping) else None
    if not isinstance(commands, list):
        return []
    return [index for index, command in enumerate(commands) if isinstance(command, Mapping) and command.get("smooth") is True]


def _parse_bendable_command_indexes(
    value: object,
    label: str,
    path: ClosedPath,
    shape_constraint: dict[str, object] | None,
) -> tuple[int, ...]:
    if shape_constraint is not None:
        raise BoardPackageError(f"{label} cannot be used with a shapeConstraint")
    if not isinstance(value, list):
        raise BoardPackageError(f"{label} must be an array")
    if any(isinstance(index, bool) or not isinstance(index, int) or index < 0 for index in value):
        raise BoardPackageError(f"{label} must contain non-negative integers")
    if len(value) != len(set(value)):
        raise BoardPackageError(f"{label} must not contain duplicates")
    for index in value:
        if index >= len(path.commands) or path.commands[index][0] != "C":
            raise BoardPackageError(f"{label} must select cubic curve commands")
    return tuple(value)


def _parse_smooth_anchor_indexes(
    value: object,
    label: str,
    path: ClosedPath,
    shape_constraint: dict[str, object] | None,
) -> tuple[int, ...]:
    if shape_constraint is not None:
        raise BoardPackageError(f"{label} cannot be used with a shapeConstraint")
    if not isinstance(value, list):
        raise BoardPackageError(f"{label} must be an array")
    if any(isinstance(index, bool) or not isinstance(index, int) or index < 0 for index in value):
        raise BoardPackageError(f"{label} must contain non-negative integers")
    if len(value) != len(set(value)):
        raise BoardPackageError(f"{label} must not contain duplicates")
    for index in value:
        if (index <= 0 or index + 1 >= len(path.commands)
                or path.commands[index][0] not in {"Q", "C"}
                or path.commands[index + 1][0] not in {"Q", "C"}):
            raise BoardPackageError(f"{label} must identify an anchor between editable Bezier segments")
    return tuple(value)


def _apply_bendable_command_indexes(
    piece: dict[str, Any], indexes: tuple[int, ...],
) -> None:
    shape = piece["shape"]
    commands = shape.get("commands") if isinstance(shape, Mapping) else None
    if not isinstance(commands, list):
        if indexes:
            raise BoardPackageError("bendableCommandIndexes must select cubic curve commands")
        return
    for command in commands:
        if command.get("command") == "curve":
            command.pop("bendable", None)
    for index in indexes:
        commands[index]["bendable"] = True


def _apply_smooth_anchor_indexes(piece: dict[str, Any], indexes: tuple[int, ...]) -> None:
    shape = piece["shape"]
    commands = shape.get("commands") if isinstance(shape, Mapping) else None
    if not isinstance(commands, list):
        if indexes:
            raise BoardPackageError("smoothAnchorIndexes must select editable Bezier anchors")
        return
    for command in commands:
        command.pop("smooth", None)
    for index in indexes:
        commands[index]["smooth"] = True


def _piece_key(hold_id: str, piece_index: int) -> str:
    return f"{hold_id}-piece-{piece_index}"


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
    raw = Path(path)
    if raw.is_symlink():
        raise BoardPackageError("board library must not be a symlink")
    try:
        root = raw.resolve(strict=True)
    except OSError as error:
        raise BoardPackageError("board library is not accessible") from error
    if not root.is_dir():
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
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _rounded_json(value: object) -> object:
    if isinstance(value, float):
        return round(value, 12)
    if isinstance(value, list):
        return [_rounded_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _rounded_json(item) for key, item in value.items()}
    return value


def _required_and_allowed_keys(
    value: Mapping[str, Any],
    required: set[str] | frozenset[str],
    allowed: set[str] | frozenset[str],
    label: str,
) -> None:
    unknown = set(value) - set(allowed)
    missing = set(required) - set(value)
    if unknown or missing:
        details: list[str] = []
        if unknown:
            details.append(f"unknown keys: {sorted(unknown)}")
        if missing:
            details.append(f"missing keys: {sorted(missing)}")
        raise BoardPackageError(f"{label} has " + "; ".join(details))


def _exact_keys(
    value: Mapping[str, Any], expected: set[str] | frozenset[str], label: str
) -> None:
    _required_and_allowed_keys(value, expected, expected, label)


def _non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise BoardPackageError(f"{label} must be a non-empty string")
    return value


def _finite_number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise BoardPackageError(f"{label} must be a finite number")
    return float(value)


def _positive_number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise BoardPackageError(f"{label} must be a positive finite number")
    return float(value)


def _normalized_point(value: object, label: str) -> tuple[float, float]:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _exact_keys(value, {"x", "y"}, label)
    return (
        _normalized_coordinate(value["x"], f"{label}.x"),
        _normalized_coordinate(value["y"], f"{label}.y"),
    )


def _normalized_coordinate(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 1
    ):
        raise BoardPackageError(f"{label} must be a finite number in 0...1")
    return float(value)


def _millimeter_range(value: object, label: str) -> None:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _exact_keys(value, {"lowerBound", "upperBound"}, label)
    lower = _positive_number(value.get("lowerBound"), f"{label}.lowerBound")
    upper = _positive_number(value.get("upperBound"), f"{label}.upperBound")
    if lower > upper:
        raise BoardPackageError(f"{label}.lowerBound must not exceed upperBound")


def _inclusive_fraction(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 0.5
    ):
        raise BoardPackageError(f"{label} must be in 0...0.5")
    return float(value)


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


def _presentation_asset_path(value: object, label: str) -> str:
    asset_path = _non_empty_string(value, label)
    path = PurePosixPath(asset_path)
    if (
        path.is_absolute()
        or path.parts[:1] != ("assets",)
        or len(path.parts) < 2
        or any(part in {".", ".."} for part in path.parts)
        or path.as_posix() != asset_path
        or path.suffix != ".png"
    ):
        raise BoardPackageError(f"{label} must name a PNG beneath assets/")
    return asset_path


def _slug(value: object) -> str:
    if not isinstance(value, str) or not _SLUG.fullmatch(value):
        raise BoardPackageError("board package path must be a single board slug")
    return value


def _reject_symlinks(root: Path) -> None:
    if root.is_symlink() or any(item.is_symlink() for item in root.rglob("*")):
        raise BoardPackageError("board package must not contain symlinks")


def _png_header_dimensions(path: Path) -> tuple[int, int]:
    try:
        with path.open("rb") as image:
            data = image.read(33)
    except OSError as error:
        raise BoardPackageError("package primary image is not readable") from error
    return _png_header_dimensions_from_bytes(data)


def _png_header_dimensions_from_bytes(data: bytes) -> tuple[int, int]:
    if (
        len(data) != 33
        or data[:8] != b"\x89PNG\r\n\x1a\n"
        or int.from_bytes(data[8:12], "big") != 13
        or data[12:16] != b"IHDR"
        or zlib.crc32(data[12:29]) & 0xFFFFFFFF
        != int.from_bytes(data[29:33], "big")
    ):
        raise BoardPackageError("package primary image must be a decodable PNG")
    width, height, _bit_depth, _color_type, _interlace = _validate_png_ihdr(
        data[16:29]
    )
    return width, height


def _png_dimensions(path: Path) -> tuple[int, int]:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise BoardPackageError("package primary image is not readable") from error
    return _png_dimensions_from_bytes(data)


def _png_dimensions_from_bytes(data: bytes) -> tuple[int, int]:
    ihdr: bytes | None = None
    compressed_parts: list[bytes] = []
    has_palette = False
    ended_idat = False
    for chunk_type, payload in _png_chunks(data):
        length = len(payload)
        if ihdr is None and chunk_type != b"IHDR":
            raise BoardPackageError("package primary image must be a decodable PNG")
        if chunk_type == b"IHDR":
            if ihdr is not None or length != 13:
                raise BoardPackageError("package primary image must be a decodable PNG")
            ihdr = payload
        elif chunk_type == b"PLTE":
            if has_palette or compressed_parts or not 3 <= length <= 768 or length % 3:
                raise BoardPackageError("package primary image must be a decodable PNG")
            has_palette = True
        elif chunk_type == b"IDAT":
            if ended_idat:
                raise BoardPackageError("package primary image must be a decodable PNG")
            compressed_parts.append(payload)
        elif chunk_type == b"IEND":
            if length != 0:
                raise BoardPackageError("package primary image must be a decodable PNG")
            break
        else:
            if compressed_parts:
                ended_idat = True
            if chunk_type and chunk_type[0] & 0x20 == 0:
                raise BoardPackageError("package primary image must be a decodable PNG")
    if ihdr is None or not compressed_parts:
        raise BoardPackageError("package primary image must be a decodable PNG")
    width, height, bit_depth, color_type, interlace = _validate_png_ihdr(ihdr)
    if color_type == 3 and not has_palette:
        raise BoardPackageError("package primary image must be a decodable PNG")

    layouts = _png_scanline_layouts(
        width,
        height,
        bit_depth,
        color_type,
        interlace,
    )
    decoded = _png_inflate_exact(compressed_parts, layouts)
    cursor = 0
    for row_size, row_count in layouts:
        for _ in range(row_count):
            if decoded[cursor] > 4:
                raise BoardPackageError("package primary image must be a decodable PNG")
            cursor += row_size
    return width, height


def _png_chunks(data: bytes) -> tuple[tuple[bytes, bytes], ...]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise BoardPackageError("package primary image must be a decodable PNG")

    chunks: list[tuple[bytes, bytes]] = []
    offset = 8
    while offset < len(data):
        if len(data) - offset < 12:
            raise BoardPackageError("package primary image must be a decodable PNG")
        length = int.from_bytes(data[offset : offset + 4], "big")
        chunk_type = data[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            raise BoardPackageError("package primary image must be a decodable PNG")
        payload = data[offset + 8 : offset + 8 + length]
        expected_crc = int.from_bytes(data[offset + 8 + length : chunk_end], "big")
        if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF != expected_crc:
            raise BoardPackageError("package primary image must be a decodable PNG")
        chunks.append((chunk_type, payload))
        offset = chunk_end
        if chunk_type == b"IEND":
            if offset != len(data):
                raise BoardPackageError("package primary image must be a decodable PNG")
            return tuple(chunks)

    raise BoardPackageError("package primary image must be a decodable PNG")


def _png_scanline_layouts(
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
    interlace: int,
) -> tuple[tuple[int, int], ...]:
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    passes = (
        ((0, 0, 1, 1),)
        if interlace == 0
        else (
            (0, 0, 8, 8),
            (4, 0, 8, 8),
            (0, 4, 4, 8),
            (2, 0, 4, 4),
            (0, 2, 2, 4),
            (1, 0, 2, 2),
            (0, 1, 1, 2),
        )
    )
    layouts: list[tuple[int, int]] = []
    bits_per_pixel = channels[color_type] * bit_depth
    for start_x, start_y, step_x, step_y in passes:
        pass_width = max(0, (width - start_x + step_x - 1) // step_x)
        pass_height = max(0, (height - start_y + step_y - 1) // step_y)
        if pass_width and pass_height:
            layouts.append(((pass_width * bits_per_pixel + 7) // 8 + 1, pass_height))
    return tuple(layouts)


def _png_inflate_exact(
    compressed_parts: list[bytes],
    layouts: tuple[tuple[int, int], ...],
) -> bytes:
    expected_size = sum(row_size * row_count for row_size, row_count in layouts)
    try:
        decompressor = zlib.decompressobj()
        decoded = decompressor.decompress(b"".join(compressed_parts), expected_size + 1)
    except zlib.error as error:
        raise BoardPackageError("package primary image must be a decodable PNG") from error
    if (
        len(decoded) != expected_size
        or not decompressor.eof
        or decompressor.unconsumed_tail
        or decompressor.unused_data
    ):
        raise BoardPackageError("package primary image must be a decodable PNG")
    return decoded


def _validate_png_ihdr(ihdr: bytes) -> tuple[int, int, int, int, int]:
    width = int.from_bytes(ihdr[0:4], "big")
    height = int.from_bytes(ihdr[4:8], "big")
    bit_depth, color_type, compression, filtering, interlace = ihdr[8:13]
    valid_depths = {
        0: {1, 2, 4, 8, 16},
        2: {8, 16},
        3: {1, 2, 4, 8},
        4: {8, 16},
        6: {8, 16},
    }
    if (
        width <= 0
        or height <= 0
        or bit_depth not in valid_depths.get(color_type, set())
        or compression != 0
        or filtering != 0
        or interlace not in {0, 1}
    ):
        raise BoardPackageError("package primary image must be a decodable PNG")
    return width, height, bit_depth, color_type, interlace
