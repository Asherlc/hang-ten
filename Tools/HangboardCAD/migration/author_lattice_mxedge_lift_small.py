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
HALF_X = BODY_X / 2.0
HALF_Z = BODY_Z / 2.0

GRIP_DEPTH_MM = {
    "edge-18": 18.0,
    "edge-14": 14.0,
    "edge-8": 8.0,
    "mono-25": 25.0,
}

# Opening rectangles measured on the reference front lip (native mm, x/z).
OPENINGS = {
    "edge-18": (-57.0, 39.0, -34.8, -20.0),
    "edge-14": (-57.0, 57.0, 7.5, 23.0),
    "edge-8": (-57.0, 57.0, 23.0, 37.0),
}

MONO_CENTER_X = 50.4
MONO_CENTER_Z = -20.0
MONO_RADIUS = 12.4
MONO_SIDES = 16

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
    """Outer brick envelope; corner radius is a display simplification applied after cut."""
    return Part.makeBox(BODY_X, BODY_Y, BODY_Z, App.Vector(-HALF_X, Y_FRONT, -HALF_Z))


def _pocket_face_filter(x0: float, x1: float, z0: float, z1: float, depth: float):
    y1 = Y_FRONT + depth
    margin = 0.05

    def matches(face) -> bool:
        center = face.CenterOfMass
        if not (x0 - margin <= center.x <= x1 + margin and z0 - margin <= center.z <= z1 + margin):
            return False
        if center.y < Y_FRONT - margin or center.y > y1 + margin:
            return False
        if isinstance(face.Surface, Part.Cylinder):
            return False
        return True

    return matches


def _mono_prism_solid(cx: float, cz: float, radius: float, depth: float, sides: int):
    angles = [2.0 * math.pi * index / sides for index in range(sides)]
    points = [
        App.Vector(cx + radius * math.cos(angle), Y_FRONT, cz + radius * math.sin(angle))
        for angle in angles
    ]
    wire = Part.makePolygon(points + [points[0]])
    return Part.Face(wire).extrude(App.Vector(0.0, depth, 0.0))


def _mono_face_filter(cx: float, cz: float, radius: float):
    def matches(face) -> bool:
        if not isinstance(face.Surface, Part.Plane):
            return False
        center = face.CenterOfMass
        radial = math.hypot(center.x - cx, center.z - cz)
        return (
            Y_FRONT - 0.05 <= center.y <= Y_FRONT + GRIP_DEPTH_MM["mono-25"] + 0.05
            and radius * 0.65 <= radial <= radius * 1.05
        )

    return matches


def _fillet_outer_vertical(body_shape):
    edges = []
    for edge in body_shape.Edges:
        p0 = edge.Vertexes[0].Point
        p1 = edge.Vertexes[1].Point
        if abs(p0.y - p1.y) < BODY_Y * 0.95:
            continue
        if abs(p0.x - p1.x) > 0.5 or abs(p0.z - p1.z) > 0.5:
            continue
        if max(abs(p0.x), abs(p1.x)) < HALF_X - 0.5:
            continue
        if max(abs(p0.z), abs(p1.z)) < HALF_Z - 0.5:
            continue
        edges.append(edge)
    if len(edges) < 4:
        return body_shape
    return body_shape.makeFillet(CORNER_R, edges[:4])


def _shell_from_body_faces(body_shape, predicate):
    faces = [face for face in body_shape.Faces if predicate(face)]
    if not faces:
        raise ValueError("no body faces matched the contact predicate")
    if len(faces) == 1:
        return faces[0]
    return Part.makeCompound(faces)


def _pocket_cutter(x0: float, x1: float, z0: float, z1: float, depth: float):
    return Part.makeBox(
        x1 - x0,
        depth + 0.02,
        z1 - z0,
        App.Vector(x0, Y_FRONT - 0.01, z0),
    )


def _mono_cutter(cx: float, cz: float, radius: float, depth: float):
    prism = _mono_prism_solid(cx, cz, radius + 0.02, depth + 0.02, MONO_SIDES)
    return prism


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
    for contact_id, (x0, x1, z0, z1) in OPENINGS.items():
        depth = GRIP_DEPTH_MM[contact_id]
        cutters.append(_pocket_cutter(x0, x1, z0, z1, depth))
        contact_predicates.append(
            (contact_id, _pocket_face_filter(x0, x1, z0, z1, depth))
        )

    mono_depth = GRIP_DEPTH_MM["mono-25"]
    cutters.append(_mono_cutter(MONO_CENTER_X, MONO_CENTER_Z, MONO_RADIUS, mono_depth))
    contact_predicates.append(
        ("mono-25", _mono_face_filter(MONO_CENTER_X, MONO_CENTER_Z, MONO_RADIUS))
    )

    fused_shape = cutters[0]
    for cutter in cutters[1:]:
        fused_shape = fused_shape.fuse(cutter)
    cutter_obj = document.addObject("Part::Feature", "PocketCutters")
    cutter_obj.Shape = fused_shape

    body_cut = document.addObject("Part::Cut", "BodySolid")
    body_cut.Base = brick
    body_cut.Tool = cutter_obj

    document.recompute()
    if body_cut.Shape.isNull() or body_cut.Shape.Volume < 1.0:
        raise ValueError("boolean cut failed to produce a solid body")

    body_cut.addProperty("App::PropertyString", "NodeID", "HangTen")
    body_cut.addProperty("App::PropertyString", "NodeRole", "HangTen")
    body_cut.NodeID = NODE_IDS["body"]
    body_cut.NodeRole = "body"
    _apply_material(body_cut, texture_source)

    document.recompute()
    body_cut.Shape = _fillet_outer_vertical(body_cut.Shape)
    document.recompute()
    body_shape = body_cut.Shape

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
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
