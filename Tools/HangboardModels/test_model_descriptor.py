"""Behavioral tests for the generated, model-derived descriptor v1 contract."""

from __future__ import annotations

import hashlib
import math
from dataclasses import FrozenInstanceError

import pytest

from model_descriptor import (
    FacePlaneAABB,
    HoldDescriptorV1,
    ModelBounds,
    ModelDescriptorV1,
    NodeBinding,
    compile_descriptor,
)


def body(node_id: str) -> NodeBinding:
    return NodeBinding(node_id, "body")


def hold(node_id: str, hold_id: str) -> NodeBinding:
    return NodeBinding(node_id, "hold", hold_id)


def test_compiler_rounds_normalized_face_bounds_and_requires_exact_inventory() -> None:
    """Catches a compiler that uses raw bounds, wrong axes, or a wrong rounding precision."""
    descriptor = compile_descriptor(
        b"usdz",
        [body("Board/Body"), hold("Board/Hold/JugLeft", "jug-left")],
        {
            "Board/Body": [(0, 0, 0), (0.58, 0.15, 0.058)],
            "Board/Hold/JugLeft": [
                (0.01234567891, 0.10123456789, 0),
                (0.14567890123, 0.14999999991, 0.02),
            ],
        },
        frozenset({"jug-left"}),
    )

    assert descriptor.model_bounds.min == (0.0, 0.0, 0.0)
    assert descriptor.model_bounds.max == (0.58, 0.15, 0.058)
    assert descriptor.holds["jug-left"].face_plane_aabb.min == (0.021285653, 0.674897119)
    assert descriptor.holds["jug-left"].face_plane_aabb.max == (0.251170519, 0.999999999)
    assert descriptor.holds["jug-left"].center == (0.136228086, 0.837448559)
    with pytest.raises(ValueError, match="logical hold IDs"):
        compile_descriptor(
            b"usdz",
            [body("Board/Body")],
            {"Board/Body": [(0, 0, 0), (1, 1, 1)]},
            frozenset({"jug-left"}),
        )


def test_compiler_normalizes_against_raw_vertices_before_rounding_model_bounds() -> None:
    """Catches normalization that reuses already-rounded physical output bounds."""
    descriptor = compile_descriptor(
        b"usdz",
        [body("Body"), hold("Hold", "one")],
        {
            "Body": [(0.00000000049, 0, 0), (0.00000000149, 1, 1)],
            "Hold": [(0.00000000099, 0, 0), (0.00000000099, 1, 1)],
        },
        frozenset({"one"}),
    )

    assert descriptor.model_bounds.min == (0.0, 0.0, 0.0)
    assert descriptor.model_bounds.max == (0.000000001, 1.0, 1.0)
    assert descriptor.holds["one"].face_plane_aabb.min == (0.5, 0.0)
    assert descriptor.holds["one"].face_plane_aabb.max == (0.5, 1.0)


def test_generated_descriptor_values_cannot_be_constructed_or_mutated_publicly() -> None:
    """Catches callers bypassing model-derived factories with hand-authored spatial data."""
    with pytest.raises(TypeError):
        HoldDescriptorV1()
    with pytest.raises(TypeError):
        HoldDescriptorV1(
            node_ids=("Hold",),
            face_plane_aabb=FacePlaneAABB((0.0, 0.0), (1.0, 1.0)),
            center=(0.5, 0.5),
        )
    with pytest.raises(TypeError):
        ModelDescriptorV1()
    with pytest.raises(TypeError):
        ModelDescriptorV1(
            model_sha256="0" * 64,
            model_bounds=ModelBounds((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
            nodes=(body("Body"),),
            holds={},
        )

    descriptor = compile_descriptor(
        b"usdz",
        [body("Body"), hold("Hold", "one")],
        {"Body": [(0, 0, 0), (1, 1, 1)], "Hold": [(0.25, 0.5, 0)]},
        frozenset({"one"}),
    )
    assert descriptor.holds["one"].center == (0.25, 0.5)
    with pytest.raises(FrozenInstanceError):
        descriptor.holds["one"].center = (0.0, 0.0)


def test_compiler_rejects_finite_vertices_whose_derived_face_span_overflows() -> None:
    """Catches finite input coordinates producing infinity or NaN during normalization."""
    with pytest.raises(ValueError, match="finite"):
        compile_descriptor(
            b"usdz",
            [body("Body"), hold("Hold", "one")],
            {
                "Body": [(-1e308, -1e308, 0), (1e308, 1e308, 1)],
                "Hold": [(0, 0, 0)],
            },
            frozenset({"one"}),
        )


def test_compiler_unions_disconnected_hold_nodes_and_serializes_deterministically() -> None:
    """Catches lost hold pieces and unstable node or hold ordering in generated output."""
    nodes = [
        hold("Board/Hold/RightPiece", "right"),
        body("Board/Body"),
        hold("Board/Hold/LeftPieceB", "left"),
        hold("Board/Hold/LeftPieceA", "left"),
    ]
    vertices = {
        "Board/Hold/RightPiece": [(8, 2, 0), (9, 4, 3)],
        "Board/Body": [(0, 0, -1), (10, 10, 5)],
        "Board/Hold/LeftPieceB": [(3, 5, 0), (4, 8, 1)],
        "Board/Hold/LeftPieceA": [(1, 1, 0), (2, 3, 1)],
    }

    descriptor = compile_descriptor(b"exact-usdz-bytes", nodes, vertices, frozenset({"left", "right"}))
    rendered = descriptor.to_json()

    assert rendered == {
        "schemaVersion": 1,
        "coordinateFrame": "hang-ten-board-v1",
        "modelSHA256": hashlib.sha256(b"exact-usdz-bytes").hexdigest(),
        "modelBounds": {"min": [0.0, 0.0, -1.0], "max": [10.0, 10.0, 5.0]},
        "nodes": [
            {"nodeID": "Board/Body", "role": "body"},
            {"nodeID": "Board/Hold/LeftPieceA", "role": "hold", "holdID": "left"},
            {"nodeID": "Board/Hold/LeftPieceB", "role": "hold", "holdID": "left"},
            {"nodeID": "Board/Hold/RightPiece", "role": "hold", "holdID": "right"},
        ],
        "holds": {
            "left": {
                "nodeIDs": ["Board/Hold/LeftPieceA", "Board/Hold/LeftPieceB"],
                "facePlaneAABB": {"min": [0.1, 0.1], "max": [0.4, 0.8]},
                "center": [0.25, 0.45],
            },
            "right": {
                "nodeIDs": ["Board/Hold/RightPiece"],
                "facePlaneAABB": {"min": [0.8, 0.2], "max": [0.9, 0.4]},
                "center": [0.85, 0.3],
            },
        },
    }
    assert list(rendered["holds"]) == ["left", "right"]
    assert ModelDescriptorV1.from_json(rendered).to_json() == rendered


@pytest.mark.parametrize(
    ("nodes", "vertices", "inventory", "message"),
    [
        (
            [body("Body"), body("Body")],
            {"Body": [(0, 0, 0)]},
            frozenset(),
            "duplicate nodeID",
        ),
        (
            [hold("Hold", "one")],
            {"Hold": [(0, 0, 0)]},
            frozenset({"one"}),
            "body",
        ),
        (
            [NodeBinding("Body", "body", "not-allowed")],
            {"Body": [(0, 0, 0)]},
            frozenset(),
            "body.*holdID",
        ),
        (
            [NodeBinding("Decoration", "decoration")],
            {"Decoration": [(0, 0, 0)]},
            frozenset(),
            "decoration",
        ),
        (
            [body("Body"), NodeBinding("Hold", "hold")],
            {"Body": [(0, 0, 0)], "Hold": [(1, 1, 1)]},
            frozenset(),
            "holdID",
        ),
        (
            [body("Body"), hold("Hold", "one")],
            {"Body": [(0, 0, 0)], "Hold": []},
            frozenset({"one"}),
            "zero vertices",
        ),
        (
            [body("Body")],
            {"Body": [(0, 0, 0)], "Unbound": [(1, 1, 1)]},
            frozenset(),
            "unbound geometry",
        ),
        (
            [body("Body"), hold("Hold", "one")],
            {"Body": [(0, 0, 0)]},
            frozenset({"one"}),
            "node/vertex disagreement",
        ),
    ],
)
def test_compiler_rejects_invalid_node_and_geometry_bindings(
    nodes: list[NodeBinding],
    vertices: dict[str, list[tuple[float, float, float]]],
    inventory: frozenset[str],
    message: str,
) -> None:
    """Catches descriptors with geometry that is ambiguous, absent, or not a contact surface."""
    with pytest.raises(ValueError, match=message):
        compile_descriptor(b"usdz", nodes, vertices, inventory)


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_compiler_rejects_non_finite_vertex_coordinates(bad_value: float) -> None:
    """Catches invalid model geometry before it can leak invalid JSON numbers."""
    with pytest.raises(ValueError, match="finite"):
        compile_descriptor(
            b"usdz",
            [body("Body")],
            {"Body": [(0, 0, 0), (bad_value, 1, 1)]},
            frozenset(),
        )


def test_compiler_rejects_zero_face_span() -> None:
    """Catches normalization that divides by a collapsed global face plane."""
    with pytest.raises(ValueError, match="face span"):
        compile_descriptor(
            b"usdz",
            [body("Body")],
            {"Body": [(1, 2, 0), (1, 2, 3)]},
            frozenset(),
        )


def test_model_hash_changes_with_exact_model_bytes() -> None:
    """Catches hashing that ignores the exact serialized USDZ payload."""
    first = compile_descriptor(
        b"usdz-a", [body("Body")], {"Body": [(0, 0, 0), (1, 1, 1)]}, frozenset()
    )
    second = compile_descriptor(
        b"usdz-b", [body("Body")], {"Body": [(0, 0, 0), (1, 1, 1)]}, frozenset()
    )

    assert first.model_sha256 != second.model_sha256
    assert first.to_json()["modelSHA256"] == hashlib.sha256(b"usdz-a").hexdigest()


def test_from_json_rejects_unknown_or_noncanonical_generated_descriptor_values() -> None:
    """Catches accepting an open schema or hand-authored noncanonical descriptor values."""
    rendered = compile_descriptor(
        b"usdz", [body("Body")], {"Body": [(0, 0, 0), (1, 1, 1)]}, frozenset()
    ).to_json()
    rendered["unexpected"] = True
    with pytest.raises(ValueError, match="unknown key"):
        ModelDescriptorV1.from_json(rendered)

    rendered.pop("unexpected")
    rendered["coordinateFrame"] = "made-up-frame"
    with pytest.raises(ValueError, match="coordinateFrame"):
        ModelDescriptorV1.from_json(rendered)
