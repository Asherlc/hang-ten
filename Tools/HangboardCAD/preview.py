"""Fast, host-side preview and diagnostic for a compiled board asset.

This is the inner loop of the migration: after rebuilding a board it renders the
compiled nodes with normal-shaded (lambert) fills so the *shape* of the geometry
is visible, prints the node inventory and bounds, and reports a top-facet metric
that is useful when comparing a candidate to its pre-migration reference.

It never imports FreeCAD and never writes into a package, so it is cheap and
safe to run after every authoring edit. It is a diagnostic, not a build input —
nothing here is a pass/fail gate, and flat or rounded tops both produce
up-facing facets (compare to the reference under the same metric, not against
zero).

    .context/<workspace>/venv/bin/python Tools/HangboardCAD/preview.py \
        --package <slug> [--reference <pre-migration.usdz>] [--out <dir>]

Writes `<out>/<slug>-front.png`, `-side.png`, `-top.png` (and `-ref-*.png` for
the reference when one is given), then prints the diagnostics to stdout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from usdz_writer import read_usdz  # noqa: E402

LIGHT = np.array([0.0, -0.5, 0.87])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def _native(node):
    """Runtime metres -> native millimetres (x right, y depth front-negative, z up)."""
    p = np.asarray(node["points_m"], dtype=np.float64) * 1000.0
    return np.stack([p[:, 0], -p[:, 2], p[:, 1]], axis=1)


def _triangles(model):
    rows = []
    for node in model["nodes"].values():
        pts = _native(node)
        tri = np.asarray(node["triangles"])
        if len(tri) == 0:
            continue
        a, b, c = pts[tri[:, 0]], pts[tri[:, 1]], pts[tri[:, 2]]
        normals = np.cross(b - a, c - a)
        lengths = np.linalg.norm(normals, axis=1)
        lengths[lengths == 0] = 1.0
        normals = normals / lengths[:, None]
        rows.append((pts[tri], normals))
    if not rows:
        return np.zeros((0, 3, 3)), np.zeros((0, 3))
    return np.concatenate([r[0] for r in rows]), np.concatenate([r[1] for r in rows])


def _project(points, view):
    """Orthographic (u, v, depth) for one view. u/v are the plotted axes."""
    if view == "front":  # native (x, z), looking from -y
        return points[:, :, 0], points[:, :, 2], points[:, :, 1]
    if view == "side":  # native (y, z), looking from +x
        return points[:, :, 1], points[:, :, 2], points[:, :, 0]
    # top: native (x, y), looking from +z
    return points[:, :, 0], points[:, :, 1], points[:, :, 2]


def _render(points, normals, view, path, size=(520, 680)):
    """Painter's-algorithm lambert render of one orthographic view.

    Uses a uniform scale (letterboxed) so a wide, short board is not stretched
    into an unreadable portrait.
    """
    width, height = size
    shade = np.clip(normals @ LIGHT, 0.0, 1.0)
    u, v, depth = _project(points, view)

    u0, u1 = float(u.min()), float(u.max())
    v0, v1 = float(v.min()), float(v.max())
    pad = 0.04 * max(u1 - u0, v1 - v0, 1e-6)
    u0, u1, v0, v1 = u0 - pad, u1 + pad, v0 - pad, v1 + pad
    span_u = max(u1 - u0, 1e-6)
    span_v = max(v1 - v0, 1e-6)
    scale = min((width - 1) / span_u, (height - 1) / span_v)
    offset_x = 0.5 * ((width - 1) - scale * span_u)
    offset_y = 0.5 * ((height - 1) - scale * span_v)

    def screen(xu, xv):
        sx = offset_x + (xu - u0) * scale
        sy = offset_y + (v1 - xv) * scale
        return sx, sy

    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    order = np.argsort(-depth.mean(axis=1))  # back (larger depth) first
    for index in order:
        uu = u[index]
        vv = v[index]
        corners = [screen(uu[k], vv[k]) for k in range(3)]
        grey = int(40 + shade[index] * 200)
        draw.polygon(corners, fill=(grey, grey, grey))
    image.save(path)


def _roles(descriptor_path):
    import json
    if not descriptor_path.is_file():
        return {}
    descriptor = json.loads(descriptor_path.read_text())
    return {node["nodeID"]: node.get("role", "") for node in descriptor.get("nodes", [])}


def _largest_upfacing_top(model):
    """Return (area_mm2, depth_span_mm) for the largest near-up top facet, or None.

    Flat tops and rounded crests both produce up-facing facets; this is a
    comparison aid against a reference under the same metric, not a defect
    counter. A depth-spanning strip much larger than the reference *and* a
    bright band in the front render together suggest a prismatic flat wall.
    """
    points, normals = _triangles(model)
    if len(points) == 0:
        return None
    bounds_min = points.reshape(-1, 3).min(axis=0)
    bounds_max = points.reshape(-1, 3).max(axis=0)
    areas = 0.5 * np.linalg.norm(
        np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0]), axis=1
    )
    height = bounds_max[2] - bounds_min[2]
    if height <= 0:
        return None
    top = points[:, :, 2].mean(axis=1) > bounds_min[2] + 0.82 * height
    up = (normals[:, 2] > 0.9) & top
    if not up.any():
        return None
    spans = points[up][:, :, 1].max(axis=1) - points[up][:, :, 1].min(axis=1)
    index = int(np.argmax(areas[up]))
    return float(areas[up][index]), float(spans[index])


def _print_top_facet(stats, reference_stats=None, *, against_reference: bool = True):
    if stats is None:
        print("  info no up-facing top facet above the height threshold")
        return
    area, span = stats
    print(f"  info largest up-facing top facet: {area:.0f} mm^2, depth span {span:.0f} mm")
    if not against_reference:
        return
    if reference_stats is None:
        print(
            "  info flat tops and rounded crests both produce up-facing facets; "
            "compare this metric (and the front render) to a reference — not against zero"
        )
        return
    ref_area, ref_span = reference_stats
    print(
        f"  info reference same metric: {ref_area:.0f} mm^2, depth span {ref_span:.0f} mm "
        "(suspect only if the candidate is much larger/wider *and* the front render "
        "shows a bright depth-spanning band the reference lacks)"
    )


def _diagnostics(model, roles, reference_stats=None, *, against_reference: bool = True):
    print(f"  nodes: {len(model['nodes'])}")
    bounds_min = np.array([np.inf] * 3)
    bounds_max = np.array([-np.inf] * 3)
    for node_id, node in sorted(model["nodes"].items()):
        pts = _native(node)
        count = len(node["triangles"])
        print(f"    {node_id:26s} {count:6d} triangles  role={roles.get(node_id, '?')}")
        bounds_min = np.minimum(bounds_min, pts.min(axis=0))
        bounds_max = np.maximum(bounds_max, pts.max(axis=0))
    print(f"  modelBounds (mm): min {bounds_min.round(2).tolist()} max {bounds_max.round(2).tolist()}")
    _print_top_facet(
        _largest_upfacing_top(model),
        reference_stats,
        against_reference=against_reference,
    )
    for node_id, node in sorted(model["nodes"].items()):
        if roles.get(node_id) == "contact" and len(node["triangles"]) < 8:
            print(f"  info region {node_id} has only {len(node['triangles'])} triangles")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--asset")
    parser.add_argument("--reference", help="pre-migration usdz to render side by side")
    parser.add_argument("--out", default=str(REPOSITORY / ".context" / "previews"))
    args = parser.parse_args()

    asset = Path(args.asset) if args.asset else REPOSITORY / "Hangboards" / args.package / "assets" / "primary.usdz"
    if not asset.is_file():
        print(f"no compiled asset at {asset}; run compile_board.py first", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    reference_stats = None
    reference_model = None
    if args.reference:
        reference_path = Path(args.reference)
        if not reference_path.is_file():
            print(f"no reference asset at {reference_path}", file=sys.stderr)
            return 1
        reference_model = read_usdz(reference_path)
        reference_stats = _largest_upfacing_top(reference_model)

    print(f"candidate: {asset}")
    model = read_usdz(asset)
    _diagnostics(model, _roles(asset.parent / "primary.model.json"), reference_stats)
    points, normals = _triangles(model)
    for view in ("front", "side", "top"):
        path = out / f"{args.package}-{view}.png"
        _render(points, normals, view, path)
        print(f"  wrote {path}")

    if reference_model is not None:
        print(f"reference: {args.reference}")
        # Reference has no package descriptor beside it in the usual scratch
        # layout; print inventory without roles, and do not re-advise against itself.
        _diagnostics(reference_model, {}, against_reference=False)
        ref_points, ref_normals = _triangles(reference_model)
        for view in ("front", "side", "top"):
            _render(ref_points, ref_normals, view, out / f"{args.package}-ref-{view}.png")
        print("  wrote reference renders next to the candidate renders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
