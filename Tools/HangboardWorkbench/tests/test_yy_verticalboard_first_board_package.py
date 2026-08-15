from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "yy-verticalboard-first"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


EXPECTED_HOLDS = (
    ("pocket-45", "45 mm four-finger pocket", "pocket", 45, 4, 2),
    ("pocket-33", "33 mm four-finger pocket", "pocket", 33, 4, 2),
    ("pocket-25", "25 mm four-finger pocket", "pocket", 25, 4, 2),
    ("pocket-22", "22 mm four-finger pocket", "pocket", 22, 4, 2),
    ("pocket-20", "20 mm four-finger pocket", "pocket", 20, 4, 2),
    ("center-handle", "40 / 24 mm center handle", "edge", None, None, 2),
    ("sloper-35", "35° sloper", "sloper", None, None, 2),
    ("sloper-20", "20° sloper", "sloper", None, None, 1),
    ("jug-left", "Left jug", "jug", None, None, 1),
    ("jug-right", "Right jug", "jug", None, None, 1),
)
# Literal review contract from the accepted numbered overlay and source audit. The
# piece index is meaningful: paired holds are left then right, while the center
# handle is specifically upper 40 mm then lower 24 mm.
EXPECTED_PIECES = {
    ("pocket-45", 0): ((0.089, 0.454, 0.147, 0.084), {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"}, "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952"),
    ("pocket-45", 1): ((0.764, 0.454, 0.147, 0.084), {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"}, "bd8addd2817a7608a041627eb4751d4469f6319505708c6cb66f7de7b4510094"),
    ("pocket-33", 0): ((0.249, 0.455, 0.143, 0.081), {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"}, "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952"),
    ("pocket-33", 1): ((0.608, 0.455, 0.143, 0.081), {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"}, "bd8addd2817a7608a041627eb4751d4469f6319505708c6cb66f7de7b4510094"),
    ("pocket-25", 0): ((0.09, 0.345, 0.145, 0.08), {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}, "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952"),
    ("pocket-25", 1): ((0.765, 0.345, 0.145, 0.08), {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}, "bd8addd2817a7608a041627eb4751d4469f6319505708c6cb66f7de7b4510094"),
    ("pocket-22", 0): ((0.285, 0.596, 0.14, 0.08), {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}, "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952"),
    ("pocket-22", 1): ((0.575, 0.596, 0.14, 0.08), {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}, "bd8addd2817a7608a041627eb4751d4469f6319505708c6cb66f7de7b4510094"),
    ("pocket-20", 0): ((0.138, 0.596, 0.14, 0.08), {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}, "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952"),
    ("pocket-20", 1): ((0.722, 0.596, 0.14, 0.08), {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}, "bd8addd2817a7608a041627eb4751d4469f6319505708c6cb66f7de7b4510094"),
    ("center-handle", 0): ((0.43, 0.455, 0.14, 0.082), {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"}, "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952"),
    ("center-handle", 1): ((0.432, 0.597, 0.136, 0.08), {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}, "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952"),
    ("sloper-35", 0): ((0.251, 0.311, 0.143, 0.104), {"type": "surface"}, "dc87355812bc565f3ae440fc257116e3fd93f19ded489b6f3b22acafab947347"),
    ("sloper-35", 1): ((0.606, 0.311, 0.143, 0.104), {"type": "surface"}, "0be6e6cc96179c075fad20d7bcf9a48d5f5ba5d1340a726db552377033f65c52"),
    ("sloper-20", 0): ((0.394, 0.312, 0.212, 0.052), {"type": "surface"}, "105868228cb1f512018bc4eea7207b339f0836c87cc0bbdc9ffe78c7a7f13cf5"),
    ("jug-left", 0): ((0.073, 0.291, 0.177, 0.051), {"type": "surface"}, "686b58bb5a730c13ecc77c70357f9285c35058fdbb0ce5f29fdf190e66f96a53"),
    ("jug-right", 0): ((0.75, 0.291, 0.177, 0.051), {"type": "surface"}, "ae205f67af4382c9ecd2f261fb931a6308f65893170eccc7e45f75837aecb22d"),
}
MIRRORED_MULTI_PIECE_HOLDS = ("pocket-45", "pocket-33", "pocket-25", "pocket-22", "pocket-20", "sloper-35")


def _frame_tuple(piece: dict[str, object]) -> tuple[float, float, float, float]:
    frame = piece["frame"]
    assert isinstance(frame, dict)
    return (frame["x"], frame["y"], frame["width"], frame["height"])


def _path_digest(piece: dict[str, object]) -> str:
    shape = piece["shape"]
    assert isinstance(shape, dict)
    commands = [
        {
            "command": command["command"],
            "to": command.get("to"),
            "control": command.get("control"),
            "control1": command.get("control1"),
            "control2": command.get("control2"),
        }
        for command in shape["commands"]
    ]
    return sha256(json.dumps(commands, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _png_dimensions(path: Path) -> tuple[int, int]:
    signature, length, chunk_type, width, height = struct.unpack(">8sI4sII", path.read_bytes()[:24])
    assert signature == b"\x89PNG\r\n\x1a\n" and length == 13 and chunk_type == b"IHDR"
    return width, height


def _global_points(piece: dict[str, object]) -> list[tuple[float, float]]:
    frame = piece["frame"]
    shape = piece["shape"]
    assert isinstance(frame, dict) and isinstance(shape, dict)
    points = []
    for command in shape["commands"]:
        for key in ("to", "control", "control1", "control2"):
            if key in command:
                x, y = command[key]
                points.append((frame["x"] + x * frame["width"], frame["y"] + y * frame["height"]))
    return points


def _assert_exact_global_mirror(left: dict[str, object], right: dict[str, object]) -> None:
    left_frame, right_frame = left["frame"], right["frame"]
    assert isinstance(left_frame, dict) and isinstance(right_frame, dict)
    assert right_frame["x"] == pytest.approx(1 - left_frame["x"] - left_frame["width"], abs=1e-12)
    assert right_frame["y"] == pytest.approx(left_frame["y"], abs=1e-12)
    assert right_frame["width"] == pytest.approx(left_frame["width"], abs=1e-12)
    assert right_frame["height"] == pytest.approx(left_frame["height"], abs=1e-12)
    assert right["treatment"] == left["treatment"]
    assert [item["command"] for item in right["shape"]["commands"]] == [item["command"] for item in left["shape"]["commands"]]
    for (left_x, left_y), (right_x, right_y) in zip(_global_points(left), _global_points(right), strict=True):
        assert right_x == pytest.approx(1 - left_x, abs=1e-12)
        assert right_y == pytest.approx(left_y, abs=1e-12)


def _overlap_area(left: dict[str, float], right: dict[str, float]) -> float:
    return max(0.0, min(left["x"] + left["width"], right["x"] + right["width"]) - max(left["x"], right["x"])) * max(0.0, min(left["y"] + left["height"], right["y"] + right["height"]) - max(left["y"], right["y"]))


def test_yy_verticalboard_first_preserves_audited_logical_holds_and_contacts() -> None:
    board = board_package.load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert (board["id"], board["manufacturer"], board["name"]) == ("yy.verticalboard-first", "YY Vertical", "VerticalBoard First")
    assert board["subtitle"] == "Ten-grip poplar hangboard with five four-finger pocket depths, two sloper angles, two jugs, and a central handle."
    assert board["productURL"] == "https://www.yyvertical.com/en/products/verticalboard-first"
    assert board["dimensions"] == "540 × 130 × 50 mm"
    assert board["aspectRatio"] == pytest.approx(2.0, abs=1e-12)
    assert board["presentation"] == {"assetPath": "assets/primary.png"}
    source_asset = PACKAGE_ROOT / board["presentation"]["assetPath"]
    assert sha256(source_asset.read_bytes()).hexdigest() == "e765f9ffad834127c96499008d5f99fa768bd11764e64cb96becc6d93d8a8011"
    assert _png_dimensions(source_asset) == (1774, 887)
    assert tuple((hold["id"], hold["name"], hold["kind"], hold.get("sizeMillimeters"), hold.get("fingerCapacity"), len(hold["geometry"])) for hold in board["holds"]) == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {"pocket": 5, "edge": 1, "sloper": 2, "jug": 2}
    assert Counter(hold["kind"] for hold in board["holds"] for _piece in hold["geometry"]) == {"pocket": 10, "edge": 2, "sloper": 3, "jug": 2}
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 17
    pieces = [piece for hold in board["holds"] for piece in hold["geometry"]]
    actual_pieces = {(hold["id"], index): piece for hold in board["holds"] for index, piece in enumerate(hold["geometry"])}
    assert actual_pieces.keys() == EXPECTED_PIECES.keys()
    for key, (frame, treatment, digest) in EXPECTED_PIECES.items():
        piece = actual_pieces[key]
        assert _frame_tuple(piece) == frame
        assert piece.get("treatment") == treatment
        assert _path_digest(piece) == digest
    for piece in pieces:
        assert piece["shape"]["type"] == "path"
        assert piece["shape"]["commands"][0]["command"] == "move"
        assert piece["shape"]["commands"][-1]["command"] == "close"
        assert sum(command["command"] == "curve" for command in piece["shape"]["commands"]) >= 4
        frame = piece["frame"]
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0
        assert all(0 <= coordinate <= 1 for command in piece["shape"]["commands"] for point in command.values() if isinstance(point, list) for coordinate in point)
    for hold_id in MIRRORED_MULTI_PIECE_HOLDS:
        _assert_exact_global_mirror(holds[hold_id]["geometry"][0], holds[hold_id]["geometry"][1])
    _assert_exact_global_mirror(holds["jug-left"]["geometry"][0], holds["jug-right"]["geometry"][0])
    upper_40_mm, lower_24_mm = holds["center-handle"]["geometry"]
    assert upper_40_mm["frame"]["y"] < lower_24_mm["frame"]["y"]
    assert upper_40_mm["frame"] != lower_24_mm["frame"]
    assert upper_40_mm["treatment"] == {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"}
    assert lower_24_mm["treatment"] == {"type": "recess", "rimInsetFraction": 0.1, "depth": "shallow"}
    for piece in (upper_40_mm, lower_24_mm, holds["sloper-20"]["geometry"][0]):
        frame = piece["frame"]
        assert frame["x"] == pytest.approx(1 - frame["x"] - frame["width"], abs=1e-12)
    for hold_id in ("sloper-35", "sloper-20", "jug-left", "jug-right"):
        assert all(piece["treatment"] == {"type": "surface"} for piece in holds[hold_id]["geometry"])
    for index, left in enumerate(pieces):
        for right in pieces[index + 1:]:
            assert _overlap_area(left["frame"], right["frame"]) == pytest.approx(0, abs=1e-12)
    assert all("depthRangeMillimeters" not in hold and "gripType" not in hold and "features" not in hold for hold in board["holds"])
    assert {hold["id"]: hold.get("fingerCapacity") for hold in board["holds"]} == {"pocket-45": 4, "pocket-33": 4, "pocket-25": 4, "pocket-22": 4, "pocket-20": 4, "center-handle": None, "sloper-35": None, "sloper-20": None, "jug-left": None, "jug-right": None}
    raw_document = json.loads((PACKAGE_ROOT / "board.json").read_text())
    forbidden_keys = {"cueStyle", "claims", "semantics", "evidence", "artwork", "ui", "depthRangeMillimeters", "gripType", "features"}
    def keys(value: object) -> set[str]:
        if isinstance(value, dict): return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list): return set().union(*(keys(item) for item in value))
        return set()
    assert forbidden_keys.isdisjoint(keys(raw_document))
    assert {"semantics.json", "evidence.json", "artwork.json", "catalog.json"}.isdisjoint(path.name for path in PACKAGE_ROOT.rglob("*") if path.is_file())
