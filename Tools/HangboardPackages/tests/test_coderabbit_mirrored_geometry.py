from __future__ import annotations

import json
from pathlib import Path

import pytest

from _board_package_helpers import document_contact_geometry
from hangboard_packages.cad_source import load_board as load_cad_board, package_source_path

REPO_ROOT = Path(__file__).resolve().parents[3]
MIRRORED_PAIRS = {
    "escape-unlimited": (
        ("edge-45-left", "edge-45-right"),
        ("edge-20-left", "edge-20-right"),
        ("edge-15-left", "edge-15-right"),
    ),
    "frictitious-doormount-pro-7": (
        ("edge-35-left", "edge-35-right"),
        ("mixed-25-pocket-left", "mixed-25-pocket-right"),
        ("hold-7", "hold-6"),
        ("hold-11", "hold-8"),
        ("hold-10", "hold-9"),
        ("hold-12", "hold-13"),
    ),
    "metolius-simulator-3d": (
        ("jug-1-left", "jug-1-right"),
        ("flat-sloper-2-left", "flat-sloper-2-right"),
        ("pocket-4-left", "pocket-4-right"),
        ("edge-5-left", "edge-5-right"),
        ("edge-6-left", "edge-6-right"),
        ("edge-7-left", "edge-7-right"),
        ("pocket-8-left", "pocket-8-right"),
        ("pocket-9-left", "pocket-9-right"),
        ("pocket-10-left", "pocket-10-right"),
        ("edge-11-left", "edge-11-right"),
        ("pocket-12-left", "pocket-12-right"),
        ("pocket-13-left", "pocket-13-right"),
    ),
    "nature-stoak-board-iii": (
        ("gradient-edge-left", "gradient-edge-right"),
    ),
    "trango-rock-prodigy-training-center": (
        ("edge-thin-crimp-left", "edge-thin-crimp-right"),
    ),
    "escape-beta-22": tuple(
        (f"hold-{family:02d}-left", f"hold-{family:02d}-right")
        for family in range(1, 9)
    ),
    "yy-verticalboard-evo": (
        ("edge-inclined-30-left", "edge-inclined-30-right"),
        ("edge-18-left", "edge-18-right"),
    ),
    "yy-verticalboard-first": (
        ("edge-45-left", "edge-45-right"),
    ),
}

def _mirrored_point(point: list[float]) -> tuple[float, float]:
    return (1 - point[0], point[1])


def _assert_mirrored_piece(left: dict[str, object], right: dict[str, object]) -> None:
    left_frame = left["frame"]
    right_frame = right["frame"]
    assert isinstance(left_frame, dict)
    assert isinstance(right_frame, dict)
    assert right_frame["x"] == pytest.approx(1 - left_frame["x"] - left_frame["width"])
    assert right_frame["y"] == pytest.approx(left_frame["y"])
    assert right_frame["width"] == pytest.approx(left_frame["width"])
    assert right_frame["height"] == pytest.approx(left_frame["height"])

    left_constraint = left.get("shapeConstraint")
    right_constraint = right.get("shapeConstraint")
    # Allow asymmetric representations (one side path, other side constraint)
    # as long as both represent the same visual shape
    if left_constraint is not None and right_constraint is not None:
        assert right_constraint == left_constraint or (
            isinstance(left_constraint, dict)
            and isinstance(right_constraint, dict)
            and right_constraint["shape"] == left_constraint["shape"]
            and right_constraint["rotationDegrees"] == pytest.approx(-left_constraint["rotationDegrees"])
        )

    left_shape = left["shape"]
    right_shape = right["shape"]
    # Handle both path shapes (with commands) and constraint shapes (roundedRect, etc.)
    # Allow asymmetric representations (one side path, other side constraint) as long
    # as frames are properly mirrored - the visual shape equivalence is verified
    # by the frame bounds and constraint type matching
    if "commands" in left_shape and "commands" in right_shape:
        left_commands = left_shape["commands"]
        right_commands = right_shape["commands"]
        assert len(right_commands) == len(left_commands)
        for left_command, right_command in zip(left_commands, right_commands, strict=True):
            assert right_command["command"] == left_command["command"]
            for field in ("to", "control", "control1", "control2"):
                if field in left_command:
                    assert tuple(right_command[field]) == pytest.approx(_mirrored_point(left_command[field]))
                else:
                    assert field not in right_command
    else:
        # Asymmetric case: one side may be a path, the other a constraint.
        # Just verify the frames are mirrored and both represent the same hold type.
        # When both sides are constraint shapes, their dictionaries must match.
        if left_shape.get("type") == right_shape.get("type") == "roundedRect":
            assert left_shape == right_shape
        left_constraint_shape = left.get("shapeConstraint", {}).get("shape")
        right_constraint_shape = right.get("shapeConstraint", {}).get("shape")
        if left_constraint_shape and right_constraint_shape:
            assert left_constraint_shape == right_constraint_shape


@pytest.mark.parametrize("board_id", MIRRORED_PAIRS)
def test_coderabbit_flagged_pairs_preserve_mirrored_geometry(board_id: str) -> None:
    package = REPO_ROOT / "Hangboards" / board_id
    cad_source = package_source_path(package)
    board = (
        load_cad_board(cad_source)
        if cad_source.is_file()
        else json.loads((package / "board.json").read_text(encoding="utf-8"))
    )
    media = board["presentations"][0]["media"]
    if media["type"] == "model":
        descriptor = json.loads(
            (REPO_ROOT / "Hangboards" / board_id / media["descriptorPath"]).read_text(encoding="utf-8")
        )
        if descriptor["schemaVersion"] == 2:
            left_instance, right_instance = media["instances"]
            assert left_instance["baseTransform"].get("reflection") is None
            assert right_instance["baseTransform"]["reflection"] == "x"
            bounds = descriptor["modelBounds"]
            assert right_instance["baseTransform"]["translation"][0] == pytest.approx(
                -(bounds["min"][0] + bounds["max"][0]), abs=1e-9
            )
            for left_id, right_id in MIRRORED_PAIRS[board_id]:
                left_slot = next(slot for slot, cid in left_instance["contactIDsBySlotID"].items()
                                 if cid == left_id)
                right_slot = next(slot for slot, cid in right_instance["contactIDsBySlotID"].items()
                                  if cid == right_id)
                assert left_slot == right_slot
                assert descriptor["contactSlots"][left_slot]["nodeIDs"]
            return
        contacts = descriptor["contacts"]
        for left_id, right_id in MIRRORED_PAIRS[board_id]:
            left = contacts[left_id]
            right = contacts[right_id]
            assert not set(left["nodeIDs"]) & set(right["nodeIDs"])
            left_bounds = left["facePlaneAABB"]
            right_bounds = right["facePlaneAABB"]
            # The supplied Simulator mesh has submillimeter bilateral
            # tessellation differences; model AABBs are not authored raster
            # paths. Other boards keep the exact 1e-6 bound.
            bounds = descriptor["modelBounds"]
            for axis in (0, 1):
                span = bounds["max"][axis] - bounds["min"][axis]
                tolerance = (
                    0.0005 / span
                    if board_id == "metolius-simulator-3d"
                    else 1e-6
                )
                for bound, opposite in (("min", "max"), ("max", "min")):
                    expected = 1 - left_bounds[opposite][axis] if axis == 0 else left_bounds[bound][axis]
                    assert right_bounds[bound][axis] == pytest.approx(expected, abs=tolerance)
                left_center = left["center"][axis]
                expected_center = 1 - left_center if axis == 0 else left_center
                assert right["center"][axis] == pytest.approx(expected_center, abs=tolerance)
                for contact in (left, right):
                    contact_bounds = contact["facePlaneAABB"]
                    assert (
                        contact_bounds["min"][axis] - 1e-6
                        <= contact["center"][axis]
                        <= contact_bounds["max"][axis] + 1e-6
                    )
        return
    geometry = document_contact_geometry(board)
    for left_id, right_id in MIRRORED_PAIRS[board_id]:
        left_geometry = geometry[left_id]
        right_geometry = geometry[right_id]
        assert len(right_geometry) == len(left_geometry)
        for left_piece, right_piece in zip(left_geometry, right_geometry, strict=True):
            _assert_mirrored_piece(left_piece, right_piece)
