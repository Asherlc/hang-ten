from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import write_board_package, write_primary_only_draft

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "hangboard-packages.sh"


def _run_cli(
    *args: str,
    environment_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HANGBOARD_PYTHON"] = sys.executable
    environment.update(environment_overrides or {})
    return subprocess.run(
        [str(SCRIPT_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )


def _json_output(output: str) -> dict[str, object]:
    return json.loads(output[output.find("{") :])


def test_package_cli_reports_directly_discovered_boards_and_drafts(tmp_path: Path) -> None:
    write_board_package(tmp_path / "package-board", board_id="fixture.board")
    write_primary_only_draft(tmp_path / "draft-board")

    result = _run_cli("status", "--root", str(tmp_path))

    assert result.returncode == 0, result.stderr
    assert _json_output(result.stdout) == {
        "boards": [{"id": "fixture.board", "path": "package-board"}],
        "drafts": ["draft-board"],
    }


def test_package_cli_final_inventory_rejects_drafts(tmp_path: Path) -> None:
    write_primary_only_draft(tmp_path / "draft-board")

    result = _run_cli(
        "validate",
        "--root",
        str(tmp_path),
        "--final-inventory",
    )

    assert result.returncode == 1
    assert "missing board.json" in result.stderr


def test_wrapper_rejects_python_3_11_3_before_validation(tmp_path: Path) -> None:
    package_root = tmp_path / "packages"
    write_board_package(package_root / "package-board", board_id="fixture.board")
    version_override = tmp_path / "python-version"
    version_override.mkdir()
    (version_override / "sitecustomize.py").write_text(
        "import sys\nsys.version_info = (3, 11, 3, 'final', 0)\n",
        encoding="utf-8",
    )

    result = _run_cli(
        "status",
        "--root",
        str(package_root),
        environment_overrides={"PYTHONPATH": str(version_override)},
    )

    assert result.returncode == 69
    assert result.stderr == (
        "Hangboard package validation requires Python 3.11.4 or newer.\n"
    )
