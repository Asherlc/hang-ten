from __future__ import annotations

import os
from pathlib import Path
import subprocess

from hangboard_vectorizer import review_cli
from hangboard_vectorizer.promotion import promote_run
from hangboard_vectorizer.review_acceptance import validate_acceptance
from hangboard_vectorizer.review_artifacts import discover_review_run
from review_fixtures import make_review_run_with_edit


def test_complete_solo_review_workflow(tmp_path: Path) -> None:
    run = make_review_run_with_edit(tmp_path / "run")
    discovered = discover_review_run(run)

    assert review_cli.main(["inspect", "--run", str(run)]) == 0
    assert review_cli.main(["lint", "--run", str(run)]) == 0
    assert (
        review_cli.main(
            ["preview", "--run", str(run), "--output", str(tmp_path / "preview")]
        )
        == 0
    )
    assert (
        review_cli.main(
            [
                "accept",
                "--run",
                str(run),
                "--decision",
                "accepted",
                "--reviewer",
                "local-user",
                "--notes",
                "Reviewed fixture",
            ]
        )
        == 0
    )
    report = promote_run(discovered, None, tmp_path / "repo")
    assert report.status == "handoff-required"
    assert validate_acceptance(discover_review_run(run)).decision == "accepted"


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
