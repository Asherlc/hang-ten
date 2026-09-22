"""One-off migration: author ModelSources/lattice-triple-rung.FCStd natively.

This script is a MIGRATION TOOL, not a build input. The saved FCStd must stand
alone: the shared compiler never runs this file, and nothing here is required to
rebuild the published runtime asset.

Provenance of every number written into the document:

* Overall size 550 x 130 x 50 mm and the three grip depths (45, 20, 10 mm) come
  from ``Hangboards/lattice-triple-rung/board.json`` (``dimensions`` and each
  contact's ``depth.range``). These are PUBLISHED product facts.
* The cross-section outline is MEASURED from the approved model reference
  ``Hangboards/lattice-triple-rung/assets/primary.usdz``: the ordered boundary
  loop of the body's end cap, converted to native FreeCAD millimetres
  ``(x, y, z) = (X, -Z, Y)``. It is a measured approximation of a display mesh,
  not recovered manufacturing data.
* Contact band boundaries are the measured endpoints of each contact node's own
  swept polyline, snapped to the nearest measured profile vertex.
* Reduction from 267 measured points to the authored vertex set keeps every
  vertex whose removal would deviate the outline by more than 0.2 mm. The
  achieved maximum deviation is recorded in the provenance JSON.

The authored sketch is deliberately a closed polyline of measured vertices with
explicit dimensional constraints on the published facts, so that editing a
dimension in the FreeCAD GUI changes the exported surface. Nothing here is
presented as recovered parametric design history.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path[:0] = [
    part
    for part in os.environ.get("HANGTEN_CAD_PYTHONPATH", "").split(os.pathsep)
    if part
]

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402
import Sketcher  # noqa: E402
from pxr import Usd, UsdGeom  # noqa: E402

PACKAGE = "lattice-triple-rung"
# The approved reference is read from Git at the recorded pre-migration commit,
# never from the live runtime path: the shared compiler overwrites that path
# with this migration's own output, so reading it there would silently make the
# migration compare against itself.
REFERENCE_COMMIT = "6b828e156d4e14ec4a8aa0e3b8f17212336be7bc"
REFERENCE_PATH = f"Hangboards/{PACKAGE}/assets/primary.usdz"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "ModelSources" / f"{PACKAGE}.FCStd"
PROVENANCE = REPOSITORY / "ModelSources" / f"{PACKAGE}.provenance.json"
BODY_PRIM = "/root/LatticeBody/LatticeBody_editable_surface_001"
BAND_PRIMS = {
    "edge-10": "/root/edge_10/edge_10_editable_surface_001",
    "edge-20": "/root/edge_20/edge_20_editable_surface_001",
    "edge-45": "/root/edge_45/edge_45_editable_surface_001",
}
REDUCTION_TOLERANCE_MM = 0.2
# Published facts from board.json; asserted against the measured reference.
PUBLISHED_MM = {"width": 550.0, "height": 130.0, "depth": 50.0}
GRIP_DEPTH_MM = {"edge-45": 45.0, "edge-20": 20.0, "edge-10": 10.0}


def _world_points(stage: Usd.Stage, cache: UsdGeom.XformCache, path: str):
    prim = stage.GetPrimAtPath(path)
    mesh = UsdGeom.Mesh(prim)
    points = mesh.GetPointsAttr().Get()
    matrix = cache.GetLocalToWorldTransform(prim)
    out = []
    for point in points:
        world = matrix.Transform(point) * 1000.0
        out.append((world[0], -world[2], world[1]))
    indices = [
        tuple(mesh.GetFaceVertexIndicesAttr().Get()[i : i + 3])
        for i in range(0, len(mesh.GetFaceVertexIndicesAttr().Get()), 3)
    ]
    return out, indices


def _ordered_cap_outline(points, triangles, x_limit: float):
    cap = {i for i, point in enumerate(points) if point[0] > x_limit}
    edges: Counter = Counter()
    for triangle in triangles:
        if not set(triangle) <= cap:
            continue
        for a, b in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0])):
            edges[(min(a, b), max(a, b))] += 1
    adjacency: dict[int, list[int]] = {}
    for (a, b), count in edges.items():
        if count == 1:
            adjacency.setdefault(a, []).append(b)
            adjacency.setdefault(b, []).append(a)
    start = min(adjacency)
    loop = [start]
    previous, current = None, start
    while True:
        following = [n for n in adjacency[current] if n != previous]
        if not following:
            break
        previous, current = current, following[0]
        if current == start:
            break
        loop.append(current)
    if len(loop) != len(adjacency):
        raise ValueError("cap outline is not one closed loop")
    return [points[i] for i in loop]


def _reduce(outline, tolerance: float):
    keep = [0]
    index = 0
    count = len(outline)
    while index < count - 1:
        candidate = index + 2
        while candidate < count:
            start, end = outline[index], outline[candidate]
            span = (end[0] - start[0], end[1] - start[1], end[2] - start[2])
            length = math.dist(start, end)
            worst = 0.0
            for point in outline[index : candidate + 1]:
                dx = (point[0] - start[0], point[1] - start[1], point[2] - start[2])
                cross = (
                    span[1] * dx[2] - span[2] * dx[1],
                    span[2] * dx[0] - span[0] * dx[2],
                    span[0] * dx[1] - span[1] * dx[0],
                )
                worst = max(worst, math.sqrt(sum(c * c for c in cross)) / max(length, 1e-12))
            if worst > tolerance:
                break
            candidate += 1
        keep.append(candidate - 1)
        index = candidate - 1
    return keep


def _polyline_max_deviation(outline, indices) -> float:
    worst = 0.0
    count = len(indices)
    for position in range(count):
        start = outline[indices[position]]
        end = outline[indices[(position + 1) % count]]
        span = (end[0] - start[0], end[1] - start[1], end[2] - start[2])
        length = math.dist(start, end)
        low = indices[position]
        high = indices[(position + 1) % count]
        span_points = outline[low:] + outline[: high + 1] if high < low else outline[low : high + 1]
        for point in span_points:
            dx = (point[0] - start[0], point[1] - start[1], point[2] - start[2])
            cross = (
                span[1] * dx[2] - span[2] * dx[1],
                span[2] * dx[0] - span[0] * dx[2],
                span[0] * dx[1] - span[1] * dx[0],
            )
            worst = max(worst, math.sqrt(sum(c * c for c in cross)) / max(length, 1e-12))
    return worst


MATERIAL_NAME = "neutral_tulipwood"
MATERIAL_BASE_COLOR = "0.72,0.55,0.36"
MATERIAL_ROUGHNESS = 0.58
MATERIAL_METALLIC = 0.0


def _reference_asset() -> tuple[Path, str]:
    """Materialise the approved reference from its recorded Git commit."""
    import subprocess

    override = os.environ.get("HANGTEN_REFERENCE")
    if override:
        path = Path(override)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()
    stored = subprocess.run(
        ["git", "show", f"{REFERENCE_COMMIT}:{REFERENCE_PATH}"],
        cwd=REPOSITORY,
        check=True,
        capture_output=True,
    ).stdout
    # The reference is Git LFS tracked, so the stored blob is a pointer; the
    # smudge filter resolves it and its declared object id is checked below.
    resolved = subprocess.run(
        ["git", "lfs", "smudge"], input=stored, capture_output=True, check=True
    ).stdout
    if resolved.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise ValueError("Git LFS smudge did not resolve the reference object")
    declared = None
    for line in stored.decode("utf-8", "replace").splitlines():
        if line.startswith("oid sha256:"):
            declared = line.split(":", 1)[1].strip()
    digest = hashlib.sha256(resolved).hexdigest()
    if declared is not None and declared != digest:
        raise ValueError("resolved reference does not match its Git LFS object id")
    scratch_root = Path(os.environ.get("HANGTEN_CAD_SCRATCH", "/tmp")) / f"{PACKAGE}-assets"
    scratch_root.mkdir(parents=True, exist_ok=True)
    path = scratch_root / "reference.usdz"
    path.write_bytes(resolved)
    return path, digest


def _reference_texture(reference: Path) -> tuple[str, Path, str]:
    """Extract the approved display texture from the reference package."""
    import zipfile

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


def main() -> int:
    board = json.loads(BOARD_JSON.read_text())
    reference, reference_digest = _reference_asset()
    stage = Usd.Stage.Open(str(reference))
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())

    body_points, body_triangles = _world_points(stage, cache, BODY_PRIM)
    xs = [point[0] for point in body_points]
    outline = _ordered_cap_outline(body_points, body_triangles, max(xs) - 0.1)
    measured = {
        "width": max(xs) - min(xs),
        "height": max(p[2] for p in body_points) - min(p[2] for p in body_points),
        "depth": max(p[1] for p in body_points) - min(p[1] for p in body_points),
    }
    for key, published in PUBLISHED_MM.items():
        if abs(measured[key] - published) > 0.05:
            raise ValueError(f"measured {key} {measured[key]:.3f} disagrees with published {published}")

    forced: set[int] = set()
    band_runs: dict[str, tuple[int, int]] = {}
    for contact_id, prim_path in BAND_PRIMS.items():
        band_points, _ = _world_points(stage, cache, prim_path)
        unique = sorted({(round(point[1], 4), round(point[2], 4)) for point in band_points})
        indices = sorted(
            {
                min(
                    range(len(outline)),
                    key=lambda i: (outline[i][1] - target[0]) ** 2 + (outline[i][2] - target[1]) ** 2,
                )
                for target in unique
            }
        )
        if any(indices[i + 1] - indices[i] != 1 for i in range(len(indices) - 1)):
            raise ValueError(f"{contact_id} contact band is not a contiguous profile run")
        measured_depth = max(outline[i][1] for i in indices) - min(outline[i][1] for i in indices)
        if abs(measured_depth - GRIP_DEPTH_MM[contact_id]) > 0.05:
            raise ValueError(
                f"{contact_id} measured grip depth {measured_depth:.3f} disagrees with published "
                f"{GRIP_DEPTH_MM[contact_id]}"
            )
        band_runs[contact_id] = (indices[0], indices[-1])
        forced.update(range(indices[0], indices[-1] + 1))

    reduced = sorted(set(_reduce(outline, REDUCTION_TOLERANCE_MM)) | forced)
    deviation = _polyline_max_deviation(outline, reduced)
    vertices = [outline[i] for i in reduced]
    position_of = {index: position for position, index in enumerate(reduced)}

    # The approved display material travels with the source: the texture image is
    # embedded in the FCStd so the document is self-contained and the compiler
    # never needs the previous runtime asset.
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
    document.addProperty("App::PropertyString", "HangTenProvenance", "HangTen")
    document.HangTenBoardID = board["id"]
    document.HangTenPresentationID = board["presentations"][0]["id"]
    document.HangTenSchemaVersion = 1
    document.HangTenSourceKind = "native-parametric-measured-profile"
    document.HangTenCoordinateFrame = "freecad-mm-z-up-front-negative-y"
    document.HangTenTessellationDeflection = 0.08
    document.HangTenProvenance = f"ModelSources/{PACKAGE}.provenance.json"

    body = document.addObject("PartDesign::Body", "Body")
    sketch = body.newObject("Sketcher::SketchObject", "Profile")
    # The profile lives on the body YZ plane with an explicit, fully determined
    # frame: sketch-local (u, v) maps to native (0, u, v), i.e. local +X is
    # native +Y (depth) and local +Y is native +Z (height). An explicit
    # placement avoids depending on the body origin's own axis directions.
    # Pinned-build quirk, verified in this script's own assertions: a Sketcher
    # DistanceX/DistanceY between a point and the sketch axis solves to the
    # NEGATED value (x = -value, y = -value) regardless of the initial geometry.
    # The authored outline therefore stores negated local coordinates with
    # positive driving dimensions, and the sketch frame negates them back. The
    # pad's world bounding box is asserted below, so any change in that behaviour
    # fails the build instead of silently mirroring the board.
    frame = App.Matrix(
        0.0, 0.0, 1.0, 0.0,
        -1.0, 0.0, 0.0, 0.0,
        0.0, -1.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )
    vertices = [
        (vertex[0], min(vertex[1], 0.0), max(vertex[2], 0.0)) for vertex in vertices
    ]
    sketch_shift = -min(vertex[1] for vertex in vertices)
    if min(vertex[2] for vertex in vertices) < -1e-6:
        raise ValueError("profile height must be non-negative for the authored sketch")
    sketch.MapMode = "Deactivated"
    sketch.AttachmentSupport = []
    sketch.Placement = App.Placement(App.Vector(0.0, -sketch_shift, 0.0), App.Rotation(frame))
    document.recompute()
    resolved = sketch.getGlobalPlacement()
    for local, expected in (
        (App.Vector(0.0, 0.0, 0.0), App.Vector(0.0, -sketch_shift, 0.0)),
        (App.Vector(1.0, 0.0, 0.0), App.Vector(0.0, -1.0 - sketch_shift, 0.0)),
        (App.Vector(0.0, 1.0, 0.0), App.Vector(0.0, -sketch_shift, -1.0)),
    ):
        if (resolved.multVec(local) - expected).Length > 1e-9:
            raise ValueError("profile sketch frame does not map local (u, v) to native (0, -u - shift, -v)")

    def to_local(y: float, z: float) -> App.Vector:
        return App.Vector(-(y + sketch_shift), -z, 0.0)

    geometry = [
        Part.LineSegment(
            to_local(vertices[i][1], vertices[i][2]),
            to_local(
                vertices[(i + 1) % len(vertices)][1],
                vertices[(i + 1) % len(vertices)][2],
            ),
        )
        for i in range(len(vertices))
    ]
    sketch.addGeometry(geometry, False)
    for i in range(len(vertices)):
        sketch.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % len(vertices), 1))

    lowest = min(range(len(vertices)), key=lambda i: vertices[i][2])
    highest = max(range(len(vertices)), key=lambda i: vertices[i][2])
    front = max(range(len(vertices)), key=lambda i: vertices[i][1])
    deepest = min(range(len(vertices)), key=lambda i: vertices[i][1])
    for label, index, axis in (("height", lowest, 2), ("depth", deepest, 1)):
        target = PUBLISHED_MM[label]
        measured_axis = abs(vertices[index][axis] - vertices[front if label == "height" else lowest][axis])
        if label == "height":
            measured_axis = abs(vertices[highest][2] - vertices[lowest][2])
        else:
            measured_axis = abs(vertices[front][1] - vertices[deepest][1])
        if abs(measured_axis - target) > 0.05:
            raise ValueError(f"{label} dimension {measured_axis:.3f} disagrees with published {target}")
    # Every authored vertex carries its measured coordinate as an explicit driving
    # dimension against the sketch origin. The profile is therefore fully
    # constrained (no solver freedom) and every vertex stays individually editable.
    for position in range(len(vertices)):
        sketch.addConstraint(
            Sketcher.Constraint(
                "DistanceX", position, 1, -1, 1, round(vertices[position][1] + sketch_shift, 6)
            )
        )
        sketch.addConstraint(
            Sketcher.Constraint("DistanceY", position, 1, -1, 1, round(vertices[position][2], 6))
        )
    if sketch.solve() and not sketch.FullyConstrained:
        raise ValueError("authored profile sketch is not fully constrained")
    if not sketch.FullyConstrained:
        raise ValueError("authored profile sketch is not fully constrained")

    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sketch
    pad.SideType = "Symmetric"
    pad.Length = PUBLISHED_MM["width"]

    # A contact region is the extrusion of its run of profile segments, bound to
    # the sketch's own edges. Sketch edges keep their identity when a driving
    # dimension changes, so the binding survives profile edits. Binding to the
    # pad's FACES instead was tried and rejected: FreeCAD lost the face element
    # map after a profile edit and the unrelated contact regions silently moved
    # to different faces. That failure is covered by the native checks below.
    contact_objects = {}
    for contact_id, (start_index, end_index) in sorted(band_runs.items()):
        first, last = position_of[start_index], position_of[end_index]
        if last > first:
            run = list(range(first, last))
        else:
            run = list(range(first, len(vertices))) + list(range(0, last))
        if not run:
            raise ValueError(f"{contact_id} contact band selected no profile edges")
        binder = document.addObject(
            "PartDesign::SubShapeBinder", f"Region_{contact_id.replace('-', '_')}"
        )
        binder.Support = [(sketch, f"Edge{i + 1}") for i in run]
        binder.MakeFace = False
        binder.Refine = False
        extrusion = document.addObject(
            "Part::Extrusion", f"Surface_{contact_id.replace('-', '_')}"
        )
        extrusion.Base = binder
        extrusion.DirMode = "Custom"
        extrusion.Dir = App.Vector(1.0, 0.0, 0.0)
        extrusion.Symmetric = True
        extrusion.Solid = False
        # The band is the same extrusion as the body, so its length follows the
        # pad through a native expression rather than a copied constant.
        extrusion.setExpression("LengthFwd", "Pad.Length")
        contact_objects[contact_id] = extrusion

    document.recompute()

    pad_box = pad.Shape.BoundBox
    expected_box = (-PUBLISHED_MM["width"] / 2.0, -PUBLISHED_MM["depth"], 0.0,
                    PUBLISHED_MM["width"] / 2.0, 0.0, PUBLISHED_MM["height"])
    actual_box = (pad_box.XMin, pad_box.YMin, pad_box.ZMin, pad_box.XMax, pad_box.YMax, pad_box.ZMax)
    if any(abs(a - b) > 0.05 for a, b in zip(actual_box, expected_box)):
        raise ValueError(f"authored body frame {actual_box} does not match native frame {expected_box}")

    depth_spans = {}
    for contact_id, extrusion in contact_objects.items():
        box = extrusion.Shape.BoundBox
        depth_spans[contact_id] = round(box.YLength, 3)
        extrusion.addProperty("App::PropertyString", "NodeID", "HangTen")
        extrusion.addProperty("App::PropertyString", "NodeRole", "HangTen")
        extrusion.addProperty("App::PropertyString", "ContactID", "HangTen")
        extrusion.NodeID = f"{contact_id.replace('-', '_')}_surface"
        extrusion.NodeRole = "contact"
        extrusion.ContactID = contact_id
        _apply_material(extrusion, None)

    pad.addProperty("App::PropertyString", "NodeID", "HangTen")
    pad.addProperty("App::PropertyString", "NodeRole", "HangTen")
    pad.NodeID = "lattice_body_surface"
    pad.NodeRole = "body"
    # The shared material is declared once, on the body node; the contacts carry
    # the same MaterialName and inherit the embedded texture at build time.
    _apply_material(pad, texture_source)

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    document.saveAs(str(DESTINATION))

    PROVENANCE.write_text(
        json.dumps(
            {
                "package": PACKAGE,
                "boardID": board["id"],
                "reference": REFERENCE_PATH,
                "referenceCommit": REFERENCE_COMMIT,
                "referenceSHA256": reference_digest,
                "referenceTexture": texture_member,
                "referenceTextureSHA256": texture_digest,
                "method": "ordered end-cap boundary loop; native (x, y, z) = (X, -Z, Y)",
                "publishedFacts": {
                    "source": f"Hangboards/{PACKAGE}/board.json",
                    "dimensions": board["dimensions"],
                    "gripDepthsMM": GRIP_DEPTH_MM,
                },
                "measuredMM": {key: round(value, 4) for key, value in measured.items()},
                "reductionToleranceMM": REDUCTION_TOLERANCE_MM,
                "achievedMaxDeviationMM": round(deviation, 4),
                "authoredVertexCount": len(vertices),
                "measuredVertexCount": len(outline),
                "contactBandDepthSpansMM": depth_spans,
                "notes": (
                    "Measured approximation of an approved display mesh. Not recovered "
                    "manufacturing geometry. Contact regions are native SubShapeBinder "
                    "runs of the profile sketch extruded along X, so they follow profile "
                    "dimension edits."
                ),
            },
            indent=1,
        )
        + "\n"
    )
    print(f"authored {DESTINATION} ({DESTINATION.stat().st_size} bytes)")
    print(f"measured {len(outline)} -> authored {len(vertices)} vertices, max deviation {deviation:.4f} mm")
    for contact_id, span in sorted(depth_spans.items()):
        if abs(span - GRIP_DEPTH_MM[contact_id]) > 0.1:
            raise ValueError(f"{contact_id} authored depth {span} disagrees with published {GRIP_DEPTH_MM[contact_id]}")
    print(f"authored contact depths mm: {depth_spans} (published {GRIP_DEPTH_MM})")
    print(f"pad volume mm^3: {pad.Shape.Volume:.1f} bbox: {pad.Shape.BoundBox}")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
