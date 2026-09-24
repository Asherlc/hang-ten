"""One-off migration: author Hangboards/lattice-mxedge-lift-small/lattice-mxedge-lift-small.FCStd.

Migration tool only — not a build input.

Provenance:
* Overall envelope 168 x 34 x 98 mm and grip depths 18 / 14 / 8 / 25 mm from board.json.
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
    inset profile alone. Measured on the upper trough, each half of the z = 23 split
    crowns by the same parabola (c = 0.1950 above and below), so both of this model's
    upper floor levels use one crown;
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

Region partition. The published grips are two per trough and the reference's own node
AABBs say where each one starts and stops, but the reference *sculpt* does not carry the
published depths: its upper trough is one floor 12.5 mm deep for both edge-8 and edge-14
(measured: flat y = -4.5 across z 19.5..26 at x = 0, no step anywhere along z), while
board.json publishes 8 mm and 14 mm. This model therefore gives the upper trough **one
stadium opening and two crowned floor levels**, stepping at the z = 23 line the
reference's nodes already split on — 8 mm above it, 14 mm below — so each grip's geometry
is the depth the board publishes and the step is visible as a shelf inside the pocket.
Stated deviation: the reference upper trough has no step.

Two deliberate departures from the measured sculpt make the wall and the step read as
geometry rather than as a flat cut:

* the authored front roll is a 6 mm radius, against the sculpt's sub-1.5 mm rim
  curvature. Lattice publishes a ~10 mm front radius on the physical edge, so a defined
  front radius is the product's cross-section; 6 mm is the largest that still leaves a
  straight face inside this trough's inset budget. The roll opens toward the trough's
  ends because the wall is depth-scaled by the crown, which is also the published
  behaviour (larger front radius at the ends, smaller at the centre);
* the upper trough's floor is widened (apex inset 9.5 mm, against a measured 11.2 mm) so
  each level keeps a readable shelf, and the step riser leans back 2 mm of z between the
  levels so it has real projected width in a front view. A riser normal to the front face
  projects to a zero-width line and the two levels cannot be told apart at all.

  The riser is **not a plane**. No plane can do this job: a plane swept along x meets a
  crowned floor at a z that follows the crown, so its exposed edge wanders in z (0.52 mm
  on the shallow level, 0.91 mm on the deep one) and tessellation turns that wander into a
  visible staircase. The riser is instead the surface **ruled between two constant-z
  lines** — it meets the 8 mm floor at z = 23 and the 14 mm floor at z = 21 at every x —
  which is the same rule the walls already follow: the step is authored as a lean in the
  trough's *depth-fraction* coordinate, so depth-scaling by the crown moves the riser's
  depth without moving its z. Both exposed edges are then exactly straight lines.

  The lower trough keeps its measured apex inset.

    edge-8   upper trough above z = 23: wall + 8 mm floor    y [-17, -9]   span  8
    edge-14  upper trough below z = 23: step riser, 14 mm
             floor, wall                                     y [-17, -3]   span 14
    edge-18  lower trough, lower wall, full depth            y [-17, +1]   span 18
    mono-25  lower trough right end + bore incl. floor       y [-17, +8]   span 25

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
        # Measured apex half-width is 2.8 mm (inset 11.2). Widened here because this
        # trough carries two floor levels: at 9.5 mm each level keeps a shelf wide enough
        # to read either side of the riser. Stated deviation.
        "apex_inset": 9.5,
        # Two floor levels in the one opening. The split is the z the reference's own
        # edge-8 and edge-14 nodes meet on; each level's depth is what board.json
        # publishes for the grip on that side of it.
        "step_z": 23.0,
        "step_depth": GRIP_DEPTH_MM["edge-8"],
        # z the riser leans back between the two floors, giving it projected width in a
        # front view. It is constant along the trough: the riser meets the shallow floor
        # at `step_z` and the deep floor at `step_z - step_run` at every x.
        "step_run": 2.0,
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
WALL_FRONT_RADIUS = 6.0
WALL_BACK_RADIUS = 2.0
# Segment counts per profile zone. The front roll carries the most because it is the band
# whose shading gradient is what reads as the bevel.
WALL_FRONT_SEGMENTS = 9
WALL_FACE_SEGMENTS = 3
WALL_BACK_SEGMENTS = 3
# Cutters start this far in front of the board so no boolean face is coplanar with it.
PROUD_MM = 0.3
# Stations across the trough's straight run at which the step riser's two exposed edges
# are checked for being straight. Beyond the straight run the floor is the stadium's end
# arc and pinches away from the riser's z band, so the shelf tapers out there.
STEP_EDGE_PROBES = 24

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


def _wall_stations(spec: dict, depth: float):
    """(inset mm, depth fraction) stations down one wall of a trough.

    The inset is authored in millimetres and the depth is carried as a fraction, so a
    station off the trough's centre takes the same fraction of its own crowned depth.
    That keeps the wall one uniform depth scaling of its centre profile, which is what the
    reference measures as, and it opens the rolls toward the trough's ends.
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
    return [(inset, level / depth) for inset, level in stations], angle


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


def _trough_cutter(spec: dict):
    """Stadium trough with a parabolically crowned floor, as planar triangles."""
    template = _stadium_template()
    stations, _ = _wall_stations(spec, spec["depth"])
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


def _step_levels(spec: dict, x: float) -> tuple[float, float]:
    """(shallow, deep) floor y at `x` — the two lines the step riser is ruled between."""
    core_x = max(-TROUGH_HALF_LEN, min(TROUGH_HALF_LEN, x))
    return (
        Y_FRONT + _trough_depth(dict(spec, depth=spec["step_depth"]), core_x),
        Y_FRONT + _trough_depth(spec, core_x),
    )


def _step_surface_z(spec: dict, x: float, y: float) -> float:
    """z of the trough's step divider at (x, y).

    The divider leans back `step_run` mm of z, but it leans in the trough's *depth
    fraction* rather than in absolute depth: it sits at `step_z` wherever the material is
    shallower than the shallow floor, at `step_z - step_run` wherever it is deeper than
    the deep floor, and interpolates between. Since both floors are the same crown scaled
    by their published depth, the divider therefore meets each of them on a line of
    constant z, and the two edges the front view draws are straight.

    A plane cannot do that. Swept along x it crosses a crowned floor wherever the floor
    has risen to meet it, so its edge follows the crown; that is what read as a jagged
    divider rather than a shelf.
    """
    shallow_y, deep_y = _step_levels(spec, x)
    z_high = spec["step_z"]
    z_low = z_high - spec["step_run"]
    if y <= shallow_y:
        return z_high
    if y >= deep_y:
        return z_low
    return z_high + (z_low - z_high) * (y - shallow_y) / (deep_y - shallow_y)


def _step_offset(spec: dict, x: float, y: float, z: float) -> float:
    """Signed z distance from the trough's step divider; positive on the shallow side."""
    return z - _step_surface_z(spec, x, y)


def _step_x_samples():
    """x stations of the step divider.

    These are the trough template's own straight-run samples, so the divider's
    piecewise-linear crown *is* the floor's piecewise-linear crown and the two meet
    exactly on the constant-z line rather than a chord of it. Beyond the straight run the
    floor is flat at its |x| = TROUGH_HALF_LEN depth, and `_step_levels` clamps to match.
    """
    inner = sorted(
        TROUGH_HALF_LEN - 2.0 * TROUGH_HALF_LEN * index / TROUGH_STRAIGHT_SEGMENTS
        for index in range(TROUGH_STRAIGHT_SEGMENTS + 1)
    )
    return [-2.0 * BODY_X] + inner + [2.0 * BODY_X]


def _step_half_space(spec: dict, *, above: bool):
    """Block filling everything on one side of the trough's step divider.

    The shallow trough never reaches past its own floor, which is exactly where the
    divider's lean begins, so on the shallow side the divider and the plane z = `step_z`
    cut it identically and the block is a plain box. The deep side needs the divider
    itself, swept along x as planar triangles: the ruled band between the two floors is
    non-planar, and `compile_board`'s surface-area partition assumes exact tessellation.
    """
    z_high = spec["step_z"]
    if above:
        span = 4.0 * BODY_Z
        return Part.makeBox(
            4.0 * BODY_X,
            4.0 * BODY_Y,
            span,
            App.Vector(-2.0 * BODY_X, Y_FRONT - 2.0 * BODY_Y, z_high),
        )

    z_low = z_high - spec["step_run"]
    z_far = -2.0 * BODY_Z
    y_front, y_back = Y_FRONT - 2.0 * BODY_Y, Y_BACK + 2.0 * BODY_Y
    sections = []
    for x in _step_x_samples():
        shallow_y, deep_y = _step_levels(spec, x)
        sections.append(
            [
                App.Vector(x, y_front, z_high),
                App.Vector(x, shallow_y, z_high),
                App.Vector(x, deep_y, z_low),
                App.Vector(x, y_back, z_low),
                App.Vector(x, y_back, z_far),
                App.Vector(x, y_front, z_far),
            ]
        )

    # The section is star-shaped about its last corner, so fanning from there triangulates
    # it without leaving the block. Fanning from the first corner would cut across the
    # lean.
    def cap(section, *, flip: bool):
        apex = section[-1]
        fan = [
            (apex, section[index], section[index + 1])
            for index in range(len(section) - 2)
        ]
        return [(a, c, b) for a, b, c in fan] if flip else fan

    triangles = cap(sections[0], flip=True)
    for near, far in zip(sections, sections[1:]):
        for index in range(len(near)):
            following = (index + 1) % len(near)
            triangles.append((near[index], near[following], far[following]))
            triangles.append((near[index], far[following], far[index]))
    triangles += cap(sections[-1], flip=False)
    return _triangle_solid(triangles)


def _stepped_trough_cutter(spec: dict):
    """One stadium opening carrying two crowned floor levels, split at `step_z`.

    Both levels are the same trough at their own published depth, so they share the rim
    outline exactly and differ in how steep the wall's straight face has to be to reach
    the floor. Each is clipped to its own side of the step divider and the two are fused,
    which leaves the divider itself exposed between the levels: that band is the shelf
    edge you see inside the pocket. Clipping both (rather than fusing a whole shallow
    trough into a deep one, which the deep trough would simply swallow) also means the two
    solids meet only on the divider.
    """
    shallow = dict(spec, depth=spec["step_depth"])
    if spec["step_depth"] >= spec["depth"]:
        raise ValueError("the step's shallow level must be shallower than the trough")
    above = _trough_cutter(shallow).common(_step_half_space(spec, above=True))
    below = _trough_cutter(spec).common(_step_half_space(spec, above=False))
    solid = above.fuse(below)
    if solid.isNull() or solid.Volume <= 0.0:
        raise ValueError("stepped trough cutter is empty")
    return solid


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


def _wall_filter(spec: dict, *, above: bool, y_max: float, x_min: float, x_max: float):
    """Match trough faces on one side of the split line, no deeper than `y_max`.

    A stepped trough splits on its step divider, an unstepped one on its centre line. The
    side test is on the face's whole extent, not its centroid. Each x strip of the floor is
    one plane, so the boolean hands it back as a single face spanning the full apex width,
    and a centroid test would assign it by whichever side a rounding error fell on. A face
    that straddles the split line belongs to neither side and stays with the body, which is
    also where the reference's own node split leaves it.

    The riser is the exception: it is the rise to the deeper level's floor, so it goes to
    that level by lying on the divider rather than by its z extent. It has to be named
    explicitly because it does cross the split line — it spans `step_run` mm of z — and so
    do the slivers the divider's flat upper part leaves near the trough's ends, where the
    shallow level's floor has already tapered out.
    """
    split_z = spec.get("step_z", spec["z_center"])
    stepped = "step_z" in spec

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
        if stepped and all(
            abs(_step_offset(spec, v.X, v.Y, v.Z)) < 0.05 for v in face.Vertexes
        ):
            return not above
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
        _stepped_trough_cutter(upper),
        _trough_cutter(lower),
        _mono_cutter(),
    ]

    contact_predicates = [
        (
            # Below the step: the riser, the 14 mm floor and the wall back up to the rim.
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
            # Above the step: the upper wall and the 8 mm floor it lands on.
            "edge-8",
            _wall_filter(
                upper,
                above=True,
                y_max=Y_FRONT + upper["step_depth"],
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

    # The shelf between the upper trough's two levels is the whole point of the step, so
    # assert it survived the cut at the depth it is supposed to bridge.
    step_faces = [
        face
        for face in body_shape.Faces
        if all(abs(_step_offset(upper, v.X, v.Y, v.Z)) < 0.05 for v in face.Vertexes)
    ]
    if not step_faces:
        raise ValueError(f"upper trough has no step riser at z = {upper['step_z']}")
    riser = Part.makeCompound(step_faces)

    def slice_riser(x_center: float, width: float = 1.0):
        probe = Part.makeBox(
            width,
            4.0 * BODY_Y,
            4.0 * BODY_Z,
            App.Vector(
                x_center - 0.5 * width, Y_FRONT - 2.0 * BODY_Y, -2.0 * BODY_Z
            ),
        )
        return riser.common(probe).BoundBox

    # The riser pinches shut where the two levels meet the front face at the trough's
    # ends, so its bounding box spans the whole trough; measure the rise on a centre
    # slice instead, where both levels are at their published depth.
    step_box = slice_riser(0.0)
    step_rise, step_run = step_box.YLength, step_box.ZLength
    expected_rise = upper["depth"] - upper["step_depth"]
    if abs(step_rise - expected_rise) > 0.05:
        raise ValueError(
            f"step riser spans {step_rise:.3f} mm, expected {expected_rise:.3f} mm"
        )
    # A riser that lost its lean is a riser that cannot be seen in a front view.
    if abs(step_run - upper["step_run"]) > 0.05:
        raise ValueError(
            f"step riser leans back {step_run:.3f} mm of z, "
            f"expected {upper['step_run']:.3f} mm"
        )
    # And a riser whose edges wander in z is a divider that reads as a jagged polyline
    # rather than a shelf, which is what a *planar* riser does against a crowned floor.
    # Both edges have to be the same z at every station of the trough's straight run.
    z_high = upper["step_z"]
    z_low = z_high - upper["step_run"]
    for index in range(STEP_EDGE_PROBES + 1):
        probe_x = -TROUGH_HALF_LEN + 2.0 * TROUGH_HALF_LEN * index / STEP_EDGE_PROBES
        edges = slice_riser(probe_x)
        if abs(edges.ZMax - z_high) > 0.01 or abs(edges.ZMin - z_low) > 0.01:
            raise ValueError(
                f"step riser edges at x = {probe_x:.2f} span z "
                f"[{edges.ZMin:.3f}, {edges.ZMax:.3f}], expected [{z_low:.3f}, "
                f"{z_high:.3f}]; the divider is not a straight line in a front view"
            )

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
        levels = [spec["depth"]]
        if "step_depth" in spec:
            levels.insert(0, spec["step_depth"])
        for depth in levels:
            level = dict(spec, depth=depth)
            _, angle = _wall_stations(level, depth)
            print(
                f"  {name} trough floor: {depth:.2f} mm at x=0, "
                f"{_trough_depth(level, TROUGH_HALF_LEN):.2f} mm at x=+/-{TROUGH_HALF_LEN:.0f}"
                f"; wall face {math.degrees(angle):.1f} deg over"
                f" front roll r{WALL_FRONT_RADIUS:.1f} / back roll r{WALL_BACK_RADIUS:.1f}"
            )
        if "step_depth" in spec:
            print(
                f"  {name} trough step at z={spec['step_z']:.1f}: riser {step_rise:.2f} mm "
                f"rise leaning {step_run:.2f} mm of z over {len(step_faces)} face(s); "
                f"edges straight at z={z_high:.1f} / {z_low:.1f}"
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
