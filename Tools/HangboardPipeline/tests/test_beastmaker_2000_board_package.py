from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "Tools" / "HangboardWorkbench"))

from board_package import load_board_package


PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "beastmaker-2000"
EXPECTED_HOLDS = (
    *(f"top-sloper-{index}" for index in range(1, 6)),
    *(f"front-upper-{index}" for index in range(1, 3)),
    *(f"front-middle-{index}" for index in range(1, 10)),
    *(f"front-lower-{index}" for index in range(1, 10)),
)
EXPECTED_KINDS = {
    **{f"top-sloper-{index}": "sloper" for index in range(1, 6)},
    "front-upper-1": "pocket",
    "front-upper-2": "pocket",
    "front-middle-1": "edge",
    "front-middle-2": "pocket",
    "front-middle-3": "pocket",
    "front-middle-4": "pocket",
    "front-middle-5": "jug",
    "front-middle-6": "pocket",
    "front-middle-7": "pocket",
    "front-middle-8": "pocket",
    "front-middle-9": "edge",
    "front-lower-1": "edge",
    "front-lower-2": "pocket",
    "front-lower-3": "pocket",
    "front-lower-4": "pocket",
    "front-lower-5": "edge",
    "front-lower-6": "pocket",
    "front-lower-7": "pocket",
    "front-lower-8": "pocket",
    "front-lower-9": "edge",
}
MIRRORED_PAIRS = (
    ("top-sloper-1", "top-sloper-5"),
    ("top-sloper-2", "top-sloper-4"),
    ("front-upper-1", "front-upper-2"),
    *((f"front-middle-{left}", f"front-middle-{10 - left}") for left in range(1, 5)),
    *((f"front-lower-{left}", f"front-lower-{10 - left}") for left in range(1, 5)),
)
CANONICAL_EXPECTATIONS = {
    "top-sloper-2": {
        "frame": {"x": 0.198435, "y": 0.151934, "width": 0.16180956, "height": 0.151934},
        "shapeType": "path",
        "commandSchema": (
            ("move", frozenset({"to"})),
            ("line", frozenset({"to"})),
            ("curve", frozenset({"control1", "control2", "to"})),
            ("curve", frozenset({"control1", "control2", "to"})),
            ("curve", frozenset({"control1", "control2", "to"})),
            ("close", frozenset()),
        ),
        "localPoints": (
            (0.04040404040404041, 0.0), (0.98989898989899, 0.0),
            (0.9595959595959596, 0.96), (1.0, 0.28),
            (0.98989898989899, 0.71), (0.0, 0.96),
            (0.7272727272727273, 1.0), (0.25252525252525254, 1.0),
            (0.04040404040404041, 0.0), (0.0, 0.66),
            (0.010101010101010102, 0.26),
        ),
        "reviewedAbsolutePoints": (
            (0.20497276, 0.151934), (0.35861012000000003, 0.151934),
            (0.3537068, 0.29779064), (0.36024456, 0.19447552),
            (0.35861012000000003, 0.25980714000000005), (0.198435, 0.29779064),
            (0.31611468, 0.303868), (0.239296, 0.303868),
            (0.20497276, 0.151934), (0.198435, 0.25221044000000004),
            (0.20006944, 0.19143684000000002),
        ),
        "reviewedBounds": (0.198435, 0.151934, 0.36024456, 0.303868),
    },
    "top-sloper-3": {
        "frame": {"x": 0.3585632, "y": 0.150552, "width": 0.2828736, "height": 0.11326},
        "shapeType": "path",
        "commandSchema": (
            ("move", frozenset({"to"})),
            ("curve", frozenset({"control1", "control2", "to"})),
            ("curve", frozenset({"control1", "control2", "to"})),
            ("curve", frozenset({"control1", "control2", "to"})),
            ("curve", frozenset({"control1", "control2", "to"})),
            ("close", frozenset()),
        ),
        "localPoints": (
            (0.005208333333333335, 0.0), (0.9947916666666666, 0.0),
            (0.2604166666666667, 0.0), (0.7395833333333334, 0.0),
            (0.9947916666666666, 0.9), (1.0, 0.22), (1.0, 0.62),
            (0.005208333333333335, 0.9), (0.75, 1.0),
            (0.25000000000000006, 1.0), (0.005208333333333335, 0.0),
            (0.0, 0.62), (0.0, 0.22),
        ),
        "reviewedAbsolutePoints": (
            (0.3600365, 0.150552), (0.6399634999999999, 0.150552),
            (0.43222819999999995, 0.150552), (0.5677717999999999, 0.150552),
            (0.6399634999999999, 0.252486), (0.6414367999999999, 0.1754692),
            (0.6414367999999999, 0.2207732), (0.3600365, 0.252486),
            (0.5707184, 0.263812), (0.4292816, 0.263812),
            (0.3600365, 0.150552), (0.35856319999999997, 0.2207732),
            (0.35856319999999997, 0.1754692),
        ),
        "reviewedBounds": (0.3585632, 0.150552, 0.6414368, 0.263812),
    },
    "top-sloper-4": {
        "frame": {"x": 0.63975544, "y": 0.151934, "width": 0.16180956, "height": 0.151934},
        "shapeType": "path",
        "commandSchema": (
            ("move", frozenset({"to"})),
            ("line", frozenset({"to"})),
            ("curve", frozenset({"control1", "control2", "to"})),
            ("curve", frozenset({"control1", "control2", "to"})),
            ("curve", frozenset({"control1", "control2", "to"})),
            ("close", frozenset()),
        ),
        "localPoints": (
            (0.010101010101010102, 0.0), (0.9595959595959596, 0.0),
            (1.0, 0.96), (0.98989898989899, 0.26), (1.0, 0.66),
            (0.04040404040404041, 0.96), (0.7474747474747475, 1.0),
            (0.27272727272727276, 1.0), (0.010101010101010102, 0.0),
            (0.010101010101010102, 0.71), (0.0, 0.28),
        ),
        "reviewedAbsolutePoints": (
            (0.6413898800000001, 0.151934), (0.79502724, 0.151934),
            (0.8015650000000001, 0.29779064), (0.7999305600000001, 0.19143684000000002),
            (0.8015650000000001, 0.25221044000000004), (0.6462932, 0.29779064),
            (0.760704, 0.303868), (0.68388532, 0.303868),
            (0.6413898800000001, 0.151934), (0.6413898800000001, 0.25980714000000005),
            (0.6397554400000001, 0.19447552),
        ),
        "reviewedBounds": (0.63975544, 0.151934, 0.801565, 0.303868),
    },
}
AUTHORIZED_CANONICAL_HOLDS = frozenset(CANONICAL_EXPECTATIONS)
REVIEWED_IMMUTABLE_DIGEST = "5929c66200342b6a322e6c604784d7f78e160bbf4b7091d72e6e77bc974ad975"


def reviewed_immutable_digest(board: dict[str, object]) -> str:
    """Hash reviewed structure after replacing only authorized mutable subtrees."""
    immutable = json.loads(json.dumps(board))
    for hold in immutable["holds"]:
        if hold["id"] in AUTHORIZED_CANONICAL_HOLDS:
            assert len(hold["geometry"]) == 1
            piece = hold["geometry"][0]
            piece["frame"] = f"__canonical_frame__:{hold['id']}"
            piece["shape"] = f"__canonical_shape__:{hold['id']}"
    canonical_json = json.dumps(
        immutable, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical_json.encode()).hexdigest()


def command_points(piece: dict[str, object]) -> list[tuple[float, float]]:
    frame = piece["frame"]
    shape = piece["shape"]
    assert isinstance(frame, dict)
    assert isinstance(shape, dict)
    points = []
    for command in shape["commands"]:
        assert isinstance(command, dict)
        for attribute in ("to", "control", "control1", "control2"):
            point = command.get(attribute)
            if point is not None:
                assert isinstance(point, list)
                points.append(
                    (
                        frame["x"] + point[0] * frame["width"],
                        frame["y"] + point[1] * frame["height"],
                    )
                )
    return points


def local_command_points(piece: dict[str, object]) -> list[tuple[float, float]]:
    shape = piece["shape"]
    assert isinstance(shape, dict)
    points = []
    for command in shape["commands"]:
        assert isinstance(command, dict)
        for attribute in ("to", "control", "control1", "control2"):
            point = command.get(attribute)
            if point is not None:
                assert isinstance(point, list)
                points.append((point[0], point[1]))
    return points


def assert_point_sequences(
    actual: list[tuple[float, float]], expected: tuple[tuple[float, float], ...]
) -> None:
    assert len(actual) == len(expected)
    for actual_point, expected_point in zip(actual, expected, strict=True):
        assert actual_point == pytest.approx(expected_point, abs=1e-12)


def test_beastmaker_2000_canonical_frames_preserve_reviewed_canvas_geometry() -> None:
    board = json.loads((PACKAGE_ROOT / "board.json").read_text())
    holds = {hold["id"]: hold for hold in board["holds"]}

    for hold_id, expected in CANONICAL_EXPECTATIONS.items():
        piece = holds[hold_id]["geometry"][0]
        assert piece["frame"] == pytest.approx(expected["frame"], abs=1e-12)
        assert piece["shape"]["type"] == expected["shapeType"]
        assert tuple(
            (
                command["command"],
                frozenset(key for key in command if key != "command"),
            )
            for command in piece["shape"]["commands"]
        ) == expected["commandSchema"]
        assert_point_sequences(local_command_points(piece), expected["localPoints"])
        assert_point_sequences(command_points(piece), expected["reviewedAbsolutePoints"])
        actual_points = command_points(piece)
        actual_bounds = (
            min(x for x, _ in actual_points),
            min(y for _, y in actual_points),
            max(x for x, _ in actual_points),
            max(y for _, y in actual_points),
        )
        assert actual_bounds == pytest.approx(expected["reviewedBounds"], abs=1e-12)


def test_beastmaker_2000_reviewed_immutable_structure_is_preserved() -> None:
    board = json.loads((PACKAGE_ROOT / "board.json").read_text())

    assert reviewed_immutable_digest(board) == REVIEWED_IMMUTABLE_DIGEST


def test_beastmaker_2000_inventory_paths_and_symmetry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert tuple(holds) == EXPECTED_HOLDS
    assert {hold_id: hold["kind"] for hold_id, hold in holds.items()} == EXPECTED_KINDS
    assert Counter(hold["kind"] for hold in holds.values()) == {
        "sloper": 5,
        "edge": 5,
        "pocket": 14,
        "jug": 1,
    }

    assert sorted(
        str(path.relative_to(PACKAGE_ROOT))
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file()
    ) == ["assets/primary.png", "board.json"]

    for hold in holds.values():
        assert len(hold["geometry"]) == 1
        piece = hold["geometry"][0]
        assert piece["shape"]["type"] == "path"
        assert piece["shape"]["commands"][0]["command"] == "move"
        assert piece["shape"]["commands"][-1]["command"] == "close"
        assert len(piece["shape"]["commands"]) >= 6
        frame = piece["frame"]
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert "sizeMillimeters" not in hold
        assert "depthRangeMillimeters" not in hold
        assert "gripType" not in hold
        assert "fingerCapacity" not in hold
        assert "features" not in hold

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id]["geometry"][0]["frame"]
        right = holds[right_id]["geometry"][0]["frame"]
        assert right["x"] == pytest.approx(1 - left["x"] - left["width"], abs=1e-6)
        assert right["y"] == pytest.approx(left["y"], abs=1e-6)
        assert right["width"] == pytest.approx(left["width"], abs=1e-6)
        assert right["height"] == pytest.approx(left["height"], abs=1e-6)

        def command_points(hold_id: str) -> list[tuple[float, float]]:
            piece = holds[hold_id]["geometry"][0]
            frame = piece["frame"]
            points = []
            for command in piece["shape"]["commands"]:
                for attribute in ("to", "control", "control1", "control2"):
                    point = command.get(attribute)
                    if point is not None:
                        points.append(
                            (
                                frame["x"] + point[0] * frame["width"],
                                frame["y"] + point[1] * frame["height"],
                            )
                        )
            return points

        reflected_left = [(1 - x, y) for x, y in command_points(left_id)]
        actual_right = command_points(right_id)
        assert all(
            any(
                right_x == pytest.approx(left_x, abs=1e-6)
                and right_y == pytest.approx(left_y, abs=1e-6)
                for right_x, right_y in actual_right
            )
            for left_x, left_y in reflected_left
        )
        assert all(
            any(
                left_x == pytest.approx(right_x, abs=1e-6)
                and left_y == pytest.approx(right_y, abs=1e-6)
                for left_x, left_y in reflected_left
            )
            for right_x, right_y in actual_right
        )
