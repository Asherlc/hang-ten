"""The one shared Hang Ten board build command: FCStd + board.json -> runtime set.

Run it with FreeCAD's own interpreter, which is the pinned toolchain:

    HANGTEN_CAD_PYTHONPATH=<extra site dir> \\
      /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \\
      Tools/HangboardCAD/compile_board.py --package <package-directory>

Stages, in order:

1. Validate ``board.json`` and the source archive (``contract.inspect_archive``).
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


class BuildError(RuntimeError):
    """A source, export, or package invariant failed."""


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


def _node_specification(obj) -> dict:
    role = getattr(obj, "NodeRole", "")
    if role not in {"body", "contact", "attachment"}:
        raise BuildError(f"{obj.Name} has an invalid NodeRole {role!r}")
    spec = {"id": obj.NodeID, "role": role}
    if role == "contact":
        key = "ContactSlotID" if "ContactSlotID" in obj.PropertiesList else "ContactID"
        value = getattr(obj, key, "")
        if not value:
            raise BuildError(f"{obj.Name} is a contact node without an explicit binding")
        spec["slot" if key == "ContactSlotID" else "contact"] = value
    return spec


def _embedded_texture(document, source: Path, staging: Path, member: str) -> tuple[str, Path]:
    """Extract an FCStd-included file and stage it under ``textures/``."""
    import zipfile

    basename = os.path.basename(member)
    if not basename or contract.safe_member(basename) != basename:
        raise BuildError(f"unsafe embedded texture member: {member!r}")
    with zipfile.ZipFile(source) as archive:
        if basename not in archive.namelist():
            raise BuildError(f"source declares texture {basename} but does not contain it")
        data = archive.read(basename)
    destination = staging / "textures" / basename
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return f"textures/{basename}", destination


def _material_registry(objects, document, source: Path, staging: Path) -> dict:
    """Collect one material definition per MaterialName across all bound nodes.

    A node without ``TextureFile`` inherits the texture declared by another node
    using the same material name, so a shared material is declared once. Any
    genuine disagreement between nodes is an error rather than a silent pick.
    """
    declared: dict[str, dict] = {}
    for obj in objects:
        name = str(getattr(obj, "MaterialName", ""))
        if not name:
            raise BuildError(f"{obj.Name} is missing MaterialName")
        base_color = (0.8, 0.8, 0.8)
        raw = str(getattr(obj, "BaseColor", ""))
        if raw:
            parts = [float(part) for part in raw.split(",")]
            if len(parts) != 3:
                raise BuildError(f"{obj.Name} BaseColor must be three comma-separated floats")
            base_color = (parts[0], parts[1], parts[2])
        entry = {
            "base_color": base_color,
            "roughness": float(getattr(obj, "Roughness", 0.5)),
            "metallic": float(getattr(obj, "Metallic", 0.0)),
            "texture": None,
        }
        member = str(getattr(obj, "TextureFile", "")) if "TextureFile" in obj.PropertiesList else ""
        if member:
            entry["texture"] = _embedded_texture(document, source, staging, member)
        existing = declared.get(name)
        if existing is None:
            declared[name] = entry
            continue
        for key in ("base_color", "roughness", "metallic"):
            if existing[key] != entry[key]:
                raise BuildError(f"material {name} declares conflicting {key} across nodes")
        if entry["texture"] is not None:
            if existing["texture"] is not None and existing["texture"] != entry["texture"]:
                raise BuildError(f"material {name} declares conflicting textures across nodes")
            existing["texture"] = entry["texture"]

    registry = {}
    for name, entry in declared.items():
        archive_path, texture_path = entry["texture"] or (None, None)
        registry[name] = usdz_writer.Material(
            name=name,
            base_color=entry["base_color"],
            roughness=entry["roughness"],
            metallic=entry["metallic"],
            texture_archive_path=archive_path,
            texture_source=texture_path,
        )
    return registry


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


def _partition_body_triangles(body_shape, contact_shapes, deflection: float):
    """Assign each body triangle to the contact region it belongs to.

    The approved runtime contract partitions the board surface: the body node
    carries the surface *minus* the contact regions, and each contact node
    carries its region. Emitting both over the same surface instead would
    duplicate coplanar geometry and z-fight.

    A body triangle is assigned to a contact when its centroid lies on that
    contact region's surface. The regions are built from the source document's
    own sketch edges, so the assignment follows any profile edit; no face or
    triangle index is used.
    """
    import Part

    points, facets = body_shape.tessellate(deflection)
    assignment: dict[int, int] = {}
    for position, shape in enumerate(contact_shapes):
        box = shape.BoundBox
        margin = 0.25
        for index, facet in enumerate(facets):
            if index in assignment:
                continue
            centroid = (points[facet[0]] + points[facet[1]] + points[facet[2]]) / 3.0
            if not (
                box.XMin - margin <= centroid.x <= box.XMax + margin
                and box.YMin - margin <= centroid.y <= box.YMax + margin
                and box.ZMin - margin <= centroid.z <= box.ZMax + margin
            ):
                continue
            if shape.distToShape(Part.Vertex(centroid))[0] < 1e-4:
                assignment[index] = position
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


def _tessellate(shape, deflection: float):
    points, facets = shape.tessellate(deflection)
    triangles = [tuple(int(i) for i in facet) for facet in facets]
    if not triangles:
        raise BuildError("tessellation produced no triangles")
    return points, triangles


def _planar_uvs(points, bounds) -> list[tuple[float, float]]:
    """Front-view planar projection, a declared display choice (not source data)."""
    min_x, _, min_z, max_x, _, max_z = bounds
    span_x = max(max_x - min_x, 1e-9)
    span_z = max(max_z - min_z, 1e-9)
    return [
        ((point.x - min_x) / span_x, (point.z - min_z) / span_z) for point in points
    ]


def build(package: str, source: Path, board_path: Path, out_dir: Path, publish: bool) -> dict:
    board = json.loads(board_path.read_text())
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
    contract.inspect_archive(source)

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
    deflection = float(properties["HangTenTessellationDeflection"])
    if not (0.0 < deflection <= 1.0):
        raise BuildError("source tessellation deflection is out of range")

    print("[3/10] extracting bound components and semantic regions")
    objects = _bound_objects(document)
    if not objects:
        raise BuildError("source declares no bound nodes")
    specifications = [_node_specification(obj) for obj in objects]
    version = int(properties["HangTenSchemaVersion"])
    slots: list[str] = []
    if version == 2:
        slots = sorted(
            {
                spec["slot"]
                for spec in specifications
                if spec["role"] == "contact"
            }
        )
    contract.validate_bindings(specifications, board, version, slots)

    print("[4/10] tessellating with pinned quality")
    body_object = next((obj for obj in objects if obj.NodeRole == "body"), None)
    if body_object is None:
        raise BuildError("source declares no body node")
    contact_objects = [obj for obj in objects if obj.NodeRole == "contact"]
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
    materials = _material_registry(objects, document, source, staging)
    body_points, body_facets, assignment = _partition_body_triangles(
        body_object.Shape, [obj.Shape for obj in contact_objects], deflection
    )
    triangles_by_node: dict[str, list] = {body_object.NodeID: []}
    for obj in contact_objects:
        triangles_by_node[obj.NodeID] = []
    for index, facet in enumerate(body_facets):
        owner = assignment.get(index)
        target = (
            body_object.NodeID if owner is None else contact_objects[owner].NodeID
        )
        triangles_by_node[target].append(index)

    meshes = []
    for obj in [body_object] + contact_objects:
        indices = triangles_by_node[obj.NodeID]
        if not indices:
            raise BuildError(f"{obj.NodeID} received no surface triangles")
        points, triangles = _subset_mesh(body_points, body_facets, indices)
        points, triangles, normals = _crease_normals(points, triangles, CREASE_DEGREES)
        meshes.append(
            usdz_writer.Mesh(
                node_id=obj.NodeID,
                points_mm=[(p.x, p.y, p.z) for p in points],
                triangles=triangles,
                material=materials[obj.MaterialName],
                uvs=_planar_uvs(points, model_box),
                normals_mm=[(n.x, n.y, n.z) for n in normals],
            )
        )
        print(f"      {obj.NodeID}: {len(triangles)} triangles, role={obj.NodeRole}")

    try:
        print("[6/10] writing the USDZ directly")
        asset = staging / "primary.usdz"
        usdz_writer.write_usdz(asset, meshes)

        print("[7/10] reopening the exported asset")
        reopened = usdz_writer.read_usdz(asset)
        if set(reopened["nodes"]) != {mesh.node_id for mesh in meshes}:
            raise BuildError("reopened asset node inventory does not match the source")
        for node_id, node in reopened["nodes"].items():
            if not node["material"]:
                raise BuildError(f"{node_id} lost its material binding in the export")

        print("[8/10] deriving the descriptor from the exported bytes")
        model_bytes = asset.read_bytes()
        if version == 2:
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
            "source": str(source.relative_to(REPOSITORY)),
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
        # The descriptor is hash-bound to the asset, so it is moved last: an
        # interruption between the two moves leaves a detectable mismatch
        # rather than a silently stale pairing.
        os.replace(asset_temp, asset_target)
        os.replace(descriptor_temp, descriptor_target)
        result["published"] = True
        result["asset"] = str(asset_target.relative_to(REPOSITORY))
        result["descriptor"] = str(descriptor_target.relative_to(REPOSITORY))
        result["assetSHA256"] = _digest(asset_target)
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, help="Hangboards/<package-directory>")
    parser.add_argument("--source", help="defaults to ModelSources/<package>.FCStd")
    parser.add_argument("--board", help="defaults to Hangboards/<package>/board.json")
    parser.add_argument("--assets", help="defaults to Hangboards/<package>/assets")
    parser.add_argument("--check", action="store_true", help="validate and stage only")
    parser.add_argument("--report", help="write the JSON build report here")
    arguments = parser.parse_args(argv)

    package = arguments.package
    source = Path(arguments.source) if arguments.source else REPOSITORY / "ModelSources" / f"{package}.FCStd"
    board_path = Path(arguments.board) if arguments.board else REPOSITORY / "Hangboards" / package / "board.json"
    assets = Path(arguments.assets) if arguments.assets else REPOSITORY / "Hangboards" / package / "assets"
    for path in (source, board_path):
        if not path.is_file():
            raise BuildError(f"missing required input: {path}")

    result = build(package, source, board_path, assets, publish=not arguments.check)
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
