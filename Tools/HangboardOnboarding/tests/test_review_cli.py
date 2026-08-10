from __future__ import annotations

import json
from pathlib import Path

from hangboard_vectorizer import review_cli
from review_fixtures import (
    make_review_run,
    make_review_run_with_edit,
    make_review_run_with_edit_and_acceptance,
)


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


def test_main_lint_writes_report_and_prints_json(tmp_path: Path, capsys) -> None:
    run = make_review_run_with_edit(tmp_path)

    result = review_cli.main(["lint", "--run", str(run), "--json"])

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["passed"] is True
    assert (
        run / "stages/02/attempt-0001/lint-report.json"
    ).is_file()


def test_main_accept_defaults_reviewer_and_prints_json(tmp_path: Path, capsys) -> None:
    run = make_review_run_with_edit(tmp_path)

    result = review_cli.main(
        [
            "accept",
            "--run",
            str(run),
            "--decision",
            "accepted",
            "--notes",
            "Reviewed all regions",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["decision"] == "accepted"
    assert payload["reviewer"] == "local-user"


def test_main_inspect_reports_accepted_state_after_acceptance(
    tmp_path: Path, capsys
) -> None:
    run = make_review_run_with_edit_and_acceptance(tmp_path)

    result = review_cli.main(["inspect", "--run", str(run)])

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["state"] == "accepted"
    assert payload["nextAction"] == "promote"


def test_main_preview_writes_bundle_and_prints_json(tmp_path: Path, capsys) -> None:
    run = make_review_run_with_edit(tmp_path / "run")
    output = tmp_path / "preview-output"

    result = review_cli.main(
        ["preview", "--run", str(run), "--output", str(output)]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["galleryPath"] == str(output / "review-preview/review-gallery.html")
    assert (output / "review-preview/automatic.png").is_file()
    assert (output / "review-preview/edited.png").is_file()


def test_main_compare_prints_output_path_and_returns_two_without_edited_regions(
    tmp_path: Path, capsys
) -> None:
    run = make_review_run(tmp_path / "run")
    output = tmp_path / "compare.html"

    result = review_cli.main(
        ["compare", "--run", str(run), "--output", str(output)]
    )

    captured = capsys.readouterr()
    assert result == 2
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["output"] == str(output.resolve(strict=False))
    assert output.is_file() is False


def test_main_preview_returns_three_for_invalid_region_data(
    tmp_path: Path, capsys
) -> None:
    run = make_review_run_with_edit(
        tmp_path / "run",
        mutate_edited=lambda document: document["regions"].__setitem__(0, {"id": 1}),
    )
    output = tmp_path / "preview-output"

    result = review_cli.main(
        ["preview", "--run", str(run), "--output", str(output)]
    )

    captured = capsys.readouterr()
    assert result == 3
    assert captured.out == ""
    assert "error:" in captured.err
