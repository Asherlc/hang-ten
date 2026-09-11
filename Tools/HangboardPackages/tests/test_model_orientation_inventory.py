from __future__ import annotations

import math
from pathlib import Path

import pytest

from test_model_first_packages import write_model_package
from conftest import load_board_catalog_module


def _orientation() -> dict[str, object]:
    return {
        "pivot": "modelBoundsCenter",
        "rotations": {
            "reverse": [0, 1, 0, 0],
            "front": [0, 0, 0, 1],
        },
    }


def _positions() -> list[dict[str, object]]:
    return [
        {"id": "front", "presentationID": "primary", "holdIDs": ["hold-left"]},
        {"id": "reverse", "presentationID": "primary", "holdIDs": ["hold-right"]},
    ]


def test_model_orientation_is_normalized_and_membership_is_exact(tmp_path: Path) -> None:
    package = write_model_package(tmp_path, orientation=_orientation(), positions=_positions())
    board = load_board_catalog_module().load_board_package(package).board
    assert board.positions[0].hold_ids == ("hold-left",)
    assert tuple(board.presentations[0].media.orientation.rotations) == ("front", "reverse")
    assert board.hold_ids_for_position("reverse") == ("hold-right",)


def test_legacy_model_positions_materialize_complete_inventory(tmp_path: Path) -> None:
    package = write_model_package(tmp_path, orientation={
        "pivot": "modelBoundsCenter", "rotations": {"front": [0, 0, 0, 1]}
    }, positions=[
        {"id": "front", "presentationID": "primary"},
    ])
    board = load_board_catalog_module().load_board_package(package).board
    assert board.positions[0].hold_ids == ("hold-left", "hold-right")


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("pivot", "wrong", "orientation.pivot"),
        ("rotations", {"front": [0, 0, 0, 1], "unknown": [0, 1, 0, 0]}, "orientation.rotations"),
        ("rotations", {"front": [0, 0, 0, 1]}, "orientation.rotations"),
    ],
)
def test_model_orientation_rejects_invalid_rotation_inventory(
    tmp_path: Path, field: str, value: object, reason: str
) -> None:
    orientation = _orientation()
    orientation[field] = value
    with pytest.raises(ValueError, match=reason):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, orientation=orientation, positions=_positions())
        )


@pytest.mark.parametrize("quaternion", [[0, 0, 0, 0], [0, 0, 0, 2], [math.inf, 0, 0, 1], [0.1234567891, 0, 0, 1]])
def test_model_orientation_rejects_non_unit_or_noncanonical_quaternion(
    tmp_path: Path, quaternion: list[float]
) -> None:
    orientation = _orientation()
    orientation["rotations"] = {"front": quaternion, "reverse": [0, 1, 0, 0]}
    with pytest.raises(ValueError, match="orientation.rotations"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, orientation=orientation, positions=_positions())
        )


def test_model_orientation_rejects_overlapping_or_incomplete_hold_membership(tmp_path: Path) -> None:
    positions = [
        {"id": "front", "presentationID": "primary", "holdIDs": ["hold-left", "hold-right"]},
        {"id": "reverse", "presentationID": "primary", "holdIDs": ["hold-right"]},
    ]
    with pytest.raises(ValueError, match=r"positions\[1\]\.holdIDs"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, orientation=_orientation(), positions=positions)
        )


def test_model_orientation_and_suspension_are_mutually_exclusive(tmp_path: Path) -> None:
    fixture = {"base": "singleCordModel", "mutations": []}
    # The shared fixture is intentionally not copied here; this checks the closed
    # model-media contract using a minimal orientation-bearing package.
    with pytest.raises(ValueError, match="orientation and suspension are mutually exclusive"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, orientation=_orientation(), media_overrides={"suspension": {}})
        )
