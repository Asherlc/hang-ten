"""Repository-confined discovery of canonical hangboard packages."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tempfile

from .board_artwork import BoardHoldPieceDocument
from .board_catalog import BoardHold, BoardPackage, load_board_package, load_catalog
from .generic_stage0 import StageCheckpoint
from .onboarding_run import RunContext, approve_stage, resume_run, start_run


_BOARD_ID = re.compile(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z")
_DIAGNOSTIC_CODES = {
    "invalid_path",
    "invalid_board_id",
    "missing_manifest",
    "identity_mismatch",
    "invalid_run",
    "invalid_outputs",
}


@dataclass(frozen=True, slots=True)
class LibraryBoard:
    board_id: str
    display_name: str
    run_path: Path
    revision_token: str


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
        self._pieces = package.artwork.hold_pieces

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
                    "regionCount": len(self._holds),
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
                    "regionCount": len(self._holds),
                    "vectorRegions": {"fileSha256": self._hash(regions)},
                    "vectorSvg": {"fileSha256": self._hash(svg)},
                }
            )
        else:
            candidate["regionCount"] = len(self._holds)
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
                                for piece in self._pieces
                                if piece.hold_id == hold.id
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
        holds = {hold.id: hold for hold in self._holds}
        regions = [
            {
                "id": index,
                "key": piece.hold_id,
                "type": holds[piece.hold_id].kind,
                "pieceIndex": 0,
                "displayPath": self._piece_path(piece, width, height),
                "anchor": [
                    (
                        holds[piece.hold_id].frame.x
                        + holds[piece.hold_id].frame.width / 2
                    )
                    * width,
                    (
                        holds[piece.hold_id].frame.y
                        + holds[piece.hold_id].frame.height / 2
                    )
                    * height,
                ],
                "bounds": [
                    holds[piece.hold_id].frame.x * width,
                    holds[piece.hold_id].frame.y * height,
                    (
                        holds[piece.hold_id].frame.x
                        + holds[piece.hold_id].frame.width
                    )
                    * width,
                    (
                        holds[piece.hold_id].frame.y
                        + holds[piece.hold_id].frame.height
                    )
                    * height,
                ],
                "metadata": self._runtime_metadata(holds[piece.hold_id]),
                "symmetry": {},
            }
            for index, piece in enumerate(self._pieces, start=1)
        ]
        return {
            "schemaVersion": 1,
            "stage": stage,
            "canvas": {"width": width, "height": height},
            "regions": regions,
            "silhouettePaths": [
                {
                    "pieceIndex": 0,
                    "displayPath": (
                        f"M 0 0 L {width} 0 L {width} {height} "
                        f"L 0 {height} Z"
                    ),
                }
            ],
        }

    @staticmethod
    def _runtime_metadata(hold: BoardHold) -> dict[str, object]:
        metadata: dict[str, object] = {}
        if hold.kind in {"edge", "pocket"} and hold.size_millimeters is not None:
            metadata["depthMm"] = hold.size_millimeters
        if hold.kind == "pocket":
            metadata["fingerCount"] = hold.finger_capacity
        if hold.kind == "sloper":
            metadata["profile"] = (
                "round" if "roundSloper" in hold.features else "flat"
            )
        return metadata

    @staticmethod
    def _piece_path(
        piece: BoardHoldPieceDocument, width: int = 1, height: int = 1
    ) -> str:
        frame, shape = piece.frame, piece.shape
        x, y = frame.x * width, frame.y * height
        w, h = frame.width * width, frame.height * height
        if shape.type == "roundedRect":
            return f"M {x} {y} L {x+w} {y} L {x+w} {y+h} L {x} {y+h} Z"
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
    """Discover canonical board packages from the repository registry."""

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
        catalog_path = self._boards_root / "catalog.json"
        if not catalog_path.is_file() or catalog_path.is_symlink():
            diagnostic = LibraryDiagnostic(
                "catalog.json",
                "missing_manifest",
                "Hangboards/catalog.json: canonical catalog is missing",
            )
            return LibrarySnapshot((), (diagnostic,))
        try:
            catalog = load_catalog(catalog_path)
        except (OSError, ValueError) as error:
            diagnostic = LibraryDiagnostic(
                "catalog.json",
                "invalid_run",
                f"Hangboards/catalog.json: {error}",
            )
            return LibrarySnapshot((), (diagnostic,))
        boards: list[LibraryBoard] = []
        diagnostics: list[LibraryDiagnostic] = []
        for catalog_entry in catalog.entries:
            if not self._valid_package_slug(catalog_entry.path):
                diagnostics.append(
                    LibraryDiagnostic(
                        catalog_entry.path,
                        "invalid_path",
                        "catalog package path must be one relative directory slug",
                    )
                )
                continue
            entry = self._boards_root / catalog_entry.path
            try:
                board = self._read_board(entry)
                if board.board_id != catalog_entry.id:
                    raise _BoardDiagnosticError(
                        "identity_mismatch",
                        f"Hangboards/{catalog_entry.path}: "
                        "package id does not match catalog id",
                    )
                boards.append(board)
            except _BoardDiagnosticError as error:
                diagnostics.append(
                    LibraryDiagnostic(
                        catalog_entry.path, error.code, error.message
                    )
                )
        boards.sort(key=lambda board: (board.display_name.casefold(), board.board_id))
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

    def _read_board(self, package_root: Path) -> LibraryBoard:
        if package_root.is_symlink() or not package_root.is_dir():
            raise _BoardDiagnosticError(
                "invalid_path",
                f"Hangboards/{package_root.name}: "
                "must be a non-symlink directory",
            )
        if not _BOARD_ID.fullmatch(package_root.name):
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
        )

    def _materialize_package_run(self, board: LibraryBoard, destination: Path) -> None:
        package = load_board_package(board.run_path)
        manifest = json.loads(
            (board.run_path / "board.json").read_text(encoding="utf-8")
        )
        presentation = manifest["presentation"]
        asset_path = presentation.get("assetPath")
        if asset_path is None:
            asset_path = presentation["photoAsset"]["path"]
        asset = (board.run_path / asset_path).resolve(strict=True)
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
        if not isinstance(value, str) or not _BOARD_ID.fullmatch(value):
            raise BoardLibraryError("board identifier is invalid")
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
            and bool(_BOARD_ID.fullmatch(value))
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
