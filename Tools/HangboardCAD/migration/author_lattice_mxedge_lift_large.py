"""One-off migration: author Hangboards/lattice-mxedge-lift-large/lattice-mxedge-lift-large.FCStd.

Migration tool only — not a build input.

Provenance:
* Mesh envelope 168 x 34 x 98 mm (native X / depth Y / height Z), same brick as Small.
  board.json's "20 x 11 x 5 cm" is the shared rounded catalogue string. The committed
  descriptor modelBounds claims runtime Z +/-0.049 m; the reference mesh is +/-0.017 m.
  This source follows the mesh. Grip depths 22 / 16 / 12 / 28 mm are the published values.
* Front geometry measured from the Git-resolved reference USDZ
  (sha256 b8f9b7f75002f91b4ec45cf9b5212c7ae8a1ea6dffe9af9d5421a7566b9b2f25) on a 0.5 mm grid:
  - two stadium troughs, not four pockets. Upper recess sits near z [10, 34]; lower near
    z [-33, -12]. edge-12 and edge-16 split the upper trough (AABBs meet around z = 22);
    edge-22 is the lower trough's lower wall and mono-28 is the right-end bore;
  - stadium matches Small: arc centres x = +/-48 mm, rim radius 14 mm. Centres measured
    at z = 22 (upper; contact split) and z = -22 (lower; depth peak);
  - trough walls are **flat / vertical** (constant stadium radius, no ogee or entry
    bevel). MX grips are flat edges; the earlier Small-style smoothstep inset was a
    lambert readability choice and is intentionally omitted here;
  - floor crown c = 0.134 on depth(x) = depth(0) * (1 - c * (x/48)^2), fit on the upper
    floor (16.00, 15.87, 15.46, 14.79, 13.86 mm at x = 0, 12, 24, 36, 48) and the lower
    floor left of the mono (20.00, 19.83, 19.33 mm at x = 0, 12, 24);
  - measured centre floors are 16.0 mm (upper) and 20.0 mm (lower). Upper uses the
    published 16 mm. Lower uses the published 22 mm so the edge-22 region depth matches
    board.json. Stated deviation: lower floor 2 mm deeper than measured;
  - mono bore centred at (x 48, z -22). Radius tapers from 13.6 mm at the lip to
    11.7 mm at the published 28 mm floor (reference floor y = +10.5, r about 11.8);
  - two external cord mouths on the top edge, r 3.4 mm, 3 mm deep, at x = +/-69.75,
    y = 1. The reference omits the passage interior.
* Display material texture embedded from the same reference package.
* Measured approximation of a sculpted display mesh — not manufacturing geometry.
  compare_exports is evidence, not a gate.

Region partition (published depth is the region's Y extent at x = 0):

    edge-16  upper trough, lower wall, full depth        span 16
    edge-12  upper trough, upper wall, front 12 mm       span 12
    edge-22  lower trough, lower wall, left of the mono  span 22
    mono-28  lower trough right end + bore incl. floor   span 28
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

PACKAGE = "lattice-mxedge-lift-large"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
BODY_PRIM = "/root/body/MXL_body_editable_skin_001"

Y_FRONT = -17.0
BODY_X = 168.0
BODY_Y = 34.0
BODY_Z = 98.0
HALF_X = BODY_X / 2.0
HALF_Z = BODY_Z / 2.0
Y_BACK = Y_FRONT + BODY_Y

# Outer envelope: 15 mm XZ corners plus a 4 mm roll into the front and back faces.
# Planar facets throughout — an OCCT fillet leaves a tessellation-vs-Area gap at compile.
CORNER_R = 15.0
CORNER_SEGMENTS = 12
CORNER_CENTER_X = HALF_X - CORNER_R
CORNER_CENTER_Z = HALF_Z - CORNER_R
EDGE_ROLL_R = 4.0
EDGE_ROLL_SEGMENTS = 4

GRIP_DEPTH_MM = {
    "edge-22": 22.0,
    "edge-16": 16.0,
    "edge-12": 12.0,
    "mono-28": 28.0,
}

# Measured stadium openings: arc centres at x = +/-48, rim radius = half the opening height.
TROUGH_HALF_LEN = 48.0
TROUGH_RADIUS = 14.0
# Even, so a vertex lands exactly on z = z_center and no facet straddles the wall that
# divides the trough's two regions.
TROUGH_ARC_SEGMENTS = 14
# Chords of the crowned floor parabola; 10 holds it to under 0.01 mm.
TROUGH_STRAIGHT_SEGMENTS = 10
TROUGHS = {
    "upper": {
        "z_center": 22.0,
        "depth": GRIP_DEPTH_MM["edge-16"],
        "crown_fraction": 0.134,
        # Flat vertical walls — no inward ogee/bevel.
        "apex_inset": 0.0,
    },
    "lower": {
        "z_center": -22.0,
        "depth": GRIP_DEPTH_MM["edge-22"],
        "crown_fraction": 0.134,
        "apex_inset": 0.0,
    },
}
# Depth fractions of the wall stations. With apex_inset 0 the rings share one
# stadium outline (flat walls); fractions still space the crowned floor and the
# absolute lip station for edge-12.
WALL_FRACTIONS = (
    0.0, 0.15, 0.35, 0.55, 0.75, 0.9, 1.0
)
# Micro inward ledge (mm) only at absolute lip stations. Flat vertical walls are
# otherwise coplanar and OCCT merges them into one face, which breaks the
# published-depth split (edge-12 = front 12 mm of the upper wall). This step is
# not an ogee/bevel; it is a hairline face break.
LIP_FACE_BREAK_MM = 0.25
STATION_MARGIN = 0.02
# Cutters start this far in front of the board so no boolean face is coplanar with it.
PROUD_MM = 0.3
CONTACT_X_LIMIT = 63.0
MONO_X_MIN = 34.4

MONO_CENTER_X = 48.0
MONO_CENTER_Z = -22.0
# Measured on the mono node around that centre: r 13.6 mm at y = -16, r 11.8 mm at
# y = 10 (the reference floor). The exported floor sits at the published 28 mm
# (y = 11), where the same taper is 11.7 mm.
MONO_RIM_R = 13.6
MONO_FLOOR_R = 11.7
# External cord mouths on the top edge. The reference only models the mouth
# (board.json: interior omitted): r 3.4 mm, 3 mm deep, centred at x = +/-69.75, y = 1.
HOLE_X = 69.75
HOLE_Y = 1.0
HOLE_RADIUS = 3.4
HOLE_DEPTH = 3.0
HOLE_SIDES = 24
# Planar n-gon only — a true Cylinder fails compile_board partition (distToShape 1e-4).
MONO_SIDES = 48

NODE_IDS = {
    "body": "MXL_body_editable_skin_001",
    "edge-22": "MXL_edge_22_editable_skin_001",
    "edge-16": "MXL_edge_16_editable_skin_001",
    "edge-12": "MXL_edge_12_editable_skin_001",
    "mono-28": "MXL_mono_28_editable_skin_001",
}

MATERIAL_NAME = "neutral_tulipwood"
MATERIAL_BASE_COLOR = "0.72,0.55,0.36"
MATERIAL_ROUGHNESS = 0.58
MATERIAL_METALLIC = 0.0


def _world_points(stage, cache, path: str):
    prim = stage.GetPrimAtPath(path)
    mesh = UsdGeom.Mesh(prim)
    points = mesh.GetPointsAttr().Get()
    matrix = cache.GetLocalToWorldTransform(prim)
    out = []
    for point in points:
        world = matrix.Transform(point) * 1000.0
        out.append((world[0], -world[2], world[1]))
    return out


def _reference_texture(reference: Path) -> tuple[str, Path, str]:
    with zipfile.ZipFile(reference) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".png")]
        if len(names) != 1:
            raise ValueError(f"expected exactly one reference texture, found {names}")
        member = names[0]
        data = archive.read(member)
    scratch_root = Path(os.environ.get("HANGTEN_CAD_SCRATCH", "/tmp")) / f"{PACKAGE}-assets"
    scratch_root.mkdir(parents=True, exist_ok=True)
    scratch = scratch_root / os.path.basename(member)
    scratch.write_bytes(data)
    return os.path.basename(member), scratch, hashlib.sha256(data).hexdigest()


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


def _inverse_smoothstep(fraction: float) -> float:
    """Wall inset parameter for a depth fraction (exact inverse of a smoothstep)."""
    clamped = min(max(fraction, 0.0), 1.0)
    return 0.5 - math.sin(math.asin(1.0 - 2.0 * clamped) / 3.0)


def _loft_solid(sections):
    """Ruled loft through polygonal sections, capped.

    Every section shares its arc centres with the others and differs only in radius, so
    each lateral face is a planar trapezoid and tessellates exactly.
    """
    wires = [Part.makePolygon(list(points) + [points[0]]) for points in sections]
    return Part.makeLoft(wires, True, True)


def _triangle_solid(triangles):
    """Closed solid from an explicit triangle soup, outward-oriented.

    The crowned trough floor makes a quad between two wall stations non-planar, and a
    non-planar face would break `compile_board`'s surface-area partition check, which
    assumes tessellation is exact. Triangles are planar by construction, so the cutter is
    authored as triangles rather than lofted through polygon wires.
    """
    volume = 0.0
    for a, b, c in triangles:
        volume += (
            a.x * (b.y * c.z - b.z * c.y)
            - a.y * (b.x * c.z - b.z * c.x)
            + a.z * (b.x * c.y - b.y * c.x)
        )
    if volume < 0.0:
        triangles = [(a, c, b) for a, b, c in triangles]
    faces = [
        Part.Face(Part.makePolygon([a, b, c, a]))
        for a, b, c in triangles
    ]
    shell = Part.makeShell(faces)
    if not shell.isClosed():
        raise ValueError("triangulated cutter shell is not closed")
    solid = Part.makeSolid(shell)
    if solid.Volume <= 0.0:
        raise ValueError(f"triangulated cutter has non-positive volume {solid.Volume}")
    return solid


def _rounded_rect_points(radius: float, y: float, segments: int = CORNER_SEGMENTS):
    """CCW XZ envelope outline whose corner radius is `radius` (corner centres fixed)."""
    corners = (
        (CORNER_CENTER_X, -CORNER_CENTER_Z, -math.pi / 2.0, 0.0),
        (CORNER_CENTER_X, CORNER_CENTER_Z, 0.0, math.pi / 2.0),
        (-CORNER_CENTER_X, CORNER_CENTER_Z, math.pi / 2.0, math.pi),
        (-CORNER_CENTER_X, -CORNER_CENTER_Z, math.pi, 1.5 * math.pi),
    )
    points = []
    for cx, cz, start, end in corners:
        for index in range(segments + 1):
            angle = start + (end - start) * index / segments
            points.append(
                App.Vector(cx + radius * math.cos(angle), y, cz + radius * math.sin(angle))
            )
    return points


def _ngon_points(cx: float, cz: float, radius: float, y: float, sides: int = MONO_SIDES):
    return [
        App.Vector(
            cx + radius * math.cos(2.0 * math.pi * index / sides),
            y,
            cz + radius * math.sin(2.0 * math.pi * index / sides),
        )
        for index in range(sides)
    ]


def _body_solid():
    """Envelope with 15 mm XZ corners and a 4 mm roll into the front and back faces."""
    sections = []
    roll = []
    for index in range(EDGE_ROLL_SEGMENTS + 1):
        angle = 0.5 * math.pi * index / EDGE_ROLL_SEGMENTS
        inset = EDGE_ROLL_R * (1.0 - math.sin(angle))
        offset = EDGE_ROLL_R * (1.0 - math.cos(angle))
        roll.append((offset, inset))
    for offset, inset in roll:
        sections.append(_rounded_rect_points(CORNER_R - inset, Y_FRONT + offset))
    for offset, inset in reversed(roll):
        sections.append(_rounded_rect_points(CORNER_R - inset, Y_BACK - offset))
    return _loft_solid(sections)


def _trough_depth(spec: dict, core_x: float) -> float:
    """Local trough depth at a station on the stadium core segment.

    The reference wall is one uniform depth scaling of its centre profile, so the whole
    wall — not just the floor — follows this parabola.
    """
    t = core_x / TROUGH_HALF_LEN
    return spec["depth"] * (1.0 - spec["crown_fraction"] * t * t)


def _stadium_template():
    """CCW ring of (core_x, outward normal) samples of the stadium's core segment.

    A point of the outline inset by `s` is `(core_x + (R - s)*nx, z_center + (R - s)*nz)`,
    so every station reuses one template and corresponding samples stay aligned. The
    straight runs are subdivided because that is where the crowned floor bends.
    """
    template = []
    for index in range(TROUGH_ARC_SEGMENTS + 1):
        angle = -math.pi / 2.0 + math.pi * index / TROUGH_ARC_SEGMENTS
        template.append((TROUGH_HALF_LEN, math.cos(angle), math.sin(angle)))
    for index in range(1, TROUGH_STRAIGHT_SEGMENTS):
        span = 2.0 * TROUGH_HALF_LEN * index / TROUGH_STRAIGHT_SEGMENTS
        template.append((TROUGH_HALF_LEN - span, 0.0, 1.0))
    for index in range(TROUGH_ARC_SEGMENTS + 1):
        angle = math.pi / 2.0 + math.pi * index / TROUGH_ARC_SEGMENTS
        template.append((-TROUGH_HALF_LEN, math.cos(angle), math.sin(angle)))
    for index in range(1, TROUGH_STRAIGHT_SEGMENTS):
        span = 2.0 * TROUGH_HALF_LEN * index / TROUGH_STRAIGHT_SEGMENTS
        template.append((-TROUGH_HALF_LEN + span, 0.0, -1.0))
    return template


def _stations(spec: dict, absolute_depths=()):
    """Ordered wall stations of one trough, rim first.

    A ``fraction`` station rides the local trough depth, which is what keeps the wall a
    uniform scaling of the centre profile. An ``absolute`` station holds one constant y so
    a region boundary can land exactly on a published grip depth. Because the floor
    crowns, an absolute station sweeps across a band of fractions along the trough, and
    any fraction inside that band would cross it and fold the surface — so those are
    dropped and the ordering is then asserted at both ends of the sweep.
    """
    depth_center = spec["depth"]
    depth_end = _trough_depth(spec, TROUGH_HALF_LEN)
    bands = [
        (depth / depth_center - STATION_MARGIN, depth / depth_end + STATION_MARGIN)
        for depth in absolute_depths
    ]
    for depth in absolute_depths:
        if depth >= depth_end:
            raise ValueError(f"absolute station {depth} mm is deeper than the trough end")
    stations = [
        ("fraction", fraction)
        for fraction in WALL_FRACTIONS
        if all(not low < fraction < high for low, high in bands)
    ]
    stations += [("absolute", depth) for depth in absolute_depths]
    stations.sort(
        key=lambda station: (
            station[1] * depth_center if station[0] == "fraction" else station[1]
        )
    )
    for core_x in (0.0, TROUGH_HALF_LEN):
        depths = [_station_depth(spec, station, core_x) for station in stations]
        if any(b - a <= 1e-6 for a, b in zip(depths, depths[1:])):
            raise ValueError(f"wall stations are not ordered at core x {core_x}: {depths}")
    return stations


def _station_depth(spec: dict, station, core_x: float) -> float:
    kind, value = station
    if kind == "fraction":
        return _trough_depth(spec, core_x) * value
    return value


def _ring(spec: dict, template, station, *, y_override: float | None = None):
    """One closed ring of cutter vertices, one per template sample.

    Walls stay at the stadium rim radius (flat / vertical). Absolute lip
    stations take a `LIP_FACE_BREAK_MM` inward step so OCCT cannot merge the
    front lip band with the deeper wall into one coplanar face.
    """
    points = []
    for core_x, normal_x, normal_z in template:
        if station is None:
            depth, inset = 0.0, 0.0
        else:
            depth = _station_depth(spec, station, core_x)
            kind, _value = station
            if kind == "absolute":
                inset = LIP_FACE_BREAK_MM
            elif spec["apex_inset"] > 0.0:
                depth_local = _trough_depth(spec, core_x)
                inset = spec["apex_inset"] * _inverse_smoothstep(depth / depth_local)
            else:
                inset = 0.0
        radius = TROUGH_RADIUS - inset
        points.append(
            App.Vector(
                core_x + radius * normal_x,
                Y_FRONT + depth if y_override is None else y_override,
                spec["z_center"] + radius * normal_z,
            )
        )
    return points


def _cap_triangles(spec: dict, ring, *, flip: bool):
    """Close a stadium ring with facets that follow the crowned floor.

    A fan from one centre point would replace the parabolic floor with a cone, so the
    straight run is bridged strip by strip between its top and bottom samples, which pair
    up by x. Each end arc's samples all share one core x and therefore one y, so an arc
    is flat and can be fanned from its own axis point.
    """
    arc = TROUGH_ARC_SEGMENTS
    straight = TROUGH_STRAIGHT_SEGMENTS
    top = [arc] + list(range(arc + 1, arc + straight)) + [arc + straight]
    bottom = [2 * arc + straight] + list(
        range(2 * arc + straight + 1, 2 * arc + 2 * straight)
    ) + [0]
    bottom = list(reversed(bottom))  # now aligned with `top` by x

    triangles = []
    for index in range(straight):
        a, b = ring[top[index]], ring[top[index + 1]]
        c, d = ring[bottom[index + 1]], ring[bottom[index]]
        triangles.append((a, b, c))
        triangles.append((a, c, d))

    for start, axis_x in ((0, TROUGH_HALF_LEN), (arc + straight, -TROUGH_HALF_LEN)):
        axis = App.Vector(axis_x, ring[start].y, spec["z_center"])
        for index in range(start, start + arc):
            triangles.append((axis, ring[index], ring[index + 1]))

    if flip:
        triangles = [(a, c, b) for a, b, c in triangles]
    return triangles


def _trough_cutter(spec: dict, absolute_depths=()):
    """Stadium trough with a parabolically crowned floor, as planar triangles."""
    template = _stadium_template()
    rings = [_ring(spec, template, None, y_override=Y_FRONT - PROUD_MM)]
    rings += [_ring(spec, template, station) for station in _stations(spec, absolute_depths)]

    triangles = _cap_triangles(spec, rings[0], flip=True)
    count = len(template)
    for near, far in zip(rings, rings[1:]):
        for index in range(count):
            following = (index + 1) % count
            triangles.append((near[index], near[following], far[following]))
            triangles.append((near[index], far[following], far[index]))
    triangles += _cap_triangles(spec, rings[-1], flip=False)
    return _triangle_solid(triangles)


def _mono_radius(y: float, floor_y: float) -> float:
    t = min(max((y - Y_FRONT) / (floor_y - Y_FRONT), 0.0), 1.0)
    return MONO_RIM_R + (MONO_FLOOR_R - MONO_RIM_R) * t


def _mono_cutter():
    """Tapered bore in the lower trough's right end; planar n-gon, no Cylinder."""
    lower = TROUGHS["lower"]
    deepest = max(
        _trough_depth(lower, min(abs(MONO_CENTER_X - MONO_RIM_R), TROUGH_HALF_LEN)),
        _trough_depth(lower, min(abs(MONO_CENTER_X + MONO_RIM_R), TROUGH_HALF_LEN)),
    )
    apex_y = Y_FRONT + deepest
    floor_y = Y_FRONT + GRIP_DEPTH_MM["mono-28"]
    sections = [
        _ngon_points(MONO_CENTER_X, MONO_CENTER_Z, MONO_RIM_R, Y_FRONT - PROUD_MM),
        _ngon_points(MONO_CENTER_X, MONO_CENTER_Z, _mono_radius(apex_y, floor_y), apex_y),
        _ngon_points(MONO_CENTER_X, MONO_CENTER_Z, MONO_FLOOR_R, floor_y),
    ]
    return _loft_solid(sections)


def _hole_cutter(sign: float):
    """Shallow vertical mouth in the top edge. Circle in XY, lofted in Z, n-gon only."""
    cx = sign * HOLE_X
    z_open = HALF_Z + PROUD_MM
    z_floor = HALF_Z - HOLE_DEPTH

    def ring(z: float):
        return [
            App.Vector(
                cx + HOLE_RADIUS * math.cos(2.0 * math.pi * index / HOLE_SIDES),
                HOLE_Y + HOLE_RADIUS * math.sin(2.0 * math.pi * index / HOLE_SIDES),
                z,
            )
            for index in range(HOLE_SIDES)
        ]

    return _loft_solid([ring(z_open), ring(z_floor)])


def _in_trough(spec: dict, x: float, z: float, slack: float = 0.2) -> bool:
    radial = math.hypot(max(abs(x) - TROUGH_HALF_LEN, 0.0), z - spec["z_center"])
    return radial <= TROUGH_RADIUS + slack


def _is_front_plane(face) -> bool:
    box = face.BoundBox
    return box.YLength < 0.01 and abs(box.YMin - Y_FRONT) < 0.05


def _wall_filter(spec: dict, *, above: bool, y_max: float, x_min: float, x_max: float):
    """Match trough-wall faces on one side of the apex, no deeper than `y_max`.

    The side test is on the face's whole extent, not its centroid. Each x strip of the
    floor is one plane, so the boolean hands it back as a single face spanning the full
    apex width, and a centroid test would assign it by whichever side a rounding error
    fell on. A face that straddles the centre line belongs to neither wall and stays with
    the body, which is also where the reference's own node split leaves it.
    """
    z_center = spec["z_center"]

    def matches(face) -> bool:
        box = face.BoundBox
        if _is_front_plane(face) or box.YLength < 0.01:
            return False
        if box.YMin < Y_FRONT - 0.05 or box.YMax > y_max + 0.05:
            return False
        center = face.CenterOfMass
        if not _in_trough(spec, center.x, center.z):
            return False
        if not x_min <= center.x <= x_max:
            return False
        return box.ZMin >= z_center - 0.05 if above else box.ZMax <= z_center + 0.05

    return matches


def _mono_filter(spec: dict):
    """Match the lower trough's right end plus the bore walls and floor."""
    floor_y = Y_FRONT + GRIP_DEPTH_MM["mono-28"]

    def matches(face) -> bool:
        box = face.BoundBox
        if _is_front_plane(face):
            return False
        if box.YMin < Y_FRONT - 0.05 or box.YMax > floor_y + 0.05:
            return False
        center = face.CenterOfMass
        if center.x < MONO_X_MIN:
            return False
        bore_radial = math.hypot(center.x - MONO_CENTER_X, center.z - MONO_CENTER_Z)
        return _in_trough(spec, center.x, center.z) or bore_radial <= MONO_RIM_R + 0.2

    return matches


def _shell_from_body_faces(body_shape, predicate):
    faces = [face for face in body_shape.Faces if predicate(face)]
    if not faces:
        raise ValueError("no body faces matched the contact predicate")
    if len(faces) == 1:
        return faces[0]
    return Part.makeCompound(faces)


def main() -> int:
    board = json.loads(BOARD_JSON.read_text())
    scratch = Path(os.environ.get("HANGTEN_CAD_SCRATCH", "/tmp")) / f"{PACKAGE}-assets"
    reference, reference_digest = load_reference(PACKAGE, "primary.usdz", scratch / "ref")
    stage = Usd.Stage.Open(str(reference))
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    body_points = _world_points(stage, cache, BODY_PRIM)
    measured = {
        "width": max(p[0] for p in body_points) - min(p[0] for p in body_points),
        "depth": max(p[1] for p in body_points) - min(p[1] for p in body_points),
        "height": max(p[2] for p in body_points) - min(p[2] for p in body_points),
    }
    for key, target in (("width", BODY_X), ("depth", BODY_Y), ("height", BODY_Z)):
        if abs(measured[key] - target) > 0.2:
            raise ValueError(f"reference {key} {measured[key]:.3f} mm != target {target}")

    texture_member, texture_source, texture_digest = _reference_texture(reference)

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
    document.HangTenTessellationDeflection = 0.05

    brick = document.addObject("Part::Feature", "OuterEnvelope")
    # Rolled envelope is authored into the solid (not a post-cut Shape assign on Part::Cut).
    brick.Shape = _body_solid()
    document.recompute()
    brick_box = brick.Shape.BoundBox
    expected = (-HALF_X, Y_FRONT, -HALF_Z, HALF_X, Y_BACK, HALF_Z)
    actual = (
        brick_box.XMin,
        brick_box.YMin,
        brick_box.ZMin,
        brick_box.XMax,
        brick_box.YMax,
        brick_box.ZMax,
    )
    if any(abs(a - b) > 0.2 for a, b in zip(actual, expected)):
        raise ValueError(f"envelope bbox {actual} != expected {expected}")

    upper = TROUGHS["upper"]
    lower = TROUGHS["lower"]
    cutters = [
        _trough_cutter(upper, absolute_depths=(GRIP_DEPTH_MM["edge-12"],)),
        _trough_cutter(lower),
        _mono_cutter(),
        _hole_cutter(1.0),
        _hole_cutter(-1.0),
    ]

    contact_predicates = [
        (
            "edge-16",
            _wall_filter(
                upper,
                above=False,
                y_max=Y_FRONT + upper["depth"],
                x_min=-CONTACT_X_LIMIT,
                x_max=CONTACT_X_LIMIT,
            ),
        ),
        (
            "edge-12",
            _wall_filter(
                upper,
                above=True,
                y_max=Y_FRONT + GRIP_DEPTH_MM["edge-12"],
                x_min=-CONTACT_X_LIMIT,
                x_max=CONTACT_X_LIMIT,
            ),
        ),
        (
            # The reference hands the lower trough's right end to the mono, not to edge-22.
            "edge-22",
            _wall_filter(
                lower,
                above=False,
                y_max=Y_FRONT + lower["depth"],
                x_min=-CONTACT_X_LIMIT,
                x_max=MONO_X_MIN,
            ),
        ),
        ("mono-28", _mono_filter(lower)),
    ]

    fused_shape = cutters[0]
    for cutter in cutters[1:]:
        fused_shape = fused_shape.fuse(cutter)
    cutter_obj = document.addObject("Part::Feature", "TroughCutters")
    cutter_obj.Shape = fused_shape

    body_cut = document.addObject("Part::Cut", "BodyCut")
    body_cut.Base = brick
    body_cut.Tool = cutter_obj

    document.recompute()
    if body_cut.Shape.isNull() or body_cut.Shape.Volume < 1.0:
        raise ValueError("boolean cut failed to produce a solid body")

    # Bake into Part::Feature so a later recompute cannot wipe the solid (Part::Cut is Base/Tool).
    body = document.addObject("Part::Feature", "BodySolid")
    body.Shape = body_cut.Shape
    body.addProperty("App::PropertyString", "NodeID", "HangTen")
    body.addProperty("App::PropertyString", "NodeRole", "HangTen")
    body.NodeID = NODE_IDS["body"]
    body.NodeRole = "body"
    _apply_material(body, texture_source)

    document.recompute()
    body_shape = body.Shape
    if body_shape.isNull() or body_shape.Volume < 1.0:
        raise ValueError("cut body failed to produce a solid")

    regions = {}
    for contact_id, predicate in contact_predicates:
        feature = document.addObject("Part::Feature", f"Contact_{contact_id.replace('-', '_')}")
        feature.Shape = _shell_from_body_faces(body_shape, predicate)
        feature.addProperty("App::PropertyString", "NodeID", "HangTen")
        feature.addProperty("App::PropertyString", "NodeRole", "HangTen")
        feature.addProperty("App::PropertyString", "ContactID", "HangTen")
        feature.NodeID = NODE_IDS[contact_id]
        feature.NodeRole = "contact"
        feature.ContactID = contact_id
        _apply_material(feature, None)
        box = feature.Shape.BoundBox
        regions[contact_id] = {
            "faces": len(feature.Shape.Faces),
            "x": (round(box.XMin, 2), round(box.XMax, 2)),
            "z": (round(box.ZMin, 2), round(box.ZMax, 2)),
            "depth": round(box.YLength, 3),
        }

    document.recompute()
    stale = [obj.Name for obj in document.Objects if "Invalid" in obj.State or "Error" in obj.State]
    if stale:
        raise ValueError(f"document failed recompute: {stale}")

    for contact_id, published in GRIP_DEPTH_MM.items():
        measured_depth = regions[contact_id]["depth"]
        if abs(measured_depth - published) > 0.25:
            raise ValueError(
                f"{contact_id} region depth {measured_depth} mm != published {published} mm"
            )

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    document.saveAs(str(DESTINATION))

    print(f"authored {DESTINATION} ({DESTINATION.stat().st_size} bytes)")
    print(f"reference envelope mm: {measured}")
    print(f"body faces: {len(body_shape.Faces)}  volume {body_shape.Volume:.0f} mm^3")
    for name, spec in TROUGHS.items():
        print(
            f"  {name} trough floor: {spec['depth']:.2f} mm at x=0, "
            f"{_trough_depth(spec, TROUGH_HALF_LEN):.2f} mm at x=+/-{TROUGH_HALF_LEN:.0f}"
        )
    for contact_id, info in regions.items():
        print(
            f"  {contact_id:8s} faces={info['faces']:3d} x={info['x']} z={info['z']} "
            f"depth={info['depth']} (published {GRIP_DEPTH_MM[contact_id]})"
        )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
