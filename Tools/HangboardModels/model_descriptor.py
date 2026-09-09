"""Generated, closed-schema descriptors for Hang Ten USDZ board models.

This module deliberately derives every spatial value from USDZ node vertices.
It has no inputs for authored bounds, face-plane axes, or hold rectangles.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, TypeAlias


Vector2: TypeAlias = tuple[float, float]
Vector3: TypeAlias = tuple[float, float, float]
NodeRole: TypeAlias = Literal["body", "hold"]

_COORDINATE_FRAME = "hang-ten-board-v1"
_SCHEMA_VERSION = 1
_DESCRIPTOR_KEYS = frozenset(
    {"schemaVersion", "coordinateFrame", "modelSHA256", "modelBounds", "nodes", "holds"}
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class NodeBinding:
    """A named model node with its one permitted semantic role."""

    node_id: str
    role: NodeRole | str
    hold_id: str | None = None


@dataclass(frozen=True)
class ModelBounds:
    """Physical metre bounds, derived across every bound node vertex."""

    min: Vector3
    max: Vector3


@dataclass(frozen=True)
class FacePlaneAABB:
    """A hold's normalized +X/+Y rectangle in hang-ten-board-v1."""

    min: Vector2
    max: Vector2


@dataclass(frozen=True)
class HoldDescriptorV1:
    """Generated descriptor data for a logical hold that may have several nodes."""

    node_ids: tuple[str, ...]
    face_plane_aabb: FacePlaneAABB
    center: Vector2


@dataclass(frozen=True)
class ModelDescriptorV1:
    """Closed v1 model descriptor; construct it through ``compile_descriptor``."""

    model_sha256: str
    model_bounds: ModelBounds
    nodes: tuple[NodeBinding, ...]
    holds: Mapping[str, HoldDescriptorV1]

    def to_json(self) -> dict[str, object]:
        """Return the canonical deterministic JSON-ready representation."""
        return {
            "schemaVersion": _SCHEMA_VERSION,
            "coordinateFrame": _COORDINATE_FRAME,
            "modelSHA256": self.model_sha256,
            "modelBounds": _bounds_to_json(self.model_bounds),
            "nodes": [
                _node_to_json(node)
                for node in sorted(self.nodes, key=lambda node: node.node_id)
            ],
            "holds": {
                hold_id: _hold_to_json(self.holds[hold_id])
                for hold_id in sorted(self.holds)
            },
        }

    @classmethod
    def from_json(cls, value: Mapping[str, object]) -> ModelDescriptorV1:
        """Load a closed, canonical generated descriptor representation.

        This validates the descriptor's internal derivation invariants.  Raw
        model geometry remains the sole source for a newly compiled descriptor.
        """
        if not isinstance(value, Mapping):
            raise ValueError("descriptor must be an object")
        _require_exact_keys(value, _DESCRIPTOR_KEYS, "descriptor")
        if value["schemaVersion"] != _SCHEMA_VERSION or isinstance(value["schemaVersion"], bool):
            raise ValueError("schemaVersion must be 1")
        if value["coordinateFrame"] != _COORDINATE_FRAME:
            raise ValueError("coordinateFrame must be hang-ten-board-v1")
        model_sha256 = _sha256(value["modelSHA256"])
        model_bounds = _parse_model_bounds(value["modelBounds"])
        _require_nonzero_face_span(model_bounds)
        nodes = _parse_nodes(value["nodes"])
        holds = _parse_holds(value["holds"], nodes)
        return cls(
            model_sha256=model_sha256,
            model_bounds=model_bounds,
            nodes=nodes,
            holds=MappingProxyType(holds),
        )


def compile_descriptor(
    model_bytes: bytes,
    nodes: Sequence[NodeBinding],
    vertices_by_node_id: Mapping[str, Sequence[Vector3]],
    logical_hold_ids: frozenset[str],
) -> ModelDescriptorV1:
    """Derive a deterministic descriptor solely from bound USDZ node vertices."""
    if not isinstance(model_bytes, bytes):
        raise ValueError("model_bytes must be exact USDZ bytes")
    bindings = _validate_bindings(nodes)
    expected_hold_ids = _validate_logical_hold_ids(logical_hold_ids)
    vertices = _validate_bound_geometry(bindings, vertices_by_node_id)
    actual_hold_ids = {binding.hold_id for binding in bindings if binding.role == "hold"}
    if actual_hold_ids != expected_hold_ids:
        raise ValueError("bound hold IDs must equal logical hold IDs")

    raw_model_bounds = _raw_model_bounds(vertices.values())
    _require_nonzero_face_span(raw_model_bounds)
    holds = _compile_holds(bindings, vertices, raw_model_bounds)
    return ModelDescriptorV1(
        model_sha256=hashlib.sha256(model_bytes).hexdigest(),
        model_bounds=_rounded_bounds(raw_model_bounds),
        nodes=tuple(sorted(bindings, key=lambda binding: binding.node_id)),
        holds=MappingProxyType(holds),
    )


def _validate_bindings(nodes: Sequence[NodeBinding]) -> list[NodeBinding]:
    if isinstance(nodes, (str, bytes)) or not isinstance(nodes, Sequence):
        raise ValueError("nodes must be a sequence of NodeBinding values")
    bindings = list(nodes)
    node_ids: set[str] = set()
    body_count = 0
    for binding in bindings:
        if not isinstance(binding, NodeBinding):
            raise ValueError("nodes must contain NodeBinding values")
        if not isinstance(binding.node_id, str) or not binding.node_id:
            raise ValueError("nodeID must be a non-empty string")
        if binding.node_id in node_ids:
            raise ValueError(f"duplicate nodeID: {binding.node_id}")
        node_ids.add(binding.node_id)
        if binding.role == "decoration":
            raise ValueError("decoration nodes are not permitted")
        if binding.role not in {"body", "hold"}:
            raise ValueError(f"unknown node role: {binding.role}")
        if binding.role == "body":
            body_count += 1
            if binding.hold_id is not None:
                raise ValueError("body node may not declare holdID")
        elif not isinstance(binding.hold_id, str) or not binding.hold_id:
            raise ValueError("hold node requires a non-empty holdID")
    if body_count == 0:
        raise ValueError("descriptor requires a body node")
    if body_count != 1:
        raise ValueError("descriptor requires exactly one body node")
    return bindings


def _validate_logical_hold_ids(logical_hold_ids: frozenset[str]) -> set[str]:
    if not isinstance(logical_hold_ids, frozenset):
        raise ValueError("logical hold IDs must be a frozenset")
    if any(not isinstance(hold_id, str) or not hold_id for hold_id in logical_hold_ids):
        raise ValueError("logical hold IDs must contain non-empty strings")
    return set(logical_hold_ids)


def _validate_bound_geometry(
    bindings: Sequence[NodeBinding], vertices_by_node_id: Mapping[str, Sequence[Vector3]]
) -> dict[str, tuple[Vector3, ...]]:
    if not isinstance(vertices_by_node_id, Mapping):
        raise ValueError("vertices_by_node_id must be a mapping")
    bound_ids = {binding.node_id for binding in bindings}
    geometry_ids = set(vertices_by_node_id)
    unbound_ids = geometry_ids - bound_ids
    if unbound_ids:
        raise ValueError(f"unbound geometry for nodeID: {sorted(unbound_ids)[0]}")
    missing_ids = bound_ids - geometry_ids
    if missing_ids:
        raise ValueError(f"node/vertex disagreement for nodeID: {sorted(missing_ids)[0]}")
    parsed: dict[str, tuple[Vector3, ...]] = {}
    for node_id in bound_ids:
        raw_vertices = vertices_by_node_id[node_id]
        if isinstance(raw_vertices, (str, bytes)) or not isinstance(raw_vertices, Sequence):
            raise ValueError(f"vertices for nodeID must be a sequence: {node_id}")
        if not raw_vertices:
            raise ValueError(f"nodeID has zero vertices: {node_id}")
        parsed[node_id] = tuple(_vector3(vertex, f"vertex for nodeID {node_id}") for vertex in raw_vertices)
    return parsed


def _vector3(value: object, field: str) -> Vector3:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 3:
        raise ValueError(f"{field} must contain exactly three coordinates")
    coordinates = tuple(_finite_number(coordinate, field) for coordinate in value)
    return (coordinates[0], coordinates[1], coordinates[2])


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field} coordinates must be finite numbers")
    return float(value)


def _raw_model_bounds(vertices_by_node: Iterable[Sequence[Vector3]]) -> ModelBounds:
    vertices = [
        vertex for node_vertices in vertices_by_node for vertex in node_vertices
    ]
    return ModelBounds(
        min=(
            min(vertex[0] for vertex in vertices),
            min(vertex[1] for vertex in vertices),
            min(vertex[2] for vertex in vertices),
        ),
        max=(
            max(vertex[0] for vertex in vertices),
            max(vertex[1] for vertex in vertices),
            max(vertex[2] for vertex in vertices),
        ),
    )


def _rounded_bounds(bounds: ModelBounds) -> ModelBounds:
    return ModelBounds(
        min=tuple(_round(value) for value in bounds.min),
        max=tuple(_round(value) for value in bounds.max),
    )


def _require_nonzero_face_span(model_bounds: ModelBounds) -> None:
    if model_bounds.max[0] <= model_bounds.min[0] or model_bounds.max[1] <= model_bounds.min[1]:
        raise ValueError("model bounds must have non-zero face span in +X and +Y")


def _compile_holds(
    bindings: Sequence[NodeBinding], vertices_by_node_id: Mapping[str, Sequence[Vector3]], model_bounds: ModelBounds
) -> dict[str, HoldDescriptorV1]:
    node_ids_by_hold: dict[str, list[str]] = {}
    vertices_by_hold: dict[str, list[Vector3]] = {}
    for binding in bindings:
        if binding.role == "hold":
            assert binding.hold_id is not None
            node_ids_by_hold.setdefault(binding.hold_id, []).append(binding.node_id)
            vertices_by_hold.setdefault(binding.hold_id, []).extend(vertices_by_node_id[binding.node_id])
    result: dict[str, HoldDescriptorV1] = {}
    for hold_id in sorted(node_ids_by_hold):
        hold_vertices = vertices_by_hold[hold_id]
        min_x, max_x = min(vertex[0] for vertex in hold_vertices), max(vertex[0] for vertex in hold_vertices)
        min_y, max_y = min(vertex[1] for vertex in hold_vertices), max(vertex[1] for vertex in hold_vertices)
        face_bounds = FacePlaneAABB(
            min=(
                _normalize(min_x, model_bounds.min[0], model_bounds.max[0]),
                _normalize(min_y, model_bounds.min[1], model_bounds.max[1]),
            ),
            max=(
                _normalize(max_x, model_bounds.min[0], model_bounds.max[0]),
                _normalize(max_y, model_bounds.min[1], model_bounds.max[1]),
            ),
        )
        result[hold_id] = HoldDescriptorV1(
            node_ids=tuple(sorted(node_ids_by_hold[hold_id])),
            face_plane_aabb=face_bounds,
            center=(
                _round((face_bounds.min[0] + face_bounds.max[0]) / 2),
                _round((face_bounds.min[1] + face_bounds.max[1]) / 2),
            ),
        )
    return result


def _normalize(value: float, minimum: float, maximum: float) -> float:
    return _round((value - minimum) / (maximum - minimum))


def _round(value: float) -> float:
    return round(value, 9)


def _bounds_to_json(bounds: ModelBounds) -> dict[str, object]:
    return {"min": list(bounds.min), "max": list(bounds.max)}


def _node_to_json(node: NodeBinding) -> dict[str, str]:
    value: dict[str, str] = {"nodeID": node.node_id, "role": node.role}
    if node.role == "hold":
        assert node.hold_id is not None
        value["holdID"] = node.hold_id
    return value


def _hold_to_json(hold: HoldDescriptorV1) -> dict[str, object]:
    return {
        "nodeIDs": list(hold.node_ids),
        "facePlaneAABB": {"min": list(hold.face_plane_aabb.min), "max": list(hold.face_plane_aabb.max)},
        "center": list(hold.center),
    }


def _require_exact_keys(value: Mapping[str, object], expected: frozenset[str], field: str) -> None:
    unknown = set(value) - expected
    if unknown:
        raise ValueError(f"{field} contains unknown key: {sorted(unknown)[0]}")
    missing = expected - set(value)
    if missing:
        raise ValueError(f"{field} is missing key: {sorted(missing)[0]}")


def _sha256(value: object) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError("modelSHA256 must be a lowercase SHA-256 digest")
    return value


def _parse_model_bounds(value: object) -> ModelBounds:
    mapping = _mapping(value, "modelBounds")
    _require_exact_keys(mapping, frozenset({"min", "max"}), "modelBounds")
    bounds = ModelBounds(
        min=_vector3_json(mapping["min"], "modelBounds.min"),
        max=_vector3_json(mapping["max"], "modelBounds.max"),
    )
    if any(bounds.min[axis] > bounds.max[axis] for axis in range(3)):
        raise ValueError("modelBounds minimum may not exceed maximum")
    return bounds


def _parse_nodes(value: object) -> tuple[NodeBinding, ...]:
    raw_nodes = _sequence(value, "nodes")
    nodes: list[NodeBinding] = []
    for raw_node in raw_nodes:
        mapping = _mapping(raw_node, "node")
        role = mapping.get("role")
        expected = frozenset({"nodeID", "role", "holdID"}) if role == "hold" else frozenset({"nodeID", "role"})
        _require_exact_keys(mapping, expected, "node")
        node_id = mapping["nodeID"]
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("nodeID must be a non-empty string")
        if role not in {"body", "hold"}:
            raise ValueError("node role must be body or hold")
        hold_id = mapping.get("holdID")
        if role == "hold" and (not isinstance(hold_id, str) or not hold_id):
            raise ValueError("hold node requires a non-empty holdID")
        nodes.append(NodeBinding(node_id, role, hold_id if role == "hold" else None))
    _validate_bindings(nodes)
    if [node.node_id for node in nodes] != sorted(node.node_id for node in nodes):
        raise ValueError("nodes must be sorted by nodeID")
    return tuple(nodes)


def _parse_holds(value: object, nodes: Sequence[NodeBinding]) -> dict[str, HoldDescriptorV1]:
    holds = _mapping(value, "holds")
    if list(holds) != sorted(holds):
        raise ValueError("holds must be sorted by holdID")
    expected_by_hold: dict[str, list[str]] = {}
    for node in nodes:
        if node.role == "hold":
            assert node.hold_id is not None
            expected_by_hold.setdefault(node.hold_id, []).append(node.node_id)
    if set(holds) != set(expected_by_hold):
        raise ValueError("holds must equal node hold IDs")
    parsed: dict[str, HoldDescriptorV1] = {}
    for hold_id, raw_hold in holds.items():
        if not isinstance(hold_id, str) or not hold_id:
            raise ValueError("hold IDs must be non-empty strings")
        mapping = _mapping(raw_hold, f"hold {hold_id}")
        _require_exact_keys(
            mapping,
            frozenset({"nodeIDs", "facePlaneAABB", "center"}),
            f"hold {hold_id}",
        )
        node_ids = _string_sequence(mapping["nodeIDs"], f"hold {hold_id}.nodeIDs")
        if not node_ids or node_ids != sorted(node_ids) or node_ids != sorted(expected_by_hold[hold_id]):
            raise ValueError(f"hold {hold_id} nodeIDs must exactly match bound nodes")
        bounds_mapping = _mapping(mapping["facePlaneAABB"], f"hold {hold_id}.facePlaneAABB")
        _require_exact_keys(bounds_mapping, frozenset({"min", "max"}), f"hold {hold_id}.facePlaneAABB")
        face_bounds = FacePlaneAABB(
            min=_vector2_json(bounds_mapping["min"], f"hold {hold_id}.facePlaneAABB.min"),
            max=_vector2_json(bounds_mapping["max"], f"hold {hold_id}.facePlaneAABB.max"),
        )
        if any(face_bounds.min[axis] > face_bounds.max[axis] for axis in range(2)) or any(
            coordinate < 0 or coordinate > 1 for coordinate in (*face_bounds.min, *face_bounds.max)
        ):
            raise ValueError(f"hold {hold_id} facePlaneAABB must be normalized")
        center = _vector2_json(mapping["center"], f"hold {hold_id}.center")
        expected_center = (
            _round((face_bounds.min[0] + face_bounds.max[0]) / 2),
            _round((face_bounds.min[1] + face_bounds.max[1]) / 2),
        )
        if center != expected_center:
            raise ValueError(f"hold {hold_id} center must derive from facePlaneAABB")
        parsed[hold_id] = HoldDescriptorV1(tuple(node_ids), face_bounds, center)
    return parsed


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{field} must be an object")
    return value


def _sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be an array")
    return value


def _string_sequence(value: object, field: str) -> list[str]:
    values = _sequence(value, field)
    if any(not isinstance(item, str) or not item for item in values):
        raise ValueError(f"{field} must contain non-empty strings")
    return list(values)  # type: ignore[return-value]


def _vector2_json(value: object, field: str) -> Vector2:
    values = _sequence(value, field)
    if len(values) != 2:
        raise ValueError(f"{field} must contain exactly two coordinates")
    return (_canonical_number(values[0], field), _canonical_number(values[1], field))


def _vector3_json(value: object, field: str) -> Vector3:
    values = _sequence(value, field)
    if len(values) != 3:
        raise ValueError(f"{field} must contain exactly three coordinates")
    return (
        _canonical_number(values[0], field),
        _canonical_number(values[1], field),
        _canonical_number(values[2], field),
    )


def _canonical_number(value: object, field: str) -> float:
    number = _finite_number(value, field)
    if _round(number) != number:
        raise ValueError(f"{field} must be rounded to nine decimals")
    return number
