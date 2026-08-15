from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "metolius-project"
EXPECTED_HOLDS = (
    ("jug-left", "jug", None, None),
    ("jug-right", "jug", None, None),
    ("sloper-flat-left", "sloper", None, None),
    ("sloper-flat-right", "sloper", None, None),
    ("pocket-45-three-left", "pocket", 45, 3),
    ("pocket-45-three-right", "pocket", 45, 3),
    ("edge-30-left", "edge", 30, None),
    ("edge-30-right", "edge", 30, None),
    ("pocket-40-two-left", "pocket", 40, 2),
    ("pocket-40-two-right", "pocket", 40, 2),
    ("pocket-22-three-left", "pocket", 22, 3),
    ("pocket-22-three-right", "pocket", 22, 3),
    ("pocket-22-two-left", "pocket", 22, 2),
    ("pocket-22-two-right", "pocket", 22, 2),
    ("sloper-round-center", "sloper", None, None),
    ("edge-39-center", "edge", 39, None),
    ("edge-16-center", "edge", 16, None),
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("sloper-flat-left", "sloper-flat-right"),
    ("pocket-45-three-left", "pocket-45-three-right"),
    ("edge-30-left", "edge-30-right"),
    ("pocket-40-two-left", "pocket-40-two-right"),
    ("pocket-22-three-left", "pocket-22-three-right"),
    ("pocket-22-two-left", "pocket-22-two-right"),
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_metolius_project_preserves_audited_inventory_and_mirrored_contacts() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board.id == "metolius.project"
    assert board.manufacturer == "Metolius"
    assert board.name == "Project Training Board"
    assert board.facts["dimensions"] == "622 × 152 mm"
    assert board.facts["aspectRatio"] == 4.08
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters, hold.finger_capacity)
        for hold in board.holds
    ) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "pocket": 8,
        "edge": 4,
        "sloper": 3,
        "jug": 2,
    }

    for hold in board.holds:
        for piece in hold.geometry:
            assert piece.shape.type == "path"
            assert piece.shape.commands[0].command == "move"
            assert piece.shape.commands[-1].command == "close"
            assert any(command.command == "curve" for command in piece.shape.commands)
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
            assert piece.frame.width * piece.frame.height > 0

    for left_id, right_id in MIRRORED_PAIRS:
        left_pieces = holds[left_id].geometry
        right_pieces = holds[right_id].geometry
        assert len(left_pieces) == len(right_pieces)
        for left, right in zip(left_pieces, right_pieces, strict=True):
            assert math.isclose(
                right.frame.x,
                1 - left.frame.x - left.frame.width,
                abs_tol=1e-12,
            )
            assert right.frame.y == left.frame.y
            assert right.frame.width == left.frame.width
            assert right.frame.height == left.frame.height
            assert right.treatment == left.treatment
            for left_command, right_command in zip(
                left.shape.commands, right.shape.commands, strict=True
            ):
                assert left_command.command == right_command.command
                for (left_x, left_y), (right_x, right_y) in zip(
                    _points(left_command), _points(right_command), strict=True
                ):
                    assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                    assert math.isclose(right_y, left_y, abs_tol=1e-12)

    assert len(holds["jug-left"].geometry) == 4
    assert len(holds["jug-right"].geometry) == 4
    assert all(len(holds[hold_id].geometry) == 1 for hold_id in (
        "sloper-flat-left", "sloper-flat-right", "sloper-round-center",
        "pocket-45-three-left", "pocket-45-three-right",
        "edge-30-left", "edge-30-right",
        "pocket-40-two-left", "pocket-40-two-right",
        "pocket-22-three-left", "pocket-22-three-right",
        "pocket-22-two-left", "pocket-22-two-right",
        "edge-39-center", "edge-16-center",
    ))

    top_ids = (
        "jug-left", "sloper-flat-left", "sloper-round-center",
        "sloper-flat-right", "jug-right",
    )
    for left_id, right_id in zip(top_ids, top_ids[1:]):
        assert math.isclose(
            holds[left_id].frame.x + holds[left_id].frame.width,
            holds[right_id].frame.x,
            abs_tol=1e-12,
        )

    assert holds["jug-left"].features == ("jug",)
    assert holds["jug-right"].features == ("jug",)
    assert holds["sloper-round-center"].features == ("roundSloper",)
    assert all(holds[hold_id].grip_type == "sloper" for hold_id in (
        "sloper-flat-left", "sloper-flat-right", "sloper-round-center",
    ))
    assert all(hold.depth_range_millimeters is None for hold in board.holds)

    raw_document = json.loads((PACKAGE_ROOT / "board.json").read_text())
    forbidden_keys = {"cueStyle", "semantics", "evidence", "claims", "ui"}

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert forbidden_keys.isdisjoint(keys(raw_document))
