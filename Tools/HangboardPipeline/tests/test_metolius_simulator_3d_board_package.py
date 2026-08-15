from __future__ import annotations

from collections import Counter
import math
from pathlib import Path

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "metolius-simulator-3d"
EXPECTED_HOLDS = (
    "jug-outer-left",
    "jug-outer-right",
    "sloper-flat-55-left",
    "sloper-flat-55-right",
    "sloper-round-65-left",
    "sloper-round-65-right",
    "pocket-30-three-left",
    "pocket-30-three-right",
    "edge-25-left",
    "edge-25-right",
    "edge-19-left",
    "edge-19-right",
    "edge-36-left",
    "edge-36-right",
    "pocket-15-three-left",
    "pocket-15-three-right",
    "pocket-35-three-left",
    "pocket-35-three-right",
    "pocket-17-three-left",
    "pocket-17-three-right",
    "edge-14-left",
    "edge-14-right",
    "pocket-30-two-left",
    "pocket-30-two-right",
    "pocket-14-two-left",
    "pocket-14-two-right",
    "jug-center",
    "pocket-50-three-center",
    "pocket-37-three-center",
    "pocket-28-two-center",
    "pocket-32-two-center",
)
MIRRORED_PAIRS = tuple(
    (EXPECTED_HOLDS[index], EXPECTED_HOLDS[index + 1])
    for index in range(0, 26, 2)
)
SURFACE_HOLDS = {
    "jug-outer-left",
    "jug-outer-right",
    "sloper-flat-55-left",
    "sloper-flat-55-right",
    "sloper-round-65-left",
    "sloper-round-65-right",
    "jug-center",
}
EXPECTED_SIZES = {
    "sloper-flat-55-left": 55,
    "sloper-flat-55-right": 55,
    "sloper-round-65-left": 65,
    "sloper-round-65-right": 65,
    "pocket-30-three-left": 30,
    "pocket-30-three-right": 30,
    "edge-25-left": 25,
    "edge-25-right": 25,
    "edge-19-left": 19,
    "edge-19-right": 19,
    "edge-36-left": 36,
    "edge-36-right": 36,
    "pocket-15-three-left": 15,
    "pocket-15-three-right": 15,
    "pocket-35-three-left": 35,
    "pocket-35-three-right": 35,
    "pocket-17-three-left": 17,
    "pocket-17-three-right": 17,
    "edge-14-left": 14,
    "edge-14-right": 14,
    "pocket-30-two-left": 30,
    "pocket-30-two-right": 30,
    "pocket-14-two-left": 14,
    "pocket-14-two-right": 14,
    "pocket-50-three-center": 50,
    "pocket-37-three-center": 37,
    "pocket-28-two-center": 28,
    "pocket-32-two-center": 32,
}


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def test_metolius_simulator_3d_audited_inventory_and_geometry() -> None:
    package = load_board_package(PACKAGE_ROOT)
    board = package.board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board.id == "metolius.simulator-3d"
    assert board.manufacturer == "Metolius"
    assert board.name == "Simulator 3D"
    assert board.facts["dimensions"] == "28 × 8.75 in (711 × 222 mm)"
    assert board.facts["aspectRatio"] == 3.2
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(holds) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in holds.values()) == {
        "pocket": 16,
        "edge": 8,
        "sloper": 4,
        "jug": 3,
    }

    assert {
        hold_id: holds[hold_id].size_millimeters for hold_id in EXPECTED_SIZES
    } == EXPECTED_SIZES
    assert all(holds[hold_id].size_millimeters is None for hold_id in (
        "jug-outer-left", "jug-outer-right", "jug-center",
    ))
    assert all(
        holds[hold_id].finger_capacity == 3
        for hold_id in holds
        if "three" in hold_id
    )
    assert all(
        holds[hold_id].finger_capacity == 2
        for hold_id in holds
        if "two" in hold_id
    )
    assert all(
        holds[hold_id].finger_capacity is None
        for hold_id in holds
        if "three" not in hold_id and "two" not in hold_id
    )

    for hold_id, hold in holds.items():
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert any(command.command == "curve" for command in piece.shape.commands)
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0
        if hold_id in SURFACE_HOLDS:
            assert piece.treatment == {"type": "surface"}
        else:
            assert piece.treatment is not None
            assert piece.treatment["type"] == "recess"
            assert piece.treatment["depth"] in {"deep", "shallow"}

    for left_id, right_id in MIRRORED_PAIRS:
        left = holds[left_id].geometry[0]
        right = holds[right_id].geometry[0]
        assert math.isclose(
            right.frame.x,
            1 - left.frame.x - left.frame.width,
            abs_tol=1e-12,
        )
        assert right.frame.y == left.frame.y
        assert right.frame.width == left.frame.width
        assert right.frame.height == left.frame.height
        for left_command, right_command in zip(
            left.shape.commands,
            right.shape.commands,
            strict=True,
        ):
            assert left_command.command == right_command.command
            for (left_x, left_y), (right_x, right_y) in zip(
                _points(left_command),
                _points(right_command),
                strict=True,
            ):
                assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                assert math.isclose(right_y, left_y, abs_tol=1e-12)

    for hold_id in (
        "jug-center",
        "pocket-50-three-center",
        "pocket-37-three-center",
        "pocket-28-two-center",
        "pocket-32-two-center",
    ):
        frame = holds[hold_id].geometry[0].frame
        assert math.isclose(frame.x + frame.width / 2, 0.5, abs_tol=0.004)

    raw_document = (PACKAGE_ROOT / "board.json").read_text(encoding="utf-8")
    for forbidden in (
        "cueStyle", "evidence", "claims", "shortLabel", "detail",
        "artwork.json", "semantics.json", "catalog.json",
    ):
        assert forbidden not in raw_document
