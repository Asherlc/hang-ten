"""Blender-free readback of the actual triangles in a shipped USDZ.

Shared by the offline model tools (``verify_simplification_pilot.py``) and
``ReviewTools/render_simplification.py``. It reads geometry only; it never
authors, repairs, or re-exports a model.
"""
from __future__ import annotations

import struct
import zipfile
from pathlib import Path

import numpy as np
from pxr import Usd, UsdGeom

from remove_mounting_bores import _read_mesh


def read_scene(path: Path) -> tuple[object, list[dict]]:
    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise ValueError(f"cannot open USDZ: {path}")
    cache = UsdGeom.XformCache()
    meshes = [_read_mesh(p, cache) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh)]
    if not meshes:
        raise ValueError("USDZ has no mesh geometry")
    for mesh in meshes:
        if not np.isfinite(mesh["world"]).all():
            raise ValueError("nonfinite mesh point")
        for values in mesh["channels"].values():
            if not np.isfinite(values).all():
                raise ValueError("nonfinite face-corner channel")
    return stage, meshes


def vertical_hits(meshes: list[dict], xy: np.ndarray) -> list[tuple]:
    """Intersect a line parallel to board +Z with the actual mesh triangles."""
    hits = []
    for mesh in meshes:
        tri = mesh["world"][mesh["f"]]
        eligible = (tri[:, :, :2].min(1) <= xy).all(1) & (
            tri[:, :, :2].max(1) >= xy
        ).all(1)
        tri = tri[eligible]
        if not len(tri):
            continue
        a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
        denominator = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (
            c[:, 0] - b[:, 0]
        ) * (a[:, 1] - c[:, 1])
        valid = np.abs(denominator) > 1e-15
        a, b, c, denominator = a[valid], b[valid], c[valid], denominator[valid]
        u = (
            (b[:, 1] - c[:, 1]) * (xy[0] - c[:, 0])
            + (c[:, 0] - b[:, 0]) * (xy[1] - c[:, 1])
        ) / denominator
        v = (
            (c[:, 1] - a[:, 1]) * (xy[0] - c[:, 0])
            + (a[:, 0] - c[:, 0]) * (xy[1] - c[:, 1])
        ) / denominator
        inside = (u >= -1e-7) & (v >= -1e-7) & (u + v <= 1 + 1e-7)
        z = u * a[:, 2] + v * b[:, 2] + (1 - u - v) * c[:, 2]
        orientation = (
            -1 if mesh["mesh"].GetOrientationAttr().Get() == "leftHanded" else 1
        )
        double_sided = bool(mesh["mesh"].GetDoubleSidedAttr().Get())
        hits.extend(
            (
                float(height),
                mesh["prim"].GetName(),
                float(winding) * orientation,
                double_sided,
            )
            for height, winding in zip(z[inside], denominator[inside])
        )
    return sorted(hits)


def validate_archive(path: Path) -> None:
    raw = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            if entry.compress_type != zipfile.ZIP_STORED:
                raise ValueError("USDZ member is compressed")
            name_len, extra_len = struct.unpack_from(
                "<HH", raw, entry.header_offset + 26
            )
            if (entry.header_offset + 30 + name_len + extra_len) % 64:
                raise ValueError("USDZ member is not aligned to 64 bytes")
            if entry.filename.startswith("/") or ".." in Path(entry.filename).parts:
                raise ValueError("unsafe USDZ member path")
