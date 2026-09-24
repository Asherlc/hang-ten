"""One-off migration: author Hangboards/lattice-mxedge-lift-small/lattice-mxedge-lift-small.FCStd.

Migration tool only — not a build input.

Provenance:
* Overall envelope 168 x 34 x 98 mm and grip depths 18 / 14 / 8 / 25 mm from board.json.
* Hold openings and outer rounded-rectangle envelope measured from the Git-resolved
  reference USDZ (pre-migration commit via reference.load_reference).
* Display material texture embedded from the same reference package.
* Measured approximation of a sculpted display mesh — not manufacturing geometry.
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
CORNER_R = 12.0
# Planar corner facets (true OCCT fillets leave a tessellation-vs-Area gap at compile).
CORNER_SEGMENTS = 24
HALF_X = BODY_X / 2.0
HALF_Z = BODY_Z / 2.0

GRIP_DEPTH_MM = {
    "edge-18": 18.0,
    "edge-14": 14.0,
    "edge-8": 8.0,
    "mono-25": 25.0,
}

# Opening rectangles measured on the reference front lip (native mm, x/z).
# Corner radii from reference end curvature (stadium-ish for edge-14/8; tighter for edge-18).
# edge-14 / edge-8 are inset 0.3 mm from the shared z=23 line so the cuts stay separate.
OPENINGS = {
    "edge-18": (-57.0, 39.0, -34.8, -20.0, 5.0),
    "edge-14": (-57.0, 57.0, 7.5, 22.7, 7.5),
    "edge-8": (-57.0, 57.0, 23.3, 37.0, 7.0),
}

# Front-entry lip chamfer measured ~2.3 mm on the mono; 3 mm reads for edge openings.
LIP_FILLET_R = 3.0
# Arc corners approximated with this many planar segments (compile partition stays planar).
OPENING_CORNER_SEGMENTS = 12

MONO_CENTER_X = 50.4
MONO_CENTER_Z = -20.0
MONO_RADIUS = 12.4
# Planar n-gon only — a true Cylinder fails compile_board partition (distToShape 1e-4).
MONO_SIDES = 64

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


def _outer_brick_solid():
    """Rounded-rectangle brick with planar corner facets (baked before pocket cuts)."""
    face = _rounded_rect_face(-HALF_X, HALF_X, -HALF_Z, HALF_Z, CORNER_R, Y_FRONT, CORNER_SEGMENTS)
    return face.extrude(App.Vector(0.0, BODY_Y, 0.0))


def _pocket_face_filter(
    x0: float,
    x1: float,
    z0: float,
    z1: float,
    depth: float,
    *,
    expand_x0: bool = True,
    expand_x1: bool = True,
    expand_z0: bool = True,
    expand_z1: bool = True,
):
    """Match pocket walls, floor, stadium ends, and front lip faces by CoM."""
    y1 = Y_FRONT + depth
    x0_lip = x0 - LIP_FILLET_R - 0.25 if expand_x0 else x0 - 0.25
    x1_lip = x1 + LIP_FILLET_R + 0.25 if expand_x1 else x1 + 0.25
    z0_lip = z0 - LIP_FILLET_R - 0.25 if expand_z0 else z0 - 0.25
    z1_lip = z1 + LIP_FILLET_R + 0.25 if expand_z1 else z1 + 0.25

    def matches(face) -> bool:
        center = face.CenterOfMass
        if center.y < Y_FRONT - 0.05 or center.y > y1 + 0.05:
            return False
        # Never claim the mono bore from an edge pocket (openings nearly touch in X).
        radial = math.hypot(center.x - MONO_CENTER_X, center.z - MONO_CENTER_Z)
        if radial <= MONO_RADIUS + LIP_FILLET_R + 0.75:
            return False
        in_core = x0 - 0.25 <= center.x <= x1 + 0.25 and z0 - 0.25 <= center.z <= z1 + 0.25
        in_lip = (
            center.y <= Y_FRONT + LIP_FILLET_R + 0.75
            and x0_lip <= center.x <= x1_lip
            and z0_lip <= center.z <= z1_lip
        )
        if not (in_core or in_lip):
            return False
        if isinstance(face.Surface, Part.Plane):
            normal = face.Surface.Axis
            if abs(normal.y + 1.0) < 0.05 and abs(center.y - Y_FRONT) < 0.2:
                return False
        return True

    return matches


def _mono_face_filter(cx: float, cz: float, radius: float):
    """Planar n-gon walls + floor + lip; no true Cylinder as sole contact surface."""

    def matches(face) -> bool:
        center = face.CenterOfMass
        radial = math.hypot(center.x - cx, center.z - cz)
        if not (
            Y_FRONT - 0.05 <= center.y <= Y_FRONT + GRIP_DEPTH_MM["mono-25"] + 0.05
            and radius * 0.55 <= radial <= radius + LIP_FILLET_R + 0.5
        ):
            return False
        if isinstance(face.Surface, Part.Plane):
            normal = face.Surface.Axis
            if abs(normal.y + 1.0) < 0.05 and abs(center.y - Y_FRONT) < 0.2:
                return False
        return True

    return matches


def _mono_prism_solid(cx: float, cz: float, radius: float, depth: float, sides: int, y0: float = Y_FRONT):
    angles = [2.0 * math.pi * index / sides for index in range(sides)]
    points = [
        App.Vector(cx + radius * math.cos(angle), y0, cz + radius * math.sin(angle))
        for angle in angles
    ]
    wire = Part.makePolygon(points + [points[0]])
    return Part.Face(wire).extrude(App.Vector(0.0, depth, 0.0))


def _rounded_rect_points(
    x0: float,
    x1: float,
    z0: float,
    z1: float,
    corner_r: float,
    y: float,
    segments: int,
):
    """CCW XZ rounded-rect vertices (planar) at plane y = const."""
    width = x1 - x0
    height = z1 - z0
    radius = min(corner_r, width / 2.0 - 0.05, height / 2.0 - 0.05)
    if radius < 0.05:
        return [
            App.Vector(x0, y, z0),
            App.Vector(x1, y, z0),
            App.Vector(x1, y, z1),
            App.Vector(x0, y, z1),
        ]
    cx0, cx1 = x0 + radius, x1 - radius
    cz0, cz1 = z0 + radius, z1 - radius
    points: list = []
    # Bottom edge, then bottom-right corner, right, top-right, top, top-left, left, bottom-left.
    points.append(App.Vector(cx0, y, z0))
    points.append(App.Vector(cx1, y, z0))
    for index in range(1, segments + 1):
        angle = -math.pi / 2.0 + (math.pi / 2.0) * (index / segments)
        points.append(App.Vector(cx1 + radius * math.cos(angle), y, cz0 + radius * math.sin(angle)))
    points.append(App.Vector(x1, y, cz1))
    for index in range(1, segments + 1):
        angle = 0.0 + (math.pi / 2.0) * (index / segments)
        points.append(App.Vector(cx1 + radius * math.cos(angle), y, cz1 + radius * math.sin(angle)))
    points.append(App.Vector(cx0, y, z1))
    for index in range(1, segments + 1):
        angle = math.pi / 2.0 + (math.pi / 2.0) * (index / segments)
        points.append(App.Vector(cx0 + radius * math.cos(angle), y, cz1 + radius * math.sin(angle)))
    points.append(App.Vector(x0, y, cz0))
    # Final corner: omit the last sample — it coincides with points[0].
    for index in range(1, segments):
        angle = math.pi + (math.pi / 2.0) * (index / segments)
        points.append(App.Vector(cx0 + radius * math.cos(angle), y, cz0 + radius * math.sin(angle)))
    return points


def _rounded_rect_face(
    x0: float,
    x1: float,
    z0: float,
    z1: float,
    corner_r: float,
    y: float,
    segments: int = OPENING_CORNER_SEGMENTS,
):
    points = _rounded_rect_points(x0, x1, z0, z1, corner_r, y, segments)
    wire = Part.makePolygon(points + [points[0]])
    return Part.Face(wire)


def _rounded_rect_wire(
    x0: float,
    x1: float,
    z0: float,
    z1: float,
    corner_r: float,
    y: float,
    segments: int = OPENING_CORNER_SEGMENTS,
):
    return _rounded_rect_face(x0, x1, z0, z1, corner_r, y, segments).OuterWire


def _shell_from_body_faces(body_shape, predicate):
    faces = [face for face in body_shape.Faces if predicate(face)]
    if not faces:
        raise ValueError("no body faces matched the contact predicate")
    if len(faces) == 1:
        return faces[0]
    return Part.makeCompound(faces)


def _pocket_cutter(x0: float, x1: float, z0: float, z1: float, corner_r: float, depth: float):
    face = _rounded_rect_face(x0, x1, z0, z1, corner_r, Y_FRONT - 0.01)
    return face.extrude(App.Vector(0.0, depth + 0.02, 0.0))


def _pocket_lip_cutter(
    x0: float,
    x1: float,
    z0: float,
    z1: float,
    corner_r: float,
    lip_r: float,
    *,
    expand_x0: bool = True,
    expand_x1: bool = True,
    expand_z0: bool = True,
    expand_z1: bool = True,
):
    """Lofted entry chamfer between congruent polygonal openings (planar ruled faces)."""
    x0_outer = x0 - lip_r if expand_x0 else x0
    x1_outer = x1 + lip_r if expand_x1 else x1
    z0_outer = z0 - lip_r if expand_z0 else z0
    z1_outer = z1 + lip_r if expand_z1 else z1
    outer_height = z1_outer - z0_outer
    outer_width = x1_outer - x0_outer
    outer_corner = min(corner_r + lip_r, outer_width / 2.0 - 0.05, outer_height / 2.0 - 0.05)
    outer = _rounded_rect_wire(
        x0_outer,
        x1_outer,
        z0_outer,
        z1_outer,
        outer_corner,
        Y_FRONT - 0.01,
    )
    inner = _rounded_rect_wire(x0, x1, z0, z1, corner_r, Y_FRONT + lip_r)
    return Part.makeLoft([outer, inner], solid=True, ruled=True)


def _mono_cutter(cx: float, cz: float, radius: float, depth: float):
    return _mono_prism_solid(cx, cz, radius + 0.02, depth + 0.02, MONO_SIDES)


def _mono_lip_cutter(cx: float, cz: float, radius: float, lip_r: float):
    """Faceted entry chamfer: loft expanded n-gon → bore n-gon (no Cylinder/torus)."""

    def ngon_wire(rad: float, y: float):
        angles = [2.0 * math.pi * index / MONO_SIDES for index in range(MONO_SIDES)]
        points = [
            App.Vector(cx + rad * math.cos(angle), y, cz + rad * math.sin(angle))
            for angle in angles
        ]
        return Part.makePolygon(points + [points[0]])

    return Part.makeLoft(
        [ngon_wire(radius + lip_r, Y_FRONT - 0.01), ngon_wire(radius, Y_FRONT + lip_r)],
        solid=True,
        ruled=True,
    )


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

    brick = document.addObject("Part::Feature", "OuterBrick")
    # Rounded envelope is authored into the brick solid (not a post-cut Shape assign on Part::Cut).
    brick.Shape = _outer_brick_solid()
    document.recompute()
    brick_box = brick.Shape.BoundBox
    expected = (
        -HALF_X,
        Y_FRONT,
        -HALF_Z,
        HALF_X,
        Y_FRONT + BODY_Y,
        HALF_Z,
    )
    actual = (
        brick_box.XMin,
        brick_box.YMin,
        brick_box.ZMin,
        brick_box.XMax,
        brick_box.YMax,
        brick_box.ZMax,
    )
    if any(abs(a - b) > 1.0 for a, b in zip(actual, expected)):
        raise ValueError(f"brick bbox {actual} != expected {expected}")

    cutters = []
    contact_predicates = []
    # Asymmetric lip expansion avoids eating the edge-14/edge-8 divider and the mono.
    # Flags: expand_x0, expand_x1, expand_z0, expand_z1
    lip_expand = {
        "edge-18": (True, False, True, True),
        "edge-14": (True, True, True, False),
        "edge-8": (True, True, False, True),
    }
    for contact_id, (x0, x1, z0, z1, corner_r) in OPENINGS.items():
        depth = GRIP_DEPTH_MM[contact_id]
        expand_x0, expand_x1, expand_z0, expand_z1 = lip_expand[contact_id]
        cutters.append(_pocket_cutter(x0, x1, z0, z1, corner_r, depth))
        cutters.append(
            _pocket_lip_cutter(
                x0,
                x1,
                z0,
                z1,
                corner_r,
                LIP_FILLET_R,
                expand_x0=expand_x0,
                expand_x1=expand_x1,
                expand_z0=expand_z0,
                expand_z1=expand_z1,
            )
        )
        contact_predicates.append(
            (
                contact_id,
                _pocket_face_filter(
                    x0,
                    x1,
                    z0,
                    z1,
                    depth,
                    expand_x0=expand_x0,
                    expand_x1=expand_x1,
                    expand_z0=expand_z0,
                    expand_z1=expand_z1,
                ),
            )
        )

    mono_depth = GRIP_DEPTH_MM["mono-25"]
    cutters.append(_mono_cutter(MONO_CENTER_X, MONO_CENTER_Z, MONO_RADIUS, mono_depth))
    cutters.append(_mono_lip_cutter(MONO_CENTER_X, MONO_CENTER_Z, MONO_RADIUS, LIP_FILLET_R))
    contact_predicates.append(
        ("mono-25", _mono_face_filter(MONO_CENTER_X, MONO_CENTER_Z, MONO_RADIUS))
    )

    fused_shape = cutters[0]
    for cutter in cutters[1:]:
        fused_shape = fused_shape.fuse(cutter)
    cutter_obj = document.addObject("Part::Feature", "PocketCutters")
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
        raise ValueError("filleted body failed to produce a solid")

    depth_spans = {}
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
        depth_spans[contact_id] = round(feature.Shape.BoundBox.YLength, 3)

    document.recompute()
    stale = [obj.Name for obj in document.Objects if "Invalid" in obj.State or "Error" in obj.State]
    if stale:
        raise ValueError(f"document failed recompute: {stale}")

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    document.saveAs(str(DESTINATION))

    print(f"authored {DESTINATION} ({DESTINATION.stat().st_size} bytes)")
    print(f"reference envelope mm: {measured}")
    print(f"authored contact Y spans mm: {depth_spans} (published {GRIP_DEPTH_MM})")
    print(f"outer corner R={CORNER_R} mm ({CORNER_SEGMENTS} segs), lip R={LIP_FILLET_R} mm, mono sides={MONO_SIDES}")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
