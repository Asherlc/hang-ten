from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from threading import Event, Lock

from PIL import Image
import numpy as np
import pytest

import hangboard_vectorizer.workbench as workbench_module
from hangboard_vectorizer.board_library import (
    BoardLibraryError,
    LibraryBoard,
    RepositoryBoardLibrary,
)
from hangboard_vectorizer.generic_stage0 import StageCheckpoint
from hangboard_vectorizer.onboard_cli import main
from hangboard_vectorizer.onboarding_run import RunContext, start_run
from hangboard_vectorizer.workbench import WorkbenchService, WorkbenchView
from hangboard_vectorizer.workbench_store import WorkbenchStore


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


def test_checkout_repository_library_discovers_compact_ii() -> None:
    repository_root = Path(__file__).resolve().parents[3]

    snapshot = RepositoryBoardLibrary(repository_root).snapshot()

    assert "metolius-wood-grips-compact-ii" in {
        board.board_id for board in snapshot.boards
    }
    assert snapshot.diagnostics == ()


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


def test_open_library_board_links_the_exact_token_returned_by_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library, entry = _repository_library(tmp_path)
    service = _fixture_service(tmp_path / "workspace", library=library)
    newer_run = _complete_runtime_board(
        _fixture_service(tmp_path / "newer-seed"),
        entry.display_name,
        color=(90, 110, 130),
    )
    actual_copy = library.copy_current_run
    advanced_revisions = []

    def advance_current_then_copy(board_id: str, destination: Path) -> LibraryBoard:
        advanced_revisions.append(
            library.publish(
                run_root=newer_run.run_root,
                board_id=entry.board_id,
                expected_revision_token=entry.revision_token,
            )
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
        opened.board_id, stage=3, expected_revision_id=opened.revision_id
    )
    changed = _complete_runtime_board(
        _fixture_service(tmp_path / "changed-seed"),
        entry.display_name,
        color=(90, 110, 130),
    )
    published = library.publish(
        run_root=changed.run_root,
        board_id=entry.board_id,
        expected_revision_token=entry.revision_token,
    )

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
        opened.board_id, stage=3, expected_revision_id=opened.revision_id
    )
    changed = _complete_runtime_board(
        _fixture_service(tmp_path / "changed-seed"),
        entry.display_name,
        color=(90, 110, 130),
    )
    library.publish(
        run_root=changed.run_root,
        board_id=entry.board_id,
        expected_revision_token=entry.revision_token,
    )

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


def test_parallel_library_opens_share_one_runtime_board(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library, entry = _repository_library(tmp_path)
    service = _fixture_service(tmp_path / "workspace", library=library)
    actual_copy = library.copy_current_run
    copy_guard = Lock()
    first_copy = Event()
    release_first = Event()
    copy_count = 0

    def coordinate_copy(board_id: str, destination: Path) -> LibraryBoard:
        nonlocal copy_count
        with copy_guard:
            copy_count += 1
            position = copy_count
        if position == 1:
            first_copy.set()
            release_first.wait(0.5)
        else:
            release_first.set()
        return actual_copy(board_id, destination)

    monkeypatch.setattr(library, "copy_current_run", coordinate_copy)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(service.open_library_board, entry.board_id)
        assert first_copy.wait(2)
        second = executor.submit(service.open_library_board, entry.board_id)
        opened = (first.result(timeout=5), second.result(timeout=5))

    assert opened[0].board_id == opened[1].board_id
    assert opened[0].revision_id == opened[1].revision_id
    assert len(service.store.list_boards()) == 1


def test_save_repository_conflict_leaves_runtime_revision_unsaved(
    tmp_path: Path,
) -> None:
    library, entry = _repository_library(tmp_path)
    service = _fixture_service(tmp_path / "workspace", library=library)
    opened = service.open_library_board(entry.board_id)
    changed = _complete_runtime_board(
        _fixture_service(tmp_path / "changed-seed"),
        entry.display_name,
        color=(90, 110, 130),
    )
    library.publish(
        run_root=changed.run_root,
        board_id=entry.board_id,
        expected_revision_token=entry.revision_token,
    )

    with pytest.raises(BoardLibraryError, match="publication conflict"):
        service.save(
            opened.board_id, expected_revision_id=opened.revision_id
        )

    runtime_board = service.store.read_board(opened.board_id)
    assert runtime_board.saved_revision_id is None
    assert runtime_board.repository_revision_token == entry.revision_token


def test_save_new_board_publishes_then_links_runtime_record(tmp_path: Path) -> None:
    library = _empty_repository_library(tmp_path / "repository")
    service = _fixture_service(tmp_path / "workspace", library=library)
    complete = _complete_runtime_board(service, "Example Board")

    saved = service.save(
        complete.board_id, expected_revision_id=complete.revision_id
    )

    entries = library.snapshot().boards
    assert [(entry.board_id, entry.display_name) for entry in entries] == [
        (saved.repository_board_id, complete.product_name)
    ]
    assert saved.repository_revision_token == entries[0].revision_token
    assert saved.saved is True


def test_save_existing_board_uses_expected_repository_revision_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library, entry = _repository_library(tmp_path)
    service = _fixture_service(tmp_path / "workspace", library=library)
    opened = service.open_library_board(entry.board_id)
    revised = service.revise_stage(
        opened.board_id, stage=3, expected_revision_id=opened.revision_id
    )
    complete = _approve_to_completion(service, revised)
    expected_tokens = []
    actual_publish = library.publish

    def record_expected_token(
        *,
        run_root: Path,
        board_id: str | None,
        expected_revision_token: str | None,
    ):
        expected_tokens.append(expected_revision_token)
        return actual_publish(
            run_root=run_root,
            board_id=board_id,
            expected_revision_token=expected_revision_token,
        )

    monkeypatch.setattr(library, "publish", record_expected_token)

    saved = service.save(
        complete.board_id, expected_revision_id=complete.revision_id
    )

    assert saved.repository_revision_token != entry.revision_token
    assert expected_tokens == [entry.revision_token]


@pytest.mark.parametrize("existing_board", (False, True))
def test_save_retry_reconciles_publication_after_atomic_runtime_update_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing_board: bool,
) -> None:
    if existing_board:
        library, entry = _repository_library(tmp_path)
        service = _fixture_service(tmp_path / "workspace", library=library)
        complete = service.open_library_board(entry.board_id)
    else:
        library = _empty_repository_library(tmp_path / "repository")
        service = _fixture_service(tmp_path / "workspace", library=library)
        complete = _complete_runtime_board(service, "Example Board")
    actual_publish = service.store.publish_repository_revision
    attempts = 0

    def fail_once(*args: object, **kwargs: object):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("runtime publication update interrupted")
        return actual_publish(*args, **kwargs)

    monkeypatch.setattr(service.store, "publish_repository_revision", fail_once)
    with pytest.raises(OSError, match="runtime publication update interrupted"):
        service.save(complete.board_id, expected_revision_id=complete.revision_id)

    saved = service.save(
        complete.board_id, expected_revision_id=complete.revision_id
    )
    repository_board = library.get_board(saved.repository_board_id)
    assert saved.saved is True
    assert len(library.snapshot().boards) == 1
    assert repository_board.revision_token == saved.repository_revision_token


def test_independent_workspaces_with_identical_local_ids_conflict_on_save(
    tmp_path: Path,
) -> None:
    library, entry = _repository_library(tmp_path)
    first_service = _fixture_service(tmp_path / "workspace-a", library=library)
    second_service = _fixture_service(tmp_path / "workspace-b", library=library)
    first_opened = first_service.open_library_board(entry.board_id)
    second_opened = second_service.open_library_board(entry.board_id)
    first_complete = _approve_to_completion(
        first_service,
        first_service.revise_stage(
            first_opened.board_id,
            stage=3,
            expected_revision_id=first_opened.revision_id,
        ),
    )
    second_complete = _approve_to_completion(
        second_service,
        second_service.revise_stage(
            second_opened.board_id,
            stage=3,
            expected_revision_id=second_opened.revision_id,
        ),
    )
    assert (first_complete.board_id, first_complete.revision_id) == (
        second_complete.board_id,
        second_complete.revision_id,
    )

    first_service.save(
        first_complete.board_id,
        expected_revision_id=first_complete.revision_id,
    )

    with pytest.raises(BoardLibraryError, match="conflict"):
        second_service.save(
            second_complete.board_id,
            expected_revision_id=second_complete.revision_id,
        )


def test_repository_save_uses_one_combined_runtime_metadata_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _empty_repository_library(tmp_path / "repository")
    service = _fixture_service(tmp_path / "workspace", library=library)
    complete = _complete_runtime_board(service, "Example Board")

    def reject_legacy_update(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("split repository metadata update was used")

    monkeypatch.setattr(service.store, "link_repository_revision", reject_legacy_update)
    monkeypatch.setattr(service.store, "save_revision", reject_legacy_update)

    saved = service.save(
        complete.board_id, expected_revision_id=complete.revision_id
    )

    assert saved.saved is True
    assert saved.repository_board_id == "example-board"


@pytest.mark.parametrize(("product_name", "color", "region_keys"), _BOARD_FIXTURES)
def test_product_neutral_repository_replay(
    tmp_path: Path,
    product_name: str,
    color: tuple[int, int, int],
    region_keys: tuple[str, ...],
) -> None:
    library, entry = _repository_library(
        tmp_path, product_name=product_name, color=color, region_keys=region_keys
    )
    service = _fixture_service(
        tmp_path / "workspace", region_keys=region_keys, library=library
    )

    opened = service.open_library_board(entry.board_id)
    revised = service.revise_stage(
        opened.board_id, stage=3, expected_revision_id=opened.revision_id
    )
    complete = _approve_to_completion(service, revised)
    saved = service.save(
        complete.board_id, expected_revision_id=complete.revision_id
    )
    reopened = service.open_library_board(entry.board_id)

    assert saved.repository_revision_token != entry.revision_token
    assert reopened.repository_revision_token == saved.repository_revision_token


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
    editor_root = Path(__file__).resolve().parents[2] / "hold-highlight-editor"
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
    library_root = root / "Tools" / "HangboardOnboarding" / "boards"
    library_root.mkdir(parents=True)
    return RepositoryBoardLibrary(root)


def _repository_library(
    root: Path,
    *,
    product_name: str = "Example Board",
    color: tuple[int, int, int] = (45, 65, 85),
    region_keys: tuple[str, ...] = ("grip-001",),
) -> tuple[RepositoryBoardLibrary, LibraryBoard]:
    library = _empty_repository_library(root / "repository")
    seed = _fixture_service(root / "seed", region_keys=region_keys)
    complete = _complete_runtime_board(seed, product_name, color=color)
    published = library.publish(
        run_root=complete.run_root,
        board_id=None,
        expected_revision_token=None,
    )
    return library, published.board


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
