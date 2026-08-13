from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import shutil
from threading import Event, Lock

from PIL import Image
import numpy as np
import pytest

import hangboard_vectorizer.workbench as workbench_module
from hangboard_vectorizer.board_library import (
    LibraryBoard,
    RepositoryBoardLibrary,
)
from hangboard_vectorizer.generic_stage0 import StageCheckpoint
from hangboard_vectorizer.generic_stage2 import GenericStage2Runner
from hangboard_vectorizer.onboard_cli import main
from hangboard_vectorizer.onboarding_run import (
    RunContext,
    approve_stage,
    resume_run,
    start_run,
)
from hangboard_vectorizer.workbench import (
    WorkbenchService,
    WorkbenchServiceError,
    WorkbenchView,
)
import hangboard_vectorizer.workbench_promotion as workbench_promotion
from hangboard_vectorizer.workbench_store import (
    BoardRecord,
    WorkbenchStore,
)


_BOARD_FIXTURES = (
    ("Beastmaker 1000", (77, 52, 34), ("grip-001", "grip-002")),
    (
        "Metolius Wood Grips Compact II",
        (103, 70, 42),
        ("grip-001", "grip-002", "grip-003"),
    ),
    (
        "Metolius Simulator 3D",
        (64, 82, 96),
        ("grip-001", "grip-002", "grip-003", "grip-004"),
    ),
)

_DIRECT_PACKAGE_SOURCE = (
    Path(__file__).resolve().parents[3]
    / "Hangboards/metolius-wood-grips-compact-ii"
)


def _copy_valid_package(destination: Path, board_id: str) -> None:
    """Copy a complete package and assign it a test-only canonical ID."""
    shutil.copytree(_DIRECT_PACKAGE_SOURCE, destination)
    for filename, key in (
        ("board.json", "id"),
        ("evidence.json", "boardID"),
        ("semantics.json", "boardID"),
        ("artwork.json", "boardID"),
    ):
        path = destination / filename
        document = json.loads(path.read_text(encoding="utf-8"))
        document[key] = board_id
        path.write_text(json.dumps(document), encoding="utf-8")


def _set_package_subtitle(package_root: Path, subtitle: str) -> None:
    """Create a legal, observable revision without adding package artifacts."""
    path = package_root / "board.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["subtitle"] = subtitle
    path.write_text(json.dumps(document), encoding="utf-8")


def test_checkout_repository_library_discovers_compact_ii() -> None:
    repository_root = Path(__file__).resolve().parents[3]

    snapshot = RepositoryBoardLibrary(repository_root).snapshot()

    assert "metolius.wood-grips-compact-ii" in {
        board.board_id for board in snapshot.boards
    }
    assert snapshot.diagnostics == ()


def test_workbench_publishes_a_validated_package_and_registry_without_legacy_artifacts(
    tmp_path: Path,
) -> None:
    """A package publication only changes the canonical package and registry."""
    repository_root = tmp_path / "repository"
    candidate_root = tmp_path / "candidate" / "compact-ii"
    shutil.copytree(_DIRECT_PACKAGE_SOURCE, candidate_root)
    hangboards = repository_root / "Hangboards"
    hangboards.mkdir(parents=True)
    (hangboards / "catalog.json").write_text(
        '{"schemaVersion": 1, "boards": []}\n', encoding="utf-8"
    )
    legacy_targets = {
        "HangTen/Models/GeneratedBoardCatalog.swift": "legacy catalog\n",
        "HangTen.xcodeproj/project.pbxproj": "legacy project\n",
        "Hangboards/legacy-board.json": "unrelated registry entry\n",
    }
    for relative, contents in legacy_targets.items():
        target = repository_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")

    publication = workbench_promotion.publish_package_candidate(
        repository_root,
        candidate_root,
        board_id="metolius.wood-grips-compact-ii",
    )

    assert publication.paths == (
        Path("Hangboards/catalog.json"),
        Path("Hangboards/compact-ii"),
    )
    catalog = json.loads((hangboards / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["boards"] == [
        {
            "id": "metolius.wood-grips-compact-ii",
            "path": "compact-ii",
        }
    ]
    assert (hangboards / "compact-ii" / "board.json").read_bytes() == (
        candidate_root / "board.json"
    ).read_bytes()
    assert {
        relative: (repository_root / relative).read_text(encoding="utf-8")
        for relative in legacy_targets
    } == legacy_targets


def test_parallel_package_publications_preserve_both_catalog_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Publishing a different board must not overwrite a concurrent catalog edit."""
    repository_root = tmp_path / "repository"
    hangboards = repository_root / "Hangboards"
    hangboards.mkdir(parents=True)
    (hangboards / "catalog.json").write_text(
        '{"schemaVersion": 1, "boards": []}\n', encoding="utf-8"
    )
    candidates = tmp_path / "candidates"
    first_candidate = candidates / "first-board"
    second_candidate = candidates / "second-board"
    _copy_valid_package(first_candidate, "example.first-board")
    _copy_valid_package(second_candidate, "example.second-board")

    actual_copytree = workbench_promotion.shutil.copytree
    first_copy_started = Event()
    release_first_copy = Event()
    second_copy_started = Event()

    def coordinated_copytree(
        source: Path, destination: Path, *args: object, **kwargs: object
    ):
        if Path(source) == first_candidate:
            first_copy_started.set()
            if not release_first_copy.wait(timeout=5):
                raise TimeoutError("first package copy was not released")
        elif Path(source) == second_candidate:
            second_copy_started.set()
        return actual_copytree(source, destination, *args, **kwargs)

    monkeypatch.setattr(workbench_promotion.shutil, "copytree", coordinated_copytree)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            workbench_promotion.publish_package_candidate,
            repository_root,
            first_candidate,
            board_id="example.first-board",
        )
        assert first_copy_started.wait(2)
        second = executor.submit(
            workbench_promotion.publish_package_candidate,
            repository_root,
            second_candidate,
            board_id="example.second-board",
        )
        if second_copy_started.wait(timeout=0.5):
            second.result(timeout=5)
        release_first_copy.set()
        first.result(timeout=5)
        second.result(timeout=5)

    catalog = json.loads((hangboards / "catalog.json").read_text(encoding="utf-8"))
    assert {entry["id"] for entry in catalog["boards"]} == {
        "example.first-board",
        "example.second-board",
    }
    assert json.loads((hangboards / "first-board" / "board.json").read_text())["id"] == "example.first-board"
    assert json.loads((hangboards / "second-board" / "board.json").read_text())["id"] == "example.second-board"


def test_failed_parallel_publication_cannot_rollback_a_successful_catalog_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing job must not restore a catalog snapshot older than another job."""
    repository_root = tmp_path / "repository"
    hangboards = repository_root / "Hangboards"
    hangboards.mkdir(parents=True)
    (hangboards / "catalog.json").write_text(
        '{"schemaVersion": 1, "boards": []}\n', encoding="utf-8"
    )
    candidates = tmp_path / "candidates"
    invalid_candidate = candidates / "invalid-approved"
    valid_candidate = candidates / "valid-board"
    invalid_candidate.mkdir(parents=True)
    _copy_valid_package(valid_candidate, "example.valid-board")

    actual_copytree = workbench_promotion.shutil.copytree
    invalid_copy_started = Event()
    release_invalid_copy = Event()
    valid_copy_started = Event()

    def coordinated_copytree(
        source: Path, destination: Path, *args: object, **kwargs: object
    ):
        if Path(source) == invalid_candidate:
            invalid_copy_started.set()
            if not release_invalid_copy.wait(timeout=5):
                raise TimeoutError("invalid package copy was not released")
        elif Path(source) == valid_candidate:
            valid_copy_started.set()
        return actual_copytree(source, destination, *args, **kwargs)

    monkeypatch.setattr(workbench_promotion.shutil, "copytree", coordinated_copytree)
    with ThreadPoolExecutor(max_workers=2) as executor:
        invalid = executor.submit(
            workbench_promotion.publish_package_candidate,
            repository_root,
            invalid_candidate,
            board_id="example.invalid-board",
        )
        assert invalid_copy_started.wait(2)
        valid = executor.submit(
            workbench_promotion.publish_package_candidate,
            repository_root,
            valid_candidate,
            board_id="example.valid-board",
        )
        if valid_copy_started.wait(timeout=0.5):
            valid.result(timeout=5)
        release_invalid_copy.set()
        with pytest.raises(ValueError, match="board.json"):
            invalid.result(timeout=5)
        valid.result(timeout=5)

    catalog = json.loads((hangboards / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["boards"] == [
        {
            "id": "example.valid-board",
            "path": "valid-board",
        }
    ]
    assert json.loads((hangboards / "valid-board" / "board.json").read_text())["id"] == "example.valid-board"
    assert not (hangboards / "invalid-board").exists()


def test_package_publication_replaces_a_matching_canonical_package(
    tmp_path: Path,
) -> None:
    """A matching ID/path is a canonical revision, not a duplicate package."""
    repository_root = tmp_path / "repository"
    hangboards = repository_root / "Hangboards"
    destination = hangboards / "compact-ii"
    shutil.copytree(_DIRECT_PACKAGE_SOURCE, destination)
    _set_package_subtitle(destination, "Previous canonical revision")
    (hangboards / "catalog.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "boards": [
                    {
                        "id": "metolius.wood-grips-compact-ii",
                        "path": "compact-ii",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    candidate = tmp_path / "candidate" / "compact-ii"
    shutil.copytree(_DIRECT_PACKAGE_SOURCE, candidate)

    workbench_promotion.publish_package_candidate(
        repository_root,
        candidate,
        board_id="metolius.wood-grips-compact-ii",
    )

    catalog = json.loads((hangboards / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["boards"] == [
        {
            "id": "metolius.wood-grips-compact-ii",
            "path": "compact-ii",
        }
    ]
    assert (destination / "board.json").read_bytes() == (
        candidate / "board.json"
    ).read_bytes()


def test_package_publication_atomically_updates_an_existing_revision(
    tmp_path: Path,
) -> None:
    """An approved package can be revised without duplicating its registry entry."""
    repository_root = tmp_path / "repository"
    hangboards = repository_root / "Hangboards"
    destination = hangboards / "compact-ii"
    shutil.copytree(_DIRECT_PACKAGE_SOURCE, destination)
    _set_package_subtitle(destination, "Previous canonical revision")
    (hangboards / "catalog.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "boards": [
                    {
                        "id": "metolius.wood-grips-compact-ii",
                        "path": "compact-ii",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    candidate = tmp_path / "candidate" / "compact-ii"
    shutil.copytree(_DIRECT_PACKAGE_SOURCE, candidate)
    _set_package_subtitle(candidate, "New candidate revision")

    workbench_promotion.publish_package_candidate(
        repository_root,
        candidate,
        board_id="metolius.wood-grips-compact-ii",
    )

    catalog = json.loads((hangboards / "catalog.json").read_text(encoding="utf-8"))
    assert len(catalog["boards"]) == 1
    assert catalog["boards"][0] == {
        "id": "metolius.wood-grips-compact-ii",
        "path": "compact-ii",
    }
    assert json.loads((destination / "board.json").read_text())["subtitle"] == (
        "New candidate revision"
    )


def test_failed_existing_package_revision_preserves_package_and_catalog(
    tmp_path: Path,
) -> None:
    """Validation failure must leave the prior canonical package fully active."""
    repository_root = tmp_path / "repository"
    hangboards = repository_root / "Hangboards"
    destination = hangboards / "compact-ii"
    shutil.copytree(_DIRECT_PACKAGE_SOURCE, destination)
    _set_package_subtitle(destination, "Previous canonical revision")
    catalog_path = hangboards / "catalog.json"
    catalog_bytes = (
        json.dumps(
            {
                "schemaVersion": 1,
                "boards": [
                    {
                        "id": "metolius.wood-grips-compact-ii",
                        "path": "compact-ii",
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    ).encode()
    catalog_path.write_bytes(catalog_bytes)
    candidate = tmp_path / "candidate" / "compact-ii"
    shutil.copytree(_DIRECT_PACKAGE_SOURCE, candidate)
    (candidate / "evidence.json").unlink()

    with pytest.raises(ValueError, match="evidence.json"):
        workbench_promotion.publish_package_candidate(
            repository_root,
            candidate,
            board_id="metolius.wood-grips-compact-ii",
        )

    assert catalog_path.read_bytes() == catalog_bytes
    assert json.loads((destination / "board.json").read_text())["subtitle"] == (
        "Previous canonical revision"
    )
    assert (destination / "evidence.json").is_file()


@pytest.mark.parametrize(
    ("board_id", "candidate_slug"),
    (
        ("metolius.wood-grips-compact-ii", "different-path"),
        ("example.different-id", "compact-ii"),
    ),
)
def test_package_publication_rejects_id_or_path_aliases(
    tmp_path: Path, board_id: str, candidate_slug: str
) -> None:
    """Only the exact existing ID/path pair may replace a canonical package."""
    repository_root = tmp_path / "repository"
    hangboards = repository_root / "Hangboards"
    destination = hangboards / "compact-ii"
    shutil.copytree(_DIRECT_PACKAGE_SOURCE, destination)
    _set_package_subtitle(destination, "Previous canonical revision")
    catalog_path = hangboards / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "boards": [
                    {
                        "id": "metolius.wood-grips-compact-ii",
                        "path": "compact-ii",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    candidate = tmp_path / "candidate" / candidate_slug
    _copy_valid_package(candidate, board_id)

    with pytest.raises(ValueError, match="catalog already contains"):
        workbench_promotion.publish_package_candidate(
            repository_root,
            candidate,
            board_id=board_id,
        )

    assert json.loads(catalog_path.read_text())["boards"][0]["path"] == "compact-ii"
    assert json.loads((destination / "board.json").read_text())["subtitle"] == (
        "Previous canonical revision"
    )


def test_final_save_never_publishes_into_the_canonical_repository_registry(
    tmp_path: Path,
) -> None:
    """A local save must not mutate canonical app artifacts."""
    library = _empty_repository_library(tmp_path / "repository")
    service = _fixture_service(tmp_path / "workspace", library=library)
    complete = _complete_runtime_board(service, "Example Board")

    saved = service.save(
        complete.board_id,
        expected_revision_id=complete.revision_id,
    )

    assert saved.saved is True
    assert saved.repository_board_id is None
    assert saved.repository_revision_token is None
    assert library.snapshot().boards == ()


def test_ui_created_run_is_resumable_by_cli_and_cli_run_is_listed_by_ui(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    service = _fixture_service(tmp_path)
    created = service.create_from_upload("Example Board", _fixture_image_bytes())

    assert service.mutation_reservation_key(created.board_id) == created.board_id
    assert (
        main(
            [
                "--output",
                str(created.run_root),
                "--workspace-root",
                str(tmp_path),
                "--status",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "awaiting_approval"

    cli_run = _create_cli_fixture_run(tmp_path / "cli-run")
    imported = service.import_run(cli_run)
    assert imported.run_root == cli_run
    assert any(board.board_id == imported.board_id for board in service.list_boards())


@pytest.mark.parametrize(("product_name", "color", "region_keys"), _BOARD_FIXTURES)
def test_product_neutral_workflow_preserves_stable_ids_through_local_save(
    tmp_path: Path,
    product_name: str,
    color: tuple[int, int, int],
    region_keys: tuple[str, ...],
) -> None:
    service = _fixture_service(tmp_path, region_keys=region_keys)
    stage3_decoy = _downstream_decoy_keys(3, len(region_keys))
    stage4_decoy = _downstream_decoy_keys(4, len(region_keys))

    current = service.create_from_upload(
        product_name, _fixture_image_bytes(color=color)
    )
    revision_id = current.revision_id
    for stage in (0, 1):
        current = service.approve_and_advance(
            current.board_id,
            expected_revision_id=revision_id,
            expected_stage=stage,
        )

    stage2 = _stage_document(current.run_root, 2, "stage-2-regions.json")
    assert set(stage2) == {
        "canvas",
        "labelEncoding",
        "regions",
        "schemaVersion",
        "stage",
    }
    stage2["regions"][0]["metadata"]["mode"] = "aperture"
    service.save_draft(
        current.board_id,
        stage2,
        expected_revision_id=revision_id,
        expected_stage=2,
    )
    current = service.approve_and_advance(
        current.board_id,
        expected_revision_id=revision_id,
        expected_stage=2,
    )
    manifest = json.loads((current.run_root / "run.json").read_text())
    assert manifest["stages"][2]["attempt"] == 2
    stage2 = _stage_document(current.run_root, 2, "stage-2-regions.json")
    assert stage2["regions"][0]["metadata"]["mode"] == "aperture"

    stage3 = _stage_document(
        current.run_root, 3, "stage-3-vector-regions.json"
    )
    assert set(stage3) == {
        "canvas",
        "pieceCount",
        "regions",
        "schemaVersion",
        "silhouettePaths",
        "stage",
    }
    stage3["regions"][0]["metadata"]["mode"] = "surface"
    service.save_draft(
        current.board_id,
        stage3,
        expected_revision_id=revision_id,
        expected_stage=3,
    )
    current = service.approve_and_advance(
        current.board_id,
        expected_revision_id=revision_id,
        expected_stage=3,
    )
    manifest = json.loads((current.run_root / "run.json").read_text())
    assert manifest["stages"][3]["attempt"] == 2
    stage3 = _stage_document(
        current.run_root, 3, "stage-3-vector-regions.json"
    )
    assert stage3["regions"][0]["metadata"]["mode"] == "surface"
    assert set(_region_identity(stage3)[1]).isdisjoint(stage3_decoy)

    stage4 = _stage_document(current.run_root, 4, "stage-4-manifest.json")
    assert set(stage4) == {"canvas", "regions", "schemaVersion", "stage"}
    assert set(_region_identity(stage4)[1]).isdisjoint(stage4_decoy)
    _assert_stable_identity_chain(stage2, stage3, stage4)
    assert _region_identity(stage2) == (
        list(range(1, len(region_keys) + 1)),
        list(region_keys),
    )
    assert current.revision_id == revision_id

    complete = service.approve_and_advance(
        current.board_id,
        expected_revision_id=revision_id,
        expected_stage=4,
    )
    saved = service.save(
        complete.board_id, expected_revision_id=complete.revision_id
    )
    board_manifest = json.loads(
        (
            tmp_path / "boards" / saved.board_id / "board.json"
        ).read_text(encoding="utf-8")
    )
    assert saved.saved is True
    assert board_manifest["savedRevisionId"] == revision_id


def test_open_library_board_copies_current_token_and_is_idempotent(
    tmp_path: Path,
) -> None:
    library, entry = _repository_library(tmp_path)
    service = _fixture_service(tmp_path / "workspace", library=library)

    assert service.library_open_reservation_key(entry.board_id) == (
        f"repository-board:{entry.board_id}"
    )
    assert service.library_snapshot() == library.snapshot()
    first = service.open_library_board(entry.board_id)
    second = service.open_library_board(entry.board_id)

    assert second.board_id == first.board_id
    assert second.revision_id == first.revision_id
    assert second.repository_board_id == entry.board_id
    assert second.repository_revision_token == entry.revision_token
    assert service.library_open_reservation_key(entry.board_id) == (
        f"repository-board:{entry.board_id}"
    )
    assert service.mutation_reservation_key(first.board_id) == (
        f"repository-board:{entry.board_id}"
    )


def test_open_draft_repository_board_starts_editable_runtime_from_primary_image(
    tmp_path: Path,
) -> None:
    library = _empty_repository_library(tmp_path / "repository")
    draft_root = library.repository_root / "Hangboards" / "beastmaker-1000"
    primary = draft_root / "assets" / "primary.png"
    primary.parent.mkdir(parents=True)
    primary.write_bytes(_fixture_image_bytes())
    service = _fixture_service(tmp_path / "workspace", library=library)

    entry = library.get_board("beastmaker-1000")
    first = service.open_library_board(entry.board_id)
    second = service.open_library_board(entry.board_id)

    assert entry.status == "draft"
    assert first.product_name == "beastmaker-1000"
    assert first.stage == 0
    assert second.board_id == first.board_id
    assert second.revision_id == first.revision_id
    assert first.repository_board_id == entry.board_id
    assert first.repository_revision_token == entry.revision_token


def test_open_library_board_links_the_exact_token_returned_by_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library, entry = _repository_library(tmp_path)
    service = _fixture_service(tmp_path / "workspace", library=library)
    actual_copy = library.copy_current_run
    advanced_revisions = []

    def advance_current_then_copy(board_id: str, destination: Path) -> LibraryBoard:
        advanced_revisions.append(
            _advance_package_revision(library, entry.board_id)
        )
        return actual_copy(board_id, destination)

    monkeypatch.setattr(library, "copy_current_run", advance_current_then_copy)

    opened = service.open_library_board(entry.board_id)

    assert len(advanced_revisions) == 1
    assert opened.repository_board_id == entry.board_id
    assert opened.repository_revision_token == advanced_revisions[0].revision_token


def test_first_library_open_never_exposes_an_active_unlinked_conflict_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library, entry = _repository_library(tmp_path)
    workspace = tmp_path / "workspace"
    service = _fixture_service(workspace, library=library)
    actual_write = service.store._write_board
    active_snapshots = []

    def record_published_state(updated, *args: object, **kwargs: object) -> None:
        actual_write(updated, *args, **kwargs)
        persisted = WorkbenchStore(workspace).read_board(updated.id)
        if persisted.active_revision_id:
            active_snapshots.append(
                (
                    persisted.active_revision_id,
                    persisted.repository_board_id,
                    persisted.repository_revision_token,
                    service.mutation_reservation_key(persisted.id),
                )
            )

    monkeypatch.setattr(service.store, "_write_board", record_published_state)

    opened = service.open_library_board(entry.board_id)

    expected = (
        opened.revision_id,
        entry.board_id,
        entry.revision_token,
        f"repository-board:{entry.board_id}",
    )
    assert active_snapshots
    assert all(snapshot == expected for snapshot in active_snapshots)


def test_interrupted_first_library_open_never_exposes_active_unlinked_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library, entry = _repository_library(tmp_path)
    workspace = tmp_path / "workspace"
    service = _fixture_service(workspace, library=library)
    actual_write = service.store._write_board
    active_snapshots = []
    interrupted = False

    def interrupt_final_transition(updated, *args: object, **kwargs: object) -> None:
        nonlocal interrupted
        if (
            not interrupted
            and updated.active_revision_id
            and updated.repository_board_id == entry.board_id
            and updated.repository_revision_token == entry.revision_token
        ):
            interrupted = True
            raise OSError("repository open finalization interrupted")
        actual_write(updated, *args, **kwargs)
        persisted = WorkbenchStore(workspace).read_board(updated.id)
        if persisted.active_revision_id:
            active_snapshots.append(
                (
                    persisted.repository_board_id,
                    persisted.repository_revision_token,
                )
            )

    monkeypatch.setattr(service.store, "_write_board", interrupt_final_transition)

    with pytest.raises(OSError, match="repository open finalization interrupted"):
        service.open_library_board(entry.board_id)

    persisted = service.store.list_boards()[0]
    assert interrupted is True
    assert active_snapshots == []
    assert persisted.active_revision_id == ""
    assert persisted.repository_board_id is None
    assert persisted.repository_revision_token is None
    assert persisted.revisions[-1].state == "failed"


def test_first_library_open_reconciles_post_replace_finalization_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library, entry = _repository_library(tmp_path)
    service = _fixture_service(tmp_path / "workspace", library=library)
    actual_write = service.store._write_board
    injected = False

    def fail_after_target_replace(updated, *args: object, **kwargs: object) -> None:
        nonlocal injected
        if (
            not injected
            and updated.active_revision_id
            and updated.repository_board_id == entry.board_id
            and updated.repository_revision_token == entry.revision_token
        ):
            actual_write(updated, *args, **kwargs)
            injected = True
            raise OSError("repository open post-replace error")
        actual_write(updated, *args, **kwargs)

    monkeypatch.setattr(service.store, "_write_board", fail_after_target_replace)

    opened = service.open_library_board(entry.board_id)

    persisted = service.store.read_board(opened.board_id)
    revision = service.store.read_revision(opened.board_id, opened.revision_id)
    assert injected is True
    assert persisted.active_revision_id == opened.revision_id
    assert persisted.repository_board_id == entry.board_id
    assert persisted.repository_revision_token == entry.revision_token
    assert revision.current_stage == 4
    assert revision.state == "complete"


def test_open_changed_library_manifest_preserves_divergent_runtime_revision(
    tmp_path: Path,
) -> None:
    library, entry = _repository_library(tmp_path)
    service = _fixture_service(tmp_path / "workspace", library=library)
    opened = service.open_library_board(entry.board_id)
    divergent = service.revise_stage(
        opened.board_id, stage=1, expected_revision_id=opened.revision_id
    )
    published = _advance_package_revision(library, entry.board_id)

    newer = service.open_library_board(entry.board_id)
    runtime_board = service.store.read_board(opened.board_id)
    revisions = {revision.id: revision for revision in runtime_board.revisions}

    assert published.revision_token != entry.revision_token
    assert newer.board_id == opened.board_id
    assert newer.revision_id not in {opened.revision_id, divergent.revision_id}
    assert newer.repository_revision_token == published.revision_token
    assert set(revisions) == {
        opened.revision_id,
        divergent.revision_id,
        newer.revision_id,
    }
    assert revisions[divergent.revision_id].state == "active"
    assert revisions[divergent.revision_id].run_root.is_dir()


def test_failed_newer_library_open_restores_the_exact_previous_active_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library, entry = _repository_library(tmp_path)
    service = _fixture_service(tmp_path / "workspace", library=library)
    opened = service.open_library_board(entry.board_id)
    divergent = service.revise_stage(
        opened.board_id, stage=1, expected_revision_id=opened.revision_id
    )
    _advance_package_revision(library, entry.board_id)

    actual_write = service.store._write_board

    def fail_finalization(updated, *args: object, **kwargs: object) -> None:
        if updated.repository_revision_token != entry.revision_token:
            raise OSError("repository finalization interrupted")
        actual_write(updated, *args, **kwargs)

    monkeypatch.setattr(service.store, "_write_board", fail_finalization)
    with pytest.raises(OSError, match="repository finalization interrupted"):
        service.open_library_board(entry.board_id)

    board = service.store.read_board(opened.board_id)
    failed = board.revisions[-1]
    assert board.active_revision_id == divergent.revision_id
    assert board.repository_revision_token == entry.revision_token
    assert failed.state == "failed"


def test_parallel_library_opens_are_serialized_and_share_one_runtime_board(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library, entry = _repository_library(tmp_path)
    service = _fixture_service(tmp_path / "workspace", library=library)
    actual_copy = library.copy_current_run
    copy_guard = Lock()
    first_copy = Event()
    release_first = Event()
    second_started = Event()
    copy_count = 0

    def coordinate_copy(board_id: str, destination: Path) -> LibraryBoard:
        nonlocal copy_count
        with copy_guard:
            copy_count += 1
        first_copy.set()
        if not release_first.wait(timeout=5):
            raise TimeoutError("first library copy was not released")
        return actual_copy(board_id, destination)

    def open_second() -> WorkbenchView:
        second_started.set()
        return service.open_library_board(entry.board_id)

    monkeypatch.setattr(library, "copy_current_run", coordinate_copy)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(service.open_library_board, entry.board_id)
        assert first_copy.wait(2)
        second = executor.submit(open_second)
        assert second_started.wait(2)
        with copy_guard:
            assert copy_count == 1
        release_first.set()
        opened = (first.result(timeout=5), second.result(timeout=5))

    assert opened[0].board_id == opened[1].board_id
    assert opened[0].revision_id == opened[1].revision_id
    assert len(service.store.list_boards()) == 1


def test_open_library_board_scans_runtime_boards_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library, entry = _repository_library(tmp_path)
    service = _fixture_service(tmp_path / "workspace", library=library)
    actual_list_boards = service.store.list_boards
    scan_count = 0

    def count_scans() -> tuple[BoardRecord, ...]:
        nonlocal scan_count
        scan_count += 1
        return actual_list_boards()

    monkeypatch.setattr(service.store, "list_boards", count_scans)

    service.open_library_board(entry.board_id)

    assert scan_count == 1


def test_revision_replays_hash_bound_file_semantic_proposal_into_child_run(
    tmp_path: Path,
) -> None:
    service, current, proposal, _proposal_path = _accepted_file_proposal_parent(
        tmp_path
    )

    revised = service.revise_stage(
        current.board_id,
        stage=3,
        expected_revision_id=current.revision_id,
    )

    child_proposal = revised.run_root / "inputs/stage-2-semantic-proposal.json"
    assert revised.stage == 3
    child_manifest = json.loads((revised.run_root / "run.json").read_text())
    child_stage1 = child_manifest["stages"][1]
    child_acceptance = json.loads(
        (revised.run_root / child_stage1["acceptancePath"]).read_text()
    )
    expected_child_proposal = dict(proposal)
    expected_child_proposal["inputAcceptanceSha256"] = child_stage1[
        "acceptanceSha256"
    ]
    expected_child_proposal["inputRasterSha256"] = child_acceptance[
        "registered"
    ]["fileSha256"]
    child_proposal_bytes = child_proposal.read_bytes()
    assert json.loads(child_proposal_bytes) == expected_child_proposal
    child_stage2 = child_manifest["stages"][2]
    child_capture = json.loads(
        (
            revised.run_root
            / child_stage2["artifactRoot"]
            / "stage-2-semantic-capture.json"
        ).read_text()
    )
    assert child_capture["proposal"] == {
        "path": "inputs/stage-2-semantic-proposal.json",
        "provider": "file",
        "sha256": sha256(child_proposal_bytes).hexdigest(),
    }


@pytest.mark.parametrize("revised_stage", (0, 1))
def test_deferred_revision_carries_file_proposal_when_stage1_is_approved(
    tmp_path: Path, revised_stage: int
) -> None:
    service, current, proposal, _proposal_path = _accepted_file_proposal_parent(
        tmp_path
    )
    revised = service.revise_stage(
        current.board_id,
        stage=revised_stage,
        expected_revision_id=current.revision_id,
    )
    while revised.stage < 1:
        revised = service.approve_and_advance(
            revised.board_id,
            expected_revision_id=revised.revision_id,
            expected_stage=revised.stage,
        )

    advanced = service.approve_and_advance(
        revised.board_id,
        expected_revision_id=revised.revision_id,
        expected_stage=1,
    )

    child_manifest = json.loads((advanced.run_root / "run.json").read_text())
    child_stage1 = child_manifest["stages"][1]
    child_acceptance = json.loads(
        (advanced.run_root / child_stage1["acceptancePath"]).read_text()
    )
    expected_child_proposal = dict(proposal)
    expected_child_proposal["inputAcceptanceSha256"] = child_stage1[
        "acceptanceSha256"
    ]
    expected_child_proposal["inputRasterSha256"] = child_acceptance[
        "registered"
    ]["fileSha256"]
    child_proposal_bytes = (
        advanced.run_root / "inputs/stage-2-semantic-proposal.json"
    ).read_bytes()
    child_stage2 = child_manifest["stages"][2]
    child_capture = json.loads(
        (
            advanced.run_root
            / child_stage2["artifactRoot"]
            / "stage-2-semantic-capture.json"
        ).read_text()
    )
    assert advanced.stage == 2
    assert json.loads(child_proposal_bytes) == expected_child_proposal
    assert child_capture["proposal"] == {
        "path": "inputs/stage-2-semantic-proposal.json",
        "provider": "file",
        "sha256": sha256(child_proposal_bytes).hexdigest(),
    }


def test_revision_replay_rejects_candidate_hashes_changed_after_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, current, _proposal, _proposal_path = (
        _accepted_file_proposal_parent(tmp_path)
    )
    manifest = json.loads((current.run_root / "run.json").read_text())
    stage2 = manifest["stages"][2]
    candidate_hashes_path = current.run_root / stage2["candidateHashesPath"]
    original_resume_run = workbench_module.resume_run
    changed = False

    def change_hashes_after_parent_validation(*args: object, **kwargs: object) -> object:
        nonlocal changed
        result = original_resume_run(*args, **kwargs)
        if not changed:
            candidate_hashes_path.write_bytes(
                candidate_hashes_path.read_bytes() + b" "
            )
            changed = True
        return result

    monkeypatch.setattr(
        workbench_module, "resume_run", change_hashes_after_parent_validation
    )

    with pytest.raises(
        WorkbenchServiceError, match="Stage 2 candidate hashes changed"
    ):
        service.revise_stage(
            current.board_id,
            stage=3,
            expected_revision_id=current.revision_id,
        )


def test_revision_replay_rejects_semantic_capture_changed_after_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, current, _proposal, _proposal_path = (
        _accepted_file_proposal_parent(tmp_path)
    )
    manifest = json.loads((current.run_root / "run.json").read_text())
    stage2 = manifest["stages"][2]
    capture_path = (
        current.run_root
        / stage2["artifactRoot"]
        / "stage-2-semantic-capture.json"
    )
    capture = json.loads(capture_path.read_text())
    capture["changedAfterAcceptance"] = True
    changed_capture = (
        json.dumps(capture, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    original_resume_run = workbench_module.resume_run
    changed = False

    def change_capture_after_parent_validation(*args: object, **kwargs: object) -> object:
        nonlocal changed
        result = original_resume_run(*args, **kwargs)
        if not changed:
            capture_path.write_bytes(changed_capture)
            changed = True
        return result

    monkeypatch.setattr(
        workbench_module, "resume_run", change_capture_after_parent_validation
    )

    with pytest.raises(
        WorkbenchServiceError, match="Stage 2 semantic capture changed"
    ):
        service.revise_stage(
            current.board_id,
            stage=3,
            expected_revision_id=current.revision_id,
        )


def test_revision_replay_parses_the_hash_validated_proposal_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, current, proposal, proposal_path = _accepted_file_proposal_parent(
        tmp_path
    )
    changed_proposal = deepcopy(proposal)
    changed_proposal["regions"][0]["metadata"] = {"raceMarker": "unverified"}
    changed_proposal_text = (
        json.dumps(changed_proposal, indent=2, sort_keys=True) + "\n"
    )
    original_read_text = Path.read_text

    def replace_proposal_on_reopen(
        path: Path, *args: object, **kwargs: object
    ) -> str:
        if path == proposal_path:
            return changed_proposal_text
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replace_proposal_on_reopen)

    revised = service.revise_stage(
        current.board_id,
        stage=3,
        expected_revision_id=current.revision_id,
    )

    child_proposal = json.loads(
        (
            revised.run_root / "inputs/stage-2-semantic-proposal.json"
        ).read_bytes()
    )
    assert child_proposal["regions"][0]["metadata"] == {}


def test_stage2_inventory_mutation_propagates_unchanged_through_stage4(
    tmp_path: Path,
) -> None:
    service = _fixture_service(
        tmp_path, region_keys=("grip-001", "grip-002", "grip-003")
    )
    current = service.create_from_upload("Generic Fixture Board", _fixture_image_bytes())
    for stage in (0, 1):
        current = service.approve_and_advance(
            current.board_id,
            expected_revision_id=current.revision_id,
            expected_stage=stage,
        )

    stage2 = _stage_document(current.run_root, 2, "stage-2-regions.json")
    retained = deepcopy(stage2["regions"][1])
    retained["type"] = "edge"
    added = deepcopy(stage2["regions"][2])
    added.update(
        {
            "id": 4,
            "key": "grip-004",
            "anchor": [90, 40],
            "bounds": [85, 35, 96, 46],
            "contour": [[85, 35], [95, 35], [95, 45], [85, 45]],
        }
    )
    stage2["regions"] = [retained, added]
    service.save_draft(
        current.board_id,
        stage2,
        expected_revision_id=current.revision_id,
        expected_stage=2,
    )
    current = service.approve_and_advance(
        current.board_id,
        expected_revision_id=current.revision_id,
        expected_stage=2,
    )
    accepted_stage2 = _stage_document(current.run_root, 2, "stage-2-regions.json")
    stage3 = _stage_document(current.run_root, 3, "stage-3-vector-regions.json")
    current = service.approve_and_advance(
        current.board_id,
        expected_revision_id=current.revision_id,
        expected_stage=3,
    )
    stage4 = _stage_document(current.run_root, 4, "stage-4-manifest.json")

    expected = ([2, 4], ["grip-002", "grip-004"])
    assert _region_identity(accepted_stage2) == expected
    assert [region["type"] for region in accepted_stage2["regions"]] == ["edge", "pocket"]
    assert _region_identity(stage3) == expected
    assert _region_identity(stage4) == expected
    assert [region["type"] for region in stage3["regions"]] == ["edge", "pocket"]
    assert [region["type"] for region in stage4["regions"]] == ["edge", "pocket"]


@pytest.mark.parametrize("mutation", ("mutate", "drop", "reorder"))
def test_identity_propagation_assertion_rejects_a_changed_upstream_inventory(
    tmp_path: Path, mutation: str
) -> None:
    service = _fixture_service(
        tmp_path,
        region_keys=("grip-001", "grip-002", "grip-003"),
        stage3_identity_mutation=mutation,
    )
    current = service.create_from_upload("Fixture Board", _fixture_image_bytes())
    for stage in (0, 1):
        current = service.approve_and_advance(
            current.board_id,
            expected_revision_id=current.revision_id,
            expected_stage=stage,
        )
    stage2 = _stage_document(current.run_root, 2, "stage-2-regions.json")
    service.save_draft(
        current.board_id,
        stage2,
        expected_revision_id=current.revision_id,
        expected_stage=2,
    )
    current = service.approve_and_advance(
        current.board_id,
        expected_revision_id=current.revision_id,
        expected_stage=2,
    )
    stage2 = _stage_document(current.run_root, 2, "stage-2-regions.json")
    stage3 = _stage_document(
        current.run_root, 3, "stage-3-vector-regions.json"
    )

    with pytest.raises(AssertionError, match="stable region identity"):
        _assert_stable_identity_chain(stage2, stage3)


def test_production_workbench_surface_contains_no_product_tokens() -> None:
    onboarding_modules = (
        Path(workbench_module.__file__).resolve(),
        Path(workbench_module.__file__).with_name("workbench_store.py").resolve(),
        Path(workbench_module.__file__).with_name("review_edits.py").resolve(),
        Path(workbench_module.__file__).with_name("onboarding_run.py").resolve(),
        Path(workbench_module.__file__).with_name("onboard_cli.py").resolve(),
    )
    editor_root = Path(__file__).resolve().parents[2] / "HangboardWorkbench"
    editor_modules = tuple(
        editor_root / name
        for name in (
            "server.py",
            "job_manager.py",
            "app.js",
            "editor-model.js",
            "vector-path-model.js",
            "workbench-client.js",
            "workbench-controller.js",
            "workbench-model.js",
        )
    )

    violations: dict[str, list[str]] = {}
    for path in (*onboarding_modules, *editor_modules):
        normalized = "".join(
            character
            for character in path.read_text(encoding="utf-8").lower()
            if character.isalnum()
        )
        matches = [
            token
            for token in (
                "beastmaker",
                "metolius",
                "woodgrips",
                "compactii",
                "simulator3d",
            )
            if token in normalized
        ]
        if matches:
            violations[str(path)] = matches

    assert violations == {}


def _fixture_image_bytes(color: tuple[int, int, int] = (45, 65, 85)) -> bytes:
    stream = BytesIO()
    Image.new("RGB", (512, 256), color).save(stream, format="PNG")
    return stream.getvalue()


def _fixture_service(
    root: Path,
    *,
    region_keys: tuple[str, ...] = ("grip-001",),
    stage3_identity_mutation: str | None = None,
    library: RepositoryBoardLibrary | None = None,
) -> WorkbenchService:
    return WorkbenchService(
        WorkbenchStore(root),
        runners=_stub_runners(
            region_keys, stage3_identity_mutation=stage3_identity_mutation
        ),
        library=library,
    )


def _empty_repository_library(root: Path) -> RepositoryBoardLibrary:
    library_root = root / "Hangboards"
    library_root.mkdir(parents=True)
    (library_root / "catalog.json").write_text(
        '{"schemaVersion": 1, "boards": []}\n', encoding="utf-8"
    )
    return RepositoryBoardLibrary(root)


def _repository_library(
    root: Path,
    *,
    product_name: str = "Example Board",
    color: tuple[int, int, int] = (45, 65, 85),
    region_keys: tuple[str, ...] = ("grip-001",),
) -> tuple[RepositoryBoardLibrary, LibraryBoard]:
    library = _empty_repository_library(root / "repository")
    del product_name, color, region_keys
    package = library.repository_root / "Hangboards" / _DIRECT_PACKAGE_SOURCE.name
    shutil.copytree(_DIRECT_PACKAGE_SOURCE, package)
    shutil.copy2(
        _DIRECT_PACKAGE_SOURCE.parent / "catalog.json", package.parent / "catalog.json"
    )
    return library, library.get_board("metolius.wood-grips-compact-ii")


def _advance_package_revision(
    library: RepositoryBoardLibrary, board_id: str
) -> LibraryBoard:
    board = library.get_board(board_id)
    evidence = board.run_path / "evidence.json"
    evidence.write_bytes(evidence.read_bytes() + b"\n")
    return library.get_board(board_id)


def _complete_runtime_board(
    service: WorkbenchService,
    product_name: str,
    *,
    color: tuple[int, int, int] = (45, 65, 85),
) -> WorkbenchView:
    current = service.create_from_upload(product_name, _fixture_image_bytes(color))
    return _approve_to_completion(service, current)


def _approve_to_completion(
    service: WorkbenchService, current: WorkbenchView
) -> WorkbenchView:
    while current.stage < 4:
        current = service.approve_and_advance(
            current.board_id,
            expected_revision_id=current.revision_id,
            expected_stage=current.stage,
        )
    return service.approve_and_advance(
        current.board_id,
        expected_revision_id=current.revision_id,
        expected_stage=current.stage,
    )


def _accepted_file_proposal_parent(
    root: Path,
) -> tuple[WorkbenchService, WorkbenchView, dict[str, object], Path]:
    runners = _stub_runners(("grip-001",))
    runners[2] = GenericStage2Runner()
    service = WorkbenchService(WorkbenchStore(root), runners=runners)
    current = service.create_from_upload(
        "Generic File Proposal Board", _fixture_image_bytes()
    )
    current = service.approve_and_advance(
        current.board_id,
        expected_revision_id=current.revision_id,
        expected_stage=0,
    )
    approve_stage(current.run_root, 1)
    manifest = json.loads((current.run_root / "run.json").read_text())
    stage1 = manifest["stages"][1]
    acceptance = json.loads(
        (current.run_root / stage1["acceptancePath"]).read_text()
    )
    proposal: dict[str, object] = {
        "canvas": {"height": 64, "width": 128},
        "inputAcceptanceSha256": stage1["acceptanceSha256"],
        "inputRasterSha256": acceptance["registered"]["fileSha256"],
        "productKey": manifest["product"]["key"],
        "provider": "file",
        "regions": [
            {
                "anchor": [24, 24],
                "geometry": {
                    "mode": "surface",
                    "polygon": [[12, 12], [36, 12], [36, 36], [12, 36]],
                },
                "id": 1,
                "key": "grip-001",
                "metadata": {},
                "type": "edge",
            }
        ],
        "schemaVersion": 1,
    }
    proposal_path = current.run_root / "inputs/stage-2-semantic-proposal.json"
    proposal_path.write_text(
        json.dumps(proposal, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    resume_run(current.run_root, runners=runners)
    current = service.get_board(current.board_id)
    for stage in (2, 3):
        current = service.approve_and_advance(
            current.board_id,
            expected_revision_id=current.revision_id,
            expected_stage=stage,
        )
    return service, current, proposal, proposal_path


def _create_cli_fixture_run(path: Path) -> Path:
    source = path.parent / "cli-source.png"
    source.write_bytes(_fixture_image_bytes())
    start_run(
        "CLI Fixture Board",
        str(source),
        path,
        runners=_stub_runners(),
        workspace_root=path.parent,
    )
    return path


def _stub_runners(
    region_keys: tuple[str, ...] = ("grip-001",),
    *,
    stage3_identity_mutation: str | None = None,
) -> dict[int, _StubStageRunner]:
    stage3_runner: _StubStageRunner = _StubStageRunner(
        3, _downstream_decoy_keys(3, len(region_keys))
    )
    if stage3_identity_mutation is not None:
        stage3_runner = _BrokenStage3Runner(
            _downstream_decoy_keys(3, len(region_keys)),
            stage3_identity_mutation,
        )
    return {
        0: _StubStageRunner(0, ()),
        1: _StubStageRunner(1, ()),
        2: _StubStageRunner(2, region_keys),
        3: stage3_runner,
        4: _StubStageRunner(4, _downstream_decoy_keys(4, len(region_keys))),
    }


def _downstream_decoy_keys(stage: int, count: int) -> tuple[str, ...]:
    return tuple(f"stage-{stage}-decoy-{index:03d}" for index in range(1, count + 1))


class _StubStageRunner:
    def __init__(
        self,
        stage: int,
        region_keys: tuple[str, ...],
    ) -> None:
        self.stage = stage
        self.region_keys = region_keys

    def run(self, context: RunContext, artifact_root: Path) -> StageCheckpoint:
        artifact_root.mkdir(parents=True)
        review = artifact_root / f"stage-{self.stage}-review.png"
        Image.new("RGB", (128, 64), (120, 80, 40)).save(review)
        candidate = self._candidate(context, artifact_root)
        candidate_path = artifact_root / f"stage-{self.stage}-candidate.json"
        _write_json(candidate_path, candidate)
        hashes = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in sorted(artifact_root.iterdir())
            if path.is_file()
        }
        _write_json(artifact_root / "candidate-hashes.json", hashes)
        return StageCheckpoint(
            stage=self.stage,
            artifact_root=artifact_root,
            candidate_hashes=hashes,
            review_path=review,
            machine_passed=True,
        )

    def _candidate(
        self, context: RunContext, artifact_root: Path
    ) -> dict[str, object]:
        candidate: dict[str, object] = {"profile": {}, "stage": self.stage}
        if self.stage == 0:
            candidate["registered"] = {}
            return candidate

        stages = context.manifest["stages"]
        assert isinstance(stages, list)
        upstream = stages[self.stage - 1]
        assert isinstance(upstream, dict)
        candidate["inputAcceptance"] = {
            "path": upstream["acceptancePath"],
            "sha256": upstream["acceptanceSha256"],
        }
        if self.stage == 1:
            registered = artifact_root / "stage-1-auto-rgba.png"
            Image.new("RGBA", (128, 64), (10, 20, 30, 255)).save(registered)
            with Image.open(registered) as image:
                rgba = np.asarray(image, dtype=np.uint8)
            candidate["registered"] = {
                "alphaSha256": sha256(rgba[..., 3].tobytes()).hexdigest(),
                "fileSha256": _hash_file(registered),
                "height": 64,
                "pixelSha256": sha256(rgba.tobytes()).hexdigest(),
                "width": 128,
            }
        elif self.stage == 2:
            regions = artifact_root / "stage-2-regions.json"
            labels = artifact_root / "stage-2-labels.png"
            _write_json(regions, self._stage2_document())
            Image.new("I;16", (128, 64), 0).save(labels)
            candidate.update(
                {
                    "regionCount": len(self.region_keys),
                    "regions": {"fileSha256": _hash_file(regions)},
                    "registered": {"fileSha256": _hash_file(labels)},
                }
            )
        elif self.stage == 3:
            stage2 = _accepted_stage_document(
                context, 2, "regions", "stage-2-regions.json"
            )
            vector_document = self._stage3_document(stage2["regions"])
            regions = artifact_root / "stage-3-vector-regions.json"
            svg = artifact_root / "stage-3-vector.svg"
            _write_json(regions, vector_document)
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
            candidate.update(
                {
                    "regionCount": len(vector_document["regions"]),
                    "vectorRegions": {"fileSha256": _hash_file(regions)},
                    "vectorSvg": {"fileSha256": _hash_file(svg)},
                }
            )
        else:
            stage3 = _accepted_stage_document(
                context, 3, "vectorRegions", "stage-3-vector-regions.json"
            )
            stage4_document = self._stage4_document(stage3["regions"])
            normal = artifact_root / "stage-4-normal.png"
            product_svg = artifact_root / "stage-4-product.svg"
            manifest = artifact_root / "stage-4-manifest.json"
            highlights = artifact_root / "stage-4-highlights.json"
            Image.new("RGB", (128, 64), (1, 2, 3)).save(normal)
            product_svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
            _write_json(manifest, stage4_document)
            _write_json(
                highlights,
                {
                    "regions": [
                        {"id": region["id"], "key": region["key"]}
                        for region in stage4_document["regions"]
                    ]
                },
            )
            candidate.update(
                {
                    "regionCount": len(stage4_document["regions"]),
                    "normal": {"fileSha256": _hash_file(normal)},
                    "productSvg": {"fileSha256": _hash_file(product_svg)},
                    "manifest": {"fileSha256": _hash_file(manifest)},
                    "highlights": {"fileSha256": _hash_file(highlights)},
                }
            )
        return candidate

    def _stage2_document(self) -> dict[str, object]:
        return {
            "canvas": {"height": 64, "width": 128},
            "labelEncoding": "uint16-region-id",
            "regions": [
                {
                    "anchor": [10 + 20 * offset, 15],
                    "areaPixels": 100,
                    "bounds": [5 + 20 * offset, 10, 16 + 20 * offset, 21],
                    "contour": [
                        [5 + 20 * offset, 10],
                        [15 + 20 * offset, 10],
                        [15 + 20 * offset, 20],
                        [5 + 20 * offset, 20],
                    ],
                    "id": index,
                    "key": key,
                    "metadata": {"fixture": True},
                    "type": "pocket",
                }
                for offset, (index, key) in enumerate(
                    enumerate(self.region_keys, start=1)
                )
            ],
            "schemaVersion": 1,
            "stage": 2,
        }

    def _stage3_document(
        self, source_regions: list[Mapping[str, object]]
    ) -> dict[str, object]:
        return {
            "canvas": {"height": 64, "width": 128},
            "pieceCount": 1,
            "regions": [
                {
                    "anchor": list(region["anchor"]),
                    "displayPath": _contour_display_path(region["contour"]),
                    "id": region["id"],
                    "key": region["key"],
                    "metadata": dict(region["metadata"]),
                    "pieceIndex": 0,
                    "primitive": "fixture-polygon",
                    "type": region["type"],
                }
                for region in source_regions
            ],
            "schemaVersion": 1,
            "silhouettePaths": [
                {
                    "displayPath": "M 0 0 L 128 0 L 128 64 L 0 64 Z",
                    "id": "piece-01-silhouette",
                    "pieceIndex": 0,
                    "primitive": "fixture-polygon",
                }
            ],
            "stage": 3,
        }

    def _stage4_document(
        self, source_regions: list[Mapping[str, object]]
    ) -> dict[str, object]:
        return {
            "canvas": {"height": 64, "width": 128},
            "regions": [
                {
                    "id": region["id"],
                    "key": region["key"],
                    "type": region["type"],
                }
                for region in source_regions
            ],
            "schemaVersion": 1,
            "stage": 4,
        }


class _BrokenStage3Runner(_StubStageRunner):
    def __init__(self, decoy_keys: tuple[str, ...], mutation: str) -> None:
        super().__init__(3, decoy_keys)
        assert mutation in {"mutate", "drop", "reorder"}
        self.mutation = mutation

    def _stage3_document(
        self, source_regions: list[Mapping[str, object]]
    ) -> dict[str, object]:
        corrupted = deepcopy(source_regions)
        if self.mutation == "mutate":
            corrupted[0]["key"] = "changed-key"
        elif self.mutation == "drop":
            corrupted.pop()
        else:
            corrupted[0], corrupted[1] = corrupted[1], corrupted[0]
        return super()._stage3_document(corrupted)


def _stage_document(run_root: Path, stage: int, filename: str) -> dict[str, object]:
    manifest = json.loads((run_root / "run.json").read_text(encoding="utf-8"))
    record = manifest["stages"][stage]
    document = json.loads(
        (run_root / record["artifactRoot"] / filename).read_text(encoding="utf-8")
    )
    assert isinstance(document, dict)
    return document


def _accepted_stage_document(
    context: RunContext,
    stage: int,
    acceptance_field: str,
    filename: str,
) -> dict[str, object]:
    record = context.manifest["stages"][stage]
    assert record["status"] == "approved"
    acceptance_path = context.root / record["acceptancePath"]
    assert _hash_file(acceptance_path) == record["acceptanceSha256"]
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    binding = acceptance[acceptance_field]
    artifact_path = context.root / binding["path"]
    assert artifact_path.name == filename
    assert _hash_file(artifact_path) == binding["fileSha256"]
    document = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _contour_display_path(contour: object) -> str:
    assert isinstance(contour, list) and len(contour) >= 3
    first, *remaining = contour
    commands = [f"M {first[0]} {first[1]}"]
    commands.extend(f"L {point[0]} {point[1]}" for point in remaining)
    return " ".join((*commands, "Z"))


def _region_identity(
    document: Mapping[str, object],
) -> tuple[list[object], list[object]]:
    regions = document["regions"]
    assert isinstance(regions, list)
    return (
        [region["id"] for region in regions],
        [region["key"] for region in regions],
    )


def _assert_stable_identity_chain(*documents: Mapping[str, object]) -> None:
    identities = [_region_identity(document) for document in documents]
    assert all(identity == identities[0] for identity in identities[1:]), (
        "stable region identity did not propagate between stages"
    )


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
