"""One-off migration: author Hangboards/lattice-mxedge-lift-small/lattice-mxedge-lift-small.FCStd.

Migration tool only — not a build input.

Provenance:
* Overall envelope 168 x 34 x 98 mm (±84 / ±17 / ±49) and grip depths 18 / 14 / 8 / 25 mm
  from board.json / reference mesh packaging. Catalogue copy "20 × 11 × 5 cm" is rounded
  marketing and is **not** used to rescale the body.
* MXSMALL grips (Lattice MXEdge Lift): MX18, MX14, MX8 + 25 mm mono — area-equivalent
  labels; true depth varies along length (crowned floors).
* Front geometry measured from the Git-resolved reference USDZ (pre-migration commit via
  reference.load_reference) by depth-mapping its front surface on a 0.5 mm grid:
  - the front carries **two stadium troughs**, not four separate openings. Every x column
    of the reference front has exactly two recessed runs, z [10.5, 34.5] and
    z [-32.5, -8.5], both spanning the full width. The four published grips are a
    *partition of those two troughs*, not four pockets: edge-8 and edge-14 are the upper
    and lower walls of the upper trough (their reference AABBs meet at z = 23), and
    edge-18 and mono-25 split the lower one;
  - each trough is a stadium: arc centres at x = +/-48 mm, rim radius 14 mm, centred at
    z = 22.5 (upper) and z = -20.5 (lower);
  - each trough wall is a **front roll, a straight face, then a roll into the floor** —
    the published MXEdge cross-section (front radius, top face, back radius), not one
    continuous ogee. Sections cut at 0.1 mm through the reference give a face that
    plateaus at 56-58 deg (upper trough) and 65-66 deg (lower), with each roll spanning
    3.5-4 mm of inset:

        upper, x = 0.3   apex 12.50 mm   roll 0->3.5   face 56-58 deg   roll 7.5->11.2
        upper, x = 48    apex 10.06 mm   roll 0->4.0   face 51-55 deg   roll 7.5->11.0
        lower, x = 0.3   apex 16.60 mm   roll 0->4.0   face 65-66 deg   roll 6.5->10.7

    The rolls are progressive rather than circular: the sculpt's osculating radius at the
    rim is under 1.5 mm and grows along the roll, so the rim reaches 30 deg within 1.0 mm
    of inset and reads as a knife edge rather than a bevel;
  - the walls are what the reference renders as one dark band (upper wall, facing down)
    and one bright band (lower wall, facing up) per trough;
  - **the floor is crowned along the trough's length** — deepest at the centre and
    shallower toward the ends, which is the published MXEdge behaviour ("true depth
    varies along length"). The reference wall is one uniform depth scaling of its centre
    profile: at every z the measured depth is depth(x = 0) * (1 - c * (x/48)^2), holding
    to 0.03 mm for c = 0.1952 (upper) and c = 0.1885 (lower). The rim outline itself does
    not change along x. Cutters therefore scale depth by that parabola and leave the
    inset profile alone. The physical / reference upper trough is **one** stadium opening
    with **one** floor (no stepped shelf); MX8 and MX14 are partitions of that trough;
  - measured trough centre depths are 12.5 mm (upper) and 16.5 mm (lower). This model
    uses the published 14 mm / 18 mm instead, so each exported region's depth equals the
    depth board.json publishes. Stated deviation: floors 1.5 mm deeper than measured;
  - the mono is a bore inside the lower trough's right end: measured rim r 10.7 mm at
    (x 48.4, z -20.3), near-cylindrical to a floor of r 9.2 mm. The floor is placed at
    the published 25 mm (measured 27.2 mm);
  - front and back perimeter roll r 4 mm (the measured front face is flat only to
    |z| <= 45 mm), outer corner radius 15 mm. Both come from the reference silhouette:
    a 15 mm corner reproduces its measured max |x| at |z| = 36/40/44/46/48 to 0.25 mm.
* Display material texture embedded from the same reference package.
* Measured approximation of a sculpted display mesh — not manufacturing geometry.

Region partition. `compile_board` requires each region's extent along the depth axis to
equal the published grip depth, and the reference's own nodes do not (its edge-8 node
spans the full upper trough). The upper trough is authored as **one stadium opening with
one crowned floor** at the published 14 mm (x = 0). edge-8 / edge-14 split on the z = 23
line the reference nodes already meet on:

    edge-8   upper trough above z = 23: upper-wall lip only     y [-17, -9]  span  8
    edge-14  upper trough below z = 23: wall + single floor     y [-17, -3]  span 14
    edge-18  lower trough, lower wall, full depth               y [-17, +1]  span 18
    mono-25  lower trough right end + bore incl. floor          y [-17, +8]  span 25

edge-8 is therefore the front 8 mm of the upper wall (the lip actually gripped), not a
second floor. The single upper floor belongs to edge-14.

Wall front radius. Lattice publishes ~10 mm on the physical edge. With the measured apex
insets (upper 11.2 mm, lower 11.0 mm) and a 2 mm back roll, a 10 mm front roll does not
leave a straight face (front + back would meet or exceed the inset). This model uses
**8.9 mm** — the largest front radius ≤ 10 mm that still leaves a measurable straight
face on both troughs (≥ 3.7 mm upper, ≥ 7.2 mm lower). Stated residual vs Lattice ~10 mm:
1.1 mm. The roll opens toward the trough's ends under crown depth-scaling (published
behaviour: larger front radius at the ends, smaller at the centre).

Because the floor is crowned, a region's deepest face is the one at x = 0; each of those
spans reaches the published depth there and no deeper.
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

PACKAGE = "lattice-mxedge-lift-small"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
BODY_PRIM = "/root/body/Body_actual_surface_001"

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
    "edge-18": 18.0,
    "edge-14": 14.0,
    "edge-8": 8.0,
    "mono-25": 25.0,
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
        "z_center": 22.5,
        "depth": GRIP_DEPTH_MM["edge-14"],
        "crown_fraction": 0.1952,
        # Measured apex inset 11.2 mm (half-width 2.8). Restored now that the upper
        # trough is a single floor again — no shelf-widening.
        "apex_inset": 11.2,
        # Reference edge-8 / edge-14 node AABBs meet on this line; partitions the one
        # opening (wall lip vs wall+floor), not two floor levels.
        "split_z": 23.0,
    },
    "lower": {
        "z_center": -20.5,
        "depth": GRIP_DEPTH_MM["edge-18"],
        "crown_fraction": 0.1885,
        "apex_inset": 11.0,
    },
}
# Wall cross-section: front roll, straight face, roll into the floor. The radii are of the
# centre profile; depth-scaling by the crown opens both rolls toward the trough's ends.
# Lattice publishes ~10 mm front; 8.9 mm is the largest ≤10 that still leaves a straight
# face inside the measured inset budget with the 2 mm back roll (see module docstring).
WALL_FRONT_RADIUS = 8.9
WALL_BACK_RADIUS = 2.0
# Segment counts per profile zone. The front roll carries the most because it is the band
# whose shading gradient is what reads as the bevel.
WALL_FRONT_SEGMENTS = 9
WALL_FACE_SEGMENTS = 3
WALL_BACK_SEGMENTS = 3
# Cutters start this far in front of the board so no boolean face is coplanar with it.
PROUD_MM = 0.3

# Partition boundaries measured on the reference's own contact nodes.
CONTACT_X_LIMIT = 57.0
MONO_X_MIN = 37.5

MONO_CENTER_X = 48.4
MONO_CENTER_Z = -20.3
MONO_RIM_R = 10.7
MONO_TAPER_R = 10.2
MONO_FLOOR_R = 9.2
MONO_TAPER_DEPTH = 4.0
# Planar n-gon only — a true Cylinder fails compile_board partition (distToShape 1e-4).
MONO_SIDES = 48

NODE_IDS = {
    "body": "Body_actual_surface_001",
    "edge-18": "edge_18_actual_surface_001",
    "edge-14": "edge_14_actual_surface_001",
    "edge-8": "edge_8_actual_surface_001",
    "mono-25": "mono_25_actual_surface_001",
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


def _wall_face_angle(
    inset_max: float, depth: float, front_radius: float, back_radius: float
) -> float:
    """Angle of the wall's straight face from the front face plane.

    The wall leaves the rim tangent to the front face, turns through `front_radius` to the
    face angle t, runs straight, then turns back through `back_radius` tangent to the
    floor. Each roll displaces the profile by r*(sin t, 1 - cos t), so

        inset_max = (front_radius + back_radius) sin t + straight cos t
        depth     = (front_radius + back_radius) (1 - cos t) + straight sin t

    and eliminating `straight` leaves one equation in t, increasing on (0, pi/2):

        inset_max sin t - depth cos t = (front_radius + back_radius) (1 - cos t)
    """
    blend = front_radius + back_radius
    if blend >= inset_max or blend > depth:
        raise ValueError(
            f"wall rolls {blend} mm do not fit an inset of {inset_max} mm "
            f"and a depth of {depth} mm"
        )
    low, high = 0.0, 0.5 * math.pi
    for _ in range(80):
        middle = 0.5 * (low + high)
        residual = (
            inset_max * math.sin(middle)
            - depth * math.cos(middle)
            - blend * (1.0 - math.cos(middle))
        )
        if residual < 0.0:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def _wall_stations(spec: dict, depth: float, *, lip_depth: float | None = None):
    """(inset mm, depth fraction) stations down one wall of a trough.

    The inset is authored in millimetres and the depth is carried as a fraction, so a
    station off the trough's centre takes the same fraction of its own crowned depth.
    That keeps the wall one uniform depth scaling of its centre profile, which is what the
    reference measures as, and it opens the rolls toward the trough's ends.

    When `lip_depth` is set, a station is inserted at fraction lip_depth/depth so a
    contact boundary can land exactly on a published grip depth at x = 0.
    """
    inset_max = spec["apex_inset"]
    blend = WALL_FRONT_RADIUS + WALL_BACK_RADIUS
    angle = _wall_face_angle(inset_max, depth, WALL_FRONT_RADIUS, WALL_BACK_RADIUS)
    straight = (inset_max - blend * math.sin(angle)) / math.cos(angle)

    stations = []
    for index in range(WALL_FRONT_SEGMENTS + 1):
        turn = angle * index / WALL_FRONT_SEGMENTS
        stations.append(
            (WALL_FRONT_RADIUS * math.sin(turn), WALL_FRONT_RADIUS * (1.0 - math.cos(turn)))
        )
    roll_inset, roll_depth = stations[-1]
    for index in range(1, WALL_FACE_SEGMENTS + 1):
        run = straight * index / WALL_FACE_SEGMENTS
        stations.append(
            (roll_inset + run * math.cos(angle), roll_depth + run * math.sin(angle))
        )
    face_inset, face_depth = stations[-1]
    for index in range(1, WALL_BACK_SEGMENTS + 1):
        turn = angle * index / WALL_BACK_SEGMENTS
        stations.append(
            (
                face_inset + WALL_BACK_RADIUS * (math.sin(angle) - math.sin(angle - turn)),
                face_depth + WALL_BACK_RADIUS * (math.cos(angle - turn) - math.cos(angle)),
            )
        )
    if abs(stations[-1][0] - inset_max) > 1e-6 or abs(stations[-1][1] - depth) > 1e-6:
        raise ValueError(
            f"wall profile ends at {stations[-1]}, expected ({inset_max}, {depth})"
        )
    fractions = [(inset, level / depth) for inset, level in stations]
    if lip_depth is not None:
        if not 0.0 < lip_depth < depth:
            raise ValueError(f"lip depth {lip_depth} mm is outside (0, {depth})")
        fractions = _insert_fraction(fractions, lip_depth / depth)
    return fractions, angle


def _insert_fraction(stations, target_fraction: float):
    """Insert a wall station at `target_fraction` by interpolating inset."""
    for index, (inset, fraction) in enumerate(stations):
        if abs(fraction - target_fraction) < 1e-9:
            return stations
        if fraction > target_fraction:
            if index == 0:
                raise ValueError(f"lip fraction {target_fraction} is before the rim")
            prev_inset, prev_fraction = stations[index - 1]
            span = fraction - prev_fraction
            if span <= 0.0:
                raise ValueError("wall stations are not ordered by fraction")
            t = (target_fraction - prev_fraction) / span
            inserted = (prev_inset + t * (inset - prev_inset), target_fraction)
            return stations[:index] + [inserted] + stations[index:]
    raise ValueError(f"lip fraction {target_fraction} is past the floor")


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


def _ring(spec: dict, template, station, *, y_override: float | None = None):
    """One closed ring of cutter vertices at one station of the wall profile.

    A station fixes the inset in millimetres and the depth as a *fraction* of the local
    trough depth rather than as an absolute y, which is what keeps the wall a uniform
    scaling of the centre profile as the floor crowns.
    """
    inset, fraction = (0.0, 0.0) if station is None else station
    points = []
    for core_x, normal_x, normal_z in template:
        depth = _trough_depth(spec, core_x) * fraction
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


def _trough_cutter(spec: dict, *, lip_depth: float | None = None):
    """Stadium trough with a parabolically crowned floor, as planar triangles."""
    template = _stadium_template()
    stations, _ = _wall_stations(spec, spec["depth"], lip_depth=lip_depth)
    rings = [_ring(spec, template, None, y_override=Y_FRONT - PROUD_MM)]
    rings += [_ring(spec, template, station) for station in stations]

    triangles = _cap_triangles(spec, rings[0], flip=True)
    count = len(template)
    for near, far in zip(rings, rings[1:]):
        for index in range(count):
            following = (index + 1) % count
            triangles.append((near[index], near[following], far[following]))
            triangles.append((near[index], far[following], far[index]))
    triangles += _cap_triangles(spec, rings[-1], flip=False)
    return _triangle_solid(triangles)


def _mono_cutter():
    """Bore inside the lower trough's right end; no Cylinder, planar n-gon only."""
    lower = TROUGHS["lower"]
    # Stay cylindrical until below the crowned trough floor across the whole bore mouth,
    # so the taper starts in solid material rather than part way across the floor.
    deepest = max(
        _trough_depth(lower, min(abs(MONO_CENTER_X - MONO_RIM_R), TROUGH_HALF_LEN)),
        _trough_depth(lower, min(abs(MONO_CENTER_X + MONO_RIM_R), TROUGH_HALF_LEN)),
    )
    apex_y = Y_FRONT + deepest
    floor_y = Y_FRONT + GRIP_DEPTH_MM["mono-25"]
    sections = [
        _ngon_points(MONO_CENTER_X, MONO_CENTER_Z, MONO_RIM_R, Y_FRONT - PROUD_MM),
        _ngon_points(MONO_CENTER_X, MONO_CENTER_Z, MONO_RIM_R, apex_y),
        _ngon_points(MONO_CENTER_X, MONO_CENTER_Z, MONO_TAPER_R, apex_y + MONO_TAPER_DEPTH),
        _ngon_points(MONO_CENTER_X, MONO_CENTER_Z, MONO_FLOOR_R, floor_y),
    ]
    return _loft_solid(sections)


def _in_trough(spec: dict, x: float, z: float, slack: float = 0.2) -> bool:
    radial = math.hypot(max(abs(x) - TROUGH_HALF_LEN, 0.0), z - spec["z_center"])
    return radial <= TROUGH_RADIUS + slack


def _is_front_plane(face) -> bool:
    box = face.BoundBox
    return box.YLength < 0.01 and abs(box.YMin - Y_FRONT) < 0.05


def _is_trough_floor(face, spec: dict) -> bool:
    """True if `face` lies on the crowned trough floor rather than a wall.

    Floor facets sit in the apex band around z_center and at the local floor depth band.
    They must go to the deep-side contact (edge-14 / edge-18): a single floor spans the
    full apex in z and would otherwise straddle the wall split line.
    """
    box = face.BoundBox
    shallowest = Y_FRONT + _trough_depth(spec, TROUGH_HALF_LEN) - 0.3
    deepest = Y_FRONT + spec["depth"] + 0.3
    if box.YMin < shallowest or box.YMax > deepest:
        return False
    apex = TROUGH_RADIUS - spec["apex_inset"]
    center = face.CenterOfMass
    return abs(center.z - spec["z_center"]) <= apex + 0.5


def _wall_filter(spec: dict, *, above: bool, y_max: float, x_min: float, x_max: float):
    """Match trough faces on one side of the split line, no deeper than `y_max`.

    The side test is on the face's whole extent, not its centroid. Each x strip of a
    wall band is one plane, so the boolean can hand back a face spanning a wide z run,
    and a centroid test would assign it by whichever side a rounding error fell on. A
    wall face that straddles the split line belongs to neither side and stays with the
    body, which is also where the reference's own node split leaves it.

    The single crowned floor is the exception: it spans the apex across the split and
    belongs to the deep side (the published deeper grip that owns the floor).
    """
    split_z = spec.get("split_z", spec["z_center"])

    def matches(face) -> bool:
        box = face.BoundBox
        if _is_front_plane(face):
            return False
        if box.YMin < Y_FRONT - 0.05 or box.YMax > y_max + 0.05:
            return False
        center = face.CenterOfMass
        if not _in_trough(spec, center.x, center.z):
            return False
        if not x_min <= center.x <= x_max:
            return False
        if _is_trough_floor(face, spec):
            return not above
        if box.YLength < 0.01:
            return False
        return box.ZMin >= split_z - 0.05 if above else box.ZMax <= split_z + 0.05

    return matches


def _mono_filter(spec: dict):
    """Match the lower trough's right end plus the bore walls and floor."""
    floor_y = Y_FRONT + GRIP_DEPTH_MM["mono-25"]

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
        _trough_cutter(upper, lip_depth=GRIP_DEPTH_MM["edge-8"]),
        _trough_cutter(lower),
        _mono_cutter(),
    ]

    contact_predicates = [
        (
            # Below z = 23: lower wall of the upper trough plus the single crowned floor.
            "edge-14",
            _wall_filter(
                upper,
                above=False,
                y_max=Y_FRONT + upper["depth"],
                x_min=-CONTACT_X_LIMIT,
                x_max=CONTACT_X_LIMIT,
            ),
        ),
        (
            # Above z = 23: front 8 mm of the upper wall — the lip actually gripped.
            "edge-8",
            _wall_filter(
                upper,
                above=True,
                y_max=Y_FRONT + GRIP_DEPTH_MM["edge-8"],
                x_min=-CONTACT_X_LIMIT,
                x_max=CONTACT_X_LIMIT,
            ),
        ),
        (
            # The reference hands the lower trough's right end to the mono, not to edge-18.
            "edge-18",
            _wall_filter(
                lower,
                above=False,
                y_max=Y_FRONT + lower["depth"],
                x_min=-CONTACT_X_LIMIT,
                x_max=MONO_X_MIN,
            ),
        ),
        ("mono-25", _mono_filter(lower)),
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
    if DESTINATION.exists():
        DESTINATION.unlink()
    document.saveAs(str(DESTINATION))

    print(f"authored {DESTINATION} ({DESTINATION.stat().st_size} bytes)")
    print(f"reference envelope mm: {measured}")
    print(f"body faces: {len(body_shape.Faces)}  volume {body_shape.Volume:.0f} mm^3")
    for name, spec in TROUGHS.items():
        _, angle = _wall_stations(spec, spec["depth"])
        print(
            f"  {name} trough floor: {spec['depth']:.2f} mm at x=0, "
            f"{_trough_depth(spec, TROUGH_HALF_LEN):.2f} mm at x=+/-{TROUGH_HALF_LEN:.0f}"
            f"; wall face {math.degrees(angle):.1f} deg over"
            f" front roll r{WALL_FRONT_RADIUS:.1f} / back roll r{WALL_BACK_RADIUS:.1f}"
            f"; apex inset {spec['apex_inset']:.1f} mm"
        )
        if "split_z" in spec:
            print(
                f"  {name} trough partition at z={spec['split_z']:.1f}: "
                f"edge-8 lip {GRIP_DEPTH_MM['edge-8']:.0f} mm / "
                f"edge-14 floor {spec['depth']:.0f} mm (single crowned floor)"
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
