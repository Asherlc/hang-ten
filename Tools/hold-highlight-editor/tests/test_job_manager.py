from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
from threading import Event

import pytest


EDITOR_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EDITOR_ROOT))

import job_manager as job_manager_module  # noqa: E402
from job_manager import (  # noqa: E402
    BoardJobManager,
    JobCapacityError,
    JobConflictError,
    JobNotFoundError,
)


@pytest.fixture
def make_manager():
    managers = []

    def build(**options) -> BoardJobManager:
        manager = BoardJobManager(**options)
        managers.append(manager)
        return manager

    yield build
    for manager in managers:
        manager.shutdown()


def test_job_manager_rejects_second_mutation_for_same_board(make_manager):
    gate = Event()
    manager = make_manager(max_workers=2)
    first = manager.submit("board-a", lambda: gate.wait(1))
    with pytest.raises(JobConflictError, match="already running"):
        manager.submit("board-a", lambda: None)
    second = manager.submit("board-b", lambda: "ok")
    gate.set()
    assert manager.wait(first.id).state == "succeeded"
    assert manager.wait(second.id).state == "succeeded"


def test_submit_uses_conflict_key_without_changing_logical_board_identity(make_manager):
    started = Event()
    release = Event()
    manager = make_manager(max_workers=2)

    first = manager.submit(
        "board-0001",
        lambda: (started.set(), release.wait(1))[1],
        conflict_key="repository-board:example",
    )
    assert started.wait(1)
    try:
        with pytest.raises(JobConflictError, match="already running"):
            manager.submit(
                "board-0002",
                lambda: None,
                conflict_key="repository-board:example",
            )
        assert manager.get(first.id).board_id == "board-0001"
        release.set()
        assert manager.wait(first.id).state == "succeeded"
        second = manager.submit(
            "board-0002",
            lambda: None,
            conflict_key="repository-board:example",
        )
        assert manager.wait(second.id).state == "succeeded"
    finally:
        release.set()


def test_job_records_are_immutable_serializable_snapshots(make_manager):
    manager = make_manager(max_workers=1)

    submitted = manager.submit("board-a", lambda: {"revisionId": "revision-1"})
    finished = manager.wait(submitted.id)

    with pytest.raises(FrozenInstanceError):
        finished.state = "running"
    assert json.loads(json.dumps(finished.as_dict())) == {
        "id": submitted.id,
        "boardId": "board-a",
        "state": "succeeded",
        "result": {"revisionId": "revision-1"},
        "error": None,
    }
    finished.result["revisionId"] = "mutated"
    detached = finished.as_dict()
    detached["result"]["revisionId"] = "also-mutated"
    assert manager.get(submitted.id).result == {"revisionId": "revision-1"}


def test_job_manager_bounds_workers_but_runs_independent_boards(make_manager):
    first_started = Event()
    second_started = Event()
    release = Event()
    manager = make_manager(max_workers=2)

    first = manager.submit(
        "board-a", lambda: (first_started.set(), release.wait(1))[1]
    )
    second = manager.submit(
        "board-b", lambda: (second_started.set(), release.wait(1))[1]
    )

    assert first_started.wait(1)
    assert second_started.wait(1)
    release.set()
    assert manager.wait(first.id).state == "succeeded"
    assert manager.wait(second.id).state == "succeeded"


def test_job_manager_never_runs_more_than_configured_worker_count(make_manager):
    first_started = Event()
    second_started = Event()
    release = Event()
    manager = make_manager(max_workers=1)

    first = manager.submit(
        "board-a", lambda: (first_started.set(), release.wait(1))[1]
    )
    second = manager.submit(
        "board-b", lambda: second_started.set()
    )

    assert first_started.wait(1)
    assert not second_started.is_set()
    release.set()
    assert manager.wait(first.id).state == "succeeded"
    assert manager.wait(second.id).state == "succeeded"
    assert second_started.is_set()


def test_failed_job_has_safe_message_and_releases_board(make_manager):
    manager = make_manager(max_workers=1)

    def fail():
        raise RuntimeError("secret implementation detail")

    failed = manager.wait(manager.submit("board-a", fail).id)
    retried = manager.wait(manager.submit("board-a", lambda: "ok").id)

    assert failed.state == "failed"
    assert failed.error == "job failed"
    assert "Traceback" not in failed.as_dict()["error"]
    assert retried.state == "succeeded"


def test_job_manager_bounds_queued_work_and_completed_retention(make_manager):
    gate = Event()
    manager = make_manager(max_workers=1, max_queue=1, max_completed=2)
    running = manager.submit("board-a", lambda: gate.wait(1))
    queued = manager.submit("board-b", lambda: "queued")

    with pytest.raises(JobCapacityError, match="capacity"):
        manager.submit("board-c", lambda: "rejected")

    gate.set()
    manager.wait(running.id)
    manager.wait(queued.id)
    third = manager.wait(manager.submit("board-c", lambda: "third").id)

    assert third.state == "succeeded"
    with pytest.raises(JobNotFoundError, match="unknown job"):
        manager.get(running.id)


def test_completed_outcome_is_removed_after_expiry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, make_manager
):
    now = [100.0]
    monkeypatch.setattr(job_manager_module, "monotonic", lambda: now[0])
    outcome_root = tmp_path / "job-outcomes"
    manager = make_manager(
        max_workers=1,
        result_ttl_seconds=1,
        outcome_root=outcome_root,
    )
    submitted = manager.submit(
        "workbench-board-reservation-1",
        lambda: {"boardId": "board-1", "revisionId": "revision-1"},
    )
    assert manager.wait(submitted.id).state == "succeeded"

    now[0] += 2
    with pytest.raises(JobNotFoundError, match="unknown job"):
        manager.get(submitted.id)
    assert not (outcome_root / f"{submitted.id}.json").exists()
    manager.shutdown()

    restarted = make_manager(max_workers=1, outcome_root=outcome_root)
    with pytest.raises(JobNotFoundError, match="unknown job"):
        restarted.get(submitted.id)


def test_failed_outcome_is_removed_after_expiry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, make_manager
):
    now = [100.0]
    monkeypatch.setattr(job_manager_module, "monotonic", lambda: now[0])
    outcome_root = tmp_path / "job-outcomes"
    manager = make_manager(
        max_workers=1,
        result_ttl_seconds=1,
        outcome_root=outcome_root,
    )

    def fail():
        raise RuntimeError("private failure detail")

    submitted = manager.submit("board-a", fail)
    completed = manager.wait(submitted.id)
    assert completed.state == "failed"
    assert completed.error == "job failed"

    now[0] += 2
    with pytest.raises(JobNotFoundError, match="unknown job"):
        manager.get(submitted.id)
    assert not (outcome_root / f"{submitted.id}.json").exists()
    manager.shutdown()

    restarted = make_manager(max_workers=1, outcome_root=outcome_root)
    with pytest.raises(JobNotFoundError, match="unknown job"):
        restarted.get(submitted.id)


@pytest.mark.parametrize(
    ("record_update",),
    [
        ({"id": "f" * 32},),
        ({"boardId": None},),
        ({"state": "succeeded", "error": "must be absent"},),
    ],
)
def test_malformed_outcome_records_are_rejected(
    tmp_path: Path, make_manager, record_update: dict[str, object]
):
    outcome_root = tmp_path / "job-outcomes"
    outcome_root.mkdir()
    job_id = "a" * 32
    record = {
        "id": job_id,
        "boardId": "board-a",
        "state": "succeeded",
        "result": {"revisionId": "revision-1"},
        "error": None,
        **record_update,
    }
    (outcome_root / f"{job_id}.json").write_text(json.dumps(record))
    manager = make_manager(max_workers=1, outcome_root=outcome_root)

    with pytest.raises(JobNotFoundError, match="unknown job"):
        manager.get(job_id)
