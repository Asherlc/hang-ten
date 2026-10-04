"""Inspect the shipped USDZ's geometry, never a renderer or authoring surrogate.

Run with Blender --background --factory-startup --python THIS -- MODEL [REPORT].
World-space USD transforms include the exported root. Camera-space rays use the
approved X-axis position rotations. All tolerances are display-shape guards,
not purported manufacturer measurements. No image processing is performed.
"""

from collections import defaultdict
from pathlib import Path
import hashlib
import json
import math
import sys

import numpy as np
from pxr import Gf, Usd, UsdGeom


def descriptor_owners(asset):
    """Use the runtime descriptor's identity contract for native CAD meshes."""
    descriptor = Path(asset).with_suffix(".model.json")
    if not descriptor.is_file():
        return None  # Historical standalone Blender exports carry contact attributes.
    document = json.loads(descriptor.read_text())
    assert document.get("schemaVersion") == 1, "Poker requires its contact descriptor"
    assert document.get("modelSHA256") == hashlib.sha256(Path(asset).read_bytes()).hexdigest(), "descriptor SHA-256 does not match model"
    result = {}
    for node in document["nodes"]:
        node_id = node["nodeID"]
        assert node_id and node_id not in result, ("duplicate or empty descriptor node", node_id)
        assert node["role"] in {"body", "contact", "attachment"}, node
        owner = node.get("contactID") if node["role"] == "contact" else "body"
        assert isinstance(owner, str) and owner, ("missing contact identity", node_id)
        result[node_id] = owner
    assert result, "empty descriptor node inventory"
    return result


def mesh_owner(prim, node_owners):
    """Resolve an exact descriptor node or its descendant, retaining old tags."""
    current = prim
    descriptor_owner = None
    legacy_owner = None
    while current and not current.IsPseudoRoot():
        legacy_owner = legacy_owner or current.GetAttribute("userProperties:contact_id").Get()
        if node_owners is not None and descriptor_owner is None:
            path = current.GetPath().pathString.lstrip("/")
            matches = [owner for node_id, owner in node_owners.items()
                       if path == node_id or path.endswith("/" + node_id)]
            assert len(matches) <= 1, ("ambiguous descriptor node identity", path)
            if matches:
                descriptor_owner = matches[0]
        current = current.GetParent()
    if node_owners is not None:
        assert descriptor_owner is not None, ("mesh missing from descriptor", prim.GetPath())
        assert not legacy_owner or legacy_owner == descriptor_owner, ("descriptor/contact attribute conflict", prim.GetPath())
        return descriptor_owner
    return legacy_owner or "body"


def inspect_section(asset):
    stage = Usd.Stage.Open(str(asset))
    node_owners = descriptor_owners(asset)
    triangles = []
    owners = []
    edges = defaultdict(list)
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        mesh = UsdGeom.Mesh(prim)
        transform = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        points = np.array([transform.Transform(Gf.Vec3d(*p)) for p in mesh.GetPointsAttr().Get()])
        counts = list(mesh.GetFaceVertexCountsAttr().Get())
        assert set(counts) == {3}, (prim.GetPath(), set(counts))
        indices = np.array(mesh.GetFaceVertexIndicesAttr().Get()).reshape((-1, 3))
        contact = mesh_owner(prim, node_owners)
        for triangle in points[indices]:
            number = len(triangles)
            triangles.append(triangle)
            owners.append(contact)
            keys = [tuple(round(float(v), 8) for v in point) for point in triangle]
            for i in range(3):
                edges[tuple(sorted((keys[i], keys[(i + 1) % 3])))].append(number)
    triangles = np.array(triangles)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.linalg.norm(normals, axis=1)[:, None]

    def ray(x, v, face):
        # Camera pose after R_x(face*pi/2), inverted onto base world coordinates.
        theta = -face * math.pi / 2
        rotation = np.array(((1, 0, 0), (0, math.cos(theta), -math.sin(theta)),
                             (0, math.sin(theta), math.cos(theta))))
        origin = rotation @ np.array((x, v, .2))
        direction = rotation @ np.array((0., 0., -1.))
        e1 = triangles[:, 1] - triangles[:, 0]
        e2 = triangles[:, 2] - triangles[:, 0]
        p = np.cross(np.broadcast_to(direction, e2.shape), e2)
        det = np.einsum("ij,ij->i", e1, p)
        mask = np.abs(det) > 1e-14
        inverse = np.zeros_like(det)
        inverse[mask] = 1 / det[mask]
        delta = origin - triangles[:, 0]
        u = np.einsum("ij,ij->i", delta, p) * inverse
        q = np.cross(delta, e1)
        vv = q @ direction * inverse
        distance = np.einsum("ij,ij->i", e2, q) * inverse
        mask &= (u >= -1e-7) & (vv >= -1e-7) & (u + vv <= 1 + 1e-7) & (distance > 0)
        assert np.any(mask), (x, v, face)
        hit = int(np.argmin(np.where(mask, distance, np.inf)))
        return {"x": x, "v": v, "owner": owners[hit], "frontZ": float(.2 - distance[hit])}

    report = {"cRays": [], "dRays": [], "seams": []}
    for side, x in (("left", -.132), ("right", .132)):
        for v in (.002, .015, .020, .025, .030, .035, .040):
            report["cRays"].append(ray(x, v, 2))
        for v in (-.020, -.010, .0, .015):
            report["dRays"].append(ray(x, v, 3))
    for edge, adjacent in edges.items():
        if len(adjacent) != 2 or abs(edge[1][0] - edge[0][0]) < .1:
            continue
        first, second = adjacent
        labels = {owners[first], owners[second]}
        for side in ("left", "right"):
            if labels == {f"face-c-{side}-shallow-half-round", f"face-d-{side}-deep-rounded-recess"}:
                angle = math.degrees(math.acos(float(np.clip(normals[first] @ normals[second], -1, 1))))
                report["seams"].append({"side": side, "edge": edge, "angleDegrees": angle})
    return report


def require_section(report):
    for row in report["cRays"]:
        side = "left" if row["x"] < 0 else "right"
        assert row["owner"] == f"face-c-{side}-shallow-half-round", ("Face C upper relief ownership", row)
    for row in report["dRays"]:
        side = "left" if row["x"] < 0 else "right"
        assert row["owner"] == f"face-d-{side}-deep-rounded-recess", ("Face D rounded relief ownership", row)
    for side in ("left", "right"):
        rows = [row for row in report["seams"] if row["side"] == side]
        assert rows, ("missing shared C/D edge", side)
        assert max(row["angleDegrees"] for row in rows) < 5, ("C/D geometric ridge", rows)
        depths = [.05 - row["frontZ"] for row in report["cRays"] if (row["x"] < 0) == (side == "left")]
        assert max(depths) - min(depths) > .004, ("near-flush C skirt", side, depths)
        depths = [.05 - row["frontZ"] for row in report["dRays"] if (row["x"] < 0) == (side == "left")]
        assert max(depths) > .015, ("D must retain substantial rounded recess", side, depths)


if __name__ == "__main__":
    arguments = sys.argv[sys.argv.index("--") + 1:]
    report = inspect_section(Path(arguments[0]))
    document = json.dumps(report, indent=2)
    print(document)
    if len(arguments) > 1:
        Path(arguments[1]).write_text(document + "\n")
    try:
        require_section(report)
    except AssertionError:
        import traceback
        traceback.print_exc()
        sys.exit(1)
    print("POKER_CD_SECTION_OK")
