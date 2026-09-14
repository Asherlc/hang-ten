"""Native schema-v3 hangboard package storage for Hangboard Workbench."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace as dataclass_replace
import fcntl
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from typing import Any, Iterator, Mapping, Protocol
import uuid

_PACKAGES_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "HangboardPackages" / "src"
if _PACKAGES_SOURCE_ROOT.is_dir() and str(_PACKAGES_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGES_SOURCE_ROOT))

try:
    from hangboard_packages import board_catalog as _board_catalog
except ImportError:  # PyInstaller resolves this through its explicit hidden import.
    _board_catalog = None

from board_geometry import (
    ClosedPath,
    GeometryError,
    NormalizedFrame,
    display_path_for_shape,
    parse_closed_path,
    shape_for_path,
    union_normalized_frames,
)


_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:[a-z0-9._-]*[a-z0-9])?$")
_SLUG = re.compile(r"^[a-z0-9]+(?:[a-z0-9-]*[a-z0-9])?$")
_ASPECT_RATIO_RELATIVE_TOLERANCE = 0.001
_SHAPE_CONSTRAINTS = frozenset(
    {"oval", "circle", "pill", "roundedRectangle", "rectangle"}
)
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


class BoardEditorUnavailableError(BoardPackageError):
    """Raised when a package has valid media that Workbench cannot edit."""


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
    media_type: str = "raster"
    descriptor_path: str | None = None


@dataclass(frozen=True, slots=True)
class BoardPackage:
    root: Path
    board: dict[str, Any]
    image_width: int
    image_height: int
    presentations: tuple[BoardPresentation, ...]
    schema_version: int = 3

    @property
    def board_id(self) -> str:
        return self.board["id"]

    @property
    def contact_ids(self) -> tuple[str, ...]:
        return tuple(contact["id"] for contact in self.board["contacts"])

    @property
    def editor_available(self) -> bool:
        return all(item.media_type == "raster" for item in self.presentations)

    def presentation(self, presentation_id: str | None = None) -> BoardPresentation:
        selected = (
            next((item for item in self.presentations if item.id == presentation_id), None)
            if presentation_id is not None
            else next((item for item in self.presentations if item.is_default), None)
        )
        if selected is None:
            raise BoardPackageError("presentation is not available")
        return selected

    def contact_frame(self, contact_id: str) -> NormalizedFrame:
        _identifier(contact_id, "contact ID")
        for presentation in self.board["presentations"]:
            media = presentation["media"]
            if media["type"] != "raster":
                continue
            pieces = media["contactGeometry"].get(contact_id)
            if pieces:
                try:
                    return union_normalized_frames(
                        NormalizedFrame.from_json(piece["frame"], f"contact {contact_id}")
                        for piece in pieces
                    )
                except (GeometryError, KeyError, TypeError) as error:
                    raise BoardPackageError(
                        f"contact {contact_id} has invalid geometry"
                    ) from error
        raise BoardPackageError("contact is not available")


class _EditorDocumentPackage(Protocol):
    board: dict[str, Any]
    presentations: tuple[BoardPresentation, ...]

    def presentation(self, presentation_id: str | None = None) -> BoardPresentation: ...


@dataclass(frozen=True, slots=True)
class _EditorPiece:
    contact_id: str
    piece_index: int
    path: ClosedPath
    treatment: dict[str, Any] | None
    shape_constraint: dict[str, object] | None
    bendable_command_indexes: tuple[int, ...]
    smooth_anchor_indexes: tuple[int, ...]


def _catalog() -> Any:
    if _board_catalog is None:
        raise BoardPackageError("schema-v3 package support is unavailable")
    return _board_catalog


def validate_catalog_board(
    board: Mapping[str, Any], *, allow_missing_kind: bool = False
) -> None:
    """Validate a remote manifest with the one shipped schema-v3 decoder."""
    del allow_missing_kind
    try:
        _catalog()._load_board(board)
    except (KeyError, TypeError, ValueError) as error:
        raise BoardPackageError(str(error)) from error


def _board_editor_available(board: Mapping[str, Any]) -> bool:
    validate_catalog_board(board)
    return all(item["media"]["type"] == "raster" for item in board["presentations"])


def discover_packages(
    library_root: Path, *, final_inventory: bool = False
) -> tuple[BoardPackage, ...]:
    root = _library_root(library_root)
    with _library_lock(root, shared=True):
        return _discover_packages_unlocked(root, final_inventory=final_inventory)


def open_package(library_root: Path, board_id: str) -> BoardPackage:
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
        if not package.editor_available:
            raise BoardEditorUnavailableError("3D model editing is not supported")
        return load_board_package(package.root)


def load_board_package(package_root: Path) -> BoardPackage:
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
    board = _load_json(root / "board.json", "board.json")
    validate_catalog_board(board)
    if inspect_png_header_only:
        _validate_package_shape_for_discovery(root, board)
    else:
        try:
            _catalog().load_board_package(root)
        except (KeyError, OSError, TypeError, ValueError) as error:
            raise BoardPackageError(str(error)) from error
    presentations = _presentations_from_board(
        root, board, inspect_png_header_only=inspect_png_header_only
    )
    default = next(item for item in presentations if item.is_default)
    package = BoardPackage(
        root,
        board,
        default.image_width,
        default.image_height,
        presentations,
    )
    if not inspect_png_header_only:
        for presentation in presentations:
            if presentation.media_type == "raster":
                editor_document(package, presentation.id)
    return package


def _presentations_from_board(
    root: Path,
    board: Mapping[str, Any],
    *,
    inspect_png_header_only: bool = False,
) -> tuple[BoardPresentation, ...]:
    result: list[BoardPresentation] = []
    for item in board["presentations"]:
        media = item["media"]
        width = 0
        height = 0
        if media["type"] == "raster":
            try:
                width, height = (
                    _png_header_dimensions(root / media["assetPath"])
                    if inspect_png_header_only
                    else _catalog()._validate_png_structure(
                        root / media["assetPath"], media["assetPath"]
                    )
                )
            except (OSError, ValueError) as error:
                raise BoardPackageError(str(error)) from error
        derivation = item["derivation"]
        result.append(
            BoardPresentation(
                id=item["id"],
                name=item["name"],
                asset_path=media["assetPath"],
                aspect_ratio=item["aspectRatio"],
                is_default=item["isDefault"],
                image_width=width,
                image_height=height,
                source_presentation_id=(
                    derivation.get("sourcePresentationID")
                    if derivation["type"] == "derived"
                    else None
                ),
                is_inverted=derivation.get("isInverted", False),
                media_type=media["type"],
                descriptor_path=media.get("descriptorPath"),
            )
        )
    return tuple(result)


def _validate_package_shape_for_discovery(
    root: Path, board: Mapping[str, Any]
) -> None:
    """Validate the package inventory without decoding full raster/model assets."""
    if {item.name for item in root.iterdir()} != {"board.json", "assets"}:
        raise BoardPackageError("board package must contain only board.json and assets/")
    assets = root / "assets"
    if assets.is_symlink() or not assets.is_dir():
        raise BoardPackageError("board package assets must be a regular directory")
    for item in root.rglob("*"):
        if item.is_symlink():
            raise BoardPackageError("board package must not contain symlinks")
    expected_assets: set[str] = set()
    for presentation in board["presentations"]:
        media = presentation["media"]
        expected_assets.add(media["assetPath"])
        if media["type"] == "model":
            expected_assets.add(media["descriptorPath"])
    actual_assets = {
        item.relative_to(root).as_posix()
        for item in assets.rglob("*")
        if item.is_file()
    }
    if actual_assets != expected_assets:
        raise BoardPackageError("board package assets must exactly match its presentations")


def primary_image_path(package: BoardPackage) -> Path:
    return presentation_image_path(package)


def presentation_image_path(
    package: BoardPackage, presentation_id: str | None = None
) -> Path:
    presentation = package.presentation(presentation_id)
    if presentation.media_type != "raster":
        raise BoardEditorUnavailableError("3D model editing is not supported")
    image = package.root / presentation.asset_path
    if not image.is_file() or image.is_symlink():
        raise BoardPackageError("package presentation image is missing")
    return image


def editor_document(
    package: _EditorDocumentPackage, presentation_id: str | None = None
) -> dict[str, object]:
    """Project native contact facts and media-owned paths into the editor."""
    presentation = package.presentation(presentation_id)
    if presentation.media_type != "raster":
        raise BoardEditorUnavailableError("3D model editing is not supported")
    raw_presentation = next(
        item for item in package.board["presentations"] if item["id"] == presentation.id
    )
    geometry = raw_presentation["media"]["contactGeometry"]
    width, height = presentation.image_width, presentation.image_height
    regions: list[dict[str, object]] = []
    region_id = 1
    for contact in package.board["contacts"]:
        contact_id = contact["id"]
        for piece_index, piece in enumerate(geometry.get(contact_id, [])):
            key = _piece_key(contact_id, piece_index)
            try:
                path = display_path_for_shape(
                    piece["frame"], piece["shape"], width, height, label=f"contact {key}"
                )
                if presentation.is_inverted:
                    path = _inverted_display_path(
                        path, width, height, label=f"contact {key}"
                    )
            except (GeometryError, KeyError, TypeError) as error:
                raise BoardPackageError(f"contact {key} has invalid geometry") from error
            region: dict[str, object] = {
                "id": region_id,
                "key": key,
                "displayPath": path.data,
                "metadata": {
                    "contactID": contact_id,
                    "pieceIndex": piece_index,
                    "presentationID": presentation.id,
                },
            }
            for member in ("treatment", "shapeConstraint"):
                if member in piece:
                    region[member] = _copy_json(piece[member])
            bendable = _bendable_command_indexes(piece)
            if bendable:
                region["bendableCommandIndexes"] = bendable
            smooth = _smooth_anchor_indexes(piece)
            if smooth:
                region["smoothAnchorIndexes"] = smooth
            regions.append(region)
            region_id += 1
    return {
        "presentationID": presentation.id,
        "contacts": _copy_json(package.board["contacts"]),
        "canvas": {"width": width, "height": height},
        "regions": regions,
    }


def _inverted_display_path(
    path: ClosedPath, width: int, height: int, *, label: str
) -> ClosedPath:
    commands: list[str] = []
    for command, values in path.commands:
        if command == "Z":
            commands.append(command)
            continue
        inverted_values = tuple(
            (width - value) if index % 2 == 0 else (height - value)
            for index, value in enumerate(values)
        )
        commands.append(
            " ".join((command, *(format(value, ".12g") for value in inverted_values)))
        )
    return parse_closed_path(" ".join(commands), width, height, label=label)


def save_editor_document(
    library_root: Path, slug: str, document: Mapping[str, Any]
) -> BoardPackage:
    root = _library_root(library_root)
    slug = _slug(slug)
    with _library_lock(root):
        inventory = _discover_packages_unlocked(root)
        live = next((item for item in inventory if item.root.name == slug), None)
        if live is None:
            raise BoardPackageError("board package is not available")
        if not live.editor_available:
            raise BoardEditorUnavailableError("3D model editing is not supported")
        live = load_board_package(live.root)
        candidate_board = apply_editor_document(live, document)
        if _json_values_are_exactly_equal(candidate_board, live.board):
            return live
        candidate_parent = Path(tempfile.mkdtemp(prefix=".workbench-edit-", dir=root))
        candidate = candidate_parent / slug
        try:
            shutil.copytree(live.root, candidate)
            _write_json(candidate / "board.json", candidate_board)
            return _replace_package_locked(root, slug, candidate, inventory=inventory)
        finally:
            shutil.rmtree(candidate_parent, ignore_errors=True)


def apply_editor_document(
    package: _EditorDocumentPackage, document: Mapping[str, Any]
) -> dict[str, Any]:
    requested_id = document.get("presentationID")
    presentation = package.presentation(requested_id if isinstance(requested_id, str) else None)
    if presentation.media_type != "raster":
        raise BoardEditorUnavailableError("3D model editing is not supported")
    if presentation.source_presentation_id is not None:
        raise BoardPackageError("derived presentations cannot be edited")
    contacts, pieces = _validate_editor_document(
        document,
        presentation.image_width,
        presentation.image_height,
        presentation.id,
    )
    current_presentation = next(
        item for item in package.board["presentations"] if item["id"] == presentation.id
    )
    current_geometry = current_presentation["media"]["contactGeometry"]
    current_paths = _current_display_paths(
        current_geometry, presentation.image_width, presentation.image_height
    )
    pieces_by_contact: dict[str, list[_EditorPiece]] = {}
    for piece in pieces.values():
        pieces_by_contact.setdefault(piece.contact_id, []).append(piece)
    for contact_pieces in pieces_by_contact.values():
        contact_pieces.sort(key=lambda item: item.piece_index)
    geometry: dict[str, list[dict[str, Any]]] = {}
    for contact in contacts:
        contact_id = contact["id"]
        contact_pieces = pieces_by_contact.get(contact_id)
        if not contact_pieces:
            continue
        old_pieces = current_geometry.get(contact_id, [])
        updated: list[dict[str, Any]] = []
        for piece in contact_pieces:
            if piece.piece_index < len(old_pieces):
                raw_piece = _copy_json(old_pieces[piece.piece_index])
                current_path = current_paths.get((contact_id, piece.piece_index))
                if current_path is None or current_path.data != piece.path.data:
                    frame, shape = shape_for_path(
                        piece.path, presentation.image_width, presentation.image_height
                    )
                    raw_piece["frame"] = frame.to_json()
                    raw_piece["shape"] = _rounded_json(shape)
            else:
                frame, shape = shape_for_path(
                    piece.path, presentation.image_width, presentation.image_height
                )
                raw_piece = {"frame": frame.to_json(), "shape": _rounded_json(shape)}
            _replace_optional(raw_piece, "treatment", piece.treatment)
            _replace_optional(raw_piece, "shapeConstraint", piece.shape_constraint)
            _apply_bendable_command_indexes(raw_piece, piece.bendable_command_indexes)
            _apply_smooth_anchor_indexes(raw_piece, piece.smooth_anchor_indexes)
            updated.append(raw_piece)
        geometry[contact_id] = updated

    copied = _copy_json(package.board)
    copied["contacts"] = contacts
    for raw_presentation in copied["presentations"]:
        derivation = raw_presentation["derivation"]
        owns_same_geometry = raw_presentation["id"] == presentation.id or (
            derivation["type"] == "derived"
            and derivation["sourcePresentationID"] == presentation.id
        )
        if owns_same_geometry:
            raw_presentation["media"]["contactGeometry"] = _copy_json(geometry)
    validate_catalog_board(copied)
    return copied


def delete_presentation(
    library_root: Path, slug: str, presentation_id: str
) -> BoardPackage:
    root = _library_root(library_root)
    slug = _slug(slug)
    with _library_lock(root):
        inventory = _discover_packages_unlocked(root)
        live = next((item for item in inventory if item.root.name == slug), None)
        if live is None:
            raise BoardPackageError("board package is not available")
        if not live.editor_available:
            raise BoardEditorUnavailableError("3D model editing is not supported")
        live = load_board_package(live.root)
        board, removed_assets = _delete_presentation_from_board(live.board, presentation_id)
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
    presentation_id = _identifier(presentation_id, "presentation ID")
    copied = _copy_json(board)
    presentations = copied["presentations"]
    selected = next((item for item in presentations if item["id"] == presentation_id), None)
    if selected is None:
        raise BoardPackageError("presentation is not available")
    if selected["media"]["type"] != "raster":
        raise BoardEditorUnavailableError("3D model editing is not supported")
    if selected["derivation"]["type"] == "derived":
        raise BoardPackageError("only original presentations can be deleted")
    originals = [item for item in presentations if item["derivation"]["type"] == "original"]
    if len(originals) == 1:
        raise BoardPackageError("cannot delete the only original presentation")
    removed_ids = {
        item["id"]
        for item in presentations
        if item["id"] == presentation_id
        or (
            item["derivation"]["type"] == "derived"
            and item["derivation"]["sourcePresentationID"] == presentation_id
        )
    }
    removed = [item for item in presentations if item["id"] in removed_ids]
    remaining = [item for item in presentations if item["id"] not in removed_ids]
    if any(item["isDefault"] for item in removed):
        next_default = next(
            item for item in remaining if item["derivation"]["type"] == "original"
        )
        for item in remaining:
            item["isDefault"] = item is next_default
        copied["aspectRatio"] = next_default["aspectRatio"]
    copied["presentations"] = remaining

    remaining_asset_paths = {item["media"]["assetPath"] for item in remaining}
    removed_assets = {
        item["media"]["assetPath"]
        for item in removed
        if item["media"]["assetPath"] not in remaining_asset_paths
    }
    owned_contacts = {
        contact_id
        for item in remaining
        if item["derivation"]["type"] == "original"
        for contact_id in item["media"]["contactGeometry"]
    }
    copied["contacts"] = [
        contact for contact in copied["contacts"] if contact["id"] in owned_contacts
    ]
    retained_contact_ids = {contact["id"] for contact in copied["contacts"]}
    copied["contacts"] = [
        contact
        for contact in copied["contacts"]
        if contact.get("pairedContactID") is None
        or contact["pairedContactID"] in retained_contact_ids
    ]
    retained_contact_ids = {contact["id"] for contact in copied["contacts"]}
    for item in remaining:
        item["media"]["contactGeometry"] = {
            contact_id: geometry
            for contact_id, geometry in item["media"]["contactGeometry"].items()
            if contact_id in retained_contact_ids
        }
    if "positions" in copied:
        removed_positions = {
            item["id"] for item in copied["positions"] if item["presentationID"] in removed_ids
        }
        copied["positions"] = [
            item for item in copied["positions"] if item["id"] not in removed_positions
        ]
        for position in copied["positions"]:
            if "contactIDs" in position:
                position["contactIDs"] = [
                    item for item in position["contactIDs"] if item in retained_contact_ids
                ]
        if "positionTransitions" in copied:
            copied["positionTransitions"] = [
                item
                for item in copied["positionTransitions"]
                if item["fromPositionID"] not in removed_positions
                and item["toPositionID"] not in removed_positions
            ]
    if "equipmentObjects" in copied:
        used = {contact["equipmentObjectID"] for contact in copied["contacts"]}
        copied["equipmentObjects"] = [
            item for item in copied["equipmentObjects"] if item["id"] in used
        ]
    validate_catalog_board(copied)
    return copied, tuple(sorted(removed_assets))


def replace_package(library_root: Path, slug: str, candidate_root: Path) -> None:
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
            packages.append(_load_board_package(child, inspect_png_header_only=True))
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
    return tuple(
        sorted(
            packages,
            key=lambda package: (
                package.board["manufacturer"].lower(),
                package.board["manufacturer"],
                package.board["name"].lower(),
                package.board["name"],
                package.board_id.lower(),
                package.board_id,
            ),
        )
    )


def _is_primary_only_draft(root: Path) -> bool:
    try:
        return _catalog().is_primary_only_draft(root)
    except ValueError as error:
        raise BoardPackageError(str(error)) from error


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
        _replace_transaction(root, slug, staged_package)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return dataclass_replace(candidate, root=root / slug)


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


def _validate_editor_document(
    document: Mapping[str, Any], width: int, height: int, presentation_id: str
) -> tuple[list[dict[str, Any]], dict[str, _EditorPiece]]:
    if not isinstance(document, Mapping):
        raise BoardPackageError("editor document must be an object")
    _exact_keys(
        document,
        {"presentationID", "contacts", "canvas", "regions"},
        "editor document",
    )
    if document["presentationID"] != presentation_id:
        raise BoardPackageError("editor document presentation does not match the selected surface")
    if document["canvas"] != {"width": width, "height": height}:
        raise BoardPackageError("editor document canvas does not match the selected image")
    raw_contacts = document["contacts"]
    if not isinstance(raw_contacts, list) or not raw_contacts:
        raise BoardPackageError("editor document contacts must be a non-empty array")
    contacts = _copy_json(raw_contacts)
    contact_ids: list[str] = []
    for index, contact in enumerate(contacts):
        if not isinstance(contact, Mapping):
            raise BoardPackageError(f"editor document.contacts[{index}] must be an object")
        contact_ids.append(
            _identifier(contact.get("id"), f"editor document.contacts[{index}].id")
        )
    if len(set(contact_ids)) != len(contact_ids):
        raise BoardPackageError("editor document contacts must have unique IDs")
    regions = document["regions"]
    if not isinstance(regions, list) or not regions:
        raise BoardPackageError("editor document regions must be a non-empty array")
    parsed: dict[str, _EditorPiece] = {}
    pieces_by_contact: dict[str, set[int]] = {}
    for raw_region in regions:
        if not isinstance(raw_region, Mapping):
            raise BoardPackageError("editor document contains an invalid contact piece")
        _required_and_allowed_keys(
            raw_region,
            {"id", "key", "displayPath", "metadata"},
            {
                "id", "key", "displayPath", "metadata", "treatment",
                "shapeConstraint", "bendableCommandIndexes", "smoothAnchorIndexes",
            },
            "editor region",
        )
        key = raw_region["key"]
        if not isinstance(key, str) or not key or key in parsed:
            raise BoardPackageError("editor document contains a duplicate or invalid piece key")
        if isinstance(raw_region["id"], bool) or not isinstance(raw_region["id"], int):
            raise BoardPackageError(f"editor region {key}.id must be an integer")
        metadata = raw_region["metadata"]
        if not isinstance(metadata, Mapping):
            raise BoardPackageError(f"editor region {key}.metadata must be an object")
        _exact_keys(
            metadata,
            {"contactID", "pieceIndex", "presentationID"},
            f"editor region {key}.metadata",
        )
        contact_id = _identifier(
            metadata["contactID"], f"editor region {key}.metadata.contactID"
        )
        if contact_id not in contact_ids:
            raise BoardPackageError(f"editor region {key} references an unknown contact")
        if metadata["presentationID"] != presentation_id:
            raise BoardPackageError(
                f"editor region {key} presentation does not match the selected surface"
            )
        piece_index = metadata["pieceIndex"]
        if isinstance(piece_index, bool) or not isinstance(piece_index, int) or piece_index < 0:
            raise BoardPackageError(
                f"editor region {key}.metadata.pieceIndex must be a non-negative integer"
            )
        indexes = pieces_by_contact.setdefault(contact_id, set())
        if piece_index in indexes:
            raise BoardPackageError(
                f"contact {contact_id} has duplicate piece index {piece_index}"
            )
        indexes.add(piece_index)
        try:
            path = parse_closed_path(
                raw_region["displayPath"], width, height, label=f"contact {key}"
            )
        except GeometryError as error:
            raise BoardPackageError(str(error)) from error
        constraint = (
            _parse_shape_constraint(
                raw_region["shapeConstraint"], f"editor region {key}.shapeConstraint"
            )
            if "shapeConstraint" in raw_region
            else None
        )
        bendable = (
            _parse_command_indexes(
                raw_region["bendableCommandIndexes"],
                f"editor region {key}.bendableCommandIndexes",
                path,
                constraint,
                bendable=True,
            )
            if "bendableCommandIndexes" in raw_region
            else ()
        )
        smooth = (
            _parse_command_indexes(
                raw_region["smoothAnchorIndexes"],
                f"editor region {key}.smoothAnchorIndexes",
                path,
                constraint,
                bendable=False,
            )
            if "smoothAnchorIndexes" in raw_region
            else ()
        )
        treatment = _copy_json(raw_region["treatment"]) if "treatment" in raw_region else None
        parsed[key] = _EditorPiece(
            contact_id, piece_index, path, treatment, constraint, bendable, smooth
        )
    for contact_id, indexes in pieces_by_contact.items():
        if indexes != set(range(len(indexes))):
            raise BoardPackageError(
                f"contact {contact_id} pieces must be indexed contiguously from 0"
            )
    return contacts, parsed


def _current_display_paths(
    geometry: Mapping[str, Any], width: int, height: int
) -> dict[tuple[str, int], ClosedPath]:
    return {
        (contact_id, index): display_path_for_shape(
            piece["frame"], piece["shape"], width, height,
            label=f"contact {_piece_key(contact_id, index)}",
        )
        for contact_id, pieces in geometry.items()
        for index, piece in enumerate(pieces)
    }


def _parse_shape_constraint(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _exact_keys(value, {"shape", "rotationDegrees"}, label)
    shape = value["shape"]
    if shape not in _SHAPE_CONSTRAINTS:
        raise BoardPackageError(f"{label}.shape is unsupported")
    rotation = value["rotationDegrees"]
    if (
        isinstance(rotation, bool) or not isinstance(rotation, (int, float))
        or not math.isfinite(rotation) or not -180 <= rotation < 180
    ):
        raise BoardPackageError(
            f"{label}.rotationDegrees must be finite and in [-180, 180)"
        )
    return {"shape": shape, "rotationDegrees": float(rotation)}


def _parse_command_indexes(
    value: object,
    label: str,
    path: ClosedPath,
    constraint: Mapping[str, object] | None,
    *,
    bendable: bool,
) -> tuple[int, ...]:
    if constraint is not None:
        raise BoardPackageError(f"{label} cannot be used with a shapeConstraint")
    if not isinstance(value, list) or any(
        isinstance(index, bool) or not isinstance(index, int) or index < 0
        for index in value
    ):
        raise BoardPackageError(f"{label} must contain non-negative integers")
    if len(value) != len(set(value)):
        raise BoardPackageError(f"{label} must not contain duplicates")
    for index in value:
        if bendable:
            valid = index < len(path.commands) and path.commands[index][0] == "C"
        else:
            valid = (
                0 < index < len(path.commands) - 1
                and path.commands[index][0] in {"Q", "C"}
                and path.commands[index + 1][0] in {"Q", "C"}
            )
        if not valid:
            raise BoardPackageError(f"{label} selects an unsupported path command")
    return tuple(value)


def _bendable_command_indexes(piece: Mapping[str, Any]) -> list[int]:
    if "shapeConstraint" in piece:
        return []
    shape = piece.get("shape")
    commands = shape.get("commands") if isinstance(shape, Mapping) else None
    if not isinstance(commands, list):
        return []
    return [
        index for index, command in enumerate(commands)
        if isinstance(command, Mapping) and command.get("command") == "curve"
        and command.get("bendable") is True
    ]


def _smooth_anchor_indexes(piece: Mapping[str, Any]) -> list[int]:
    if "shapeConstraint" in piece:
        return []
    shape = piece.get("shape")
    commands = shape.get("commands") if isinstance(shape, Mapping) else None
    if not isinstance(commands, list):
        return []
    return [
        index for index, command in enumerate(commands)
        if isinstance(command, Mapping) and command.get("smooth") is True
    ]


def _apply_bendable_command_indexes(piece: dict[str, Any], indexes: tuple[int, ...]) -> None:
    shape = piece.get("shape")
    commands = shape.get("commands") if isinstance(shape, Mapping) else None
    if not isinstance(commands, list):
        if indexes:
            raise BoardPackageError("bendable indexes require path geometry")
        return
    for command in commands:
        command.pop("bendable", None)
    for index in indexes:
        commands[index]["bendable"] = True


def _apply_smooth_anchor_indexes(piece: dict[str, Any], indexes: tuple[int, ...]) -> None:
    shape = piece.get("shape")
    commands = shape.get("commands") if isinstance(shape, Mapping) else None
    if not isinstance(commands, list):
        if indexes:
            raise BoardPackageError("smooth indexes require path geometry")
        return
    for command in commands:
        command.pop("smooth", None)
    for index in indexes:
        commands[index]["smooth"] = True


def _replace_optional(target: dict[str, Any], key: str, value: Any | None) -> None:
    if value is None:
        target.pop(key, None)
    else:
        target[key] = _copy_json(value)


def _piece_key(contact_id: str, piece_index: int) -> str:
    return f"{contact_id}-piece-{piece_index}"


@contextmanager
def _library_lock(root: Path, *, shared: bool = False) -> Iterator[None]:
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        raise BoardPackageError("safe workbench lock opening is unavailable")
    try:
        descriptor = os.open(root / ".workbench.lock", os.O_CREAT | os.O_RDWR | no_follow, 0o600)
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
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise BoardPackageError(f"{label} is invalid JSON") from error
    if not isinstance(value, dict):
        raise BoardPackageError(f"{label} must be an object")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, allow_nan=False))


def _rounded_json(value: object) -> object:
    if isinstance(value, float):
        return round(value, 12)
    if isinstance(value, list):
        return [_rounded_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _rounded_json(item) for key, item in value.items()}
    return value


def _json_values_are_exactly_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(
            _json_values_are_exactly_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _json_values_are_exactly_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def _required_and_allowed_keys(
    value: Mapping[str, Any], required: set[str], allowed: set[str], label: str
) -> None:
    unknown = set(value) - allowed
    missing = required - set(value)
    if unknown or missing:
        details: list[str] = []
        if unknown:
            details.append(f"unknown keys: {sorted(unknown)}")
        if missing:
            details.append(f"missing keys: {sorted(missing)}")
        raise BoardPackageError(f"{label} has " + "; ".join(details))


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    _required_and_allowed_keys(value, expected, expected, label)


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise BoardPackageError(f"{label} must be identifier-shaped")
    return value


def _slug(value: object) -> str:
    if not isinstance(value, str) or not _SLUG.fullmatch(value):
        raise BoardPackageError("board package path must be a single board slug")
    return value


def _png_header_dimensions(path: Path) -> tuple[int, int]:
    try:
        return _png_header_dimensions_from_bytes(path.read_bytes()[:33])
    except OSError as error:
        raise BoardPackageError("package image is not readable") from error


def _png_header_dimensions_from_bytes(data: bytes) -> tuple[int, int]:
    if len(data) != 33 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise BoardPackageError("package image must be a decodable PNG")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width <= 0 or height <= 0:
        raise BoardPackageError("package image must be a decodable PNG")
    return width, height


def _png_dimensions(path: Path) -> tuple[int, int]:
    try:
        return _catalog()._validate_png_structure(path, path.name)
    except (OSError, ValueError) as error:
        raise BoardPackageError(str(error)) from error


def _png_dimensions_from_bytes(data: bytes) -> tuple[int, int]:
    with tempfile.NamedTemporaryFile(suffix=".png") as image:
        image.write(data)
        image.flush()
        return _png_dimensions(Path(image.name))
