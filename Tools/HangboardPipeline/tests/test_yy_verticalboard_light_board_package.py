from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw
import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "yy-verticalboard-light"
BOARD_PATH = PACKAGE_ROOT / "board.json"
PRIMARY_PATH = PACKAGE_ROOT / "assets" / "primary.png"
RUNTIME_CANVAS_SIZE = (1680, 280)

EXPECTED_HOLDS = (
    ("outer-jug-left", "jug", None, 4),
    ("outer-jug-right", "jug", None, 4),
    ("sloper-30-left", "sloper", None, 1),
    ("sloper-20-center", "sloper", None, 1),
    ("sloper-30-right", "sloper", None, 1),
    ("edge-20-left", "edge", 20, 1),
    ("edge-20-right", "edge", 20, 1),
    ("edge-25-left", "edge", 25, 1),
    ("edge-25-right", "edge", 25, 1),
    ("edge-45-left", "edge", 45, 1),
    ("edge-45-right", "edge", 45, 1),
    ("edge-40-center", "edge", 40, 1),
)

MIRRORED_PAIRS = (
    ("outer-jug-left", "outer-jug-right"),
    ("sloper-30-left", "sloper-30-right"),
    ("edge-20-left", "edge-20-right"),
    ("edge-25-left", "edge-25-right"),
    ("edge-45-left", "edge-45-right"),
)


def _command_points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def _assert_exact_global_mirror(left: object, right: object) -> None:
    assert right.frame.x == pytest.approx(
        1 - left.frame.x - left.frame.width, abs=1e-12
    ), "a mirrored contact moved horizontally and would highlight the wrong cavity"
    assert right.frame.y == pytest.approx(
        left.frame.y, abs=1e-12
    ), "a mirrored contact moved vertically and broke the physical pair"
    assert right.frame.width == pytest.approx(left.frame.width, abs=1e-12)
    assert right.frame.height == pytest.approx(left.frame.height, abs=1e-12)
    assert right.treatment == left.treatment, (
        "a mirrored contact changed physical surface treatment"
    )
    assert [command.command for command in right.shape.commands] == [
        command.command for command in left.shape.commands
    ], "a mirrored contact changed path topology"

    for left_command, right_command in zip(
        left.shape.commands, right.shape.commands, strict=True
    ):
        for (left_x, left_y), (right_x, right_y) in zip(
            _command_points(left_command),
            _command_points(right_command),
            strict=True,
        ):
            assert right_x == pytest.approx(1 - left_x, abs=1e-12)
            assert right_y == pytest.approx(left_y, abs=1e-12)


def _cubic(
    start: tuple[float, float],
    control1: tuple[float, float],
    control2: tuple[float, float],
    end: tuple[float, float],
    steps: int = 32,
) -> list[tuple[float, float]]:
    points = []
    for index in range(1, steps + 1):
        t = index / steps
        inverse = 1 - t
        points.append(
            (
                inverse**3 * start[0]
                + 3 * inverse**2 * t * control1[0]
                + 3 * inverse * t**2 * control2[0]
                + t**3 * end[0],
                inverse**3 * start[1]
                + 3 * inverse**2 * t * control1[1]
                + 3 * inverse * t**2 * control2[1]
                + t**3 * end[1],
            )
        )
    return points


def _flatten(piece: object) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    current: tuple[float, float] | None = None
    first: tuple[float, float] | None = None
    for command in piece.shape.commands:
        if command.command == "move":
            assert command.to is not None
            current = command.to
            first = current
            points.append(current)
        elif command.command == "line":
            assert command.to is not None
            current = command.to
            points.append(current)
        elif command.command == "quad":
            assert current is not None and command.control is not None
            assert command.to is not None
            control1 = (
                current[0] + (2 / 3) * (command.control[0] - current[0]),
                current[1] + (2 / 3) * (command.control[1] - current[1]),
            )
            control2 = (
                command.to[0] + (2 / 3) * (command.control[0] - command.to[0]),
                command.to[1] + (2 / 3) * (command.control[1] - command.to[1]),
            )
            points.extend(_cubic(current, control1, control2, command.to))
            current = command.to
        elif command.command == "curve":
            assert current is not None and command.control1 is not None
            assert command.control2 is not None and command.to is not None
            points.extend(
                _cubic(current, command.control1, command.control2, command.to)
            )
            current = command.to
        elif command.command == "close":
            assert first is not None
            if points[-1] != first:
                points.append(first)
            current = first
        else:  # pragma: no cover - the canonical loader already rejects this
            raise AssertionError(f"unsupported path command: {command.command}")

    return [
        (
            piece.frame.x + x * piece.frame.width,
            piece.frame.y + y * piece.frame.height,
        )
        for x, y in points
    ]


def _bounds(piece: object) -> tuple[float, float, float, float]:
    points = _flatten(piece)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _assert_jug_surrounds_edge(jug: object, edge: object) -> None:
    top, outside, bottom, inside = jug.geometry
    edge_left, edge_top, edge_right, edge_bottom = _bounds(edge.geometry[0])
    top_left, _top_y, top_right, top_bottom = _bounds(top)
    bottom_left, bottom_top, bottom_right, _bottom_y = _bounds(bottom)
    left_side, right_side = sorted(
        (_bounds(outside), _bounds(inside)), key=lambda bounds: bounds[0]
    )
    _left_x, left_top, left_right, left_bottom = left_side
    right_left, right_top, _right_x, right_bottom = right_side

    assert top_bottom < edge_top, "the top jug surface intrudes into its 20 mm edge"
    assert bottom_top > edge_bottom, (
        "the bottom jug surface intrudes into its 20 mm edge"
    )
    assert left_right < edge_left, (
        "the outside jug surface intrudes into its 20 mm edge"
    )
    assert right_left > edge_right, (
        "the inside jug surface intrudes into its 20 mm edge"
    )
    assert top_left < edge_left and top_right > edge_right
    assert bottom_left < edge_left and bottom_right > edge_right
    assert left_top < edge_top and left_bottom > edge_bottom
    assert right_top < edge_top and right_bottom > edge_bottom


def _assert_no_piece_overlaps(board: object) -> None:
    width, height = RUNTIME_CANVAS_SIZE
    occupied = Image.new("1", (width, height), 0)
    for hold in board.holds:
        for piece_index, piece in enumerate(hold.geometry):
            mask = Image.new("1", (width, height), 0)
            polygon = [
                (round(x * (width - 1)), round(y * (height - 1)))
                for x, y in _flatten(piece)
            ]
            ImageDraw.Draw(mask).polygon(polygon, fill=1)
            overlap = ImageChops.logical_and(occupied, mask)
            overlaps = sum(overlap.get_flattened_data())
            assert overlaps == 0, (
                f"{hold.id} piece {piece_index + 1} overlaps another contact by "
                f"{overlaps} pixels, making selection ambiguous"
            )
            occupied = ImageChops.logical_or(occupied, mask)


def _assert_runtime_board_coordinate_contract(board: object) -> None:
    frames = [piece.frame for hold in board.holds for piece in hold.geometry]
    runtime_envelope = (
        min(frame.x for frame in frames),
        min(frame.y for frame in frames),
        max(frame.x + frame.width for frame in frames),
        max(frame.y + frame.height for frame in frames),
    )
    assert runtime_envelope == pytest.approx(
        (0.0, 0.0, 1.0, 0.95), rel=0, abs=1e-12
    ), (
        "the selectable map is not normalized to the full 6:1 runtime board; "
        "source-image padding would compress fills, highlights, and hit targets"
    )

    slopers = [hold for hold in board.holds if hold.kind == "sloper"]
    assert max(
        piece.frame.y + piece.frame.height
        for hold in slopers
        for piece in hold.geometry
    ) < 0.4, "the top sloper surfaces moved into the runtime board's face row"

    lower_edges = [
        hold
        for hold in board.holds
        if hold.id in {
            "edge-25-left",
            "edge-25-right",
            "edge-45-left",
            "edge-45-right",
            "edge-40-center",
        }
    ]
    assert min(
        piece.frame.y for hold in lower_edges for piece in hold.geometry
    ) > 0.7, "the lower edge cavities moved out of the runtime board's lower row"


def test_yy_verticalboard_light_preserves_source_backed_package_contract() -> None:
    assert BOARD_PATH.is_file(), (
        "Hangboards/yy-verticalboard-light/board.json is missing; the draft is not "
        "directly discoverable"
    )
    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {
        "assets",
        "board.json",
    }, "a sidecar or extra root entry would violate direct-package discovery"
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }, "a duplicate/source raster would be bundled as unintended app content"

    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert board.id == "yy.verticalboard-light"
    assert board.manufacturer == "YY Vertical"
    assert board.name == "VerticalBoard Light"
    assert board.facts["subtitle"] == "Compact symmetrical poplar training board"
    assert board.facts["dimensions"] == "54 × 9 × 5 cm"
    assert math.isclose(board.facts["aspectRatio"], 54 / 9, abs_tol=1e-12), (
        "the physical display ratio no longer matches the official dimensions"
    )
    assert board.facts["productURL"] == (
        "https://www.yyvertical.com/en/products/verticalboard-light"
    )
    assert board.presentation_asset_path == "assets/primary.png"

    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters, len(hold.geometry))
        for hold in board.holds
    ) == EXPECTED_HOLDS, (
        "the labeled twelve-contact layout or the split jug-piece inventory changed"
    )
    assert Counter(hold.kind for hold in board.holds) == {
        "edge": 7,
        "sloper": 3,
        "jug": 2,
    }, "a physical contact was reclassified or silently added/removed"
    assert sum(len(hold.geometry) for hold in board.holds) == 18, (
        "the expected ten single-piece contacts plus two four-piece jugs changed"
    )
    assert [
        hold.size_millimeters for hold in board.holds if hold.kind == "edge"
    ] == [20, 20, 25, 25, 45, 45, 40], (
        "an official 20/25/45/40 mm edge label was lost or assigned to the wrong hold"
    )

    for hold in board.holds:
        assert hold.finger_capacity is None, (
            f"{hold.id} invents an unsupported finger capacity"
        )
        assert hold.depth_range_millimeters is None, (
            f"{hold.id} turns a labeled size into an unsupported depth range"
        )
        if hold.kind == "sloper":
            assert hold.grip_type == "sloper"
            assert hold.features is None
        elif hold.kind == "jug":
            assert hold.grip_type is None
            assert hold.features == ("jug",)
        else:
            assert hold.grip_type is None
            assert hold.features is None

        for piece in hold.geometry:
            assert piece.shape.type == "path", (
                f"{hold.id} regressed to a coarse primitive instead of calibrated geometry"
            )
            assert piece.shape.commands[0].command == "move"
            assert piece.shape.commands[-1].command == "close"
            assert any(command.command == "curve" for command in piece.shape.commands), (
                f"{hold.id} lost its rounded source-visible boundary"
            )
            assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
            assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1

    for left_id, right_id in MIRRORED_PAIRS:
        assert len(holds[left_id].geometry) == len(holds[right_id].geometry)
        for left_piece, right_piece in zip(
            holds[left_id].geometry, holds[right_id].geometry, strict=True
        ):
            _assert_exact_global_mirror(left_piece, right_piece)

    _assert_jug_surrounds_edge(holds["outer-jug-left"], holds["edge-20-left"])
    _assert_jug_surrounds_edge(holds["outer-jug-right"], holds["edge-20-right"])
    _assert_runtime_board_coordinate_contract(board)
    _assert_no_piece_overlaps(board)

    raw_document = json.loads(BOARD_PATH.read_text(encoding="utf-8"))
    forbidden_keys = {
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

    def recursive_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(
                *(recursive_keys(child) for child in value.values())
            )
        if isinstance(value, list):
            return set().union(*(recursive_keys(child) for child in value))
        return set()

    assert forbidden_keys.isdisjoint(recursive_keys(raw_document)), (
        "retired sidecar, training, or unsupported factual content leaked into board.json"
    )
