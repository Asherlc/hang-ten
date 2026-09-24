"""One-off migration: author Hangboards/trango-rock-prodigy-natural/*.FCStd.

Migration tool only — not a build input. The saved FCStd stands alone.

Acceptance bar: the reference mesh is a genuinely sculpted shell (16,842 body
points per half). A native pad/loft model cannot match every scooped wall
exactly. This is a native *measured approximation* driven from each reference
hold prim's own mesh:

* Constant-depth holds (closed-crimp, upper-pocket, center-lower-pocket, jug)
  extrude a mesh-derived XZ footprint at the published / measured depth.
* Variable-depth holds (top/bottom rails, outer-supported-pocket) loft
  measured YZ cross-sections along X so depth tapers with the reference
  (and with the manufacturer 20–33 / 10–24 mm rail ranges).

Holds whose measured footprint is genuinely a regular shape are authored as a
clean primitive built from the measured opening bounds — a stadium (the two
variable rails, the center-lower pocket, the 3-finger upper pocket) or an
ellipse (the outer-supported-pocket). This is a deliberate, labeled visual
adaptation for fidelity of form, not a traced measurement. The measured
envelope is kept only where the shape is genuinely irregular — the closed-crimp
sloper/wedge and the elongated top jug. Rail depth still follows the measured
profile, so the variable rails keep their taper.

Irregular measured footprints are vectorized: each closed XZ ring is
Chaikin-smoothed and fit with a low-degree `Part.BSplineCurve.approximate` (C2,
DegMax=5, ``OUTLINE_FIT_TOLERANCE_MM``), then discretized at
``OUTLINE_DEFLECTION_MM`` and resampled to ``OUTLINE_SAMPLES`` evenly spaced
points. A low-degree *approximation* keeps the fit from chasing measured noise
into tens of poles: too many poles both wiggles the silhouette and makes OCCT
mesh the extruded surface into hundreds of thousands of triangles per hold
(measured: a 168-pole VDegree=1 BSplineSurface meshes into 1.66M triangles /
89 s at 0.02 mm, and still 266k at 0.5 mm). Rail depth/z profiles are densely
sampled then linearly resampled so the taper reads smooth rather than
stair-stepped. Still mesh-derived — not photo-traced.

`compare_exports` is evidence, not a gate — see docs/freecad-authoring-migration.md
"Accepted deviation for a sculpted board".

Shape revision (mesh-derived pass): prior passes used AABB boxes, invented
hook/ribbon paths, and constant rail depths. User visual review rejected those;
measurements against the 5.7 MB pre-migration reference confirmed rails taper
20.9→32.7 and 10.9→23.7 mm, and closed-crimp is a floor-envelope wedge+tab
(not a Nike swoosh). This script derives those facts from the reference prims.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import zipfile
from collections import defaultdict
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

PACKAGE = "trango-rock-prodigy-natural"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
SCRATCH = Path(
    os.environ.get(
        "HANGTEN_CAD_SCRATCH",
        str(REPOSITORY / ".context" / "trango-natural-cad" / "freecad-scratch"),
    )
)
REFERENCE_COMMIT = "de267c7ff2483d5cf91f197d3cbbec5415214a05"

HALF_X = 95.25
HALF_Z = 76.2
Y_FRONT = -38.1
Y_BACK = 0.0
BODY_X = 190.5
BODY_Y = 38.1
BODY_Z = 152.4
LEFT_CENTER_X = -145.25
RIGHT_CENTER_X = 145.25

CORNER_R = 10.0
CORNER_SEGMENTS = 10
EDGE_ROLL_R = 3.0
EDGE_ROLL_SEGMENTS = 6

# Chordal deflection used to discretize the fitted B-spline outline into the
# exported polygon. Fine enough to read smooth, coarse enough that the prism
# tessellates in a few hundred triangles instead of millions.
OUTLINE_DEFLECTION_MM = 0.05
# Even vertex count for the exported outline. The fit is resampled to this many
# equally-spaced points so the silhouette reads as a regular curve, not a set of
# uneven facet edges.
OUTLINE_SAMPLES = 120
# Low-degree approximation tolerance. A tight fit chases measured noise into
# tens of poles (which both wiggles the silhouette and makes OCCT explode the
# surface mesh); a loose fit gives one smooth low-order curve.
OUTLINE_FIT_TOLERANCE_MM = 0.8
# Pull the top-jug footprint this far inside the board's top edge so the
# partition seam does not coincide with the rim.
TOP_JUG_EDGE_INSET = 1.0

# Bottom-inner-corner notch (left-half). Keeps the L / flag outline from the
# manufacturer top-down photo. Measured against the body mesh's rising bottom
# edge near the inner gap; extended 1 mm past true edges for a clean cut.
NOTCH_LEFT = {"x0": -100.0, "x1": -49.0, "z0": -77.0, "z1": -44.0}
NOTCH_MARGIN_Y = 2.0

# Gentle top-front roll (approximation of side.jpg). Cut-only; top-jug fuse
# restores material over its own footprint afterward.
TOP_BEVEL_RUN_Y = 6.0
TOP_BEVEL_RUN_Z = 4.0

MATERIAL_NAME = "beech_substrate"
MATERIAL_BASE_COLOR = "0.78,0.65,0.45"
MATERIAL_ROUGHNESS = 0.78
MATERIAL_METALLIC = 0.0

# Build strategy per hold.
# extrude: constant-depth loft of identical opening/floor rings from outline.
# taper: multi-section loft along X from measured cross-sections.
# protrusion: extrude proud of the front plane to satisfy published depth.
HOLD_KIND = {
    "closed-crimp": ("extrude", "recess"),
    "center-lower-pocket": ("extrude", "recess"),
    "upper-pocket": ("extrude", "recess"),
    "outer-supported-pocket": ("taper", "recess"),
    "bottom-variable-rail": ("taper", "recess"),
    "top-variable-rail": ("taper", "recess"),
    "top-jug": ("extrude", "protrusion"),
}

GRIP_DEPTH_MM = {"top-jug": 40.0, "upper-pocket": 38.0}

# Holds whose measured footprint is genuinely a regular shape are authored as a
# clean primitive built from the measured bounds (a deliberate, labeled visual
# adaptation — see module docstring), not a noisy mesh-derived contour. Holds
# left out of this table keep the measured envelope: the keyhole upper pocket,
# the closed-crimp wedge, and the elongated top jug.
PRIMITIVE_SHAPE = {
    "top-variable-rail": "stadium",
    "bottom-variable-rail": "stadium",
    "center-lower-pocket": "stadium",
    "upper-pocket": "lobes3",
    "outer-supported-pocket": "ellipse",
}
# Spacing between the overlapping bores of a multi-finger pocket, as a multiple
# of the bore radius. Below 2 the circles overlap, giving the scalloped 3-finger
# opening the manufacturer photo shows.
LOBE_SPACING_FACTOR = 1.55

NODE_SUFFIX = {
    "closed-crimp": "closed_crimp_001",
    "center-lower-pocket": "pocket_2finger_001",
    "upper-pocket": "pocket_3finger_001",
    "outer-supported-pocket": "pocket_supported_001",
    "bottom-variable-rail": "rail_lower_001",
    "top-variable-rail": "rail_upper_001",
    "top-jug": "jug_001",
}

LEFT_HOLD_PATHS = {
    "closed-crimp": "/root/hold__left_closed_crimp/hold__left_closed_crimp_002",
    "center-lower-pocket": "/root/hold__left_pocket_2finger/hold__left_pocket_2finger_002",
    "upper-pocket": "/root/hold__left_pocket_3finger/hold__left_pocket_3finger_002",
    "outer-supported-pocket": "/root/hold__left_pocket_supported/hold__left_pocket_supported_002",
    "bottom-variable-rail": "/root/hold__left_rail_lower/hold__left_rail_lower_002",
    "top-variable-rail": "/root/hold__left_rail_upper/hold__left_rail_upper_002",
    "top-jug": "/root/hold__left_jug/hold__left_jug_002",
}


def _base_id(contact_id: str) -> str:
    for side in ("-left", "-right"):
        if contact_id.endswith(side):
            return contact_id[: -len(side)]
    raise ValueError(contact_id)


def _side(contact_id: str) -> str:
    return "left" if contact_id.endswith("-left") else "right"


def _world_points_and_tris(stage, cache, path: str):
    prim = stage.GetPrimAtPath(path)
    mesh = UsdGeom.Mesh(prim)
    matrix = cache.GetLocalToWorldTransform(prim)
    points = []
    for point in mesh.GetPointsAttr().Get():
        world = matrix.Transform(point) * 1000.0
        points.append((world[0], -world[2], world[1]))
    counts = list(mesh.GetFaceVertexCountsAttr().Get() or [])
    indices = list(mesh.GetFaceVertexIndicesAttr().Get() or [])
    triangles = []
    at = 0
    for count in counts:
        face = indices[at : at + count]
        at += count
        for k in range(1, count - 1):
            triangles.append((face[0], face[k], face[k + 1]))
    return points, triangles


def _ensure_ccw(points):
    area = 0.5 * sum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    )
    return list(reversed(points)) if area < 0 else list(points)


def _reduce_closed(points, tol: float):
    if len(points) < 4:
        return _ensure_ccw(points)
    keep = [0]
    index = 0
    count = len(points)
    while index < count - 1:
        candidate = index + 2
        while candidate < count:
            start, end = points[index], points[candidate]
            span = (end[0] - start[0], end[1] - start[1])
            length = math.hypot(*span)
            worst = 0.0
            for point in points[index : candidate + 1]:
                dx = (point[0] - start[0], point[1] - start[1])
                worst = max(
                    worst,
                    abs(span[0] * dx[1] - span[1] * dx[0]) / max(length, 1e-12),
                )
            if worst > tol:
                break
            candidate += 1
        keep.append(candidate - 1)
        index = candidate - 1
    return _ensure_ccw([points[i] for i in keep])


def _smooth_open(points, passes: int = 2):
    """Chaikin-ish corner cutting on an open polyline (keeps endpoints)."""
    if len(points) < 3:
        return list(points)
    current = list(points)
    for _ in range(passes):
        nxt = [current[0]]
        for i in range(len(current) - 1):
            a, b = current[i], current[i + 1]
            nxt.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            nxt.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        nxt.append(current[-1])
        current = nxt
    return current


def _resample_closed(points, count: int):
    """Resample a closed polyline to ``count`` evenly spaced (arc-length) points."""
    total_count = len(points)
    if total_count < 3 or count < 3:
        return list(points)
    lengths = [
        math.hypot(
            points[(index + 1) % total_count][0] - points[index][0],
            points[(index + 1) % total_count][1] - points[index][1],
        )
        for index in range(total_count)
    ]
    total = sum(lengths)
    if total <= 1e-9:
        return list(points)
    step = total / count
    result = []
    index = 0
    travelled = 0.0
    for position in range(count):
        target = position * step
        while travelled + lengths[index] < target:
            travelled += lengths[index]
            index = (index + 1) % total_count
        segment = lengths[index]
        fraction = (target - travelled) / segment if segment > 1e-12 else 0.0
        start = points[index]
        end = points[(index + 1) % total_count]
        result.append(
            (
                start[0] + fraction * (end[0] - start[0]),
                start[1] + fraction * (end[1] - start[1]),
            )
        )
    return result


def _vectorize_closed(points_xz, tol_mm: float = 0.35):
    """Fit a smooth low-degree closed curve to a measured XZ footprint.

    Returns ``(curve, outline_xz)``. ``curve`` is a periodic-ish
    ``Part.BSplineCurve`` in the y=0 plane fitted by *approximation* with a low
    maximum degree: a tight interpolation through every reduced point chases
    measurement noise into tens of poles, which both wiggles the silhouette and
    makes OCCT mesh the extruded surface into hundreds of thousands of triangles.
    ``outline_xz`` is that curve discretized at ``OUTLINE_DEFLECTION_MM`` and
    then resampled to ``OUTLINE_SAMPLES`` evenly spaced points, so the exported
    polygon reads as a regular curve rather than uneven facet edges.
    """
    points = _ensure_ccw(points_xz)
    if len(points) < 4:
        raise ValueError("outline too small to vectorize")
    reduced = _reduce_closed(points, max(tol_mm, 0.8))
    smoothed = _smooth_open(reduced + [reduced[0]], passes=2)[:-1]
    smoothed = _ensure_ccw(smoothed)
    vectors = [App.Vector(x, 0.0, z) for x, z in smoothed]
    curve = Part.BSplineCurve()
    curve.approximate(
        Points=vectors + [vectors[0]],
        DegMin=3,
        DegMax=5,
        Tolerance=OUTLINE_FIT_TOLERANCE_MM,
        Continuity="C2",
    )
    discrete = curve.discretize(Deflection=OUTLINE_DEFLECTION_MM)
    outline = [(float(p.x), float(p.z)) for p in discrete]
    if math.hypot(outline[0][0] - outline[-1][0], outline[0][1] - outline[-1][1]) < 1e-6:
        outline = outline[:-1]
    return curve, _resample_closed(_ensure_ccw(outline), OUTLINE_SAMPLES)


def _angular_outline(points_xz, bins: int = 180, tol: float = 0.8):
    projected = list({(round(x, 2), round(z, 2)) for x, z in points_xz})
    cx = sum(p[0] for p in projected) / len(projected)
    cz = sum(p[1] for p in projected) / len(projected)
    best = [None] * bins
    best_r = [-1.0] * bins
    for x, z in projected:
        angle = math.atan2(z - cz, x - cx)
        bi = int((angle + math.pi) / (2 * math.pi) * bins) % bins
        radius = math.hypot(x - cx, z - cz)
        if radius > best_r[bi]:
            best_r[bi] = radius
            best[bi] = (x, z)
    outline = [p for p in best if p is not None]
    return _vectorize_closed(_reduce_closed(outline, tol), tol_mm=0.4)


def _envelope_outline(points_xz, bin_mm: float = 2.5, tol: float = 1.2):
    """Closed XZ curve from min/max-z per x bin.

    Suited to elongated holds (the top jug) where a radius-from-centroid outline
    degenerates into a bowtie. Upper and lower envelopes are smoothed
    independently, then fit as one closed curve.
    """
    bins: dict[float, list[float]] = defaultdict(list)
    for x, z in points_xz:
        bins[round(x / bin_mm) * bin_mm].append(z)
    xs = sorted(bins)
    upper = _smooth_open([(x, max(bins[x])) for x in xs], passes=3)
    lower = _smooth_open([(x, min(bins[x])) for x in xs], passes=3)
    raw = upper + list(reversed(lower))
    return _vectorize_closed(_reduce_closed(raw, tol), tol_mm=0.5)


def _floor_envelope_outline(points, bin_mm: float = 2.5, floor_band: float = 0.6, tol: float = 1.2):
    """Envelope of the floor-band points — the closed-crimp wedge+tab footprint."""
    floor_y = max(p[1] for p in points)
    floor = [(p[0], p[2]) for p in points if p[1] > floor_y - floor_band]
    return _envelope_outline(floor, bin_mm=bin_mm, tol=tol)


def _x_sections(points, triangles, n: int = 5):
    """Measured YZ spans along x, then linearly resampled for a clean loft.

    Rails taper almost linearly in the reference; fewer smooth sections beat a
    stair-step of noisy mesh slices.
    """
    xs = [p[0] for p in points]
    x_min, x_max = min(xs), max(xs)
    lo = x_min + 0.06 * (x_max - x_min)
    hi = x_max - 0.06 * (x_max - x_min)
    samples = []
    dense = 17
    for i in range(dense):
        cut = lo + (hi - lo) * i / max(dense - 1, 1)
        ys = []
        zs = []
        for tri in triangles:
            verts = [points[v] for v in tri]
            cross = []
            for j in range(3):
                a, b = verts[j], verts[(j + 1) % 3]
                if (a[0] - cut) * (b[0] - cut) < 0:
                    f = (cut - a[0]) / (b[0] - a[0])
                    cross.append(
                        (
                            a[1] + f * (b[1] - a[1]),
                            a[2] + f * (b[2] - a[2]),
                        )
                    )
            if len(cross) == 2:
                for y, z in cross:
                    ys.append(y)
                    zs.append(z)
        if not zs:
            continue
        samples.append((cut, min(zs), max(zs), max(ys) - Y_FRONT))
    if len(samples) < 3:
        raise ValueError("too few x-sections")

    def lerp_cols(frac):
        target = lo + (hi - lo) * frac
        for i in range(len(samples) - 1):
            x0, z00, z10, d0 = samples[i]
            x1, z01, z11, d1 = samples[i + 1]
            if x0 <= target <= x1 or i == len(samples) - 2:
                t = 0.0 if x1 == x0 else (target - x0) / (x1 - x0)
                t = max(0.0, min(1.0, t))
                return {
                    "x": target,
                    "z0": z00 + t * (z01 - z00),
                    "z1": z10 + t * (z11 - z10),
                    "depth": d0 + t * (d1 - d0),
                }
        x, z0, z1, d = samples[-1]
        return {"x": x, "z0": z0, "z1": z1, "depth": d}

    return [lerp_cols(i / max(n - 1, 1)) for i in range(n)]


def _mirror_xz(points, side: str):
    if side == "left":
        return list(points)
    # Negating x flips the winding; restore it so a mirrored region surface has
    # the same orientation as the unmirrored one. Otherwise one half's recess
    # normals point backward and the single-sided material culls it (white holes
    # in the app, which the double-sided offline renderer hides).
    return _ensure_ccw([(-x, z) for x, z in points])


def _orient_region(shape):
    """Orient a recess region so its floor faces the board front.

    Mirroring the outline can leave the shell reversed, and the material is
    single-sided, so an inverted half is culled in the app (white holes) even
    though the double-sided offline render hides it. The floor is the deepest
    planar face with a +/-Y normal; its native normal must have y > 0, which the
    runtime maps to a front-facing +z.
    """
    deepest_y = None
    floor_normal_y = None
    for face in shape.Faces:
        try:
            u, v = face.Surface.parameter(face.CenterOfMass)
            normal = face.normalAt(u, v)
        except Exception:
            continue
        if abs(normal.y) > 0.9 and (deepest_y is None or face.CenterOfMass.y > deepest_y):
            deepest_y = face.CenterOfMass.y
            floor_normal_y = normal.y
    if floor_normal_y is not None and floor_normal_y > 0:
        return shape.reversed()
    return shape


def _mirror_sections(rows, side: str):
    if side == "left":
        return list(rows)
    return [{"x": -r["x"], "z0": r["z0"], "z1": r["z1"], "depth": r["depth"]} for r in reversed(rows)]


def _reference_texture(reference: Path) -> tuple[str, Path, str]:
    with zipfile.ZipFile(reference) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".png")]
        if not names:
            raise ValueError("no reference texture found")
        member = names[0]
        data = archive.read(member)
    scratch = SCRATCH / "assets"
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / os.path.basename(member)
    path.write_bytes(data)
    return os.path.basename(member), path, hashlib.sha256(data).hexdigest()


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


def _loft_solid(sections, solid: bool = True):
    wires = [Part.makePolygon(list(points) + [points[0]]) for points in sections]
    return Part.makeLoft(wires, solid, True)


def _rounded_rect_points(cx0, cx1, cz0, cz1, radius, y, segments=CORNER_SEGMENTS):
    ccx = (cx0 + cx1) / 2.0
    ccz = (cz0 + cz1) / 2.0
    hx = (cx1 - cx0) / 2.0
    hz = (cz1 - cz0) / 2.0
    r = max(min(radius, hx, hz), 0.5)
    cx = hx - r
    cz = hz - r
    corners = (
        (cx, -cz, -math.pi / 2.0, 0.0),
        (cx, cz, 0.0, math.pi / 2.0),
        (-cx, cz, math.pi / 2.0, math.pi),
        (-cx, -cz, math.pi, 1.5 * math.pi),
    )
    points = []
    for ox, oz, start, end in corners:
        for index in range(segments + 1):
            angle = start + (end - start) * index / segments
            points.append(
                App.Vector(
                    ccx + ox + r * math.cos(angle),
                    y,
                    ccz + oz + r * math.sin(angle),
                )
            )
    return points


def _notch_bounds(side):
    if side == "left":
        return NOTCH_LEFT
    return {
        "x0": -NOTCH_LEFT["x1"],
        "x1": -NOTCH_LEFT["x0"],
        "z0": NOTCH_LEFT["z0"],
        "z1": NOTCH_LEFT["z1"],
    }


def _notch_solid(side):
    bounds = _notch_bounds(side)
    origin = App.Vector(bounds["x0"], Y_FRONT - NOTCH_MARGIN_Y, bounds["z0"])
    return Part.makeBox(
        bounds["x1"] - bounds["x0"],
        (Y_BACK - Y_FRONT) + 2.0 * NOTCH_MARGIN_Y,
        bounds["z1"] - bounds["z0"],
        origin,
    )


def _top_edge_bevel_solid(center_x):
    width = 2.0 * HALF_X + 2.0
    y0 = Y_FRONT - 0.5
    z0 = HALF_Z + 0.5
    pts = [
        App.Vector(0.0, y0, z0),
        App.Vector(0.0, y0 + TOP_BEVEL_RUN_Y, z0),
        App.Vector(0.0, y0, z0 - TOP_BEVEL_RUN_Z),
        App.Vector(0.0, y0, z0),
    ]
    face = Part.Face(Part.makePolygon(pts))
    prism = face.extrude(App.Vector(width, 0.0, 0.0))
    prism.translate(App.Vector(center_x - HALF_X - 1.0, 0.0, 0.0))
    return prism


def _half_body_solid(center_x: float):
    x0, x1 = center_x - HALF_X, center_x + HALF_X
    z0, z1 = -HALF_Z, HALF_Z
    sections = []
    roll = []
    for index in range(EDGE_ROLL_SEGMENTS + 1):
        angle = 0.5 * math.pi * index / EDGE_ROLL_SEGMENTS
        inset = EDGE_ROLL_R * (1.0 - math.sin(angle))
        offset = EDGE_ROLL_R * (1.0 - math.cos(angle))
        roll.append((offset, inset))
    for offset, inset in roll:
        sections.append(
            _rounded_rect_points(x0, x1, z0, z1, CORNER_R - inset, Y_FRONT + offset)
        )
    for offset, inset in reversed(roll):
        sections.append(
            _rounded_rect_points(x0, x1, z0, z1, CORNER_R - inset, Y_BACK - offset)
        )
    return _loft_solid(sections)


def _depth_span_y(depth, kind):
    if kind == "recess":
        return Y_FRONT, Y_FRONT + depth
    if kind == "protrusion":
        return Y_FRONT - (depth - (Y_BACK - Y_FRONT)), Y_BACK
    raise ValueError(kind)


def _wire_at_y(outline_xz, y: float):
    """Build a closed polygonal Wire from an XZ outline at depth y."""
    points = [App.Vector(x, y, z) for x, z in outline_xz]
    return Part.makePolygon(points + [points[0]])


def _ring_from_outline(outline_xz, y):
    return [App.Vector(x, y, z) for x, z in outline_xz]


def _extrude_contact(outline_xz, depth, kind):
    """Extrude the smooth measured polygon at a constant depth.

    ``outline_xz`` is the dense discretization of the fitted B-spline, so the
    silhouette reads smooth while the prism tessellates in a few hundred
    triangles (see module docstring).
    """
    opening_y, floor_y = _depth_span_y(depth, kind)
    opening_wire = _wire_at_y(outline_xz, opening_y)
    floor_wire = _wire_at_y(outline_xz, floor_y)
    opening_face = Part.Face(opening_wire)
    solid_tool = opening_face.extrude(App.Vector(0.0, floor_y - opening_y, 0.0))
    # Contact region: lateral ruled surface, plus a floor face for a recess.
    # A protrusion's "floor" would be the board's back plane, coplanar with the
    # body back face — leave it off so the back stays a single clean surface.
    lateral = Part.makeLoft([floor_wire, opening_wire], False, True)
    if kind == "protrusion":
        surface = lateral
    else:
        surface = lateral.fuse(Part.Face(floor_wire))
    opening_ring = _ring_from_outline(outline_xz, opening_y)
    return solid_tool, surface, opening_ring


def _taper_contact(sections_xz_depth, kind, outline_xz=None):
    """Loft rectangular YZ sections along X for a variable-depth recess."""
    if kind != "recess":
        raise ValueError("taper contacts are recesses")
    loft_sections = []
    for row in sections_xz_depth:
        opening_y = Y_FRONT
        floor_y = Y_FRONT + row["depth"]
        loft_sections.append(
            [
                App.Vector(row["x"], opening_y, row["z0"]),
                App.Vector(row["x"], opening_y, row["z1"]),
                App.Vector(row["x"], floor_y, row["z1"]),
                App.Vector(row["x"], floor_y, row["z0"]),
            ]
        )
    solid_tool = _loft_solid(loft_sections, solid=True)
    surface = _loft_solid(loft_sections, solid=False)
    if outline_xz is None:
        xs = [r["x"] for r in sections_xz_depth]
        z0 = min(r["z0"] for r in sections_xz_depth)
        z1 = max(r["z1"] for r in sections_xz_depth)
        outline_xz = [
            (min(xs), z0),
            (max(xs), z0),
            (max(xs), z1),
            (min(xs), z1),
        ]
    opening_ring = _ring_from_outline(outline_xz, Y_FRONT)
    return solid_tool, surface, opening_ring


def _opening_bounds(points, band: float = 1.0):
    """Bounds of the opening rim: the points at the front plane.

    The reference hold prim includes its walls, so its raw x/z extent overshoots
    the opening. Restrict to the front band to recover the actual footprint.
    """
    front = min(p[1] for p in points)
    rim = [p for p in points if p[1] <= front + band]
    xs = [p[0] for p in rim]
    zs = [p[2] for p in rim]
    return min(xs), max(xs), min(zs), max(zs)


def _lobed_outline(x0, x1, z0, z1, count: int, samples: int = 400):
    """Union outline of ``count`` overlapping circular bores along x.

    The manufacturer's multi-finger pockets are drilled/bores that overlap, so
    the opening is scalloped (e.g. the 3-finger pocket is three overlapping
    circles). Width matches the measured opening; the circle radius follows from
    ``LOBE_SPACING_FACTOR``.
    """
    cx = (x0 + x1) / 2.0
    cz = (z0 + z1) / 2.0
    width = x1 - x0
    radius = width / ((count - 1) * LOBE_SPACING_FACTOR + 2.0)
    spacing = LOBE_SPACING_FACTOR * radius
    centers = [cx + (index - (count - 1) / 2.0) * spacing for index in range(count)]
    top = []
    bottom = []
    for index in range(samples + 1):
        x = x0 + width * index / samples
        heights = [
            math.sqrt(radius * radius - (x - center) ** 2)
            for center in centers
            if abs(x - center) <= radius
        ]
        if not heights:
            continue
        half = max(heights)
        top.append((x, cz + half))
        bottom.append((x, cz - half))
    return _resample_closed(_ensure_ccw(top + list(reversed(bottom))), OUTLINE_SAMPLES)


def _primitive_outline(shape: str, x0, x1, z0, z1):
    """A clean stadium, ellipse, or lobed outline from measured bounds."""
    if shape == "lobes3":
        return _lobed_outline(x0, x1, z0, z1, 3)
    cx = (x0 + x1) / 2.0
    cz = (z0 + z1) / 2.0
    a = (x1 - x0) / 2.0
    b = (z1 - z0) / 2.0
    if shape == "ellipse":
        points = [
            (
                cx + a * math.cos(2.0 * math.pi * index / OUTLINE_SAMPLES),
                cz + b * math.sin(2.0 * math.pi * index / OUTLINE_SAMPLES),
            )
            for index in range(OUTLINE_SAMPLES)
        ]
    else:  # stadium: rounded rectangle with semicircular caps
        flat = max(a - b, 0.0)
        radius = b if flat > 1e-6 else min(a, b)
        segments = OUTLINE_SAMPLES // 2
        points = []
        for index in range(segments + 1):
            angle = -math.pi / 2.0 + math.pi * index / segments
            points.append(
                (cx + flat + radius * math.cos(angle), cz + radius * math.sin(angle))
            )
        for index in range(segments + 1):
            angle = math.pi / 2.0 + math.pi * index / segments
            points.append(
                (cx - flat + radius * math.cos(angle), cz + radius * math.sin(angle))
            )
    return _resample_closed(_ensure_ccw(points), OUTLINE_SAMPLES)


def _depth_at(x, sections):
    """Interpolate the measured depth profile at ``x`` (clamped at the ends)."""
    xs = [row["x"] for row in sections]
    if x <= xs[0]:
        return sections[0]["depth"]
    if x >= xs[-1]:
        return sections[-1]["depth"]
    for index in range(len(sections) - 1):
        if xs[index] <= x <= xs[index + 1]:
            span = xs[index + 1] - xs[index]
            fraction = 0.0 if span == 0 else (x - xs[index]) / span
            return sections[index]["depth"] + fraction * (
                sections[index + 1]["depth"] - sections[index]["depth"]
            )
    return sections[-1]["depth"]


def _primitive_taper_sections(shape: str, bounds, depth_sections, n: int = 140):
    """Cross-sections of a clean primitive, with the measured depth taper.

    Each row is (x, z0, z1, depth): the z-range follows the primitive outline so
    the opening stays a regular stadium/ellipse, and the depth follows the
    measured profile so a variable rail keeps its taper. These feed the same
    loft the measured rails use.
    """
    x0, x1, z0, z1 = bounds
    cx = (x0 + x1) / 2.0
    cz = (z0 + z1) / 2.0
    a = (x1 - x0) / 2.0
    b = (z1 - z0) / 2.0
    flat = max(a - b, 0.0)
    radius = b if flat > 1e-6 else min(a, b)
    rows = []
    for index in range(n):
        fraction = 0.005 + 0.99 * index / (n - 1)
        x = x0 + (x1 - x0) * fraction
        if shape == "ellipse":
            t = (x - cx) / a if a else 0.0
            half = b * math.sqrt(max(0.0, 1.0 - t * t))
        else:
            offset = abs(x - cx) - flat
            if offset <= 0.0:
                half = radius
            elif offset <= radius:
                half = math.sqrt(max(0.0, radius * radius - offset * offset))
            else:
                half = 0.0
        if half <= 1e-6:
            continue
        rows.append(
            {"x": x, "z0": cz - half, "z1": cz + half, "depth": _depth_at(x, depth_sections)}
        )
    return rows


def _measure_holds(stage, cache):
    measured = {}
    for base, path in LEFT_HOLD_PATHS.items():
        points, triangles = _world_points_and_tris(stage, cache, path)
        strategy, kind = HOLD_KIND[base]
        depth_mesh = max(p[1] for p in points) - min(p[1] for p in points)
        shape_kind = PRIMITIVE_SHAPE.get(base)
        if shape_kind is not None:
            x0, x1, z0, z1 = _opening_bounds(points)
            outline = _primitive_outline(shape_kind, x0, x1, z0, z1)
            if strategy == "taper":
                depth_sections = _x_sections(points, triangles, n=5)
                sections = _primitive_taper_sections(shape_kind, (x0, x1, z0, z1), depth_sections)
                measured[base] = {
                    "strategy": strategy,
                    "kind": kind,
                    "primitive": True,
                    "outline": outline,
                    "sections": sections,
                    "depth": max(s["depth"] for s in sections),
                    "depth_mesh": depth_mesh,
                }
            else:
                depth = {"center-lower-pocket": 27.0, "upper-pocket": 38.0}.get(base, depth_mesh)
                measured[base] = {
                    "strategy": strategy,
                    "kind": kind,
                    "primitive": True,
                    "outline": outline,
                    "depth": depth,
                    "depth_mesh": depth_mesh,
                }
            continue
        if base == "closed-crimp":
            _curve, outline = _floor_envelope_outline(points)
            depth = 10.0
        elif base == "top-jug":
            # Elongated strip: radial binning degenerates, so use an envelope.
            # Keep the footprint just inside the board's top edge so the body /
            # region partition seam does not land on the shared top rim (which
            # tears into a ragged band there).
            projected = [(p[0], min(p[2], HALF_Z - TOP_JUG_EDGE_INSET)) for p in points]
            _curve, outline = _envelope_outline(projected)
            depth = 40.0
        elif strategy == "taper":
            _curve, outline = _angular_outline([(p[0], p[2]) for p in points], bins=120, tol=1.0)
            sections = _x_sections(points, triangles, n=5)
            measured[base] = {
                "strategy": strategy,
                "kind": kind,
                "outline": outline,
                "sections": sections,
                "depth": max(s["depth"] for s in sections),
                "depth_mesh": depth_mesh,
            }
            continue
        else:
            _curve, outline = _angular_outline([(p[0], p[2]) for p in points], bins=160, tol=0.75)
            if base == "upper-pocket":
                depth = 38.0
            elif base == "center-lower-pocket":
                depth = 27.0
            elif base == "top-jug":
                depth = 40.0
            else:
                depth = depth_mesh
        if len(outline) < 4:
            raise ValueError(f"{base}: outline too small ({len(outline)})")
        measured[base] = {
            "strategy": strategy,
            "kind": kind,
            "outline": outline,
            "depth": depth,
            "depth_mesh": depth_mesh,
        }
    return measured


def main() -> int:
    board = json.loads(BOARD_JSON.read_text())
    # Prefer a pre-resolved reference directory (workspace-owned 5.7 MB mesh)
    # so authoring does not depend on live LFS smudge.
    os.environ.setdefault(
        "HANGTEN_REFERENCE_DIR",
        str(REPOSITORY / ".context" / "trango-natural-cad" / "ref"),
    )
    reference, reference_digest = load_reference(
        PACKAGE, "primary.usdz", SCRATCH / "ref", commit=REFERENCE_COMMIT
    )
    if reference.stat().st_size < 1_000_000:
        raise ValueError(
            f"reference looks like an LFS pointer stub ({reference.stat().st_size} bytes); "
            "set HANGTEN_REFERENCE_DIR to the resolved 5.7 MB USDZ directory"
        )
    stage = Usd.Stage.Open(str(reference))
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    left_points, _ = _world_points_and_tris(stage, cache, "/root/body__left/body__left_002")
    measured_body = {
        "width": max(p[0] for p in left_points) - min(p[0] for p in left_points),
        "depth": max(p[1] for p in left_points) - min(p[1] for p in left_points),
        "height": max(p[2] for p in left_points) - min(p[2] for p in left_points),
    }
    body_mesh_targets = {"width": BODY_X, "depth": BODY_Y, "height": 146.4}
    for key, target in body_mesh_targets.items():
        if abs(measured_body[key] - target) > 0.2:
            raise ValueError(
                f"reference {key} {measured_body[key]:.3f} mm != target {target}"
            )

    holds = _measure_holds(stage, cache)
    _member, texture_source, texture_digest = _reference_texture(reference)

    if DESTINATION.exists():
        DESTINATION.unlink()
    document = App.newDocument(PACKAGE)
    document.Label = board["name"]
    document.addProperty("App::PropertyString", "HangTenBoardID", "HangTen")
    document.addProperty("App::PropertyString", "HangTenPresentationID", "HangTen")
    document.addProperty("App::PropertyInteger", "HangTenSchemaVersion", "HangTen")
    document.addProperty("App::PropertyString", "HangTenSourceKind", "HangTen")
    document.addProperty("App::PropertyString", "HangTenCoordinateFrame", "HangTen")
    document.addProperty("App::PropertyFloat", "HangTenTessellationDeflection", "HangTen")
    document.HangTenBoardID = board["id"]
    document.HangTenPresentationID = board["presentations"][0]["id"]
    document.HangTenSchemaVersion = 1
    document.HangTenSourceKind = "native-parametric-measured-profile"
    document.HangTenCoordinateFrame = "freecad-mm-z-up-front-negative-y"
    document.HangTenTessellationDeflection = 0.02

    contact_ids = [c["id"] for c in board["contacts"]]
    regions = {}
    half_bodies = {}
    for side, center_x in (("left", LEFT_CENTER_X), ("right", RIGHT_CENTER_X)):
        brick = document.addObject("Part::Feature", f"OuterEnvelope_{side}")
        brick.Shape = _half_body_solid(center_x)
        document.recompute()

        notch_tool = document.addObject("Part::Feature", f"NotchTool_{side}")
        notch_tool.Shape = _notch_solid(side)
        notch_cut = document.addObject("Part::Cut", f"NotchCut_{side}")
        notch_cut.Base = brick
        notch_cut.Tool = notch_tool
        document.recompute()
        if notch_cut.Shape.isNull() or notch_cut.Shape.Volume < 1.0:
            raise ValueError(f"{side} outline notch cut failed")

        bevel_tool = document.addObject("Part::Feature", f"BevelTool_{side}")
        bevel_tool.Shape = _top_edge_bevel_solid(center_x)
        bevel_cut = document.addObject("Part::Cut", f"BevelCut_{side}")
        bevel_cut.Base = notch_cut
        bevel_cut.Tool = bevel_tool
        document.recompute()
        if bevel_cut.Shape.isNull() or bevel_cut.Shape.Volume < 1.0:
            raise ValueError(f"{side} top-edge bevel cut failed")

        cut_chain = bevel_cut
        fuse_tools = []
        pending_surfaces = []
        for contact_id in contact_ids:
            if _side(contact_id) != side:
                continue
            base = _base_id(contact_id)
            spec = holds[base]
            outline = _mirror_xz(spec["outline"], side)
            if spec["strategy"] == "taper":
                sections = _mirror_sections(spec["sections"], side)
                solid_tool, raw_surface, opening_ring = _taper_contact(
                    sections, spec["kind"], outline_xz=outline
                )
            else:
                solid_tool, raw_surface, opening_ring = _extrude_contact(
                    outline, spec["depth"], spec["kind"]
                )
            if spec["kind"] == "recess":
                region_shape = _orient_region(raw_surface.reversed())
            else:
                region_shape = raw_surface.reversed()
            tag = contact_id.replace("-", "_")
            solid_obj = document.addObject("Part::Feature", f"Cutter_{tag}")
            solid_obj.Shape = solid_tool
            if spec["kind"] == "recess":
                cut_obj = document.addObject("Part::Cut", f"Cut_{tag}")
                cut_obj.Base = cut_chain
                cut_obj.Tool = solid_obj
                document.recompute()
                if cut_obj.Shape.isNull() or cut_obj.Shape.Volume < 1.0:
                    raise ValueError(f"{contact_id} cut failed")
                cut_chain = cut_obj
            else:
                fuse_tools.append(solid_obj)
            pending_surfaces.append((contact_id, region_shape, opening_ring, spec))

        if fuse_tools:
            fuse_obj = document.addObject("Part::MultiFuse", f"Fuse_{side}")
            fuse_obj.Shapes = [cut_chain] + fuse_tools
            document.recompute()
            if fuse_obj.Shape.isNull() or fuse_obj.Shape.Volume < 1.0:
                raise ValueError(f"{side} jug fuse failed")
            cut_chain = fuse_obj

        half = document.addObject("Part::Feature", f"HalfBody_{side}")
        half.Shape = cut_chain.Shape
        document.recompute()
        half_bodies[side] = half

        for contact_id, region_shape, opening_ring, spec in pending_surfaces:
            base = _base_id(contact_id)
            tag = contact_id.replace("-", "_")
            region = document.addObject("Part::Feature", f"Region_{tag}")
            region.Shape = region_shape
            region.addProperty("App::PropertyString", "NodeID", "HangTen")
            region.addProperty("App::PropertyString", "NodeRole", "HangTen")
            region.addProperty("App::PropertyString", "ContactID", "HangTen")
            region.NodeID = f"hold__{side}_{NODE_SUFFIX[base]}"
            region.NodeRole = "contact"
            region.ContactID = contact_id
            region.addProperty("App::PropertyString", "HangTenHoldOutline", "HangTen")
            region.HangTenHoldOutline = json.dumps(
                [[round(p.x, 4), round(p.z, 4)] for p in opening_ring]
            )
            _apply_material(region, None)
            box = region.Shape.BoundBox
            regions[contact_id] = {
                "faces": len(region.Shape.Faces),
                "x": (round(box.XMin, 2), round(box.XMax, 2)),
                "z": (round(box.ZMin, 2), round(box.ZMax, 2)),
                "depth": round(box.YLength, 3),
                "strategy": spec["strategy"],
            }

    body = document.addObject("Part::Compound", "Body")
    body.Links = [half_bodies["left"], half_bodies["right"]]
    document.recompute()
    body.addProperty("App::PropertyString", "NodeID", "HangTen")
    body.addProperty("App::PropertyString", "NodeRole", "HangTen")
    body.NodeID = "body__001"
    body.NodeRole = "body"
    _apply_material(body, texture_source)
    document.recompute()

    stale = [
        obj.Name for obj in document.Objects if set(obj.State) & {"Invalid", "Error"}
    ]
    if stale:
        raise ValueError(f"document failed recompute: {stale}")

    for base, published in GRIP_DEPTH_MM.items():
        for side_name in ("left", "right"):
            contact_id = f"{base}-{side_name}"
            measured_depth = regions[contact_id]["depth"]
            if abs(measured_depth - published) > 0.25:
                raise ValueError(
                    f"{contact_id} region depth {measured_depth} mm != published {published} mm"
                )

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    document.saveAs(str(DESTINATION))

    print(f"authored {DESTINATION} ({DESTINATION.stat().st_size} bytes)")
    print(f"reference sha256 {reference_digest}")
    print(f"texture sha256 {texture_digest}")
    print(f"reference envelope mm (left half): {measured_body}")
    print("acceptance: mesh-derived measured-approximation; see module docstring")
    for base, spec in sorted(holds.items()):
        if spec["strategy"] == "taper":
            depths = [s["depth"] for s in spec["sections"]]
            print(
                f"  measured {base:24s} taper {min(depths):.2f}->{max(depths):.2f} mm "
                f"outline_n={len(spec['outline'])}"
            )
        else:
            print(
                f"  measured {base:24s} depth={spec['depth']:.2f} "
                f"(mesh {spec['depth_mesh']:.2f}) outline_n={len(spec['outline'])}"
            )
    for contact_id in sorted(regions):
        info = regions[contact_id]
        published = GRIP_DEPTH_MM.get(_base_id(contact_id), "n/a")
        print(
            f"  {contact_id:28s} faces={info['faces']:3d} "
            f"x={info['x']} z={info['z']} depth={info['depth']} "
            f"({info['strategy']}, published {published})"
        )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
