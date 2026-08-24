from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
MIRRORED_PAIRS = {
    "escape-unlimited": (
        ("edge-45-left", "edge-45-right"),
        ("edge-20-left", "edge-20-right"),
        ("edge-15-left", "edge-15-right"),
    ),
    "frictitious-doormount-pro-7": (
        ("edge-35-left", "edge-35-right"),
        ("mixed-25-pocket-left", "mixed-25-pocket-right"),
        ("hold-7", "hold-6"),
        ("hold-11", "hold-8"),
        ("hold-10", "hold-9"),
        ("hold-12", "hold-13"),
    ),
    "metolius-project": (
        ("jug-1-left", "jug-1-right"),
        ("pocket-3-left", "pocket-3-right"),
        ("edge-4-left", "edge-4-right"),
        ("pocket-5-left", "pocket-5-right"),
        ("pocket-6-left", "pocket-6-right"),
        ("pocket-7-left", "pocket-7-right"),
    ),
    "metolius-simulator-3d": (
        ("jug-1-left", "jug-1-right"),
        ("round-sloper-3-left", "round-sloper-3-right"),
        ("pocket-4-left", "pocket-4-right"),
        ("edge-5-left", "edge-5-right"),
        ("edge-6-left", "edge-6-right"),
        ("edge-7-left", "edge-7-right"),
        ("pocket-8-left", "pocket-8-right"),
        ("pocket-9-left", "pocket-9-right"),
        ("pocket-10-left", "pocket-10-right"),
        ("edge-11-left", "edge-11-right"),
        ("pocket-12-left", "pocket-12-right"),
        ("pocket-13-left", "pocket-13-right"),
    ),
    "beastmaker-2000": (
        ("front-middle-2", "front-middle-8"),
        ("hold-26", "hold-27"),
    ),
    "escape-beta-22": tuple(
        (f"hold-{family:02d}-left", f"hold-{family:02d}-right")
        for family in range(1, 9)
    ),
}


def _mirrored_point(point: list[float]) -> tuple[float, float]:
    return (1 - point[0], point[1])


def _assert_mirrored_piece(left: dict[str, object], right: dict[str, object]) -> None:
    left_frame = left["frame"]
    right_frame = right["frame"]
    assert isinstance(left_frame, dict)
    assert isinstance(right_frame, dict)
    assert right_frame["x"] == pytest.approx(1 - left_frame["x"] - left_frame["width"])
    assert right_frame["y"] == pytest.approx(left_frame["y"])
    assert right_frame["width"] == pytest.approx(left_frame["width"])
    assert right_frame["height"] == pytest.approx(left_frame["height"])

    left_constraint = left.get("shapeConstraint")
    right_constraint = right.get("shapeConstraint")
    assert right_constraint == left_constraint or (
        isinstance(left_constraint, dict)
        and isinstance(right_constraint, dict)
        and right_constraint["shape"] == left_constraint["shape"]
        and right_constraint["rotationDegrees"] == pytest.approx(-left_constraint["rotationDegrees"])
    )

    left_commands = left["shape"]["commands"]
    right_commands = right["shape"]["commands"]
    assert len(right_commands) == len(left_commands)
    for left_command, right_command in zip(left_commands, right_commands, strict=True):
        assert right_command["command"] == left_command["command"]
        for field in ("to", "control", "control1", "control2"):
            if field in left_command:
                assert tuple(right_command[field]) == pytest.approx(_mirrored_point(left_command[field]))
            else:
                assert field not in right_command


@pytest.mark.parametrize("board_id", MIRRORED_PAIRS)
def test_coderabbit_flagged_pairs_are_exact_mirrors(board_id: str) -> None:
    board = json.loads((REPO_ROOT / "Hangboards" / board_id / "board.json").read_text())
    holds = {hold["id"]: hold for hold in board["holds"]}
    for left_id, right_id in MIRRORED_PAIRS[board_id]:
        left_geometry = holds[left_id]["geometry"]
        right_geometry = holds[right_id]["geometry"]
        assert len(right_geometry) == len(left_geometry)
        for left_piece, right_piece in zip(left_geometry, right_geometry, strict=True):
            _assert_mirrored_piece(left_piece, right_piece)
