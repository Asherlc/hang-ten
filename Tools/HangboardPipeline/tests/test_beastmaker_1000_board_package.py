from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "beastmaker-1000"
WORKBENCH_ROOT = REPOSITORY_ROOT / "Tools" / "HangboardWorkbench"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


EXPECTED_HOLDS = (
    ("jug-left", "jug"),
    ("jug-right", "jug"),
    ("sloper-35-left", "sloper"),
    ("sloper-35-right", "sloper"),
    ("sloper-center", "sloper"),
    ("pocket-top-outer-left", "pocket"),
    ("pocket-top-outer-right", "pocket"),
    ("pocket-top-left", "pocket"),
    ("pocket-top-right", "pocket"),
    ("pocket-middle-outer-left", "pocket"),
    ("pocket-middle-mid-left", "pocket"),
    ("pocket-middle-inner-left", "pocket"),
    ("pocket-middle-center", "pocket"),
    ("pocket-middle-inner-right", "pocket"),
    ("pocket-middle-mid-right", "pocket"),
    ("pocket-middle-outer-right", "pocket"),
    ("pocket-bottom-outer-left", "pocket"),
    ("pocket-bottom-mid-left", "pocket"),
    ("pocket-bottom-inner-left", "pocket"),
    ("pocket-bottom-inner-right", "pocket"),
    ("pocket-bottom-mid-right", "pocket"),
    ("pocket-bottom-outer-right", "pocket"),
)


def test_beastmaker_1000_is_a_valid_current_foundation_package() -> None:
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }

    package = board_package.load_board_package(PACKAGE_ROOT)

    assert package.board_id == "beastmaker-1000"
    assert [(hold["id"], hold["kind"]) for hold in package.board["holds"]] == list(
        EXPECTED_HOLDS
    )
    assert all(hold["geometry"] for hold in package.board["holds"])


def test_beastmaker_1000_declares_its_primary_canvas_ratio() -> None:
    package = board_package.load_board_package(PACKAGE_ROOT)
    png_header = (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()[:24]

    assert png_header[:8] == b"\x89PNG\r\n\x1a\n"
    assert png_header[12:16] == b"IHDR"
    width, height = struct.unpack(">II", png_header[16:24])
    assert (width, height) == (1000, 259)
    assert package.board["aspectRatio"] == pytest.approx(width / height)
