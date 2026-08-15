"""Direct, single-file hangboard packages owned by Hangboard Workbench."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
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
    parse_closed_path,
    shape_for_path,
    union_normalized_frames,
)


_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:[a-z0-9._-]*[a-z0-9])?$")
_SLUG = re.compile(r"^[a-z0-9]+(?:[a-z0-9-]*[a-z0-9])?$")
_BOARD_FIELDS = frozenset(
    {
        "schemaVersion",
        "id",
        "manufacturer",
        "name",
        "subtitle",
        "productURL",
        "dimensions",
        "aspectRatio",
        "presentation",
        "holds",
    }
)
_HOLD_REQUIRED_FIELDS = frozenset({"id", "name", "kind", "geometry"})
_HOLD_OPTIONAL_FIELDS = frozenset(
    {
        "sizeMillimeters",
        "depthRangeMillimeters",
        "gripType",
        "fingerCapacity",
        "features",
    }
)
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
        "twoFingerPocket",
        "threeFingerPocket",
        "fourFingerPocket",
        "fourFingerFlatEdge",
        "fourFingerIncutEdge",
        "largeOpenHandRail",
        "deepTwoFingerPocket",
        "thinCrimp",
        "shallowThreeFingerSlot",
        "widePinch",
        "mediumPinch",
        "smallPinch",
    }
)
_TREATMENT_TYPES = frozenset({"surface", "shelf", "recess"})
_RECESS_DEPTHS = frozenset({"shallow", "deep"})
_FRAME_EDGE_TOLERANCE = 0.0000005


class BoardPackageError(ValueError):
    """Raised for invalid or unsafe direct board-package operations."""


@dataclass(frozen=True, slots=True)
class BoardPackage:
    root: Path
    board: dict[str, Any]

    @property
    def board_id(self) -> str:
        return self.board["id"]

    @property
    def hold_ids(self) -> tuple[str, ...]:
        return tuple(hold["id"] for hold in self.board["holds"])

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


def discover_packages(
    library_root: Path, *, final_inventory: bool = False
) -> tuple[BoardPackage, ...]:
    """Discover validated completed packages among the library's direct children."""
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
            raise BoardPackageError("board is not available")
        return package


def load_board_package(package_root: Path) -> BoardPackage:
    """Load one completed package without accepting links or extra files."""
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
            "board package must contain only board.json and assets/primary.png"
        )
    assets = root / "assets"
    if not assets.is_dir() or assets.is_symlink():
        raise BoardPackageError(
            "board package must contain only board.json and assets/primary.png"
        )
    if {item.name for item in assets.iterdir()} != {"primary.png"}:
        raise BoardPackageError(
            "board package must contain only board.json and assets/primary.png"
        )
    image = assets / "primary.png"
    if not image.is_file() or image.is_symlink():
        raise BoardPackageError("package primary image is missing")
    width, height = _png_dimensions(image)
    board = _load_json(root / "board.json", "board.json")
    _validate_board(board, width, height)
    return BoardPackage(root, board)


def primary_image_path(package: BoardPackage) -> Path:
    """Return the one canonical package image after confinement validation."""
    image = package.root / "assets" / "primary.png"
    if not image.is_file() or image.is_symlink():
        raise BoardPackageError("package primary image is missing")
    _png_dimensions(image)
    return image


def editor_document(package: BoardPackage) -> dict[str, object]:
    """Expose every geometry piece as an independently keyed editable region."""
    width, height = _png_dimensions(primary_image_path(package))
    regions: list[dict[str, object]] = []
    region_id = 1
    for hold in package.board["holds"]:
        hold_id = hold["id"]
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
            except (GeometryError, KeyError, TypeError) as error:
                raise BoardPackageError(f"hold {key} has invalid geometry") from error
            regions.append(
                {
                    "id": region_id,
                    "key": key,
                    "type": hold["kind"],
                    "displayPath": path.data,
                    "metadata": {"holdID": hold_id, "pieceIndex": piece_index},
                }
            )
            region_id += 1
    return {
        "schemaVersion": 1,
        "canvas": {"width": width, "height": height},
        "regions": regions,
    }


def save_editor_document(
    library_root: Path, slug: str, document: Mapping[str, Any]
) -> BoardPackage:
    """Atomically save edited piece paths back into the package's board.json."""
    root = _library_root(library_root)
    slug = _slug(slug)
    with _library_lock(root):
        inventory = _discover_packages_unlocked(root)
        live = next(
            (package for package in inventory if package.root.name == slug), None
        )
        if live is None:
            raise BoardPackageError("board package is not available")
        width, height = _png_dimensions(primary_image_path(live))
        parsed_regions = _validate_editor_document(document, live, width, height)
        changes: list[tuple[str, int, Any]] = []
        for hold in live.board["holds"]:
            hold_id = hold["id"]
            for piece_index, piece in enumerate(hold["geometry"]):
                key = _piece_key(hold_id, piece_index)
                current = display_path_for_shape(
                    piece["frame"], piece["shape"], width, height, label=f"hold {key}"
                )
                edited = parsed_regions[key]
                if edited.data != current.data:
                    changes.append((hold_id, piece_index, edited))
        if not changes:
            return live

        candidate_parent = Path(tempfile.mkdtemp(prefix=".workbench-edit-", dir=root))
        candidate = candidate_parent / slug
        try:
            shutil.copytree(live.root, candidate)
            board_path = candidate / "board.json"
            board = _load_json(board_path, "board.json")
            holds = {hold["id"]: hold for hold in board["holds"]}
            for hold_id, piece_index, path in changes:
                frame, shape = shape_for_path(path, width, height)
                piece = holds[hold_id]["geometry"][piece_index]
                piece["frame"] = frame.to_json()
                piece["shape"] = _rounded_json(shape)
            _write_json(board_path, board)
            load_board_package(candidate)
            _replace_package_locked(root, slug, candidate, inventory=inventory)
            return load_board_package(root / slug)
        finally:
            shutil.rmtree(candidate_parent, ignore_errors=True)


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
        if child.is_symlink():
            raise BoardPackageError("board library direct children must not be symlinks")
        if not child.is_dir():
            raise BoardPackageError("board library must contain only direct child directories")
        _slug(child.name)
        names = {item.name for item in child.iterdir()}
        if "board.json" in names:
            packages.append(load_board_package(child))
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
            package.board["manufacturer"].casefold(),
            package.board["manufacturer"],
            package.board["name"].casefold(),
            package.board["name"],
            package.board_id.casefold(),
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
    _png_dimensions(image)
    return True


def _replace_package_locked(
    root: Path,
    slug: str,
    candidate_root: Path,
    *,
    inventory: tuple[BoardPackage, ...] | None = None,
) -> None:
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
        load_board_package(staged_package)
        _replace_transaction(root, slug, staged_package, stage)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _replace_transaction(
    root: Path, slug: str, staged_package: Path, stage: Path
) -> None:
    live_package = root / slug
    backup = stage / ".previous"
    moved_live = False
    installed = False
    try:
        if live_package.exists():
            if live_package.is_symlink() or not live_package.is_dir():
                raise BoardPackageError("existing board package is unsafe")
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
            if moved_live and backup.exists():
                os.replace(backup, live_package)
        except OSError as restore_error:
            raise BoardPackageError(
                "could not restore the previous board package"
            ) from restore_error
        raise BoardPackageError("could not save board package") from error
    if moved_live:
        shutil.rmtree(backup)


def _validate_board(board: Mapping[str, Any], width: int, height: int) -> None:
    _exact_keys(board, _BOARD_FIELDS, "board.json")
    _schema_version_one(board.get("schemaVersion"), "board.json.schemaVersion")
    _identifier(board.get("id"), "board.json.id")
    for field in ("manufacturer", "name", "subtitle", "dimensions"):
        _non_empty_string(board.get(field), f"board.json.{field}")
    _https_url(board.get("productURL"), "board.json.productURL")
    _positive_number(board.get("aspectRatio"), "board.json.aspectRatio")
    presentation = board.get("presentation")
    if presentation != {"assetPath": "assets/primary.png"}:
        raise BoardPackageError(
            "board.json.presentation must declare assets/primary.png"
        )
    holds = board.get("holds")
    if not isinstance(holds, list) or not holds:
        raise BoardPackageError("board.json.holds must be a non-empty array")
    identifiers: set[str] = set()
    for index, hold in enumerate(holds):
        label = f"board.json.holds[{index}]"
        if not isinstance(hold, Mapping):
            raise BoardPackageError(f"{label} must be an object")
        _required_and_allowed_keys(
            hold,
            _HOLD_REQUIRED_FIELDS,
            _HOLD_REQUIRED_FIELDS | _HOLD_OPTIONAL_FIELDS,
            label,
        )
        hold_id = _identifier(hold.get("id"), f"{label}.id")
        if hold_id in identifiers:
            raise BoardPackageError("duplicate hold ID")
        identifiers.add(hold_id)
        _non_empty_string(hold.get("name"), f"{label}.name")
        _enum(hold.get("kind"), _HOLD_KINDS, f"{label}.kind")
        geometry = hold.get("geometry")
        if not isinstance(geometry, list) or not geometry:
            raise BoardPackageError(f"{label}.geometry must be non-empty")
        for piece_index, piece in enumerate(geometry):
            _validate_piece(
                piece,
                width,
                height,
                f"{label}.geometry[{piece_index}]",
            )
        if "sizeMillimeters" in hold:
            _positive_integer(hold["sizeMillimeters"], f"{label}.sizeMillimeters")
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


def _validate_piece(piece: object, width: int, height: int, label: str) -> None:
    if not isinstance(piece, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _required_and_allowed_keys(
        piece, {"frame", "shape"}, {"frame", "shape", "treatment"}, label
    )
    try:
        frame = NormalizedFrame.from_json(piece["frame"], f"{label}.frame")
        display_path_for_shape(
            piece["frame"], piece["shape"], width, height, label=label
        )
    except (GeometryError, KeyError, TypeError) as error:
        raise BoardPackageError(str(error)) from error
    if not _shape_fills_declared_frame(piece["shape"]):
        raise BoardPackageError(f"{label}.frame must match its derived shape bounds")
    if "treatment" in piece:
        _validate_treatment(piece["treatment"], f"{label}.treatment")
    # Constructing the frame above is part of the validation contract.
    _ = frame


def _shape_fills_declared_frame(shape: object) -> bool:
    if not isinstance(shape, Mapping) or shape.get("type") == "roundedRect":
        return True
    if shape.get("type") != "path" or not isinstance(shape.get("commands"), list):
        return False
    points: list[list[object]] = []
    for command in shape["commands"]:
        if not isinstance(command, Mapping):
            return False
        points.extend(value for key, value in command.items() if key != "command")
    if not points:
        return False
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return (
        min(xs) <= _FRAME_EDGE_TOLERANCE
        and min(ys) <= _FRAME_EDGE_TOLERANCE
        and max(xs) >= 1 - _FRAME_EDGE_TOLERANCE
        and max(ys) >= 1 - _FRAME_EDGE_TOLERANCE
    )


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


def _validate_editor_document(
    document: Mapping[str, Any], package: BoardPackage, width: int, height: int
) -> dict[str, Any]:
    if not isinstance(document, Mapping):
        raise BoardPackageError("editor document must be an object")
    _exact_keys(document, {"schemaVersion", "canvas", "regions"}, "editor document")
    _schema_version_one(document.get("schemaVersion"), "editor document.schemaVersion")
    if document.get("canvas") != {"width": width, "height": height}:
        raise BoardPackageError("editor document canvas does not match the primary image")
    regions = document.get("regions")
    if not isinstance(regions, list):
        raise BoardPackageError("editor document regions must be an array")

    expected: dict[str, tuple[int, str, dict[str, object]]] = {}
    region_id = 1
    for hold in package.board["holds"]:
        for piece_index, _piece in enumerate(hold["geometry"]):
            key = _piece_key(hold["id"], piece_index)
            expected[key] = (
                region_id,
                hold["kind"],
                {"holdID": hold["id"], "pieceIndex": piece_index},
            )
            region_id += 1

    parsed: dict[str, Any] = {}
    for region in regions:
        if not isinstance(region, Mapping):
            raise BoardPackageError("editor document contains an invalid hold piece")
        _exact_keys(
            region,
            {"id", "key", "type", "displayPath", "metadata"},
            "editor region",
        )
        key = region.get("key")
        if not isinstance(key, str) or key not in expected:
            raise BoardPackageError("editor document contains an unknown hold piece")
        if key in parsed:
            raise BoardPackageError("duplicate hold piece key")
        expected_id, expected_type, expected_metadata = expected[key]
        if (
            region.get("id") != expected_id
            or region.get("type") != expected_type
            or region.get("metadata") != expected_metadata
        ):
            raise BoardPackageError(f"editor region {key} metadata does not match its hold piece")
        try:
            parsed[key] = parse_closed_path(
                region.get("displayPath"), width, height, label=f"hold {key}"
            )
        except GeometryError as error:
            raise BoardPackageError(str(error)) from error
    if set(parsed) != set(expected):
        raise BoardPackageError(
            "editor document hold pieces must exactly match board geometry"
        )
    return parsed


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


def _schema_version_one(value: object, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value != 1:
        raise BoardPackageError(f"{label} must be 1")


def _positive_number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise BoardPackageError(f"{label} must be a positive finite number")
    return float(value)


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BoardPackageError(f"{label} must be a positive integer")
    return value


def _millimeter_range(value: object, label: str) -> None:
    if not isinstance(value, Mapping):
        raise BoardPackageError(f"{label} must be an object")
    _exact_keys(value, {"lowerBound", "upperBound"}, label)
    lower = _positive_integer(value.get("lowerBound"), f"{label}.lowerBound")
    upper = _positive_integer(value.get("upperBound"), f"{label}.upperBound")
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


def _slug(value: object) -> str:
    if not isinstance(value, str) or not _SLUG.fullmatch(value):
        raise BoardPackageError("board package path must be a single board slug")
    return value


def _reject_symlinks(root: Path) -> None:
    if root.is_symlink() or any(item.is_symlink() for item in root.rglob("*")):
        raise BoardPackageError("board package must not contain symlinks")


def _png_dimensions(path: Path) -> tuple[int, int]:
    try:
        header = path.read_bytes()[:24]
    except OSError as error:
        raise BoardPackageError("package primary image is not readable") from error
    if (
        len(header) < 24
        or header[:8] != b"\x89PNG\r\n\x1a\n"
        or header[12:16] != b"IHDR"
    ):
        raise BoardPackageError("package primary image must be a PNG")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    if width <= 0 or height <= 0:
        raise BoardPackageError("package primary image has invalid dimensions")
    return width, height
