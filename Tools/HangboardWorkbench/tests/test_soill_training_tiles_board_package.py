from __future__ import annotations

from collections import Counter
import json
import math
import struct
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "soill-training-tiles"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
from board_package import load_board_package  # noqa: E402


EXPECTED_HOLDS = (
    ("jug-left", "jug"),
    ("jug-right", "jug"),
    ("top-sloper-outer-left", "sloper"),
    ("top-sloper-outer-right", "sloper"),
    ("top-sloper-inner-left", "sloper"),
    ("top-sloper-inner-right", "sloper"),
    ("middle-positive-edge-outer-left", "edge"),
    ("middle-positive-edge-outer-right", "edge"),
    ("middle-positive-edge-inner-left", "edge"),
    ("middle-positive-edge-inner-right", "edge"),
    ("bottom-flat-edge-outer-left", "edge"),
    ("bottom-flat-edge-outer-right", "edge"),
    ("bottom-flat-edge-middle-left", "edge"),
    ("bottom-flat-edge-middle-right", "edge"),
    ("bottom-flat-edge-inner-left", "edge"),
    ("bottom-flat-edge-inner-right", "edge"),
)
MIRRORED_PAIRS = (
    ("jug-left", "jug-right"),
    ("top-sloper-outer-left", "top-sloper-outer-right"),
    ("top-sloper-inner-left", "top-sloper-inner-right"),
    ("middle-positive-edge-outer-left", "middle-positive-edge-outer-right"),
    ("middle-positive-edge-inner-left", "middle-positive-edge-inner-right"),
    ("bottom-flat-edge-outer-left", "bottom-flat-edge-outer-right"),
    ("bottom-flat-edge-middle-left", "bottom-flat-edge-middle-right"),
    ("bottom-flat-edge-inner-left", "bottom-flat-edge-inner-right"),
)
AUDITED_LEFT_JUG_FRAME = (0.11, 0.3158, 0.045, 0.0792)
AUDITED_LEFT_JUG_COMMANDS = (
    ("move", (0.5, 0), None, None),
    ("curve", (0.99, 0.454545454545455), (0.75, 0), (0.95, 0.202020202020202)),
    ("curve", (0.67, 0.97979797979798), (1, 0.666666666666667), (0.88, 0.898989898989899)),
    ("curve", (0.22, 0.909090909090909), (0.6175, 1), (0.35, 0.98989898989899)),
    ("curve", (0.02, 0.424242424242424), (0.05, 0.797979797979798), (0, 0.616161616161616)),
    ("curve", (0.5, 0), (0.06, 0.191919191919192), (0.25, 0.01010101010101)),
    ("close", None, None, None),
)


def _point(value: object) -> tuple[float, float] | None:
    if value is None:
        return None
    assert isinstance(value, list)
    assert len(value) == 2
    x, y = value
    assert isinstance(x, (int, float))
    assert isinstance(y, (int, float))
    return x, y


def _points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (
            _point(command.get("to")),
            _point(command.get("control")),
            _point(command.get("control1")),
            _point(command.get("control2")),
        )
        if point is not None
    )


def _sample_cubic_loop(piece: dict[str, object]) -> tuple[tuple[float, float], ...]:
    shape = piece["shape"]
    assert isinstance(shape, dict)
    commands = shape["commands"]
    assert isinstance(commands, list)
    first = commands[0]
    assert isinstance(first, dict)
    start = _point(first.get("to"))
    assert start is not None
    current = start
    samples = [_canvas_point(piece, current)]
    for command in commands[1:]:
        assert isinstance(command, dict)
        if command["command"] != "curve":
            continue
        control1 = _point(command.get("control1"))
        control2 = _point(command.get("control2"))
        destination = _point(command.get("to"))
        assert control1 is not None
        assert control2 is not None
        assert destination is not None
        for index in range(1, 33):
            t = index / 32
            inverse_t = 1 - t
            local_point = (
                inverse_t**3 * current[0]
                + 3 * inverse_t**2 * t * control1[0]
                + 3 * inverse_t * t**2 * control2[0]
                + t**3 * destination[0],
                inverse_t**3 * current[1]
                + 3 * inverse_t**2 * t * control1[1]
                + 3 * inverse_t * t**2 * control2[1]
                + t**3 * destination[1],
            )
            samples.append(_canvas_point(piece, local_point))
        current = destination
    return tuple(samples)


def _canvas_point(
    piece: dict[str, object], point: tuple[float, float]
) -> tuple[float, float]:
    frame = piece["frame"]
    assert isinstance(frame, dict)
    return (
        frame["x"] + point[0] * frame["width"],
        frame["y"] + point[1] * frame["height"],
    )


def _contains_point(
    polygon: tuple[tuple[float, float], ...], point: tuple[float, float]
) -> bool:
    inside = False
    point_x, point_y = point
    for (start_x, start_y), (end_x, end_y) in zip(polygon, polygon[1:]):
        if (start_y > point_y) != (end_y > point_y):
            crossing_x = (end_x - start_x) * (point_y - start_y) / (
                end_y - start_y
            ) + start_x
            if point_x < crossing_x:
                inside = not inside
    return inside


def test_soill_training_tiles_preserve_sixteen_discrete_mirrored_contacts() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert board["id"] == "soill.training-tiles"
    assert board["manufacturer"] == "So iLL"
    assert board["name"] == "Training Tiles • So iLL x Meagan Martin"
    assert board["dimensions"] == "Not published by manufacturer"
    assert board_package._HOLD_KINDS == frozenset(
        {"jug", "edge", "pocket", "pinch", "sloper"}
    )
    primary = PACKAGE_ROOT / "assets" / "primary.png"
    png = primary.read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">I", png[8:12])[0] == 13
    assert png[12:16] == b"IHDR"
    width, height = struct.unpack(">II", png[16:24])
    assert width > 0
    assert height > 0
    assert math.isclose(board["aspectRatio"], width / height, abs_tol=1e-12)
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }

    assert tuple((hold["id"], hold["kind"]) for hold in board["holds"]) == EXPECTED_HOLDS
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "edge": 10,
        "sloper": 4,
        "jug": 2,
    }

    for hold in board["holds"]:
        assert len(hold["geometry"]) == 1
        assert "sizeMillimeters" not in hold
        assert "depthRangeMillimeters" not in hold
        assert "fingerCapacity" not in hold
        assert "features" not in hold
        assert hold.get("gripType") == (
            "sloper" if hold["kind"] == "sloper" else None
        )
        piece = hold["geometry"][0]
        shape = piece["shape"]
        assert shape["type"] == "path"
        commands = shape["commands"]
        assert commands[0]["command"] == "move"
        assert commands[-1]["command"] == "close"
        assert sum(command["command"] == "curve" for command in commands) >= 5
        frame = piece["frame"]
        assert 0 <= frame["x"] < frame["x"] + frame["width"] <= 1
        assert 0 <= frame["y"] < frame["y"] + frame["height"] <= 1
        assert frame["width"] * frame["height"] > 0
        assert all(
            0 <= coordinate <= 1
            for command in commands
            for point in _points(command)
            for coordinate in point
        )

    assert holds["jug-left"]["geometry"][0]["treatment"] == {
        "type": "recess",
        "rimInsetFraction": 0.1,
        "depth": "deep",
    }
    assert holds["jug-right"]["geometry"][0]["treatment"] == {
        "type": "recess",
        "rimInsetFraction": 0.1,
        "depth": "deep",
    }
    assert holds["jug-left"]["name"] == "Left jug"
    assert holds["jug-right"]["name"] == "Right jug"
    assert all(
        holds[hold_id]["geometry"][0]["treatment"]
        == {"type": "shelf", "rimInsetFraction": 0.1}
        for hold_id in (
            "middle-positive-edge-outer-left",
            "middle-positive-edge-outer-right",
            "middle-positive-edge-inner-left",
            "middle-positive-edge-inner-right",
        )
    )

    left_jug = holds["jug-left"]["geometry"][0]
    frame = left_jug["frame"]
    assert (
        frame["x"],
        frame["y"],
        frame["width"],
        frame["height"],
    ) == AUDITED_LEFT_JUG_FRAME
    shape = left_jug["shape"]
    assert tuple(
        (
            command["command"],
            _point(command.get("to")),
            _point(command.get("control1")),
            _point(command.get("control2")),
        )
        for command in shape["commands"]
    ) == AUDITED_LEFT_JUG_COMMANDS
    left_jug_curves = [
        command for command in shape["commands"] if command["command"] == "curve"
    ]
    for previous, following in zip(
        left_jug_curves, left_jug_curves[1:] + left_jug_curves[:1]
    ):
        previous_control2 = _point(previous.get("control2"))
        previous_destination = _point(previous.get("to"))
        following_control1 = _point(following.get("control1"))
        assert previous_control2 is not None
        assert previous_destination is not None
        assert following_control1 is not None
        incoming = (
            (previous_destination[0] - previous_control2[0]) * frame["width"],
            (previous_destination[1] - previous_control2[1]) * frame["height"],
        )
        outgoing = (
            (following_control1[0] - previous_destination[0]) * frame["width"],
            (following_control1[1] - previous_destination[1]) * frame["height"],
        )
        incoming_length = math.hypot(*incoming)
        outgoing_length = math.hypot(*outgoing)
        assert incoming_length > 0
        assert outgoing_length > 0
        assert (
            (incoming[0] * outgoing[0] + incoming[1] * outgoing[1])
            / (incoming_length * outgoing_length)
            > 0.97
        )
    sampled_left_jug = _sample_cubic_loop(left_jug)
    assert sampled_left_jug[0] == sampled_left_jug[-1]
    assert _contains_point(sampled_left_jug, (0.132, 0.355))
    assert all(
        holds[hold_id]["geometry"][0]["treatment"] == {"type": "surface"}
        for hold_id in (
            "bottom-flat-edge-outer-left",
            "bottom-flat-edge-outer-right",
            "bottom-flat-edge-middle-left",
            "bottom-flat-edge-middle-right",
            "bottom-flat-edge-inner-left",
            "bottom-flat-edge-inner-right",
        )
    )

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id]["geometry"][0]
        right = holds[right_id]["geometry"][0]
        left_frame = left["frame"]
        right_frame = right["frame"]
        assert math.isclose(
            right_frame["x"],
            1 - left_frame["x"] - left_frame["width"],
            abs_tol=1e-12,
        )
        assert math.isclose(right_frame["y"], left_frame["y"], abs_tol=1e-12)
        assert math.isclose(
            right_frame["width"], left_frame["width"], abs_tol=1e-12
        )
        assert math.isclose(
            right_frame["height"], left_frame["height"], abs_tol=1e-12
        )
        left_commands = left["shape"]["commands"]
        right_commands = right["shape"]["commands"]
        for left_command, right_command in zip(
            left_commands, right_commands, strict=True
        ):
            assert left_command["command"] == right_command["command"]
            for (left_x, left_y), (right_x, right_y) in zip(
                _points(left_command), _points(right_command), strict=True
            ):
                assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                assert math.isclose(right_y, left_y, abs_tol=1e-12)

    raw = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    forbidden = {"cueStyle", "semantics", "evidence", "claims", "ui"}

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(child) for child in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(child) for child in value))
        return set()

    assert forbidden.isdisjoint(keys(raw))
