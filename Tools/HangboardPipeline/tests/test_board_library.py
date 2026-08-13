from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from hangboard_vectorizer import board_library
from hangboard_vectorizer.board_library import BoardLibraryError, RepositoryBoardLibrary
from hangboard_vectorizer.onboarding_run import read_status


FIXTURE = Path(__file__).resolve().parents[3] / "Hangboards" / "metolius-wood-grips-compact-ii"


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
    assert snapshot.diagnostics == ()
    assert len(snapshot.boards[0].revision_token) == 64


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


def test_snapshot_validates_the_canonical_manifest_identity(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    package = repository / "Hangboards" / FIXTURE.name
    manifest_path = package / "board.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["id"] = "different-board"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert snapshot.boards == ()
    assert snapshot.diagnostics[0].code == "invalid_run"


def test_revision_token_covers_the_whole_package(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    library = RepositoryBoardLibrary(repository)
    before = library.get_board("metolius.wood-grips-compact-ii").revision_token
    evidence = repository / "Hangboards" / FIXTURE.name / "evidence.json"
    evidence.write_bytes(evidence.read_bytes() + b"\n")

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
    canonical_artwork = json.loads((FIXTURE / "artwork.json").read_text(encoding="utf-8"))
    # Runtime geometry must retain both the package silhouette and rounded hold
    # contours; replacing either with a bounding rectangle loses canonical art.
    assert vector_document["silhouettePaths"][0]["displayPath"].count(" C ") > 0
    rounded_piece = next(
        piece
        for piece in canonical_artwork["holdPieces"]
        if piece["shape"]["type"] == "roundedRect"
    )
    rounded_region = next(
        region
        for region in vector_document["regions"]
        if region["key"] == rounded_piece["holdID"]
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


@pytest.mark.parametrize("package_path", ["../outside", "/tmp/outside"])
def test_catalog_rejects_escaping_package_paths(
    tmp_path: Path, package_path: str
) -> None:
    repository = tmp_path / "repository"
    registry = repository / "Hangboards"
    registry.mkdir(parents=True)
    (registry / "catalog.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "boards": [{"id": "escaped-board", "path": package_path}],
            }
        ),
        encoding="utf-8",
    )

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert snapshot.boards == ()
    assert snapshot.diagnostics[0].code == "invalid_path"


def test_catalog_slug_is_independent_from_canonical_board_id(
    tmp_path: Path,
) -> None:
    library = RepositoryBoardLibrary(_repository(tmp_path))

    board = library.get_board("metolius.wood-grips-compact-ii")

    assert board.run_path.name == "metolius-wood-grips-compact-ii"
