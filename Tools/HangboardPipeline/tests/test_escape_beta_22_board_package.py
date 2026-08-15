from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "escape-beta-22"
EXPECTED_HOLDS = (
    ("hold-01-left", "Left Thin Pinch", "pinch", None),
    ("hold-01-right", "Right Thin Pinch", "pinch", None),
    ("hold-02-left", "Left Wide Pinch", "pinch", None),
    ("hold-02-right", "Right Wide Pinch", "pinch", None),
    ("hold-03-left", "Left 38mm Mini-Jug", "jug", 38),
    ("hold-03-right", "Right 38mm Mini-Jug", "jug", 38),
    ("hold-04-left", "Left 29mm Incut Jug", "jug", 29),
    ("hold-04-right", "Right 29mm Incut Jug", "jug", 29),
    ("hold-05-left", "Left 12mm Incut Edge", "edge", 12),
    ("hold-05-right", "Right 12mm Incut Edge", "edge", 12),
    ("hold-06-left", "Left 38mm Flat Edge", "edge", 38),
    ("hold-06-right", "Right 38mm Flat Edge", "edge", 38),
    ("hold-07-left", "Left 29mm Flat Edge", "edge", 29),
    ("hold-07-right", "Right 29mm Flat Edge", "edge", 29),
    ("hold-08-left", "Left 12mm Flat Edge", "edge", 12),
    ("hold-08-right", "Right 12mm Flat Edge", "edge", 12),
    ("hold-09-left", "Left 50mm Sloper Edge", "sloper", 50),
    ("hold-09-right", "Right 50mm Sloper Edge", "sloper", 50),
    ("hold-10-left", "Left 31mm Sloper Edge", "sloper", 31),
    ("hold-10-right", "Right 31mm Sloper Edge", "sloper", 31),
    ("hold-11-left", "Left 12mm Sloper Edge", "sloper", 12),
    ("hold-11-right", "Right 12mm Sloper Edge", "sloper", 12),
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_escape_beta_22_audited_package_contract() -> None:
    raw_board = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert {item.name for item in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {item.name for item in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    with Image.open(PACKAGE_ROOT / "assets" / "primary.png") as primary_image:
        assert primary_image.size == (1536, 1024)
        primary_image_aspect_ratio = primary_image.width / primary_image.height

    assert board.id == "escape-beta-22"
    assert board.manufacturer == "Escape Climbing"
    assert board.name == "Beta Board"
    assert board.facts["dimensions"] == "26 × 6 × 2 in"
    assert board.facts["aspectRatio"] == pytest.approx(
        primary_image_aspect_ratio, rel=0, abs=1e-12
    )
    assert board.presentation_asset_path == "assets/primary.png"
    assert raw_board["productURL"] == "https://escapeclimbing.com/products/ec72100"
    assert tuple(
        (hold.id, hold.name, hold.kind, hold.size_millimeters) for hold in board.holds
    ) == EXPECTED_HOLDS

    for raw_hold, hold in zip(raw_board["holds"], board.holds, strict=True):
        assert "depthRangeMillimeters" not in raw_hold
        assert "gripType" not in raw_hold
        assert "fingerCapacity" not in raw_hold
        assert "features" not in raw_hold
        assert hold.depth_range_millimeters is None
        assert hold.grip_type is None
        assert hold.finger_capacity is None
        assert hold.features is None

        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.treatment is None
        assert piece.shape.type == "path"
        commands = piece.shape.commands
        assert commands[0].command == "move"
        assert commands[-1].command == "close"
        assert 0 <= piece.frame.x <= 1
        assert 0 <= piece.frame.y <= 1
        assert 0 <= piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y + piece.frame.height <= 1
        for point in (point for command in commands for point in _points(command)):
            assert 0 <= point[0] <= 1
            assert 0 <= point[1] <= 1

        family = int(hold.id.split("-")[1])
        if family <= 8:
            assert [command.command for command in commands] == [
                "move",
                "curve",
                "curve",
                "curve",
                "curve",
                "close",
            ]
        else:
            assert [command.command for command in commands] == [
                "move",
                "curve",
                "line",
                "curve",
                "curve",
                "close",
            ]

    for family in range(1, 12):
        left = holds[f"hold-{family:02d}-left"].geometry[0]
        right = holds[f"hold-{family:02d}-right"].geometry[0]
        assert right.frame.x == pytest.approx(1 - left.frame.x - left.frame.width, abs=1e-12)
        assert right.frame.y == pytest.approx(left.frame.y, abs=1e-12)
        assert right.frame.width == pytest.approx(left.frame.width, abs=1e-12)
        assert right.frame.height == pytest.approx(left.frame.height, abs=1e-12)
        for left_command, right_command in zip(
            left.shape.commands, right.shape.commands, strict=True
        ):
            assert right_command.command == left_command.command
            left_points = _points(left_command)
            right_points = _points(right_command)
            assert len(right_points) == len(left_points)
            for (left_x, left_y), (right_x, right_y) in zip(
                left_points, right_points, strict=True
            ):
                assert right_x == pytest.approx(1 - left_x, abs=1e-12)
                assert right_y == pytest.approx(left_y, abs=1e-12)
