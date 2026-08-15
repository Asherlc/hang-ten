from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import sys

from PIL import Image
import pytest


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


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


def _serialized_commands(piece: dict[str, object]) -> tuple[object, ...]:
    shape = piece["shape"]
    assert isinstance(shape, dict)
    commands = shape["commands"]
    assert isinstance(commands, list)
    return tuple(
        (
            command["command"],
            command.get("to"),
            command.get("control"),
            command.get("control1"),
            command.get("control2"),
        )
        for command in commands
        if isinstance(command, dict)
    )


def _intersection_area(first: dict[str, object], second: dict[str, object]) -> float:
    first_x = first["x"]
    first_y = first["y"]
    first_width = first["width"]
    first_height = first["height"]
    second_x = second["x"]
    second_y = second["y"]
    second_width = second["width"]
    second_height = second["height"]
    assert all(
        isinstance(value, (int, float))
        for value in (
            first_x,
            first_y,
            first_width,
            first_height,
            second_x,
            second_y,
            second_width,
            second_height,
        )
    )
    width = max(0, min(first_x + first_width, second_x + second_width) - max(first_x, second_x))
    height = max(0, min(first_y + first_height, second_y + second_height) - max(first_y, second_y))
    return width * height


def _piece(holds: dict[str, dict[str, object]], hold_id: str) -> dict[str, object]:
    geometry = holds[hold_id]["geometry"]
    assert isinstance(geometry, list) and len(geometry) == 1
    piece = geometry[0]
    assert isinstance(piece, dict)
    return piece


def _frame(piece: dict[str, object]) -> dict[str, object]:
    frame = piece["frame"]
    assert isinstance(frame, dict)
    return frame


def test_moon_armstrong_audited_inventory_offset_layout_and_contact_regions() -> None:
    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert board["id"] == "moon.armstrong"
    assert board["manufacturer"] == "Moon Climbing"
    assert board["name"] == "Armstrong Fingerboard"
    assert board["dimensions"] == "65 cm × 16.5 cm × 5.5 cm"
    assert board["aspectRatio"] == pytest.approx(1672 / 941, rel=0.001)
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert tuple((hold["id"], hold["kind"], hold.get("sizeMillimeters")) for hold in board["holds"]) == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "edge": 12,
        "pocket": 4,
        "jug": 3,
        "sloper": 2,
    }

    assert all(len(hold["geometry"]) == 1 for hold in board["holds"])
    for hold in board["holds"]:
        piece = _piece(holds, hold["id"])
        shape = piece["shape"]
        frame = _frame(piece)
        assert isinstance(shape, dict)
        commands = shape["commands"]
        assert shape["type"] == "path"
        assert isinstance(commands, list)
        assert commands[0]["command"] == "move"
        assert commands[-1]["command"] == "close"
        assert any(command["command"] == "curve" for command in commands)
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0
        points = [
            point
            for command in commands
            for key in ("to", "control", "control1", "control2")
            if key in command
            for point in [command[key]]
        ]
        assert min(point[0] for point in points) == pytest.approx(0, abs=5e-7)
        assert min(point[1] for point in points) == pytest.approx(0, abs=5e-7)
        assert max(point[0] for point in points) == pytest.approx(1, abs=5e-7)
        assert max(point[1] for point in points) == pytest.approx(1, abs=5e-7)

    # Moon's pairs reuse contact shapes but are diagonally offset, not mirrored
    # into the opposing module. This catches the tempting whole-board mirror.
    for left_id, right_id in PAIRS:
        left = _piece(holds, left_id)
        right = _piece(holds, right_id)
        left_frame = _frame(left)
        right_frame = _frame(right)
        assert left_frame["x"] + left_frame["width"] / 2 < 0.5
        assert right_frame["x"] + right_frame["width"] / 2 > 0.5
        assert math.isclose(left_frame["y"], right_frame["y"], abs_tol=1e-12)
        assert math.isclose(left_frame["width"], right_frame["width"], abs_tol=1e-12)
        assert math.isclose(left_frame["height"], right_frame["height"], abs_tol=1e-12)
        assert _serialized_commands(left) == _serialized_commands(right)

    for left_id, right_id in (
        ("edge-25-left", "edge-25-right"),
        ("edge-20-left", "edge-20-right"),
        ("edge-10-left", "edge-10-right"),
        ("edge-8-left", "edge-8-right"),
    ):
        left = _frame(_piece(holds, left_id))
        right = _frame(_piece(holds, right_id))
        assert not math.isclose(right["x"], 1 - left["x"] - left["width"], abs_tol=1e-12)

    for hold_id in ("center-jug", "center-edge-22", "center-edge-18"):
        piece = _piece(holds, hold_id)
        frame = _frame(piece)
        treatment = piece["treatment"]
        assert math.isclose(frame["x"] + frame["width"] / 2, 0.5, abs_tol=0.002)
        assert isinstance(treatment, dict)
        assert treatment["type"] == "shelf"

    # The broad sloper plane and incut cavity are distinct contacts on each top
    # module, while each mono aperture is isolated from its two-finger pocket.
    for side in ("left", "right"):
        jug = _frame(_piece(holds, f"incut-jug-{side}"))
        sloper = _frame(_piece(holds, f"sloper-35-{side}"))
        assert jug != sloper
        assert _intersection_area(jug, sloper) == 0

        mono = _frame(_piece(holds, f"pocket-22-one-{side}"))
        two = _frame(_piece(holds, f"pocket-22-two-{side}"))
        assert _intersection_area(mono, two) == 0
        assert 0.025 <= mono["width"] <= 0.029
        assert 0.045 <= mono["height"] <= 0.051

    assert holds["sloper-35-left"]["gripType"] == "sloper"
    assert holds["sloper-35-right"]["gripType"] == "sloper"
    for side in ("left", "right"):
        assert holds[f"pocket-22-two-{side}"]["fingerCapacity"] == 2
        assert holds[f"pocket-22-two-{side}"]["gripType"] == "twoFingerPocket"
        assert holds[f"pocket-22-one-{side}"]["fingerCapacity"] == 1
        assert holds[f"pocket-22-one-{side}"].get("gripType") is None

    assert all(hold.get("depthRangeMillimeters") is None for hold in board["holds"])
    assert all(hold.get("features") is None for hold in board["holds"])

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
