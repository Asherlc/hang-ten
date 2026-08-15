from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
from board_package import load_board_package  # noqa: E402


PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "trango-rock-prodigy-natural"
PRIMARY_SHA256 = "55d76a5724b96cb94d15c2fff2480975415322d807cf4abead9c1fa07dd278f4"
ALLOWED_HOLD_KINDS = frozenset({"jug", "edge", "pocket", "pinch", "sloper"})
EXPECTED_HOLDS = (
    ("jug-left", "jug", 1),
    ("jug-right", "jug", 1),
    ("top-variable-rail-left", "edge", 1),
    ("top-variable-rail-right", "edge", 1),
    ("bottom-variable-rail-left", "edge", 1),
    ("bottom-variable-rail-right", "edge", 1),
    ("closed-crimp-left", "edge", 2),
    ("closed-crimp-right", "edge", 2),
    ("deep-pocket-left", "pocket", 1),
    ("deep-pocket-right", "pocket", 1),
    ("shallow-pocket-left", "pocket", 1),
    ("shallow-pocket-right", "pocket", 1),
    ("supported-pocket-left", "pocket", 2),
    ("supported-pocket-right", "pocket", 2),
    ("wide-pinch-left", "pinch", 2),
    ("wide-pinch-right", "pinch", 2),
    ("medium-pinch-left", "pinch", 2),
    ("medium-pinch-right", "pinch", 2),
)
MIRRORED_PAIRS = tuple(
    (f"{stem}-left", f"{stem}-right")
    for stem in (
        "jug",
        "top-variable-rail",
        "bottom-variable-rail",
        "closed-crimp",
        "deep-pocket",
        "shallow-pocket",
        "supported-pocket",
        "wide-pinch",
        "medium-pinch",
    )
)
EXPECTED_OPTIONAL_METADATA_BY_STEM = {
    # (sizeMillimeters, depthRangeMillimeters, gripType, fingerCapacity, features)
    "jug": (40, None, None, None, ("jug",)),
    "top-variable-rail": (None, (20, 33), None, None, None),
    "bottom-variable-rail": (None, (10, 24), None, None, None),
    "closed-crimp": (None, None, "fullCrimp", None, ("thinCrimp",)),
    "deep-pocket": (
        38,
        None,
        "threeFingerPocket",
        3,
        ("pocket", "threeFingerPocket"),
    ),
    "shallow-pocket": (
        None,
        None,
        "twoFingerPocket",
        2,
        ("pocket", "twoFingerPocket"),
    ),
    "supported-pocket": (
        None,
        None,
        "threeFingerPocket",
        3,
        ("pocket", "threeFingerPocket"),
    ),
    "wide-pinch": (None, None, None, None, ("widePinch",)),
    "medium-pinch": (None, None, None, None, ("mediumPinch",)),
}


def _points(command: object) -> tuple[tuple[float, float], ...]:
    assert isinstance(command, dict)
    return tuple(
        tuple(command[key])
        for key in ("to", "control", "control1", "control2")
        if key in command
    )


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_all_keys(child) for child in value))
    return set()


def _png_dimensions(path: Path) -> tuple[int, int]:
    image = path.read_bytes()
    assert image[:8] == b"\x89PNG\r\n\x1a\n"
    assert image[12:16] == b"IHDR"
    return struct.unpack(">II", image[16:24])


def test_trango_rock_prodigy_natural_preserves_audited_topology_and_mirrors() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert hashlib.sha256(
        (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()
    ).hexdigest() == PRIMARY_SHA256
    image_width, image_height = _png_dimensions(
        PACKAGE_ROOT / "assets" / "primary.png"
    )
    assert (image_width, image_height) == (1536, 1024)

    assert board["id"] == "trango.rock-prodigy-natural"
    assert board["manufacturer"] == "Trango"
    assert board["name"] == "Rock Prodigy Natural"
    assert board["productURL"] == "https://trango.com/products/rock-prodigy-natural"
    assert board["dimensions"] == "Each board: 7.5 × 6 × 1.5 in"
    assert board["aspectRatio"] == pytest.approx(
        image_width / image_height, abs=1e-12
    )
    assert board["presentation"]["assetPath"] == "assets/primary.png"

    assert tuple(
        (hold["id"], hold["kind"], len(hold["geometry"])) for hold in board["holds"]
    ) == EXPECTED_HOLDS
    kind_counts = Counter(hold["kind"] for hold in board["holds"])
    assert board_package._HOLD_KINDS == ALLOWED_HOLD_KINDS
    assert set(kind_counts) <= ALLOWED_HOLD_KINDS
    assert {kind: kind_counts[kind] for kind in ALLOWED_HOLD_KINDS} == {
        "edge": 6,
        "pocket": 6,
        "pinch": 4,
        "jug": 2,
        "sloper": 0,
    }
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 26

    for hold in board["holds"]:
        for piece in hold["geometry"]:
            assert piece["shape"]["type"] == "path"
            assert board_package._shape_fills_declared_frame(piece["shape"])
            commands = piece["shape"]["commands"]
            assert commands[0]["command"] == "move"
            assert commands[-1]["command"] == "close"
            curves = commands[1:-1]
            assert len(curves) >= 4
            assert all(command["command"] == "curve" for command in curves)
            assert curves[-1]["to"] == commands[0]["to"]
            frame = piece["frame"]
            assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
            assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
            for command in commands:
                assert all(
                    0 <= coordinate <= 1
                    for point in _points(command)
                    for coordinate in point
                )

    for left_id, right_id in MIRRORED_PAIRS:
        for left, right in zip(
            holds[left_id]["geometry"], holds[right_id]["geometry"], strict=True
        ):
            assert right["frame"]["x"] == pytest.approx(
                1 - left["frame"]["x"] - left["frame"]["width"], abs=1e-12
            )
            assert right["frame"]["y"] == pytest.approx(left["frame"]["y"], abs=1e-12)
            assert right["frame"]["width"] == pytest.approx(
                left["frame"]["width"], abs=1e-12
            )
            assert right["frame"]["height"] == pytest.approx(
                left["frame"]["height"], abs=1e-12
            )
            assert right.get("treatment") == left.get("treatment")
            for left_command, right_command in zip(
                left["shape"]["commands"], right["shape"]["commands"], strict=True
            ):
                assert left_command["command"] == right_command["command"]
                for (left_x, left_y), (right_x, right_y) in zip(
                    _points(left_command), _points(right_command), strict=True
                ):
                    assert right_x == pytest.approx(1 - left_x, abs=1e-12)
                    assert right_y == pytest.approx(left_y, abs=1e-12)

    for stem, expected_metadata in EXPECTED_OPTIONAL_METADATA_BY_STEM.items():
        for side in ("left", "right"):
            hold = holds[f"{stem}-{side}"]
            depth_range = hold.get("depthRangeMillimeters")
            actual_metadata = (
                hold.get("sizeMillimeters"),
                None
                if depth_range is None
                else (depth_range["lowerBound"], depth_range["upperBound"]),
                hold.get("gripType"),
                hold.get("fingerCapacity"),
                None if "features" not in hold else tuple(hold["features"]),
            )
            assert actual_metadata == expected_metadata

    raw = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    assert {
        "cueStyle",
        "claims",
        "semantics",
        "evidence",
        "instructions",
        "artwork",
        "catalog",
    }.isdisjoint(_all_keys(raw))
    for forbidden_sidecar in (
        "semantics.json",
        "evidence.json",
        "artwork.json",
        "catalog.json",
    ):
        assert not (PACKAGE_ROOT / forbidden_sidecar).exists()


def test_trango_rock_prodigy_natural_preserves_audited_composite_contacts() -> None:
    holds = {
        hold["id"]: hold
        for hold in load_board_package(PACKAGE_ROOT).board["holds"]
    }

    # These canonical frames preserve the audited full-canvas shapes after the
    # foundation's deterministic frame-local re-encoding.
    expected_pinch_thumb_frames = {
        "wide-pinch-left": (0.2079, 0.739, 0.14065, 0.015),
        "wide-pinch-right": (0.65145, 0.739, 0.14065, 0.015),
        "medium-pinch-left": (0.2079, 0.739, 0.14065, 0.015),
        "medium-pinch-right": (0.65145, 0.739, 0.14065, 0.015),
    }
    for side in ("left", "right"):
        top_rail = holds[f"top-variable-rail-{side}"]["geometry"][0]
        bottom_rail = holds[f"bottom-variable-rail-{side}"]["geometry"][0]
        wide_finger, wide_thumb = holds[f"wide-pinch-{side}"]["geometry"]
        medium_finger, medium_thumb = holds[f"medium-pinch-{side}"]["geometry"]

        assert wide_finger == top_rail
        assert medium_finger == bottom_rail
        assert wide_thumb == medium_thumb
        assert wide_finger != wide_thumb
        assert medium_finger != medium_thumb

    for hold_id, expected_frame in expected_pinch_thumb_frames.items():
        thumb = holds[hold_id]["geometry"][1]
        frame = thumb["frame"]
        assert (
            frame["x"],
            frame["y"],
            frame["width"],
            frame["height"],
        ) == expected_frame
        assert thumb["treatment"] == {"type": "surface"}

    expected_closed_crimp_pieces = {
        "closed-crimp-left": (
            (
                (0.043, 0.51884, 0.2, 0.10416),
                {"type": "shelf", "rimInsetFraction": 0.08},
            ),
            ((0.266, 0.511, 0.027, 0.112), {"type": "surface"}),
        ),
        "closed-crimp-right": (
            (
                (0.757, 0.51884, 0.2, 0.10416),
                {"type": "shelf", "rimInsetFraction": 0.08},
            ),
            ((0.707, 0.511, 0.027, 0.112), {"type": "surface"}),
        ),
    }
    for hold_id, expected_pieces in expected_closed_crimp_pieces.items():
        finger, upright_thumb = holds[hold_id]["geometry"]
        actual_pieces = tuple(
            (
                (
                    piece["frame"]["x"],
                    piece["frame"]["y"],
                    piece["frame"]["width"],
                    piece["frame"]["height"],
                ),
                piece.get("treatment"),
            )
            for piece in (finger, upright_thumb)
        )
        assert actual_pieces == expected_pieces
        assert finger["shape"] != upright_thumb["shape"]

    expected_supported_pocket_frames = {
        "supported-pocket-left": (
            (0.065, 0.657, 0.078, 0.081),
            (0.148, 0.657, 0.046, 0.081),
        ),
        "supported-pocket-right": (
            (0.857, 0.657, 0.078, 0.081),
            (0.806, 0.657, 0.046, 0.081),
        ),
    }
    for hold_id, expected_frames in expected_supported_pocket_frames.items():
        pieces = holds[hold_id]["geometry"]
        assert tuple(
            (
                piece["frame"]["x"],
                piece["frame"]["y"],
                piece["frame"]["width"],
                piece["frame"]["height"],
            )
            for piece in pieces
        ) == expected_frames
        assert pieces[0]["frame"] != pieces[1]["frame"]

        left_piece, right_piece = sorted(
            pieces, key=lambda piece: piece["frame"]["x"]
        )
        divider_width = right_piece["frame"]["x"] - (
            left_piece["frame"]["x"] + left_piece["frame"]["width"]
        )
        assert divider_width == pytest.approx(0.005, abs=1e-12)
