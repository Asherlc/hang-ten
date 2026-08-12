from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
from threading import Event, Thread

from PIL import Image
import pytest

from hangboard_vectorizer import board_library
from hangboard_vectorizer.board_library import BoardLibraryError, RepositoryBoardLibrary
from hangboard_vectorizer.generic_stage0 import StageCheckpoint
from hangboard_vectorizer.onboarding_run import (
    RunContext,
    approve_stage,
    read_status,
    resume_run,
    start_run,
)


def test_board_diagnostic_error_formats_its_message() -> None:
    error = board_library._BoardDiagnosticError("invalid_run", "broken run")

    assert str(error) == "broken run"


def test_snapshot_discovers_self_describing_runs_and_sorts_them(tmp_path: Path) -> None:
    _complete_board(tmp_path, "charlie", "charlie")
    _complete_board(tmp_path, "alpha-2", "Alpha 2")
    _complete_board(tmp_path, "alpha-1", "alpha 1")

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == [
        "alpha-1",
        "alpha-2",
        "charlie",
    ]
    assert snapshot.diagnostics == ()
    assert all(len(board.revision_token) == 64 for board in snapshot.boards)


def test_snapshot_does_not_create_repository_paths(tmp_path: Path) -> None:
    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert snapshot == board_library.LibrarySnapshot(boards=(), diagnostics=())
    assert not _boards_root(tmp_path).exists()


def test_snapshot_reports_a_symlinked_transaction_root(tmp_path: Path) -> None:
    boards = _boards_root(tmp_path)
    boards.mkdir(parents=True)
    (boards / ".transactions").symlink_to(tmp_path / "missing-transactions")

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert snapshot.boards == ()
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        (".transactions", "invalid_transaction")
    ]


def test_invalid_board_is_diagnostic_without_hiding_valid_boards(tmp_path: Path) -> None:
    _complete_board(tmp_path, "valid-board", "Valid Board")
    invalid = _complete_board(tmp_path, "wrong-directory", "Wrong Directory")
    manifest = _read_json(invalid / "run.json")
    product = manifest["product"]
    assert isinstance(product, dict)
    product["key"] = "different-key"
    _write_json(invalid / "run.json", manifest)

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["valid-board"]
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("wrong-directory", "identity_mismatch")
    ]
    assert "Tools/HangboardPipeline/boards/wrong-directory/run.json" in snapshot.diagnostics[0].message


def test_snapshot_ignores_hidden_transaction_directories(tmp_path: Path) -> None:
    _complete_board(tmp_path, "visible-board", "Visible Board")
    transaction = _boards_root(tmp_path) / ".publication.tmp-123"
    transaction.mkdir()
    (transaction / "run.json").write_text("not inspected", encoding="utf-8")

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["visible-board"]
    assert snapshot.diagnostics == ()


def test_snapshot_reports_symlinked_board_directories(tmp_path: Path) -> None:
    target = _complete_board(tmp_path, "valid-board", "Valid Board")
    (_boards_root(tmp_path) / "linked-board").symlink_to(target, target_is_directory=True)

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["valid-board"]
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("linked-board", "invalid_path")
    ]


def test_snapshot_reports_invalid_board_ids(tmp_path: Path) -> None:
    _complete_board(tmp_path, "valid-board", "Valid Board")
    invalid = _boards_root(tmp_path) / "Invalid_Board"
    invalid.mkdir()

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["valid-board"]
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("Invalid_Board", "invalid_board_id")
    ]


def test_snapshot_reports_missing_run_manifest(tmp_path: Path) -> None:
    missing = _boards_root(tmp_path) / "missing-manifest"
    missing.mkdir(parents=True)

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert snapshot.boards == ()
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("missing-manifest", "missing_manifest")
    ]
    assert "Tools/HangboardPipeline/boards/missing-manifest/run.json" in snapshot.diagnostics[0].message


def test_snapshot_reports_incomplete_runs(tmp_path: Path) -> None:
    _incomplete_board(tmp_path, "incomplete-board", "Incomplete Board")

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert snapshot.boards == ()
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("incomplete-board", "invalid_run")
    ]


def test_snapshot_reports_bad_approval_hashes(tmp_path: Path) -> None:
    run = _complete_board(tmp_path, "approval-board", "Approval Board")
    approval = run / "approvals" / "stage-3.json"
    document = _read_json(approval)
    document["decision"] = "rejected"
    _write_json(approval, document)

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert snapshot.boards == ()
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("approval-board", "invalid_run")
    ]


def test_snapshot_reports_bad_stage_four_output_hashes(tmp_path: Path) -> None:
    run = _complete_board(tmp_path, "output-board", "Output Board")
    normal = _stage_four_acceptance(run)["normal"]
    assert isinstance(normal, dict)
    output = run / str(normal["path"])
    output.write_bytes(b"changed output")

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert snapshot.boards == ()
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("output-board", "invalid_outputs")
    ]


def test_snapshot_reports_bad_stage_four_hash_when_stages_are_truncated(
    tmp_path: Path,
) -> None:
    run = _complete_board(tmp_path, "truncated-board", "Truncated Board")
    normal = _stage_four_acceptance(run)["normal"]
    assert isinstance(normal, dict)
    (run / str(normal["path"])).write_bytes(b"changed output")
    manifest = _read_json(run / "run.json")
    stages = manifest["stages"]
    assert isinstance(stages, list)
    manifest["stages"] = stages[:4]
    _write_json(run / "run.json", manifest)

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert snapshot.boards == ()
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("truncated-board", "invalid_outputs")
    ]


def test_snapshot_revision_tokens_are_deterministic(tmp_path: Path) -> None:
    run = _complete_board(tmp_path, "token-board", "Token Board")
    library = RepositoryBoardLibrary(tmp_path)

    first = library.snapshot().boards[0]
    second = library.snapshot().boards[0]

    assert first.revision_token == second.revision_token
    assert first.revision_token == sha256((run / "run.json").read_bytes()).hexdigest()


def test_package_validation_scans_the_run_tree_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = _complete_board(tmp_path, "scan-board", "Scan Board")
    library = RepositoryBoardLibrary(tmp_path)
    original = library._reject_tree_symlinks
    scanned: list[Path] = []

    def record_scan(root: Path) -> None:
        scanned.append(root)
        original(root)

    monkeypatch.setattr(library, "_reject_tree_symlinks", record_scan)

    library._validated_package(run)

    assert scanned == [run]


def test_copy_current_run_copies_only_a_validated_confined_run(tmp_path: Path) -> None:
    run = _complete_board(tmp_path, "copy-board", "Copy Board")
    destination = tmp_path / "runtime" / "run"

    board = RepositoryBoardLibrary(tmp_path).copy_current_run("copy-board", destination)

    assert board.run_path == run
    assert destination != run
    assert read_status(destination)["status"] == "complete"
    assert not list(destination.parent.glob(f".{destination.name}.tmp-*"))


def test_copy_current_run_rejects_parent_directory_components(tmp_path: Path) -> None:
    _complete_board(tmp_path, "copy-board", "Copy Board")
    destination = tmp_path / "runtime" / ".." / "escaped-run"

    with pytest.raises(BoardLibraryError, match="parent-directory"):
        RepositoryBoardLibrary(tmp_path).copy_current_run(
            "copy-board", destination
        )

    assert not (tmp_path / "escaped-run").exists()


def test_copy_current_run_returns_identity_from_the_exact_copied_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    canonical = _complete_board(repository, "copy-board", "Copy Board")
    replacement = _complete_board(
        tmp_path / "replacement", "copy-board", "Copy Board"
    )
    library = RepositoryBoardLibrary(repository)
    before = library.get_board("copy-board")
    replacement_token = sha256((replacement / "run.json").read_bytes()).hexdigest()
    destination = tmp_path / "runtime" / "run"
    original_copy = library._copy_tree

    def replace_out_of_band_then_copy(source: Path, target: Path) -> None:
        shutil.rmtree(source)
        shutil.copytree(replacement, source)
        original_copy(source, target)

    monkeypatch.setattr(library, "_copy_tree", replace_out_of_band_then_copy)

    copied = library.copy_current_run("copy-board", destination)

    assert replacement_token != before.revision_token
    assert copied.run_path == canonical
    assert copied.revision_token == replacement_token
    assert copied.revision_token == sha256(
        (destination / "run.json").read_bytes()
    ).hexdigest()
    assert (
        sha256((canonical / "run.json").read_bytes()).hexdigest()
        == replacement_token
    )


def test_copy_current_run_rejects_an_out_of_band_board_identity_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _complete_board(repository, "copy-board", "Copy Board")
    replacement = _complete_board(
        tmp_path / "replacement", "different-board", "Different Board"
    )
    library = RepositoryBoardLibrary(repository)
    destination = tmp_path / "runtime" / "run"
    original_copy = library._copy_tree

    def replace_out_of_band_then_copy(source: Path, target: Path) -> None:
        shutil.rmtree(source)
        shutil.copytree(replacement, source)
        original_copy(source, target)

    monkeypatch.setattr(library, "_copy_tree", replace_out_of_band_then_copy)

    with pytest.raises(BoardLibraryError, match="requested board"):
        library.copy_current_run("copy-board", destination)

    assert not destination.exists()


def test_copy_current_run_rejects_a_symlinked_destination_parent(tmp_path: Path) -> None:
    _complete_board(tmp_path, "copy-board", "Copy Board")
    outside = tmp_path / "outside"
    outside.mkdir()
    runtime = tmp_path / "runtime"
    runtime.symlink_to(outside, target_is_directory=True)

    with pytest.raises(BoardLibraryError, match="symlink"):
        RepositoryBoardLibrary(tmp_path).copy_current_run("copy-board", runtime / "run")

    assert not (outside / "run").exists()


def test_copy_current_run_holds_the_publication_lock_until_copy_finishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _complete_board(repository, "copy-board", "Copy Board")
    candidate = _complete_board(tmp_path / "candidate", "copy-board", "Copy Board")
    reader = RepositoryBoardLibrary(repository)
    publisher = RepositoryBoardLibrary(repository)
    existing = reader.get_board("copy-board")
    destination = tmp_path / "runtime" / "run"
    copy_started, release_copy, publication_finished = Event(), Event(), Event()
    copied: list[object] = []
    published: list[object] = []
    errors: list[BaseException] = []
    original_copy = reader._copy_tree

    def paused_copy(source: Path, target: Path) -> None:
        copy_started.set()
        if not release_copy.wait(2):
            raise TimeoutError("copy was not released")
        original_copy(source, target)

    def copy_board() -> None:
        try:
            copied.append(reader.copy_current_run("copy-board", destination))
        except BaseException as error:
            errors.append(error)

    def publish_board() -> None:
        try:
            published.append(
                publisher.publish(
                    run_root=candidate,
                    board_id=existing.board_id,
                    expected_revision_token=existing.revision_token,
                )
            )
        except BaseException as error:
            errors.append(error)
        finally:
            publication_finished.set()

    monkeypatch.setattr(reader, "_copy_tree", paused_copy)
    copy_thread = Thread(target=copy_board)
    publication_thread = Thread(target=publish_board)
    copy_thread.start()
    assert copy_started.wait(2)
    publication_thread.start()
    try:
        assert not publication_finished.wait(0.2)
    finally:
        release_copy.set()
        copy_thread.join(2)
        publication_thread.join(2)

    assert not copy_thread.is_alive()
    assert not publication_thread.is_alive()
    assert errors == []
    assert copied == [existing]
    assert len(published) == 1
    assert sha256((destination / "run.json").read_bytes()).hexdigest() == (
        existing.revision_token
    )


def test_get_board_rejects_invalid_and_missing_boards(tmp_path: Path) -> None:
    invalid = _boards_root(tmp_path) / "Invalid_Board"
    invalid.mkdir(parents=True)
    library = RepositoryBoardLibrary(tmp_path)

    with pytest.raises(BoardLibraryError, match="identifier is invalid"):
        library.get_board("Invalid_Board")
    with pytest.raises(BoardLibraryError, match="does not exist"):
        library.get_board("missing-board")


@pytest.mark.parametrize("replacing", [False, True], ids=["new", "replacement"])
def test_publish_installs_a_validated_canonical_package(
    tmp_path: Path, replacing: bool
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    candidate = _complete_board(
        tmp_path / "candidate", "publish-board", "Publish Board"
    )
    runtime_candidate = tmp_path / "runtime" / "selected-run"
    runtime_candidate.parent.mkdir()
    candidate.rename(runtime_candidate)
    candidate = runtime_candidate
    library = RepositoryBoardLibrary(repository)
    existing = (
        _complete_board(repository, "publish-board", "Publish Board")
        if replacing
        else None
    )
    previous = library.get_board("publish-board") if existing is not None else None

    published = library.publish(
        run_root=candidate,
        board_id=previous.board_id if previous is not None else None,
        expected_revision_token=(
            previous.revision_token if previous is not None else None
        ),
    )

    assert isinstance(published, board_library.PublishedBoard)
    if previous is not None:
        assert published.revision_token != previous.revision_token
    assert published.board.board_id == "publish-board"
    assert published.board.run_path == _boards_root(repository) / "publish-board"
    assert library.get_board("publish-board").revision_token == published.revision_token
    assert not (
        _boards_root(repository) / "publish-board" / "publication.json"
    ).exists()


def test_publish_identical_retry_succeeds_before_stale_token_conflict(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _complete_board(repository, "retry-board", "Retry Board")
    candidate = _complete_board(tmp_path / "candidate", "retry-board", "Retry Board")
    library = RepositoryBoardLibrary(repository)
    existing = library.get_board("retry-board")
    published = library.publish(
        run_root=candidate,
        board_id=existing.board_id,
        expected_revision_token=existing.revision_token,
    )

    retried = library.publish(
        run_root=candidate,
        board_id=existing.board_id,
        expected_revision_token="not-a-revision-token",
    )

    assert retried == published


def test_publish_reports_invalid_candidate_as_a_library_error(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    candidate = _complete_board(
        tmp_path / "candidate", "invalid-board", "Invalid Board"
    )
    normal = _stage_four_acceptance(candidate)["normal"]
    assert isinstance(normal, dict)
    (candidate / str(normal["path"])).write_bytes(b"invalid output")

    with pytest.raises(BoardLibraryError, match="Stage 4"):
        RepositoryBoardLibrary(repository).publish(
            run_root=candidate,
            board_id=None,
            expected_revision_token=None,
        )

    assert not (_boards_root(repository) / "invalid-board").exists()


@pytest.mark.parametrize(
    "conflict",
    ["changed-current", "new-board-collision", "malformed-expected"],
    ids=["changed-current", "new-board-collision", "malformed-expected"],
)
def test_publish_rejects_revision_conflicts(tmp_path: Path, conflict: str) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    canonical = _complete_board(repository, "conflict-board", "Conflict Board")
    library = RepositoryBoardLibrary(repository)
    expected = library.get_board("conflict-board")
    changed = _complete_board(tmp_path / "changed", "conflict-board", "Conflict Board")
    candidate = _complete_board(
        tmp_path / "candidate", "conflict-board", "Conflict Board"
    )
    shutil.rmtree(canonical)
    shutil.copytree(changed, canonical)
    current = library.get_board("conflict-board")
    assert current.revision_token not in {
        expected.revision_token,
        sha256((candidate / "run.json").read_bytes()).hexdigest(),
    }

    board_id = None if conflict == "new-board-collision" else expected.board_id
    expected_token = {
        "changed-current": expected.revision_token,
        "new-board-collision": None,
        "malformed-expected": "not-a-revision-token",
    }[conflict]
    with pytest.raises(BoardLibraryError) as raised:
        library.publish(
            run_root=candidate,
            board_id=board_id,
            expected_revision_token=expected_token,
        )

    assert (expected_token or "absent") in str(raised.value)
    assert current.revision_token in str(raised.value)
    assert library.get_board("conflict-board") == current


def test_publish_rejects_board_id_that_does_not_match_the_run(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    candidate = _complete_board(tmp_path / "candidate", "actual-board", "Actual Board")

    with pytest.raises(BoardLibraryError, match="does not match run product key"):
        RepositoryBoardLibrary(repository).publish(
            run_root=candidate,
            board_id="different-board",
            expected_revision_token=None,
        )


def test_publish_preserves_an_out_of_band_replacement_captured_during_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    canonical = _complete_board(repository, "conflict-board", "Conflict Board")
    candidate = _complete_board(
        tmp_path / "candidate", "conflict-board", "Conflict Board"
    )
    changed = _complete_board(
        tmp_path / "changed", "conflict-board", "Conflict Board"
    )
    library = RepositoryBoardLibrary(repository)
    existing = library.get_board("conflict-board")
    changed_token = sha256((changed / "run.json").read_bytes()).hexdigest()
    copy_started, release_copy = Event(), Event()
    original_copy = library._copy_tree
    results: list[object] = []
    errors: list[BaseException] = []

    def paused_candidate_copy(source: Path, target: Path) -> None:
        copy_started.set()
        if not release_copy.wait(2):
            raise TimeoutError("candidate copy was not released")
        original_copy(source, target)

    def publish_board() -> None:
        try:
            results.append(
                library.publish(
                    run_root=candidate,
                    board_id=existing.board_id,
                    expected_revision_token=existing.revision_token,
                )
            )
        except BaseException as error:
            errors.append(error)

    monkeypatch.setattr(library, "_copy_tree", paused_candidate_copy)
    publication_thread = Thread(target=publish_board)
    publication_thread.start()
    assert copy_started.wait(2)
    try:
        shutil.rmtree(canonical)
        shutil.copytree(changed, canonical)
    finally:
        release_copy.set()
        publication_thread.join(3)

    assert not publication_thread.is_alive()
    assert results == []
    assert len(errors) == 1
    assert isinstance(errors[0], BoardLibraryError)
    assert "publication conflict" in str(errors[0])
    assert library.get_board("conflict-board").revision_token == changed_token
    assert not [
        path
        for path in (_boards_root(repository) / ".transactions").iterdir()
        if path.name != "lock"
    ]


def test_publish_fsyncs_rollback_destination_before_canonical_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _complete_board(repository, "ordered-board", "Ordered Board")
    candidate = _complete_board(
        tmp_path / "candidate", "ordered-board", "Ordered Board"
    )
    library = RepositoryBoardLibrary(repository)
    existing = library.get_board("ordered-board")
    state: dict[str, object] = {
        "rollback_moved": False,
        "rollback_parent": None,
        "destination_synced": False,
    }
    original_move = library._move_path
    original_fsync = library._fsync_directory

    def tracked_move(source: Path, destination: Path) -> None:
        original_move(source, destination)
        if destination.name == "rollback":
            state["rollback_moved"] = True
            state["rollback_parent"] = destination.parent

    def checked_fsync(path: Path) -> None:
        if state["rollback_moved"]:
            if path == state["rollback_parent"]:
                state["destination_synced"] = True
            if path == _boards_root(repository):
                assert state["destination_synced"] is True
        original_fsync(path)

    monkeypatch.setattr(library, "_move_path", tracked_move)
    monkeypatch.setattr(library, "_fsync_directory", checked_fsync)

    published = library.publish(
        run_root=candidate,
        board_id=existing.board_id,
        expected_revision_token=existing.revision_token,
    )

    assert published.revision_token != existing.revision_token


def test_first_publication_fsyncs_every_new_repository_directory_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    candidate = _complete_board(
        tmp_path / "candidate", "durable-board", "Durable Board"
    )
    library = RepositoryBoardLibrary(repository)
    fsynced: list[Path] = []
    original_fsync = library._fsync_directory

    def record_fsync(path: Path) -> None:
        fsynced.append(path)
        original_fsync(path)

    monkeypatch.setattr(library, "_fsync_directory", record_fsync)

    library.publish(
        run_root=candidate,
        board_id=None,
        expected_revision_token=None,
    )

    root = repository.resolve()
    assert fsynced[:4] == [
        root,
        root / "Tools",
        root / "Tools" / "HangboardPipeline",
        _boards_root(root),
    ]


def test_concurrent_publishers_return_the_package_each_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _complete_board(repository, "concurrent-board", "Concurrent Board")
    first_candidate = _complete_board(
        tmp_path / "first", "concurrent-board", "Concurrent Board"
    )
    second_candidate = _complete_board(
        tmp_path / "second", "concurrent-board", "Concurrent Board"
    )
    first_library = RepositoryBoardLibrary(repository)
    second_library = RepositoryBoardLibrary(repository)
    existing = first_library.get_board("concurrent-board")
    first_token = sha256((first_candidate / "run.json").read_bytes()).hexdigest()
    second_token = sha256((second_candidate / "run.json").read_bytes()).hexdigest()
    assert len({existing.revision_token, first_token, second_token}) == 3
    first_replaced, release_first, second_finished = Event(), Event(), Event()
    results: dict[str, object] = {}
    errors: list[BaseException] = []
    original_replace = first_library._replace_board_locked
    original_get = first_library.get_board

    def pause_after_replace(
        candidate: board_library.LibraryBoard,
        current: board_library.LibraryBoard | None,
    ) -> None:
        original_replace(candidate, current)
        first_replaced.set()
        if not release_first.wait(3):
            raise TimeoutError("first publisher was not released")

    def wait_for_second_publisher(board_id: str) -> board_library.LibraryBoard:
        if first_replaced.is_set() and not second_finished.wait(3):
            raise TimeoutError("second publisher did not finish")
        return original_get(board_id)

    def publish_first() -> None:
        try:
            results["first"] = first_library.publish(
                run_root=first_candidate,
                board_id=existing.board_id,
                expected_revision_token=existing.revision_token,
            )
        except BaseException as error:
            errors.append(error)

    def publish_second() -> None:
        try:
            results["second"] = second_library.publish(
                run_root=second_candidate,
                board_id=existing.board_id,
                expected_revision_token=first_token,
            )
        except BaseException as error:
            errors.append(error)
        finally:
            second_finished.set()

    monkeypatch.setattr(first_library, "_replace_board_locked", pause_after_replace)
    monkeypatch.setattr(first_library, "get_board", wait_for_second_publisher)
    first_thread = Thread(target=publish_first)
    second_thread = Thread(target=publish_second)
    first_thread.start()
    assert first_replaced.wait(3)
    second_thread.start()
    release_first.set()
    first_thread.join(4)
    second_thread.join(4)

    assert errors == []
    first = results["first"]
    second = results["second"]
    assert isinstance(first, board_library.PublishedBoard)
    assert isinstance(second, board_library.PublishedBoard)
    assert first.revision_token == first_token
    assert second.revision_token == second_token


@pytest.mark.parametrize(
    "failure_point",
    [
        "before-rollback-move",
        "after-rollback-move",
        "after-candidate-installation",
        "before-cleanup",
    ],
)
def test_snapshot_inspects_interrupted_replacement_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_point: str
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _complete_board(repository, "recovery-board", "Recovery Board")
    candidate = _complete_board(
        tmp_path / "candidate", "recovery-board", "Recovery Board"
    )
    library = RepositoryBoardLibrary(repository)
    existing = library.get_board("recovery-board")
    candidate_token = sha256((candidate / "run.json").read_bytes()).hexdigest()
    original_move = RepositoryBoardLibrary._move_path
    original_remove = RepositoryBoardLibrary._remove_transaction

    def interrupted_move(
        self: RepositoryBoardLibrary, source: Path, destination: Path
    ) -> None:
        is_rollback = destination.name == "rollback"
        is_installation = source.name == "candidate"
        if failure_point == "before-rollback-move" and is_rollback:
            raise OSError("injected before rollback move")
        original_move(self, source, destination)
        if failure_point == "after-rollback-move" and is_rollback:
            raise OSError("injected after rollback move")
        if failure_point == "after-candidate-installation" and is_installation:
            raise OSError("injected after candidate installation")

    def interrupted_remove(self: RepositoryBoardLibrary, transaction: Path) -> None:
        if failure_point == "before-cleanup":
            raise OSError("injected before cleanup")
        original_remove(self, transaction)

    monkeypatch.setattr(RepositoryBoardLibrary, "_move_path", interrupted_move)
    monkeypatch.setattr(
        RepositoryBoardLibrary, "_remove_transaction", interrupted_remove
    )
    with pytest.raises(OSError, match="injected"):
        library.publish(
            run_root=candidate,
            board_id=existing.board_id,
            expected_revision_token=existing.revision_token,
        )
    monkeypatch.undo()

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert len(snapshot.boards) == 1
    assert snapshot.boards[0].board_id == "recovery-board"
    assert snapshot.boards[0].revision_token == candidate_token
    assert snapshot.diagnostics == ()
    transactions = _boards_root(repository) / ".transactions"
    assert len([path for path in transactions.iterdir() if path.name != "lock"]) == 1

    published = RepositoryBoardLibrary(repository).publish(
        run_root=candidate,
        board_id="recovery-board",
        expected_revision_token=existing.revision_token,
    )

    assert published.revision_token == candidate_token
    assert [path.name for path in transactions.iterdir()] == ["lock"]


def test_recovery_restores_prior_when_staged_candidate_is_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _complete_board(repository, "restore-board", "Restore Board")
    candidate = _complete_board(
        tmp_path / "candidate", "restore-board", "Restore Board"
    )
    library = RepositoryBoardLibrary(repository)
    existing = library.get_board("restore-board")
    original_move = RepositoryBoardLibrary._move_path

    def fail_after_rollback(
        self: RepositoryBoardLibrary, source: Path, destination: Path
    ) -> None:
        original_move(self, source, destination)
        if destination.name == "rollback":
            raise OSError("injected after rollback move")

    monkeypatch.setattr(RepositoryBoardLibrary, "_move_path", fail_after_rollback)
    with pytest.raises(OSError, match="injected"):
        library.publish(
            run_root=candidate,
            board_id=existing.board_id,
            expected_revision_token=existing.revision_token,
        )
    monkeypatch.undo()
    staged = next(
        path / "candidate"
        for path in (_boards_root(repository) / ".transactions").iterdir()
        if path.is_dir()
    )
    (staged / "run.json").write_text("not json", encoding="utf-8")

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert [board.revision_token for board in snapshot.boards] == [
        existing.revision_token
    ]
    assert [(item.code, item.path) for item in snapshot.diagnostics] == [
        (
            "invalid_transaction",
            staged.parent.relative_to(_boards_root(repository)).as_posix(),
        )
    ]
    assert staged.parent.exists()


def test_recovery_retains_ambiguous_transaction_evidence(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    canonical = _complete_board(repository, "ambiguous-board", "Ambiguous Board")
    expected_run = _complete_board(
        tmp_path / "expected", "ambiguous-board", "Ambiguous Board"
    )
    candidate = _complete_board(
        tmp_path / "candidate", "ambiguous-board", "Ambiguous Board"
    )
    current = RepositoryBoardLibrary(repository).get_board("ambiguous-board")
    transaction = _boards_root(repository) / ".transactions" / "ambiguous"
    transaction.mkdir(parents=True)
    shutil.copytree(expected_run, transaction / "rollback")
    shutil.copytree(candidate, transaction / "candidate")
    _write_json(
        transaction / "journal.json",
        {
            "schemaVersion": 1,
            "boardId": "ambiguous-board",
            "expectedRevisionToken": sha256(
                (expected_run / "run.json").read_bytes()
            ).hexdigest(),
            "candidateRevisionToken": sha256(
                (candidate / "run.json").read_bytes()
            ).hexdigest(),
            "phase": "prior_moved",
        },
    )

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert [board.revision_token for board in snapshot.boards] == [
        current.revision_token
    ]
    assert [(item.code, item.path) for item in snapshot.diagnostics] == [
        ("invalid_transaction", ".transactions/ambiguous")
    ]
    assert transaction.exists()
    assert canonical.exists()


def test_recovery_does_not_install_candidate_with_invalid_rollback_evidence(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    prior = _complete_board(tmp_path / "prior", "evidence-board", "Evidence Board")
    candidate = _complete_board(
        tmp_path / "candidate", "evidence-board", "Evidence Board"
    )
    transaction = _boards_root(repository) / ".transactions" / "invalid-rollback"
    transaction.mkdir(parents=True)
    shutil.copytree(prior, transaction / "rollback")
    shutil.copytree(candidate, transaction / "candidate")
    expected_token = sha256((prior / "run.json").read_bytes()).hexdigest()
    candidate_token = sha256((candidate / "run.json").read_bytes()).hexdigest()
    (transaction / "rollback" / "run.json").write_text(
        "not json", encoding="utf-8"
    )
    _write_json(
        transaction / "journal.json",
        {
            "schemaVersion": 1,
            "boardId": "evidence-board",
            "expectedRevisionToken": expected_token,
            "candidateRevisionToken": candidate_token,
            "phase": "prior_moved",
        },
    )

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert snapshot.boards == ()
    assert [(item.code, item.path) for item in snapshot.diagnostics] == [
        ("invalid_transaction", ".transactions/invalid-rollback")
    ]
    assert transaction.exists()
    assert (transaction / "rollback").exists()


def test_publish_removes_invalid_journal_without_package_evidence(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _complete_board(repository, "utf8-board", "UTF8 Board")
    candidate = _complete_board(
        tmp_path / "candidate", "utf8-board", "UTF8 Board"
    )
    library = RepositoryBoardLibrary(repository)
    existing = library.get_board("utf8-board")
    transaction = _boards_root(repository) / ".transactions" / "invalid-utf8"
    transaction.mkdir(parents=True)
    (transaction / "journal.json").write_bytes(b"\xff\xfe")

    published = library.publish(
        run_root=candidate,
        board_id="utf8-board",
        expected_revision_token=existing.revision_token,
    )

    assert published.board.board_id == "utf8-board"
    assert not transaction.exists()


def test_publish_removes_stray_transaction_file(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _complete_board(repository, "stray-board", "Stray Board")
    candidate = _complete_board(
        tmp_path / "candidate", "stray-board", "Stray Board"
    )
    library = RepositoryBoardLibrary(repository)
    existing = library.get_board("stray-board")
    stray = _boards_root(repository) / ".transactions" / "stray"
    stray.parent.mkdir()
    stray.write_text("not transaction evidence", encoding="utf-8")

    published = library.publish(
        run_root=candidate,
        board_id="stray-board",
        expected_revision_token=existing.revision_token,
    )

    assert published.board.board_id == "stray-board"
    assert not stray.exists()


def test_recovery_reports_stray_transaction_unlink_failure_with_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    library = RepositoryBoardLibrary(repository)
    transactions = _boards_root(repository) / ".transactions"
    transactions.mkdir(parents=True)
    stray = transactions / "unlink-failure"
    stray.write_text("not transaction evidence", encoding="utf-8")
    failure = OSError("injected unlink failure")
    original_unlink = Path.unlink

    def fail_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if path == stray:
            raise failure
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_unlink)

    with pytest.raises(BoardLibraryError) as raised:
        library._recover_transactions_locked()

    assert str(raised.value) == "stray transaction entry is not removable"
    assert raised.value.__cause__ is failure


def test_recovery_reports_transaction_directory_fsync_failure_with_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    library = RepositoryBoardLibrary(repository)
    transactions = _boards_root(repository) / ".transactions"
    transactions.mkdir(parents=True)
    stray = transactions / "fsync-failure"
    stray.write_text("not transaction evidence", encoding="utf-8")
    failure = OSError("injected directory fsync failure")
    original_fsync = library._fsync_directory

    def fail_fsync(path: Path) -> None:
        if path == transactions:
            raise failure
        original_fsync(path)

    monkeypatch.setattr(library, "_fsync_directory", fail_fsync)

    with pytest.raises(BoardLibraryError) as raised:
        library._recover_transactions_locked()

    assert str(raised.value) == "stray transaction entry is not removable"
    assert raised.value.__cause__ is failure
    assert not stray.exists()


def test_publish_retains_invalid_canonical_transaction_evidence(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _complete_board(repository, "evidence-board", "Evidence Board")
    candidate = _complete_board(
        tmp_path / "candidate", "evidence-board", "Evidence Board"
    )
    library = RepositoryBoardLibrary(repository)
    existing = library.get_board("evidence-board")
    transaction = _boards_root(repository) / ".transactions" / "retained-evidence"
    evidence = transaction / "invalid-canonical"
    evidence.mkdir(parents=True)
    (evidence / "run.json").write_text("not json", encoding="utf-8")

    with pytest.raises(BoardLibraryError, match="manual intervention"):
        library.publish(
            run_root=candidate,
            board_id="evidence-board",
            expected_revision_token=existing.revision_token,
        )

    assert evidence.exists()


def test_recovery_restores_a_valid_captured_package_that_mismatches_the_journal(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    prior = _complete_board(tmp_path / "prior", "recovery-board", "Recovery Board")
    candidate = _complete_board(
        tmp_path / "candidate", "recovery-board", "Recovery Board"
    )
    changed = _complete_board(
        tmp_path / "changed", "recovery-board", "Recovery Board"
    )
    expected_token = sha256((prior / "run.json").read_bytes()).hexdigest()
    candidate_token = sha256((candidate / "run.json").read_bytes()).hexdigest()
    changed_token = sha256((changed / "run.json").read_bytes()).hexdigest()
    transaction = _boards_root(repository) / ".transactions" / "captured-conflict"
    transaction.mkdir(parents=True)
    shutil.copytree(candidate, transaction / "candidate")
    shutil.copytree(changed, transaction / "rollback")
    _write_json(
        transaction / "journal.json",
        {
            "schemaVersion": 1,
            "boardId": "recovery-board",
            "expectedRevisionToken": expected_token,
            "candidateRevisionToken": candidate_token,
            "phase": "prior_moved",
        },
    )

    snapshot = RepositoryBoardLibrary(repository).snapshot()

    assert [board.revision_token for board in snapshot.boards] == [changed_token]
    assert [(item.code, item.path) for item in snapshot.diagnostics] == [
        ("invalid_transaction", ".transactions/captured-conflict")
    ]
    assert transaction.exists()
    assert (transaction / "rollback").exists()
    assert (transaction / "candidate").exists()


@pytest.mark.parametrize("proven_package", ["candidate", "rollback"])
def test_recovery_preserves_invalid_canonical_before_using_proven_package(
    tmp_path: Path, proven_package: str
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    prior = _complete_board(tmp_path / "prior", "proven-board", "Proven Board")
    candidate = _complete_board(
        tmp_path / "candidate", "proven-board", "Proven Board"
    )
    expected_token = sha256((prior / "run.json").read_bytes()).hexdigest()
    candidate_token = sha256((candidate / "run.json").read_bytes()).hexdigest()
    canonical = _boards_root(repository) / "proven-board"
    canonical.mkdir(parents=True)
    (canonical / "run.json").write_text("{}\n", encoding="utf-8")
    transaction = _boards_root(repository) / ".transactions" / proven_package
    transaction.mkdir(parents=True)
    if proven_package == "candidate":
        shutil.copytree(candidate, transaction / "candidate")
        published_token = candidate_token
    else:
        shutil.copytree(prior, transaction / "rollback")
        published_token = expected_token
    _write_json(
        transaction / "journal.json",
        {
            "schemaVersion": 1,
            "boardId": "proven-board",
            "expectedRevisionToken": expected_token,
            "candidateRevisionToken": candidate_token,
            "phase": "prior_moved",
        },
    )

    first = RepositoryBoardLibrary(repository).snapshot()
    second = RepositoryBoardLibrary(repository).snapshot()

    assert [board.revision_token for board in first.boards] == [published_token]
    assert [board.revision_token for board in second.boards] == [published_token]
    assert [(item.code, item.path) for item in first.diagnostics] == [
        ("invalid_transaction", f".transactions/{proven_package}")
    ]
    assert [(item.code, item.path) for item in second.diagnostics] == [
        ("invalid_transaction", f".transactions/{proven_package}")
    ]
    assert canonical.exists()
    assert not (transaction / "invalid-canonical").exists()


def _complete_board(repository: Path, board_id: str, product_name: str) -> Path:
    assert _product_key(product_name) == board_id
    run = _boards_root(repository) / board_id
    run.parent.mkdir(parents=True, exist_ok=True)
    source = _source_image(repository, board_id)
    runners = {stage: _StubStageRunner(stage) for stage in range(5)}
    start_run(product_name, str(source), run, runners=runners, workspace_root=repository)
    for stage in range(5):
        approve_stage(run, stage)
        if stage < 4:
            resume_run(run, runners=runners)
    assert read_status(run)["status"] == "complete"
    return run


def _incomplete_board(repository: Path, board_id: str, product_name: str) -> Path:
    assert _product_key(product_name) == board_id
    run = _boards_root(repository) / board_id
    run.parent.mkdir(parents=True, exist_ok=True)
    source = _source_image(repository, board_id)
    start_run(
        product_name,
        str(source),
        run,
        runners={stage: _StubStageRunner(stage) for stage in range(5)},
        workspace_root=repository,
    )
    assert read_status(run)["status"] == "awaiting_approval"
    return run


def _source_image(repository: Path, name: str) -> Path:
    source = repository / ".fixtures" / f"{name}.png"
    source.parent.mkdir(exist_ok=True)
    Image.new("RGB", (512, 512), (45, 65, 85)).save(source)
    return source


def _stage_four_acceptance(run: Path) -> dict[str, object]:
    manifest = _read_json(run / "run.json")
    stages = manifest["stages"]
    assert isinstance(stages, list)
    stage = stages[4]
    assert isinstance(stage, dict)
    return _read_json(run / str(stage["acceptancePath"]))


def _boards_root(repository: Path) -> Path:
    return repository / "Tools" / "HangboardPipeline" / "boards"


def _product_key(value: str) -> str:
    return "-".join(value.lower().split())


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class _StubStageRunner:
    def __init__(self, stage: int) -> None:
        self.stage = stage

    def run(self, context: RunContext, artifact_root: Path) -> StageCheckpoint:
        artifact_root.mkdir(parents=True)
        review = artifact_root / f"stage-{self.stage}-review.png"
        Image.new("RGB", (4, 4), (120, 80, 40)).save(review)
        candidate = self._candidate(context, artifact_root)
        _write_json(artifact_root / f"stage-{self.stage}-candidate.json", candidate)
        hashes = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in sorted(artifact_root.iterdir())
            if path.is_file()
        }
        _write_json(artifact_root / "candidate-hashes.json", hashes)
        return StageCheckpoint(self.stage, artifact_root, hashes, review, True)

    def _candidate(self, context: RunContext, root: Path) -> dict[str, object]:
        candidate: dict[str, object] = {"profile": {}, "stage": self.stage}
        if self.stage == 0:
            candidate["registered"] = {}
            return candidate
        stages = context.manifest["stages"]
        assert isinstance(stages, list) and isinstance(stages[-1], dict)
        candidate["inputAcceptance"] = {
            "path": stages[-1]["acceptancePath"],
            "sha256": stages[-1]["acceptanceSha256"],
        }
        if self.stage == 1:
            path = root / "stage-1-auto-rgba.png"
            Image.new("RGBA", (4, 4), (10, 20, 30, 255)).save(path)
            candidate["registered"] = {"fileSha256": _hash(path)}
        elif self.stage == 2:
            regions, labels = root / "stage-2-regions.json", root / "stage-2-labels.png"
            _write_json(regions, {"canvas": {"width": 4, "height": 4}, "regions": []})
            Image.new("I;16", (4, 4), 0).save(labels)
            candidate.update({"regionCount": 0, "regions": {"fileSha256": _hash(regions)}, "registered": {"fileSha256": _hash(labels)}})
        elif self.stage == 3:
            regions, svg = root / "stage-3-vector-regions.json", root / "stage-3-vector.svg"
            _write_json(regions, {"canvas": {"width": 4, "height": 4}, "regions": []})
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n', encoding="utf-8")
            candidate.update({"regionCount": 0, "vectorRegions": {"fileSha256": _hash(regions)}, "vectorSvg": {"fileSha256": _hash(svg)}})
        else:
            candidate["regionCount"] = 0
            for field, name in (("normal", "stage-4-normal.png"), ("productSvg", "stage-4-product.svg"), ("manifest", "stage-4-manifest.json"), ("highlights", "stage-4-highlights.json")):
                path = root / name
                if path.suffix == ".png":
                    Image.new("RGB", (4, 4), (1, 2, 3)).save(path)
                elif path.suffix == ".svg":
                    path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n', encoding="utf-8")
                else:
                    _write_json(path, {})
                candidate[field] = {"fileSha256": _hash(path)}
        return candidate


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
