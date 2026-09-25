"""Hybrid migration: Hangboards/soill-iron-palm-2/*.FCStd.

Piece-by-piece measured approximation over a faceted-import base:

  Piece 1: left/right large slopers → faceted import at full reference
  resolution. An analytic sphere cannot reproduce the reference collar that
  blends the ball into the body, pinch and rails: the collar is a sculpted
  surface, so a generated sphere leaves a seat seam, and flaring or pulling
  the neighbours to hide it produces a chin/lip or a crease. Importing the
  reference sloper keeps the moulded blend intact (and the model budget is
  well inside the catalogue range).
  Piece 2: top jug → native rounded rail extruded into the fitted sloper
  spheres (sphere-cut ends). Reference end-collar mesh merge was dropped
  — it left open edges and a blacked-out top face.
  Remaining: rails, pinches stay faceted-import meshes

HangTenSourceKind stays `faceted-import` until every node is native.
Publish with `--allow-faceted-import`.

Cross-ref: .context/fearless-penguin/soill-iron-palm-2/cross-ref.md
"""

from __future__ import annotations

import hashlib
import json
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
sys.path.insert(0, str(REPOSITORY / "Tools" / "HangboardPackages" / "src"))

import FreeCAD as App  # noqa: E402
import Mesh  # noqa: E402
import Part  # noqa: E402
from pxr import Usd, UsdGeom  # noqa: E402

from hangboard_packages import cad_source  # noqa: E402
from reference import load_reference  # noqa: E402

PACKAGE = "soill-iron-palm-2"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
SCRATCH = Path(
    os.environ.get(
        "HANGTEN_CAD_SCRATCH",
        str(REPOSITORY / ".context" / "fearless-penguin" / PACKAGE),
    )
)

# Reference USD mesh name → (NodeRole, ContactID|None)
NODE_MAP = {
    "body_board_001": ("body", None),
    "left_large_sloper_001": ("contact", "sloper-left"),
    "right_large_sloper_001": ("contact", "sloper-right"),
    "left_pinch_001": ("contact", "pinch-left"),
    "right_pinch_001": ("contact", "pinch-right"),
    "rail_15_001": ("contact", "flat-edge-15"),
    "rail_35_001": ("contact", "flat-edge-35"),
    "rail_40_001": ("contact", "rounded-edge-40"),
    "top_jug_001": ("contact", "top-incut-jug"),
}

# Fitted sloper bulbs, measured from the reference mesh (robust least-squares on
# the front cap, Y < -55 mm, mirrored left/right; residual ~0.25 mm). Only the
# sphere is used here — the top jug is boolean-cut by it so its ends sit on the
# bulbs. The slopers themselves ship as faceted imports (see module docstring).
SLOPER_SPHERES = {
    "left_large_sloper_001": {
        "center_mm": (-244.00, -28.24, 72.20),
        "radius_mm": 73.32,
    },
    "right_large_sloper_001": {
        "center_mm": (244.00, -28.24, 72.20),
        "radius_mm": 73.32,
    },
}

# Piece 2: measured mid-span incut top jug. Reference top_jug_001 spans native
# z 66..109 (front silhouette sampled below) and reaches into the fitted spheres
# at the ends; a shorter bar left the top window (z 43..66) open and the bar read
# as a black strip.
NATIVE_TOP_JUG = {
    # Must reach into the fitted spheres (inner tangent at front ≈ ±188 mm).
    "x_half_mm": 195.0,
    # YZ closed profile, native (y_front, z_up): back edge, then the measured
    # front silhouette up to the rounded crown, then back edge again.
    "profile_yz_mm": [
        (-0.5, 66.0),
        (-61.0, 66.0),
        (-66.5, 70.0),
        (-69.0, 77.0),
        (-70.0, 85.0),
        (-69.9, 91.0),
        (-69.5, 96.0),
        (-68.4, 100.0),
        (-62.6, 104.0),
        (-52.0, 107.0),
        (-38.0, 108.5),
        (-0.5, 108.5),
    ],
    "contact": "top-incut-jug",
}

NATIVE_NODES = {"top_jug_001"}

# Faceted remainder — keep shell-critical meshes denser. Pinches ship at their
# reference triangle count: decimating them spiked a sliver that poked through
# the ball seat and rendered as a black tick.
TARGET_TRIS = {
    "body_board_001": 14166,
    "left_large_sloper_001": 20000,
    "right_large_sloper_001": 20000,
    "left_pinch_001": 13997,
    "right_pinch_001": 14250,
    "rail_15_001": 7952,
    "rail_35_001": 919,
    "rail_40_001": 3510,
}

MATERIAL_NAME = "neutral_urethane"
MATERIAL_BASE_COLOR = "0.18,0.18,0.20"
MATERIAL_ROUGHNESS = 0.72
MATERIAL_METALLIC = 0.0

# Contact shells nudged toward the front to avoid z-fighting body lips.
CONTACT_NUDGE_Y_MM = -0.25


def _runtime_to_native(points):
    """Runtime metres (+X right +Y up +Z front) → native mm (+X +Z up front -Y)."""
    out = []
    for point in points:
        out.append((point[0] * 1000.0, -point[2] * 1000.0, point[1] * 1000.0))
    return out


def _world_mesh(stage, cache, prim):
    mesh = UsdGeom.Mesh(prim)
    points = mesh.GetPointsAttr().Get()
    counts = mesh.GetFaceVertexCountsAttr().Get()
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    matrix = cache.GetLocalToWorldTransform(prim)
    world = [matrix.Transform(point) for point in points]
    native = _runtime_to_native(world)
    facets = []
    cursor = 0
    for count in counts:
        face = list(indices[cursor : cursor + count])
        cursor += count
        if count == 3:
            facets.append(tuple(face))
        elif count == 4:
            a, b, c, d = face
            facets.append((a, b, c))
            facets.append((a, c, d))
        else:
            # Fan triangulation for rare n-gons.
            for i in range(1, count - 1):
                facets.append((face[0], face[i], face[i + 1]))
    return native, facets


def _reference_texture(reference: Path) -> tuple[Path, str]:
    with zipfile.ZipFile(reference) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".png")]
        if not names:
            raise ValueError("no reference texture found")
        preferred = [n for n in names if "urethane" in n.lower() or "neutral" in n.lower()]
        member = preferred[0] if preferred else names[0]
        data = archive.read(member)
    scratch = SCRATCH / "assets"
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / os.path.basename(member)
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


def _build_mesh(points, facets, harmonize: bool = True) -> Mesh.Mesh:
    mesh = Mesh.Mesh()
    # FreeCAD addFacets wants flat list of Vector triplets or (p1,p2,p3) points.
    triples = []
    for a, b, c in facets:
        triples.append(points[a])
        triples.append(points[b])
        triples.append(points[c])
    mesh.addFacets(triples)
    mesh.removeDuplicatedPoints()
    mesh.removeDuplicatedFacets()
    if harmonize:
        # Only for meshes we construct: harmonizeNormals can flip a triangle on
        # an open imported shell, which then renders as a black sliver.
        mesh.harmonizeNormals()
    return mesh


def _simplify(mesh: Mesh.Mesh, target_tris: int) -> Mesh.Mesh:
    """Decimate toward target_tris; fall back to original if decimate fails."""
    before = mesh.CountFacets
    if before <= target_tris:
        print(f"    keep {before} tris (already ≤{target_tris})")
        return mesh
    try:
        trial = mesh.copy()
        # FreeCAD: decimate(tolerance, reduction) or decimate(targetSize=int)
        trial.decimate(int(target_tris))
        # targetSize is a soft request; push further with reduction passes.
        for _ in range(8):
            if trial.CountFacets <= target_tris:
                break
            prev = trial.CountFacets
            need = 1.0 - (float(target_tris) / float(prev))
            reduction = min(max(need, 0.15), 0.85)
            nxt = trial.copy()
            nxt.decimate(0.75, reduction)
            nxt.removeDuplicatedPoints()
            nxt.removeDuplicatedFacets()
            if nxt.CountFacets < 10 or nxt.CountFacets >= prev:
                break
            trial = nxt
        trial.removeDuplicatedPoints()
        trial.removeDuplicatedFacets()
        trial.harmonizeNormals()
        if trial.CountFacets < 10:
            raise ValueError("decimate collapsed mesh")
        print(f"    simplify {before} → {trial.CountFacets} tris (target ≤{target_tris})")
        return trial
    except Exception as exc:
        print(f"    simplify failed ({exc}); keeping {before} tris")
        return mesh


def _mesh_to_shape(mesh: Mesh.Mesh) -> Part.Shape:
    shape = Part.Shape()
    # Tight sewing tolerance — looser values open seams at rail ends.
    shape.makeShapeFromMesh(mesh.Topology, 0.01)
    if shape.isNull() or not shape.Faces:
        raise ValueError("makeShapeFromMesh produced an empty shape")
    # Prefer a shell; keep faces if solidification fails.
    try:
        shells = shape.Shells
        if len(shells) == 1:
            return shells[0]
        if shells:
            return Part.makeCompound(shells)
    except Exception:
        pass
    return shape



def _native_top_jug(spec: dict, sloper_specs: dict) -> Part.Shape:
    """Native mid-span rail cut to the sloper spheres.

    Mid-span uses a measured YZ incut profile extruded along X, then boolean-cut
    by the fitted sloper spheres so the ends sit on the bulbs. Returns the Part
    solid directly (no mesh round-trip) so compile keeps closed shells and
    outward normals — meshing + re-import previously blacked out the top face.
    """
    x_half = float(spec["x_half_mm"])
    profile = [(float(y), float(z)) for y, z in spec["profile_yz_mm"]]

    # Closed YZ wire at x=-x_half. Clockwise when looking along +X so a single
    # +X extrusion yields outward shell normals.
    ordered = list(reversed(profile))
    wire_pts = [App.Vector(-x_half, y, z) for y, z in ordered]
    wire_pts.append(App.Vector(-x_half, ordered[0][0], ordered[0][1]))
    face = Part.Face(Part.makePolygon(wire_pts))
    if face.isNull():
        raise ValueError("top_jug profile face is null")
    rail = face.extrude(App.Vector(2.0 * x_half, 0.0, 0.0))
    if rail.isNull() or not rail.Faces:
        raise ValueError("top_jug extrusion is empty")

    try:
        sharp = []
        for edge in rail.Edges:
            if edge.Length < 1.0:
                continue
            tangent = edge.tangentAt(edge.FirstParameter)
            if abs(tangent.x) > 0.85:
                sharp.append(edge)
        if sharp:
            rail = rail.makeFillet(2.5, sharp[:12])
    except Exception as error:
        print(f"    top_jug fillet skipped: {error}")

    for s in sloper_specs.values():
        sx, sy, sz = (float(v) for v in s["center_mm"])
        # Slightly oversized cut so end caps sit inside the bulbs and do not
        # z-fight the sloper surface (reads as a black line on the top bar).
        radius = float(s["radius_mm"]) + 0.6
        sphere = Part.makeSphere(radius)
        sphere.translate(App.Vector(sx, sy, sz))
        rail = rail.cut(sphere)

    if rail.isNull() or not rail.Faces:
        raise ValueError("native top_jug rail is empty after sphere cuts")
    try:
        rail.fix(0.1, 0.1, 0.1)
    except Exception:
        pass
    if rail.ShapeType == "Compound" and len(rail.Solids) == 1:
        rail = rail.Solids[0]
    print(
        f"rail solid faces={len(rail.Faces)} closed={rail.isClosed()} "
        f"vol={rail.Volume:.0f} ",
        end="",
    )
    return rail



def main() -> int:
    # A CAD-backed package keeps its board metadata in the FCStd manifest; the
    # hand-authored board.json is only present before the first embed.
    if BOARD_JSON.is_file():
        board = json.loads(BOARD_JSON.read_text())
    elif DESTINATION.is_file():
        board = cad_source.load_board(DESTINATION)
    else:
        raise SystemExit("no board.json and no embedded board manifest")
    reference, reference_digest = load_reference(PACKAGE, "primary.usdz", SCRATCH / "ref")
    stage = Usd.Stage.Open(str(reference))
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    texture_source, texture_digest = _reference_texture(reference)

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
    document.HangTenSourceKind = "faceted-import"
    document.HangTenCoordinateFrame = "freecad-mm-z-up-front-negative-y"
    # Analytic spheres tessellate finely enough at 0.2; tighter values stall when
    # compounded with dense reference collars.
    document.HangTenTessellationDeflection = 0.2
    # The FCStd owns the board metadata; board.json is generated from this at
    # build time and must not exist in the package.
    document.addProperty("App::PropertyString", "HangTenBoardManifest", "HangTen")
    document.HangTenBoardManifest = cad_source.render_manifest(
        cad_source.board_to_manifest(board)
    )

    imported = []

    # --- Piece 2: native mid-span top jug cut into sloper spheres ---
    jug_name = "top_jug_001"
    role, contact_id = NODE_MAP[jug_name]
    jug_shape = _native_top_jug(NATIVE_TOP_JUG, SLOPER_SPHERES)
    feature = document.addObject("Part::Feature", jug_name)
    feature.Shape = jug_shape
    feature.addProperty("App::PropertyString", "NodeID", "HangTen")
    feature.addProperty("App::PropertyString", "NodeRole", "HangTen")
    feature.NodeID = jug_name
    feature.NodeRole = role
    feature.addProperty("App::PropertyString", "ContactID", "HangTen")
    feature.ContactID = contact_id
    feature.Placement = App.Placement(
        App.Vector(0.0, CONTACT_NUDGE_Y_MM, 0.0), App.Rotation()
    )
    _apply_material(feature, None)
    imported.append((jug_name, role, contact_id, "rail", len(jug_shape.Faces)))
    print(f"native {jug_name}: faces={len(jug_shape.Faces)}")

    # --- Remaining nodes: faceted import from reference ---
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        name = prim.GetName()
        if name not in NODE_MAP or name in NATIVE_NODES:
            continue
        role, contact_id = NODE_MAP[name]
        points, facets = _world_mesh(stage, cache, prim)
        print(f"  import {name}: {len(points)} pts, {len(facets)} tris →", end=" ")
        mesh = _build_mesh(points, facets, harmonize=False)
        mesh = _simplify(mesh, TARGET_TRIS.get(name, 2000))
        shape = _mesh_to_shape(mesh)
        feature = document.addObject("Part::Feature", name)
        feature.Shape = shape
        feature.addProperty("App::PropertyString", "NodeID", "HangTen")
        feature.addProperty("App::PropertyString", "NodeRole", "HangTen")
        feature.NodeID = name
        feature.NodeRole = role
        if contact_id is not None:
            feature.addProperty("App::PropertyString", "ContactID", "HangTen")
            feature.ContactID = contact_id
            feature.Placement = App.Placement(
                App.Vector(0.0, CONTACT_NUDGE_Y_MM, 0.0), App.Rotation()
            )
        _apply_material(feature, texture_source if role == "body" else None)
        # Store the approved display mesh alongside the B-rep so compile can
        # ship the exact source triangles instead of re-tessellating a Part
        # shape (which opens slivers at the curved ball seats).
        source_feature = document.addObject("Mesh::Feature", f"{name}_source")
        source_feature.Mesh = mesh
        if contact_id is not None:
            source_feature.Placement = App.Placement(
                App.Vector(0.0, CONTACT_NUDGE_Y_MM, 0.0), App.Rotation()
            )
        imported.append((name, role, contact_id, mesh.CountFacets, len(shape.Faces)))
        print(f"Part faces={len(shape.Faces)}")

    missing = set(NODE_MAP) - {row[0] for row in imported}
    if missing:
        raise ValueError(f"missing nodes: {sorted(missing)}")

    document.recompute()
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    if DESTINATION.exists():
        DESTINATION.unlink()
    document.saveAs(str(DESTINATION))

    print(f"authored {DESTINATION} ({DESTINATION.stat().st_size} bytes)")
    print(f"reference sha256 {reference_digest}")
    print(f"texture sha256 {texture_digest}")
    print(
        "piece 2: native top jug (sphere-cut rail); slopers shipped as "
        "faceted imports at reference resolution; "
        "sourceKind=faceted-import; --allow-faceted-import"
    )
    for name, role, contact_id, tris, faces in imported:
        print(f"  {name:28s} role={role:7s} contact={contact_id} geom={tris} faces={faces}")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
