"""Inspect the shipped USDZ's geometry, never a renderer or authoring surrogate.

Run with Blender --background --factory-startup --python THIS -- MODEL [REPORT].
World-space USD transforms include the exported root. Camera-space rays use the
approved X-axis position rotations. All tolerances are display-shape guards,
not purported manufacturer measurements. No image processing is performed.
"""

from collections import defaultdict
from pathlib import Path
import json
import math
import sys

import numpy as np
from pxr import Gf, Usd, UsdGeom


def inspect_section(asset):
    stage = Usd.Stage.Open(str(asset))
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
        owner_prim = prim
        contact = None
        while owner_prim and not contact:
            contact = owner_prim.GetAttribute("userProperties:contact_id").Get()
            owner_prim = owner_prim.GetParent()
        contact = contact or "body"
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
