from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from conftest import write_board_package, write_primary_only_draft

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "hangboard-tools.sh"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HANGBOARD_PYTHON"] = sys.executable
    return subprocess.run(
        [str(SCRIPT_PATH), "packages", *args],
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


def test_operations_emit_partial_report_and_fail_after_middle_package_error(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from hangboard_vectorizer import board_catalog_cli

    packages = tuple(
        SimpleNamespace(root=tmp_path / name, board=SimpleNamespace(id=f"fixture.{name}"))
        for name in ("first", "middle", "last")
    )
    inventory = SimpleNamespace(packages=packages, drafts=())
    monkeypatch.setattr(board_catalog_cli, "discover_board_packages", lambda root: inventory)

    def fake_simplify(root: Path, *, write: bool):
        if root.name == "middle":
            raise OSError("simulated write failure")
        return SimpleNamespace(
            board_id=f"fixture.{root.name}", changed=False, pieces=()
        )

    monkeypatch.setattr(board_catalog_cli, "simplify_package_hold_paths", fake_simplify)
    assert board_catalog_cli.main(
        ["simplify-hold-paths", "--root", str(tmp_path), "--write"]
    ) == 1
    payload = json.loads(capsys.readouterr().out)
    assert [board["path"] for board in payload["boards"]] == ["first", "middle", "last"]
    assert payload["boards"][1]["error"] == "simulated write failure"
    assert payload["boards"][2]["id"] == "fixture.last"


def test_normalize_operation_continues_after_package_error(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from hangboard_vectorizer import board_catalog_cli

    packages = tuple(
        SimpleNamespace(root=tmp_path / name, board=SimpleNamespace(id=f"fixture.{name}"))
        for name in ("first", "middle", "last")
    )
    monkeypatch.setattr(
        board_catalog_cli,
        "discover_board_packages",
        lambda root: SimpleNamespace(packages=packages, drafts=()),
    )

    def fake_normalize(root: Path, *, write: bool):
        if root.name == "middle":
            raise ValueError("simulated normalization failure")
        return SimpleNamespace(
            board_id=f"fixture.{root.name}",
            original_width=100,
            original_height=50,
            width=90,
            height=45,
            crop=(1, 2, 3, 4),
            hold_count=1,
            changed=True,
        )

    monkeypatch.setattr(board_catalog_cli, "normalize_package_presentation", fake_normalize)
    assert board_catalog_cli.main(
        ["normalize-presentations", "--root", str(tmp_path)]
    ) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["boards"][0]["changed"] is True
    assert payload["boards"][1]["error"] == "simulated normalization failure"
    assert payload["boards"][2]["path"] == "last"
