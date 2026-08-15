from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import struct
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "yy-verticalboard-light"
BOARD_PATH = PACKAGE_ROOT / "board.json"
PRIMARY_PATH = PACKAGE_ROOT / "assets" / "primary.png"
CANVAS_SIZE = (1774, 887)
SUPPORTED_HOLD_KINDS = {"jug", "edge", "pocket", "pinch", "sloper"}

sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


EXPECTED_BOARD = {
    "schemaVersion": 1,
    "id": "yy.verticalboard-light",
    "manufacturer": "YY Vertical",
    "name": "VerticalBoard Light",
    "subtitle": "Compact symmetrical poplar training board",
    "productURL": "https://www.yyvertical.com/en/products/verticalboard-light",
    "dimensions": "54 × 9 × 5 cm",
    "aspectRatio": 2.0,
    "presentation": {"assetPath": "assets/primary.png"},
}
EXPECTED_HOLDS = (
    ("outer-jug-left", "Left outer jug", "jug", None, None, None, None, ("jug",)),
    ("outer-jug-right", "Right outer jug", "jug", None, None, None, None, ("jug",)),
    ("sloper-30-left", "Left 30° sloper", "sloper", None, None, "sloper", None, None),
    ("sloper-20-center", "Center 20° sloper", "sloper", None, None, "sloper", None, None),
    ("sloper-30-right", "Right 30° sloper", "sloper", None, None, "sloper", None, None),
    ("edge-20-left", "Left 20 mm edge", "edge", 20, None, None, None, None),
    ("edge-20-right", "Right 20 mm edge", "edge", 20, None, None, None, None),
    ("edge-25-left", "Left 25 mm edge", "edge", 25, None, None, None, None),
    ("edge-25-right", "Right 25 mm edge", "edge", 25, None, None, None, None),
    ("edge-45-left", "Left 45 mm edge", "edge", 45, None, None, None, None),
    ("edge-45-right", "Right 45 mm edge", "edge", 45, None, None, None, None),
    ("edge-40-center", "Center 40 mm edge", "edge", 40, None, None, None, None),
)
EXPECTED_KIND_COUNTS = {"jug": 2, "sloper": 3, "edge": 7}
EXPECTED_TREATMENTS = {
    "outer-jug-left": {"type": "surface"},
    "outer-jug-right": {"type": "surface"},
    "sloper-30-left": {"type": "surface"},
    "sloper-20-center": {"type": "surface"},
    "sloper-30-right": {"type": "surface"},
    "edge-20-left": {"type": "recess", "rimInsetFraction": 0.09, "depth": "shallow"},
    "edge-20-right": {"type": "recess", "rimInsetFraction": 0.09, "depth": "shallow"},
    "edge-25-left": {"type": "recess", "rimInsetFraction": 0.09, "depth": "shallow"},
    "edge-25-right": {"type": "recess", "rimInsetFraction": 0.09, "depth": "shallow"},
    "edge-45-left": {"type": "recess", "rimInsetFraction": 0.09, "depth": "deep"},
    "edge-45-right": {"type": "recess", "rimInsetFraction": 0.09, "depth": "deep"},
    "edge-40-center": {"type": "recess", "rimInsetFraction": 0.09, "depth": "deep"},
}
MIRRORED_PAIRS = (
    ("outer-jug-left", "outer-jug-right"),
    ("sloper-30-left", "sloper-30-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-25-left", "edge-25-right"),
    ("edge-45-left", "edge-45-right"),
)
FORBIDDEN_KEYS = {
    "artwork",
    "catalog",
    "claims",
    "cue",
    "cueStyle",
    "evidence",
    "instruction",
    "material",
    "routines",
    "semanticHolds",
    "semantics",
    "training",
    "ui",
    "weightGrams",
}


def _png_ihdr_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def _absolute_points(piece: dict[str, object]) -> tuple[tuple[float, float], ...]:
    frame = piece["frame"]
    shape = piece["shape"]
    assert isinstance(frame, dict) and isinstance(shape, dict)
    commands = shape["commands"]
    assert isinstance(commands, list)
    points: list[tuple[float, float]] = []
    for command in commands:
        assert isinstance(command, dict)
        for key in ("to", "control", "control1", "control2"):
            point = command.get(key)
            if point is None:
                continue
            assert isinstance(point, list) and len(point) == 2
            points.append(
                (
                    float(frame["x"]) + float(point[0]) * float(frame["width"]),
                    float(frame["y"]) + float(point[1]) * float(frame["height"]),
                )
            )
    return tuple(points)


def _flatten(piece: dict[str, object], steps: int = 32) -> list[tuple[float, float]]:
    frame = piece["frame"]
    shape = piece["shape"]
    assert isinstance(frame, dict) and isinstance(shape, dict)
    commands = shape["commands"]
    assert isinstance(commands, list)
    points: list[tuple[float, float]] = []
    current: tuple[float, float] | None = None
    first: tuple[float, float] | None = None
    for command in commands:
        assert isinstance(command, dict)
        name = command["command"]
        if name == "move":
            current = tuple(float(value) for value in command["to"])
            first = current
            points.append(current)
        elif name == "curve":
            assert current is not None
            control1 = tuple(float(value) for value in command["control1"])
            control2 = tuple(float(value) for value in command["control2"])
            end = tuple(float(value) for value in command["to"])
            for index in range(1, steps + 1):
                t = index / steps
                inverse = 1 - t
                points.append(
                    (
                        inverse**3 * current[0]
                        + 3 * inverse**2 * t * control1[0]
                        + 3 * inverse * t**2 * control2[0]
                        + t**3 * end[0],
                        inverse**3 * current[1]
                        + 3 * inverse**2 * t * control1[1]
                        + 3 * inverse * t**2 * control2[1]
                        + t**3 * end[1],
                    )
                )
            current = end
        elif name == "close":
            assert first is not None
            if points[-1] != first:
                points.append(first)
        else:  # pragma: no cover - the package loader rejects unsupported commands.
            raise AssertionError(f"unexpected path command: {name}")
    return [
        (
            float(frame["x"]) + point[0] * float(frame["width"]),
            float(frame["y"]) + point[1] * float(frame["height"]),
        )
        for point in points
    ]


def _contains(polygon: list[tuple[float, float]], x: float, y: float) -> bool:
    inside = False
    previous_x, previous_y = polygon[-1]
    for current_x, current_y in polygon:
        if (current_y > y) != (previous_y > y) and x < (
            (previous_x - current_x) * (y - current_y) / (previous_y - current_y)
            + current_x
        ):
            inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def _orientation(
    start: tuple[float, float],
    end: tuple[float, float],
    point: tuple[float, float],
) -> float:
    return (end[0] - start[0]) * (point[1] - start[1]) - (
        end[1] - start[1]
    ) * (point[0] - start[0])


def _segments_intersect(
    first_start: tuple[float, float],
    first_end: tuple[float, float],
    second_start: tuple[float, float],
    second_end: tuple[float, float],
) -> bool:
    epsilon = 1e-12
    first_second_start = _orientation(first_start, first_end, second_start)
    first_second_end = _orientation(first_start, first_end, second_end)
    second_first_start = _orientation(second_start, second_end, first_start)
    second_first_end = _orientation(second_start, second_end, first_end)
    return (
        (first_second_start > epsilon) != (first_second_end > epsilon)
        and (first_second_start < -epsilon) != (first_second_end < -epsilon)
        and (second_first_start > epsilon) != (second_first_end > epsilon)
        and (second_first_start < -epsilon) != (second_first_end < -epsilon)
    )


def _assert_no_piece_overlaps(holds: list[dict[str, object]]) -> None:
    pieces = [
        (str(hold["id"]), piece_index, _flatten(piece))
        for hold in holds
        for piece_index, piece in enumerate(hold["geometry"])
    ]
    for index, (hold_id, piece_index, polygon) in enumerate(pieces):
        for other_hold_id, other_piece_index, other_polygon in pieces[index + 1 :]:
            intersections = [
                _segments_intersect(start, end, other_start, other_end)
                for start, end in zip(polygon, polygon[1:] + polygon[:1], strict=True)
                for other_start, other_end in zip(
                    other_polygon,
                    other_polygon[1:] + other_polygon[:1],
                    strict=True,
                )
            ]
            assert not any(intersections) and not _contains(
                other_polygon, *polygon[0]
            ) and not _contains(polygon, *other_polygon[0]), (
                f"{hold_id} piece {piece_index + 1} overlaps {other_hold_id} piece "
                f"{other_piece_index + 1}; selection would be ambiguous"
            )


def _recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_recursive_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_recursive_keys(child) for child in value))
    return set()


def test_yy_verticalboard_light_is_a_complete_canonical_workbench_package() -> None:
    assert _png_ihdr_size(PRIMARY_PATH) == CANVAS_SIZE
    assert BOARD_PATH.is_file(), "the primary-only YY Verticalboard Light draft is incomplete"
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}

    raw_board = json.loads(BOARD_PATH.read_text(encoding="utf-8"))
    assert set(raw_board) == set(EXPECTED_BOARD) | {"holds"}
    assert {key: raw_board[key] for key in EXPECTED_BOARD} == EXPECTED_BOARD
    assert raw_board["aspectRatio"] == pytest.approx(2.0, abs=1e-12)
    assert FORBIDDEN_KEYS.isdisjoint(_recursive_keys(raw_board))

    package = board_package.load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = board["holds"]
    assert isinstance(holds, list)
    assert tuple(
        (
            hold["id"],
            hold["name"],
            hold["kind"],
            hold.get("sizeMillimeters"),
            hold.get("depthRangeMillimeters"),
            hold.get("gripType"),
            hold.get("fingerCapacity"),
            tuple(hold["features"]) if "features" in hold else None,
        )
        for hold in holds
    ) == EXPECTED_HOLDS
    assert all(len(hold["geometry"]) == 1 for hold in holds)
    assert {
        hold["id"]: hold["geometry"][0].get("treatment") for hold in holds
    } == EXPECTED_TREATMENTS
    assert set(hold["kind"] for hold in holds) <= SUPPORTED_HOLD_KINDS
    assert Counter(hold["kind"] for hold in holds) == EXPECTED_KIND_COUNTS
    assert [
        hold["sizeMillimeters"] for hold in holds if hold["kind"] == "edge"
    ] == [20, 20, 25, 25, 45, 45, 40]

    holds_by_id = {hold["id"]: hold for hold in holds}
    for left_id, right_id in MIRRORED_PAIRS:
        left = holds_by_id[left_id]
        right = holds_by_id[right_id]
        left_piece = left["geometry"][0]
        right_piece = right["geometry"][0]
        assert isinstance(left_piece, dict) and isinstance(right_piece, dict)
        assert [command["command"] for command in left_piece["shape"]["commands"]] == [
            command["command"] for command in right_piece["shape"]["commands"]
        ]
        for (left_x, left_y), (right_x, right_y) in zip(
            _absolute_points(left_piece), _absolute_points(right_piece), strict=True
        ):
            assert right_x == pytest.approx(1 - left_x, abs=1e-12)
            assert right_y == pytest.approx(left_y, abs=1e-12)

    all_points = [
        point
        for hold in holds
        for piece in hold["geometry"]
        for point in _absolute_points(piece)
    ]
    assert min(point[0] for point in all_points) == pytest.approx(
        0.002059523809524, abs=1e-12
    )
    assert min(point[1] for point in all_points) == pytest.approx(0.0, abs=1e-12)
    assert max(point[0] for point in all_points) == pytest.approx(
        0.997940476190476, abs=1e-12
    )
    assert max(point[1] for point in all_points) == pytest.approx(0.95, abs=1e-12)
    assert all(0 <= coordinate <= 1 for point in all_points for coordinate in point)
    _assert_no_piece_overlaps(holds)
