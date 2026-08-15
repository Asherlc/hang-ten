from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path

from PIL import Image

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "metolius-project"
EXPECTED_HOLDS = (
    ("jug-left", "jug", None, None),
    ("jug-right", "jug", None, None),
    ("sloper-flat-left", "sloper", 55, None),
    ("sloper-flat-right", "sloper", 55, None),
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
    ("sloper-round-center", "sloper", 53, None),
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
EXPECTED_PIXEL_FRAMES = {
    "jug-left": (
        (80.0, 225.0, 290.52, 67.25),
        (80.0, 280.382353, 58.542, 106.808824),
        (314.03, 280.382353, 56.49, 106.808824),
        (136.49, 341.698529, 177.54, 45.492647),
    ),
    "jug-right": (
        (1403.48, 225.0, 290.52, 67.25),
        (1635.458, 280.382353, 58.542, 106.808824),
        (1403.48, 280.382353, 56.49, 106.808824),
        (1459.97, 341.698529, 177.54, 45.492647),
    ),
    "sloper-flat-left": ((370.52, 260.602941, 274.38, 126.588235),),
    "sloper-flat-right": ((1129.10, 260.602941, 274.38, 126.588235),),
    "pocket-45-three-left": ((139.718, 290.272059, 177.54, 57.360294),),
    "pocket-45-three-right": ((1456.742, 290.272059, 177.54, 57.360294),),
    "edge-30-left": ((194.594, 389.169118, 242.10, 73.183823),),
    "edge-30-right": ((1337.306, 389.169118, 242.10, 73.183823),),
    "pocket-40-two-left": ((475.43, 391.147058, 96.84, 57.360294),),
    "pocket-40-two-right": ((1201.73, 391.147058, 96.84, 57.360294),),
    "pocket-22-three-left": ((254.312, 509.823529, 180.768, 67.25),),
    "pocket-22-three-right": ((1338.92, 509.823529, 180.768, 67.25),),
    "pocket-22-two-left": ((475.43, 505.867647, 96.84, 61.316177),),
    "pocket-22-two-right": ((1201.73, 505.867647, 96.84, 61.316177),),
    "sloper-round-center": ((644.90, 256.647059, 484.20, 130.544118),),
    "edge-39-center": ((604.55, 385.213235, 564.90, 81.095588),),
    "edge-16-center": ((604.55, 497.955882, 564.90, 75.161765),),
}


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_metolius_project_preserves_audited_inventory_and_mirrored_contacts() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    with Image.open(PACKAGE_ROOT / "assets" / "primary.png") as presentation:
        presentation_size = presentation.size

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board.id == "metolius.project"
    assert board.manufacturer == "Metolius"
    assert board.name == "Project Training Board"
    assert board.facts["dimensions"] == "622 × 152 mm"
    assert board.facts["aspectRatio"] == 4.08
    assert board.presentation_asset_path == "assets/primary.png"
    assert presentation_size == (1774, 887)
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

        # Canonical Workbench coordinates are normalized to the complete
        # presentation image, including its intentional padding. A cropped
        # inner-board coordinate system would shift every path on package open.
        for piece, expected in zip(
            hold.geometry,
            EXPECTED_PIXEL_FRAMES[hold.id],
            strict=True,
        ):
            actual = (
                piece.frame.x * presentation_size[0],
                piece.frame.y * presentation_size[1],
                piece.frame.width * presentation_size[0],
                piece.frame.height * presentation_size[1],
            )
            assert all(
                math.isclose(value, target, abs_tol=0.001)
                for value, target in zip(actual, expected, strict=True)
            )

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
