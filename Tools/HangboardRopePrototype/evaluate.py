"""Measure transient Bullet rope against the exact Mini Bar body triangles."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def _closest_on_triangle(point: np.ndarray, triangle: np.ndarray) -> np.ndarray:
    """Closest point on a triangle, including edge and vertex Voronoi regions."""
    a, b, c = triangle
    ab, ac, ap = b - a, c - a, point - a
    d1, d2 = np.dot(ab, ap), np.dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return a
    bp = point - b
    d3, d4 = np.dot(ab, bp), np.dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return b
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        return a + (d1 / (d1 - d3)) * ab
    cp = point - c
    d5, d6 = np.dot(ab, cp), np.dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return c
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        return a + (d2 / (d2 - d6)) * ac
    va = d3 * d6 - d5 * d4
    if va <= 0 and d4 - d3 >= 0 and d5 - d6 >= 0:
        edge = c - b
        return b + ((d4 - d3) / ((d4 - d3) + (d5 - d6))) * edge
    denom = 1 / (va + vb + vc)
    return a + ab * (vb * denom) + ac * (vc * denom)


def _segment_segment_distance(p: np.ndarray, q: np.ndarray,
                              a: np.ndarray, b: np.ndarray) -> float:
    u, v, w = q - p, b - a, p - a
    uu, uv, vv = np.dot(u, u), np.dot(u, v), np.dot(v, v)
    uw, vw = np.dot(u, w), np.dot(v, w)
    den = uu * vv - uv * uv
    if den < 1e-18:
        s = 0.
    else:
        s = float(np.clip((uv * vw - vv * uw) / den, 0, 1))
    t = float(np.clip((uv * s + vw) / vv, 0, 1)) if vv > 0 else 0.
    s = float(np.clip((uv * t - uw) / uu, 0, 1)) if uu > 0 else 0.
    return float(np.linalg.norm(w + s * u - t * v))


def _ray_triangle(origin: np.ndarray, direction: np.ndarray, triangle: np.ndarray) -> float | None:
    a, b, c = triangle
    edge1, edge2 = b - a, c - a
    h = np.cross(direction, edge2)
    det = float(np.dot(edge1, h))
    if abs(det) < 1e-12:
        return None
    inv = 1 / det
    s = origin - a
    u = inv * np.dot(s, h)
    if u < -1e-9 or u > 1 + 1e-9:
        return None
    q = np.cross(s, edge1)
    v = inv * np.dot(direction, q)
    if v < -1e-9 or u + v > 1 + 1e-9:
        return None
    t = float(inv * np.dot(edge2, q))
    return t if t > 1e-9 else None


def segment_triangle_distance(start: np.ndarray, end: np.ndarray, triangle: np.ndarray) -> float:
    direction = end - start
    hit = _ray_triangle(start, direction, triangle)
    if hit is not None and hit <= 1:
        return 0.
    distances = [np.linalg.norm(start - _closest_on_triangle(start, triangle)),
                 np.linalg.norm(end - _closest_on_triangle(end, triangle))]
    for index in range(3):
        distances.append(_segment_segment_distance(start, end, triangle[index], triangle[(index + 1) % 3]))
    return float(min(distances))


def point_inside_mesh(point: np.ndarray, triangles: np.ndarray) -> bool:
    direction = np.array([1., .371, .173])
    hits = [_ray_triangle(point, direction, triangle) for triangle in triangles]
    unique = {round(hit, 8) for hit in hits if hit is not None}
    return len(unique) % 2 == 1


def contact_grade(clearance: float, *, penetration_limit: float = .0005,
                  gap_limit: float = .001) -> bool:
    return -penetration_limit - 1e-12 <= clearance <= gap_limit + 1e-12


def routes_separate(left: np.ndarray, right: np.ndarray, *, radius: float,
                    minimum_clearance: float) -> bool:
    # The shared pull point is deliberately omitted by the caller.
    distances = np.linalg.norm(left[:, None, :] - right[None, :, :], axis=2)
    return float(np.min(distances)) - 2 * radius >= minimum_clearance


def repeatable(first: np.ndarray, second: np.ndarray, *, tolerance: float) -> bool:
    return first.shape == second.shape and float(np.max(np.linalg.norm(first - second, axis=1))) <= tolerance


def signed_surface_clearance(point: np.ndarray, triangles: np.ndarray, radius: float) -> float:
    """Use the nearest oriented face because the USDZ has unwelded/open edges."""
    best = math.inf
    signed = math.inf
    for triangle in triangles:
        nearest = _closest_on_triangle(point, triangle)
        delta = point - nearest
        distance = float(np.linalg.norm(delta))
        if distance < best:
            best = distance
            normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
            signed = (-distance if np.dot(delta, normal) < 0 else distance) - radius
    return signed


def _measure_route(points: np.ndarray, triangles: np.ndarray, radius: float,
                   center: np.ndarray, opposite: np.ndarray,
                   body_x_bounds: tuple[float, float]) -> dict:
    triangle_min = triangles.min(axis=1)
    triangle_max = triangles.max(axis=1)
    signed = []
    contact = []
    for point in points[1:-1]:
        clearance = signed_surface_clearance(point, triangles, radius)
        signed.append(clearance)
        if (body_x_bounds[0] <= point[0] <= body_x_bounds[1] and
                np.dot(point - center, opposite) > 0):
            contact.append(clearance)
    # An endpoint can miss a thin face; inspect every segment whose box reaches
    # the body. The exact segment-triangle routine also catches crossings.
    segment_minimum = math.inf
    for start, end in zip(points[:-1], points[1:]):
        low, high = np.minimum(start, end) - radius, np.maximum(start, end) + radius
        candidates = np.flatnonzero(np.all(triangle_max >= low, axis=1) &
                                    np.all(triangle_min <= high, axis=1))
        for index in candidates:
            segment_minimum = min(segment_minimum,
                                  segment_triangle_distance(start, end, triangles[index]))
    return {
        "minimumClearanceM": float(min(signed)) if signed else None,
        "largestExpectedContactGapM": float(max(contact)) if contact else None,
        "expectedContactSamples": len(contact),
        "minimumSegmentSurfaceDistanceM": float(segment_minimum) if math.isfinite(segment_minimum) else None,
        "centerlineLengthM": float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1))),
    }


def _render(triangles: np.ndarray, routes: dict[str, np.ndarray], path: Path,
            camera: str, title: str) -> None:
    fig = plt.figure(figsize=(8, 6), dpi=150)
    if camera == "side":
        from matplotlib.collections import PolyCollection
        ax = fig.add_subplot(111)
        ax.add_collection(PolyCollection(triangles[:, :, [1, 2]],
                                         facecolor="#b7b8b9", edgecolor="#777a7d",
                                         linewidth=.12, alpha=.35))
        for index, (name, points) in enumerate(sorted(routes.items())):
            ax.plot(points[:, 1], points[:, 2], linewidth=2,
                    color=("#bd3b34", "#196aad")[index], label=name)
        all_points = np.concatenate([triangles.reshape(-1, 3), *routes.values()])
        ax.set_xlim(all_points[:, 1].min() - .01, all_points[:, 1].max() + .01)
        ax.set_ylim(all_points[:, 2].min() - .01, all_points[:, 2].max() + .01)
        ax.set_aspect("equal")
        ax.set_xlabel("Y (m)"); ax.set_ylabel("Z (m)")
        ax.set_title(title); ax.legend(loc="upper right")
        fig.tight_layout(); fig.savefig(path); plt.close(fig)
        return
    ax = fig.add_subplot(111, projection="3d")
    surface = Poly3DCollection(triangles, alpha=.45, facecolor="#b7b8b9",
                               edgecolor="#5c6065", linewidth=.13)
    ax.add_collection3d(surface)
    for index, (name, points) in enumerate(sorted(routes.items())):
        ax.plot(points[:, 0], points[:, 1], points[:, 2], linewidth=2.2,
                color=("#bd3b34", "#196aad")[index], label=name)
    all_points = np.concatenate([triangles.reshape(-1, 3), *routes.values()])
    low, high = all_points.min(axis=0), all_points.max(axis=0)
    mid = (low + high) / 2
    reach = max(high - low) / 2 + .015
    ax.set_xlim(mid[0] - reach, mid[0] + reach)
    ax.set_ylim(mid[1] - reach, mid[1] + reach)
    ax.set_zlim(mid[2] - reach, mid[2] + reach)
    ax.set_xlabel("X (m)"); ax.set_ylabel("Y (m)"); ax.set_zlabel("Z (m)")
    if camera == "front": ax.view_init(elev=10, azim=-90)
    elif camera == "side": ax.view_init(elev=0, azim=0)
    else: ax.view_init(elev=22, azim=-60)
    ax.set_title(title)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def evaluate(case_path: Path, result_dir: Path, repeat_dir: Path | None = None) -> dict:
    case = json.loads(Path(case_path).read_text())
    result_dir = Path(result_dir)
    manifest = json.loads((result_dir / "manifest.json").read_text())
    vertices = np.array(case["vertices"], dtype=float)
    faces = np.array(case["faces"], dtype=int)
    anchor = np.array(case["anchor"], dtype=float)
    radii = {loop["id"]: loop["radius"] for loop in case["loops"]}
    report = {"sources": manifest["sources"], "bulletRevision": manifest["bulletRevision"], "runs": []}
    for run in manifest["runs"]:
        pose = case["poses"][run["pose"]]
        x, y, z, w = pose["rotation"]
        rotation = np.array([
            [1 - 2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
            [2*(x*y+z*w), 1 - 2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w), 2*(y*z+x*w), 1 - 2*(x*x+y*y)],
        ])
        body = vertices @ rotation.T + np.array(pose["translation"])
        triangles = body[faces]
        center = (body.min(axis=0) + body.max(axis=0)) / 2
        opposite = center - anchor
        opposite[0] = 0
        result = json.loads(Path(run["path"]).read_text())
        routes = {name: np.array(value["centerline"], dtype=float)
                  for name, value in result.get("loops", {}).items()}
        repeat_ok = None
        if repeat_dir is not None:
            second = json.loads((Path(repeat_dir) / run["pose"] /
                                 f"{run['lengthMode']}.json").read_text())
            second_routes = {name: np.array(value["centerline"], dtype=float)
                             for name, value in second.get("loops", {}).items()}
            repeat_ok = (result.get("status") == second.get("status") and
                         set(routes) == set(second_routes) and
                         all(repeatable(routes[name], second_routes[name], tolerance=1e-5)
                             for name in routes))
        metrics = {}
        for name, points in routes.items():
            metrics[name] = _measure_route(points, triangles, radii[name], center, opposite,
                                           (float(body[:, 0].min()), float(body[:, 0].max())))
        separate = (len(routes) == 2 and
                    routes_separate(routes["left-loop"][55:-55], routes["right-loop"][55:-55],
                                    radius=max(radii.values()), minimum_clearance=.001))
        anchor_ok = all(np.linalg.norm(points[0] - anchor) < 1e-5 and
                        np.linalg.norm(points[-1] - anchor) < 1e-5 for points in routes.values())
        contact_ok = bool(metrics) and all(
            item["expectedContactSamples"] > 0 and
            item["largestExpectedContactGapM"] is not None and
            item["largestExpectedContactGapM"] <= .001 and
            item["minimumClearanceM"] >= -.0005 and
            item["minimumSegmentSurfaceDistanceM"] >= radii[name] - .0005
            for name, item in metrics.items())
        accepted = bool(run["accepted"] and separate and anchor_ok and contact_ok and repeat_ok is not False)
        reasons = [key for key, okay in (("solver_or_slack", run["accepted"]),
                                         ("loop_separation", separate),
                                         ("anchor", anchor_ok),
                                         ("exact_mesh_contact", contact_ok),
                                         ("repeatability", repeat_ok is not False)) if not okay]
        entry = {"pose": run["pose"], "lengthMode": run["lengthMode"],
                 "solverStatus": run["status"], "accepted": accepted,
                 "failedChecks": reasons, "loops": metrics,
                 "loopSeparation": separate, "anchor": anchor_ok,
                 "repeatable": repeat_ok}
        report["runs"].append(entry)
        if routes:
            for camera in ("front", "side", "oblique"):
                path = result_dir / run["pose"] / f"{run['lengthMode']}-{camera}.png"
                _render(triangles, routes, path, camera,
                        f"{run['pose']} / {run['lengthMode']} / {camera} / {'PASS' if accepted else 'FAIL'}")
    (result_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    lines = ["# Mini Bar Bullet rope contact findings", "", "| Pose | Length | Solver | Contact | Result |",
             "|---|---|---|---|---|"]
    for row in report["runs"]:
        lines.append(f"| {row['pose']} | {row['lengthMode']} | {row['solverStatus']} | "
                     f"{'pass' if 'exact_mesh_contact' not in row['failedChecks'] else 'fail'} | "
                     f"{'PASS' if row['accepted'] else ', '.join(row['failedChecks'])} |")
    lines += ["", "Criterion: <=1 mm expected contact gap, <=0.5 mm penetration, "
              "separate loops, common anchor, solver convergence. The collider is a convex hull; "
              "all reported distances use the exact USDZ body triangles."]
    (result_dir / "findings.md").write_text("\n".join(lines) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("--repeat-results", type=Path)
    args = parser.parse_args()
    output = evaluate(args.case, args.results, args.repeat_results)
    print(json.dumps({"runs": len(output["runs"]), "accepted": sum(run["accepted"] for run in output["runs"])}))
