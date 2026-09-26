"""The one shared Hang Ten board build command: FCStd -> runtime asset set.

Run it with FreeCAD's own interpreter, which is the pinned toolchain:

    HANGTEN_CAD_PYTHONPATH=<extra site dir> \\
      /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \\
      Tools/HangboardCAD/compile_board.py --package <package-directory>

The board metadata comes from the source itself: the document-level
``HangTenBoardManifest`` property plus ``HangTenBoardID`` (read with
``hangboard_packages.cad_source``). ``--board <path>`` overrides it with an explicit JSON
file (used by the guard tests); without it the source must carry the manifest.
The compiler never writes ``board.json``: for a CAD-backed package that file is
generated from the manifest at build time (package validation and app staging)
and is not kept in the repository.

Stages, in order:

1. Validate the board metadata and the source archive (``cad_source.inspect_archive``).
2. Reopen and recompute the source document without modifying its bytes.
3. Extract the bound components and semantic regions.
4. Tessellate with the document's pinned quality setting.
5. Preserve normals, seams, and the declared material set.
6. Write a conforming USDZ directly.
7. Reopen the exported asset.
8. Derive the descriptor from the reopened bytes and node vertices.
9. Validate the complete staged package.
10. Publish the asset and descriptor set.

Nothing here reads a previous runtime asset: existing USDZ files are regression
references only, and ``--check`` never writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
# OpenUSD and any other pinned extras are provided out of band to FreeCAD's
# interpreter, which does not inherit PYTHONPATH.
sys.path[:0] = [
    part
    for part in os.environ.get("HANGTEN_CAD_PYTHONPATH", "").split(os.pathsep)
    if part
]
for _path in (
    Path(__file__).resolve().parent,
    REPOSITORY / "Tools" / "HangboardModels",
):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# Puts Tools/HangboardPackages/src on sys.path (host python3 and freecadcmd).
import use_hangboard_packages  # noqa: E402,F401
from hangboard_packages import cad_source  # noqa: E402

import contract  # noqa: E402
import usdz_writer  # noqa: E402
from contact_model_descriptor import (  # noqa: E402
    NodeBinding,
    compile_descriptor,
    compile_reusable_descriptor,
)

SOURCE_KIND_NATIVE = "native-parametric-measured-profile"
SOURCE_KIND_FACETED = "faceted-import"
DOCUMENT_PROPERTIES = (
    "HangTenBoardID",
    "HangTenPresentationID",
    "HangTenSchemaVersion",
    "HangTenSourceKind",
    "HangTenCoordinateFrame",
    "HangTenTessellationDeflection",
)
CREASE_DEGREES = 35.0
# Optional document property (App::PropertyBool). When true, the partition also
# claims chord triangles of curved region faces; see _partition_body_triangles.
# Opt-in so boards compiled before it existed keep byte-identical output.
CURVED_REGION_PARTITION = "HangTenCurvedRegionPartition"


class BuildError(RuntimeError):
    """A source, export, or package invariant failed."""


def _display(path: Path) -> str:
    """Report a path relative to the repository when it is inside it."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPOSITORY).as_posix()
    except ValueError:
        return str(resolved)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _open_source(path: Path):
    import FreeCAD as App

    return App.openDocument(str(path))


def _document_properties(document) -> dict:
    for name in DOCUMENT_PROPERTIES:
        if name not in document.PropertiesList:
            raise BuildError(f"source document is missing required property {name}")
    return {name: document.getPropertyByName(name) for name in DOCUMENT_PROPERTIES}


def _bound_objects(document) -> list:
    return [
        obj
        for obj in document.Objects
        if "NodeID" in obj.PropertiesList and getattr(obj, "NodeID", "")
    ]


def _source_meshes(document) -> dict:
    """Raw source meshes stored beside faceted-import nodes.

    A faceted import is an approved display mesh. Rebuilding it through a Part
    shape and re-tessellating introduces slivers and T-junction cracks at curved
    seats, so when the author stores the mesh as a ``<NodeID>_source``
    ``Mesh::Feature`` it is shipped as-is: same triangles as the approved asset,
    no extra geometry.
    """
    meshes: dict = {}
    for obj in document.Objects:
        if obj.TypeId != "Mesh::Feature":
            continue
        name = obj.Name
        if not name.endswith("_source"):
            continue
        node_id = name[: -len("_source")]
        points = list(obj.Mesh.Topology[0])
        facets = list(obj.Mesh.Topology[1])
        if not points or not facets:
            continue
        placement = getattr(obj, "Placement", None)
        if placement is not None:
            points = [placement.multVec(point) for point in points]
        meshes[node_id] = (points, facets)
    return meshes


def _node_specification(obj, version: int) -> dict:
    role = getattr(obj, "NodeRole", "")
    if role not in {"body", "contact", "attachment"}:
        raise BuildError(f"{obj.Name} has an invalid NodeRole {role!r}")
    spec = {"id": obj.NodeID, "role": role}
    if role == "contact":
        # The binding key is fixed by the schema: v2-or-later sources use
        # "slot", v1 sources use "contact". Resolve it once here so the slot
        # inventory, outline reader, and depth validator all read the same key.
        binding_key = "slot" if version >= 2 else "contact"
        property_name = "ContactSlotID" if "ContactSlotID" in obj.PropertiesList else "ContactID"
        # Fallback to the Label if the binding property is missing or empty
        # (FreeCAD sometimes fails to persist dynamic properties added via
        # Python).
        value = getattr(obj, property_name, "") or getattr(obj, "Label", "")
        if not value:
            raise BuildError(f"{obj.Name} is a contact node without an explicit binding")
        spec[binding_key] = value
    return spec


def _hold_polygons(contact_objects, version: int, property_name: str) -> dict:
    """Read a CAD-authored front-plane hold polygon property.

    ``HangTenHoldOutline`` / ``HangTenHoldFloorOutline`` are JSON arrays of
    ``[x, z]`` native-millimetre points in the source document: the CAD is the
    source of truth for hold geometry. Convert to the runtime front-plane space
    (metres) the descriptor normalizes against. A contact without a property is
    omitted.
    """
    outlines: dict[str, tuple] = {}
    for obj in contact_objects:
        if property_name not in obj.PropertiesList:
            continue
        raw = str(getattr(obj, property_name, "")).strip()
        if not raw:
            continue
        key = getattr(obj, "ContactID", "") if version == 1 else getattr(obj, "ContactSlotID", "")
        if not key:
            raise BuildError(f"{obj.Name} declares {property_name} without a contact binding")
        try:
            points = json.loads(raw)
        except json.JSONDecodeError as error:
            raise BuildError(f"{obj.Name} {property_name} is not valid JSON: {error}") from error
        if not isinstance(points, list) or len(points) < 3:
            raise BuildError(f"{obj.Name} {property_name} needs at least three points")
        try:
            outlines[key] = tuple(
                (float(point[0]) / 1000.0, float(point[1]) / 1000.0) for point in points
            )
        except (TypeError, IndexError, ValueError) as error:
            raise BuildError(f"{obj.Name} {property_name} points must be [x, z] pairs") from error
    return outlines



def _material_registry(objects, source: Path, staging: Path) -> dict:
    """No-op: committed USDZ models ship without materials.

    MaterialName and other material properties on FreeCAD objects are ignored.
    All meshes are exported unbound so the renderer uses its default appearance.
    """
    return {}


def _crease_normals(points, triangles, crease_degrees: float):
    """Split a vertex only where the surface actually creases.

    OCCT tessellation returns positions without normals. Averaging every
    incident face normal would round off real edges; emitting only face normals
    would facet genuinely smooth regions. Incident faces are therefore clustered
    by angle and one output vertex is emitted per (position, cluster).
    """
    import FreeCAD as App

    limit = math.cos(math.radians(crease_degrees))
    face_normals = []
    incident: dict[int, list[int]] = {}
    for face_index, triangle in enumerate(triangles):
        a, b, c = (points[index] for index in triangle)
        normal = (b - a).cross(c - a)
        if normal.Length > 1e-12:
            normal.normalize()
        else:
            normal = App.Vector(0.0, 0.0, 1.0)
        face_normals.append(normal)
        for index in triangle:
            incident.setdefault(index, []).append(face_index)

    clusters: dict[int, list] = {}
    for index, faces in incident.items():
        grouped: list[list[int]] = []
        for face_index in faces:
            normal = face_normals[face_index]
            for group in grouped:
                if normal.dot(face_normals[group[0]]) >= limit:
                    group.append(face_index)
                    break
            else:
                grouped.append([face_index])
        clusters[index] = []
        for group in grouped:
            mean = App.Vector(0.0, 0.0, 0.0)
            for face_index in group:
                mean = mean + face_normals[face_index]
            if mean.Length > 1e-12:
                mean.normalize()
            clusters[index].append((mean, group))

    out_points: list = []
    out_normals: list = []
    out_triangles: list = []
    remap: dict[tuple[int, int], int] = {}
    for face_index, triangle in enumerate(triangles):
        normal = face_normals[face_index]
        corners = []
        for index in triangle:
            chosen = 0
            best = -2.0
            for position, (mean, _group) in enumerate(clusters[index]):
                score = mean.dot(normal)
                if score > best:
                    best, chosen = score, position
            if best < limit and len(clusters[index]) > 1:
                # No cluster matches this face: keep the face normal itself so
                # the crease stays sharp instead of blending across it.
                mean = normal
                clusters[index].append((mean, []))
                chosen = len(clusters[index]) - 1
            key = (index, chosen)
            if key not in remap:
                remap[key] = len(out_points)
                out_points.append(points[index])
                out_normals.append(clusters[index][chosen][0])
            corners.append(remap[key])
        out_triangles.append(tuple(corners))
    return out_points, out_triangles, out_normals


def _curved_facet_on_region(shape, corners, centroid, deflection: float, on_surface: float) -> bool:
    """True when a chord triangle of a curved face belongs to ``shape``'s surface."""
    import Part

    normal = (corners[1] - corners[0]).cross(corners[2] - corners[0])
    if normal.Length < 1e-12:
        return False
    normal.normalize()
    for corner in corners:
        if shape.distToShape(Part.Vertex(corner))[0] >= on_surface:
            return False
    distance, _pairs, supports = shape.distToShape(Part.Vertex(centroid))
    if distance > deflection:
        return False
    kind, index, parameters = supports[0][0], supports[0][1], supports[0][2]
    if kind != "Face":
        return False
    surface_normal = shape.Faces[index].normalAt(*parameters)
    # Region shells carry no reliable orientation, so compare lines, not senses.
    return abs(surface_normal.dot(normal)) >= math.cos(math.radians(CREASE_DEGREES))


def _partition_body_triangles(
    body_shape,
    contact_shapes,
    deflection: float,
    surface_tol: float = 1e-4,
    curved_regions: bool = False,
    skip_mesh_shells: bool = False,
):
    """Assign each body triangle to the contact region it belongs to.

    The approved runtime contract partitions the board surface: the body node
    carries the surface *minus* the contact regions, and each contact node
    carries its region. Emitting both over the same surface instead would
    duplicate coplanar geometry and z-fight.

    A body triangle is assigned to a contact when its centroid lies on that
    contact region's surface. The regions are built from the source document's
    own sketch edges, so the assignment follows any profile edit; no face or
    triangle index is used.

    ``surface_tol`` is the max centroid-to-contact distance (mm). Native
    parametric contacts share the body surface so 1e-4 is enough; faceted
    imports carry separate shells that sit a fraction of a millimetre off the
    body and need a looser gate or the body lips z-fight with the contacts.
    When multiple contacts fall inside the tolerance, the nearest wins.

    A triangle tessellated from a *curved* face (an arc or a B-spline run of the
    profile) has its vertices on the surface but its centroid inside the chord,
    up to the tessellation deflection away, so the centroid rule leaves it in the
    body and the region's own surface then duplicates it. With
    ``curved_regions`` (the source's ``HangTenCurvedRegionPartition``), such a
    triangle is also assigned when all three vertices lie on the region surface,
    the centroid is within the deflection, and the triangle lies along the
    surface there, so a triangle of an adjacent face (an end cap whose vertices
    happen to lie on the region's boundary edge) is never claimed.

    ``skip_mesh_shells`` (faceted imports only) skips a contact with more than
    200 faces: an imported mesh shell never lies on the body at the native
    tolerance, and testing it is too slow. A native source can have a hold with
    hundreds of planar faces that must still be partitioned.
    """
    import Part

    points, facets = body_shape.tessellate(deflection)
    assignment: dict[int, int] = {}
    best_distance: dict[int, float] = {}
    for position, shape in enumerate(contact_shapes):
        # Dense mesh contacts (faceted imports) almost never lie on the body
        # surface at the native 1e-4 tolerance, but distToShape against thousands
        # of faces is O(body_tris × contact_faces) and can hang the compile.
        # Skip the exact test when the contact is clearly a heavy mesh shell.
        # Only for faceted imports: native polyhedral holds (Compact II, MXEdge
        # Small, Captain Fingerfood Pocket) have hundreds of planar faces.
        if skip_mesh_shells:
            try:
                face_count = len(shape.Faces)
            except Exception:
                face_count = 0
            if face_count > 200 and surface_tol <= 1e-3:
                continue
        box = shape.BoundBox
        margin = max(0.25, surface_tol)
        for index, facet in enumerate(facets):
            centroid = (points[facet[0]] + points[facet[1]] + points[facet[2]]) / 3.0
            if not (
                box.XMin - margin <= centroid.x <= box.XMax + margin
                and box.YMin - margin <= centroid.y <= box.YMax + margin
                and box.ZMin - margin <= centroid.z <= box.ZMax + margin
            ):
                continue
            distance = shape.distToShape(Part.Vertex(centroid))[0]
            claimed = distance < surface_tol
            if not claimed and curved_regions:
                claimed = _curved_facet_on_region(
                    shape, [points[corner] for corner in facet], centroid, deflection, surface_tol
                )
            if not claimed:
                continue
            prior = best_distance.get(index)
            if prior is None or distance < prior:
                assignment[index] = position
                best_distance[index] = distance
    return points, facets, assignment


def _subset_mesh(points, facets, indices):
    """Rebuild a compact vertex/triangle list from selected triangles."""
    remap: dict[int, int] = {}
    out_points = []
    out_triangles = []
    for index in indices:
        corners = []
        for corner in facets[index]:
            if corner not in remap:
                remap[corner] = len(out_points)
                out_points.append(points[corner])
            corners.append(remap[corner])
        out_triangles.append(tuple(corners))
    return out_points, out_triangles


def _triangle_area(points, facets, indices) -> float:
    total = 0.0
    for index in indices:
        a, b, c = (points[corner] for corner in facets[index])
        total += float((b - a).cross(c - a).Length) / 2.0
    return total


def _build_mesh(node_id, points, triangles, material, model_box):
    points, triangles, normals = _crease_normals(points, triangles, CREASE_DEGREES)
    return usdz_writer.Mesh(
        node_id=node_id,
        points_mm=[(p.x, p.y, p.z) for p in points],
        triangles=triangles,
        material=material,
        uvs=_planar_uvs(points, model_box),
        normals_mm=[(n.x, n.y, n.z) for n in normals],
    )


def _validate_partition(body_points, body_facets, triangles_by_node, region_surface_areas):
    """Assert no region claims more body area than the surface it exports.

    Each region ships its own tessellated CAD surface, and the body node carries
    the body surface *minus* the triangles that surface claims. If a region were
    assigned more body triangles than its own exported surface covers, removing
    them would leave a gap the region cannot fill. The region's own tessellation
    is the yardstick, so curved native surfaces (fillets, ruled lofts) are
    measured on the same footing as the body, unlike an analytic area.

    Both meshes tessellate the same source at the same deflection, so the only
    allowance needed is floating-point and tessellation error.
    """
    total = _triangle_area(body_points, body_facets, range(len(body_facets)))
    tolerance = max(1e-6, 1e-6 * total)
    for node_id, region_area in region_surface_areas.items():
        claimed = _triangle_area(
            body_points, body_facets, triangles_by_node.get(node_id, ())
        )
        if claimed - region_area > tolerance:
            raise BuildError(
                f"{node_id} claims {claimed:.4f} mm^2 of body surface but its own "
                f"exported surface is only {region_area:.4f} mm^2; the region leaves "
                f"a gap larger than {tolerance:.6f} mm^2"
            )


def _declared_depths(board, version: int) -> dict:
    """Published grip depth keyed by region identity (contact id or slot id).

    v1 names a physical contact directly; v2 names a reusable slot that each
    presentation instance maps to a physical contact. Every instance of a slot
    must agree on the published depth, or the slot is ambiguous and the build
    must fail rather than silently pick one.
    """
    declared: dict[str, float] = {}
    if version == 1:
        for contact in board.get("contacts", []):
            span = ((contact.get("depth") or {}).get("range") or {})
            low, high = span.get("minimum"), span.get("maximum")
            if isinstance(low, (int, float)) and isinstance(high, (int, float)) and low == high:
                declared[contact["id"]] = float(low)
        return declared
    by_id = {contact["id"]: contact for contact in board.get("contacts", [])}
    for presentation in board.get("presentations", []):
        for instance in presentation.get("media", {}).get("instances", []):
            for slot, contact_id in instance.get("contactIDsBySlotID", {}).items():
                span = ((by_id.get(contact_id) or {}).get("depth") or {}).get("range") or {}
                low, high = span.get("minimum"), span.get("maximum")
                if isinstance(low, (int, float)) and isinstance(high, (int, float)) and low == high:
                    if slot in declared and abs(declared[slot] - low) > 1e-6:
                        raise BuildError(f"slot {slot} declares conflicting published depths")
                    declared[slot] = float(low)
    return declared


def _validate_published_depths(contact_objects, declared, version: int, deflection) -> dict:
    """Check each authored region against the grip depth the board declares.

    The authored region's extent along the native depth axis must agree with the
    published depth; this is what catches a region that silently re-bound to
    another surface. Attachments have no published grip depth and are skipped.
    """
    measured = {}
    for obj in contact_objects:
        key = getattr(obj, "ContactID", "") if version == 1 else getattr(obj, "ContactSlotID", "")
        measured[key] = round(float(obj.Shape.BoundBox.YLength), 3)
        if key not in declared:
            continue
        tolerance = max(0.25, 3.0 * deflection)
        if abs(measured[key] - declared[key]) > tolerance:
            raise BuildError(
                f"{key} region depth {measured[key]:.3f} mm disagrees with the "
                f"published depth {declared[key]:.3f} mm (tolerance {tolerance:.3f} mm); "
                "the region has probably bound to the wrong surface"
            )
    return measured


def _planar_uvs(points, bounds) -> list[tuple[float, float]]:
    """Front-view planar projection, a declared display choice (not source data)."""
    min_x, _, min_z, max_x, _, max_z = bounds
    span_x = max(max_x - min_x, 1e-9)
    span_z = max(max_z - min_z, 1e-9)
    return [
        ((point.x - min_x) / span_x, (point.z - min_z) / span_z) for point in points
    ]


def load_board(source: Path, board_path: Path | None) -> tuple[dict, str]:
    """Board metadata and a label for where it came from.

    An explicit ``board_path`` wins; otherwise the source's own manifest is the
    single source of truth.
    """
    if board_path is not None:
        return json.loads(Path(board_path).read_text()), _display(Path(board_path))
    try:
        board = cad_source.load_board(source)
        return board, f"{_display(source)}#{cad_source.MANIFEST_PROPERTY}"
    except cad_source.ManifestError as error:
        raise BuildError(str(error)) from error


def build(
    package: str,
    source: Path,
    board_path: Path | None,
    out_dir: Path,
    publish: bool,
    allow_faceted_import: bool = False,
) -> dict:
    board, board_origin = load_board(source, board_path)
    if not isinstance(board, dict) or board.get("schemaVersion") != 3:
        raise BuildError("board.json must be schema version 3")
    presentations = [item.get("id") for item in board.get("presentations", [])]
    if not presentations:
        raise BuildError("board.json declares no presentations")
    contacts = [item.get("id") for item in board.get("contacts", [])]
    if not contacts or any(not isinstance(value, str) or not value for value in contacts):
        raise BuildError("board.json declares no usable contacts")

    print(f"[1/10] validating {source.name}")
    source_digest = _digest(source)
    cad_source.inspect_archive(source)

    print("[2/10] reopening and recomputing the source document")
    document = _open_source(source)
    if document is None:
        raise BuildError("FreeCAD could not open the source document")
    document.recompute()
    # A feature tree that fails to recompute leaves stale shapes in the file.
    # Without this check the build would happily tessellate the stale body and
    # freshly recomputed contact bands and publish the inconsistent mix, because
    # a failed recompute is reported through object state, not an exception.
    stale = []
    for obj in document.Objects:
        state = set(obj.State)
        failed = state & {"Invalid", "Error", "Touched", "Recompute"}
        if failed:
            stale.append(f"{obj.Name}({obj.TypeId})={sorted(state)}")
    if stale:
        raise BuildError("source document did not recompute cleanly: " + "; ".join(stale))
    if _digest(source) != source_digest:
        raise BuildError("reopening the source modified its bytes")
    properties = _document_properties(document)
    if properties["HangTenBoardID"] != board["id"]:
        raise BuildError("source HangTenBoardID does not match board.json id")
    if properties["HangTenPresentationID"] not in presentations:
        raise BuildError("source HangTenPresentationID is not a declared presentation")
    if properties["HangTenCoordinateFrame"] != "freecad-mm-z-up-front-negative-y":
        raise BuildError("source declares an unexpected coordinate frame")
    if properties["HangTenSourceKind"] not in {SOURCE_KIND_NATIVE, SOURCE_KIND_FACETED}:
        raise BuildError("source declares an unexpected HangTenSourceKind")
    if properties["HangTenSourceKind"] == SOURCE_KIND_FACETED and not allow_faceted_import:
        raise BuildError(
            "source is labelled faceted-import. Such a document must not be published as if it "
            "carried native parametric history; re-run with --allow-faceted-import to "
            "acknowledge that explicitly."
        )
    deflection = float(properties["HangTenTessellationDeflection"])
    if not (0.0 < deflection <= 1.0):
        raise BuildError("source tessellation deflection is out of range")

    print("[3/10] extracting bound components and semantic regions")
    objects = _bound_objects(document)
    if not objects:
        raise BuildError("source declares no bound nodes")
    version = int(properties["HangTenSchemaVersion"])
    specifications = [_node_specification(obj, version) for obj in objects]
    slots: list[str] = []
    if version >= 2:
        slots = sorted(
            {
                spec["slot"]
                for spec in specifications
                if spec["role"] == "contact"
            }
        )
    contract.validate_bindings(specifications, board, version, slots)

    out_dir.mkdir(parents=True, exist_ok=True)
    print("[4/10] tessellating with pinned quality")
    body_object = next((obj for obj in objects if obj.NodeRole == "body"), None)
    if body_object is None:
        raise BuildError("source declares no body node")
    contact_objects = [obj for obj in objects if obj.NodeRole == "contact"]
    attachment_objects = [obj for obj in objects if obj.NodeRole == "attachment"]
    # Contacts and attachments are both regions of the body surface; the
    # partition assigns each body triangle to at most one of them, so a
    # non-pickable cord aperture is exported exactly like a grip region.
    region_objects = contact_objects + attachment_objects
    model_box = None
    for obj in objects:
        box = obj.Shape.BoundBox
        if model_box is None:
            model_box = [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax]
        else:
            model_box = [
                min(model_box[0], box.XMin),
                min(model_box[1], box.YMin),
                min(model_box[2], box.ZMin),
                max(model_box[3], box.XMax),
                max(model_box[4], box.YMax),
                max(model_box[5], box.ZMax),
            ]

    print("[5/10] partitioning the surface and preserving normals and materials")
    staging = Path(tempfile.mkdtemp(prefix=".hangten-build-", dir=str(out_dir)))
    try:
        materials = _material_registry(objects, source, staging)
        faceted = properties["HangTenSourceKind"] == SOURCE_KIND_FACETED
        source_meshes = _source_meshes(document)
        if faceted and body_object.NodeID in source_meshes:
            body_points, body_facets = source_meshes[body_object.NodeID]
            assignment = {}
            print("      faceted-import body: shipping the stored source mesh")
        else:
            # Faceted imports keep a tight surface_tol: a looser gate removes body
            # lip triangles the contact shells do not fully cover, opening black
            # holes at rail ends. Overlap z-fighting is handled in the author by
            # nudging contact shells slightly toward the front.
            body_points, body_facets, assignment = _partition_body_triangles(
                body_object.Shape,
                [obj.Shape for obj in region_objects],
                deflection,
                curved_regions=bool(
                    CURVED_REGION_PARTITION in document.PropertiesList
                    and document.getPropertyByName(CURVED_REGION_PARTITION)
                ),
                skip_mesh_shells=faceted,
            )
        body_indices = [index for index in range(len(body_facets)) if index not in assignment]

        meshes = [
            _build_mesh(
                body_object.NodeID,
                *_subset_mesh(body_points, body_facets, body_indices),
                material=materials.get(getattr(body_object, "MaterialName", "")),
                model_box=model_box,
            )
        ]
        print(f"      {body_object.NodeID}: {len(body_indices)} triangles, role={body_object.NodeRole}")

        region_surface_areas = {}
        for obj in region_objects:
            # Each region object's own CAD surface is its exported mesh — the CAD is
            # the source of truth for hold geometry. The body was partitioned around
            # the same surface, so the two never overlap.
            if faceted and obj.NodeID in source_meshes:
                points, facets = source_meshes[obj.NodeID]
            else:
                points, facets = obj.Shape.tessellate(deflection)
            if not facets:
                raise BuildError(f"{obj.NodeID} has no surface")
            region_surface_areas[obj.NodeID] = _triangle_area(
                points, facets, range(len(facets))
            )
            meshes.append(
                _build_mesh(
                    obj.NodeID,
                    points,
                    facets,
                    material=materials.get(getattr(obj, "MaterialName", "")),
                    model_box=model_box,
                )
            )
            print(f"      {obj.NodeID}: {len(facets)} triangles, role={obj.NodeRole}")

        # Every region ships its own CAD surface; a region may claim no body
        # triangles (a proud patch), but it must not claim more body area than it
        # exports, or the body partition would leave a gap it cannot fill.
        _validate_partition(
            body_points,
            body_facets,
            {body_object.NodeID: body_indices, **{
                obj.NodeID: [i for i, owner in assignment.items() if owner == index]
                for index, obj in enumerate(region_objects)
            }},
            region_surface_areas,
        )
        if properties["HangTenSourceKind"] == SOURCE_KIND_FACETED:
            # Faceted imports ship approved display meshes. Their Y AABB is the
            # hold volume, not the published grip depth (which lives in
            # board.json for training UI). The native AABB==depth gate does not
            # apply; --allow-faceted-import already acknowledges this path.
            measured_depths = {
                (
                    getattr(obj, "ContactID", "")
                    if version == 1
                    else getattr(obj, "ContactSlotID", "")
                ): round(float(obj.Shape.BoundBox.YLength), 3)
                for obj in contact_objects
            }
            print(
                "      skipping published-depth AABB gate for faceted-import "
                f"(measured Y spans: {measured_depths})"
            )
        else:
            measured_depths = _validate_published_depths(
                contact_objects, _declared_depths(board, version), version, deflection
            )

        print("[6/10] writing the USDZ directly")
        asset = staging / "primary.usdz"
        usdz_writer.write_usdz(asset, meshes)

        print("[7/10] reopening the exported asset")
        reopened = usdz_writer.read_usdz(asset)
        if set(reopened["nodes"]) != {mesh.node_id for mesh in meshes}:
            raise BuildError("reopened asset node inventory does not match the source")

        print("[8/10] deriving the descriptor from the exported bytes")
        model_bytes = asset.read_bytes()
        # The CAD source owns hold geometry: a contact object may carry its
        # front-plane hold outline as native-millimetre XZ points. When present
        # it defines the descriptor region, so the app never has to derive a
        # hold from the exported mesh silhouette.
        outlines = _hold_polygons(contact_objects, version, "HangTenHoldOutline")
        if version >= 2:
            descriptor = compile_reusable_descriptor(
                model_bytes,
                [
                    __import__(
                        "contact_model_descriptor"
                    ).SlotNodeBinding(spec["id"], spec["role"], spec.get("slot"))
                    for spec in specifications
                ],
                {node_id: reopened["nodes"][node_id]["points_m"] for node_id in reopened["nodes"]},
                frozenset(slots),
                outlines,
            )
        else:
            descriptor = compile_descriptor(
                model_bytes,
                [
                    NodeBinding(spec["id"], spec["role"], spec.get("contact"))
                    for spec in specifications
                ],
                {node_id: reopened["nodes"][node_id]["points_m"] for node_id in reopened["nodes"]},
                frozenset(contacts),
                outlines,
            )
        descriptor_json = descriptor.to_json()
        if descriptor_json["modelSHA256"] != hashlib.sha256(model_bytes).hexdigest():
            raise BuildError("descriptor hash does not match the exported bytes")

        print("[9/10] validating the staged package")
        descriptor_path = staging / "primary.model.json"
        descriptor_path.write_text(json.dumps(descriptor_json, indent=2, sort_keys=False) + "\n")
        json.loads(descriptor_path.read_text())
        usdz_writer.read_usdz(asset)

        result = {
            "package": package,
            "source": _display(source),
            "board": board_origin,
            "sourceSHA256": source_digest,
            "sourceUnchanged": _digest(source) == source_digest,
            "schemaVersion": version,
            "sourceKind": properties["HangTenSourceKind"],
            "tessellationDeflectionMM": deflection,
            "nodes": sorted(reopened["nodes"]),
            "triangles": sum(len(node["triangles"]) for node in reopened["nodes"].values()),
            "modelSHA256": descriptor_json["modelSHA256"],
            "assetBytes": len(model_bytes),
            "contacts": sorted(descriptor_json.get("contacts", descriptor_json.get("contactSlots", {}))),
            "measuredRegionDepthsMM": measured_depths,
        }

        if not publish:
            result["published"] = False
            result["staging"] = str(staging)
            print("[10/10] check-only run; nothing published")
            return result

        print("[10/10] publishing the asset and descriptor set")
        assets = out_dir
        assets.mkdir(parents=True, exist_ok=True)
        asset_target = assets / "primary.usdz"
        descriptor_target = assets / "primary.model.json"
        descriptor_temp = assets / f".{descriptor_target.name}.staged"
        asset_temp = assets / f".{asset_target.name}.staged"
        shutil.copyfile(descriptor_path, descriptor_temp)
        shutil.copyfile(asset, asset_temp)
        # Two files cannot be replaced in one atomic step. The descriptor is
        # hash-bound to the asset and is moved last, so an interruption between
        # the two moves leaves a detectable mismatch rather than a silently
        # stale pairing; the delivered pair is re-verified immediately after.
        os.replace(asset_temp, asset_target)
        os.replace(descriptor_temp, descriptor_target)
        delivered = json.loads(descriptor_target.read_text())
        delivered_digest = _digest(asset_target)
        if delivered.get("modelSHA256") != delivered_digest:
            raise BuildError(
                "published descriptor does not match the published asset; the pair is "
                "inconsistent and must be rebuilt"
            )
        result["published"] = True
        result["asset"] = _display(asset_target)
        result["descriptor"] = _display(descriptor_target)
        result["assetSHA256"] = _digest(asset_target)
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, help="Hangboards/<package-directory>")
    parser.add_argument("--source", help="defaults to Hangboards/<package>/<package>.FCStd")
    parser.add_argument(
        "--board",
        help="explicit board metadata JSON; defaults to the source's HangTenBoardManifest",
    )
    parser.add_argument("--assets", help="defaults to Hangboards/<package>/assets")
    parser.add_argument("--check", action="store_true", help="validate and stage only")
    parser.add_argument(
        "--allow-faceted-import",
        action="store_true",
        help="publish a document explicitly labelled faceted-import",
    )
    parser.add_argument("--report", help="write the JSON build report here")
    arguments = parser.parse_args(argv)

    package = arguments.package
    source = (Path(arguments.source) if arguments.source
              else REPOSITORY / "Hangboards" / package / f"{package}.FCStd")
    assets = Path(arguments.assets) if arguments.assets else REPOSITORY / "Hangboards" / package / "assets"
    if not source.is_file():
        raise BuildError(f"missing required input: {source}")
    board_path = Path(arguments.board) if arguments.board else None
    if board_path is None:
        # has_manifest runs the archive contract (cad_source.inspect_archive)
        # before reading Document.xml, so a corrupt source is a BuildError.
        try:
            embedded = cad_source.has_manifest(source)
        except cad_source.ManifestError as error:
            raise BuildError(str(error)) from error
        if not embedded:
            raise BuildError(
                f"{_display(source)} carries no {cad_source.MANIFEST_PROPERTY}; embed "
                "one with Tools/HangboardCAD/set_board_manifest.py or pass --board"
            )
    if board_path is not None and not board_path.is_file():
        raise BuildError(f"missing required input: {board_path}")

    result = build(
        package,
        source,
        board_path,
        assets,
        publish=not arguments.check,
        allow_faceted_import=arguments.allow_faceted_import,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if arguments.report:
        Path(arguments.report).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as error:
        print(f"BUILD FAILED: {error}", file=sys.stderr, flush=True)
        raise SystemExit(1)
