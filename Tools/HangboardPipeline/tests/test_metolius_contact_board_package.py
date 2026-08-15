from __future__ import annotations

from collections import Counter
import math
from pathlib import Path

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "metolius-contact"
EXPECTED_HOLDS = (
    "pinch-left",
    "pinch-right",
    "jug-left",
    "jug-right",
    "sloper-round-left",
    "sloper-round-right",
    "pocket-30-four-left",
    "pocket-30-four-right",
    "pocket-40-two-left",
    "pocket-40-two-right",
    "pocket-20-three-left",
    "pocket-20-three-right",
    "pocket-30-three-left",
    "pocket-30-three-right",
    "pocket-32-two-left",
    "pocket-32-two-right",
    "pocket-20-four-left",
    "pocket-20-four-right",
    "pocket-25-three-left",
    "pocket-25-three-right",
    "pocket-25-two-left",
    "pocket-25-two-right",
    "pocket-12-four-left",
    "pocket-12-four-right",
    "pocket-17-three-left",
    "pocket-17-three-right",
    "pocket-17-two-left",
    "pocket-17-two-right",
    "sloper-flat-center",
    "edge-15-center",
    "edge-35-center",
    "edge-28-center",
    "edge-23-center",
)
MIRRORED_PAIRS = (
    ("pinch-left", "pinch-right"),
    ("jug-left", "jug-right"),
    ("sloper-round-left", "sloper-round-right"),
    ("pocket-30-four-left", "pocket-30-four-right"),
    ("pocket-40-two-left", "pocket-40-two-right"),
    ("pocket-20-three-left", "pocket-20-three-right"),
    ("pocket-30-three-left", "pocket-30-three-right"),
    ("pocket-32-two-left", "pocket-32-two-right"),
    ("pocket-20-four-left", "pocket-20-four-right"),
    ("pocket-25-three-left", "pocket-25-three-right"),
    ("pocket-25-two-left", "pocket-25-two-right"),
    ("pocket-12-four-left", "pocket-12-four-right"),
    ("pocket-17-three-left", "pocket-17-three-right"),
    ("pocket-17-two-left", "pocket-17-two-right"),
)
POCKET_FACTS = {
    "pocket-30-four": (30, 4, "fourFingerPocket"),
    "pocket-40-two": (40, 2, "twoFingerPocket"),
    "pocket-20-three": (20, 3, "threeFingerPocket"),
    "pocket-30-three": (30, 3, "threeFingerPocket"),
    "pocket-32-two": (32, 2, "twoFingerPocket"),
    "pocket-20-four": (20, 4, "fourFingerPocket"),
    "pocket-25-three": (25, 3, "threeFingerPocket"),
    "pocket-25-two": (25, 2, "twoFingerPocket"),
    "pocket-12-four": (12, 4, "fourFingerPocket"),
    "pocket-17-three": (17, 3, "threeFingerPocket"),
    "pocket-17-two": (17, 2, "twoFingerPocket"),
}


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_metolius_contact_preserves_all_physical_contacts_and_mirrors() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board.id == "metolius.contact"
    assert board.manufacturer == "Metolius"
    assert board.name == "Contact Training Board"
    assert board.facts["dimensions"] == "32.5 × 11 × 2.625 in (826 × 279 × 67 mm)"
    assert math.isclose(board.facts["aspectRatio"], 32.5 / 11, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(holds) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in holds.values()) == {
        "pocket": 22,
        "edge": 4,
        "sloper": 3,
        "pinch": 2,
        "jug": 2,
    }

    for hold in holds.values():
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert any(command.command == "curve" for command in piece.shape.commands)
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id].geometry[0]
        right = holds[right_id].geometry[0]
        assert math.isclose(right.frame.x, 1 - left.frame.x - left.frame.width, abs_tol=1e-12)
        assert right.frame.y == left.frame.y
        assert right.frame.width == left.frame.width
        assert right.frame.height == left.frame.height
        for left_command, right_command in zip(
            left.shape.commands, right.shape.commands, strict=True
        ):
            assert left_command.command == right_command.command
            for (left_x, left_y), (right_x, right_y) in zip(
                _points(left_command), _points(right_command), strict=True
            ):
                assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                assert math.isclose(right_y, left_y, abs_tol=1e-12)

    for stem, (size, capacity, grip_type) in POCKET_FACTS.items():
        for side in ("left", "right"):
            hold = holds[f"{stem}-{side}"]
            assert hold.size_millimeters == size
            assert hold.finger_capacity == capacity
            assert hold.grip_type == grip_type
            assert hold.features == ("pocket", grip_type)

    assert holds["jug-left"].features == ("jug",)
    assert holds["jug-right"].features == ("jug",)
    assert holds["sloper-round-left"].grip_type == "sloper"
    assert holds["sloper-round-left"].features == ("roundSloper",)
    assert holds["sloper-round-right"].grip_type == "sloper"
    assert holds["sloper-round-right"].features == ("roundSloper",)
    assert holds["sloper-flat-center"].grip_type == "sloper"
    assert holds["sloper-flat-center"].size_millimeters is None
    assert {
        hold_id: holds[hold_id].size_millimeters
        for hold_id in (
            "edge-15-center",
            "edge-35-center",
            "edge-28-center",
            "edge-23-center",
        )
    } == {
        "edge-15-center": 15,
        "edge-35-center": 35,
        "edge-28-center": 28,
        "edge-23-center": 23,
    }
    assert all(hold.depth_range_millimeters is None for hold in holds.values())
    assert all(
        holds[hold_id].grip_type is None
        for hold_id in (
            "pinch-left",
            "pinch-right",
            "jug-left",
            "jug-right",
            "edge-15-center",
            "edge-35-center",
            "edge-28-center",
            "edge-23-center",
        )
    )

    raw_document = (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")
    for forbidden in (
        "cueStyle",
        "shortLabel",
        "semantics",
        "evidence",
        "claims",
        "instructions",
    ):
        assert forbidden not in raw_document
