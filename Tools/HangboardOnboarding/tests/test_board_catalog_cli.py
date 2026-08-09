from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from hangboard_vectorizer import board_catalog_cli

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "Hangboards" / "catalog.json"
BOARD_ID = "metolius.wood-grips-compact-ii"
ACCEPTED_RUN_PATH = (
    REPO_ROOT
    / "Tools"
    / "HangboardOnboarding"
    / "reference"
    / "metolius-compact-ii"
    / "accepted-run"
)


def _fixture_catalog(destination_root: Path) -> tuple[Path, Path]:
    hangboards_root = destination_root / "Hangboards"
    board_root = hangboards_root / "metolius-wood-grips-compact-ii"
    board_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CATALOG_PATH, hangboards_root / "catalog.json")
    shutil.copy2(
        REPO_ROOT / "Hangboards" / "metolius-wood-grips-compact-ii" / "board.json",
        board_root / "board.json",
    )
    return hangboards_root / "catalog.json", board_root / "board.json"


def _catalog_payload_with_no_runs(lifecycle: str = "shipped") -> dict[str, object]:
    return {
        "id": "metolius.wood-grips-compact-ii",
        "lifecycle": lifecycle,
        "path": "metolius-wood-grips-compact-ii/board.json",
        "onboardingRuns": [],
        "status": "ok",
    }


def test_catalog_cli_validate_prints_expected_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    catalog_path, _ = _fixture_catalog(tmp_path)

    result = board_catalog_cli.main(["validate", "--catalog", str(catalog_path)])

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"boards": [_catalog_payload_with_no_runs()]}


def test_catalog_cli_status_matches_validate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    catalog_path, _ = _fixture_catalog(tmp_path)
    expected = {"boards": [_catalog_payload_with_no_runs()]}

    validate_result = board_catalog_cli.main(["validate", "--catalog", str(catalog_path)])
    validate_payload = json.loads(capsys.readouterr().out)
    status_result = board_catalog_cli.main(["status", "--catalog", str(catalog_path)])
    status_payload = json.loads(capsys.readouterr().out)

    assert validate_result == 0
    assert status_result == 0
    assert validate_payload == expected
    assert status_payload == expected


def test_catalog_cli_register_writes_approved_run_and_updates_catalog(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    catalog_path, board_path = _fixture_catalog(tmp_path)
    catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog_payload["boards"][0]["lifecycle"] = "draft"
    catalog_path.write_text(json.dumps(catalog_payload, indent=2) + "\n", encoding="utf-8")
    board_payload = json.loads(board_path.read_text(encoding="utf-8"))
    board_payload["lifecycle"] = "draft"
    board_payload["onboardingRuns"] = []
    board_path.write_text(json.dumps(board_payload, indent=2) + "\n", encoding="utf-8")

    run_root = tmp_path / ".context" / "hangboard-onboarding" / "metolius-compact-ii"
    shutil.copytree(ACCEPTED_RUN_PATH, run_root)

    result = board_catalog_cli.main(
        [
            "register",
            "--catalog",
            str(catalog_path),
            "--board",
            BOARD_ID,
            "--run",
            str(run_root),
            "--run-id",
            "accepted-run",
        ]
    )

    register_payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert register_payload["id"] == BOARD_ID
    assert register_payload["lifecycle"] == "approved"
    assert register_payload["runCount"] == 1
    assert register_payload["regionCount"] == 19

    copied_run = board_path.parent / "onboarding" / "runs" / "accepted-run"
    assert copied_run.is_dir()
    assert (copied_run / "run.json").is_file()

    status_result = board_catalog_cli.main(["status", "--catalog", str(catalog_path)])
    status = json.loads(capsys.readouterr().out)["boards"][0]
    assert status_result == 0
    assert status["lifecycle"] == "approved"
    assert status["onboardingRuns"][0]["status"] == "complete"
    assert status["onboardingRuns"][0]["id"] == "accepted-run"
