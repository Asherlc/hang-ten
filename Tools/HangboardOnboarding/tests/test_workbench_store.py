from __future__ import annotations

import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from uuid import UUID

import pytest

from hangboard_vectorizer.workbench_store import WorkbenchStore, WorkbenchStoreError


def test_store_creates_cli_compatible_revision_layout(tmp_path):
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Metolius Simulator 3D")
    revision = store.create_revision(board.id)
    assert revision.run_root == tmp_path / "boards" / board.id / "revisions" / "revision-0001" / "run"
    assert revision.state == "pending"
    assert store.read_board(board.id).active_revision_id == ""


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

    assert manifest["schemaVersion"] == 1
    assert manifest["revisions"][0]["runRoot"] == "revisions/revision-0001/run"
    assert reopened.product_name == "Example Board"
    assert reopened.revisions == (revision,)


def test_prepare_publication_operation_is_persisted_and_stable(
    tmp_path: Path,
) -> None:
    store, board, revision = _populated_store(tmp_path)

    first = store.prepare_repository_publication(board.id, revision.id)
    second = store.prepare_repository_publication(board.id, revision.id)

    assert first == second
    assert UUID(first).version == 4
    assert store.read_revision(
        board.id, revision.id
    ).publication_operation_id == first


def test_independent_workspaces_never_share_publication_operation(
    tmp_path: Path,
) -> None:
    first_store, first_board, first_revision = _populated_store(
        tmp_path / "workspace-a"
    )
    second_store, second_board, second_revision = _populated_store(
        tmp_path / "workspace-b"
    )

    first = first_store.prepare_repository_publication(
        first_board.id, first_revision.id
    )
    second = second_store.prepare_repository_publication(
        second_board.id, second_revision.id
    )

    assert first != second


def test_two_store_instances_prepare_one_persisted_publication_operation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_store, board, revision = _populated_store(tmp_path)
    second_store = WorkbenchStore(tmp_path)
    first_reached_write = Event()
    second_read_stale_manifest = Event()
    actual_first_write = first_store._write_board
    actual_second_read = second_store.read_board

    def pause_first_write(*args: object, **kwargs: object) -> None:
        first_reached_write.set()
        second_read_stale_manifest.wait(0.5)
        actual_first_write(*args, **kwargs)

    def record_second_read(board_id: str):
        result = actual_second_read(board_id)
        second_read_stale_manifest.set()
        return result

    monkeypatch.setattr(first_store, "_write_board", pause_first_write)
    monkeypatch.setattr(second_store, "read_board", record_second_read)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            first_store.prepare_repository_publication, board.id, revision.id
        )
        assert first_reached_write.wait(2)
        second = executor.submit(
            second_store.prepare_repository_publication, board.id, revision.id
        )
        operation_ids = (first.result(timeout=3), second.result(timeout=3))

    assert operation_ids[0] == operation_ids[1]
    assert WorkbenchStore(tmp_path).read_revision(
        board.id, revision.id
    ).publication_operation_id == operation_ids[0]


def test_store_loads_old_revision_without_publication_operation(
    tmp_path: Path,
) -> None:
    store, board, revision = _populated_store(tmp_path)
    manifest_path = tmp_path / "boards" / board.id / "board.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["revisions"][0].pop("publicationOperationId", None)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    reopened = WorkbenchStore(tmp_path).read_revision(board.id, revision.id)

    assert reopened.publication_operation_id is None


def test_store_persists_repository_link_without_changing_runtime_id(
    tmp_path: Path,
) -> None:
    store = WorkbenchStore(tmp_path)
    board, _revision = store.reserve_initial_revision("Example Board")

    linked = store.link_repository_version(
        board.id,
        repository_board_id="example-board",
        repository_version_id="revision-0001",
    )

    assert linked.id == board.id
    assert linked.repository_board_id == "example-board"
    assert linked.repository_version_id == "revision-0001"
    assert store.read_board(board.id) == linked


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
        repository_version_id="revision-0001",
    )

    assert published.active_revision_id == revision.id
    assert published.saved_revision_id == revision.id
    assert published.repository_board_id == "example-board"
    assert published.repository_version_id == "revision-0001"
    assert WorkbenchStore(tmp_path).read_board(board.id) == published


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
            repository_version_id="revision-0001",
        )

    assert WorkbenchStore(tmp_path).read_board(board.id) == before


def test_store_loads_old_manifest_without_repository_link(tmp_path: Path) -> None:
    store, board, _revision = _populated_store(tmp_path)
    manifest_path = tmp_path / "boards" / board.id / "board.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("repositoryBoardId")
    manifest.pop("repositoryVersionId")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    reopened = WorkbenchStore(tmp_path).read_board(board.id)

    assert reopened.repository_board_id is None
    assert reopened.repository_version_id is None


@pytest.mark.parametrize(
    ("repository_board_id", "repository_version_id"),
    (("example-board", None), (None, "revision-0001")),
)
def test_store_rejects_incomplete_repository_links(
    tmp_path: Path,
    repository_board_id: str | None,
    repository_version_id: str | None,
) -> None:
    store, board, _revision = _populated_store(tmp_path)

    with pytest.raises(WorkbenchStoreError, match="provided together"):
        store.link_repository_version(
            board.id,
            repository_board_id=repository_board_id,  # type: ignore[arg-type]
            repository_version_id=repository_version_id,  # type: ignore[arg-type]
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
    barrier = Barrier(8)

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
