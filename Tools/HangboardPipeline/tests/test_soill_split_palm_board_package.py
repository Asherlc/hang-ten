from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "soill-split-palm"
EXPECTED_HOLDS = (
    ("incut-jug-left", "jug", 1),
    ("incut-jug-right", "jug", 1),
    ("large-sloper-left", "sloper", 1),
    ("large-sloper-right", "sloper", 1),
    ("small-sloper-left", "sloper", 1),
    ("small-sloper-right", "sloper", 1),
    ("center-sloping-edge-38-1-left", "edge", 1),
    ("center-sloping-edge-38-1-right", "edge", 1),
    ("center-flat-edge-25-4-left", "edge", 1),
    ("center-flat-edge-25-4-right", "edge", 1),
    ("outer-edge-12-7-left", "edge", 1),
    ("outer-edge-12-7-right", "edge", 1),
    ("bottom-center-sloping-edge-12-7-left", "edge", 1),
    ("bottom-center-sloping-edge-12-7-right", "edge", 1),
    ("lower-pinch-left", "pinch", 3),
    ("lower-pinch-right", "pinch", 3),
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_soill_split_palm_preserves_audited_inventory_and_mirror_geometry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert board.id == "soill.split-palm"
    assert board.manufacturer == "So iLL"
    assert board.name == "Split Palm"
    assert board.facts["dimensions"] == "Each piece: 16.5 × 11 × 3 7/8 in"
    assert math.isclose(board.facts["aspectRatio"], 3.0, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}

    assert tuple(
        (hold.id, hold.kind, len(hold.geometry)) for hold in board.holds
    ) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "edge": 8,
        "sloper": 4,
        "jug": 2,
        "pinch": 2,
    }

    for hold in board.holds:
        assert hold.size_millimeters is None
        assert hold.depth_range_millimeters is None
        assert hold.finger_capacity is None
        assert hold.features is None
        for piece in hold.geometry:
            assert piece.shape.type == "path"
            assert piece.shape.commands[0].command == "move"
            assert piece.shape.commands[-1].command == "close"
            assert any(command.command == "curve" for command in piece.shape.commands)
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
            assert piece.frame.width * piece.frame.height > 0

    assert holds["large-sloper-left"].grip_type == "sloper"
    assert holds["large-sloper-right"].grip_type == "sloper"
    assert holds["small-sloper-left"].grip_type == "sloper"
    assert holds["small-sloper-right"].grip_type == "sloper"
    assert all(
        hold.grip_type is None
        for hold in board.holds
        if hold.kind != "sloper"
    )
    assert holds["incut-jug-left"].geometry[0].treatment == {
        "type": "shelf",
        "rimInsetFraction": 0.12,
    }
    assert holds["incut-jug-right"].geometry[0].treatment == {
        "type": "shelf",
        "rimInsetFraction": 0.12,
    }

    for left_id, right_id in (
        ("incut-jug-left", "incut-jug-right"),
        ("large-sloper-left", "large-sloper-right"),
        ("small-sloper-left", "small-sloper-right"),
        ("center-sloping-edge-38-1-left", "center-sloping-edge-38-1-right"),
        ("center-flat-edge-25-4-left", "center-flat-edge-25-4-right"),
        ("outer-edge-12-7-left", "outer-edge-12-7-right"),
        (
            "bottom-center-sloping-edge-12-7-left",
            "bottom-center-sloping-edge-12-7-right",
        ),
        ("lower-pinch-left", "lower-pinch-right"),
    ):
        for left, right in zip(
            holds[left_id].geometry, holds[right_id].geometry, strict=True
        ):
            assert math.isclose(
                right.frame.x,
                1 - left.frame.x - left.frame.width,
                abs_tol=1e-12,
            )
            assert math.isclose(right.frame.y, left.frame.y, abs_tol=1e-12)
            assert math.isclose(right.frame.width, left.frame.width, abs_tol=1e-12)
            assert math.isclose(right.frame.height, left.frame.height, abs_tol=1e-12)
            for left_command, right_command in zip(
                left.shape.commands, right.shape.commands, strict=True
            ):
                assert left_command.command == right_command.command
                for (left_x, left_y), (right_x, right_y) in zip(
                    _points(left_command), _points(right_command), strict=True
                ):
                    assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                    assert math.isclose(right_y, left_y, abs_tol=1e-12)

    raw = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    forbidden = {"cueStyle", "semantics", "evidence", "claims", "ui"}

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(child) for child in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(child) for child in value))
        return set()

    assert forbidden.isdisjoint(keys(raw))
