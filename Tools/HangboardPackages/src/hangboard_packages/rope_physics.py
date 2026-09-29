"""Closed, hash-bound inputs for live threaded-rope simulation.

Portal coordinates identify an aperture, never a pinned rope contact. All
distances use the descriptor's model basis in metres. Validation is read-only.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re


def _closed(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError("invalid rope physics members")


def _number(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    return float(value)


def _vector(value):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("vector must have three finite components")
    return tuple(_number(x, "vector") for x in value)


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", value):
        raise ValueError("invalid physics identifier")
    return value


def _provenance(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("physics estimate requires provenance")


def _estimate(value):
    _closed(value, {"value", "provenance"})
    _number(value["value"], "mass", positive=True)
    _provenance(value["provenance"])


def _indexed(values):
    if not isinstance(values, list):
        raise ValueError("physics inventory must be an array")
    result = {}
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("invalid physics inventory entry")
        key = _identifier(value.get("id"))
        if key in result:
            raise ValueError(f"duplicate physics ID {key}")
        result[key] = value
    return result


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])


def _mesh(value):
    _closed(value, {"vertices", "triangles"})
    if not isinstance(value["vertices"], list) or len(value["vertices"]) < 4:
        raise ValueError("collision mesh needs vertices")
    vertices = [_vector(v) for v in value["vertices"]]
    triangles = value["triangles"]
    if not isinstance(triangles, list) or len(triangles) < 4:
        raise ValueError("collision mesh needs triangles")
    edges = {}
    volume = 0
    for face in triangles:
        if not isinstance(face, list) or len(face) != 3 or any(
            isinstance(i, bool) or not isinstance(i, int) or i < 0 or i >= len(vertices) for i in face
        ) or len(set(face)) != 3:
            raise ValueError("invalid collision triangle")
        a, b, c = (vertices[i] for i in face)
        area = _cross(_sub(b, a), _sub(c, a))
        if _dot(area, area) <= 1e-24:
            raise ValueError("degenerate collision triangle")
        volume += _dot(a, _cross(b, c)) / 6
        for i, j in zip(face, face[1:] + face[:1]):
            key = (min(i, j), max(i, j))
            count, direction = edges.get(key, (0, 0))
            edges[key] = count + 1, direction + (1 if i < j else -1)
    if any(count != 2 or direction != 0 for count, direction in edges.values()) or volume <= 0:
        raise ValueError("collision solid must be closed with outward consistent winding")


def portal_clearance_radius(portal):
    """Radius of the circle around the declared seed center inside an aperture."""
    _closed(portal, {"id", "center", "normal", "boundary"})
    center, normal = _vector(portal["center"]), _vector(portal["normal"])
    if abs(_dot(normal, normal) - 1) > 1e-6:
        raise ValueError("portal normal must be unit length")
    if not isinstance(portal["boundary"], list) or len(portal["boundary"]) < 3:
        raise ValueError("portal needs a convex planar boundary")
    points = [_vector(p) for p in portal["boundary"]]
    if any(abs(_dot(_sub(p, center), normal)) > 1e-7 for p in points):
        raise ValueError("portal boundary must be planar")
    signs, distances = [], []
    for a, b in zip(points, points[1:] + points[:1]):
        edge = _sub(b, a)
        length = math.sqrt(_dot(edge, edge))
        if length < 1e-10:
            raise ValueError("portal boundary has duplicate vertices")
        signed = _dot(_cross(edge, _sub(center, a)), normal)
        signs.append(signed)
        distances.append(abs(signed) / length)
        # All other vertices must lie on the same side of this directed edge.
        sides = [_dot(_cross(edge, _sub(p, a)), normal) for p in points]
        if min(sides) < -1e-12 and max(sides) > 1e-12:
            raise ValueError("portal boundary must be convex")
    if min(signs) < 0 < max(signs) or min(distances) <= 0:
        raise ValueError("portal seed center must be strictly inside its aperture")
    return min(distances)


def derive_radius(baseline_radius: float, scale: float) -> float:
    radius = _number(baseline_radius, "baseline radius", True) * _number(scale, "thickness scale", True)
    return _number(radius, "derived radius", True)


def validate_rope_physics(document: dict, model_sha256: str) -> dict:
    _closed(document, {"schemaVersion", "sourceSHA256", "modelSHA256", "coordinateSystem", "collision", "portals", "channels", "profiles"})
    if type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1:
        raise ValueError("unsupported rope physics schema")
    for key in ("sourceSHA256", "modelSHA256"):
        if not isinstance(document[key], str) or not re.fullmatch(r"[0-9a-f]{64}", document[key]):
            raise ValueError("invalid physics hash")
    if document["modelSHA256"] != model_sha256:
        raise ValueError("rope physics model hash mismatch")
    if document["coordinateSystem"] != "hang-ten-board-v1":
        raise ValueError("invalid physics coordinate basis")
    _mesh(document["collision"])
    portals = _indexed(document["portals"])
    fit = {key: portal_clearance_radius(p) for key, p in portals.items()}
    channels = _indexed(document["channels"])
    for channel in channels.values():
        _closed(channel, {"id", "portalIDs", "spine", "vertices", "triangles"})
        ids = channel["portalIDs"]
        if not isinstance(ids, list) or len(ids) != 2:
            raise ValueError("channel must connect two distinct portals")
        ids = [_identifier(p) for p in ids]
        if len(set(ids)) != 2 or any(p not in portals for p in ids):
            raise ValueError("channel must connect two distinct portals")
        spine = channel["spine"]
        if not isinstance(spine, list) or len(spine) < 2:
            raise ValueError("channel must have a geometry-derived spine")
        for point in spine:
            _vector(point)
        _mesh({"vertices": channel["vertices"], "triangles": channel["triangles"]})
    profiles = _indexed(document["profiles"])
    if not profiles:
        raise ValueError("physics needs at least one profile")
    presentation_instances = set()
    for profile in profiles.values():
        _closed(profile, {"id", "presentationID", "boardMass", "ropes"}, {"instanceID"})
        _identifier(profile["presentationID"])
        if "instanceID" in profile:
            _identifier(profile["instanceID"])
        pair = (profile["presentationID"], profile.get("instanceID"))
        if pair in presentation_instances:
            raise ValueError("duplicate physics profile for presentation instance")
        presentation_instances.add(pair)
        _estimate(profile["boardMass"])
        ropes = _indexed(profile["ropes"])
        if not ropes:
            raise ValueError("physics profile requires ropes")
        for rope in ropes.values():
            _closed(rope, {"id", "baselineRadius", "thicknessScale", "radius", "restLength", "lengthProvenance", "linearMass", "nodes", "edges"})
            derived = derive_radius(rope["baselineRadius"], rope["thicknessScale"])
            if abs(_number(rope["radius"], "radius", True) - derived) > 1e-12:
                raise ValueError("rope radius must match selected baseline scale")
            _number(rope["restLength"], "rope length", True)
            _provenance(rope["lengthProvenance"])
            _estimate(rope["linearMass"])
            nodes = _indexed(rope["nodes"])
            if len(nodes) < 2:
                raise ValueError("rope graph requires two endpoints")
            for node in nodes.values():
                if node.get("kind") == "portal":
                    _closed(node, {"id", "kind", "portalID"})
                    pid = _identifier(node["portalID"])
                    if pid not in portals:
                        raise ValueError("unknown rope graph portal")
                    if derived >= fit[pid] - 1e-9:
                        raise ValueError(f"rope does not fit portal {pid}")
                elif node.get("kind") in ("support", "attachment"):
                    _closed(node, {"id", "kind", "point"})
                    _vector(node["point"])
                else:
                    raise ValueError("invalid rope graph node kind")
            ordered = list(nodes)
            if nodes[ordered[0]]["kind"] != "support" or nodes[ordered[-1]]["kind"] not in ("support", "attachment"):
                raise ValueError("rope graph must start at a support and end at a support or attachment")
            edges = rope["edges"]
            if not isinstance(edges, list) or len(edges) != len(nodes) - 1:
                raise ValueError("rope graph edges must form one ordered continuous chain")
            for i, edge in enumerate(edges):
                _closed(edge, {"from", "to", "kind"}, {"channelID", "winding"})
                if edge["from"] != ordered[i] or edge["to"] != ordered[i+1]:
                    raise ValueError("rope graph edges must follow node order")
                if edge["kind"] == "channel":
                    if "winding" in edge or "channelID" not in edge or _identifier(edge["channelID"]) not in channels:
                        raise ValueError("invalid rope channel edge")
                    ends = [nodes[edge[k]].get("portalID") for k in ("from", "to")]
                    if set(ends) != set(channels[edge["channelID"]]["portalIDs"]):
                        raise ValueError("channel graph endpoints do not match its portals")
                elif edge["kind"] == "free":
                    if "channelID" in edge or edge.get("winding") not in (None, "clockwise", "counterclockwise"):
                        raise ValueError("invalid free rope edge")
                else:
                    raise ValueError("invalid rope graph edge kind")
    return document


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate physics member {key}")
        result[key] = value
    return result


def load_rope_physics(path: Path, model_sha256: str) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("physics descriptor must be a regular file of at most 64 MiB")
    try:
        document = json.loads(path.read_text(), object_pairs_hook=_unique_keys)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid rope physics JSON") from error
    return validate_rope_physics(document, model_sha256)
