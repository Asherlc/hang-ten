#!/usr/bin/env python3
"""Verify shipped, hash-bound mounting-bore repairs without Blender.

This checks actual USD triangles, not the presence of a named cap object.
The explicit audit inventory separates mounting bores from real contact and
suspension openings. It is not a generic small-hole detector.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
from pxr import Usd, UsdGeom

from contact_model_descriptor import NodeBinding, compile_descriptor
from remove_mounting_bores import _read_mesh


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def verify_package(package: Path, spec: dict) -> dict:
    model = package / "assets/primary.usdz"
    descriptor_path = model.with_suffix(".model.json")
    descriptor = json.loads(descriptor_path.read_text())
    board = json.loads((package / "board.json").read_text())
    validate_archive(model)
    stage, meshes = read_scene(model)
    vertices = {
        m["prim"].GetName(): m["world"][np.unique(m["f"])].tolist() for m in meshes
    }
    if set(vertices) != {n["nodeID"] for n in descriptor["nodes"]}:
        raise ValueError("descriptor node inventory differs from USDZ")
    nodes = [
        NodeBinding(n["nodeID"], n["role"], n.get("contactID"))
        for n in descriptor["nodes"]
    ]
    contact_ids = frozenset(c["id"] for c in board["contacts"])
    rebuilt = compile_descriptor(model.read_bytes(), nodes, vertices, contact_ids)
    if rebuilt.to_json() != descriptor:
        raise ValueError("descriptor differs from re-opened USDZ triangles")
    if set(spec.get("dropNodes", ())) & set(vertices):
        raise ValueError("obsolete floating cap node remains")
    samples = []
    # The centre and a tight four-ray cross lie inside the reviewed bore core,
    # not in nearby genuine finger windows or the exterior board silhouette.
    for hole in spec["holes"]:
        centre = np.asarray(hole["center"], dtype=float)
        for offset in (
            (0.0, 0.0),
            (0.00035, 0.0),
            (-0.00035, 0.0),
            (0.0, 0.00035),
            (0.0, -0.00035),
        ):
            point = centre + offset
            hits = vertical_hits(meshes, point)
            front = [h for h in hits if h[2] > 0 or h[3]]
            back = [h for h in hits if h[2] < 0 or h[3]]
            if not front or not back or front[-1][0] - back[0][0] < 0.0001:
                raise ValueError(
                    f"open or reversed bore patch: {package.name} at {point.tolist()}"
                )
            samples.append(
                {
                    "xy": point.tolist(),
                    "frontZ": front[-1][0],
                    "rearZ": back[0][0],
                    "frontNode": front[-1][1],
                    "rearNode": back[0][1],
                }
            )
    return {
        "modelSHA256": sha256(model),
        "descriptorSHA256": sha256(descriptor_path),
        "contactCount": len(contact_ids),
        "nodeCount": len(nodes),
        "boreCount": len(spec["holes"]),
        "rayCount": len(samples),
        "rays": samples,
        "descriptorMatchesReopenedUSDZ": True,
        "archiveAligned": True,
    }


def verify_catalog(root: Path, manifest: dict) -> dict:
    reports = {}
    for slug, spec in manifest["models"].items():
        package = root / "Hangboards" / slug
        reports[slug] = verify_package(package, spec)
        print(f"verified {slug}: {len(spec['holes'])} bores", flush=True)
    inventory = manifest["inventory"]
    actual = {
        p.parent.parent.name for p in (root / "Hangboards").glob("*/assets/*.usdz")
    }
    if actual != set(inventory):
        raise ValueError("shipped model inventory changed; review the new catalogue")
    for slug, baseline in inventory.items():
        package = root / "Hangboards" / slug
        if sha256(package / "board.json") != baseline["boardSHA256"]:
            raise ValueError(f"board metadata changed: {slug}")
        if slug not in reports:
            if sha256(package / baseline["modelPath"]) != baseline["modelSHA256"]:
                raise ValueError(f"unaudited geometry edit: {slug}")
            if (
                sha256(package / baseline["descriptorPath"])
                != baseline["descriptorSHA256"]
            ):
                raise ValueError(f"unaudited descriptor edit: {slug}")
    return {
        "modelsAudited": len(inventory),
        "modelsRepaired": len(reports),
        "boresRemoved": sum(r["boreCount"] for r in reports.values()),
        "unchangedModels": sorted(set(inventory) - set(reports)),
        "models": reports,
    }


def _target_triangle_approved(tri, holes, mesh_name, spec) -> bool:
    """A new target triangle is allowed only inside an approved repair region.

    Front patches live inside a reviewed hole cylinder (XY within radius +
    1e-6, matching repair_stage); rear patches additionally require the
    hole's rearPlane/rearNode planar match. Skip-node meshes never receive
    front patches, so they admit only rear-patch triangles.
    """
    tri = np.asarray(tri, dtype=float).reshape(3, 3)
    skipped = mesh_name in spec.get("skipNodes", ())
    for hole in holes:
        center = np.asarray(hole["center"], dtype=float)
        radius = float(hole["radius"])
        if np.linalg.norm(tri[:, :2] - center, axis=1).max() > radius + 1e-6:
            continue
        if not skipped:
            return True
        rear = hole.get("rearPlane")
        if (
            rear is not None
            and hole.get("rearNode") == mesh_name
            and np.abs(tri[:, 2] - rear).max() <= 1e-6
        ):
            return True
    return False


def _check_no_unapproved_target_triangles(
    slug, mesh_name, retained_triangles, after_triangles, spec, key_fn
) -> None:
    """Reject target-only triangles (with multiplicities) outside regions."""
    before_counts = Counter(k.tobytes() for k in key_fn(retained_triangles))
    after_counts = Counter(k.tobytes() for k in key_fn(after_triangles))
    representative = {}
    for tri, key in zip(
        np.asarray(after_triangles).reshape(-1, 3, 3), key_fn(after_triangles)
    ):
        representative.setdefault(key.tobytes(), tri)
    for key_bytes, count in after_counts.items():
        if count <= before_counts.get(key_bytes, 0):
            continue
        tri = representative[key_bytes]
        if not _target_triangle_approved(tri, spec["holes"], mesh_name, spec):
            raise ValueError(
                f"unapproved target geometry outside repair region: {slug}/{mesh_name}"
            )


def verify_scope(source_root: Path, repaired_root: Path, manifest: dict) -> dict:
    """Prove retained triangles, contact IDs, and embedded images are unchanged."""

    def keys(triangles):
        values = np.ascontiguousarray(np.round(triangles, 7).reshape(-1, 9))
        return values.view(np.dtype((np.void, values.dtype.itemsize * 9))).ravel()

    reports = {}
    for slug, spec in manifest["models"].items():
        original = source_root / "Hangboards" / slug / "assets/primary.usdz"
        revised = repaired_root / "Hangboards" / slug / "assets/primary.usdz"
        if sha256(original) != spec["sha256"]:
            raise ValueError(f"wrong source revision: {slug}")
        source_stage, source = read_scene(original)
        target_stage, target = read_scene(revised)
        targets = {m["prim"].GetName(): m for m in target}
        retained_count = 0
        for mesh in source:
            name = mesh["prim"].GetName()
            if name in spec.get("dropNodes", ()):
                continue
            triangles = mesh["world"][mesh["f"]]
            retained = np.ones(len(triangles), dtype=bool)
            for start, end in spec.get("removeFaceRanges", {}).get(name, ()):
                retained[start:end] = False
            if name not in spec.get("skipNodes", ()):
                for hole in spec["holes"]:
                    retained &= ~(
                        np.linalg.norm(
                            triangles[:, :, :2] - hole["center"], axis=2
                        ).max(1)
                        < hole["radius"]
                    )
            after = targets[name]["world"][targets[name]["f"]]
            if len(np.setdiff1d(keys(triangles[retained]), keys(after))):
                raise ValueError(
                    f"geometry outside repair region changed: {slug}/{name}"
                )
            _check_no_unapproved_target_triangles(
                slug, name, triangles[retained], after, spec, keys
            )
            retained_count += int(retained.sum())

        def images(path):
            with zipfile.ZipFile(path) as archive:
                return {
                    n: archive.read(n)
                    for n in archive.namelist()
                    if Path(n).suffix.lower() in (".png", ".jpg", ".jpeg")
                }

        source_images = images(original)
        if source_images != images(revised):
            raise ValueError(f"embedded texture changed: {slug}")
        before = json.loads(original.with_suffix(".model.json").read_text())
        after = json.loads(revised.with_suffix(".model.json").read_text())

        def contacts(value):
            return {
                n["nodeID"]: n.get("contactID")
                for n in value["nodes"]
                if n["role"] == "contact"
            }

        if contacts(before) != contacts(after):
            raise ValueError(f"contact binding changed: {slug}")
        reports[slug] = {
            "retainedTriangles": retained_count,
            "identicalEmbeddedImages": len(source_images),
            "contactBindingsUnchanged": True,
        }
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    result = verify_catalog(args.root, json.loads(args.manifest.read_text()))
    if args.source_root:
        result["scope"] = verify_scope(
            args.source_root, args.root, json.loads(args.manifest.read_text())
        )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
