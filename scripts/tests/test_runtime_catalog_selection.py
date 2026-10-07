"""A release must select the catalog execution actually tested by its CI attempt."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "catalog_selection", Path(__file__).resolve().parents[1] / "select-runtime-catalog.py")
catalog_selection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_selection)


def producer_jobs(*attempts):
    return [{"run_id": 42, "name": "Compile runtime assets / Assemble runtime catalog",
             "run_attempt": attempt, "status": "completed", "conclusion": "success",
             "started_at": f"2026-10-05T{attempt:02d}:00:00Z",
             "completed_at": f"2026-10-05T{attempt:02d}:05:00Z",
             "runner_id": 10000 + attempt, "runner_name": f"GitHub Actions {10000 + attempt}"}
            for attempt in attempts]


def test_copied_successful_job_does_not_fabricate_a_catalog_producer():
    artifacts = [{"name": "hang-ten-board-assets-42-1", "id": 101, "expired": False},
                 {"name": "hang-ten-board-assets-42-2", "id": 102, "expired": False}]
    original = dict(producer_jobs(2)[0], id=200, runner_id=1000676350,
                    runner_name="GitHub Actions 1000676350", runner_group_id=0,
                    started_at="2026-10-05T05:06:29Z", completed_at="2026-10-05T05:09:41Z")
    # GitHub gives retained jobs a new ID/attempt and clears runner_group_id,
    # while preserving the original execution's timestamps and runner.
    copied = dict(original, id=300, run_attempt=3, runner_group_id=None)
    assert catalog_selection.select_catalog_artifact(
        artifacts, "hang-ten", 42, 3, jobs=[original, copied]) == 102


@pytest.mark.parametrize("reverse_history", [False, True])
def test_multiple_test_only_retries_keep_the_original_catalog(reverse_history):
    original = producer_jobs(1)[0]
    jobs = [original, dict(original, run_attempt=2), dict(original, run_attempt=3)]
    if reverse_history:
        jobs.reverse()
    artifacts = [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False}]
    assert catalog_selection.select_catalog_artifact(artifacts, "hang-ten", 42, 3, jobs=jobs) == 101


def test_delayed_release_ignores_future_assemblies_and_their_copies():
    first, second = producer_jobs(1, 2)
    jobs = [dict(second, run_attempt=3), dict(first, run_attempt=3), second, first]
    artifacts = [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False},
                 {"id": 102, "name": "hang-ten-board-assets-42-2", "expired": False}]
    assert catalog_selection.select_catalog_artifact(artifacts, "hang-ten", 42, 1, jobs=jobs) == 101
    assert catalog_selection.select_catalog_artifact(artifacts, "hang-ten", 42, 3, jobs=jobs) == 102


@pytest.mark.parametrize("damage", ["missing_start", "invalid_start", "missing_end", "invalid_end",
                                    "reversed_times", "missing_runner", "invalid_runner", "empty_runner_name"])
def test_successful_producer_requires_a_valid_execution_identity(damage):
    job = producer_jobs(1)[0]
    if damage == "missing_start": job.pop("started_at")
    elif damage == "invalid_start": job["started_at"] = "not-a-timestamp"
    elif damage == "missing_end": job.pop("completed_at")
    elif damage == "invalid_end": job["completed_at"] = "2026-10-05T01:05:00"
    elif damage == "reversed_times": job["completed_at"] = "2026-10-04T01:05:00Z"
    elif damage == "missing_runner": job.pop("runner_id")
    elif damage == "invalid_runner": job["runner_id"] = True
    elif damage == "empty_runner_name": job["runner_name"] = " "
    artifacts = [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False}]
    with pytest.raises(ValueError, match="execution identity"):
        catalog_selection.select_catalog_artifact(artifacts, "hang-ten", 42, 1, jobs=[job])


def test_distinct_latest_producer_executions_are_ambiguous():
    first, second = producer_jobs(1, 2)
    artifacts = [{"id": 102, "name": "hang-ten-board-assets-42-2", "expired": False}]
    with pytest.raises(ValueError, match="ambiguous.*producer"):
        catalog_selection.select_catalog_artifact(
            artifacts, "hang-ten", 42, 2, jobs=[first, second, dict(second, runner_id=99999)])


def test_missing_original_execution_does_not_guess_an_older_catalog():
    copied = dict(producer_jobs(1)[0], run_attempt=3)
    artifacts = [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False}]
    with pytest.raises(ValueError, match="no catalog"):
        catalog_selection.select_catalog_artifact(artifacts, "hang-ten", 42, 3, jobs=[copied])


def test_delayed_release_cannot_receive_a_later_untested_retry():
    artifacts = [
        {"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False},
        {"id": 102, "name": "hang-ten-board-assets-42-2", "expired": False},
    ]
    assert catalog_selection.select_catalog_artifact(artifacts, "hang-ten", 42, 1, jobs=producer_jobs(1, 2)) == 101


def test_test_only_retry_uses_the_latest_retained_catalog_producer():
    artifacts = [
        {"id": 104, "name": "hang-ten-board-assets-42-4", "expired": False},
        {"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False},
        {"id": 102, "name": "hang-ten-board-assets-42-2", "expired": False},
    ]
    assert catalog_selection.select_catalog_artifact(artifacts, "hang-ten", 42, 3, jobs=producer_jobs(1, 2, 4)) == 102


@pytest.mark.parametrize("damage", ["expired", "duplicate", "missing_id", "invalid_id"])
def test_release_cannot_fall_back_from_an_unusable_latest_catalog(damage):
    latest = {"id": 102, "name": "hang-ten-board-assets-42-2", "expired": False}
    artifacts = [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False}, latest]
    if damage == "expired": latest["expired"] = True
    elif damage == "duplicate": artifacts.append({**latest, "id": 103})
    elif damage == "missing_id": latest.pop("id")
    elif damage == "invalid_id": latest["id"] = True
    with pytest.raises(ValueError):
        catalog_selection.select_catalog_artifact(artifacts, "hang-ten", 42, 3, jobs=producer_jobs(1, 2))


def test_catalog_selection_requires_the_exact_owner_run_and_producer_attempt():
    artifacts = [
        {"id": 1, "name": "other-board-assets-42-1", "expired": False},
        {"id": 2, "name": "hang-ten-board-assets-43-1", "expired": False},
        {"id": 3, "name": "hang-ten-board-assets-42", "expired": False},
        {"id": 4, "name": "hang-ten-board-assets-42-zero", "expired": False},
        {"id": 5, "name": "hang-ten-board-assets-42-0", "expired": False},
        {"id": 6, "name": "hang-ten-board-assets-42-2", "expired": False},
    ]
    with pytest.raises(ValueError, match="no catalog"):
        catalog_selection.select_catalog_artifact(artifacts, "hang-ten", 42, 1, jobs=producer_jobs(1))


def test_deleted_latest_catalog_cannot_select_an_older_producer():
    artifacts = [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False}]
    with pytest.raises(ValueError, match="no catalog"):
        catalog_selection.select_catalog_artifact(artifacts, "hang-ten", 42, 3, jobs=producer_jobs(1, 2))


@pytest.mark.parametrize("damage", ["failed", "running", "other_run", "other_job", "future", "missing"])
def test_catalog_selection_requires_a_successful_producer_in_the_tested_run(damage):
    jobs = producer_jobs(1)
    if damage == "failed": jobs[0]["conclusion"] = "failure"
    elif damage == "running": jobs[0]["status"] = "in_progress"
    elif damage == "other_run": jobs[0]["run_id"] = 43
    elif damage == "other_job": jobs[0]["name"] = "Compile board shard 1"
    elif damage == "future": jobs[0]["run_attempt"] = 2
    elif damage == "missing": jobs = []
    artifacts = [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False}]
    with pytest.raises(ValueError, match="no successful catalog producer"):
        catalog_selection.select_catalog_artifact(artifacts, "hang-ten", 42, 1, jobs=jobs)


def test_paginated_release_selection_prints_only_the_immutable_id(tmp_path, monkeypatch, capsys):
    artifacts = tmp_path / "artifacts.json"
    artifacts.write_text(json.dumps([
        {"artifacts": [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False}]},
        {"artifacts": [{"id": 102, "name": "hang-ten-board-assets-42-2", "expired": False}]},
    ]))
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps([{"jobs": producer_jobs(1)}, {"jobs": producer_jobs(2)}]))
    monkeypatch.setattr(sys, "argv", ["select-runtime-catalog.py", "--artifact-pages", str(artifacts),
                                   "--job-pages", str(jobs), "--owner", "hang-ten",
                                   "--run-id", "42", "--run-attempt", "3"])
    assert catalog_selection.main() == 0
    assert capsys.readouterr().out == "102\n"
