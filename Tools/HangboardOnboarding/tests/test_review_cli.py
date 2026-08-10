from __future__ import annotations

import json
from pathlib import Path

from hangboard_vectorizer import review_cli
from review_fixtures import make_review_run, make_review_run_with_edit


def test_main_inspect_prints_compact_json_and_returns_zero(
    tmp_path: Path, capsys
) -> None:
    run = make_review_run_with_edit(tmp_path)

    result = review_cli.main(["inspect", "--run", str(run)])

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    assert captured.out.endswith("\n")
    payload = json.loads(captured.out)
    assert payload["state"] == "edited"
    assert payload["nextAction"] == "lint"
    assert payload["artifacts"]["editedRegions"].endswith(
        "stage-2-regions.edited.json"
    )


def test_main_accepts_explicit_json_flag(tmp_path: Path, capsys) -> None:
    run = make_review_run(tmp_path)

    result = review_cli.main(["inspect", "--run", str(run), "--json"])

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    assert json.loads(captured.out)["state"] == "automatic"


def test_main_returns_two_for_invalid_arguments(capsys) -> None:
    result = review_cli.main(["inspect"])

    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert "usage:" in captured.err


def test_main_returns_three_for_artifact_errors(
    tmp_path: Path, capsys
) -> None:
    result = review_cli.main(["inspect", "--run", str(tmp_path / "missing-run")])

    captured = capsys.readouterr()
    assert result == 3
    assert captured.out == ""
    assert "error: review run root must be a directory" in captured.err
