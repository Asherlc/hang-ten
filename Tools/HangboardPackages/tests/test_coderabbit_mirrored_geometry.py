from __future__ import annotations

import json
from pathlib import Path

import pytest

from _board_package_helpers import document_contact_geometry

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
        ("round-sloper-3-left", "round-sloper-3-right"),
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

ESCAPE_UNLIMITED_SOURCE_PAIRS = {
    ("edge-45-left", "edge-45-right"): ("upper-left", "upper-right"),
    ("edge-20-left", "edge-20-right"): ("middle-left", "middle-right"),
    ("edge-15-left", "edge-15-right"): ("lower-left", "lower-right"),
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
    assert right_constraint == left_constraint or (
        isinstance(left_constraint, dict)
        and isinstance(right_constraint, dict)
        and right_constraint["shape"] == left_constraint["shape"]
        and right_constraint["rotationDegrees"] == pytest.approx(-left_constraint["rotationDegrees"])
    )

    left_commands = left["shape"]["commands"]
    right_commands = right["shape"]["commands"]
    assert len(right_commands) == len(left_commands)
    for left_command, right_command in zip(left_commands, right_commands, strict=True):
        assert right_command["command"] == left_command["command"]
        for field in ("to", "control", "control1", "control2"):
            if field in left_command:
                assert tuple(right_command[field]) == pytest.approx(_mirrored_point(left_command[field]))
            else:
                assert field not in right_command


@pytest.mark.parametrize("board_id", MIRRORED_PAIRS)
def test_coderabbit_flagged_pairs_preserve_mirrored_geometry(board_id: str) -> None:
    board = json.loads(
        (REPO_ROOT / "Hangboards" / board_id / "board.json").read_text(encoding="utf-8")
    )
    media = board["presentations"][0]["media"]
    if media["type"] == "model":
        descriptor = json.loads(
            (REPO_ROOT / "Hangboards" / board_id / media["descriptorPath"]).read_text(encoding="utf-8")
        )
        contacts = descriptor["contacts"]
        escape_unlimited_holds = None
        if board_id == "escape-unlimited":
            hold_map = json.loads(
                (
                    REPO_ROOT
                    / ".context"
                    / "migration"
                    / "escape-unlimited-board"
                    / "hold-map.json"
                ).read_text(encoding="utf-8")
            )
            escape_unlimited_holds = {hold["holdId"]: hold for hold in hold_map["holds"]}
        for left_id, right_id in MIRRORED_PAIRS[board_id]:
            left = contacts[left_id]
            right = contacts[right_id]
            assert not set(left["nodeIDs"]) & set(right["nodeIDs"])
            if board_id == "escape-unlimited":
                left_source_id, right_source_id = ESCAPE_UNLIMITED_SOURCE_PAIRS[(left_id, right_id)]
                assert escape_unlimited_holds is not None
                left_source_center = escape_unlimited_holds[left_source_id]["sourceCentreM"]
                right_source_center = escape_unlimited_holds[right_source_id]["sourceCentreM"]
                assert right_source_center[0] == pytest.approx(-left_source_center[0])
                assert right_source_center[1:] == pytest.approx(left_source_center[1:])
                bounds = descriptor["modelBounds"]
                for contact, source_center in ((left, left_source_center), (right, right_source_center)):
                    center = contact["center"]
                    contact_bounds = contact["facePlaneAABB"]
                    for bound in ("min", "max"):
                        assert isinstance(contact_bounds[bound], list)
                        assert len(contact_bounds[bound]) == 2
                    assert len(center) == 2
                    # Source X/Z become descriptor X/Y (horizontal/board-vertical).
                    for axis, source_axis in enumerate((0, 2)):
                        span = bounds["max"][axis] - bounds["min"][axis]
                        expected = (source_center[source_axis] - bounds["min"][axis]) / span
                        # Retained mesh centers differ by up to ~0.014 normalized units.
                        assert center[axis] == pytest.approx(expected, abs=0.015)
                        minimum = contact_bounds["min"][axis]
                        maximum = contact_bounds["max"][axis]
                        assert minimum <= maximum
                        assert minimum - 1e-6 <= center[axis] <= maximum + 1e-6
                # Retained GLB surface bounds are not exact AABB mirrors despite symmetric source centers.
                continue
            left_bounds = left["facePlaneAABB"]
            right_bounds = right["facePlaneAABB"]
            # The supplied Simulator meshes have submillimeter bilateral
            # tessellation differences; model AABBs are not authored raster paths.
            bounds = descriptor["modelBounds"]
            for axis in (0, 1):
                span = bounds["max"][axis] - bounds["min"][axis]
                tolerance = 0.0005 / span if board_id == "metolius-simulator-3d" else 1e-6
                for bound, opposite in (("min", "max"), ("max", "min")):
                    expected = 1 - left_bounds[opposite][axis] if axis == 0 else left_bounds[bound][axis]
                    assert right_bounds[bound][axis] == pytest.approx(expected, abs=tolerance)
        return
    geometry = document_contact_geometry(board)
    for left_id, right_id in MIRRORED_PAIRS[board_id]:
        left_geometry = geometry[left_id]
        right_geometry = geometry[right_id]
        assert len(right_geometry) == len(left_geometry)
        for left_piece, right_piece in zip(left_geometry, right_geometry, strict=True):
            _assert_mirrored_piece(left_piece, right_piece)
