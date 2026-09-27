"""Regression cover for the v2 published-depth derivation.

The v2 migration silently shipped two defects because nothing tested them: the
compiler dropped attachment nodes, and the published-depth guard read ContactID
(absent on a v2 object) so it passed vacuously. Attachment export needs FreeCAD
and is covered by ``test_metolius_native.py``; the depth derivation is pure and
is pinned here so a future agent does not rediscover the vacuous guard.
"""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY / "Tools" / "HangboardCAD"))

import compile_board  # noqa: E402


def _board(instances: list[dict]) -> dict:
    return {
        "schemaVersion": 3,
        "id": "unit.test",
        "contacts": [
            {"id": "p40-left", "depth": {"range": {"minimum": 40, "maximum": 40}}},
            {"id": "p40-right", "depth": {"range": {"minimum": 40, "maximum": 40}}},
            {"id": "p32-left", "depth": {"range": {"minimum": 32, "maximum": 32}}},
            {"id": "p32-right", "depth": {"range": {"minimum": 32, "maximum": 32}}},
            {"id": "jug-left", "gripTypes": []},
            {"id": "jug-right", "gripTypes": []},
        ],
        "presentations": [{"media": {"instances": instances}}],
    }


def test_v2_slot_depths_come_from_every_instance() -> None:
    board = _board(
        [
            {"contactIDsBySlotID": {"pocket-40": "p40-left", "pocket-32": "p32-left", "jug": "jug-left"}},
            {"contactIDsBySlotID": {"pocket-40": "p40-right", "pocket-32": "p32-right", "jug": "jug-right"}},
        ]
    )
    assert compile_board._declared_depths(board, 2) == {"pocket-40": 40.0, "pocket-32": 32.0}


def test_v2_slots_that_disagree_on_depth_fail_the_build() -> None:
    board = _board(
        [
            {"contactIDsBySlotID": {"pocket-32": "p32-left", "jug": "jug-left"}},
            {"contactIDsBySlotID": {"pocket-32": "p32-right", "jug": "jug-right"}},
        ]
    )
    for contact in board["contacts"]:
        if contact["id"] == "p32-right":
            contact["depth"] = {"range": {"minimum": 33, "maximum": 33}}
    with pytest.raises(compile_board.BuildError, match="conflicting published depths"):
        compile_board._declared_depths(board, 2)


def test_v1_depths_are_keyed_directly_by_contact_id() -> None:
    board = {
        "schemaVersion": 3,
        "id": "unit.test",
        "contacts": [
            {"id": "edge-45", "depth": {"range": {"minimum": 45, "maximum": 45}}},
            {"id": "edge-10", "depth": {"range": {"minimum": 10, "maximum": 10}}},
        ],
    }
    assert compile_board._declared_depths(board, 1) == {"edge-45": 45.0, "edge-10": 10.0}


def test_shipped_metolius_board_declares_its_slot_depths() -> None:
    source = REPOSITORY / "Hangboards" / "metolius-rock-rings-3d" / "metolius-rock-rings-3d.FCStd"
    if compile_board.cad_source._is_lfs_pointer(source):
        pytest.skip("FCStd sources are Git LFS pointers; run `git lfs pull` first")
    board = json.loads(compile_board.cad_source.generate_board_json(source))
    assert compile_board._declared_depths(board, 2) == {
        "pocket-25": 25.0,
        "pocket-32": 32.0,
        "pocket-40": 40.0,
    }


def test_side_pocket_uses_explicit_x_depth_axis() -> None:
    region = SimpleNamespace(
        PropertiesList=["ContactID", "HangTenDepthAxis"], ContactID="side-20",
        HangTenDepthAxis="x",
        Shape=SimpleNamespace(BoundBox=SimpleNamespace(XLength=20, YLength=80, ZLength=4.4)),
    )
    assert compile_board._validate_published_depths(
        [region], {"side-20": 20}, 1, .12, {"x": 80, "y": 10, "z": 90}
    ) == {"side-20": 20}


def test_invalid_depth_axis_fails_closed() -> None:
    region = SimpleNamespace(
        PropertiesList=["ContactID", "HangTenDepthAxis"], ContactID="side-20",
        HangTenDepthAxis="diagonal",
        Shape=SimpleNamespace(BoundBox=SimpleNamespace(XLength=20, YLength=80, ZLength=4.4)),
    )
    with pytest.raises(compile_board.BuildError, match="invalid HangTenDepthAxis"):
        compile_board._validate_published_depths([region], {"side-20": 20}, 1, .12)


class _Box:
    def __init__(self, depth: float) -> None:
        self.YLength = depth


class _Shape:
    def __init__(self, depth: float) -> None:
        self.BoundBox = _Box(depth)


class _Region:
    def __init__(self, contact_id: str, depth: float) -> None:
        self.PropertiesList = ["ContactID"]
        self.ContactID = contact_id
        self.Shape = _Shape(depth)


def test_region_depth_must_match_the_published_depth() -> None:
    declared = {"edge-20": 20.0}
    compile_board._validate_published_depths([_Region("edge-20", 20.1)], declared, 1, 0.05, 38.0)
    with pytest.raises(compile_board.BuildError, match="disagrees with the published depth"):
        compile_board._validate_published_depths([_Region("edge-20", 15.0)], declared, 1, 0.05, 38.0)


def test_a_published_depth_deeper_than_the_board_needs_the_full_board_depth() -> None:
    # A nominal 40 mm jug across a 38 mm rail: the region cannot be 40 mm deep,
    # so it must span the whole board instead.
    declared = {"jug-40": 40.0}
    compile_board._validate_published_depths([_Region("jug-40", 38.0)], declared, 1, 0.05, 38.0)
    with pytest.raises(compile_board.BuildError, match="expected 38.000 mm"):
        compile_board._validate_published_depths([_Region("jug-40", 30.0)], declared, 1, 0.05, 38.0)
    # Without a board depth the published value is still the only target.
    with pytest.raises(compile_board.BuildError, match="disagrees with the published depth"):
        compile_board._validate_published_depths([_Region("jug-40", 38.0)], declared, 1, 0.05)
