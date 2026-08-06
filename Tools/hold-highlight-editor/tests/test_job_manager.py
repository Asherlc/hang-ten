from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
from threading import Event

import pytest


EDITOR_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EDITOR_ROOT))

from job_manager import BoardJobManager, JobConflictError  # noqa: E402


def test_job_manager_rejects_second_mutation_for_same_board():
    gate = Event()
    manager = BoardJobManager(max_workers=2)
    first = manager.submit("board-a", lambda: gate.wait(1))
    with pytest.raises(JobConflictError, match="already running"):
        manager.submit("board-a", lambda: None)
    second = manager.submit("board-b", lambda: "ok")
    gate.set()
    assert manager.wait(first.id).state == "succeeded"
    assert manager.wait(second.id).state == "succeeded"


def test_job_records_are_immutable_serializable_snapshots():
    manager = BoardJobManager(max_workers=1)

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


def test_job_manager_bounds_workers_but_runs_independent_boards():
    first_started = Event()
    second_started = Event()
    release = Event()
    manager = BoardJobManager(max_workers=2)

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


def test_job_manager_never_runs_more_than_configured_worker_count():
    first_started = Event()
    second_started = Event()
    release = Event()
    manager = BoardJobManager(max_workers=1)

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


def test_failed_job_has_safe_message_and_releases_board():
    manager = BoardJobManager(max_workers=1)

    def fail():
        raise RuntimeError("secret implementation detail")

    failed = manager.wait(manager.submit("board-a", fail).id)
    retried = manager.wait(manager.submit("board-a", lambda: "ok").id)

    assert failed.state == "failed"
    assert failed.error == "job failed"
    assert "Traceback" not in failed.as_dict()["error"]
    assert retried.state == "succeeded"
