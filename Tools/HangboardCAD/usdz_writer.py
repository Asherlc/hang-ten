"""Direct USDZ writing for the Hang Ten CAD compiler.

The writer takes already-tessellated native geometry and produces a conforming
USDZ package, then reopens the bytes it actually wrote. It never reads a
previous runtime asset.

Coordinate conversion is applied exactly once, from the native FreeCAD frame to
the runtime frame documented in ``docs/`` and enforced by
``Tools/HangboardModels/contact_model_descriptor.py``:

    native   millimetres, +X right, +Z up, front -Y
    runtime  metres,      +X right, +Y up, front +Z
    mapping  (x, y, z) -> (x / 1000, z / 1000, -y / 1000)

Triangle winding and index order are preserved exactly as supplied; the caller
owns orientation.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdUtils, Vt

COORDINATE_FRAME = "hang-ten-board-v1"
NODE_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_METERS_PER_MILLIMETRE = 0.001


@dataclass(frozen=True)
class Material:
    """A UsdPreviewSurface material, optionally textured by an embedded image."""

    name: str
    base_color: tuple[float, float, float] = (0.8, 0.8, 0.8)
    roughness: float = 0.5
    metallic: float = 0.0
    clearcoat: float = 0.0
    clearcoat_roughness: float = 0.03
    ior: float = 1.45
    opacity: float = 1.0
    specular: float = 0.5
    texture_archive_path: str | None = None
    texture_source: Path | None = None


@dataclass(frozen=True)
class Mesh:
    """One exported node: an exact prim name plus native millimetre geometry."""

    node_id: str
    points_mm: Sequence[tuple[float, float, float]]
    triangles: Sequence[tuple[int, int, int]]
    material: Material | None = None
    uvs: Sequence[tuple[float, float]] | None = None
    normals_mm: Sequence[tuple[float, float, float]] | None = None


def runtime_point(point_mm: Sequence[float]) -> tuple[float, float, float]:
    """Convert one native millimetre point to the runtime metre frame.

    Native FreeCAD points are written unchanged (``+X`` right, ``+Z`` up, front
    ``-Y``), and the Z-up to Y-up basis change is carried by the ``/root``
    rotation, exactly as the approved Blender-sourced references do. Writing the
    rotated board frame here instead would leave the app's model-local camera
    directions interpreted in a different frame than every shipped board.
    """
    x, y, z = point_mm
    return (x * _METERS_PER_MILLIMETRE, y * _METERS_PER_MILLIMETRE, z * _METERS_PER_MILLIMETRE)


def runtime_direction(direction: Sequence[float]) -> tuple[float, float, float]:
    """Write a normal in the native frame (the ``/root`` rotation applies it)."""
    x, y, z = direction
    return (x, y, z)


def _validate(meshes: Sequence[Mesh]) -> None:
    if not meshes:
        raise ValueError("at least one mesh is required")
    seen: set[str] = set()
    for mesh in meshes:
        if not isinstance(mesh.node_id, str) or not NODE_ID.fullmatch(mesh.node_id):
            raise ValueError(f"invalid node id: {mesh.node_id!r}")
        if mesh.node_id in seen:
            raise ValueError(f"duplicate node id: {mesh.node_id}")
        seen.add(mesh.node_id)
        if mesh.material is not None and (not isinstance(mesh.material, Material) or not mesh.material.name):
            raise ValueError(f"node {mesh.node_id} has an invalid material")
        if not mesh.points_mm:
            raise ValueError(f"node {mesh.node_id} has no points")
        for point in mesh.points_mm:
            if len(point) != 3 or not all(isinstance(c, (int, float)) and _finite(c) for c in point):
                raise ValueError(f"node {mesh.node_id} has a non-finite point")
        if not mesh.triangles:
            raise ValueError(f"node {mesh.node_id} has no triangles")
        count = len(mesh.points_mm)
        for triangle in mesh.triangles:
            if len(triangle) != 3 or any(not isinstance(i, int) or i < 0 or i >= count for i in triangle):
                raise ValueError(f"node {mesh.node_id} has an out-of-range triangle index")
        if mesh.uvs is not None and len(mesh.uvs) != len(mesh.points_mm):
            raise ValueError(f"node {mesh.node_id} uv count must match its point count")
        if mesh.normals_mm is not None and len(mesh.normals_mm) != len(mesh.points_mm):
            raise ValueError(f"node {mesh.node_id} normal count must match its point count")


def _finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


def _material(stage: Usd.Stage, material: Material) -> UsdShade.Material:
    path = f"/root/_materials/{material.name}"
    shade = UsdShade.Material.Define(stage, path)
    surface = UsdShade.Shader.Define(stage, f"{path}/PreviewSurface")
    surface.CreateIdAttr("UsdPreviewSurface")
    surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(material.roughness))
    surface.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(material.metallic))
    surface.CreateInput("clearcoat", Sdf.ValueTypeNames.Float).Set(float(material.clearcoat))
    surface.CreateInput("clearcoatRoughness", Sdf.ValueTypeNames.Float).Set(
        float(material.clearcoat_roughness)
    )
    surface.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(float(material.ior))
    surface.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(material.opacity))
    surface.CreateInput("specular", Sdf.ValueTypeNames.Float).Set(float(material.specular))
    if material.texture_archive_path:
        reader = UsdShade.Shader.Define(stage, f"{path}/stReader")
        reader.CreateIdAttr("UsdPrimvarReader_float2")
        reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
        texture = UsdShade.Shader.Define(stage, f"{path}/Image_Texture")
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(material.texture_archive_path)
        texture.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
        texture.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
        texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
            reader.ConnectableAPI(), "result"
        )
        surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
            texture.ConnectableAPI(), "rgb"
        )
    else:
        surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(*material.base_color)
        )
    shade.CreateSurfaceOutput().ConnectToSource(surface.ConnectableAPI(), "surface")
    return shade


def _mesh(stage: Usd.Stage, mesh: Mesh) -> None:
    path = f"/root/{mesh.node_id}"
    prim = UsdGeom.Mesh.Define(stage, path)
    points = [Gf.Vec3f(*runtime_point(point)) for point in mesh.points_mm]
    prim.CreatePointsAttr(points)
    prim.CreateFaceVertexCountsAttr([3] * len(mesh.triangles))
    prim.CreateFaceVertexIndicesAttr([index for triangle in mesh.triangles for index in triangle])
    prim.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    prim.CreateExtentAttr(UsdGeom.PointBased(prim).ComputeExtent(points))
    prim.CreateDoubleSidedAttr(False)

    if mesh.normals_mm is not None:
        normals = [Gf.Vec3f(*runtime_direction(normal)) for normal in mesh.normals_mm]
        prim.CreateNormalsAttr(normals)
        prim.SetNormalsInterpolation(UsdGeom.Tokens.vertex)

    if mesh.uvs is not None:
        primvar = UsdGeom.PrimvarsAPI(prim).CreatePrimvar(
            "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex
        )
        primvar.Set(Vt.Vec2fArray([Gf.Vec2f(float(u), float(v)) for u, v in mesh.uvs]))

    if mesh.material is not None:
        binding = UsdShade.MaterialBindingAPI.Apply(prim.GetPrim())
        binding.Bind(_material(stage, mesh.material))


_DOS_TIME = 0
_DOS_DATE = 33  # 1980-01-01, the earliest representable DOS date


def _normalise_package_timestamps(path: Path) -> None:
    """Zero the archive timestamps so identical inputs give identical bytes.

    ``UsdUtils.CreateNewUsdzPackage`` stamps every member with the current time,
    which makes two otherwise identical builds differ. The DOS date/time fields
    are fixed width, so rewriting them in place preserves the 64-byte alignment
    the USDZ layout depends on. The central directory is walked properly rather
    than scanned for signatures, so payload bytes that look like a header are
    never rewritten.
    """
    data = bytearray(path.read_bytes())
    end = data.rfind(b"PK\x05\x06")
    if end < 0:
        raise ValueError("packaged USDZ has no end-of-central-directory record")
    count = int.from_bytes(data[end + 10 : end + 12], "little")
    offset = int.from_bytes(data[end + 16 : end + 20], "little")
    for _ in range(count):
        if data[offset : offset + 4] != b"PK\x01\x02":
            raise ValueError("packaged USDZ central directory is malformed")
        local = int.from_bytes(data[offset + 42 : offset + 46], "little")
        if data[local : local + 4] != b"PK\x03\x04":
            raise ValueError("packaged USDZ local header is malformed")
        # Field offsets differ between the two header layouts: name and extra
        # lengths sit at +26/+28 in a local file header and at +28/+30 in a
        # central directory header. Reading the local offsets for both would
        # scan the wrong bytes and could corrupt unrelated data.
        for base, time_field, date_field, name_field in (
            (local, 10, 12, 26),
            (offset, 12, 14, 28),
        ):
            data[base + time_field : base + time_field + 2] = _DOS_TIME.to_bytes(2, "little")
            data[base + date_field : base + date_field + 2] = _DOS_DATE.to_bytes(2, "little")
            name_length = int.from_bytes(data[base + name_field : base + name_field + 2], "little")
            extra_length = int.from_bytes(data[base + name_field + 2 : base + name_field + 4], "little")
            cursor = base + 30 + name_length
            limit = cursor + extra_length
            while cursor + 4 <= limit:
                field_id = int.from_bytes(data[cursor : cursor + 2], "little")
                field_size = int.from_bytes(data[cursor + 2 : cursor + 4], "little")
                if field_id == 0x5455 and field_size >= 5:
                    flags = data[cursor + 4]
                    if flags & 0x01:
                        data[cursor + 5 : cursor + 9] = (0).to_bytes(4, "little")
                cursor += 4 + field_size
        name_length = int.from_bytes(data[offset + 28 : offset + 30], "little")
        extra = int.from_bytes(data[offset + 30 : offset + 32], "little")
        comment = int.from_bytes(data[offset + 32 : offset + 34], "little")
        offset += 46 + name_length + extra + comment
    path.write_bytes(bytes(data))


def write_usdz(path: Path, meshes: Sequence[Mesh]) -> None:
    """Write a conforming USDZ package atomically; never leave a partial file."""
    path = Path(path)
    _validate(meshes)
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".hangten-usdz-", dir=str(path.parent)))
    try:
        layer_path = staging / "stage.usdc"
        stage = Usd.Stage.CreateNew(str(layer_path))
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        root = UsdGeom.Xform.Define(stage, "/root")
        # Z-up (FreeCAD/Blender native) -> Y-up runtime basis change, matching
        # the approved reference structure: (x, y, z) -> (x, z, -y).
        root.AddRotateXYZOp().Set(Gf.Vec3f(-90.0, 0.0, 0.0))
        stage.SetDefaultPrim(root.GetPrim())
        for mesh in meshes:
            if mesh.material is not None and mesh.material.texture_source is not None:
                if not mesh.material.texture_archive_path:
                    raise ValueError("texture_source requires texture_archive_path")
                destination = staging / mesh.material.texture_archive_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(mesh.material.texture_source, destination)
            _mesh(stage, mesh)
        stage.GetRootLayer().Save()
        stage = None

        package = staging / "packaged.usdz"
        UsdUtils.CreateNewUsdzPackage(str(layer_path), str(package))
        if not package.is_file() or package.stat().st_size == 0:
            raise ValueError("USDZ packaging produced no output")
        _normalise_package_timestamps(package)
        os.replace(package, path)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _texture_asset(shader: UsdShade.Shader) -> str | None:
    value = shader.GetInput("file").Get()
    if value is None:
        return None
    resolved = value.resolvedPath
    if resolved is None:
        return None
    marker = ".usdz["
    if marker in resolved:
        return resolved.split(marker, 1)[1].rstrip("]")
    return str(value)


def _normal_to_world(matrix: Gf.Matrix4d, normal: Sequence[float]) -> tuple[float, float, float]:
    """Transform a normal by the inverse-transpose of the linear part, normalized.

    Points use the row-vector ``Transform``, so the matching normal operator is
    the inverse of the linear part (the row-vector form of the inverse-transpose);
    ``TransformDir`` would instead apply any non-uniform scale directly, giving
    the wrong normal length and direction. The result is renormalized.
    """
    linear = Gf.Matrix3d(
        matrix[0][0], matrix[0][1], matrix[0][2],
        matrix[1][0], matrix[1][1], matrix[1][2],
        matrix[2][0], matrix[2][1], matrix[2][2],
    )
    transformed = linear.GetInverse() * Gf.Vec3d(*normal)
    length = transformed.GetLength()
    if length == 0.0:
        return (0.0, 0.0, 0.0)
    transformed /= length
    return (transformed[0], transformed[1], transformed[2])


def read_usdz(path: Path) -> dict:
    """Reopen the actual written package and report its stored contents."""
    path = Path(path)
    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise ValueError(f"cannot open {path}")
    nodes: dict[str, dict] = {}
    materials: dict[str, dict] = {}
    root = stage.GetDefaultPrim()
    # Points are reported in WORLD space. Exports authored elsewhere can carry a
    # stage-level rotation (the legacy Blender assets do), so reading the raw
    # points attribute would report local coordinates under a world-space name.
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    for prim in stage.Traverse():
        if prim.IsA(UsdShade.Material):
            shade = UsdShade.Material(prim)
            surface = shade.ComputeSurfaceSource()[0]
            entry: dict[str, object] = {}
            if surface is not None:
                entry["shaderId"] = surface.GetShaderId()
                for shader_input in surface.GetInputs():
                    name = shader_input.GetBaseName()
                    source = shader_input.GetConnectedSource()
                    if source is not None:
                        entry[name] = f"<{source[0].GetPath().name}>"
                    else:
                        value = shader_input.Get()
                        entry[name] = tuple(value) if hasattr(value, "__len__") else value
            if surface is not None:
                texture = surface.GetInput("diffuseColor").GetConnectedSource()
                if texture is not None:
                    entry["diffuseColorAsset"] = _texture_asset(texture[0])
                    entry["diffuseColorAssetResolves"] = entry["diffuseColorAsset"] is not None
            materials[prim.GetName()] = entry
        if not prim.IsA(UsdGeom.Mesh):
            continue
        mesh = UsdGeom.Mesh(prim)
        counts = mesh.GetFaceVertexCountsAttr().Get() or []
        indices = mesh.GetFaceVertexIndicesAttr().Get() or []
        triangles = [
            tuple(indices[i : i + 3]) for i in range(0, len(indices), 3)
        ]
        if any(count != 3 for count in counts):
            raise ValueError(f"{prim.GetName()} contains a non-triangular face")
        bound_result = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        bound = bound_result[0] if bound_result else None
        local_to_world = cache.GetLocalToWorldTransform(prim)
        nodes[prim.GetName()] = {
            "path": str(prim.GetPath()),
            "points_m": [
                tuple(local_to_world.Transform(point)) for point in (mesh.GetPointsAttr().Get() or [])
            ],
            "triangles": triangles,
            "material": bound.GetPrim().GetName() if bound else None,
            "normals": [
                tuple(_normal_to_world(local_to_world, vector))
                for vector in (mesh.GetNormalsAttr().Get() or [])
            ],
            "uvs": (
                len(UsdGeom.PrimvarsAPI(prim).GetPrimvar("st").Get() or [])
                if UsdGeom.PrimvarsAPI(prim).HasPrimvar("st")
                else 0
            ),
        }
    members: list[str] = []
    if str(path).endswith(".usdz"):
        import zipfile

        with zipfile.ZipFile(path) as archive:
            members = sorted(archive.namelist())
    return {
        "defaultPrim": root.GetName() if root else None,
        "up_axis": UsdGeom.GetStageUpAxis(stage),
        "meters_per_unit": UsdGeom.GetStageMetersPerUnit(stage),
        "nodes": nodes,
        "materials": materials,
        "members": members,
    }
