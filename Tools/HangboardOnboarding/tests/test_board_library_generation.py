from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
EXPORT_SCRIPT_PATH = REPO_ROOT / "scripts" / "export-board-library.py"
CATALOG_PATH = REPO_ROOT / "Hangboards" / "catalog.json"
GENERATED_LIBRARY_PATH = REPO_ROOT / "HangTen" / "Resources" / "BoardLibrary.json"


def run_export(output_path: Path, *, check: bool = False) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(EXPORT_SCRIPT_PATH),
        "--catalog",
        str(CATALOG_PATH),
        "--output",
        str(output_path),
    ]
    if check:
        command.append("--check")
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_exported_board_library_uses_canonical_grips_finger_capacity_and_features(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "BoardLibrary.json"
    shutil.copy2(GENERATED_LIBRARY_PATH, output_path)

    result = run_export(output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    holds = {
        hold["id"]: hold
        for board in payload["boards"]
        for hold in board["holds"]
    }
    assert holds["pocket-29-two-left"]["gripType"] == "twoFingerPocket"
    assert holds["pocket-29-two-left"]["fingerCapacity"] == 2
    assert holds["pocket-29-two-left"]["features"] == ["pocket", "twoFingerPocket"]


def test_export_board_library_check_passes_for_regenerated_resource() -> None:
    checked = run_export(GENERATED_LIBRARY_PATH, check=True)

    assert checked.returncode == 0, checked.stderr


def test_export_board_library_check_detects_resource_drift(tmp_path: Path) -> None:
    output_path = tmp_path / "BoardLibrary.json"
    shutil.copy2(GENERATED_LIBRARY_PATH, output_path)
    generated = run_export(output_path)
    assert generated.returncode == 0, generated.stderr
    output_path.write_text(output_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    checked = run_export(output_path, check=True)

    assert checked.returncode == 1
    assert "drift detected" in checked.stderr
