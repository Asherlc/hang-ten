#!/usr/bin/env python3
"""Author explicit hardware-free display surfaces in an existing USDZ.

This is an offline authoring operation, not an importer/compiler repair hook.
Only hash-bound, individually reviewed cylindrical regions are edited. Units are
metres in the existing board frame. No image-derived geometry or hole discovery
is performed. Genuine contact openings and suspension apertures are out of scope.
"""
from __future__ import annotations
import argparse, hashlib, json, sys, tempfile, zipfile
from pathlib import Path
import numpy as np
from pxr import Usd, UsdGeom, Vt
from contact_model_descriptor import NodeBinding, compile_descriptor
from contact_model_package import _canonicalize_usdz


def patch_loop(
    boundary: np.ndarray, *, nonplanar: bool = False
) -> tuple[np.ndarray, np.ndarray]:
    """Triangulate only this explicit rim, preserving all its boundary edges."""
    from shapely import Polygon, constrained_delaunay_triangles

    p = np.asarray(boundary, dtype=np.float64)
    if p.ndim != 2 or len(p) < 3 or p.shape[1:] != (3,) or not np.isfinite(p).all():
        raise ValueError("invalid patch boundary")
    if nonplanar:
        return minimum_area_patch(p)
    q = p - p.mean(0)
    _, _, basis = np.linalg.svd(q, full_matrices=False)
    projections = [p[:, :2], q @ basis[:2].T, p[:, [0, 2]], p[:, [1, 2]]]
    valid = [
        (xy, Polygon(xy))
        for xy in projections
        if Polygon(xy).is_valid and Polygon(xy).area > 1e-18
    ]
    if not valid:
        if nonplanar:
            return minimum_area_patch(p)
        raise ValueError("boundary has no simple planar projection")
    xy, polygon = valid[0]
    lookup = {tuple(pt): i for i, pt in enumerate(xy)}
    signed = np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - xy[:, 1] * np.roll(xy[:, 0], -1))
    faces = []
    for triangle in constrained_delaunay_triangles(polygon).geoms:
        coords = list(triangle.exterior.coords)[:3]
        f = [lookup[tuple(xy)] for xy in coords]
        q = xy[f]
        u = q[1] - q[0]
        v = q[2] - q[0]
        area = u[0] * v[1] - u[1] * v[0]
        if area * signed < 0:
            f = f[::-1]
        faces.append(f)
    return p.copy(), np.asarray(faces, dtype=np.int32)


def minimum_area_patch(p):
    """Triangulate a specifically reviewed folded rim in its native 3D frame.

    Dynamic programming minimizes area plus a small aspect penalty. Every input
    rim edge is retained; all new vertices lie on the original boundary. This
    path is opt-in per bore, never a generic fallback for unknown apertures.
    """
    n = len(p)
    cost = np.zeros((n, n))
    split = np.zeros((n, n), dtype=int)
    for gap in range(2, n):
        for i in range(n - gap):
            j = i + gap
            k = np.arange(i + 1, j)
            u = p[k] - p[i]
            v = p[j] - p[i]
            area = np.linalg.norm(np.cross(u, v), axis=1) / 2
            lengths = (u * u).sum(1) + ((p[k] - p[j]) ** 2).sum(1) + (v * v).sum()
            candidates = cost[i, k] + cost[k, j] + area + 0.01 * lengths
            best = int(np.argmin(candidates))
            cost[i, j] = candidates[best]
            split[i, j] = k[best]
    todo = [(0, n - 1)]
    faces = []
    while todo:
        i, j = todo.pop()
        if j <= i + 1:
            continue
        k = int(split[i, j])
        faces.append([i, k, j])
        todo.extend([(i, k), (k, j)])
    return p.copy(), np.asarray(faces, dtype=np.int32)


def _read_mesh(prim, cache):
    mesh = UsdGeom.Mesh(prim)
    v = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
    count = np.asarray(mesh.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
    if not np.all(count == 3):
        raise ValueError(f"non-triangle mesh: {prim.GetPath()}")
    f = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64).reshape(-1, 3)
    matrix = np.array(cache.GetLocalToWorldTransform(prim))
    world = v @ matrix[:3, :3] + matrix[3, :3]
    channels = {}
    normals = mesh.GetNormalsAttr().Get()
    if normals:
        arr = np.asarray(normals, dtype=float)
        interp = mesh.GetNormalsInterpolation()
        if interp == "faceVarying":
            arr = arr.reshape(-1, 3, 3)
        elif interp in ("vertex", "varying"):
            arr = arr[f]
        elif interp == "uniform":
            arr = np.repeat(arr[:, None], 3, axis=1)
        else:
            raise ValueError(f"unsupported normals: {interp}")
        channels["normals"] = arr
    for pv in UsdGeom.PrimvarsAPI(prim).GetPrimvars():
        if pv.GetInterpolation() == "constant":
            continue
        arr = np.asarray(pv.ComputeFlattened())
        interp = pv.GetInterpolation()
        if interp == "faceVarying":
            arr = arr.reshape((len(f), 3) + arr.shape[1:])
        elif interp in ("vertex", "varying"):
            arr = arr[f]
        elif interp == "uniform":
            arr = np.repeat(arr[:, None], 3, axis=1)
        else:
            raise ValueError(f"unsupported primvar: {pv.GetName()} {interp}")
        channels[pv.GetName()] = arr
    if any(c.GetTypeName() == "GeomSubset" for c in prim.GetChildren()):
        raise ValueError("per-face material subsets require explicit authoring")
    return dict(
        prim=prim,
        mesh=mesh,
        v=v,
        world=world,
        f=f,
        matrix=matrix,
        channels=channels,
        keep=np.ones(len(f), bool),
        patches=[],
    )


def _loops(edges):
    import networkx as nx

    graph = nx.Graph()
    graph.add_edges_from((int(a), int(b)) for a, b in edges)
    loops = nx.cycle_basis(graph)
    used = []
    for loop in loops:
        used.extend(tuple(sorted((a, b))) for a, b in zip(loop, np.roll(loop, -1)))
    expected = {tuple(sorted(map(int, e))) for e in edges}
    if len(used) != len(set(used)) or set(used) != expected:
        raise ValueError("repair boundary has dangling or multiply-used edges")
    return loops


def repair_stage(stage, holes, drop_nodes, face_ranges=None, skip_nodes=()):
    cache = UsdGeom.XformCache()
    records = []
    removed = []
    for prim in list(stage.Traverse()):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        if prim.GetName() in drop_nodes:
            removed.append(prim.GetName())
            stage.RemovePrim(prim.GetPath())
            continue
        record = _read_mesh(prim, cache)
        ranges = (face_ranges or {}).get(prim.GetName(), [])
        if ranges:
            mask = np.ones(len(record["f"]), bool)
            for start, end in ranges:
                if not 0 <= start < end <= len(mask):
                    raise ValueError("invalid explicit face range")
                mask[start:end] = False
            record["f"] = record["f"][mask]
            record["channels"] = {k: v[mask] for k, v in record["channels"].items()}
            record["trimmed"] = True
        records.append(record)
    if set(removed) != set(drop_nodes):
        raise ValueError("explicit cap-node inventory mismatch")
    verts = np.concatenate([m["world"] for m in records])
    offsets = np.r_[0, np.cumsum([len(m["world"]) for m in records])]
    faces = np.concatenate([m["f"] + o for m, o in zip(records, offsets[:-1])])
    node_ids = np.concatenate([np.full(len(m["f"]), i) for i, m in enumerate(records)])
    face_local = np.concatenate([np.arange(len(m["f"])) for m in records])
    # Position welding is used only to inspect topology. Retained USD vertices,
    # face corners, UV values, and normals are not welded or resampled.
    _, unique, canonical = np.unique(
        np.round(verts, 7), axis=0, return_index=True, return_inverse=True
    )
    cv = verts[unique]
    cf = canonical[faces]
    keep = np.ones(len(faces), bool)
    reports = []
    for hole in holes:
        xy = np.asarray(hole["center"], float)
        radius = float(hole["radius"])
        if xy.shape != (2,) or not np.isfinite(xy).all() or not 0 < radius <= 0.015:
            raise ValueError("invalid explicit repair region")
        d = np.linalg.norm(verts[:, :2] - xy, axis=1)
        skip_ids = [
            i for i, m in enumerate(records) if m["prim"].GetName() in skip_nodes
        ]
        excluded = np.isin(node_ids, skip_ids)
        cut = (d[faces].max(axis=1) < radius) & keep & ~excluded
        # Existing open stencils may need a patch without any bore-wall triangles.
        keep &= ~cut
        kept_ids = np.where(keep & ~excluded)[0]
        kept = cf[keep & ~excluded]
        directed = np.concatenate([kept[:, [0, 1]], kept[:, [1, 2]], kept[:, [2, 0]]])
        # directed is a blocked concat of the three edge slots, so directed[j]
        # belongs to kept position j % N; retain it explicitly instead of
        # relying on bare modulo at the lookup site.
        face_of_directed = np.tile(np.arange(len(kept_ids)), 3)
        # All exposed edges wholly within this reviewed region belong to the
        # edited aperture. Exterior/contact boundaries outside it are excluded.
        sorted_edges = np.sort(directed, axis=1)
        _, eidx, counts = np.unique(
            sorted_edges, axis=0, return_index=True, return_counts=True
        )
        idx = eidx[counts == 1]
        edge = directed[idx]
        inside = np.linalg.norm(cv[edge, :2] - xy, axis=2).max(axis=1) < radius + 1e-6
        inside &= edge[:, 0] != edge[:, 1]
        edge = edge[inside]
        idx = idx[inside]
        rear = hole.get("rearPlane")
        if rear is not None:
            nonrear = np.abs(cv[edge, 2] - rear).max(axis=1) > 1e-6
            edge = edge[nonrear]
            idx = idx[nonrear]
        try:
            loops = _loops(edge)
        except ValueError as exc:
            debug = {
                "center": xy.tolist(),
                "radius": radius,
                "edges": edge.tolist(),
                "points": {str(i): cv[i].tolist() for i in np.unique(edge)},
            }
            # Detailed boundary remains in the exception context for a targeted review.
            raise ValueError(f"{exc}; hole={xy}") from exc
        if not loops:
            raise ValueError(f"no repair boundary at {xy}")
        edge_lookup = {
            tuple(sorted(e)): (int(kept_ids[face_of_directed[j]]), tuple(e))
            for e, j in zip(edge, idx)
        }
        patches = []
        for loop in loops:
            # Reverse the existing mesh boundary orientation so every seam is
            # shared by two oppositely wound faces.
            first = edge_lookup[tuple(sorted(loop[:2]))][1]
            if tuple(loop[:2]) == first:
                loop = loop[::-1]
            try:
                pv, pf = patch_loop(cv[loop], nonplanar=hole.get("nonplanar", False))
            except ValueError as exc:
                raise ValueError(
                    f"{exc}; hole={xy}; boundary={cv[loop].tolist()}"
                ) from exc
            owners = []
            corner_channels = []
            for a, b in zip(loop, np.roll(loop, -1)):
                fid, _ = edge_lookup[tuple(sorted((a, b)))]
                owners.append(int(node_ids[fid]))
            owner = max(set(owners), key=owners.count)
            m = records[owner]
            # Bind to the existing contact when a contact owns the whole rim;
            # mixed boundaries are not silently reclassified.
            if len(set(owners)) != 1 and not hole.get("allowMixedBoundary", False):
                raise ValueError(
                    f'boundary spans nodes: {[(records[o]["prim"].GetName(),owners.count(o)) for o in set(owners)]}; hole={xy}; bounds={[pv.min(0).tolist(),pv.max(0).tolist()]}'
                )
            channels = {}
            for key, values in m["channels"].items():
                rim = []
                for a, b in zip(loop, np.roll(loop, -1)):
                    fid, _ = edge_lookup[tuple(sorted((a, b)))]
                    lf = face_local[fid]
                    corner = int(np.where(cf[fid] == a)[0][0])
                    source_record = records[int(node_ids[fid])]
                    value = source_record["channels"][key][lf, corner].copy()
                    if key == "normals" and source_record is not m:
                        world_normal = (
                            value @ np.linalg.inv(source_record["matrix"][:3, :3]).T
                        )
                        value = world_normal @ m["matrix"][:3, :3].T
                    rim.append(value)
                rim = np.asarray(rim)
                mean = rim.mean(axis=0)
                vals = rim
                if key == "normals":
                    vals /= np.maximum(
                        np.linalg.norm(vals, axis=-1, keepdims=True), 1e-12
                    )
                channels[key] = vals[pf]
            local = (pv - m["matrix"][3, :3]) @ np.linalg.inv(m["matrix"][:3, :3])
            m["patches"].append((local, pf, channels))
            patches.append(
                {
                    "node": m["prim"].GetName(),
                    "boundary_vertices": len(loop),
                    "triangles": len(pf),
                    "bounds": [pv.min(0).tolist(), pv.max(0).tolist()],
                }
            )
        if rear is not None:
            owner = next(
                i
                for i, m in enumerate(records)
                if m["prim"].GetName() == hole["rearNode"]
            )
            m = records[owner]
            patch = planar_rear_patch(m, keep[node_ids == owner], xy, radius, rear)
            if patch:
                m["patches"].append(patch)
                patches.append(
                    {
                        "node": m["prim"].GetName(),
                        "planarRear": True,
                        "triangles": len(patch[1]),
                    }
                )
        reports.append(
            {
                "center": xy.tolist(),
                "radius": radius,
                "removed_triangles": int(cut.sum()),
                "patches": patches,
            }
        )
    for i, m in enumerate(records):
        selected = keep[node_ids == i]
        m["keep"] = selected
        if selected.all() and not m["patches"] and not m.get("trimmed"):
            continue
        pvs = [m["v"]]
        pfs = [m["f"][selected]]
        channels = {k: [v[selected]] for k, v in m["channels"].items()}
        off = len(m["v"])
        for pv, pf, pc in m["patches"]:
            pvs.append(pv)
            pfs.append(pf + off)
            off += len(pv)
            for k in channels:
                channels[k].append(pc[k])
        v = np.concatenate(pvs)
        f = np.concatenate(pfs)
        if "normals" in channels:
            channels["normals"] = [
                refresh_local_normals(
                    v, f, np.concatenate(channels["normals"]), m["matrix"], holes
                )
            ]
        # Compact now-unused bore-wall points; no retained point moves.
        used = np.unique(f)
        remap = np.full(len(v), -1, dtype=np.int32)
        remap[used] = np.arange(len(used))
        v = v[used]
        f = remap[f]
        mesh = m["mesh"]
        mesh.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(v.astype(np.float32)))
        mesh.GetFaceVertexCountsAttr().Set(
            Vt.IntArray.FromNumpy(np.full(len(f), 3, dtype=np.int32))
        )
        mesh.GetFaceVertexIndicesAttr().Set(
            Vt.IntArray.FromNumpy(f.ravel().astype(np.int32))
        )
        mesh.GetExtentAttr().Set(
            Vt.Vec3fArray.FromNumpy(np.array([v.min(0), v.max(0)], dtype=np.float32))
        )
        for key, parts in channels.items():
            values = np.concatenate(parts)
            values = values.reshape((-1,) + values.shape[2:]).astype(np.float32)
            attr = m["prim"].GetAttribute(key)
            if key == "normals":
                mesh.SetNormalsInterpolation("faceVarying")
            else:
                pv = UsdGeom.PrimvarsAPI(m["prim"]).GetPrimvar(key)
                pv.SetInterpolation("faceVarying")
                pv.BlockIndices()
            old = attr.Get()
            typeclass = type(old)
            attr.Set(typeclass.FromNumpy(values))
    return {"holes": reports, "removed_nodes": removed}


def planar_rear_patch(m, keep, xy, radius, z):
    """Close an explicitly identified planar rear mouth without double faces."""
    from shapely import Point, Polygon, union_all, constrained_delaunay_triangles

    v = m["world"]
    f = m["f"]
    tri = v[f]
    eligible = keep & (np.abs(tri[:, :, 2] - z).max(1) < 1e-6)
    eligible &= (tri[:, :, 0].max(1) >= xy[0] - radius) & (
        tri[:, :, 0].min(1) <= xy[0] + radius
    )
    eligible &= (tri[:, :, 1].max(1) >= xy[1] - radius) & (
        tri[:, :, 1].min(1) <= xy[1] + radius
    )
    fs = np.where(eligible)[0]
    polys = [Polygon(t[:, :2]) for t in tri[eligible]]
    covered = union_all([p for p in polys if p.is_valid and p.area > 1e-18])
    missing = Point(*xy).buffer(radius, quad_segs=64).difference(covered)
    faces = []
    points = []
    for t in constrained_delaunay_triangles(missing).geoms:
        q = np.asarray(t.exterior.coords)[:3]
        cross = (q[1, 0] - q[0, 0]) * (q[2, 1] - q[0, 1]) - (q[1, 1] - q[0, 1]) * (
            q[2, 0] - q[0, 0]
        )
        if cross > 0:
            q = q[::-1]
        off = len(points)
        points.extend(np.c_[q, np.full(3, z)])
        faces.append([off, off + 1, off + 2])
    if not faces:
        return None
    world = np.asarray(points)
    face = np.asarray(faces, dtype=np.int32)
    local = (world - m["matrix"][3, :3]) @ np.linalg.inv(m["matrix"][:3, :3])
    channels = {}
    for key, values in m["channels"].items():
        if key == "normals":
            normal = np.array([0.0, 0.0, -1.0]) @ m["matrix"][:3, :3].T
            normal /= np.linalg.norm(normal)
            vals = np.tile(normal, (len(world), 1))
        else:
            a = np.c_[tri[eligible, :, :2].reshape(-1, 2) - xy, np.ones(len(fs) * 3)]
            b = values[eligible].reshape((-1,) + values.shape[2:])
            coef = np.linalg.lstsq(a, b, rcond=None)[0]
            vals = np.c_[world[:, :2] - xy, np.ones(len(world))] @ coef
        channels[key] = vals[face]
    return local, face, channels


def refresh_local_normals(v, f, old, matrix, holes):
    """Remove obsolete bore-wall shading without smoothing unrelated edges."""
    world = v @ matrix[:3, :3] + matrix[3, :3]
    affected = np.zeros(len(v), bool)
    for hole in holes:
        affected |= (
            np.linalg.norm(world[:, :2] - hole["center"], axis=1) < hole["radius"] * 1.7
        )
    if not affected.any():
        return old
    _, canonical = np.unique(np.round(world, 7), axis=0, return_inverse=True)
    cf = canonical[f]
    tri = world[f]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(fn, axis=1)
    fn /= np.maximum(length[:, None], 1e-20)
    order = np.argsort(cf.ravel(), kind="stable")
    sorted_ids = cf.ravel()[order]
    keys, start, count = np.unique(sorted_ids, return_index=True, return_counts=True)
    spans = {int(k): order[a : a + n] for k, a, n in zip(keys, start, count)}
    result = old.copy().reshape(-1, 3)
    for vertex in np.unique(canonical[affected]):
        corners = spans.get(int(vertex))
        if corners is None:
            continue
        faces = corners // 3
        normals = fn[faces]
        # Do not average across a genuine sharp hold edge (45-degree crease).
        weights = (normals @ normals.T) > 0.70710678
        smoothed = weights @ normals
        smoothed /= np.maximum(np.linalg.norm(smoothed, axis=1, keepdims=True), 1e-20)
        local = smoothed @ matrix[:3, :3].T
        local /= np.maximum(np.linalg.norm(local, axis=1, keepdims=True), 1e-20)
        valid = np.linalg.norm(local, axis=1) > 0.5
        result[corners[valid]] = local[valid]
    return result.reshape(old.shape)



def package_board_bytes(package: Path) -> bytes | None:
    """A package's board.json bytes, or None when it has none.

    A CAD-backed package (``<slug>.FCStd``) commits no board.json; its document
    is generated from the FCStd's HangTenBoardManifest, exactly as the package
    validator and app staging generate it.
    """
    package = Path(package)
    source = package / f"{package.name}.FCStd"
    if source.is_file():
        packages_src = Path(__file__).resolve().parents[1] / "HangboardPackages" / "src"
        if str(packages_src) not in sys.path:
            sys.path.insert(0, str(packages_src))
        from hangboard_packages import cad_source

        return cad_source.generate_board_json(source)
    board = package / "board.json"
    return board.read_bytes() if board.is_file() else None

def repair_file(source: Path, destination: Path, spec: dict, descriptor: Path):
    if source.resolve() == destination.resolve():
        raise ValueError("author into a separate output directory")
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != spec["sha256"]:
        raise ValueError("source SHA mismatch; re-review changed model")
    descriptor_bytes = descriptor.read_bytes()
    expected_descriptor = spec.get("descriptorSHA256")
    if expected_descriptor is not None:
        if hashlib.sha256(descriptor_bytes).hexdigest() != expected_descriptor:
            raise ValueError("source descriptor SHA mismatch; re-review changed model")
    old = json.loads(descriptor_bytes.decode("utf-8"))
    # Bind contact IDs to the reviewed board metadata instead of trusting the
    # descriptor alone. Opt-in when hashes are present; mandatory via __main__
    # inventory injection. Missing board file falls back to legacy behavior so
    # minimal-spec callers and unit tests keep working.
    board_bytes = package_board_bytes(source.parents[1])
    expected_board = spec.get("boardSHA256")
    board_ids = None
    if board_bytes is not None:
        if expected_board is not None:
            if hashlib.sha256(board_bytes).hexdigest() != expected_board:
                raise ValueError("source board SHA mismatch; re-review changed model")
        board_doc = json.loads(board_bytes.decode("utf-8"))
        if "contacts" in board_doc:
            board_ids = frozenset(c["id"] for c in board_doc["contacts"])
            if frozenset(old["contacts"]) != board_ids:
                raise ValueError("source contact binding mismatch; re-review changed model")
    elif expected_board is not None:
        raise ValueError("source board SHA mismatch; re-review changed model")
    logical_ids = board_ids if board_ids is not None else frozenset(old["contacts"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="bore-author-", dir=destination.parent
    ) as td:
        root = Path(td)
        with zipfile.ZipFile(source) as z:
            for n in z.namelist():
                if n.startswith("/") or ".." in Path(n).parts:
                    raise ValueError("unsafe USDZ path")
            names = z.namelist()
            z.extractall(root)
        layer = next(n for n in names if Path(n).suffix in {".usd", ".usda", ".usdc"})
        stage = Usd.Stage.Open(str(root / layer))
        report = repair_stage(
            stage,
            spec["holes"],
            spec.get("dropNodes", []),
            spec.get("removeFaceRanges", {}),
            spec.get("skipNodes", []),
        )
        stage.GetRootLayer().Save()
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as z:
            for n in names:
                z.write(root / n, n)
    _canonicalize_usdz(destination)
    # Reopen the actual finished USDZ. Descriptor values are derived from its
    # referenced triangles, never copied or authored to hide geometry changes.
    stage = Usd.Stage.Open(str(destination))
    cache = UsdGeom.XformCache()
    vertices = {}
    for p in stage.Traverse():
        if p.IsA(UsdGeom.Mesh):
            m = _read_mesh(p, cache)
            vertices[p.GetName()] = m["world"][np.unique(m["f"])].tolist()
    # Reuse the hash-validated source descriptor bindings; do not re-read the
    # file after the repair where a swap could inject unreviewed contacts.
    nodes = [
        NodeBinding(n["nodeID"], n["role"], n.get("contactID"))
        for n in old["nodes"]
        if n["nodeID"] in vertices
    ]
    compiled = compile_descriptor(
        destination.read_bytes(), nodes, vertices, logical_ids
    )
    out = destination.with_suffix(".model.json")
    out.write_text(json.dumps(compiled.to_json(), indent=2, sort_keys=True) + "\n")
    report.update(
        {
            "sourceSHA256": spec["sha256"],
            "modelSHA256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "descriptorSHA256": hashlib.sha256(out.read_bytes()).hexdigest(),
        }
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--board")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    inventory = manifest.get("inventory", {})
    reports = {}
    for slug, spec in manifest["models"].items():
        if args.board and slug != args.board:
            continue
        source = args.root / "Hangboards" / slug / "assets/primary.usdz"
        dest = args.output / "Hangboards" / slug / "assets/primary.usdz"
        bound = dict(spec)
        baseline = inventory.get(slug, {})
        if "descriptorSHA256" not in bound and "descriptorSHA256" in baseline:
            bound["descriptorSHA256"] = baseline["descriptorSHA256"]
        if "boardSHA256" not in bound and "boardSHA256" in baseline:
            bound["boardSHA256"] = baseline["boardSHA256"]
        report = repair_file(source, dest, bound, source.with_suffix(".model.json"))
        reports[slug] = report
        print(slug, "repaired", len(report["holes"]), "holes", flush=True)
    (args.output / "repair-report.json").write_text(
        json.dumps(reports, indent=2) + "\n"
    )
