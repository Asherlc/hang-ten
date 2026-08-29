from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


def test_port_a_board_has_one_object_and_declared_primary_asset() -> None:
    package_root = REPOSITORY_ROOT / "Hangboards" / "frictitious-port-a-board"
    package = board_package.load_board_package(package_root)
    board = package.board

    assert [item["id"] for item in board["equipmentObjects"]] == ["primary"]
    assert {hold["equipmentObjectID"] for hold in board["holds"]} == {"primary"}
    assert {hold["id"] for hold in board["holds"]} == {
        "edge-30",
        "edge-30-two-finger-mono",
        "edge-25",
        "edge-20",
        "edge-15",
        "edge-12",
        "edge-10",
        "edge-8",
    }
    assert (package_root / "assets" / "primary.png").is_file()
