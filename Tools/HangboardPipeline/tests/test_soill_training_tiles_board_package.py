from __future__ import annotations

from collections import Counter
import json
import math
import struct
from pathlib import Path

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "soill-training-tiles"
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
AUDITED_LEFT_JUG_FRAME = (0.11, 0.315, 0.045, 0.08)
AUDITED_LEFT_JUG_COMMANDS = (
    ("move", (0.5, 0.01), None, None),
    ("curve", (0.99, 0.46), (0.75, 0.01), (0.95, 0.21)),
    ("curve", (0.67, 0.98), (1, 0.67), (0.88, 0.9)),
    ("curve", (0.22, 0.91), (0.6175, 1), (0.35, 0.99)),
    ("curve", (0.02, 0.43), (0.05, 0.8), (0, 0.62)),
    ("curve", (0.5, 0.01), (0.06, 0.2), (0.25, 0.02)),
    ("close", None, None, None),
)


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def _sample_cubic_loop(piece: object) -> tuple[tuple[float, float], ...]:
    commands = piece.shape.commands
    start = commands[0].to
    assert start is not None
    current = start
    samples = [_canvas_point(piece, current)]
    for command in commands[1:]:
        if command.command != "curve":
            continue
        assert command.control1 is not None
        assert command.control2 is not None
        assert command.to is not None
        for index in range(1, 33):
            t = index / 32
            inverse_t = 1 - t
            local_point = (
                inverse_t**3 * current[0]
                + 3 * inverse_t**2 * t * command.control1[0]
                + 3 * inverse_t * t**2 * command.control2[0]
                + t**3 * command.to[0],
                inverse_t**3 * current[1]
                + 3 * inverse_t**2 * t * command.control1[1]
                + 3 * inverse_t * t**2 * command.control2[1]
                + t**3 * command.to[1],
            )
            samples.append(_canvas_point(piece, local_point))
        current = command.to
    return tuple(samples)


def _canvas_point(piece: object, point: tuple[float, float]) -> tuple[float, float]:
    return (
        piece.frame.x + point[0] * piece.frame.width,
        piece.frame.y + point[1] * piece.frame.height,
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
    holds = {hold.id: hold for hold in board.holds}

    assert board.id == "soill.training-tiles"
    assert board.manufacturer == "So iLL"
    assert board.name == "Training Tiles • So iLL x Meagan Martin"
    assert board.facts["dimensions"] == "Not published by manufacturer"
    primary = PACKAGE_ROOT / "assets" / "primary.png"
    png = primary.read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">I", png[8:12])[0] == 13
    assert png[12:16] == b"IHDR"
    width, height = struct.unpack(">II", png[16:24])
    assert width > 0
    assert height > 0
    assert math.isclose(
        board.facts["aspectRatio"], width / height, abs_tol=1e-12
    )
    assert board.presentation_asset_path == "assets/primary.png"
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }

    assert tuple((hold.id, hold.kind) for hold in board.holds) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "edge": 10,
        "sloper": 4,
        "jug": 2,
    }

    for hold in board.holds:
        assert len(hold.geometry) == 1
        assert hold.size_millimeters is None
        assert hold.depth_range_millimeters is None
        assert hold.finger_capacity is None
        assert hold.features is None
        assert hold.grip_type == ("sloper" if hold.kind == "sloper" else None)
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert sum(command.command == "curve" for command in piece.shape.commands) >= 5
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0

    assert holds["jug-left"].geometry[0].treatment == {
        "type": "recess",
        "rimInsetFraction": 0.1,
        "depth": "deep",
    }
    assert holds["jug-right"].geometry[0].treatment == {
        "type": "recess",
        "rimInsetFraction": 0.1,
        "depth": "deep",
    }
    assert holds["jug-left"].name == "Left jug"
    assert holds["jug-right"].name == "Right jug"
    assert all(
        holds[hold_id].geometry[0].treatment
        == {"type": "shelf", "rimInsetFraction": 0.1}
        for hold_id in (
            "middle-positive-edge-outer-left",
            "middle-positive-edge-outer-right",
            "middle-positive-edge-inner-left",
            "middle-positive-edge-inner-right",
        )
    )

    left_jug = holds["jug-left"].geometry[0]
    assert (
        left_jug.frame.x,
        left_jug.frame.y,
        left_jug.frame.width,
        left_jug.frame.height,
    ) == AUDITED_LEFT_JUG_FRAME
    assert tuple(
        (command.command, command.to, command.control1, command.control2)
        for command in left_jug.shape.commands
    ) == AUDITED_LEFT_JUG_COMMANDS
    left_jug_curves = [
        command
        for command in left_jug.shape.commands
        if command.command == "curve"
    ]
    for previous, following in zip(
        left_jug_curves, left_jug_curves[1:] + left_jug_curves[:1]
    ):
        assert previous.control2 is not None
        assert previous.to is not None
        assert following.control1 is not None
        incoming = (
            (previous.to[0] - previous.control2[0]) * left_jug.frame.width,
            (previous.to[1] - previous.control2[1]) * left_jug.frame.height,
        )
        outgoing = (
            (following.control1[0] - previous.to[0]) * left_jug.frame.width,
            (following.control1[1] - previous.to[1]) * left_jug.frame.height,
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
        holds[hold_id].geometry[0].treatment == {"type": "surface"}
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
        left = holds[left_id].geometry[0]
        right = holds[right_id].geometry[0]
        assert math.isclose(
            right.frame.x,
            1 - left.frame.x - left.frame.width,
            abs_tol=1e-12,
        )
        assert math.isclose(right.frame.y, left.frame.y, abs_tol=1e-12)
        assert math.isclose(right.frame.width, left.frame.width, abs_tol=1e-12)
        assert math.isclose(right.frame.height, left.frame.height, abs_tol=1e-12)
        for left_command, right_command in zip(
            left.shape.commands, right.shape.commands, strict=True
        ):
            assert left_command.command == right_command.command
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
