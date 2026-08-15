from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path

import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "tension-honestone"
EXPECTED_HOLDS = (
    ("sloper-35-left", "sloper", None),
    ("sloper-35-right", "sloper", None),
    ("sloper-45-left", "sloper", None),
    ("sloper-45-right", "sloper", None),
    ("pocket-25-one-left", "pocket", 25),
    ("pocket-25-one-right", "pocket", 25),
    ("edge-20-left", "edge", 20),
    ("edge-20-right", "edge", 20),
    ("edge-15-left", "edge", 15),
    ("edge-15-right", "edge", 15),
    ("center-edge-25", "edge", 25),
    ("edge-10-left", "edge", 10),
    ("edge-10-right", "edge", 10),
    ("edge-8-left", "edge", 8),
    ("edge-8-right", "edge", 8),
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def _assert_exact_global_mirror(left: object, right: object) -> None:
    assert right.frame.x == pytest.approx(
        1 - left.frame.x - left.frame.width, abs=1e-12
    )
    assert right.frame.y == pytest.approx(left.frame.y, abs=1e-12)
    assert right.frame.width == pytest.approx(left.frame.width, abs=1e-12)
    assert right.frame.height == pytest.approx(left.frame.height, abs=1e-12)
    assert right.treatment == left.treatment
    assert [command.command for command in right.shape.commands] == [
        command.command for command in left.shape.commands
    ]
    for left_command, right_command in zip(
        left.shape.commands, right.shape.commands, strict=True
    ):
        for (left_x, left_y), (right_x, right_y) in zip(
            _points(left_command), _points(right_command), strict=True
        ):
            assert right_x == pytest.approx(1 - left_x, abs=1e-12)
            assert right_y == pytest.approx(left_y, abs=1e-12)


def test_tension_honestone_preserves_audited_contacts_and_asymmetric_zones() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert board.id == "tension.honestone"
    assert board.manufacturer == "Tension Climbing"
    assert board.name == "Honestone"
    assert board.facts["dimensions"] == "25 × 6 × 2.5 in"
    assert math.isclose(board.facts["aspectRatio"], 25 / 6, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters) for hold in board.holds
    ) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "sloper": 4,
        "pocket": 2,
        "edge": 9,
    }

    for hold in board.holds:
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert any(command.command == "curve" for command in piece.shape.commands)
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0

    # The routed cavities are mirrored, while labels move between inner and
    # outer zones to preserve the manufacturer's consistent grip spacing.
    for left_id, right_id in (
        ("pocket-25-one-left", "pocket-25-one-right"),
        ("edge-20-left", "edge-15-right"),
        ("edge-15-left", "edge-20-right"),
        ("edge-10-left", "edge-8-right"),
        ("edge-8-left", "edge-10-right"),
    ):
        _assert_exact_global_mirror(
            holds[left_id].geometry[0], holds[right_id].geometry[0]
        )

    # Adjacent depth regions meet at the source-visible shallow step and never
    # swallow the neighbouring region in the same routed slot.
    for outer_id, inner_id in (
        ("edge-20-left", "edge-15-left"),
        ("edge-20-right", "edge-15-right"),
        ("edge-10-left", "edge-8-left"),
        ("edge-10-right", "edge-8-right"),
    ):
        outer = holds[outer_id].geometry[0].frame
        inner = holds[inner_id].geometry[0].frame
        left, right = sorted((outer, inner), key=lambda frame: frame.x)
        assert left.x + left.width == pytest.approx(right.x, abs=1e-12)
        assert left.y == pytest.approx(right.y, abs=1e-12)
        assert left.height == pytest.approx(right.height, abs=1e-12)

    # The sloper IDs follow the engraved asymmetric 35°/45° sequence:
    # low outer, raised inner, low inner, raised outer.
    assert holds["sloper-35-left"].frame.x < holds["sloper-45-left"].frame.x < 0.5
    assert 0.5 < holds["sloper-35-right"].frame.x < holds["sloper-45-right"].frame.x
    assert holds["sloper-45-left"].frame.y < holds["sloper-35-left"].frame.y
    assert holds["sloper-45-right"].frame.y < holds["sloper-35-right"].frame.y
    assert all(
        holds[hold_id].grip_type == "sloper"
        for hold_id in (
            "sloper-35-left",
            "sloper-35-right",
            "sloper-45-left",
            "sloper-45-right",
        )
    )
    assert holds["pocket-25-one-left"].finger_capacity == 1
    assert holds["pocket-25-one-right"].finger_capacity == 1
    assert holds["pocket-25-one-left"].grip_type is None
    assert holds["pocket-25-one-right"].grip_type is None
    assert all(hold.depth_range_millimeters is None for hold in board.holds)
    assert all(hold.features is None for hold in board.holds)

    raw_document = json.loads((PACKAGE_ROOT / "board.json").read_text())
    forbidden_keys = {"cueStyle", "semantics", "evidence", "claims", "ui"}

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert forbidden_keys.isdisjoint(keys(raw_document))
