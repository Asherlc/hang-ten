from __future__ import annotations

import json
import os
import subprocess
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "Hangboards" / "catalog.json"
SCRIPT_PATH = REPO_ROOT / "scripts" / "hangboard-tools.sh"
BOARD_ID = "metolius.wood-grips-compact-ii"
ACCEPTED_RUN_PATH = (
    REPO_ROOT
    / "Tools"
    / "HangboardPipeline"
    / "boards"
    / "metolius-wood-grips-compact-ii"
)


def test_supported_tool_roots_expose_the_pipeline_and_workbench_contract() -> None:
    """A path relocation must not leave the wrapper targeting the retired roots."""
    assert (REPO_ROOT / "Tools/HangboardPipeline/src/hangboard_vectorizer").is_dir()
    assert (REPO_ROOT / "Tools/HangboardPipeline/boards").is_dir()
    assert (REPO_ROOT / "Tools/HangboardWorkbench/server.py").is_file()
    assert not (REPO_ROOT / "Tools/HangboardOnboarding").exists()
    assert not (REPO_ROOT / "Tools/hold-highlight-editor").exists()


def _fixture_catalog(destination_root: Path) -> tuple[Path, Path]:
    hangboards_root = destination_root / "Hangboards"
    board_root = hangboards_root / "metolius-wood-grips-compact-ii"
    board_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CATALOG_PATH, hangboards_root / "catalog.json")
    shutil.copy2(
        REPO_ROOT / "Hangboards" / "metolius-wood-grips-compact-ii" / "board.json",
        board_root / "board.json",
    )
    shutil.copy2(
        REPO_ROOT / "Hangboards" / "metolius-wood-grips-compact-ii" / "evidence.json",
        board_root / "evidence.json",
    )
    return hangboards_root / "catalog.json", board_root / "board.json"


def _wrapper_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["HANGBOARD_PYTHON"] = "/opt/homebrew/bin/python3.12"
    environment["PIP_NO_BUILD_ISOLATION"] = "1"
    return environment


def _catalog_payload_with_no_runs(lifecycle: str = "shipped") -> dict[str, object]:
    return {
        "id": "metolius.wood-grips-compact-ii",
        "lifecycle": lifecycle,
        "path": "metolius-wood-grips-compact-ii/board.json",
        "onboardingRuns": [],
        "status": "ok",
    }


def _run_catalog_cli(command: list[str]) -> dict[str, object]:
    result = subprocess.run(
        [str(SCRIPT_PATH), "catalog", *command],
        text=True,
        capture_output=True,
        check=False,
        env=_wrapper_environment(),
    )
    assert result.returncode == 0, result.stderr
    output = result.stdout.strip()
    assert output, "hangboard-tools catalog output was empty"
    try:
        payload = json.loads(output)
        assert isinstance(payload, dict)
        return payload
    except json.JSONDecodeError:
        start = output.find("{")
        assert start != -1, f"catalog output was not JSON:\n{result.stdout}"
        depth = 0
        end = None
        for idx in range(start, len(output)):
            char = output[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = idx + 1
                    break
        assert end is not None, f"catalog output was not JSON:\n{result.stdout}"
        payload = json.loads(output[start:end])
        assert isinstance(payload, dict)
        return payload


def test_catalog_cli_validate_prints_expected_json(tmp_path: Path):
    catalog_path, _ = _fixture_catalog(tmp_path)

    payload = _run_catalog_cli(
        ["validate", "--catalog", str(catalog_path)]
    )

    assert payload == {"boards": [_catalog_payload_with_no_runs()]}


def test_catalog_cli_status_matches_validate(tmp_path: Path):
    catalog_path, _ = _fixture_catalog(tmp_path)
    expected = {"boards": [_catalog_payload_with_no_runs()]}

    validate_payload = _run_catalog_cli(["validate", "--catalog", str(catalog_path)])
    status_payload = _run_catalog_cli(["status", "--catalog", str(catalog_path)])

    assert validate_payload == expected
    assert status_payload == expected


def test_catalog_cli_register_writes_approved_run_and_updates_catalog(tmp_path: Path):
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

    register_payload = _run_catalog_cli(
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

    assert register_payload["id"] == BOARD_ID
    assert register_payload["lifecycle"] == "approved"
    assert register_payload["runCount"] == 1
    assert register_payload["regionCount"] == 19

    copied_run = board_path.parent / "onboarding" / "runs" / "accepted-run"
    assert copied_run.is_dir()
    assert (copied_run / "run.json").is_file()

    status = _run_catalog_cli(["status", "--catalog", str(catalog_path)])["boards"][0]
    assert status["lifecycle"] == "approved"
    assert status["onboardingRuns"][0]["status"] == "complete"
    assert status["onboardingRuns"][0]["id"] == "accepted-run"


def test_catalog_cli_validate_missing_catalog_returns_error(tmp_path: Path):
    result = subprocess.run(
        [
            str(SCRIPT_PATH),
            "catalog",
            "validate",
            "--catalog",
            str(tmp_path / "missing-catalog.json"),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=_wrapper_environment(),
    )

    assert result.returncode == 1
    assert "does not exist" in result.stderr


def test_catalog_cli_register_unknown_board_returns_error(tmp_path: Path):
    catalog_path, _ = _fixture_catalog(tmp_path)

    result = subprocess.run(
        [
            str(SCRIPT_PATH),
            "catalog",
            "register",
            "--catalog",
            str(catalog_path),
            "--board",
            "unknown.board",
            "--run",
            str(tmp_path / ".context" / "missing-run"),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=_wrapper_environment(),
    )

    assert result.returncode == 1
    assert "board id not found" in result.stderr


def test_catalog_cli_malformed_command_returns_usage_error():
    result = subprocess.run(
        [str(SCRIPT_PATH), "catalog"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "usage:" in result.stderr.lower()
