from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "hangboard-tools.sh"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HANGBOARD_PYTHON"] = sys.executable
    return subprocess.run(
        [str(SCRIPT_PATH), "catalog", *args],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )


def _json_output(output: str) -> dict[str, object]:
    return json.loads(output[output.find("{") :])


def test_catalog_cli_reports_two_state_registry_entries(tmp_path: Path) -> None:
    package = tmp_path / "draft-board"
    package.mkdir()
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "boards": [{"id": "draft.board", "path": "draft-board", "status": "draft"}],
            }
        ),
        encoding="utf-8",
    )

    result = _run_cli("status", "--catalog", str(catalog_path))

    assert result.returncode == 0, result.stderr
    assert _json_output(result.stdout) == {
        "boards": [{"id": "draft.board", "path": "draft-board", "status": "draft"}]
    }
