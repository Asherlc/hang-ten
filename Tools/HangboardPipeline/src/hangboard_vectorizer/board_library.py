"""Repository-confined discovery of canonical hangboard packages."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Iterator

from .board_artwork import BoardShapeDocument, NormalizedFrame
from .board_catalog import (
    BoardGeometryPiece,
    BoardHold,
    BoardPackage,
    is_board_identifier,
    is_board_package_slug,
    is_primary_only_draft,
    load_board_package,
)
from .generic_stage0 import StageCheckpoint
from .onboarding_run import RunContext, approve_stage, resume_run, start_run


_DIAGNOSTIC_CODES = {
    "invalid_path",
    "invalid_board_id",
    "missing_manifest",
    "identity_mismatch",
    "invalid_run",
    "invalid_outputs",
}


@contextmanager
def package_library_lock(
    hangboards_root: Path, *, exclusive: bool
) -> Iterator[None]:
    """Coordinate cooperating readers and writers on the stable root inode."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(hangboards_root, flags)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


@dataclass(frozen=True, slots=True)
class LibraryBoard:
    board_id: str
    display_name: str
    run_path: Path
    revision_token: str
    status: str
    sort_key: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LibraryDiagnostic:
    path: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class LibrarySnapshot:
    boards: tuple[LibraryBoard, ...]
    diagnostics: tuple[LibraryDiagnostic, ...]


class _CanonicalPackageRunner:
    """Materialize a canonical package as an immutable completed onboarding run."""

    def __init__(self, stage: int, asset: Path, package: BoardPackage) -> None:
        self.stage = stage
        self._asset = asset
        self._package = package
        self._holds = package.board.holds
        self._pieces = tuple(
            (hold, piece_index, piece)
            for hold in package.board.holds
            for piece_index, piece in enumerate(hold.geometry)
        )

    def run(self, context: RunContext, artifact_root: Path) -> StageCheckpoint:
        artifact_root.mkdir(parents=True)
        review = artifact_root / f"stage-{self.stage}-review.png"
        shutil.copy2(self._asset, review)
        candidate: dict[str, object] = {"profile": {}, "stage": self.stage}
        if self.stage == 0:
            candidate["registered"] = {}
        else:
            prior = context.manifest["stages"][-1]
            candidate["inputAcceptance"] = {
                "path": prior["acceptancePath"],
                "sha256": prior["acceptanceSha256"],
            }
            self._write_stage(candidate, artifact_root)
        candidate_path = artifact_root / f"stage-{self.stage}-candidate.json"
        self._write_json(candidate_path, candidate)
        hashes = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in sorted(artifact_root.iterdir())
            if path.is_file()
        }
        self._write_json(artifact_root / "candidate-hashes.json", hashes)
        return StageCheckpoint(self.stage, artifact_root, hashes, review, True)

    def _write_stage(self, candidate: dict[str, object], root: Path) -> None:
        if self.stage == 1:
            registered = root / "stage-1-auto-rgba.png"
            shutil.copy2(self._asset, registered)
            candidate["registered"] = {"fileSha256": self._hash(registered)}
        elif self.stage == 2:
            regions = root / "stage-2-regions.json"
            self._write_json(regions, self._region_document(stage=2))
            labels = root / "stage-2-labels.png"
            shutil.copy2(self._asset, labels)
            candidate.update(
                {
                    "regionCount": len(self._pieces),
                    "regions": {"fileSha256": self._hash(regions)},
                    "registered": {"fileSha256": self._hash(labels)},
                }
            )
        elif self.stage == 3:
            regions = root / "stage-3-vector-regions.json"
            document = self._region_document(stage=3)
            self._write_json(regions, document)
            svg = root / "stage-3-vector.svg"
            svg.write_text(self._selectable_svg(document), encoding="utf-8")
            candidate.update(
                {
                    "regionCount": len(self._pieces),
                    "vectorRegions": {"fileSha256": self._hash(regions)},
                    "vectorSvg": {"fileSha256": self._hash(svg)},
                }
            )
        else:
            candidate["regionCount"] = len(self._pieces)
            files = {
                "normal": root / "stage-4-normal.png",
                "productSvg": root / "stage-4-product.svg",
                "manifest": root / "stage-4-manifest.json",
                "highlights": root / "stage-4-highlights.json",
            }
            shutil.copy2(self._asset, files["normal"])
            document = self._region_document(stage=3)
            files["productSvg"].write_text(
                self._selectable_svg(document), encoding="utf-8"
            )
            self._write_json(files["manifest"], self._region_document(stage=4))
            self._write_json(
                files["highlights"],
                {
                    "schemaVersion": 1,
                    "holds": [
                        {
                            "holdID": hold.id,
                            "displayPaths": [
                                self._piece_path(piece)
                                for owner, _piece_index, piece in self._pieces
                                if owner.id == hold.id
                            ],
                        }
                        for hold in self._holds
                    ],
                },
            )
            for key, path in files.items():
                candidate[key] = {"fileSha256": self._hash(path)}

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    @staticmethod
    def _hash(path: Path) -> str:
        return sha256(path.read_bytes()).hexdigest()

    def _region_document(self, *, stage: int) -> dict[str, object]:
        from PIL import Image

        with Image.open(self._asset) as image:
            width, height = image.size
        regions = [
            {
                "id": index,
                "key": self._region_key(hold, piece_index),
                "type": hold.kind,
                "pieceIndex": piece_index,
                "displayPath": self._piece_path(piece, width, height),
                "anchor": [
                    (
                        piece.frame.x
                        + piece.frame.width / 2
                    )
                    * width,
                    (
                        piece.frame.y
                        + piece.frame.height / 2
                    )
                    * height,
                ],
                "bounds": [
                    piece.frame.x * width,
                    piece.frame.y * height,
                    (
                        piece.frame.x
                        + piece.frame.width
                    )
                    * width,
                    (
                        piece.frame.y
                        + piece.frame.height
                    )
                    * height,
                ],
                "metadata": self._runtime_metadata(hold),
                "symmetry": {},
            }
            for index, (hold, piece_index, piece) in enumerate(self._pieces, start=1)
        ]
        return {
            "schemaVersion": 1,
            "stage": stage,
            "canvas": {"width": width, "height": height},
            "regions": regions,
            "silhouettePaths": [
                {
                    "pieceIndex": 0,
                    "displayPath": self._shape_path(
                        NormalizedFrame(0, 0, 1, 1),
                        BoardShapeDocument("roundedRect", corner_radius_fraction=0),
                        width,
                        height,
                    ),
                }
            ],
        }

    @staticmethod
    def _runtime_metadata(hold: BoardHold) -> dict[str, object]:
        metadata: dict[str, object] = {"holdID": hold.id}
        if hold.kind in {"edge", "pocket"} and hold.size_millimeters is not None:
            metadata["depthMm"] = hold.size_millimeters
        if hold.kind == "pocket":
            if hold.finger_capacity is not None:
                metadata["fingerCount"] = hold.finger_capacity
        if hold.kind == "sloper":
            metadata["profile"] = (
                "round" if "roundSloper" in (hold.features or ()) else "flat"
            )
        return metadata

    @staticmethod
    def _region_key(hold: BoardHold, piece_index: int) -> str:
        if len(hold.geometry) == 1:
            return hold.id
        return f"{hold.id}::piece:{piece_index + 1}"

    @staticmethod
    def _piece_path(
        piece: BoardGeometryPiece, width: int = 1, height: int = 1
    ) -> str:
        return _CanonicalPackageRunner._shape_path(
            piece.frame, piece.shape, width, height
        )

    @staticmethod
    def _shape_path(
        frame: NormalizedFrame,
        shape: BoardShapeDocument,
        width: int,
        height: int,
    ) -> str:
        x, y = frame.x * width, frame.y * height
        w, h = frame.width * width, frame.height * height
        if shape.type == "roundedRect":
            radius = min(w, h) * (shape.corner_radius_fraction or 0)
            return (
                f"M {x + radius} {y} L {x + w - radius} {y} "
                f"Q {x + w} {y} {x + w} {y + radius} "
                f"L {x + w} {y + h - radius} "
                f"Q {x + w} {y + h} {x + w - radius} {y + h} "
                f"L {x + radius} {y + h} "
                f"Q {x} {y + h} {x} {y + h - radius} "
                f"L {x} {y + radius} Q {x} {y} {x + radius} {y} Z"
            )
        commands = []
        for command in shape.commands:
            values = {
                "move": "M",
                "line": "L",
                "quad": "Q",
                "curve": "C",
                "close": "Z",
            }
            if command.command == "close":
                commands.append("Z")
                continue
            points = []
            for point in (
                command.control1,
                command.control2,
                command.control,
                command.to,
            ):
                if point is not None:
                    points.extend((x + point[0] * w, y + point[1] * h))
            commands.append(
                values[command.command]
                + " "
                + " ".join(str(value) for value in points)
            )
        return " ".join(commands)

    @staticmethod
    def _selectable_svg(document: Mapping[str, object]) -> str:
        canvas = document["canvas"]
        paths = "".join(
            f'<path id="{region["key"]}" d="{region["displayPath"]}"/>'
            for region in document["regions"]
        )
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {canvas["width"]} {canvas["height"]}">'
            f"{paths}</svg>\n"
        )


class BoardLibraryError(ValueError):
    """Raised when a requested board or file operation is unsafe."""


class _BoardDiagnosticError(Exception):
    def __init__(self, code: str, message: str) -> None:
        if code not in _DIAGNOSTIC_CODES:
            raise ValueError(f"unknown board diagnostic code: {code}")
        super().__init__(message)
        self.code = code
        self.message = message


class RepositoryBoardLibrary:
    """Discover canonical board packages from direct Hangboards children."""

    def __init__(self, repository_root: Path) -> None:
        try:
            self._repository_root = Path(repository_root).resolve(strict=True)
        except OSError as error:
            raise BoardLibraryError("repository root is not accessible") from error
        if not self._repository_root.is_dir():
            raise BoardLibraryError("repository root is not a directory")
        self._boards_root = self._repository_root / "Hangboards"

    @property
    def repository_root(self) -> Path:
        return self._repository_root

    def snapshot(self) -> LibrarySnapshot:
        """Return all independently valid canonical packages and diagnostics."""
        if self._boards_root.is_symlink():
            diagnostic = LibraryDiagnostic(
                "Hangboards",
                "invalid_path",
                "Hangboards: must be a non-symlink directory",
            )
            return LibrarySnapshot((), (diagnostic,))
        if not self._boards_root.exists():
            return LibrarySnapshot((), ())
        if not self._boards_root.is_dir():
            diagnostic = LibraryDiagnostic(
                "Hangboards", "invalid_path", "Hangboards: must be a directory"
            )
            return LibrarySnapshot((), (diagnostic,))
        try:
            with package_library_lock(self._boards_root, exclusive=False):
                return self._snapshot_unlocked()
        except OSError as error:
            diagnostic = LibraryDiagnostic(
                "Hangboards",
                "invalid_path",
                f"Hangboards: directory is not safely readable: {error}",
            )
            return LibrarySnapshot((), (diagnostic,))

    def _snapshot_unlocked(self) -> LibrarySnapshot:
        """Inspect packages while the caller holds the shared library lock."""
        boards: list[LibraryBoard] = []
        diagnostics: list[LibraryDiagnostic] = []
        for entry in sorted(self._boards_root.iterdir(), key=lambda path: path.name):
            if entry.is_symlink():
                diagnostics.append(
                    LibraryDiagnostic(
                        entry.name,
                        "invalid_path",
                        f"Hangboards/{entry.name}: direct child must not be a symlink",
                    )
                )
                continue
            if not entry.is_dir():
                continue
            if not is_board_package_slug(entry.name):
                diagnostics.append(
                    LibraryDiagnostic(
                        entry.name,
                        "invalid_board_id",
                        f"Hangboards/{entry.name}: directory identifier is invalid",
                    )
                )
                continue
            board_path = entry / "board.json"
            if board_path.exists() or board_path.is_symlink():
                try:
                    boards.append(self._read_board(entry))
                except _BoardDiagnosticError as error:
                    diagnostics.append(
                        LibraryDiagnostic(entry.name, error.code, error.message)
                    )
                continue
            assets = entry / "assets"
            primary = assets / "primary.png"
            try:
                is_draft = is_primary_only_draft(entry)
                if not is_draft:
                    diagnostics.append(
                        LibraryDiagnostic(
                            entry.name,
                            "missing_manifest",
                            f"Hangboards/{entry.name}: directory is missing board.json",
                        )
                    )
                    continue
                revision_token = sha256(primary.read_bytes()).hexdigest()
            except (OSError, ValueError) as error:
                diagnostics.append(
                    LibraryDiagnostic(
                        entry.name,
                        "invalid_run",
                        f"Hangboards/{entry.name}: primary image is not readable: {error}",
                    )
                )
                continue
            else:
                boards.append(
                    LibraryBoard(
                        entry.name,
                        entry.name,
                        entry,
                        revision_token,
                        "draft",
                        (entry.name.casefold(), entry.name, entry.name),
                    )
                )
        published_by_id: dict[str, list[LibraryBoard]] = {}
        for board in boards:
            if board.status == "published":
                published_by_id.setdefault(board.board_id, []).append(board)
        duplicate_ids = {
            board_id
            for board_id, matches in published_by_id.items()
            if len(matches) > 1
        }
        if duplicate_ids:
            boards = [
                board
                for board in boards
                if board.status != "published" or board.board_id not in duplicate_ids
            ]
            for board_id in sorted(duplicate_ids):
                matches = published_by_id[board_id]
                slugs = ", ".join(sorted(board.run_path.name for board in matches))
                for board in matches:
                    diagnostics.append(
                        LibraryDiagnostic(
                            board.run_path.name,
                            "identity_mismatch",
                            f"Hangboards/{board.run_path.name}: duplicate board ID "
                            f"{board_id} is published by {slugs}",
                        )
                    )
        boards.sort(key=lambda board: board.sort_key)
        diagnostics.sort(key=lambda item: (item.path, item.code, item.message))
        return LibrarySnapshot(tuple(boards), tuple(diagnostics))

    def get_board(self, board_id: str) -> LibraryBoard:
        requested = self._board_id(board_id)
        for board in self.snapshot().boards:
            if board.board_id == requested:
                return board
        raise BoardLibraryError(f"board does not exist: {requested}")

    def copy_current_run(self, board_id: str, destination: Path) -> LibraryBoard:
        """Materialize a canonical package into a new editable runtime run."""
        board = self.get_board(board_id)
        if board.status != "published":
            raise BoardLibraryError(f"board is not published: {board.board_id}")
        destination = Path(destination)
        if ".." in destination.parts:
            raise BoardLibraryError(
                "destination must not contain parent-directory components"
            )
        destination = destination.absolute()
        if destination.exists() or destination.is_symlink():
            raise BoardLibraryError(f"destination already exists: {destination}")
        self._prepare_destination_parent(destination.parent)
        stage = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.tmp-", dir=destination.parent
            )
        )
        try:
            staged_run = stage / "run"
            self._materialize_package_run(board, staged_run)
            staged_run.replace(destination)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        else:
            shutil.rmtree(stage, ignore_errors=True)
        return board

    def copy_draft_source(self, board_id: str, destination: Path) -> LibraryBoard:
        """Copy the exact draft image through no-follow descriptors.

        Descriptor-relative traversal prevents a concurrent repository writer from
        replacing a validated directory or image with a symlink between discovery
        and materialization.
        """
        board = self.get_board(board_id)
        if board.status != "draft":
            raise BoardLibraryError(f"board is not a draft: {board.board_id}")
        destination = Path(destination)
        if destination.exists() or destination.is_symlink():
            raise BoardLibraryError(f"destination already exists: {destination}")
        if not destination.parent.is_dir():
            raise BoardLibraryError("destination parent does not exist")

        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        file_flags = os.O_RDONLY | os.O_NOFOLLOW
        descriptors: list[int] = []
        try:
            descriptors.append(os.open(self._repository_root, directory_flags))
            for component in ("Hangboards", board.run_path.name, "assets"):
                descriptors.append(
                    os.open(component, directory_flags, dir_fd=descriptors[-1])
                )
            source_fd = os.open("primary.png", file_flags, dir_fd=descriptors[-1])
            descriptors.append(source_fd)
            if not stat.S_ISREG(os.fstat(source_fd).st_mode):
                raise BoardLibraryError("draft primary image is not a regular file")
            destination_fd = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            descriptors.append(destination_fd)
            digest = sha256()
            with os.fdopen(os.dup(source_fd), "rb") as source, os.fdopen(
                os.dup(destination_fd), "wb"
            ) as target:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
                    target.write(chunk)
            if digest.hexdigest() != board.revision_token:
                raise BoardLibraryError("draft primary image changed while opening")
        except (OSError, ValueError) as error:
            destination.unlink(missing_ok=True)
            if isinstance(error, BoardLibraryError):
                raise
            raise BoardLibraryError("draft primary image is not safely readable") from error
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
        return board

    def _read_board(self, package_root: Path) -> LibraryBoard:
        if package_root.is_symlink() or not package_root.is_dir():
            raise _BoardDiagnosticError(
                "invalid_path",
                f"Hangboards/{package_root.name}: "
                "must be a non-symlink directory",
            )
        if not is_board_package_slug(package_root.name):
            raise _BoardDiagnosticError(
                "invalid_board_id",
                f"Hangboards/{package_root.name}: directory identifier is invalid",
            )
        if any(path.is_symlink() for path in package_root.rglob("*")):
            raise _BoardDiagnosticError(
                "invalid_path",
                f"Hangboards/{package_root.name}: "
                "symlinked package members are not allowed",
            )
        try:
            package = load_board_package(package_root)
            board_id = self._board_id(package.board.id)
            display_name = self._display_name(package.board.facts.get("name"))
        except (OSError, ValueError, BoardLibraryError) as error:
            code = (
                "missing_manifest"
                if not (package_root / "board.json").is_file()
                else "invalid_run"
            )
            raise _BoardDiagnosticError(
                code, f"Hangboards/{package_root.name}: {error}"
            ) from error
        return LibraryBoard(
            board_id,
            display_name,
            package_root,
            self._package_revision_token(package_root),
            "published",
            (
                package.board.manufacturer.casefold(),
                package.board.manufacturer,
                display_name.casefold(),
                display_name,
                board_id,
            ),
        )

    def _materialize_package_run(self, board: LibraryBoard, destination: Path) -> None:
        package = load_board_package(board.run_path)
        asset = (board.run_path / "assets" / "primary.png").resolve(strict=True)
        try:
            asset.relative_to(board.run_path.resolve())
        except ValueError as error:
            raise BoardLibraryError("board presentation asset escapes its package") from error
        runners = {
            stage: _CanonicalPackageRunner(stage, asset, package)
            for stage in range(5)
        }
        start_run(
            board.display_name,
            str(asset),
            destination,
            runners=runners,
            workspace_root=destination.parent,
        )
        for stage in range(5):
            approve_stage(destination, stage)
            if stage < 4:
                resume_run(destination, runners=runners)

    @staticmethod
    def _package_revision_token(package: Path) -> str:
        digest = sha256()
        for path in sorted(package.rglob("*")):
            if path.is_file():
                relative = path.relative_to(package).as_posix().encode("utf-8")
                digest.update(len(relative).to_bytes(8, "big"))
                digest.update(relative)
                digest.update(path.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _board_id(value: object) -> str:
        if not is_board_identifier(value):
            raise BoardLibraryError("board identifier is invalid")
        assert isinstance(value, str)
        return value

    @staticmethod
    def _display_name(value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise BoardLibraryError("board name is invalid")
        return value.strip()

    @staticmethod
    def _valid_package_slug(value: str) -> bool:
        path = Path(value)
        return (
            not path.is_absolute()
            and len(path.parts) == 1
            and path.parts[0] not in {".", ".."}
            and is_board_package_slug(value)
        )

    @staticmethod
    def _prepare_destination_parent(parent: Path) -> None:
        missing: list[Path] = []
        cursor = parent
        while not cursor.exists():
            missing.append(cursor)
            cursor = cursor.parent
        if cursor.is_symlink() or not cursor.is_dir():
            raise BoardLibraryError("destination parent is not a safe directory")
        for path in reversed(missing):
            path.mkdir()
        cursor = parent
        while True:
            if cursor.is_symlink() or not cursor.is_dir():
                raise BoardLibraryError("destination parent contains a symlink")
            if cursor == cursor.parent:
                break
            cursor = cursor.parent
