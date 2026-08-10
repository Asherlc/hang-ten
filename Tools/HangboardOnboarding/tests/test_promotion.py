from __future__ import annotations

import json
from pathlib import Path
import tomllib

import pytest

from hangboard_vectorizer import promotion_cli
from hangboard_vectorizer.promotion import promote_run
from hangboard_vectorizer.promotion_profile import load_promotion_profile
from hangboard_vectorizer.review_artifacts import discover_review_run, inspect_run
from review_fixtures import (
    make_profile,
    make_review_run_with_blocked_promotion,
    make_review_run_with_edit_and_acceptance,
    make_review_run_with_ready_promotion,
)


def test_promote_without_runtime_profile_returns_handoff_required(
    tmp_path: Path,
) -> None:
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")

    report = promote_run(discover_review_run(run), None, tmp_path / "repo")

    assert report.status == "handoff-required"
    assert (
        run
        / "stages/02/attempt-0001/promotion/board-promotion-report.json"
    ).is_file()


def test_promote_blocks_changed_artifact_after_acceptance(tmp_path: Path) -> None:
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")
    edited = run / "stages/02/attempt-0001/stage-2-regions.edited.json"
    edited.write_text(edited.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    report = promote_run(discover_review_run(run), None, tmp_path / "repo")

    assert report.status == "blocked"
    assert any("hash" in error for error in report.errors)


def test_apply_rejects_destination_outside_repository_root(tmp_path: Path) -> None:
    profile = make_profile(tmp_path, destination_relative="../../outside.json")

    with pytest.raises(ValueError, match="outside repository root"):
        load_promotion_profile(profile)


def test_promote_with_profile_returns_ready_dry_run_and_planned_writes(
    tmp_path: Path,
) -> None:
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")
    repository_root = tmp_path / "repo"
    profile = load_promotion_profile(make_profile(tmp_path / "profile"))

    report = promote_run(discover_review_run(run), profile, repository_root)

    assert report.status == "ready"
    assert report.profileId == "fixture-profile"
    assert report.boardId == "fixture-board"
    assert report.errors == ()
    assert "profileId" not in report.inputHashes
    assert report.plannedWrites == (
        {
            "destination": "canonical/board.json",
            "sha256": report.outputHashes["promotion/edited-regions.json"],
            "source": "promotion/edited-regions.json",
        },
    )
    assert (repository_root / "canonical/board.json").exists() is False
    package_copy = run / "stages/02/attempt-0001/promotion/edited-regions.json"
    assert package_copy.is_file()


def test_promote_with_missing_required_region_returns_blocked(
    tmp_path: Path,
) -> None:
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")
    profile = make_profile(
        tmp_path / "profile",
        required_region_keys=("missing",),
        runtime_mappings=(
            {
                "regionKey": "missing",
                "runtimeHoldId": "runtime-missing",
                "gripType": "edge",
                "interactionMode": "surface",
            },
        ),
    )

    report = promote_run(
        discover_review_run(run),
        load_promotion_profile(profile),
        tmp_path / "repo",
    )

    assert report.status == "blocked"
    assert any("missing" in error for error in report.errors)


def test_promote_apply_copies_profile_destinations_atomically(tmp_path: Path) -> None:
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")
    repository_root = tmp_path / "repo"
    profile = load_promotion_profile(make_profile(tmp_path / "profile"))

    report = promote_run(
        discover_review_run(run),
        profile,
        repository_root,
        apply=True,
    )

    destination = repository_root / "canonical/board.json"
    package_copy = run / "stages/02/attempt-0001/promotion/edited-regions.json"
    assert report.status == "ready"
    assert destination.read_text(encoding="utf-8") == package_copy.read_text(
        encoding="utf-8"
    )
    assert report.outputHashes["canonical/board.json"] == report.outputHashes[
        "promotion/edited-regions.json"
    ]


def test_main_promote_prints_compact_json_and_returns_zero(
    tmp_path: Path, capsys
) -> None:
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")
    profile = make_profile(tmp_path / "profile")
    repository_root = tmp_path / "repo"

    result = promotion_cli.main(
        [
            "promote",
            "--run",
            str(run),
            "--profile",
            str(profile),
            "--repository-root",
            str(repository_root),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["status"] == "ready"
    assert payload["plannedWrites"][0]["destination"] == "canonical/board.json"


def test_main_promote_returns_two_when_apply_lacks_profile(
    tmp_path: Path, capsys
) -> None:
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")

    result = promotion_cli.main(
        [
            "promote",
            "--run",
            str(run),
            "--repository-root",
            str(tmp_path / "repo"),
            "--apply",
        ]
    )

    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert "--apply requires --profile" in captured.err


def test_pyproject_registers_promote_script_without_release_check() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    scripts = project["project"]["scripts"]
    assert scripts["hangboard-promote"] == "hangboard_vectorizer.promotion_cli:main"
    assert "hangboard-release-check" not in scripts


def test_wrapper_exposes_promote_without_release_check() -> None:
    script_path = Path(__file__).resolve().parents[3] / "scripts/hangboard-tools.sh"
    script = script_path.read_text(encoding="utf-8")

    assert "promote)" in script
    assert "hangboard-promote" in script
    assert "release-check)" not in script


def test_blocked_and_ready_promotion_fixtures_cover_task_four_states(
    tmp_path: Path,
) -> None:
    blocked = make_review_run_with_blocked_promotion(tmp_path / "blocked")
    blocked_report = promote_run(discover_review_run(blocked), None, tmp_path / "repo")
    assert blocked_report.status == "blocked"

    ready = make_review_run_with_ready_promotion(tmp_path / "ready")
    report_path = (
        ready / "stages/02/attempt-0001/promotion/board-promotion-report.json"
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ready"


def test_inspect_run_keeps_handoff_required_promotion_at_accepted_state(
    tmp_path: Path,
) -> None:
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")
    promote_run(discover_review_run(run), None, tmp_path / "repo")

    inspected = inspect_run(discover_review_run(run))

    assert inspected["state"] == "accepted"
    assert inspected["nextAction"] == "promote"
    assert inspected["artifacts"]["promotionReport"] == (
        "stages/02/attempt-0001/promotion/board-promotion-report.json"
    )


def test_inspect_run_keeps_blocked_promotion_at_accepted_state(
    tmp_path: Path,
) -> None:
    run = make_review_run_with_blocked_promotion(tmp_path / "run")
    promote_run(discover_review_run(run), None, tmp_path / "repo")

    inspected = inspect_run(discover_review_run(run))

    assert inspected["state"] == "accepted"
    assert inspected["nextAction"] == "promote"


def test_inspect_run_uses_promoted_state_without_release_check_next_action(
    tmp_path: Path,
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")

    inspected = inspect_run(discover_review_run(run))

    assert inspected["state"] == "promoted"
    assert inspected["nextAction"] == "promote"
