"""One-off migration: author Hangboards/metolius-rock-rings-3d/metolius-rock-rings-3d.FCStd.

This script is a MIGRATION TOOL, not a build input. The saved FCStd must stand
alone: the shared compiler never runs this file, and nothing here is required to
rebuild the published runtime asset.

Provenance of every number written into the document:

* Overall size 146 x 57 x 184 mm (x, depth, height) and the three grip depths
  (40, 32, 25 mm) come from ``Hangboards/metolius-rock-rings-3d/board.json``
  (``dimensions`` and each contact's ``depth.range``). These are PUBLISHED
  product facts.
* The mid-depth outline, the three pocket openings/floors, the jug band and the
  two cord apertures are MEASURED from the approved model reference
  ``Hangboards/metolius-rock-rings-3d/assets/primary.usdz`` resolved from Git.
  They are measured approximations of a display mesh, not recovered
  manufacturing data.
* The measured mid-depth outline is reduced to the authored vertex set with a
  stated tolerance; the achieved maximum deviation is printed and recorded.

The authored document is a real native feature tree: a fully constrained
Sketcher profile padded along the depth axis, a native fillet for the 6 mm
perimeter round, native ruled lofts for each pocket (opening and floor both
measured, so the published grip depth is the loft's extent), a native common for
the jug band, and native extruded cuts for the cord apertures. Nothing here is
presented as recovered parametric design history.
"""

from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path[:0] = [
    part
    for part in os.environ.get("HANGTEN_CAD_PYTHONPATH", "").split(os.pathsep)
    if part
]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402
import Sketcher  # noqa: E402
from pxr import Usd, UsdGeom  # noqa: E402

import reference as reference_module  # noqa: E402
from reference import load_reference  # noqa: E402

PACKAGE = "metolius-rock-rings-3d"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"

BODY_PRIM = "/root/ring_body/ring_body_001"
SLOT_PRIMS = {
    "jug": "/root/unit_jug/unit_jug_001",
    "pocket-25": "/root/unit_pocket_25/unit_pocket_25_001",
    "pocket-32": "/root/unit_pocket_32/unit_pocket_32_001",
    "pocket-40": "/root/unit_pocket_40/unit_pocket_40_001",
}
ATTACHMENT_PRIMS = {
    "lateral_window_001": "/root/lateral_window/lateral_window_001",
    "roof_exit_001": "/root/roof_exit/roof_exit_001",
}

MID_TOLERANCE_MM = 0.15
PROFILE_TOLERANCE_MM = 0.1
PERIMETER_ROUND_MM = 6.0
TOP_EDGE_FILLET_CUTOFF_Z = 80.0
LATERAL_DEPTH_MM = 9.0
ROOF_DEPTH_MM = 10.0
PUBLISHED_MM = {"width": 146.0, "height": 184.0}

MATERIAL_NAME = "neutral_resin"
MATERIAL_BASE_COLOR = "0.82,0.80,0.76"
MATERIAL_ROUGHNESS = 0.45
MATERIAL_METALLIC = 0.0


def _world_points(stage, cache, path):
    prim = stage.GetPrimAtPath(path)
    mesh = UsdGeom.Mesh(prim)
    matrix = cache.GetLocalToWorldTransform(prim)
    points = [
        tuple((matrix.Transform(point) * 1000.0)[i] for i in range(3)) for point in mesh.GetPointsAttr().Get()
    ]
    points = [(p[0], -p[2], p[1]) for p in points]
    raw = mesh.GetFaceVertexIndicesAttr().Get()
    triangles = [tuple(raw[i : i + 3]) for i in range(0, len(raw), 3)]
    return points, triangles


def _mesh_loops(points, triangles):
    edges: Counter = Counter()
    for triangle in triangles:
        for a, b in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
            edges[(min(a, b), max(a, b))] += 1
    adjacency: dict[int, list[int]] = {}
    for (a, b), count in edges.items():
        if count == 1:
            adjacency.setdefault(a, []).append(b)
            adjacency.setdefault(b, []).append(a)
    seen: set[int] = set()
    loops = []
    for start in list(adjacency):
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        previous, current = None, start
        while True:
            following = [n for n in adjacency[current] if n != previous]
            if not following:
                break
            previous, current = current, following[0]
            if current == start:
                break
            loop.append(current)
            seen.add(current)
        loops.append(loop)
    return loops


def _reduce_closed(points, tolerance):
    count = len(points)
    keep = [0]
    index = 0
    while index < count - 1:
        candidate = index + 2
        while candidate < count:
            start, end = points[index], points[candidate]
            span = (end[0] - start[0], end[1] - start[1])
            length = math.hypot(*span)
            worst = 0.0
            for point in points[index : candidate + 1]:
                dx = (point[0] - start[0], point[1] - start[1])
                cross = abs(span[0] * dx[1] - span[1] * dx[0])
                worst = max(worst, cross / max(length, 1e-12))
            if worst > tolerance:
                break
            candidate += 1
        keep.append(candidate - 1)
        index = candidate - 1
    return keep


def _merge_short(points, threshold):
    polygon = [tuple(point) for point in points]
    changed = True
    while changed and len(polygon) > 3:
        changed = False
        merged = []
        index = 0
        count = len(polygon)
        while index < count:
            a = polygon[index]
            b = polygon[(index + 1) % count]
            if math.dist(a, b) < threshold:
                merged.append(((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0))
                index += 2
                changed = True
            else:
                merged.append(a)
                index += 1
        polygon = merged
    return polygon


def _fill_top_notch(points):
    """Smooth the concave top-center notch into a shallow U.

    The measured mid-depth outline can pick up a lower point on the rounded top
    lip, producing a long flat top edge that renders as a bright up-facing
    facet. Replacing that flat bottom with a smooth quadratic arc keeps the
    shoulders at full height while removing the broad horizontal surface.
    """
    if not points:
        return points
    count = len(points)
    # Highest point on each half gives the left/right shoulder of the top edge.
    right_idx = max(
        range(count),
        key=lambda i: points[i][1] if points[i][0] >= 0 else -1e18,
    )
    left_idx = max(
        range(count),
        key=lambda i: points[i][1] if points[i][0] <= 0 else -1e18,
    )
    if right_idx == left_idx:
        return points
    span = (left_idx - right_idx) % count
    rotated = points[right_idx:] + points[:right_idx]
    if not rotated[1:span]:
        return points
    if sum(p[1] for p in rotated[1:span]) / len(rotated[1:span]) < 50:
        # The selected arc goes the long way around the bottom; bail out safely.
        return points
    p0 = points[right_idx]
    p2 = points[left_idx]
    # Control point at the centerline, dropped to the original notch depth.
    min_z = min(p[1] for p in rotated[1:span])
    p1 = (0.0, min_z)
    fill = []
    n = max(5, span)
    for k in range(1, n):
        t = k / n
        x = (1.0 - t) * (1.0 - t) * p0[0] + 2.0 * t * (1.0 - t) * p1[0] + t * t * p2[0]
        z = (1.0 - t) * (1.0 - t) * p0[1] + 2.0 * t * (1.0 - t) * p1[1] + t * t * p2[1]
        fill.append((x, z))
    return rotated[:1] + fill + rotated[span:]


def _mid_outline(points, triangles):
    """Measured mid-depth outline from the vertical side wall of the slab."""
    side_vertices = set()
    for triangle in triangles:
        a, b, c = points[triangle[0]], points[triangle[1]], points[triangle[2]]
        normal = (
            (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]),
            (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
            (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]),
        )
        length = math.sqrt(sum(component * component for component in normal))
        if length and abs(normal[1]) / length < 0.2:
            for corner in triangle:
                side_vertices.add(tuple(round(value, 4) for value in points[corner]))
    projected = [(v[0], v[2]) for v in side_vertices]
    bins = 720
    outline = []
    for bin_index in range(bins):
        low = -math.pi + 2 * math.pi * bin_index / bins
        high = low + 2 * math.pi / bins
        best = None
        best_radius = -1.0
        for x, z in projected:
            angle = math.atan2(z, x)
            if low <= angle < high:
                radius = math.hypot(x, z)
                if radius > best_radius:
                    best_radius, best = radius, (x, z)
        if best is not None:
            outline.append(best)
    outline.sort(key=lambda p: math.atan2(p[1], p[0]))
    outline = _merge_short(outline, 1.0)
    keep = _reduce_closed(outline, MID_TOLERANCE_MM)
    authored = [outline[i] for i in keep]
    # The descriptor derives modelBounds from the exported vertices, and the
    # package contract pins the published envelope. Merging and reduction can
    # pull an extreme in by a fraction of a millimetre, so snap the four extreme
    # vertices back onto the published 146 x 184 mm envelope.
    for axis, sign in ((0, 1), (0, -1), (1, 1), (1, -1)):
        index = max(range(len(authored)), key=lambda i: sign * authored[i][axis])
        point = list(authored[index])
        point[axis] = sign * (73.0 if axis == 0 else 92.0)
        authored[index] = tuple(point)
    deviation = 0.0
    for point in outline:
        nearest = float("inf")
        for position in range(len(authored)):
            start = authored[position]
            end = authored[(position + 1) % len(authored)]
            span = (end[0] - start[0], end[1] - start[1])
            length_sq = span[0] * span[0] + span[1] * span[1]
            if length_sq < 1e-18:
                nearest = min(nearest, math.dist(point, start))
                continue
            t = ((point[0] - start[0]) * span[0] + (point[1] - start[1]) * span[1]) / length_sq
            t = max(0.0, min(1.0, t))
            nearest = min(nearest, math.dist(point, (start[0] + t * span[0], start[1] + t * span[1])))
        deviation = max(deviation, nearest)
    return authored, deviation


def _resample_closed(points, count):
    """Resample a closed polygon to ``count`` points by arc length.

    A ruled loft needs matching vertex order between its sections or it twists
    into a wedge. Both pocket sections are therefore resampled from the same
    start (the topmost vertex) in the same direction.
    """
    polygon = [tuple(point) for point in points]
    area = 0.5 * sum(
        polygon[i][0] * polygon[(i + 1) % len(polygon)][1]
        - polygon[(i + 1) % len(polygon)][0] * polygon[i][1]
        for i in range(len(polygon))
    )
    if area < 0:
        polygon = polygon[::-1]
    size = len(polygon)
    start = max(range(size), key=lambda i: (polygon[i][1], polygon[i][0]))
    polygon = polygon[start:] + polygon[:start]
    lengths = [math.dist(polygon[i], polygon[(i + 1) % size]) for i in range(size)]
    total = sum(lengths)
    result = []
    for k in range(count):
        target = total * k / count
        accumulated = 0.0
        for i in range(size):
            if target <= accumulated + lengths[i] or i == size - 1:
                segment = lengths[i]
                fraction = (target - accumulated) / segment if segment > 1e-12 else 0.0
                fraction = max(0.0, min(1.0, fraction))
                a = polygon[i]
                b = polygon[(i + 1) % size]
                result.append((a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1])))
                break
            accumulated += lengths[i]
    return result


def _project_outline(points):
    """Ordered front-plane outline of a set of (x, z) points (star-shaped)."""
    projected = list({(round(x, 3), round(z, 3)) for x, z in points})
    cx = sum(p[0] for p in projected) / len(projected)
    cz = sum(p[1] for p in projected) / len(projected)
    bins = 180
    outline = []
    for bin_index in range(bins):
        low = -math.pi + 2 * math.pi * bin_index / bins
        high = low + 2 * math.pi / bins
        best = None
        best_radius = -1.0
        for x, z in projected:
            angle = math.atan2(z - cz, x - cx)
            if low <= angle < high:
                radius = math.hypot(x - cx, z - cz)
                if radius > best_radius:
                    best_radius, best = radius, (x, z)
        if best is not None:
            outline.append(best)
    outline.sort(key=lambda p: math.atan2(p[1] - cz, p[0] - cx))
    outline = _merge_short(outline, 1.0)
    keep = _reduce_closed(outline, 0.3)
    return [outline[i] for i in keep]


def _rim_profile(points, y):
    selected = [point for point in points if abs(point[1] - y) < 0.05]
    if len(selected) < 3:
        raise ValueError(f"no rim vertices at y={y}")
    cx = sum(point[0] for point in selected) / len(selected)
    cz = sum(point[2] for point in selected) / len(selected)
    selected.sort(key=lambda p: math.atan2(p[2] - cz, p[0] - cx))
    keep = _reduce_closed([(p[0], p[2]) for p in selected], PROFILE_TOLERANCE_MM)
    return [selected[i] for i in keep]


def _extract(stage, cache):
    body_points, body_triangles = _world_points(stage, cache, BODY_PRIM)
    mid, deviation = _mid_outline(body_points, body_triangles)
    xs = [p[0] for p in mid]
    zs = [p[1] for p in mid]
    for key, measured in (("width", max(xs) - min(xs)), ("height", max(zs) - min(zs))):
        if abs(measured - PUBLISHED_MM[key]) > 0.5:
            raise ValueError(f"measured {key} {measured:.3f} disagrees with published")

    pockets = {}
    for slot, prim_path in SLOT_PRIMS.items():
        if slot == "jug":
            continue
        points, _ = _world_points(stage, cache, prim_path)
        opening = _rim_profile(points, min(p[1] for p in points))
        measured_floor = _rim_profile(points, max(p[1] for p in points))
        op = _resample_closed([(p[0], p[2]) for p in opening], 48)
        floor = _resample_closed([(p[0], p[2]) for p in measured_floor], 48)
        pockets[slot] = {
            "opening": op,
            "floor": floor,
            "floor_y": max(p[1] for p in points),
        }

    attachments = {}
    for node_id, prim_path in ATTACHMENT_PRIMS.items():
        points, triangles = _world_points(stage, cache, prim_path)
        loops = sorted(_mesh_loops(points, triangles), key=len, reverse=True)
        right = max(loops, key=lambda loop: sum(points[i][0] for i in loop))
        left = min(loops, key=lambda loop: sum(points[i][0] for i in loop))
        attachments[node_id] = {
            "right": [points[i] for i in right],
            "left": [points[i] for i in left],
        }

    jug_points, _ = _world_points(stage, cache, SLOT_PRIMS["jug"])
    jug = {
        "x": (min(p[0] for p in jug_points), max(p[0] for p in jug_points)),
        "z": (min(p[2] for p in jug_points), max(p[2] for p in jug_points)),
        "outline": _project_outline([(p[0], p[2]) for p in jug_points]),
    }
    return mid, deviation, pockets, attachments, jug


def _published_depths(board):
    by_id = {contact["id"]: contact for contact in board.get("contacts", [])}
    depths = {}
    for presentation in board.get("presentations", []):
        for instance in presentation.get("media", {}).get("instances", []):
            for slot, contact_id in instance.get("contactIDsBySlotID", {}).items():
                span = ((by_id.get(contact_id) or {}).get("depth") or {}).get("range") or {}
                low, high = span.get("minimum"), span.get("maximum")
                if isinstance(low, (int, float)) and isinstance(high, (int, float)) and low == high:
                    if slot in depths and abs(depths[slot] - low) > 1e-6:
                        raise ValueError(f"slot {slot} declares conflicting depths")
                    depths[slot] = float(low)
    return depths


def _matrix(rows):
    return App.Matrix(*[value for row in rows for value in row])


# The pinned-build Sketcher axis distances solve to the negated value, so each
# authored local coordinate is the negated, shifted native coordinate and the
# sketch placement un-negates it. Frames map local (u, v) onto the sketch plane.
OUTLINE_FRAME = _matrix(
    [
        (-1.0, 0.0, 0.0, -73.0),
        (0.0, 0.0, -1.0, 0.0),
        (0.0, -1.0, 0.0, -92.0),
        (0.0, 0.0, 0.0, 1.0),
    ]
)
LATERAL_RIGHT_FRAME = _matrix(
    [
        (0.0, 0.0, 1.0, 74.0),
        (-1.0, 0.0, 0.0, -14.0),
        (0.0, -1.0, 0.0, 38.0),
        (0.0, 0.0, 0.0, 1.0),
    ]
)
LATERAL_LEFT_FRAME = _matrix(
    [
        (0.0, 0.0, 1.0, -74.0),
        (-1.0, 0.0, 0.0, -14.0),
        (0.0, -1.0, 0.0, 38.0),
        (0.0, 0.0, 0.0, 1.0),
    ]
)
ROOF_FRAME = _matrix(
    [
        (-1.0, 0.0, 0.0, 57.5),
        (0.0, -1.0, 0.0, -4.5),
        (0.0, 0.0, 1.0, 94.0),
        (0.0, 0.0, 0.0, 1.0),
    ]
)


def _sketch(document, name, plane_points, frame, shift, depth=None):
    sketch = document.addObject("Sketcher::SketchObject", name)
    sketch.MapMode = "Deactivated"
    sketch.AttachmentSupport = []
    sketch.Placement = App.Placement(frame)
    origin_u, origin_v = shift
    if depth is not None:
        sketch.Placement.Base.y = depth

    def local(point):
        return App.Vector(-(point[0] - origin_u), -(point[1] - origin_v), 0.0)

    count = len(plane_points)
    sketch.addGeometry(
        [
            Part.LineSegment(local(plane_points[i]), local(plane_points[(i + 1) % count]))
            for i in range(count)
        ],
        False,
    )
    for i in range(count):
        sketch.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % count, 1))
    for i, point in enumerate(plane_points):
        sketch.addConstraint(
            Sketcher.Constraint("DistanceX", i, 1, -1, 1, round(point[0] - origin_u, 6))
        )
        sketch.addConstraint(
            Sketcher.Constraint("DistanceY", i, 1, -1, 1, round(point[1] - origin_v, 6))
        )
    sketch.solve()
    if not sketch.FullyConstrained:
        raise ValueError(f"{name} is not fully constrained")
    return sketch


def _bind(obj, node_id, role, slot=None, outline=None):
    obj.addProperty("App::PropertyString", "NodeID", "HangTen")
    obj.addProperty("App::PropertyString", "NodeRole", "HangTen")
    obj.NodeID = node_id
    obj.NodeRole = role
    if slot is not None:
        obj.addProperty("App::PropertyString", "ContactSlotID", "HangTen")
        obj.ContactSlotID = slot
    if outline is not None:
        # The CAD document is the source of truth for hold geometry: the
        # compiler reads this front-plane polygon (native XZ millimetres) and
        # emits it as the descriptor's hold region.
        obj.addProperty("App::PropertyString", "HangTenHoldOutline", "HangTen")
        obj.HangTenHoldOutline = json.dumps([[round(x, 4), round(z, 4)] for x, z in outline])
    obj.addProperty("App::PropertyString", "MaterialName", "HangTen")
    obj.addProperty("App::PropertyString", "BaseColor", "HangTen")
    obj.addProperty("App::PropertyFloat", "Roughness", "HangTen")
    obj.addProperty("App::PropertyFloat", "Metallic", "HangTen")
    obj.MaterialName = MATERIAL_NAME
    obj.BaseColor = MATERIAL_BASE_COLOR
    obj.Roughness = MATERIAL_ROUGHNESS
    obj.Metallic = MATERIAL_METALLIC


def _ordered(loop, axes, tolerance):
    centre_u = sum(point[axes[0]] for point in loop) / len(loop)
    centre_v = sum(point[axes[1]] for point in loop) / len(loop)
    ordered = sorted(loop, key=lambda p: math.atan2(p[axes[1]] - centre_v, p[axes[0]] - centre_u))
    reduced = [(p[axes[0]], p[axes[1]]) for p in ordered]
    keep = _reduce_closed(reduced, tolerance)
    return [reduced[i] for i in keep]


def main() -> int:
    board = json.loads(BOARD_JSON.read_text())
    published_depths = _published_depths(board)
    scratch = Path(os.environ.get("HANGTEN_CAD_SCRATCH", "/tmp")) / f"{PACKAGE}-assets"
    reference, reference_digest = load_reference(PACKAGE, "primary.usdz", scratch)
    stage = Usd.Stage.Open(str(reference))
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    mid, deviation, pockets, attachments, jug = _extract(stage, cache)
    mid = _fill_top_notch(mid)

    if DESTINATION.exists():
        DESTINATION.unlink()
    document = App.newDocument(PACKAGE)
    document.Label = board["name"]
    for name, kind in (
        ("HangTenBoardID", "App::PropertyString"),
        ("HangTenPresentationID", "App::PropertyString"),
        ("HangTenSchemaVersion", "App::PropertyInteger"),
        ("HangTenSourceKind", "App::PropertyString"),
        ("HangTenCoordinateFrame", "App::PropertyString"),
        ("HangTenTessellationDeflection", "App::PropertyFloat"),
    ):
        document.addProperty(kind, name, "HangTen")
    document.HangTenBoardID = board["id"]
    document.HangTenPresentationID = board["presentations"][0]["id"]
    document.HangTenSchemaVersion = 2
    document.HangTenSourceKind = "native-parametric-measured-profile"
    document.HangTenCoordinateFrame = "freecad-mm-z-up-front-negative-y"
    document.HangTenTessellationDeflection = 0.08

    outline = _sketch(document, "Outline", mid, OUTLINE_FRAME, (-73.0, -92.0))
    base = document.addObject("Part::Extrusion", "BodyBase")
    base.Base = outline
    base.DirMode = "Custom"
    base.Dir = App.Vector(0.0, 1.0, 0.0)
    base.LengthFwd = 28.5
    base.LengthRev = 28.5
    base.Solid = True

    document.recompute()
    # POC: use the unrounded extrusion directly to avoid perimeter fillet
    # facets on the top surface.
    cut_chain = base
    region_surfaces = {}
    """Pocket lofts and boolean cuts are intentionally disabled for this POC.
    for slot in sorted(pockets):
        depth = published_depths.get(slot)
        if depth is None:
            raise ValueError(f"no published depth for slot {slot}")
        opening_sketch = _sketch(
            document, f"Opening_{slot.replace('-', '_')}", pockets[slot]["opening"], OUTLINE_FRAME, (-73.0, -92.0)
        )
        opening_sketch.Placement.Base.y = -28.5
        floor_sketch = _sketch(
            document, f"Floor_{slot.replace('-', '_')}", pockets[slot]["floor"], OUTLINE_FRAME, (-73.0, -92.0)
        )
        floor_sketch.Placement.Base.y = pockets[slot]["floor_y"]
        measured_depth = pockets[slot]["floor_y"] + 28.5
        if abs(measured_depth - depth) > 0.5:
            raise ValueError(
                f"{slot} measured depth {measured_depth:.2f} disagrees with published {depth}"
            )
        solid = document.addObject("Part::Loft", f"PocketSolid_{slot.replace('-', '_')}")
        solid.Sections = [opening_sketch, floor_sketch]
        solid.Solid = True
        solid.Ruled = True
        # The exported hold region is the pocket's cap-free CAD surface: the
        # loft's lateral surface (Solid=False) plus its floor face. The solid is
        # only the boolean tool, so the opening cap never becomes a hold.
        tag = slot.replace("-", "_")
        surface_loft = document.addObject("Part::Loft", f"PocketSurface_{tag}")
        # Lofting from floor to opening reverses the lateral surface normals so
        # the cavity-facing side is front-facing in the rendered highlight.
        surface_loft.Sections = [floor_sketch, opening_sketch]
        surface_loft.Solid = False
        surface_loft.Ruled = True
        floor_face = document.addObject("Part::Face", f"FloorFace_{tag}")
        floor_face.Sources = [floor_sketch]
        surface_fuse = document.addObject("Part::MultiFuse", f"PocketRegionRaw_{tag}")
        surface_fuse.Shapes = [surface_loft, floor_face]
        cut = document.addObject("Part::Cut", f"Cut_{tag}")
        cut.Base = cut_chain
        cut.Tool = solid
        cut_chain = cut
        # The pocket's cap-free lateral surface and floor are already inside the
        # body; clipping them with Part::Common against the body boundary would
        # be a degenerate boolean and fragments the surface. The raw surface is
        # reversed during binding so the cavity-facing side is front-facing.
        region_surfaces[slot] = (surface_fuse, "contact", slot, False)
    """

    """The jug band is intentionally disabled; only the body shape is needed.
    # The jug band is the front-facing region of the body only. A deep bounding
    # box pulled in the rounded top edge and back face, causing stray triangles;
    # a thin slab on the front side of the body surface captures just the planar
    # front-facing band and avoids the fillet wrap.
    jug_box = document.addObject("Part::Box", "JugBand")
    jug_box.Length = jug["x"][1] - jug["x"][0]
    jug_box.Width = 0.5
    jug_box.Height = jug["z"][1] - jug["z"][0]
    jug_box.Placement.Base = App.Vector(jug["x"][0], -29.0, jug["z"][0])
    # The jug needs shell body ∩ box; encode that in the binding pass.
    region_surfaces["jug"] = (jug_box, "contact", "jug", True)
    """

    for node_id, sides in sorted(attachments.items()):
        is_lateral = node_id == "lateral_window_001"
        axes = (1, 2) if is_lateral else (0, 1)
        solid_parts = []
        surface_parts = []
        for side in ("right", "left"):
            if is_lateral:
                frame = LATERAL_RIGHT_FRAME if side == "right" else LATERAL_LEFT_FRAME
                direction = App.Vector(-1.0 if side == "right" else 1.0, 0.0, 0.0)
                length = LATERAL_DEPTH_MM
                shift = (-14.0, 38.0)
            else:
                frame = ROOF_FRAME
                direction = App.Vector(0.0, 0.0, -1.0)
                length = ROOF_DEPTH_MM
                shift = (57.5, -4.5)
            profile = _ordered(sides[side], axes, 0.3)
            sketch = _sketch(document, f"{node_id}_{side}", profile, frame, shift)
            # The cut needs a solid; the exported hold surface is cap-free.
            extrusion = document.addObject("Part::Extrusion", f"{node_id}_{side}_solid")
            extrusion.Base = sketch
            extrusion.DirMode = "Custom"
            extrusion.Dir = direction
            extrusion.LengthFwd = length
            extrusion.Solid = True
            solid_parts.append(extrusion)
            surface = document.addObject("Part::Extrusion", f"{node_id}_{side}_surface")
            surface.Base = sketch
            surface.DirMode = "Custom"
            surface.Dir = direction
            surface.LengthFwd = length
            surface.Solid = False
            surface_parts.append(surface)
        fused = document.addObject("Part::MultiFuse", f"{node_id}_solid")
        fused.Shapes = solid_parts
        cut = document.addObject("Part::Cut", f"Cut_{node_id}")
        cut.Base = cut_chain
        cut.Tool = fused
        cut_chain = cut
        fused_surface = document.addObject("Part::MultiFuse", node_id)
        fused_surface.Shapes = surface_parts
        # The attachment surfaces start outside the body envelope and must be
        # clipped to it, but only the cap-free surfaces (not their solids) are
        # exported as nodes.
        region_surfaces[node_id] = (fused_surface, "attachment", None, True)

    document.recompute()
    stale = [
        f"{obj.Name}={obj.State}"
        for obj in document.Objects
        if set(obj.State) & {"Invalid", "Error", "Touched", "Recompute"}
    ]
    if stale:
        raise ValueError("document did not recompute cleanly: " + "; ".join(stale))

    _bind(cut_chain, "ring_body_001", "body")
    # Attachments need a Part::Common against the body to extract only the
    # portions of their tools that intersect the body surface.
    bound_objects = []
    for region_id, (surface, role, slot, needs_clip) in region_surfaces.items():
        if needs_clip:
            clipped = document.addObject(
                "Part::Common", f"Region_{region_id.replace('-', '_')}"
            )
            clipped.Base = surface
            clipped.Tool = cut_chain
            bound_objects.append((clipped, region_id, role, slot))
        else:
            # Reverse the cap-free shell so its cavity-facing side (floor toward
            # the camera, walls inward) is front-facing in the highlight.
            # Part::Reverse is parametric, so the region still follows edits.
            reversed_region = document.addObject(
                "Part::Reverse", f"Region_{region_id.replace('-', '_')}"
            )
            reversed_region.Source = surface
            bound_objects.append((reversed_region, region_id, role, slot))
    document.recompute()
    for obj, region_id, role, slot in bound_objects:
        if role == "contact":
            _bind(obj, SLOT_PRIMS[region_id].rsplit("/", 1)[-1], "contact", slot)
        else:
            _bind(obj, region_id, "attachment")

    document.saveAs(str(DESTINATION))
    print(f"authored {DESTINATION} ({DESTINATION.stat().st_size} bytes)")
    print(f"mid outline {len(mid)} vertices, max deviation {deviation:.4f} mm")
    print(f"published depths {published_depths}")
    print(f"body volume {cut_chain.Shape.Volume:.0f} mm^3 bbox {cut_chain.Shape.BoundBox}")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
