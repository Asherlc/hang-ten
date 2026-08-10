from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess

from hangboard_vectorizer.review_artifacts import sha256_file
from review_fixtures import make_profile, make_review_run_with_edit


def test_complete_solo_review_workflow_via_wrapper(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    run = make_review_run_with_edit(tmp_path / "run")
    profile = make_profile(tmp_path / "profile")
    preview_root = tmp_path / "preview"
    compare_output = tmp_path / "compare.html"
    release_repo = _make_release_check_repo(tmp_path / "release-repo")
    stage1_path = run / "stages/01/attempt-0001/stage-1-auto-rgba.png"
    baseline_path = run / "stages/02/attempt-0001/stage-2-regions.json"
    original_hashes = {
        "stage1Image": sha256_file(stage1_path),
        "stage2Regions": sha256_file(baseline_path),
    }

    inspect_result = _run_wrapper(
        repository_root, "inspect", "--run", str(run)
    )
    assert inspect_result.returncode == 0, inspect_result.stderr
    inspect_payload = _parse_json_output(inspect_result)
    assert inspect_payload["state"] == "edited"
    assert inspect_payload["nextAction"] == "lint"

    compare_result = _run_wrapper(
        repository_root,
        "compare",
        "--run",
        str(run),
        "--output",
        str(compare_output),
    )
    assert compare_result.returncode == 0, compare_result.stderr
    compare_payload = _parse_json_output(compare_result)
    assert compare_payload["output"] == str(compare_output.resolve(strict=False))
    assert compare_output.is_file()

    lint_result = _run_wrapper(repository_root, "lint", "--run", str(run))
    assert lint_result.returncode == 0, lint_result.stderr
    lint_payload = _parse_json_output(lint_result)
    assert lint_payload["passed"] is True

    preview_result = _run_wrapper(
        repository_root,
        "preview",
        "--run",
        str(run),
        "--output",
        str(preview_root),
    )
    assert preview_result.returncode == 0, preview_result.stderr
    preview_payload = _parse_json_output(preview_result)
    assert Path(preview_payload["galleryPath"]).is_file()

    accept_result = _run_wrapper(
        repository_root,
        "accept",
        "--run",
        str(run),
        "--decision",
        "accepted",
        "--reviewer",
        "local-user",
        "--notes",
        "Reviewed fixture",
    )
    assert accept_result.returncode == 0, accept_result.stderr
    accept_payload = _parse_json_output(accept_result)
    assert accept_payload["decision"] == "accepted"
    assert accept_payload["reviewer"] == "local-user"
    assert "lintReportSha256" in accept_payload["source"]

    promote_result = _run_wrapper(
        repository_root,
        "promote",
        "--run",
        str(run),
        "--profile",
        str(profile),
        "--repository-root",
        str(release_repo),
        "--apply",
    )
    assert promote_result.returncode == 0, promote_result.stderr
    promote_payload = _parse_json_output(promote_result)
    assert promote_payload["status"] == "applied"
    assert promote_payload["plannedWrites"]
    subprocess.run(
        ["git", "add", "canonical/board.json"],
        cwd=release_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "Add promoted board",
        ],
        cwd=release_repo,
        check=True,
        capture_output=True,
        text=True,
    )

    release_check_result = _run_wrapper(
        repository_root,
        "release-check",
        "--run",
        str(run),
        "--repository-root",
        str(release_repo),
        "--explain",
    )
    assert release_check_result.returncode == 0, release_check_result.stderr
    release_check_payload = _parse_json_output(release_check_result)
    assert release_check_payload["passed"] is True
    assert any(
        check["name"] == "promotion-status" and check["passed"] is True
        for check in release_check_payload["checks"]
    )

    assert original_hashes == {
        "stage1Image": sha256_file(stage1_path),
        "stage2Regions": sha256_file(baseline_path),
    }


def test_wrapper_help_lists_complete_review_workflow() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    environment = os.environ.copy()
    environment["HANGBOARD_PYTHON"] = str(
        repository_root / ".context" / "hangboard-onboarding-venv" / "bin" / "python"
    )

    completed = subprocess.run(
        [str(repository_root / "scripts" / "hangboard-tools.sh"), "--help"],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert completed.returncode == 0
    for command in (
        "inspect",
        "compare",
        "lint",
        "preview",
        "accept",
        "promote",
        "release-check",
    ):
        assert command in completed.stdout


def _run_wrapper(repository_root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HANGBOARD_PYTHON"] = str(
        repository_root / ".context" / "hangboard-onboarding-venv" / "bin" / "python"
    )
    return subprocess.run(
        [str(repository_root / "scripts" / "hangboard-tools.sh"), *arguments],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def _parse_json_output(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    return json.loads(result.stdout.strip().splitlines()[-1])


def _make_release_check_repo(root: Path) -> Path:
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    export_script = scripts_dir / "export-plan-library.sh"
    export_script.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\necho 'stubbed export-plan-library check'\n",
        encoding="utf-8",
    )
    export_script.chmod(export_script.stat().st_mode | stat.S_IXUSR)
    subprocess.run(
        ["git", "init"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return root
