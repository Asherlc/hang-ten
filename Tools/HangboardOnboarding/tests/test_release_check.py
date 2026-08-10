from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from hangboard_vectorizer import release_check_cli
from hangboard_vectorizer.release_check import release_check_report, run_release_check
from hangboard_vectorizer.review_artifacts import discover_review_run
from review_fixtures import (
    make_profile,
    make_review_run_with_blocked_promotion,
    make_review_run_with_edit_and_acceptance,
    make_review_run_with_ready_promotion,
)
from hangboard_vectorizer.promotion import promote_run
from hangboard_vectorizer.promotion_profile import load_promotion_profile


def test_release_check_fails_when_promotion_is_blocked(tmp_path: Path) -> None:
    run = make_review_run_with_blocked_promotion(tmp_path / "run")

    results = run_release_check(discover_review_run(run), tmp_path, run_xcode=False)

    assert results[0].name == "promotion-status"
    assert results[0].passed is False


def test_release_check_runs_export_check_with_repository_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...], **_: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    results = run_release_check(discover_review_run(run), tmp_path, run_xcode=False)

    assert any(command[-2:] == ("export-plan-library.sh", "--check") for command in calls)
    assert all(result.passed for result in results)
    assert (tmp_path / "canonical/board.json").is_file()


def test_release_check_fails_when_a_planned_destination_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")
    profile = load_promotion_profile(make_profile(tmp_path / "profile"))
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    promote_run(discover_review_run(run), profile, repository_root)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "ok", ""),
    )

    results = run_release_check(
        discover_review_run(run), repository_root, run_xcode=False
    )

    output_result = _result_named(results, "promotion-output-hashes")
    assert output_result.passed is False
    assert "canonical/board.json" in (output_result.error or "")


def test_release_check_fails_when_a_planned_destination_is_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")
    profile = load_promotion_profile(make_profile(tmp_path / "profile"))
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    promote_run(discover_review_run(run), profile, repository_root, apply=True)
    destination = repository_root / "canonical/board.json"
    destination.write_text(destination.read_text(encoding="utf-8") + "\n")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "ok", ""),
    )

    results = run_release_check(
        discover_review_run(run), repository_root, run_xcode=False
    )

    output_result = _result_named(results, "promotion-output-hashes")
    assert output_result.passed is False
    assert "canonical/board.json" in (output_result.error or "")


def test_release_check_fails_when_promotion_input_hashes_are_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    edited = run / "stages/02/attempt-0001/stage-2-regions.edited.json"
    edited.write_text(edited.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "ok", ""),
    )

    results = run_release_check(discover_review_run(run), tmp_path, run_xcode=False)

    assert _result_named(results, "promotion-input-hashes").passed is False


def test_release_check_fails_when_promotion_output_hashes_are_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    package_copy = run / "stages/02/attempt-0001/promotion/edited-regions.json"
    package_copy.write_text(package_copy.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "ok", ""),
    )

    results = run_release_check(discover_review_run(run), tmp_path, run_xcode=False)

    assert _result_named(results, "promotion-output-hashes").passed is False


def test_release_check_fails_when_destination_artifact_is_uncommitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    subprocess.run(("git", "init"), cwd=repository_root, check=True, capture_output=True, text=True)
    destination = repository_root / "canonical/board.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("{\"uncommitted\":true}\n", encoding="utf-8")

    real_run = subprocess.run

    def fake_run(
        command: tuple[str, ...], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if command[-2:] == ("export-plan-library.sh", "--check"):
            return subprocess.CompletedProcess(command, 0, "ok", "")
        return real_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)

    results = run_release_check(
        discover_review_run(run), repository_root, run_xcode=False
    )

    assert _result_named(results, "generated-artifacts-clean").passed is False


def test_release_check_fails_when_profile_runtime_mappings_are_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    report_path = run / "stages/02/attempt-0001/promotion/board-promotion-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["profile"] = {
        "requiredRegionKeys": ["left", "right"],
        "runtimeMappings": [
            {
                "regionKey": "left",
                "runtimeHoldId": "runtime-left",
                "gripType": "edge",
                "interactionMode": "surface",
            }
        ],
    }
    report_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "ok", ""),
    )

    results = run_release_check(discover_review_run(run), tmp_path, run_xcode=False)

    profile_result = _result_named(results, "promotion-runtime")
    assert profile_result.passed is False
    assert "right" in (profile_result.error or "")


def test_release_check_fails_when_profile_source_hash_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    profile_path = run / ".context/profile/promotion-profile.json"
    profile_path.write_text(
        profile_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "ok", ""),
    )

    results = run_release_check(discover_review_run(run), tmp_path, run_xcode=False)

    runtime_result = _result_named(results, "promotion-runtime")
    assert runtime_result.passed is False
    assert "profile hash changed" in (runtime_result.error or "")


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("regionKey", "right"),
        ("runtimeHoldId", "runtime-tampered"),
        ("gripType", "pocket"),
        ("interactionMode", "aperture"),
    ],
)
def test_release_check_compares_every_runtime_mapping_field_to_profile_and_regions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    replacement: str,
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    report_path = run / "stages/02/attempt-0001/promotion/board-promotion-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["profile"]["runtimeMappings"][0][field] = replacement
    report_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "ok", ""),
    )

    results = run_release_check(discover_review_run(run), tmp_path, run_xcode=False)

    runtime_result = _result_named(results, "promotion-runtime")
    assert runtime_result.passed is False
    assert field in (runtime_result.error or "")


def test_release_check_cli_explain_returns_machine_readable_blockers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run = make_review_run_with_blocked_promotion(tmp_path / "run")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "ok", ""),
    )

    result = release_check_cli.main(
        [
            "release-check",
            "--run",
            str(run),
            "--repository-root",
            str(tmp_path),
            "--json",
            "--explain",
        ]
    )

    captured = capsys.readouterr()
    assert result == 3
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["passed"] is False
    assert payload["blockers"][0]["check"] == "promotion-status"
    assert payload["blockers"][0]["remediation"]
    report_path = run / "stages/02/attempt-0001/promotion/release-check.json"
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert len(persisted["checks"]) == len(payload["checks"])


@pytest.mark.parametrize("target", ["run", "repository-root"])
def test_release_check_cli_returns_two_for_invalid_inputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], target: str
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    arguments = [
        "release-check",
        "--run",
        str(run),
        "--repository-root",
        str(tmp_path),
        "--json",
    ]
    if target == "run":
        arguments[2] = str(tmp_path / "missing-run")
    else:
        arguments[4] = str(tmp_path / "missing-repository-root")

    result = release_check_cli.main(arguments)

    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert "directory" in captured.err


def test_release_check_cli_explain_returns_json_for_malformed_promotion_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    report_path = run / "stages/02/attempt-0001/promotion/board-promotion-report.json"
    report_path.write_text("{not-json}\n", encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "ok", ""),
    )

    result = release_check_cli.main(
        [
            "release-check",
            "--run",
            str(run),
            "--repository-root",
            str(tmp_path),
            "--json",
            "--explain",
        ]
    )

    captured = capsys.readouterr()
    assert result == 3
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["passed"] is False
    assert any(blocker["check"] == "promotion-status" for blocker in payload["blockers"])
    assert payload["checks"]


def test_release_check_cli_explain_returns_json_for_malformed_edited_regions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    edited_path = run / "stages/02/attempt-0001/stage-2-regions.edited.json"
    edited_path.write_text("{not-json}\n", encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "ok", ""),
    )

    result = release_check_cli.main(
        [
            "release-check",
            "--run",
            str(run),
            "--repository-root",
            str(tmp_path),
            "--json",
            "--explain",
        ]
    )

    captured = capsys.readouterr()
    assert result == 3
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["passed"] is False
    assert any(blocker["check"] == "promotion-runtime" for blocker in payload["blockers"])
    assert payload["checks"]


def test_release_check_report_returns_checks_and_generated_timestamp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "ok", ""),
    )

    report = release_check_report(
        run_release_check(discover_review_run(run), tmp_path, run_xcode=False)
    )

    assert report["passed"] is True
    assert report["checks"]
    assert str(report["generatedAt"]).endswith("Z")


def _result_named(results: tuple[object, ...], name: str) -> object:
    for result in results:
        if getattr(result, "name", None) == name:
            return result
    raise AssertionError(f"missing result named {name}")
