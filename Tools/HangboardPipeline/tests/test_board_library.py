from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from conftest import write_board_package
from hangboard_vectorizer import board_library
from hangboard_vectorizer.board_library import BoardLibraryError, RepositoryBoardLibrary
from hangboard_vectorizer.onboarding_run import read_status


FIXTURE = Path(__file__).resolve().parents[3] / "Hangboards" / "metolius-wood-grips-compact-ii"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_workbench_discovers_without_catalog_and_materializes_embedded_geometry(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    package = write_board_package(
        repository / "Hangboards" / "fixture-model",
        board_id="fixture.board",
        manufacturer="Fixture Maker",
        name="Fixture Board",
    )
    board_path = package / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    document["holds"][0]["geometry"] = [
        {
            "frame": {"x": 0.1, "y": 0.2, "width": 0.2, "height": 0.3},
            "shape": {
                "type": "path",
                "commands": [
                    {"command": "move", "to": [0, 0]},
                    {"command": "line", "to": [1, 0]},
                    {"command": "quad", "control": [1, 1], "to": [0, 1]},
                    {"command": "close"},
                ],
            },
        }
    ]
    board_path.write_text(json.dumps(document), encoding="utf-8")
    library = RepositoryBoardLibrary(repository)

    snapshot = library.snapshot()

    assert [(board.board_id, board.display_name, board.status) for board in snapshot.boards] == [
        ("fixture.board", "Fixture Board", "published")
    ]
    assert snapshot.diagnostics == ()

    destination = tmp_path / ".context" / "runtime" / "run"
    library.copy_current_run("fixture.board", destination)
    vector_path = next(destination.glob("stages/03/*/stage-3-vector-regions.json"))
    vector_document = json.loads(vector_path.read_text(encoding="utf-8"))
    assert vector_document["regions"][0]["key"] == "hold-left"
    assert " Q " in vector_document["regions"][0]["displayPath"]


def _repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    package = repository / "Hangboards" / FIXTURE.name
    package.parent.mkdir(parents=True)
    shutil.copytree(FIXTURE, package)
    (package.parent / "catalog.json").write_text(
        '{"schemaVersion":1,"boards":[{"id":"metolius.wood-grips-compact-ii","path":"metolius-wood-grips-compact-ii"}]}\n',
        encoding="utf-8",
    )
    return repository


def test_snapshot_discovers_canonical_packages(tmp_path: Path) -> None:
    library = RepositoryBoardLibrary(_repository(tmp_path))

    snapshot = library.snapshot()

    assert [(board.board_id, board.display_name) for board in snapshot.boards] == [
        ("metolius.wood-grips-compact-ii", "Wood Grips Compact II")
    ]
    assert [board.status for board in snapshot.boards] == ["published"]
    assert snapshot.diagnostics == ()
    assert len(snapshot.boards[0].revision_token) == 64


def test_repository_inventory_lists_published_and_draft_boards() -> None:
    snapshot = RepositoryBoardLibrary(REPOSITORY_ROOT).snapshot()
    board_directories = {
        path.name for path in (REPOSITORY_ROOT / "Hangboards").iterdir() if path.is_dir()
    }

    published = {board.run_path.name for board in snapshot.boards if board.status == "published"}
    drafts = {board.run_path.name for board in snapshot.boards if board.status == "draft"}

    assert published == {"metolius-wood-grips-compact-ii"}
    assert len(published) == 1
    assert len(drafts) == 32
    assert published.isdisjoint(drafts)
    assert published | drafts == board_directories


def test_snapshot_does_not_create_registry(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    assert RepositoryBoardLibrary(repository).snapshot() == board_library.LibrarySnapshot((), ())
    assert not (repository / "Hangboards").exists()


def test_snapshot_reports_invalid_package_without_hiding_valid_package(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    invalid = repository / "Hangboards" / "invalid-package"
    invalid.mkdir()
    catalog = repository / "Hangboards" / "catalog.json"
    document = json.loads(catalog.read_text(encoding="utf-8"))
    document["boards"].append({"id": "invalid-package", "path": "invalid-package"})
    catalog.write_text(json.dumps(document), encoding="utf-8")

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["metolius.wood-grips-compact-ii"]
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("invalid-package", "missing_manifest")
    ]
    assert "Hangboards/invalid-package" in snapshot.diagnostics[0].message


def test_snapshot_reports_unregistered_image_board_as_draft(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    candidate = repository / "Hangboards" / "beastmaker-1000" / "assets"
    candidate.mkdir(parents=True)
    (candidate / "primary.png").write_bytes(b"candidate image")

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert [(item.board_id, item.display_name, item.status) for item in snapshot.boards] == [
        ("beastmaker-1000", "beastmaker-1000", "draft"),
        ("metolius.wood-grips-compact-ii", "Wood Grips Compact II", "published"),
    ]
    assert snapshot.diagnostics == ()


def test_snapshot_rejects_draft_directory_with_invalid_board_id(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    primary = repository / "Hangboards" / "Beastmaker 1000" / "assets" / "primary.png"
    primary.parent.mkdir(parents=True)
    primary.write_bytes(b"draft image")

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert [board.board_id for board in snapshot.boards] == [
        "metolius.wood-grips-compact-ii"
    ]
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("Beastmaker 1000", "invalid_board_id")
    ]


def test_snapshot_reports_unreadable_draft_without_hiding_valid_boards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    primary = repository / "Hangboards" / "beastmaker-1000" / "assets" / "primary.png"
    primary.parent.mkdir(parents=True)
    primary.write_bytes(b"draft image")
    actual_read_bytes = Path.read_bytes

    def fail_for_draft(path: Path) -> bytes:
        if path == primary:
            raise PermissionError("permission denied")
        return actual_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_for_draft)

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert [board.board_id for board in snapshot.boards] == [
        "metolius.wood-grips-compact-ii"
    ]
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("beastmaker-1000", "invalid_run")
    ]
    assert "primary image is not readable" in snapshot.diagnostics[0].message


def test_snapshot_does_not_discover_draft_through_symlinked_assets(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    outside = tmp_path / "outside-assets"
    outside.mkdir()
    (outside / "primary.png").write_bytes(b"outside image")
    draft = repository / "Hangboards" / "escaped-draft"
    draft.mkdir()
    (draft / "assets").symlink_to(outside, target_is_directory=True)

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert [board.board_id for board in snapshot.boards] == [
        "metolius.wood-grips-compact-ii"
    ]


def test_copy_draft_source_rejects_primary_replaced_by_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    primary = repository / "Hangboards" / "beastmaker-1000" / "assets" / "primary.png"
    primary.parent.mkdir(parents=True)
    primary.write_bytes(b"draft image")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside image")
    library = RepositoryBoardLibrary(repository)
    destination = tmp_path / "workspace" / "source.png"
    destination.parent.mkdir()
    actual_open = board_library.os.open
    replaced = False

    def replace_before_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal replaced
        if path == "primary.png" and not replaced:
            replaced = True
            primary.unlink()
            primary.symlink_to(outside)
        return actual_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(board_library.os, "open", replace_before_open)

    with pytest.raises(BoardLibraryError, match="not safely readable"):
        library.copy_draft_source("beastmaker-1000", destination)

    assert not destination.exists()


def test_copy_draft_source_rejects_content_changed_after_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    primary = repository / "Hangboards" / "beastmaker-1000" / "assets" / "primary.png"
    primary.parent.mkdir(parents=True)
    primary.write_bytes(b"original image")
    library = RepositoryBoardLibrary(repository)
    destination = tmp_path / "workspace" / "source.png"
    destination.parent.mkdir()
    actual_open = board_library.os.open
    replaced = False

    def replace_before_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal replaced
        if path == "primary.png" and not replaced:
            replaced = True
            replacement = primary.with_suffix(".replacement")
            replacement.write_bytes(b"changed image")
            replacement.replace(primary)
        return actual_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(board_library.os, "open", replace_before_open)

    with pytest.raises(BoardLibraryError, match="changed while opening"):
        library.copy_draft_source("beastmaker-1000", destination)

    assert not destination.exists()


def test_snapshot_uses_document_identity_independently_of_directory_slug(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    package = repository / "Hangboards" / FIXTURE.name
    manifest_path = package / "board.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["id"] = "different-board"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["different-board"]
    assert snapshot.diagnostics == ()


def test_revision_token_covers_the_whole_package(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    library = RepositoryBoardLibrary(repository)
    before = library.get_board("metolius.wood-grips-compact-ii").revision_token
    board_path = repository / "Hangboards" / FIXTURE.name / "board.json"
    board_path.write_bytes(board_path.read_bytes() + b"\n")

    after = library.get_board("metolius.wood-grips-compact-ii").revision_token

    assert after != before


def test_copy_current_run_materializes_an_editable_runtime_run(tmp_path: Path) -> None:
    library = RepositoryBoardLibrary(_repository(tmp_path))
    destination = tmp_path / ".context" / "runtime" / "run"

    board = library.copy_current_run("metolius.wood-grips-compact-ii", destination)

    assert board.board_id == "metolius.wood-grips-compact-ii"
    status = read_status(destination)
    assert (status["status"], status["stage"]) == ("complete", 4)
    assert (destination / "run.json").is_file()

    stage_three = next(destination.glob("stages/03/*/stage-3-vector-regions.json"))
    vector_document = json.loads(stage_three.read_text(encoding="utf-8"))
    canonical_board = json.loads((FIXTURE / "board.json").read_text(encoding="utf-8"))
    rounded_hold = next(
        hold
        for hold in canonical_board["holds"]
        if hold["geometry"][0]["shape"]["type"] == "roundedRect"
    )
    rounded_region = next(
        region
        for region in vector_document["regions"]
        if region["key"] == rounded_hold["id"]
    )
    assert rounded_region["displayPath"].count(" Q ") == 4


def test_copy_current_run_rejects_existing_destination(tmp_path: Path) -> None:
    library = RepositoryBoardLibrary(_repository(tmp_path))
    destination = tmp_path / "existing"
    destination.mkdir()

    with pytest.raises(BoardLibraryError, match="already exists"):
        library.copy_current_run("metolius.wood-grips-compact-ii", destination)


def test_get_board_rejects_invalid_identifier(tmp_path: Path) -> None:
    library = RepositoryBoardLibrary(_repository(tmp_path))

    with pytest.raises(BoardLibraryError, match="identifier is invalid"):
        library.get_board("../escape")


def test_snapshot_rejects_a_symlinked_direct_child_package(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    hangboards = repository / "Hangboards"
    outside = write_board_package(tmp_path / "outside")
    hangboards.mkdir(parents=True)
    (hangboards / "escaped-board").symlink_to(outside, target_is_directory=True)

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert snapshot.boards == ()
    assert snapshot.diagnostics[0].code == "invalid_path"


def test_catalog_slug_is_independent_from_canonical_board_id(
    tmp_path: Path,
) -> None:
    library = RepositoryBoardLibrary(_repository(tmp_path))

    board = library.get_board("metolius.wood-grips-compact-ii")

    assert board.run_path.name == "metolius-wood-grips-compact-ii"
