from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path

import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "trango-rock-prodigy-forge"
EXPECTED_HOLDS = (
    ("pinch-variable-left", "pinch", 2),
    ("pinch-variable-right", "pinch", 2),
    ("sloper-30-left", "sloper", 1),
    ("sloper-30-right", "sloper", 1),
    ("sloper-40-left", "sloper", 1),
    ("sloper-40-right", "sloper", 1),
    ("edge-large-flat-left", "edge", 1),
    ("edge-large-flat-right", "edge", 1),
    ("edge-slopey-crimper-left", "edge", 1),
    ("edge-slopey-crimper-right", "edge", 1),
    ("edge-variable-7-20-left", "edge", 1),
    ("edge-variable-7-20-right", "edge", 1),
    ("pocket-mr-deep-25-left", "pocket", 1),
    ("pocket-mr-deep-25-right", "pocket", 1),
    ("pocket-mr-shallow-15-left", "pocket", 1),
    ("pocket-mr-shallow-15-right", "pocket", 1),
    ("edge-closed-crimp-left", "edge", 2),
    ("edge-closed-crimp-right", "edge", 2),
    ("pocket-imr-variable-19-31-left", "pocket", 1),
    ("pocket-imr-variable-19-31-right", "pocket", 1),
)
MIRRORED_PAIRS = tuple(
    (EXPECTED_HOLDS[index][0], EXPECTED_HOLDS[index + 1][0])
    for index in range(0, len(EXPECTED_HOLDS), 2)
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def _recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_recursive_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_recursive_keys(child) for child in value))
    return set()


def test_trango_rock_prodigy_forge_preserves_audited_physical_package() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert board.id == "trango.rock-prodigy-forge"
    assert board.manufacturer == "Trango"
    assert board.name == "Rock Prodigy Forge"
    assert board.facts["dimensions"] == "Each piece: 12.75 × 5.25 in"
    assert math.isclose(board.facts["aspectRatio"], 34 / 7, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"

    assert tuple(
        (hold.id, hold.kind, len(hold.geometry)) for hold in board.holds
    ) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "edge": 8,
        "pocket": 6,
        "sloper": 4,
        "pinch": 2,
    }
    assert sum(len(hold.geometry) for hold in board.holds) == 24

    for hold in board.holds:
        for piece in hold.geometry:
            assert piece.shape.type == "path"
            assert piece.shape.commands[0].command == "move"
            assert piece.shape.commands[-1].command == "close"
            assert sum(
                command.command == "curve" for command in piece.shape.commands
            ) >= 4
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
            assert piece.frame.width * piece.frame.height > 0

    for left_id, right_id in MIRRORED_PAIRS:
        left_pieces = holds[left_id].geometry
        right_pieces = holds[right_id].geometry
        assert len(left_pieces) == len(right_pieces)
        for left, right in zip(left_pieces, right_pieces, strict=True):
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

    for hold_id in ("pinch-variable-left", "pinch-variable-right"):
        assert holds[hold_id].features == (
            "widePinch",
            "mediumPinch",
            "smallPinch",
        )
    for hold_id in (
        "sloper-30-left",
        "sloper-30-right",
        "sloper-40-left",
        "sloper-40-right",
    ):
        assert holds[hold_id].grip_type == "sloper"
    for hold_id in ("edge-variable-7-20-left", "edge-variable-7-20-right"):
        depth_range = holds[hold_id].depth_range_millimeters
        assert depth_range is not None
        assert (depth_range.lower_bound, depth_range.upper_bound) == (7, 20)
    for hold_id in ("pocket-mr-deep-25-left", "pocket-mr-deep-25-right"):
        hold = holds[hold_id]
        assert (hold.size_millimeters, hold.finger_capacity, hold.grip_type) == (
            25,
            2,
            "twoFingerPocket",
        )
        assert hold.features == (
            "pocket",
            "twoFingerPocket",
            "deepTwoFingerPocket",
        )
    for hold_id in ("pocket-mr-shallow-15-left", "pocket-mr-shallow-15-right"):
        hold = holds[hold_id]
        assert (hold.size_millimeters, hold.finger_capacity, hold.grip_type) == (
            15,
            2,
            "twoFingerPocket",
        )
        assert hold.features == ("pocket", "twoFingerPocket")
    for hold_id in ("edge-closed-crimp-left", "edge-closed-crimp-right"):
        hold = holds[hold_id]
        assert hold.size_millimeters is None
        assert hold.grip_type == "fullCrimp"
        assert hold.features == ("thinCrimp",)
        assert tuple(piece.treatment["type"] for piece in hold.geometry) == (
            "recess",
            "surface",
        )
    for hold_id in (
        "pocket-imr-variable-19-31-left",
        "pocket-imr-variable-19-31-right",
    ):
        hold = holds[hold_id]
        depth_range = hold.depth_range_millimeters
        assert depth_range is not None
        assert (depth_range.lower_bound, depth_range.upper_bound) == (19, 31)
        assert (hold.finger_capacity, hold.grip_type) == (3, "threeFingerPocket")
        assert hold.features == ("pocket", "threeFingerPocket")

    sized_ids = {
        "pocket-mr-deep-25-left",
        "pocket-mr-deep-25-right",
        "pocket-mr-shallow-15-left",
        "pocket-mr-shallow-15-right",
    }
    ranged_ids = {
        "edge-variable-7-20-left",
        "edge-variable-7-20-right",
        "pocket-imr-variable-19-31-left",
        "pocket-imr-variable-19-31-right",
    }
    grip_ids = {
        "sloper-30-left",
        "sloper-30-right",
        "sloper-40-left",
        "sloper-40-right",
        *sized_ids,
        "edge-closed-crimp-left",
        "edge-closed-crimp-right",
        "pocket-imr-variable-19-31-left",
        "pocket-imr-variable-19-31-right",
    }
    capacity_ids = sized_ids | {
        "pocket-imr-variable-19-31-left",
        "pocket-imr-variable-19-31-right",
    }
    feature_ids = capacity_ids | {
        "pinch-variable-left",
        "pinch-variable-right",
        "edge-closed-crimp-left",
        "edge-closed-crimp-right",
    }
    assert all(
        hold.size_millimeters is None
        for hold in board.holds
        if hold.id not in sized_ids
    )
    assert all(
        hold.depth_range_millimeters is None
        for hold in board.holds
        if hold.id not in ranged_ids
    )
    assert all(
        hold.grip_type is None for hold in board.holds if hold.id not in grip_ids
    )
    assert all(
        hold.finger_capacity is None
        for hold in board.holds
        if hold.id not in capacity_ids
    )
    assert all(
        hold.features is None for hold in board.holds if hold.id not in feature_ids
    )

    raw = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    forbidden = {
        "cueStyle",
        "claims",
        "semantics",
        "evidence",
        "artwork",
        "catalog",
        "ui",
        "instructions",
    }
    assert forbidden.isdisjoint(_recursive_keys(raw))


def test_forge_40_degree_slopers_stay_above_lower_board_silhouette() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    for hold_id in ("sloper-40-left", "sloper-40-right"):
        piece = holds[hold_id].geometry[0]
        for command in piece.shape.commands:
            for local_x, local_y in _points(command):
                global_x = piece.frame.x + local_x * piece.frame.width
                global_y = piece.frame.y + local_y * piece.frame.height
                left_x = global_x if hold_id.endswith("-left") else 1 - global_x
                if 0.079 <= left_x <= 0.201:
                    # Hand-audited against the diagonal lower silhouette in
                    # assets/primary.png: from about (0.08, 0.658) at the
                    # outside corner to (0.20, 0.610) at the inside corner.
                    assert global_y <= 0.69 - 0.4 * left_x + 1e-12
