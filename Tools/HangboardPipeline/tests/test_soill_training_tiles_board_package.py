from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import struct

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "soill-training-tiles"
EXPECTED_HOLDS = (
    ("jug-left", "jug"),
    ("jug-right", "jug"),
    ("top-sloper-outer-left", "sloper"),
    ("top-sloper-outer-right", "sloper"),
    ("top-sloper-inner-left", "sloper"),
    ("top-sloper-inner-right", "sloper"),
    ("middle-positive-edge-outer-left", "edge"),
    ("middle-positive-edge-outer-right", "edge"),
    ("middle-positive-edge-inner-left", "edge"),
    ("middle-positive-edge-inner-right", "edge"),
    ("bottom-flat-edge-outer-left", "edge"),
    ("bottom-flat-edge-outer-right", "edge"),
    ("bottom-flat-edge-middle-left", "edge"),
    ("bottom-flat-edge-middle-right", "edge"),
    ("bottom-flat-edge-inner-left", "edge"),
    ("bottom-flat-edge-inner-right", "edge"),
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("top-sloper-outer-left", "top-sloper-outer-right"),
    ("top-sloper-inner-left", "top-sloper-inner-right"),
    ("middle-positive-edge-outer-left", "middle-positive-edge-outer-right"),
    ("middle-positive-edge-inner-left", "middle-positive-edge-inner-right"),
    ("bottom-flat-edge-outer-left", "bottom-flat-edge-outer-right"),
    ("bottom-flat-edge-middle-left", "bottom-flat-edge-middle-right"),
    ("bottom-flat-edge-inner-left", "bottom-flat-edge-inner-right"),
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_soill_training_tiles_preserve_sixteen_discrete_mirrored_contacts() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert board.id == "soill.training-tiles"
    assert board.manufacturer == "So iLL"
    assert board.name == "Training Tiles • So iLL x Meagan Martin"
    assert board.facts["dimensions"] == "Not published by manufacturer"
    primary = PACKAGE_ROOT / "assets" / "primary.png"
    png = primary.read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert png[12:16] == b"IHDR"
    width, height = struct.unpack(">II", png[16:24])
    assert math.isclose(
        board.facts["aspectRatio"], width / height, abs_tol=1e-12
    )
    assert board.presentation_asset_path == "assets/primary.png"
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }

    assert tuple((hold.id, hold.kind) for hold in board.holds) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "edge": 10,
        "sloper": 4,
        "jug": 2,
    }

    for hold in board.holds:
        assert len(hold.geometry) == 1
        assert hold.size_millimeters is None
        assert hold.depth_range_millimeters is None
        assert hold.finger_capacity is None
        assert hold.features is None
        assert hold.grip_type == ("sloper" if hold.kind == "sloper" else None)
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert sum(command.command == "curve" for command in piece.shape.commands) >= 5
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0

    assert holds["jug-left"].geometry[0].treatment == {
        "type": "recess",
        "rimInsetFraction": 0.1,
        "depth": "deep",
    }
    assert holds["jug-right"].geometry[0].treatment == {
        "type": "recess",
        "rimInsetFraction": 0.1,
        "depth": "deep",
    }
    assert all(
        holds[hold_id].geometry[0].treatment
        == {"type": "shelf", "rimInsetFraction": 0.1}
        for hold_id in (
            "middle-positive-edge-outer-left",
            "middle-positive-edge-outer-right",
            "middle-positive-edge-inner-left",
            "middle-positive-edge-inner-right",
        )
    )

    left_jug_frame = holds["jug-left"].geometry[0].frame
    assert 0.10 <= left_jug_frame.x <= 0.16
    assert 0.30 <= left_jug_frame.y <= 0.36
    assert left_jug_frame.width < 0.07
    assert left_jug_frame.height < 0.10
    assert left_jug_frame.x <= 0.132 <= left_jug_frame.x + left_jug_frame.width
    assert left_jug_frame.y <= 0.355 <= left_jug_frame.y + left_jug_frame.height
    assert all(
        holds[hold_id].geometry[0].treatment == {"type": "surface"}
        for hold_id in (
            "bottom-flat-edge-outer-left",
            "bottom-flat-edge-outer-right",
            "bottom-flat-edge-middle-left",
            "bottom-flat-edge-middle-right",
            "bottom-flat-edge-inner-left",
            "bottom-flat-edge-inner-right",
        )
    )

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id].geometry[0]
        right = holds[right_id].geometry[0]
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
