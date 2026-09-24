"""Hybrid migration: Hangboards/soill-iron-palm-2/*.FCStd.

Piece-by-piece measured approximation over a faceted-import base:

  Piece 1 (current): left/right large slopers → LS-fit analytic sphere for the
  bulb + retained reference mesh collar for the board blend (no fake necks).
  Remaining: rails, pinches, top jug stay faceted-import meshes

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

import FreeCAD as App  # noqa: E402
import Mesh  # noqa: E402
import Part  # noqa: E402
from pxr import Usd, UsdGeom  # noqa: E402

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

# Nodes authored as native Part geometry this piece (not full mesh-import).
# Sphere centre/R from least-squares fit on reference bulb points (Y < -25 mm),
# mirrored. The reference blend collar (faces near the board) stays faceted so
# the bulb stays molded into the board instead of floating.
NATIVE_SLOPERS = {
    "left_large_sloper_001": {
        "center_mm": (-244.49, -23.10, 71.17),
        "radius_mm": 77.05,
        "blend_y_mm": -28.0,
        "contact": "sloper-left",
    },
    "right_large_sloper_001": {
        "center_mm": (244.49, -23.10, 71.17),
        "radius_mm": 77.05,
        "blend_y_mm": -28.0,
        "contact": "sloper-right",
    },
}

# Faceted remainder — keep shell-critical meshes denser.
TARGET_TRIS = {
    "body_board_001": 14166,
    "left_pinch_001": 2500,
    "right_pinch_001": 2500,
    "rail_15_001": 7952,
    "rail_35_001": 919,
    "rail_40_001": 3510,
    "top_jug_001": 200,
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


def _build_mesh(points, facets) -> Mesh.Mesh:
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



def _carve_mesh_for_slopers(mesh: Mesh.Mesh, specs: dict, inflate_mm: float = 4.0) -> Mesh.Mesh:
    """Remove body triangles that sit inside a native sloper sphere.

    Leaves a seat so the analytic bulb is not fighting the faceted front shell.
    """
    points = list(mesh.Topology[0])
    facets = list(mesh.Topology[1])
    spheres = [
        (
            float(s["center_mm"][0]),
            float(s["center_mm"][1]),
            float(s["center_mm"][2]),
            float(s["radius_mm"]) + inflate_mm,
        )
        for s in specs.values()
    ]
    kept = []
    for a, b, c in facets:
        cx = (points[a].x + points[b].x + points[c].x) / 3.0
        cy = (points[a].y + points[b].y + points[c].y) / 3.0
        cz = (points[a].z + points[b].z + points[c].z) / 3.0
        inside = False
        for sx, sy, sz, radius in spheres:
            dx, dy, dz = cx - sx, cy - sy, cz - sz
            if dx * dx + dy * dy + dz * dz <= radius * radius:
                inside = True
                break
        if not inside:
            kept.append((a, b, c))
    if len(kept) < 100:
        raise ValueError(f"sloper carve left only {len(kept)} body triangles")
    out = Mesh.Mesh()
    triples = []
    for a, b, c in kept:
        triples.append(points[a])
        triples.append(points[b])
        triples.append(points[c])
    out.addFacets(triples)
    out.removeDuplicatedPoints()
    out.removeDuplicatedFacets()
    out.harmonizeNormals()
    print(
        f"    carve sloper seats: {len(facets)} → {out.CountFacets} tris "
        f"(inflate {inflate_mm} mm)"
    )
    return out


def _native_sloper(spec: dict, points, facets) -> Part.Shape:
    """Smooth fitted bulb mesh + reference blend collar, as one mesh shell.

    Sphere centre/R from LS fit on the free bulb. Collar faces near the board
    stay from the reference so the hold keeps its molded attachment. Merged to
    a single mesh before Part conversion so compile stays responsive.
    """
    import math

    cx, cy, cz = (float(v) for v in spec["center_mm"])
    radius = float(spec["radius_mm"])
    blend_y = float(spec.get("blend_y_mm", -28.0))
    bulb_deflection = float(spec.get("bulb_deflection_mm", 0.6))

    sphere = Part.makeSphere(radius)
    sphere.translate(App.Vector(cx, cy, cz))
    extent = radius * 4.0
    clip = Part.makeBox(extent, extent + 2.0, extent)
    clip.translate(App.Vector(cx - extent / 2.0, -extent, cz - extent / 2.0))
    bulb = sphere.common(clip)
    if bulb.isNull() or not bulb.Faces:
        raise ValueError(f"sloper bulb at ({cx},{cy},{cz}) is empty")
    bulb_pts, bulb_faces = bulb.tessellate(bulb_deflection)
    if not bulb_faces:
        raise ValueError(f"sloper bulb tessellation empty at ({cx},{cy},{cz})")

    collar_facets = []
    for a, b, c in facets:
        pa, pb, pc = points[a], points[b], points[c]
        mx = (pa[0] + pb[0] + pc[0]) / 3.0
        my = (pa[1] + pb[1] + pc[1]) / 3.0
        mz = (pa[2] + pb[2] + pc[2]) / 3.0
        dist = math.sqrt((mx - cx) ** 2 + (my - cy) ** 2 + (mz - cz) ** 2)
        if my >= blend_y or dist > radius + 1.5:
            collar_facets.append((a, b, c))
    if len(collar_facets) < 50:
        raise ValueError(
            f"sloper collar at x={cx} kept only {len(collar_facets)} faces"
        )
    collar_mesh = _build_mesh(points, collar_facets)
    collar_mesh = _simplify(collar_mesh, 2000)

    merged = Mesh.Mesh()
    triples = []
    for face in bulb_faces:
        triples.append(bulb_pts[face[0]])
        triples.append(bulb_pts[face[1]])
        triples.append(bulb_pts[face[2]])
    # Collar topology points are FreeCAD Vectors from _build_mesh path — use mesh API.
    collar_pts = list(collar_mesh.Topology[0])
    for a, b, c in collar_mesh.Topology[1]:
        triples.append(collar_pts[a])
        triples.append(collar_pts[b])
        triples.append(collar_pts[c])
    merged.addFacets(triples)
    merged.removeDuplicatedPoints()
    merged.removeDuplicatedFacets()
    merged.harmonizeNormals()
    print(f"bulb+collar tris≈{merged.CountFacets} ", end="")
    return _mesh_to_shape(merged)


def main() -> int:
    board = json.loads(BOARD_JSON.read_text())
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

    imported = []
    # Index reference meshes by name for native pieces that keep a collar.
    ref_meshes = {}
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh) and prim.GetName() in NODE_MAP:
            ref_meshes[prim.GetName()] = _world_mesh(stage, cache, prim)

    # --- Piece 1: LS-fit smooth bulb + reference blend collar ---
    for name, spec in NATIVE_SLOPERS.items():
        role, contact_id = NODE_MAP[name]
        points, facets = ref_meshes[name]
        shape = _native_sloper(spec, points, facets)
        feature = document.addObject("Part::Feature", name)
        feature.Shape = shape
        feature.addProperty("App::PropertyString", "NodeID", "HangTen")
        feature.addProperty("App::PropertyString", "NodeRole", "HangTen")
        feature.NodeID = name
        feature.NodeRole = role
        feature.addProperty("App::PropertyString", "ContactID", "HangTen")
        feature.ContactID = contact_id
        feature.Placement = App.Placement(
            App.Vector(0.0, CONTACT_NUDGE_Y_MM, 0.0), App.Rotation()
        )
        _apply_material(feature, None)
        imported.append((name, role, contact_id, "bulb+collar", len(shape.Faces)))
        print(
            f"native {name}: R={spec['radius_mm']} at {spec['center_mm']} "
            f"faces={len(shape.Faces)}"
        )

    # --- Remaining nodes: faceted import from reference ---
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        name = prim.GetName()
        if name not in NODE_MAP or name in NATIVE_SLOPERS:
            continue
        role, contact_id = NODE_MAP[name]
        points, facets = _world_mesh(stage, cache, prim)
        print(f"  import {name}: {len(points)} pts, {len(facets)} tris →", end=" ")
        mesh = _build_mesh(points, facets)
        mesh = _simplify(mesh, TARGET_TRIS.get(name, 2000))
        if name == "body_board_001":
            mesh = _carve_mesh_for_slopers(mesh, NATIVE_SLOPERS, inflate_mm=4.0)
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
    print("piece 1: native slopers; sourceKind=faceted-import; --allow-faceted-import")
    for name, role, contact_id, tris, faces in imported:
        print(f"  {name:28s} role={role:7s} contact={contact_id} geom={tris} faces={faces}")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
