"""One-off migration: author Hangboards/lattice-mxedge-lift-small/lattice-mxedge-lift-small.FCStd.

Migration tool only — not a build input.

Provenance:
* Overall envelope 168 x 34 x 98 mm and grip depths 18 / 14 / 8 / 25 mm from board.json.
* Front geometry measured from the Git-resolved reference USDZ (pre-migration commit via
  reference.load_reference), by depth-mapping its front surface on a 0.5 mm grid and
  sectioning it at x = 10 mm:
  - the front carries **two stadium troughs**, not four flush pockets: arc centres at
    x = +/-48 mm, end radius 14 mm (half the opening height), openings z [8.5, 36.5]
    and z [-34.5, -6.5], widest at x = +/-62 mm;
  - each trough wall is an ogee tangent to the front face at the rim and to the trough
    floor. A smoothstep in the wall inset tracks the measured wall to ~0.3 mm, so the
    wall is authored as a loft of uniformly offset stadium sections;
  - the walls are what the reference renders as one dark band (upper wall, facing down)
    and one bright band (lower wall, facing up) per trough;
  - measured trough depths are 12.5 mm (upper) and 16.5 mm (lower). This model uses the
    published 14 mm / 18 mm instead, so each exported region's depth equals the depth
    board.json publishes. Stated deviation: floors 1.5 mm deeper than measured;
  - the mono is a bore inside the lower trough's right end: measured rim r 10.7 mm at
    (x 48.4, z -20.3), near-cylindrical to a floor of r 9.2 mm. The floor is placed at
    the published 25 mm (measured 27.2 mm);
  - front and back perimeter roll r 4 mm (the measured front face is flat only to
    |z| <= 45 mm), outer corner radius 12 mm.
* Display material texture embedded from the same reference package.
* Measured approximation of a sculpted display mesh — not manufacturing geometry.

Region partition. `compile_board` requires each region's extent along the depth axis to
equal the published grip depth, and the reference's own nodes do not satisfy that (its
edge-8 node spans the full 12.5 mm trough). Each authored region is therefore the run of
trough-wall faces whose depth extent *is* the published depth, which for edge-8 is the
front 8 mm of the upper trough's upper wall — the lip actually gripped:

    edge-14  upper trough, lower wall, full depth        y [-17, -3]   span 14
    edge-8   upper trough, upper wall, front 8 mm        y [-17, -9]   span  8
    edge-18  lower trough, lower wall, full depth        y [-17, +1]   span 18
    mono-25  lower trough right end + bore incl. floor   y [-17, +8]   span 25
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

# Outer envelope: 12 mm XZ corners plus a 4 mm roll into the front and back faces.
# Planar facets throughout — an OCCT fillet leaves a tessellation-vs-Area gap at compile.
CORNER_R = 12.0
CORNER_SEGMENTS = 8
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

# Measured stadium openings: arc centres at x = +/-48, end radius = half the opening height.
TROUGH_HALF_LEN = 48.0
TROUGH_RADIUS = 14.0
TROUGH_SEGMENTS = 10  # planar facets per stadium end arc
# Depth is the published grip depth of the trough's lower wall (see module docstring).
TROUGHS = {
    "upper": {"z_center": 22.5, "depth": GRIP_DEPTH_MM["edge-14"], "apex_inset": 11.5},
    "lower": {"z_center": -20.5, "depth": GRIP_DEPTH_MM["edge-18"], "apex_inset": 11.0},
}
# Depth fractions of the lofted wall stations; the inset follows the inverse smoothstep.
WALL_FRACTIONS = (0.0, 0.03, 0.08, 0.15, 0.25, 0.37, 0.5, 0.62, 0.73, 0.83, 0.91, 0.97, 1.0)
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
MONO_SIDES = 32

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


def _smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _inverse_smoothstep(fraction: float) -> float:
    """Wall inset parameter for a depth fraction (exact inverse of `_smoothstep`)."""
    clamped = min(max(fraction, 0.0), 1.0)
    return 0.5 - math.sin(math.asin(1.0 - 2.0 * clamped) / 3.0)


def _loft_solid(sections):
    """Ruled loft through polygonal sections, capped.

    Every section shares its arc centres with the others and differs only in radius, so
    each lateral face is a planar trapezoid and tessellates exactly.
    """
    wires = [Part.makePolygon(list(points) + [points[0]]) for points in sections]
    return Part.makeLoft(wires, True, True)


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


def _stadium_points(z_center: float, radius: float, y: float, segments: int = TROUGH_SEGMENTS):
    """CCW XZ stadium outline; arc centres stay at x = +/-TROUGH_HALF_LEN."""
    points = []
    for cx, start, end in (
        (TROUGH_HALF_LEN, -math.pi / 2.0, math.pi / 2.0),
        (-TROUGH_HALF_LEN, math.pi / 2.0, 1.5 * math.pi),
    ):
        for index in range(segments + 1):
            angle = start + (end - start) * index / segments
            points.append(
                App.Vector(cx + radius * math.cos(angle), y, z_center + radius * math.sin(angle))
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
    """Envelope with 12 mm XZ corners and a 4 mm roll into the front and back faces."""
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


def _wall_stations(spec: dict, extra_fractions=()):
    """(y, inset) stations of one trough wall, rim first."""
    fractions = sorted(set(WALL_FRACTIONS) | set(extra_fractions))
    return [
        (Y_FRONT + spec["depth"] * fraction, spec["apex_inset"] * _inverse_smoothstep(fraction))
        for fraction in fractions
    ]


def _trough_cutter(spec: dict, extra_fractions=()):
    stations = _wall_stations(spec, extra_fractions)
    sections = [_stadium_points(spec["z_center"], TROUGH_RADIUS, Y_FRONT - PROUD_MM)]
    sections.extend(
        _stadium_points(spec["z_center"], TROUGH_RADIUS - inset, y) for y, inset in stations
    )
    return _loft_solid(sections)


def _mono_cutter():
    """Bore inside the lower trough's right end; no Cylinder, planar n-gon only."""
    apex_y = Y_FRONT + TROUGHS["lower"]["depth"]
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
    """Match trough-wall faces on one side of the apex, no deeper than `y_max`."""

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
        return (center.z > spec["z_center"]) if above else (center.z < spec["z_center"])

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
    # Station exactly at the published 8 mm so the edge-8 region's depth extent is 8.000.
    edge_8_fraction = GRIP_DEPTH_MM["edge-8"] / upper["depth"]
    cutters = [
        _trough_cutter(upper, extra_fractions=(edge_8_fraction,)),
        _trough_cutter(lower),
        _mono_cutter(),
    ]

    contact_predicates = [
        (
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
    document.saveAs(str(DESTINATION))

    print(f"authored {DESTINATION} ({DESTINATION.stat().st_size} bytes)")
    print(f"reference envelope mm: {measured}")
    print(f"body faces: {len(body_shape.Faces)}  volume {body_shape.Volume:.0f} mm^3")
    for contact_id, info in regions.items():
        print(
            f"  {contact_id:8s} faces={info['faces']:3d} x={info['x']} z={info['z']} "
            f"depth={info['depth']} (published {GRIP_DEPTH_MM[contact_id]})"
        )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
