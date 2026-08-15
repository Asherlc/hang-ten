from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path

from PIL import Image

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "moon-armstrong"

EXPECTED_HOLDS = (
    ("incut-jug-left", "jug", None),
    ("incut-jug-right", "jug", None),
    ("sloper-35-left", "sloper", None),
    ("sloper-35-right", "sloper", None),
    ("edge-25-left", "edge", 25),
    ("edge-25-right", "edge", 25),
    ("edge-20-left", "edge", 20),
    ("edge-20-right", "edge", 20),
    ("edge-15-left", "edge", 15),
    ("edge-15-right", "edge", 15),
    ("edge-10-left", "edge", 10),
    ("edge-10-right", "edge", 10),
    ("edge-8-left", "edge", 8),
    ("edge-8-right", "edge", 8),
    ("pocket-22-two-left", "pocket", 22),
    ("pocket-22-two-right", "pocket", 22),
    ("pocket-22-one-left", "pocket", 22),
    ("pocket-22-one-right", "pocket", 22),
    ("center-jug", "jug", None),
    ("center-edge-22", "edge", 22),
    ("center-edge-18", "edge", 18),
)

PAIRS = (
    ("incut-jug-left", "incut-jug-right"),
    ("sloper-35-left", "sloper-35-right"),
    ("edge-25-left", "edge-25-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-15-left", "edge-15-right"),
    ("edge-10-left", "edge-10-right"),
    ("edge-8-left", "edge-8-right"),
    ("pocket-22-two-left", "pocket-22-two-right"),
    ("pocket-22-one-left", "pocket-22-one-right"),
)


def _serialized_commands(piece: object) -> tuple[object, ...]:
    return tuple(
        (
            command.command,
            command.to,
            command.control,
            command.control1,
            command.control2,
        )
        for command in piece.shape.commands
    )


def _intersection_area(first: object, second: object) -> float:
    width = max(
        0,
        min(first.x + first.width, second.x + second.width) - max(first.x, second.x),
    )
    height = max(
        0,
        min(first.y + first.height, second.y + second.height) - max(first.y, second.y),
    )
    return width * height


def test_moon_armstrong_audited_inventory_offset_layout_and_contact_regions() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert board.id == "moon.armstrong"
    assert board.manufacturer == "Moon Climbing"
    assert board.name == "Armstrong Fingerboard"
    assert board.facts["dimensions"] == "65 cm × 16.5 cm × 5.5 cm"
    assert math.isclose(board.facts["aspectRatio"], 65 / 16.5, abs_tol=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters) for hold in board.holds
    ) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "edge": 12,
        "pocket": 4,
        "jug": 3,
        "sloper": 2,
    }

    assert all(len(hold.geometry) == 1 for hold in board.holds)
    for hold in board.holds:
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert any(command.command == "curve" for command in piece.shape.commands)
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0

    # Moon's pairs reuse contact shapes but are diagonally offset, not mirrored
    # into the opposing module. This catches the tempting whole-board mirror.
    for left_id, right_id in PAIRS:
        left = holds[left_id].geometry[0]
        right = holds[right_id].geometry[0]
        assert left.frame.x + left.frame.width / 2 < 0.5
        assert right.frame.x + right.frame.width / 2 > 0.5
        assert math.isclose(left.frame.y, right.frame.y, abs_tol=1e-12)
        assert math.isclose(left.frame.width, right.frame.width, abs_tol=1e-12)
        assert math.isclose(left.frame.height, right.frame.height, abs_tol=1e-12)
        assert _serialized_commands(left) == _serialized_commands(right)

    for left_id, right_id in (
        ("edge-25-left", "edge-25-right"),
        ("edge-20-left", "edge-20-right"),
        ("edge-10-left", "edge-10-right"),
        ("edge-8-left", "edge-8-right"),
    ):
        left = holds[left_id].geometry[0].frame
        right = holds[right_id].geometry[0].frame
        assert not math.isclose(right.x, 1 - left.x - left.width, abs_tol=1e-12)

    for hold_id in ("center-jug", "center-edge-22", "center-edge-18"):
        frame = holds[hold_id].geometry[0].frame
        assert math.isclose(frame.x + frame.width / 2, 0.5, abs_tol=0.002)
        assert holds[hold_id].geometry[0].treatment["type"] == "shelf"

    # The broad sloper plane and incut cavity are distinct contacts on each top
    # module, while each mono aperture is isolated from its two-finger pocket.
    for side in ("left", "right"):
        jug = holds[f"incut-jug-{side}"].geometry[0].frame
        sloper = holds[f"sloper-35-{side}"].geometry[0].frame
        assert jug != sloper
        assert _intersection_area(jug, sloper) == 0

        mono = holds[f"pocket-22-one-{side}"].geometry[0].frame
        two = holds[f"pocket-22-two-{side}"].geometry[0].frame
        assert _intersection_area(mono, two) == 0
        assert 0.025 <= mono.width <= 0.029
        assert 0.045 <= mono.height <= 0.051

    assert holds["sloper-35-left"].grip_type == "sloper"
    assert holds["sloper-35-right"].grip_type == "sloper"
    for side in ("left", "right"):
        assert holds[f"pocket-22-two-{side}"].finger_capacity == 2
        assert holds[f"pocket-22-two-{side}"].grip_type == "twoFingerPocket"
        assert holds[f"pocket-22-one-{side}"].finger_capacity == 1
        assert holds[f"pocket-22-one-{side}"].grip_type is None

    assert all(hold.depth_range_millimeters is None for hold in board.holds)
    assert all(hold.features is None for hold in board.holds)

    payload = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    serialized = json.dumps(payload)
    for forbidden in (
        "cueStyle",
        "semantics",
        "evidence",
        "claims",
        "palette",
        "shadow",
        "branding",
    ):
        assert forbidden not in serialized
    assert {entry.name for entry in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {entry.name for entry in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }


def test_moon_armstrong_primary_contains_both_separate_through_monos() -> None:
    image = Image.open(PACKAGE_ROOT / "assets" / "primary.png").convert("RGB")
    width, height = image.size
    assert (width, height) == (1672, 941)

    # Each mono center exposes the same near-white backdrop as the image corner,
    # and its surrounding rim remains visibly wooden rather than becoming a
    # broad background cut-out.
    backdrop = image.getpixel((0, 0))
    for normalized_x, normalized_y in ((0.3475, 0.661), (0.8185, 0.661)):
        center_x = round(normalized_x * width)
        center_y = round(normalized_y * height)
        center = image.getpixel((center_x, center_y))
        assert sum(abs(a - b) for a, b in zip(center, backdrop, strict=True)) < 45

        wooden_rim = image.getpixel((center_x, round((normalized_y - 0.044) * height)))
        assert sum(abs(a - b) for a, b in zip(wooden_rim, backdrop, strict=True)) > 70
