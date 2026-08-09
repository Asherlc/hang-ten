from __future__ import annotations

import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from hangboard_vectorizer.workbench_store import WorkbenchStore, WorkbenchStoreError


_REVISION_TOKEN_A = "a" * 64


def test_store_creates_cli_compatible_revision_layout(tmp_path):
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Metolius Simulator 3D")
    revision = store.create_revision(board.id)
    assert revision.run_root == tmp_path / "boards" / board.id / "revisions" / "revision-0001" / "run"
    assert revision.state == "pending"
    assert store.read_board(board.id).active_revision_id == ""


def test_initial_reservation_cleanup_does_not_mask_the_publication_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = WorkbenchStore(tmp_path)

    def fail_with_residual_file(board, **_kwargs: object) -> None:
        residual = tmp_path / "boards" / board.id / ".manifest-write-residual"
        residual.write_text("incomplete", encoding="utf-8")
        raise RuntimeError("manifest publication failed")

    monkeypatch.setattr(store, "_write_board", fail_with_residual_file)

    with pytest.raises(RuntimeError, match="manifest publication failed"):
        store.reserve_initial_revision("Example Board")


def test_activate_initial_revision_is_atomic_when_manifest_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Example Board")
    revision = store.create_revision(board.id)

    def fail_replace(_source: object, _destination: object) -> None:
        raise OSError("replacement interrupted")

    monkeypatch.setattr("hangboard_vectorizer.workbench_store.os.replace", fail_replace)

    with pytest.raises(OSError, match="replacement interrupted"):
        store.activate_revision(board.id, revision.id)

    persisted = WorkbenchStore(tmp_path).read_board(board.id)
    assert persisted.active_revision_id == ""
    assert persisted.revisions[0].state == "pending"


def test_activate_fork_revision_publishes_child_and_stale_parent_together(
    tmp_path: Path,
) -> None:
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Example Board")
    parent = store.create_revision(board.id)
    store.activate_revision(board.id, parent.id)
    child = store.create_revision(
        board.id, parent_revision_id=parent.id, fork_stage=2
    )

    activated = store.activate_revision(
        board.id,
        child.id,
        stale_parent_revision_id=parent.id,
        stale_from_stage=2,
    )

    reopened = WorkbenchStore(tmp_path).read_board(board.id)
    records = {revision.id: revision for revision in reopened.revisions}
    assert activated.id == child.id
    assert reopened.active_revision_id == child.id
    assert records[child.id].state == "active"
    assert records[parent.id].stale_from_stage == 2


@pytest.mark.parametrize(
    ("stale_parent_revision_id", "stale_from_stage"),
    [("revision-0001", None), (None, 2)],
)
def test_activate_revision_requires_paired_stale_parent_arguments(
    tmp_path: Path,
    stale_parent_revision_id: str | None,
    stale_from_stage: int | None,
) -> None:
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Example Board")
    revision = store.create_revision(board.id)

    with pytest.raises(WorkbenchStoreError, match="provided together"):
        store.activate_revision(
            board.id,
            revision.id,
            stale_parent_revision_id=stale_parent_revision_id,
            stale_from_stage=stale_from_stage,
        )


def test_activate_fork_revision_requires_atomic_parent_stale_marker(
    tmp_path: Path,
) -> None:
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Example Board")
    parent = store.create_revision(board.id)
    store.activate_revision(board.id, parent.id)
    child = store.create_revision(
        board.id, parent_revision_id=parent.id, fork_stage=2
    )

    with pytest.raises(WorkbenchStoreError, match="stale parent"):
        store.activate_revision(board.id, child.id)

    persisted = store.read_board(board.id)
    assert persisted.active_revision_id == parent.id
    assert persisted.revisions[-1].state == "pending"


def test_synchronize_revision_cannot_publish_a_pending_reservation(
    tmp_path: Path,
) -> None:
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Example Board")
    revision = store.create_revision(board.id)

    with pytest.raises(WorkbenchStoreError, match="pending activation"):
        store.synchronize_revision(
            board.id,
            revision.id,
            current_stage=0,
            state="active",
        )

    persisted = store.read_board(board.id)
    assert persisted.active_revision_id == ""
    assert persisted.revisions[0].state == "pending"


def test_competing_fork_activation_cannot_overwrite_the_winning_child(
    tmp_path: Path,
) -> None:
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Example Board")
    parent = store.create_revision(board.id)
    store.activate_revision(board.id, parent.id)
    first = store.create_revision(
        board.id, parent_revision_id=parent.id, fork_stage=2
    )
    second = store.create_revision(
        board.id, parent_revision_id=parent.id, fork_stage=2
    )
    store.activate_revision(
        board.id,
        first.id,
        stale_parent_revision_id=parent.id,
        stale_from_stage=2,
    )

    with pytest.raises(WorkbenchStoreError, match="active revision changed"):
        store.activate_revision(
            board.id,
            second.id,
            stale_parent_revision_id=parent.id,
            stale_from_stage=2,
        )

    persisted = store.read_board(board.id)
    records = {revision.id: revision for revision in persisted.revisions}
    assert persisted.active_revision_id == first.id
    assert records[first.id].state == "active"
    assert records[second.id].state == "pending"


def test_mark_failed_fork_preserves_the_current_active_revision_atomically(
    tmp_path: Path,
) -> None:
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Example Board")
    parent = store.create_revision(board.id)
    store.activate_revision(board.id, parent.id)
    loser = store.create_revision(
        board.id, parent_revision_id=parent.id, fork_stage=2
    )
    winner = store.create_revision(
        board.id, parent_revision_id=parent.id, fork_stage=2
    )
    store.activate_revision(
        board.id,
        winner.id,
        stale_parent_revision_id=parent.id,
        stale_from_stage=2,
    )

    store.mark_revision_failed(
        board.id,
        loser.id,
        restore_active_revision_id=None,
    )

    persisted = store.read_board(board.id)
    records = {revision.id: revision for revision in persisted.revisions}
    assert persisted.active_revision_id == winner.id
    assert records[loser.id].state == "failed"


def test_save_revision_is_atomic_and_rejects_stale_lineage(tmp_path):
    store, board, first = _populated_store(tmp_path)
    second = store.create_revision(board.id, parent_revision_id=first.id, fork_stage=2)
    store.mark_descendants_stale(board.id, first.id, from_stage=2)
    with pytest.raises(WorkbenchStoreError, match="stale"):
        store.save_revision(board.id, first.id)
    store.mark_revision_complete(board.id, second.id)
    assert store.save_revision(board.id, second.id).saved_revision_id == second.id


def test_board_manifest_is_schema_versioned_and_survives_reopening(tmp_path: Path) -> None:
    store, board, revision = _populated_store(tmp_path)

    manifest = json.loads(
        (tmp_path / "boards" / board.id / "board.json").read_text(encoding="utf-8")
    )
    reopened = WorkbenchStore(tmp_path).read_board(board.id)

    assert manifest["schemaVersion"] == 2
    assert manifest["revisions"][0]["runRoot"] == "revisions/revision-0001/run"
    assert "repositoryVersionId" not in manifest
    assert "publicationOperationId" not in manifest["revisions"][0]
    assert reopened.product_name == "Example Board"
    assert reopened.revisions == (revision,)


def test_schema_1_repository_link_loads_safely_and_migrates_on_next_mutation(
    tmp_path: Path,
) -> None:
    store, board, revision = _populated_store(tmp_path)
    second = store.create_revision(board.id)
    manifest_path = tmp_path / "boards" / board.id / "board.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schemaVersion"] = 1
    manifest["repositoryBoardId"] = "example-board"
    manifest["repositoryVersionId"] = "revision-0042"
    manifest.pop("repositoryRevisionToken", None)
    manifest["revisions"][0]["publicationOperationId"] = (
        "77377ba8-d4e7-48aa-afb4-5a762f3f7040"
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    legacy = WorkbenchStore(tmp_path).read_board(board.id)

    assert tuple(item.id for item in legacy.revisions) == (revision.id, second.id)
    assert legacy.repository_board_id == "example-board"
    assert legacy.repository_revision_token is None
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["schemaVersion"] == 1

    store.mark_descendants_stale(board.id, revision.id, from_stage=2)
    migrated = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert migrated["schemaVersion"] == 2
    assert migrated["repositoryBoardId"] == "example-board"
    assert migrated["repositoryRevisionToken"] is None
    assert "repositoryVersionId" not in migrated
    assert all(
        "publicationOperationId" not in item for item in migrated["revisions"]
    )


def test_store_persists_repository_revision_without_changing_runtime_id(
    tmp_path: Path,
) -> None:
    store = WorkbenchStore(tmp_path)
    board, _revision = store.reserve_initial_revision("Example Board")

    linked = store.link_repository_revision(
        board.id,
        repository_board_id="example-board",
        repository_revision_token=_REVISION_TOKEN_A,
    )

    assert linked.id == board.id
    assert linked.repository_board_id == "example-board"
    assert linked.repository_revision_token == _REVISION_TOKEN_A
    assert store.read_board(board.id) == linked


def test_finalize_repository_open_publishes_complete_active_link_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = WorkbenchStore(tmp_path)
    board, revision = store.reserve_initial_revision("Example Board")
    writes = []
    actual_write = store._write_board

    def record_write(updated, *args: object, **kwargs: object) -> None:
        writes.append(updated)
        actual_write(updated, *args, **kwargs)

    monkeypatch.setattr(store, "_write_board", record_write)

    finalized = store.finalize_repository_open(
        board.id,
        revision.id,
        repository_board_id="example-board",
        repository_revision_token=_REVISION_TOKEN_A,
    )

    assert len(writes) == 1
    assert finalized == store.read_board(board.id)
    assert finalized.active_revision_id == revision.id
    assert finalized.repository_board_id == "example-board"
    assert finalized.repository_revision_token == _REVISION_TOKEN_A
    assert finalized.saved_revision_id is None
    persisted_revision = store.read_revision(board.id, revision.id)
    assert persisted_revision.current_stage == 4
    assert persisted_revision.state == "complete"


def test_finalize_repository_open_interruption_preserves_pending_unlinked_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = WorkbenchStore(tmp_path)
    board, revision = store.reserve_initial_revision("Example Board")
    before = store.read_board(board.id)

    def fail_replace(_source: object, _destination: object) -> None:
        raise OSError("repository open replacement interrupted")

    monkeypatch.setattr("hangboard_vectorizer.workbench_store.os.replace", fail_replace)

    with pytest.raises(OSError, match="repository open replacement interrupted"):
        store.finalize_repository_open(
            board.id,
            revision.id,
            repository_board_id="example-board",
            repository_revision_token=_REVISION_TOKEN_A,
        )

    assert WorkbenchStore(tmp_path).read_board(board.id) == before


def test_publish_repository_revision_updates_link_and_saved_revision_atomically(
    tmp_path: Path,
) -> None:
    store, board, revision = _populated_store(tmp_path)
    store.activate_revision(board.id, revision.id)
    store.mark_revision_complete(board.id, revision.id)

    published = store.publish_repository_revision(
        board.id,
        revision.id,
        repository_board_id="example-board",
        repository_revision_token=_REVISION_TOKEN_A,
    )

    assert published.active_revision_id == revision.id
    assert published.saved_revision_id == revision.id
    assert published.repository_board_id == "example-board"
    assert published.repository_revision_token == _REVISION_TOKEN_A
    assert WorkbenchStore(tmp_path).read_board(board.id) == published


def test_repository_preflight_is_read_only_for_the_active_complete_revision(
    tmp_path: Path,
) -> None:
    store, board, revision = _populated_store(tmp_path)
    store.activate_revision(board.id, revision.id)
    store.mark_revision_complete(board.id, revision.id)
    manifest_path = tmp_path / "boards" / board.id / "board.json"
    before = manifest_path.read_bytes()

    validated = store.preflight_repository_revision(board.id, revision.id)

    assert validated.id == revision.id
    assert manifest_path.read_bytes() == before


@pytest.mark.parametrize("operation", ("preflight", "finalize"))
def test_repository_publication_gates_reject_a_non_active_complete_revision(
    tmp_path: Path, operation: str
) -> None:
    store, board, active = _populated_store(tmp_path)
    store.activate_revision(board.id, active.id)
    store.mark_revision_complete(board.id, active.id)
    inactive = store.create_revision(board.id)
    store.mark_revision_complete(board.id, inactive.id)
    before = store.read_board(board.id)

    with pytest.raises(WorkbenchStoreError, match="active revision changed"):
        if operation == "preflight":
            store.preflight_repository_revision(board.id, inactive.id)
        else:
            store.publish_repository_revision(
                board.id,
                inactive.id,
                repository_board_id="example-board",
                repository_revision_token=_REVISION_TOKEN_A,
            )

    assert store.read_board(board.id) == before


def test_publish_repository_revision_failure_preserves_all_previous_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, board, revision = _populated_store(tmp_path)
    store.activate_revision(board.id, revision.id)
    store.mark_revision_complete(board.id, revision.id)
    before = store.read_board(board.id)

    def fail_replace(_source: object, _destination: object) -> None:
        raise OSError("repository metadata replacement interrupted")

    monkeypatch.setattr("hangboard_vectorizer.workbench_store.os.replace", fail_replace)
    with pytest.raises(OSError, match="repository metadata replacement interrupted"):
        store.publish_repository_revision(
            board.id,
            revision.id,
            repository_board_id="example-board",
            repository_revision_token=_REVISION_TOKEN_A,
        )

    assert WorkbenchStore(tmp_path).read_board(board.id) == before


def test_store_loads_old_manifest_without_repository_link(tmp_path: Path) -> None:
    store, board, _revision = _populated_store(tmp_path)
    manifest_path = tmp_path / "boards" / board.id / "board.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("repositoryBoardId")
    manifest.pop("repositoryRevisionToken")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    reopened = WorkbenchStore(tmp_path).read_board(board.id)

    assert reopened.repository_board_id is None
    assert reopened.repository_revision_token is None


@pytest.mark.parametrize(
    ("repository_board_id", "repository_revision_token"),
    ((None, _REVISION_TOKEN_A),),
)
def test_store_rejects_revision_token_without_repository_board_id(
    tmp_path: Path,
    repository_board_id: str | None,
    repository_revision_token: str | None,
) -> None:
    store, board, _revision = _populated_store(tmp_path)

    with pytest.raises(WorkbenchStoreError, match="provided together"):
        store.link_repository_revision(
            board.id,
            repository_board_id=repository_board_id,  # type: ignore[arg-type]
            repository_revision_token=repository_revision_token,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("revision_token", ("a" * 63, "A" * 64, "g" * 64))
def test_store_rejects_invalid_repository_revision_token(
    tmp_path: Path, revision_token: str
) -> None:
    store, board, _revision = _populated_store(tmp_path)

    with pytest.raises(WorkbenchStoreError, match="revision token"):
        store.link_repository_revision(
            board.id,
            repository_board_id="example-board",
            repository_revision_token=revision_token,
        )


def test_write_draft_publishes_new_immutable_documents(tmp_path: Path) -> None:
    store, board, revision = _populated_store(tmp_path)

    first = store.write_draft(board.id, revision.id, 2, {"regions": ["first"]})
    second = store.write_draft(board.id, revision.id, 2, {"regions": ["second"]})

    assert first == (
        tmp_path
        / "boards"
        / board.id
        / "revisions"
        / revision.id
        / "drafts"
        / "stage-2"
        / "draft-0001.json"
    )
    assert second.name == "draft-0002.json"
    assert json.loads(first.read_text(encoding="utf-8")) == {"regions": ["first"]}
    assert json.loads(second.read_text(encoding="utf-8")) == {"regions": ["second"]}


def test_register_run_preserves_a_confined_existing_cli_root(
    tmp_path: Path,
) -> None:
    store = WorkbenchStore(tmp_path)
    cli_run = tmp_path / "cli-run"
    cli_run.mkdir()

    board, revision = store.register_run("Example Board", cli_run)
    reopened = WorkbenchStore(tmp_path).read_revision(board.id, revision.id)

    assert revision.run_root == cli_run
    assert reopened.run_root == cli_run
    assert store.read_board(board.id).active_revision_id == revision.id

    with pytest.raises(WorkbenchStoreError, match="already registered"):
        store.register_run("Duplicate", cli_run)


def test_register_run_rejects_a_root_outside_the_workspace(tmp_path: Path) -> None:
    store = WorkbenchStore(tmp_path / "workspace")
    outside = tmp_path / "outside-run"
    outside.mkdir()

    with pytest.raises(WorkbenchStoreError, match="workspace"):
        store.register_run("Example Board", outside)


def test_concurrent_board_reservations_publish_distinct_manifests(
    tmp_path: Path,
) -> None:
    store = WorkbenchStore(tmp_path)
    barrier = Barrier(8, timeout=5)

    def create(index: int):
        barrier.wait()
        return store.create_board(f"Board {index}")

    with ThreadPoolExecutor(max_workers=8) as executor:
        boards = tuple(executor.map(create, range(8)))

    assert len({board.id for board in boards}) == 8
    assert {board.id for board in store.list_boards()} == {
        board.id for board in boards
    }


def test_losing_initial_reservation_cannot_delete_another_store_winner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    winner = WorkbenchStore(tmp_path)
    loser = WorkbenchStore(tmp_path)
    original_next_id = loser._next_numbered_id
    winning_reservation = None

    def collide(
        root: Path,
        pattern: object,
        prefix: str,
        **kwargs: object,
    ) -> str:
        nonlocal winning_reservation
        if root == loser._boards_root and prefix == "board":
            winning_reservation = winner.reserve_initial_revision("Winner")
            return "board-0001"
        return original_next_id(root, pattern, prefix, **kwargs)

    monkeypatch.setattr(loser, "_next_numbered_id", collide)

    with pytest.raises(FileExistsError):
        loser.reserve_initial_revision("Loser")

    assert winning_reservation is not None
    winning_board, winning_revision = winning_reservation
    persisted = WorkbenchStore(tmp_path).read_board(winning_board.id)
    assert persisted.product_name == "Winner"
    assert persisted.revisions == (winning_revision,)


def test_write_draft_reports_serialization_errors_without_publishing(
    tmp_path: Path,
) -> None:
    store, board, revision = _populated_store(tmp_path)

    with pytest.raises(TypeError, match="JSON serializable"):
        store.write_draft(board.id, revision.id, 2, {"invalid": object()})

    drafts = (
        tmp_path
        / "boards"
        / board.id
        / "revisions"
        / revision.id
        / "drafts"
        / "stage-2"
    )
    assert list(drafts.iterdir()) == []


def test_save_revision_rejects_incomplete_lineage(tmp_path: Path) -> None:
    store, board, revision = _populated_store(tmp_path)

    with pytest.raises(WorkbenchStoreError, match="complete"):
        store.save_revision(board.id, revision.id)

    assert store.read_board(board.id).saved_revision_id is None


def test_failed_manifest_replace_keeps_previous_saved_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, board, first = _populated_store(tmp_path)
    store.mark_revision_complete(board.id, first.id)
    store.save_revision(board.id, first.id)
    second = store.create_revision(board.id, parent_revision_id=first.id, fork_stage=2)
    store.mark_revision_complete(board.id, second.id)

    def fail_replace(_source: object, _destination: object) -> None:
        raise OSError("replacement interrupted")

    monkeypatch.setattr("hangboard_vectorizer.workbench_store.os.replace", fail_replace)

    with pytest.raises(OSError, match="interrupted"):
        store.save_revision(board.id, second.id)

    assert store.read_board(board.id).saved_revision_id == first.id


def test_create_board_keeps_published_directory_when_directory_fsync_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = WorkbenchStore(tmp_path)

    def fail_directory_fsync(_directory: Path) -> None:
        raise OSError("directory fsync failed")

    monkeypatch.setattr(store, "_fsync_directory", fail_directory_fsync)

    with pytest.raises(OSError, match="directory fsync failed"):
        store.create_board("Example Board")

    board = WorkbenchStore(tmp_path).read_board("board-0001")
    assert board.product_name == "Example Board"
    assert (tmp_path / "boards" / board.id).is_dir()


def test_create_revision_keeps_published_directory_when_directory_fsync_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Example Board")

    def fail_directory_fsync(_directory: Path) -> None:
        raise OSError("directory fsync failed")

    monkeypatch.setattr(store, "_fsync_directory", fail_directory_fsync)

    with pytest.raises(OSError, match="directory fsync failed"):
        store.create_revision(board.id)

    reopened = WorkbenchStore(tmp_path)
    revision = reopened.read_revision(board.id, "revision-0001")
    assert reopened.read_board(board.id).active_revision_id == ""
    assert revision.state == "pending"
    assert revision.run_root.parent.is_dir()


@pytest.mark.parametrize("board_id", ["../outside", "/tmp/outside", "board/child"])
def test_store_rejects_board_id_traversal(tmp_path: Path, board_id: str) -> None:
    store = WorkbenchStore(tmp_path)

    with pytest.raises(WorkbenchStoreError, match="identifier"):
        store.read_board(board_id)


def test_store_rejects_symlink_escape_from_boards_directory(tmp_path: Path) -> None:
    store = WorkbenchStore(tmp_path / "workspace")
    outside = tmp_path / "outside"
    outside.mkdir()
    escaped_board = outside / "board.json"
    escaped_board.write_text("{}", encoding="utf-8")
    (tmp_path / "workspace" / "boards" / "board-0001").symlink_to(outside)

    with pytest.raises(WorkbenchStoreError, match="workspace"):
        store.read_board("board-0001")


def _populated_store(tmp_path):
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Example Board")
    revision = store.create_revision(board.id)
    return store, board, revision
