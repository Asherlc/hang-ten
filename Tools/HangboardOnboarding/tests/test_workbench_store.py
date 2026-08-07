from __future__ import annotations

import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from hangboard_vectorizer.workbench_store import WorkbenchStore, WorkbenchStoreError


def test_store_creates_cli_compatible_revision_layout(tmp_path):
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Metolius Simulator 3D")
    revision = store.create_revision(board.id)
    assert revision.run_root == tmp_path / "boards" / board.id / "revisions" / "revision-0001" / "run"
    assert store.read_board(board.id).active_revision_id == "revision-0001"


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
    assert reopened.read_board(board.id).active_revision_id == revision.id
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
