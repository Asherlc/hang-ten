from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import struct
import sys

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "metolius-contact"
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
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
EXPECTED_HOLD_METADATA = {
    "pinch-left": {"name": "Left variable-width pinch", "kind": "pinch"},
    "pinch-right": {"name": "Right variable-width pinch", "kind": "pinch"},
    "jug-left": {"name": "Left outer jug", "kind": "jug", "features": ["jug"]},
    "jug-right": {"name": "Right outer jug", "kind": "jug", "features": ["jug"]},
    "sloper-round-left": {"name": "Left 63 mm round sloper", "kind": "sloper", "gripType": "sloper", "features": ["roundSloper"]},
    "sloper-round-right": {"name": "Right 63 mm round sloper", "kind": "sloper", "gripType": "sloper", "features": ["roundSloper"]},
    "pocket-30-four-left": {"name": "Left 30 mm four-finger pocket", "kind": "pocket", "sizeMillimeters": 30, "fingerCapacity": 4, "gripType": "fourFingerPocket", "features": ["pocket", "fourFingerPocket"]},
    "pocket-30-four-right": {"name": "Right 30 mm four-finger pocket", "kind": "pocket", "sizeMillimeters": 30, "fingerCapacity": 4, "gripType": "fourFingerPocket", "features": ["pocket", "fourFingerPocket"]},
    "pocket-40-two-left": {"name": "Left 40 mm two-finger pocket", "kind": "pocket", "sizeMillimeters": 40, "fingerCapacity": 2, "gripType": "twoFingerPocket", "features": ["pocket", "twoFingerPocket"]},
    "pocket-40-two-right": {"name": "Right 40 mm two-finger pocket", "kind": "pocket", "sizeMillimeters": 40, "fingerCapacity": 2, "gripType": "twoFingerPocket", "features": ["pocket", "twoFingerPocket"]},
    "pocket-20-three-left": {"name": "Left 20 mm three-finger pocket", "kind": "pocket", "sizeMillimeters": 20, "fingerCapacity": 3, "gripType": "threeFingerPocket", "features": ["pocket", "threeFingerPocket"]},
    "pocket-20-three-right": {"name": "Right 20 mm three-finger pocket", "kind": "pocket", "sizeMillimeters": 20, "fingerCapacity": 3, "gripType": "threeFingerPocket", "features": ["pocket", "threeFingerPocket"]},
    "pocket-30-three-left": {"name": "Left 30 mm three-finger pocket", "kind": "pocket", "sizeMillimeters": 30, "fingerCapacity": 3, "gripType": "threeFingerPocket", "features": ["pocket", "threeFingerPocket"]},
    "pocket-30-three-right": {"name": "Right 30 mm three-finger pocket", "kind": "pocket", "sizeMillimeters": 30, "fingerCapacity": 3, "gripType": "threeFingerPocket", "features": ["pocket", "threeFingerPocket"]},
    "pocket-32-two-left": {"name": "Left 32 mm two-finger pocket", "kind": "pocket", "sizeMillimeters": 32, "fingerCapacity": 2, "gripType": "twoFingerPocket", "features": ["pocket", "twoFingerPocket"]},
    "pocket-32-two-right": {"name": "Right 32 mm two-finger pocket", "kind": "pocket", "sizeMillimeters": 32, "fingerCapacity": 2, "gripType": "twoFingerPocket", "features": ["pocket", "twoFingerPocket"]},
    "pocket-20-four-left": {"name": "Left 20 mm four-finger pocket", "kind": "pocket", "sizeMillimeters": 20, "fingerCapacity": 4, "gripType": "fourFingerPocket", "features": ["pocket", "fourFingerPocket"]},
    "pocket-20-four-right": {"name": "Right 20 mm four-finger pocket", "kind": "pocket", "sizeMillimeters": 20, "fingerCapacity": 4, "gripType": "fourFingerPocket", "features": ["pocket", "fourFingerPocket"]},
    "pocket-25-three-left": {"name": "Left 25 mm three-finger pocket", "kind": "pocket", "sizeMillimeters": 25, "fingerCapacity": 3, "gripType": "threeFingerPocket", "features": ["pocket", "threeFingerPocket"]},
    "pocket-25-three-right": {"name": "Right 25 mm three-finger pocket", "kind": "pocket", "sizeMillimeters": 25, "fingerCapacity": 3, "gripType": "threeFingerPocket", "features": ["pocket", "threeFingerPocket"]},
    "pocket-25-two-left": {"name": "Left 25 mm two-finger pocket", "kind": "pocket", "sizeMillimeters": 25, "fingerCapacity": 2, "gripType": "twoFingerPocket", "features": ["pocket", "twoFingerPocket"]},
    "pocket-25-two-right": {"name": "Right 25 mm two-finger pocket", "kind": "pocket", "sizeMillimeters": 25, "fingerCapacity": 2, "gripType": "twoFingerPocket", "features": ["pocket", "twoFingerPocket"]},
    "pocket-12-four-left": {"name": "Left 12 mm four-finger pocket", "kind": "pocket", "sizeMillimeters": 12, "fingerCapacity": 4, "gripType": "fourFingerPocket", "features": ["pocket", "fourFingerPocket"]},
    "pocket-12-four-right": {"name": "Right 12 mm four-finger pocket", "kind": "pocket", "sizeMillimeters": 12, "fingerCapacity": 4, "gripType": "fourFingerPocket", "features": ["pocket", "fourFingerPocket"]},
    "pocket-17-three-left": {"name": "Left 17 mm three-finger pocket", "kind": "pocket", "sizeMillimeters": 17, "fingerCapacity": 3, "gripType": "threeFingerPocket", "features": ["pocket", "threeFingerPocket"]},
    "pocket-17-three-right": {"name": "Right 17 mm three-finger pocket", "kind": "pocket", "sizeMillimeters": 17, "fingerCapacity": 3, "gripType": "threeFingerPocket", "features": ["pocket", "threeFingerPocket"]},
    "pocket-17-two-left": {"name": "Left 17 mm two-finger pocket", "kind": "pocket", "sizeMillimeters": 17, "fingerCapacity": 2, "gripType": "twoFingerPocket", "features": ["pocket", "twoFingerPocket"]},
    "pocket-17-two-right": {"name": "Right 17 mm two-finger pocket", "kind": "pocket", "sizeMillimeters": 17, "fingerCapacity": 2, "gripType": "twoFingerPocket", "features": ["pocket", "twoFingerPocket"]},
    "sloper-flat-center": {"name": "Center 53 mm flat sloper", "kind": "sloper", "gripType": "sloper"},
    "edge-15-center": {"name": "Center 15 mm edge", "kind": "edge", "sizeMillimeters": 15},
    "edge-35-center": {"name": "Center 35 mm edge", "kind": "edge", "sizeMillimeters": 35},
    "edge-28-center": {"name": "Center 28 mm edge", "kind": "edge", "sizeMillimeters": 28},
    "edge-23-center": {"name": "Center 23 mm edge", "kind": "edge", "sizeMillimeters": 23},
}
PRESENTATION_SIZE = (1774, 887)
EXPECTED_PIXEL_FRAMES = {
    "pinch-left": (65.208, 213.06, 245.88084, 471.614),
    "pinch-right": (1462.91116, 213.06, 245.88084, 471.614),
    "jug-left": (311.072, 167.3, 158.296, 153.296),
    "jug-right": (1304.632, 167.3, 158.296, 153.296),
    "sloper-round-left": (469.368, 154.144, 200.396, 152.724),
    "sloper-round-right": (1104.236, 154.144, 200.396, 152.724),
    "pocket-30-four-left": (349.804, 320.024, 170.084, 56.056),
    "pocket-30-four-right": (1254.112, 320.024, 170.084, 56.056),
    "pocket-40-two-left": (550.2, 325.744, 84.2, 49.764),
    "pocket-40-two-right": (1139.6, 325.744, 84.2, 49.764),
    "pocket-20-three-left": (248.764, 410.972, 117.88, 52.052),
    "pocket-20-three-right": (1407.356, 410.972, 117.88, 52.052),
    "pocket-30-three-left": (393.588, 410.972, 127.984, 49.764),
    "pocket-30-three-right": (1252.428, 410.972, 127.984, 49.764),
    "pocket-32-two-left": (548.516, 409.256, 85.884, 52.052),
    "pocket-32-two-right": (1139.6, 409.256, 85.884, 52.052),
    "pocket-20-four-left": (223.504, 493.34, 144.824, 48.62),
    "pocket-20-four-right": (1405.672, 493.34, 144.824, 48.62),
    "pocket-25-three-left": (391.904, 493.912, 129.668, 48.048),
    "pocket-25-three-right": (1252.428, 493.912, 129.668, 48.048),
    "pocket-25-two-left": (548.516, 493.34, 85.884, 46.904),
    "pocket-25-two-right": (1139.6, 493.34, 85.884, 46.904),
    "pocket-12-four-left": (215.084, 573.992, 153.244, 45.76),
    "pocket-12-four-right": (1405.672, 573.992, 153.244, 45.76),
    "pocket-17-three-left": (390.22, 573.992, 131.352, 44.616),
    "pocket-17-three-right": (1252.428, 573.992, 131.352, 44.616),
    "pocket-17-two-left": (546.832, 572.848, 87.568, 45.188),
    "pocket-17-two-right": (1139.6, 572.848, 87.568, 45.188),
    "sloper-flat-center": (669.764, 153.0, 434.472, 84.084),
    "edge-15-center": (676.5, 239.372, 421.0, 47.476),
    "edge-35-center": (659.66, 317.164, 454.68, 90.376),
    "edge-28-center": (664.712, 439.572, 444.576, 104.676),
    "edge-23-center": (663.028, 556.832, 447.944, 78.364),
}


def _points(command: object) -> tuple[tuple[float, float], ...]:
    assert isinstance(command, dict)
    return tuple(
        point
        for point in (
            command.get("to"),
            command.get("control"),
            command.get("control1"),
            command.get("control2"),
        )
        if point is not None
    )


def test_metolius_contact_aspect_ratio_matches_its_png_ihdr() -> None:
    board = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    primary = (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()

    assert primary[:8] == b"\x89PNG\r\n\x1a\n"
    assert primary[12:16] == b"IHDR"
    width, height = struct.unpack(">II", primary[16:24])
    assert (width, height) == PRESENTATION_SIZE
    assert width / height == 2.0
    assert board["aspectRatio"] == 2.0


def test_metolius_contact_preserves_all_physical_contacts_and_mirrors() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}
    with Image.open(PACKAGE_ROOT / "assets" / "primary.png") as presentation:
        presentation_size = presentation.size

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board["id"] == "metolius.contact"
    assert board["manufacturer"] == "Metolius"
    assert board["name"] == "Contact Training Board"
    assert board["dimensions"] == "32.5 × 11 × 2.625 in (826 × 279 × 67 mm)"
    assert board["aspectRatio"] == 2.0
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert presentation_size == PRESENTATION_SIZE
    assert tuple(holds) == EXPECTED_HOLDS
    assert tuple(EXPECTED_HOLD_METADATA) == EXPECTED_HOLDS
    for hold_id, expected_metadata in EXPECTED_HOLD_METADATA.items():
        assert {key: value for key, value in holds[hold_id].items() if key != "geometry"} == {
            "id": hold_id,
            **expected_metadata,
        }
    assert Counter(hold["kind"] for hold in holds.values()) == {
        "pocket": 22,
        "edge": 4,
        "sloper": 3,
        "pinch": 2,
        "jug": 2,
    }

    for hold in holds.values():
        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        shape = piece["shape"]
        frame = piece["frame"]
        assert shape["type"] == "path"
        assert shape["commands"][0]["command"] == "move"
        assert shape["commands"][-1]["command"] == "close"
        assert any(command["command"] == "curve" for command in shape["commands"])
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0

        # Canonical Workbench frames are normalized to the complete primary
        # image canvas, including its intentional outer padding.
        actual_pixel_frame = (
            frame["x"] * presentation_size[0],
            frame["y"] * presentation_size[1],
            frame["width"] * presentation_size[0],
            frame["height"] * presentation_size[1],
        )
        assert all(
            math.isclose(actual, expected, abs_tol=1e-6)
            for actual, expected in zip(
                actual_pixel_frame,
                EXPECTED_PIXEL_FRAMES[hold["id"]],
                strict=True,
            )
        )

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id]["geometry"][0]
        right = holds[right_id]["geometry"][0]
        left_frame = left["frame"]
        right_frame = right["frame"]
        assert math.isclose(
            right_frame["x"], 1 - left_frame["x"] - left_frame["width"], abs_tol=1e-12
        )
        assert right_frame["y"] == left_frame["y"]
        assert right_frame["width"] == left_frame["width"]
        assert right_frame["height"] == left_frame["height"]
        for left_command, right_command in zip(
            left["shape"]["commands"], right["shape"]["commands"], strict=True
        ):
            assert left_command["command"] == right_command["command"]
            for (left_x, left_y), (right_x, right_y) in zip(
                _points(left_command), _points(right_command), strict=True
            ):
                assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                assert math.isclose(right_y, left_y, abs_tol=1e-12)

    for stem, (size, capacity, grip_type) in POCKET_FACTS.items():
        for side in ("left", "right"):
            hold = holds[f"{stem}-{side}"]
            assert hold["sizeMillimeters"] == size
            assert hold["fingerCapacity"] == capacity
            assert hold["gripType"] == grip_type
            assert hold["features"] == ["pocket", grip_type]

    assert holds["jug-left"]["features"] == ["jug"]
    assert holds["jug-right"]["features"] == ["jug"]
    assert holds["sloper-round-left"]["gripType"] == "sloper"
    assert holds["sloper-round-left"]["features"] == ["roundSloper"]
    assert holds["sloper-round-right"]["gripType"] == "sloper"
    assert holds["sloper-round-right"]["features"] == ["roundSloper"]
    assert holds["sloper-flat-center"]["gripType"] == "sloper"
    assert holds["sloper-flat-center"].get("sizeMillimeters") is None
    assert {
        hold_id: holds[hold_id]["sizeMillimeters"]
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
    assert all(hold.get("depthRangeMillimeters") is None for hold in holds.values())
    assert all(
        holds[hold_id].get("gripType") is None
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
