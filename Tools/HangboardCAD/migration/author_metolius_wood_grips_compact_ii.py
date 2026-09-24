"""One-off migration: author Hangboards/metolius-wood-grips-compact-ii/*.FCStd.

Migration tool only -- not a build input. The saved FCStd stands alone.

Acceptance bar (declared up front): the approved asset is a sculpted display
shell (rolled front/back edges, a depth-varying top with a rolled jug, pitched
flat slopers and a convex round sloper), so the native source is a *measured
approximation*. ``compare_exports`` is evidence, not a gate. The node/role
inventory, published 29 / 19 mm region depths, the 610 x 157 mm face, and
descriptor ``facePlaneAABB`` agreement with the reference are the acceptance
signals.

Provenance (native mm, +X right, +Z up, front -Y):

Published (manufacturer):
* Face 610 x 157 mm (24 x 6.2 in) -- Metolius Wood Grips II product page,
  https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards
  (also ``board.json`` ``dimensions``).
* Hold inventory and grip depths -- the official numbered Wood Grips Compact
  diagram on the same page
  (https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg):
  #1 outer jugs, #2 56 mm flat slopers, #3 29 mm edges, #4 29 mm three-finger
  pockets, #5 29 mm two-finger pockets, #6 19 mm edges, #7 19 mm three-finger
  pockets, #8 19 mm two-finger pockets, #9 56 mm round sloper, #10 29 mm
  four-finger pocket, #11 19 mm four-finger pocket. The 29 / 19 mm values are
  the region depths the compiler gates on.
* Relative placement: the manufacturer front photograph
  (https://www.metoliusclimbing.com/cdn/shop/files/Wood-Grips-II-Compact-Training-Board.jpg)
  shows two rows of five pockets between side-open edges, jugs at both ends of
  the top, flat slopers either side of a central round sloper.

Retained authored estimates (not manufacturer dimensions):
* Every numeric silhouette control point, pocket centre/width/height, edge
  recess size, fillet radius, top-profile drop, and the 64 mm body depth below
  is carried verbatim from the approved pre-migration model's authoring script
  (``Tools/HangboardModels/wood_grips_compact_ii.py``, last present at
  ``d7ca9c5c9^``). That script states the values were drawn by hand from the
  manufacturer photograph and are display estimates; Metolius publishes no
  body thickness, pocket aperture, radius, or back profile for this board. The
  reference USDZ is resolved from Git only to confirm the envelope.
* Six physical mounting holes and the engraved logos are deliberately omitted
  (repository screw-hole/hardware omission policy).

Construction: the body is a closed polyhedral solid built from the silhouette
at a series of depth stations (each station is the silhouette offset along its
inward normal by the front/back roll inset, with the top lowered by the
depth-dependent jug/sloper profile). Every face is a planar quad or triangle so
contact partitioning by the compiler is exact. Each pocket and side-open edge
is a planar-faced ruled cutter (capsule / rounded rectangle stations with a
back fillet and a flared mouth fillet). One ``Part::Cut`` removes all cutters;
the result is baked into the exported ``BodySolid``. Contacts are faces of the
cut body: a pocket/edge region is every body face lying on that hold's cutter,
and the top regions (jugs, flat slopers, round sloper) are the up-facing top
faces partitioned at the same x boundaries the reference used.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import zipfile
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
from pxr import Usd, UsdGeom  # noqa: E402

from reference import load_reference  # noqa: E402

PACKAGE = "metolius-wood-grips-compact-ii"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
SCRATCH = Path(
    os.environ.get(
        "HANGTEN_CAD_SCRATCH",
        str(REPOSITORY / ".context" / f"freecad-{PACKAGE}"),
    )
)

# Published face (manufacturer): 610 x 157 mm.
FACE_WIDTH = 610.0
FACE_HEIGHT = 157.0
# Retained display estimate (no published thickness).
BODY_DEPTH = 64.0

# Retained silhouette: cubic spans in left-origin (x, h) mm, left half only,
# mirrored about x = 305. Drawn by hand from the manufacturer photograph in the
# pre-migration model; display estimates, not manufacturer dimensions.
SPANS = [
    ((305, 151), (268, 151), (228, 151), (204, 151)),
    ((204, 151), (197, 151), (198, 146), (190, 146)),
    ((190, 146), (163, 146), (133, 146), (111, 146)),
    ((111, 146), (103, 146), (103, 157), (94, 157)),
    ((94, 157), (72, 157), (44, 157), (29, 155)),
    ((29, 155), (10, 153), (0, 148), (0, 139)),
    ((0, 139), (0, 128), (14, 110), (16, 88)),
    ((16, 88), (18, 76), (13, 75), (16, 68)),
    ((16, 68), (20, 62), (23, 52), (24, 40)),
    ((24, 40), (26, 25), (26, 20), (25, 15)),
    ((25, 15), (23, 6), (34, 0), (48, 0)),
    ((48, 0), (112, 0), (222, 0), (305, 0)),
]
SPAN_STEPS = 8

# Top-region x boundaries (left-origin), identical to the reference partition.
JUG_LIMIT = 106.0
FLAT_SLOPER_LIMIT = 196.0
TOP_REGION_MIN_H = 126.0
TOP_REGION_MIN_NORMAL_Z = 0.12

# Retained pocket layout (depth, centre h, outer-pocket x, inner-pocket x,
# three-finger width, two-finger width); all pockets are 25 mm tall capsules,
# the centre four-finger pocket is 96 mm wide.
POCKET_LAYOUT = [
    (29.0, 88.0, 151.0, 221.0, 66.0, 46.0),
    (19.0, 29.0, 161.0, 224.5, 62.0, 39.0),
]
POCKET_HEIGHT = 25.0
CENTER_POCKET_WIDTH = 96.0
POCKET_BACK_FILLET = 4.5
POCKET_MOUTH_FILLET = 3.5

# Retained side-open edge recesses (depth, centre h, width, height, centre x),
# corner radius 8 mm, 6 mm back and mouth fillets.
EDGE_LAYOUT = [
    (29.0, 98.0, 119.0, 48.0, 39.0),
    (19.0, 34.0, 131.0, 43.0, 43.0),
]
EDGE_RADIUS = 8.0
EDGE_FILLET = 6.0

FILLET_STEPS = 6
ARC_STEPS = 8
MOUTH_OVERSHOOT = 20.0

NODE_IDS = {
    "edge-19-left": "Wood_Grips_Compact_II_020",
    "edge-19-right": "Wood_Grips_Compact_II_021",
    "edge-29-left": "Wood_Grips_Compact_II_022",
    "edge-29-right": "Wood_Grips_Compact_II_023",
    "jug-left": "Wood_Grips_Compact_II_024",
    "jug-right": "Wood_Grips_Compact_II_025",
    "pocket-19-four-center": "Wood_Grips_Compact_II_026",
    "pocket-19-three-left": "Wood_Grips_Compact_II_027",
    "pocket-19-three-right": "Wood_Grips_Compact_II_028",
    "pocket-19-two-left": "Wood_Grips_Compact_II_029",
    "pocket-19-two-right": "Wood_Grips_Compact_II_030",
    "pocket-29-four-center": "Wood_Grips_Compact_II_031",
    "pocket-29-three-left": "Wood_Grips_Compact_II_032",
    "pocket-29-three-right": "Wood_Grips_Compact_II_033",
    "pocket-29-two-left": "Wood_Grips_Compact_II_034",
    "pocket-29-two-right": "Wood_Grips_Compact_II_035",
    "sloper-flat-left": "Wood_Grips_Compact_II_036",
    "sloper-flat-right": "Wood_Grips_Compact_II_037",
    "sloper-round-center": "Wood_Grips_Compact_II_038",
    "body": "Wood_Grips_Compact_II_039",
}

MATERIAL_NAME = "canonical_neutral_wood"
MATERIAL_BASE_COLOR = "0.69,0.49,0.28"
MATERIAL_ROUGHNESS = 0.62
MATERIAL_METALLIC = 0.0

PLANAR_TOLERANCE = 1e-7


def native(x_left: float, h: float, d: float) -> App.Vector:
    """Left-origin width, bottom-origin height, depth-from-back -> native mm."""
    return App.Vector(x_left - FACE_WIDTH / 2.0, -d, h)


# --------------------------------------------------------------------------
# Silhouette


def _cubic(p0, p1, p2, p3, t):
    return tuple(
        (1 - t) ** 3 * p0[k]
        + 3 * (1 - t) ** 2 * t * p1[k]
        + 3 * (1 - t) * t * t * p2[k]
        + t**3 * p3[k]
        for k in range(2)
    )


def _is_straight(span) -> bool:
    (x0, y0), (x3, y3) = span[0], span[3]
    for x, y in span[1:3]:
        cross = (x3 - x0) * (y - y0) - (y3 - y0) * (x - x0)
        if abs(cross) > 1e-9:
            return False
    return True


def _split_at_x(points, targets):
    """Insert a vertex wherever a top segment crosses a region boundary."""
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        crossings = []
        for target in targets:
            if min(a[0], b[0]) < target < max(a[0], b[0]) and min(a[1], b[1]) > 120:
                t = (target - a[0]) / (b[0] - a[0])
                crossings.append((t, (target, a[1] + t * (b[1] - a[1]))))
        for _t, point in sorted(crossings):
            out.append(point)
        out.append(b)
    return out


def silhouette():
    left = []
    for span in SPANS:
        steps = 1 if _is_straight(span) else SPAN_STEPS
        for index in range(steps):
            left.append(_cubic(*span, index / steps))
    left.append((FACE_WIDTH / 2.0, 0.0))
    left = _split_at_x(left, (JUG_LIMIT, FLAT_SLOPER_LIMIT))
    outline = left + [(FACE_WIDTH - x, h) for x, h in reversed(left[1:-1])]
    count = len(outline)
    inward = []
    for index in range(count):
        before, after = outline[index - 1], outline[(index + 1) % count]
        dx, dh = after[0] - before[0], after[1] - before[1]
        length = math.hypot(dx, dh)
        inward.append((-dh / length, dx / length))
    return outline, inward


def _smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def top_profile(x, h, d):
    """Retained depth-dependent top: rolled jugs, pitched flat, convex round."""
    if h <= 132:
        return h
    mirrored_x = min(x, FACE_WIDTH - x)
    sloper_depth = 56.0
    jug_t = max(0.0, min(1.0, (d - (BODY_DEPTH - 34)) / 34))
    sloper_t = max(0.0, min(1.0, (d - (BODY_DEPTH - sloper_depth)) / sloper_depth))
    jug_drop = 18 * (h - 132) / 25 * (1 - math.sqrt(max(0.0, 1 - jug_t * jug_t)))
    flat_drop = 8 * (h - 132) / 14 * sloper_t
    center_drop = 16 * (h - 132) / 19 * (1 - math.sqrt(max(0.0, 1 - sloper_t * sloper_t)))
    jug_mix = _smoothstep(99, 113, mirrored_x)
    center_mix = _smoothstep(185, 204, mirrored_x)
    drop = (jug_drop * (1 - jug_mix) + flat_drop * jug_mix) * (1 - center_mix) + center_drop * center_mix
    return h - drop


def roll_inset(h, d):
    """2 mm back roll; 7 mm (bottom rail) to 2 mm (top) front roll."""
    radius = 7 - 5 * _smoothstep(15, 40, h)
    if d < 2:
        return 2 - math.sqrt(max(0.0, 4 - (d - 2) ** 2))
    if d > BODY_DEPTH - radius:
        return radius - math.sqrt(max(0.0, radius**2 - (d - (BODY_DEPTH - radius)) ** 2))
    return 0.0


def depth_stations():
    stations = {0.0, 0.25, 0.6, 1.2, 2.0}
    stations.update(float(value) for value in range(4, 57, 4))
    for index in range(1, 9):
        stations.add(round(57 + 7 * math.sin(index * math.pi / 16), 6))
    for index in range(1, 5):
        stations.add(round(62 + 2 * math.sin(index * math.pi / 8), 6))
    stations.add(BODY_DEPTH)
    return sorted(stations)


# --------------------------------------------------------------------------
# Planar polyhedron builder


def _planar(points) -> bool:
    a, b, c = points[0], points[1], points[2]
    normal = (b - a).cross(c - a)
    if normal.Length < 1e-12:
        return False
    normal.normalize()
    return all(abs((p - a).dot(normal)) < PLANAR_TOLERANCE for p in points[3:])


def _signed_volume(polygons) -> float:
    volume = 0.0
    for polygon in polygons:
        a = polygon[0]
        for b, c in zip(polygon[1:], polygon[2:]):
            volume += a.dot(b.cross(c))
    return volume / 6.0


def _polyhedron(polygons):
    if _signed_volume(polygons) < 0:
        polygons = [list(reversed(polygon)) for polygon in polygons]
    faces = [Part.Face(Part.makePolygon(list(polygon) + [polygon[0]])) for polygon in polygons]
    shell = Part.makeShell(faces)
    if not shell.isClosed():
        raise ValueError("polyhedral shell is not closed")
    solid = Part.makeSolid(shell)
    if solid.Volume <= 0 or not solid.isValid():
        raise ValueError(f"invalid polyhedral solid (volume {solid.Volume})")
    return solid


def _ring_polygons(rings, mirror_left_of=None):
    """Side quads (or triangle pairs where non-planar) plus the two end caps."""
    count = len(rings[0])
    polygons = [list(reversed(rings[0])), list(rings[-1])]
    for near, far in zip(rings, rings[1:]):
        for index in range(count):
            following = (index + 1) % count
            a, b, c, d = near[index], near[following], far[following], far[index]
            if _planar([a, b, c, d]):
                polygons.append([a, b, c, d])
            elif mirror_left_of is not None and (a.x + b.x) / 2.0 > mirror_left_of:
                # Reflected diagonal so mirrored halves facet identically.
                polygons += [[a, b, d], [b, c, d]]
            else:
                polygons += [[a, b, c], [a, c, d]]
    return polygons


def body_solid():
    outline, inward = silhouette()
    rings = []
    for d in depth_stations():
        ring = []
        for (x, h), (nx, nh) in zip(outline, inward):
            inset = roll_inset(h, d)
            ring.append(native(x + nx * inset, top_profile(x, h, d) + nh * inset, d))
        rings.append(ring)
    solid = _polyhedron(_ring_polygons(rings, mirror_left_of=0.0))
    # Merge coplanar neighbours (the constant-section lower body between the
    # rolls); top-region faces are checked against the partition boundaries in
    # classify_faces so a merge can never straddle two holds.
    refined = solid.removeSplitter()
    if not refined.isValid() or abs(refined.Volume - solid.Volume) > 1e-3:
        raise ValueError("refining the envelope changed its volume")
    return refined


# --------------------------------------------------------------------------
# Hold cutters


def _rounded_rect(cx, cy, width, height, radius):
    points = []
    corners = [
        (cx + width / 2 - radius, cy + height / 2 - radius, 0),
        (cx - width / 2 + radius, cy + height / 2 - radius, 90),
        (cx - width / 2 + radius, cy - height / 2 + radius, 180),
        (cx + width / 2 - radius, cy - height / 2 + radius, 270),
    ]
    for ox, oy, start in corners:
        for index in range(ARC_STEPS + 1):
            theta = math.radians(start + index * 90 / ARC_STEPS)
            points.append((ox + radius * math.cos(theta), oy + radius * math.sin(theta)))
    clean = []
    for point in points:
        if not clean or math.dist(point, clean[-1]) > 1e-6:
            clean.append(point)
    if math.dist(clean[0], clean[-1]) < 1e-6:
        clean.pop()
    return clean


def recess_stations(depth, back_r, mouth_r):
    """(depth-from-back, inset) stations: floor fillet, wall, flared mouth."""
    stations = [
        (
            BODY_DEPTH - depth + back_r * (1 - math.cos(i * math.pi / 2 / FILLET_STEPS)),
            back_r * (1 - math.sin(i * math.pi / 2 / FILLET_STEPS)),
        )
        for i in range(FILLET_STEPS + 1)
    ]
    stations += [
        (
            BODY_DEPTH - mouth_r + mouth_r * math.sin(i * math.pi / 2 / FILLET_STEPS),
            -mouth_r * (1 - math.cos(i * math.pi / 2 / FILLET_STEPS)),
        )
        for i in range(FILLET_STEPS + 1)
    ]
    stations.append((BODY_DEPTH + MOUTH_OVERSHOOT, -mouth_r))
    return stations


def recess_cutter(cx, cy, width, height, depth, radius, back_r, mouth_r):
    rings = []
    for d, inset in recess_stations(depth, back_r, mouth_r):
        corner = max(1.0, radius - inset)
        points = _rounded_rect(cx, cy, width - 2 * inset, height - 2 * inset, corner)
        rings.append([native(x, h, d) for x, h in points])
    counts = {len(ring) for ring in rings}
    if len(counts) != 1:
        raise ValueError(f"recess stations disagree on vertex count: {counts}")
    return _polyhedron(_ring_polygons(rings))


def mouth_outline(cx, cy, width, height, radius, mouth_r):
    """Front-plane opening of a recess (native [x, z]), the tap target."""
    points = _rounded_rect(cx, cy, width + 2 * mouth_r, height + 2 * mouth_r, radius + mouth_r)
    return [[round(x - FACE_WIDTH / 2.0, 4), round(h, 4)] for x, h in points]


def hold_cutters():
    """{contact id: (cutter solid, outline or None)} in left-origin layout."""
    cutters = {}
    for depth, cy, outer, inner, outer_w, inner_w in POCKET_LAYOUT:
        tag = int(depth)
        for side, sign in (("left", 1), ("right", -1)):
            place = (lambda v: v) if sign == 1 else (lambda v: FACE_WIDTH - v)
            for kind, cx, width in (("three", outer, outer_w), ("two", inner, inner_w)):
                radius = POCKET_HEIGHT / 2
                cutters[f"pocket-{tag}-{kind}-{side}"] = (
                    recess_cutter(place(cx), cy, width, POCKET_HEIGHT, depth, radius,
                                  POCKET_BACK_FILLET, POCKET_MOUTH_FILLET),
                    mouth_outline(place(cx), cy, width, POCKET_HEIGHT, radius, POCKET_MOUTH_FILLET),
                )
        radius = POCKET_HEIGHT / 2
        cutters[f"pocket-{tag}-four-center"] = (
            recess_cutter(FACE_WIDTH / 2, cy, CENTER_POCKET_WIDTH, POCKET_HEIGHT, depth, radius,
                          POCKET_BACK_FILLET, POCKET_MOUTH_FILLET),
            mouth_outline(FACE_WIDTH / 2, cy, CENTER_POCKET_WIDTH, POCKET_HEIGHT, radius,
                          POCKET_MOUTH_FILLET),
        )
    for depth, cy, width, height, cx in EDGE_LAYOUT:
        tag = int(depth)
        for side, x in (("left", cx), ("right", FACE_WIDTH - cx)):
            # Side-open: the outline is the face-plane region, clipped later to
            # the body's own extent by the region bounding box.
            cutters[f"edge-{tag}-{side}"] = (
                recess_cutter(x, cy, width, height, depth, EDGE_RADIUS, EDGE_FILLET, EDGE_FILLET),
                None,
            )
    return cutters


# --------------------------------------------------------------------------
# Face classification


def _face_sample(face):
    """A point on the face and the outward normal there."""
    points, triangles = face.tessellate(0.1)
    if not triangles:
        raise ValueError("face has no tessellation")
    best = max(
        triangles,
        key=lambda t: (points[t[1]] - points[t[0]]).cross(points[t[2]] - points[t[0]]).Length,
    )
    centroid = (points[best[0]] + points[best[1]] + points[best[2]]) / 3.0
    u, v = face.Surface.parameter(centroid)
    return centroid, face.normalAt(u, v)


def classify_faces(body_shape, cutters):
    regions = {contact_id: [] for contact_id in cutters}
    for top in ("jug-left", "sloper-flat-left", "sloper-round-center", "sloper-flat-right", "jug-right"):
        regions[top] = []
    vertex = Part.Vertex
    for face in body_shape.Faces:
        point, normal = _face_sample(face)
        owner = None
        for contact_id, (cutter, _outline) in cutters.items():
            box = cutter.BoundBox
            if not (box.XMin - 0.5 <= point.x <= box.XMax + 0.5
                    and box.ZMin - 0.5 <= point.z <= box.ZMax + 0.5):
                continue
            if cutter.distToShape(vertex(point))[0] < 1e-5:
                owner = contact_id
                break
        if owner is None and point.z > TOP_REGION_MIN_H and normal.z > TOP_REGION_MIN_NORMAL_Z:
            x = point.x + FACE_WIDTH / 2.0
            owner = (
                "jug-left" if x < JUG_LIMIT
                else "sloper-flat-left" if x < FLAT_SLOPER_LIMIT
                else "sloper-round-center" if x < FACE_WIDTH - FLAT_SLOPER_LIMIT
                else "sloper-flat-right" if x < FACE_WIDTH - JUG_LIMIT
                else "jug-right"
            )
            box = face.BoundBox
            for boundary in (JUG_LIMIT, FLAT_SLOPER_LIMIT,
                             FACE_WIDTH - FLAT_SLOPER_LIMIT, FACE_WIDTH - JUG_LIMIT):
                edge = boundary - FACE_WIDTH / 2.0
                if box.XMin < edge - 1.0 and box.XMax > edge + 1.0:
                    raise ValueError(f"top face straddles region boundary x={edge}: {box}")
        if owner is not None:
            regions[owner].append(face)
    return regions


# --------------------------------------------------------------------------
# Document


def _world_points(stage, cache, prim):
    mesh = UsdGeom.Mesh(prim)
    matrix = cache.GetLocalToWorldTransform(prim)
    for point in mesh.GetPointsAttr().Get():
        world = matrix.Transform(point) * 1000.0
        yield (world[0], -world[2], world[1])


def _reference_envelope(reference: Path):
    stage = Usd.Stage.Open(str(reference))
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    lows, highs = [math.inf] * 3, [-math.inf] * 3
    for prim in stage.Traverse():
        if prim.GetTypeName() != "Mesh":
            continue
        for point in _world_points(stage, cache, prim):
            for axis in range(3):
                lows[axis] = min(lows[axis], point[axis])
                highs[axis] = max(highs[axis], point[axis])
    return lows, highs


def _reference_texture(reference: Path) -> tuple[Path, str]:
    with zipfile.ZipFile(reference) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".png")]
        if len(names) != 1:
            raise ValueError(f"expected exactly one reference texture, found {names}")
        data = archive.read(names[0])
    scratch = SCRATCH / "assets"
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / os.path.basename(names[0])
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def _apply_material(obj, texture_source: Path | None) -> None:
    obj.addProperty("App::PropertyString", "MaterialName", "HangTen")
    obj.addProperty("App::PropertyString", "BaseColor", "HangTen")
    obj.addProperty("App::PropertyFloat", "Roughness", "HangTen")
    obj.addProperty("App::PropertyFloat", "Metallic", "HangTen")
    if texture_source is not None:
        obj.addProperty("App::PropertyFileIncluded", "TextureFile", "HangTen")
    obj.MaterialName = MATERIAL_NAME
    obj.BaseColor = MATERIAL_BASE_COLOR
    obj.Roughness = MATERIAL_ROUGHNESS
    obj.Metallic = MATERIAL_METALLIC
    if texture_source is not None:
        obj.TextureFile = str(texture_source)


def _bbox_outline(shape):
    box = shape.BoundBox
    return [
        [round(box.XMin, 4), round(box.ZMin, 4)],
        [round(box.XMax, 4), round(box.ZMin, 4)],
        [round(box.XMax, 4), round(box.ZMax, 4)],
        [round(box.XMin, 4), round(box.ZMax, 4)],
    ]


def main() -> int:
    board = json.loads(BOARD_JSON.read_text())
    declared_depths = {
        contact["id"]: float(contact["depth"]["range"]["minimum"])
        for contact in board["contacts"]
        if contact.get("depth")
    }
    reference, reference_digest = load_reference(PACKAGE, "primary.usdz", SCRATCH / "ref")
    lows, highs = _reference_envelope(reference)
    for axis, target in ((0, FACE_WIDTH), (1, BODY_DEPTH), (2, FACE_HEIGHT)):
        if abs((highs[axis] - lows[axis]) - target) > 0.2:
            raise ValueError(f"reference axis {axis} extent {highs[axis] - lows[axis]:.3f} != {target}")
    texture_source, texture_digest = _reference_texture(reference)

    document = App.newDocument(PACKAGE.replace("-", "_"))
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
    document.HangTenSchemaVersion = 1
    document.HangTenSourceKind = "native-parametric-measured-profile"
    document.HangTenCoordinateFrame = "freecad-mm-z-up-front-negative-y"
    document.HangTenTessellationDeflection = 0.05

    envelope = document.addObject("Part::Feature", "OuterEnvelope")
    envelope.Shape = body_solid()
    cutters = hold_cutters()
    cutter_object = document.addObject("Part::Feature", "HoldCutters")
    cutter_object.Shape = Part.makeCompound([solid for solid, _ in cutters.values()])
    body_cut = document.addObject("Part::Cut", "BodyCut")
    body_cut.Base = envelope
    body_cut.Tool = cutter_object
    document.recompute()
    if body_cut.Shape.isNull() or not body_cut.Shape.isValid():
        raise ValueError("hold boolean cut failed")
    if len(body_cut.Shape.Solids) != 1:
        raise ValueError(f"cut body has {len(body_cut.Shape.Solids)} solids")

    body = document.addObject("Part::Feature", "BodySolid")
    body.Shape = body_cut.Shape.copy()
    body.addProperty("App::PropertyString", "NodeID", "HangTen")
    body.addProperty("App::PropertyString", "NodeRole", "HangTen")
    body.NodeID = NODE_IDS["body"]
    body.NodeRole = "body"
    _apply_material(body, texture_source)
    document.recompute()

    regions = classify_faces(body.Shape, cutters)
    report = {}
    for contact_id, faces in regions.items():
        if not faces:
            raise ValueError(f"{contact_id} matched no body faces")
        feature = document.addObject("Part::Feature", "Contact_" + contact_id.replace("-", "_"))
        feature.Shape = faces[0] if len(faces) == 1 else Part.makeCompound(faces)
        feature.addProperty("App::PropertyString", "NodeID", "HangTen")
        feature.addProperty("App::PropertyString", "NodeRole", "HangTen")
        feature.addProperty("App::PropertyString", "ContactID", "HangTen")
        feature.addProperty("App::PropertyString", "HangTenHoldOutline", "HangTen")
        feature.NodeID = NODE_IDS[contact_id]
        feature.NodeRole = "contact"
        feature.ContactID = contact_id
        outline = cutters.get(contact_id, (None, None))[1]
        feature.HangTenHoldOutline = json.dumps(outline or _bbox_outline(feature.Shape))
        _apply_material(feature, None)
        box = feature.Shape.BoundBox
        report[contact_id] = {
            "faces": len(faces),
            "x": (round(box.XMin, 2), round(box.XMax, 2)),
            "z": (round(box.ZMin, 2), round(box.ZMax, 2)),
            "depth": round(box.YLength, 3),
        }
        published = declared_depths.get(contact_id)
        if published is not None and abs(box.YLength - published) > 0.25:
            raise ValueError(f"{contact_id} region depth {box.YLength:.3f} != published {published}")

    document.recompute()
    stale = [obj.Name for obj in document.Objects if {"Invalid", "Error"} & set(obj.State)]
    if stale:
        raise ValueError(f"document failed recompute: {stale}")

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    if DESTINATION.exists():
        DESTINATION.unlink()
    document.saveAs(str(DESTINATION))

    body_shape = body.Shape
    print(f"authored {DESTINATION} ({DESTINATION.stat().st_size} bytes)")
    print(f"reference sha256 {reference_digest}")
    print(f"texture sha256 {texture_digest}")
    print(f"reference envelope mm: min {lows} max {highs}")
    print(f"body faces {len(body_shape.Faces)} volume {body_shape.Volume:.0f} mm^3")
    for contact_id, info in sorted(report.items()):
        print(
            f"  {contact_id:24s} faces={info['faces']:4d} x={info['x']} z={info['z']} "
            f"depth={info['depth']} (published {declared_depths.get(contact_id, 'n/a')})"
        )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
