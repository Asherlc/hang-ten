"""One-off migration: author Hangboards/captain-fingerfood-pocket/*.FCStd.

Migration tool only — not a build input. The saved FCStd stands alone.

Acceptance bar (declared up front): sculpted display shell → measured
approximation. compare_exports is evidence, not a gate. Visually coherent
holds, published grip depths on edge-15/edge-20, node inventory, and envelope
match are the acceptance signals.

Measured facts (Git reference, native mm, +X right +Z up front -Y):

* Envelope 110 × 29 × 66 (x × y × z). Catalogue "110 × 66 × 29 mm" agrees;
  descriptor ±55/±33/±14.5 m matches the mesh.
* One continuous front cavity (rounded-rect trough with ~15 mm corners and a
  6.5 mm entry lip), not four separate pockets. Contacts partition that cavity
  plus the outer rim.
* Outer envelope corners ~10 mm (measured); perimeter roll ~3.5 mm.
* edge-15 / edge-20: opposing long lips with a **stepped floor** (15 mm on +Z,
  20 mm on −Z) per manufacturer “15 sowie 20 mm tiefe Griffleiste” and the
  reference floor (~y 0.7 / 5.3). Published depths 15 / 20 mm.
* pocket-end-wall-15-20: left short end of the same cavity (no fixed depth gate).
* jug-outer-rim: continuous top exterior band (U), full body depth — one contact,
  not a separate pinch.
* Cord through-holes at x=±22, z=0: ~3 mm radius n-gon, floor through back.

Construction: rolled rounded-rect envelope (~10 mm corners), one rounded-rect
cavity with a 6.5 mm entry lip and stepped 15/20 mm floors, through-hole n-gon
cord bores cut last, contacts as faces of the cut body.
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

PACKAGE = "captain-fingerfood-pocket"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
SCRATCH = Path(
    os.environ.get(
        "HANGTEN_CAD_SCRATCH",
        str(REPOSITORY / ".context" / "freecad-captain-fingerfood-pocket"),
    )
)

# Mesh envelope (native mm).
HALF_X = 55.0
HALF_Z = 33.0
Y_FRONT = -14.5
Y_BACK = 14.5
BODY_X = 110.0
BODY_Y = 29.0
BODY_Z = 66.0

CORNER_R = 11.0  # manufacturer photos: heavily rounded outer corners
CORNER_CENTER_X = HALF_X - CORNER_R
CORNER_CENTER_Z = HALF_Z - CORNER_R
CORNER_SEGMENTS = 10
EDGE_ROLL_R = 4.0  # soft outer roll-over visible in product shots
EDGE_ROLL_SEGMENTS = 8

# Cavity is a rounded rectangle (not a full-end stadium). Measured opening
# ≈ ±41.8 × ±22.8 with ~15 mm corners; manufacturer lip radius 6.5 mm.
OPEN_HALF_X = 41.8
OPEN_HALF_Z = 22.8
OPEN_CORNER_R = 15.0  # LINESGriffe / mesh: generous cavity corners
OPEN_SEGMENTS = 10
TROUGH_Z_CENTER = 0.0
DEPTH_15 = 15.0
DEPTH_20 = 20.0
FLOOR_Y = Y_FRONT + DEPTH_20
LIP_15_Y = Y_FRONT + DEPTH_15
LIP_R = 6.5  # published Griffkante radius
LIP_SEGMENTS = 8
FLOOR_INSET = 1.6  # slight shrink from opening to floor after the lip

# Cord through-holes at x=±22, z=0 (n-gon loft, no Cylinder). Visible on the
# cavity floor and the back face.
CORD_X = 22.0
CORD_R = 3.0
CORD_SIDES = 16

GRIP_DEPTH_MM = {"edge-15": DEPTH_15, "edge-20": DEPTH_20}

NODE_IDS = {
    "body": "body_skin_001",
    "edge-15": "edge_15_skin_001",
    "edge-20": "edge_20_skin_001",
    "jug-outer-rim": "jug_outer_rim_skin_001",
    "pocket-end-wall-15-20": "pocket_end_wall_15_20_skin_001",
}

MATERIAL_NAME = "lines_blue_charcoal"
MATERIAL_BASE_COLOR = "0.22,0.35,0.55"
MATERIAL_ROUGHNESS = 0.68
MATERIAL_METALLIC = 0.0

BODY_PRIM = "/root/body_main/body_skin_001"


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
        names = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".png") and "lines" in name.lower()
        ]
        if not names:
            names = [n for n in archive.namelist() if n.lower().endswith(".png")]
        if not names:
            raise ValueError("no reference texture found")
        # Prefer the lines body texture; fall back to first PNG.
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


def _loft_solid(sections):
    wires = [Part.makePolygon(list(points) + [points[0]]) for points in sections]
    return Part.makeLoft(wires, True, True)


def _rounded_rect_points(radius: float, y: float, segments: int = CORNER_SEGMENTS):
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
                App.Vector(
                    cx + radius * math.cos(angle),
                    y,
                    cz + radius * math.sin(angle),
                )
            )
    return points


def _opening_xz(half_x: float, half_z: float, corner_r: float, segments: int = OPEN_SEGMENTS):
    """CCW (x, z) rounded-rect cavity outline centred on the origin."""
    cx = half_x - corner_r
    cz = half_z - corner_r
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
                (ox + corner_r * math.cos(angle), oz + corner_r * math.sin(angle))
            )
    return points


def _opening_points(half_x: float, half_z: float, corner_r: float, y: float):
    return [App.Vector(x, y, z) for x, z in _opening_xz(half_x, half_z, corner_r)]


def _body_solid():
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


def _lip_stations(floor_depth: float):
    """(depth_from_front, radial_inset) — 6.5 mm entry lip, then floors.

    A station lands on DEPTH_15 so the upper (+Z) contact can own a published
    15 mm wall band before the lower half continues to 20 mm.
    """
    stations = [(-0.05, 0.0)]
    for index in range(1, LIP_SEGMENTS + 1):
        angle = 0.5 * math.pi * index / LIP_SEGMENTS
        depth = LIP_R * (1.0 - math.cos(angle))
        inset = LIP_R * (1.0 - math.sin(angle))
        stations.append((depth, inset))
    inset_15 = LIP_R * 0.12 + FLOOR_INSET * 0.7
    inset_20 = LIP_R * 0.12 + FLOOR_INSET
    if floor_depth > DEPTH_15 + 0.5:
        # Keep stations strictly deepening.
        if stations[-1][0] < DEPTH_15 - 0.2:
            stations.append((DEPTH_15, inset_15))
        stations.append((floor_depth, inset_20))
    elif abs(floor_depth - stations[-1][0]) > 0.2:
        stations.append((floor_depth, inset_15))
    return stations


def _station_ring(depth: float, inset: float):
    """Opening ring at Y_FRONT + depth, inset from the measured opening."""
    return _opening_points(
        OPEN_HALF_X - inset,
        OPEN_HALF_Z - inset,
        max(OPEN_CORNER_R - inset, 2.0),
        Y_FRONT + depth,
    )


def _cap_fan(ring, flip: bool):
    """Planar triangle fan closing a ring (flat floor)."""
    center = App.Vector(0.0, ring[0].y, TROUGH_Z_CENTER)
    triangles = []
    count = len(ring)
    for index in range(count):
        a, b = ring[index], ring[(index + 1) % count]
        triangles.append((center, a, b) if not flip else (center, b, a))
    return triangles


def _triangle_solid(triangles):
    volume = 0.0
    for a, b, c in triangles:
        volume += (
            a.x * (b.y * c.z - b.z * c.y)
            - a.y * (b.x * c.z - b.z * c.x)
            + a.z * (b.x * c.y - b.y * c.x)
        )
    if volume < 0.0:
        triangles = [(a, c, b) for a, b, c in triangles]
    faces = [Part.Face(Part.makePolygon([a, b, c, a])) for a, b, c in triangles]
    shell = Part.makeShell(faces)
    if not shell.isClosed():
        raise ValueError("triangulated cutter shell is not closed")
    solid = Part.makeSolid(shell)
    if solid.Volume <= 0.0:
        raise ValueError(f"triangulated cutter volume {solid.Volume}")
    return solid


def _half_opening_points(half_x: float, half_z: float, corner_r: float, y: float, *, upper: bool):
    """Closed half rounded-rect at depth y, diameter along z=0."""
    full = _opening_xz(half_x, half_z, corner_r)
    kept = [(x, z) for x, z in full if (z >= -1e-9 if upper else z <= 1e-9)]
    left = (-half_x, 0.0)
    right = (half_x, 0.0)
    if upper:
        pts = [right] + [(x, z) for x, z in kept if abs(z) > 1e-9] + [left]
    else:
        pts = [left] + [(x, z) for x, z in kept if abs(z) > 1e-9] + [right]
    cleaned = [pts[0]]
    for point in pts[1:]:
        if math.hypot(point[0] - cleaned[-1][0], point[1] - cleaned[-1][1]) > 1e-6:
            cleaned.append(point)
    return [App.Vector(x, y, z) for x, z in cleaned]


def _upper_floor_filler():
    """Fill the +Z half between 15 mm and 20 mm so that half reads as a 15 mm edge."""
    inset = LIP_R * 0.15 + FLOOR_INSET
    y0 = Y_FRONT + DEPTH_15
    y1 = Y_FRONT + DEPTH_20 + 0.05
    hx = OPEN_HALF_X - inset
    hz = OPEN_HALF_Z - inset
    cr = max(OPEN_CORNER_R - inset, 2.0)
    sections = [
        _half_opening_points(hx, hz, cr, y0, upper=True),
        _half_opening_points(hx, hz, cr, y1, upper=True),
    ]
    return _loft_solid(sections)


def _trough_cutter():
    """Rounded-rect cavity to 20 mm with a 6.5 mm entry lip (triangle soup)."""
    stations = _lip_stations(DEPTH_20)
    rings = [_station_ring(depth, inset) for depth, inset in stations]
    triangles = _cap_fan(rings[0], flip=True)
    count = len(rings[0])
    for near, far in zip(rings, rings[1:]):
        for index in range(count):
            following = (index + 1) % count
            triangles.append((near[index], near[following], far[following]))
            triangles.append((near[index], far[following], far[index]))
    triangles += _cap_fan(rings[-1], flip=False)
    return _triangle_solid(triangles)


def _cord_mouth(sign: float):
    """Through-hole n-gon from the cavity floors through the back face.

    Opens on both the 15 mm and 20 mm floor levels (z≈0 sits on the step), so
    the start plane is slightly proud of the shallower floor.
    """
    cx = sign * CORD_X
    y0 = LIP_15_Y - 0.8
    y1 = Y_BACK + 0.8
    sections = []
    for y in (y0, y1):
        sections.append(
            [
                App.Vector(
                    cx + CORD_R * math.cos(2.0 * math.pi * i / CORD_SIDES),
                    y,
                    CORD_R * math.sin(2.0 * math.pi * i / CORD_SIDES),
                )
                for i in range(CORD_SIDES)
            ]
        )
    return _loft_solid(sections)


def _in_trough(x: float, z: float, slack: float = 0.5) -> bool:
    """True if (x, z) lies inside the opening rounded-rect (plus slack)."""
    ax, az = abs(x), abs(z)
    hx, hz, r = OPEN_HALF_X + slack, OPEN_HALF_Z + slack, OPEN_CORNER_R
    if ax <= hx - r and az <= hz:
        return True
    if az <= hz - r and ax <= hx:
        return True
    cx, cz = hx - r, hz - r
    if ax >= cx and az >= cz:
        return math.hypot(ax - cx, az - cz) <= r + slack
    return False


def _is_front_plane(face) -> bool:
    box = face.BoundBox
    return box.YLength < 0.02 and abs(box.YMin - Y_FRONT) < 0.08


def _shell_from_body_faces(body_shape, predicate):
    faces = [face for face in body_shape.Faces if predicate(face)]
    if not faces:
        raise ValueError("no body faces matched the contact predicate")
    if len(faces) == 1:
        return faces[0]
    return Part.makeCompound(faces)


def _edge_15_filter(face) -> bool:
    """Upper (+Z) lip and 15 mm floor — manufacturer 15 mm Griffleiste."""
    box = face.BoundBox
    if _is_front_plane(face) or box.YLength < 0.02:
        return False
    if box.YMin < Y_FRONT - 0.08 or box.YMax > LIP_15_Y + 0.2:
        return False
    center = face.CenterOfMass
    if not _in_trough(center.x, center.z):
        return False
    if center.x < -OPEN_HALF_X + OPEN_CORNER_R:
        return False
    if box.YLength < 0.05 and abs(box.YMin - LIP_15_Y) < 0.25:
        return box.ZMin >= TROUGH_Z_CENTER - 0.05
    return box.ZMin >= TROUGH_Z_CENTER - 0.05


def _edge_20_filter(face) -> bool:
    """Lower (−Z) lip and 20 mm floor — manufacturer 20 mm Griffleiste."""
    box = face.BoundBox
    if _is_front_plane(face) or box.YLength < 0.02:
        return False
    if box.YMin < Y_FRONT - 0.08 or box.YMax > FLOOR_Y + 0.2:
        return False
    center = face.CenterOfMass
    if not _in_trough(center.x, center.z):
        return False
    if center.x < -OPEN_HALF_X + OPEN_CORNER_R:
        return False
    if box.YLength < 0.05 and abs(box.YMin - FLOOR_Y) < 0.25:
        return box.ZMax <= TROUGH_Z_CENTER + 0.05
    return box.ZMax <= TROUGH_Z_CENTER + 0.05


def _pocket_end_filter(face) -> bool:
    """Left short end of the cavity (whole-face extent on −X)."""
    box = face.BoundBox
    if _is_front_plane(face) or box.YLength < 0.02:
        return False
    if box.YMin < Y_FRONT - 0.08 or box.YMax > FLOOR_Y + 0.2:
        return False
    center = face.CenterOfMass
    if not _in_trough(center.x, center.z, slack=0.8):
        return False
    return box.XMax <= -OPEN_HALF_X + OPEN_CORNER_R + 0.5


def _jug_filter(face) -> bool:
    """Continuous top exterior band (source-backed U), not the cavity."""
    box = face.BoundBox
    if box.ZMax < HALF_Z - 6.5:
        return False
    if box.ZMin < HALF_Z - 8.0 and abs(box.ZMax - HALF_Z) > 0.5:
        # Tall side face that only grazes the top — skip unless it's the top rim.
        if box.ZLength > 8.0:
            return False
    center = face.CenterOfMass
    if _in_trough(center.x, center.z, slack=0.2):
        return False
    # Prefer the rolled top lip: high Z, not the flat back.
    return center.z >= HALF_Z - 5.5 or (box.ZMin >= HALF_Z - 5.5)


def main() -> int:
    board = json.loads(BOARD_JSON.read_text())
    reference, reference_digest = load_reference(PACKAGE, "primary.usdz", SCRATCH / "ref")
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
    document.HangTenTessellationDeflection = 0.05

    brick = document.addObject("Part::Feature", "OuterEnvelope")
    brick.Shape = _body_solid()
    document.recompute()

    # Deep cavity first, then raise the +Z floor to 15 mm, then punch cords
    # through the finished body so the filler cannot plug the holes.
    trough_obj = document.addObject("Part::Feature", "TroughCutter")
    trough_obj.Shape = _trough_cutter()
    body_cut = document.addObject("Part::Cut", "BodyCut")
    body_cut.Base = brick
    body_cut.Tool = trough_obj
    document.recompute()
    if body_cut.Shape.isNull() or body_cut.Shape.Volume < 1.0:
        raise ValueError("boolean cut failed")

    filler_obj = document.addObject("Part::Feature", "UpperFloorFiller")
    filler_obj.Shape = _upper_floor_filler()
    body_fused = document.addObject("Part::Fuse", "BodyWithStep")
    body_fused.Base = body_cut
    body_fused.Tool = filler_obj
    document.recompute()
    if body_fused.Shape.isNull() or body_fused.Shape.Volume < 1.0:
        raise ValueError("upper floor filler fuse failed")

    cord_fused = _cord_mouth(1.0).fuse(_cord_mouth(-1.0))
    cord_obj = document.addObject("Part::Feature", "CordCutters")
    cord_obj.Shape = cord_fused
    body_holed = document.addObject("Part::Cut", "BodyCordCut")
    body_holed.Base = body_fused
    body_holed.Tool = cord_obj
    document.recompute()
    if body_holed.Shape.isNull() or body_holed.Shape.Volume < 1.0:
        raise ValueError("cord through-hole cut failed")

    body = document.addObject("Part::Feature", "BodySolid")
    body.Shape = body_holed.Shape
    body.addProperty("App::PropertyString", "NodeID", "HangTen")
    body.addProperty("App::PropertyString", "NodeRole", "HangTen")
    body.NodeID = NODE_IDS["body"]
    body.NodeRole = "body"
    _apply_material(body, texture_source)
    document.recompute()
    body_shape = body.Shape

    contact_predicates = [
        ("edge-15", _edge_15_filter),
        ("edge-20", _edge_20_filter),
        ("pocket-end-wall-15-20", _pocket_end_filter),
        ("jug-outer-rim", _jug_filter),
    ]
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
        box = feature.Shape.BoundBox
        feature.addProperty("App::PropertyString", "HangTenHoldOutline", "HangTen")
        feature.HangTenHoldOutline = json.dumps(
            [
                [round(box.XMin, 4), round(box.ZMin, 4)],
                [round(box.XMax, 4), round(box.ZMin, 4)],
                [round(box.XMax, 4), round(box.ZMax, 4)],
                [round(box.XMin, 4), round(box.ZMax, 4)],
            ]
        )
        _apply_material(feature, None)
        regions[contact_id] = {
            "faces": len(getattr(feature.Shape, "Faces", [feature.Shape])),
            "x": (round(box.XMin, 2), round(box.XMax, 2)),
            "z": (round(box.ZMin, 2), round(box.ZMax, 2)),
            "depth": round(box.YLength, 3),
        }

    document.recompute()
    stale = [
        obj.Name
        for obj in document.Objects
        if "Invalid" in obj.State or "Error" in obj.State
    ]
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
    print(f"reference sha256 {reference_digest}")
    print(f"texture sha256 {texture_digest}")
    print(f"reference envelope mm: {measured}")
    print(f"body faces: {len(body_shape.Faces)}  volume {body_shape.Volume:.0f} mm^3")
    print(
        "acceptance: sculpted measured-approximation; "
        f"edge floors authored at published {GRIP_DEPTH_MM} "
        "(ref node Y extents were ~15.3 / 19.8 mm)"
    )
    for contact_id, info in regions.items():
        published = GRIP_DEPTH_MM.get(contact_id, "n/a")
        print(
            f"  {contact_id:24s} faces={info['faces']:3d} "
            f"x={info['x']} z={info['z']} depth={info['depth']} (published {published})"
        )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
