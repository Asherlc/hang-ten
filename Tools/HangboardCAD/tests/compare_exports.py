"""Sampled geometric comparison between two exported USDZ models.

This is a regression check against the approved reference asset, not a build
input: the compiler never reads it. It samples surface points on each model and
measures the distance to the other model's triangles in both directions, so a
one-sided comparison cannot hide a missing feature.

    .context/organic-shark/venv/bin/python Tools/HangboardCAD/tests/compare_exports.py \
        <reference.usdz> <candidate.usdz> [--limit-mm 0.5]

The result is a sampled bound, not an exact Hausdorff distance and not a claim
about physical product accuracy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from usdz_writer import read_usdz  # noqa: E402


def triangles(model) -> np.ndarray:
    rows = []
    for node in model["nodes"].values():
        points = np.asarray(node["points_m"], dtype=np.float64) * 1000.0
        for triangle in node["triangles"]:
            rows.append(points[list(triangle)])
    return np.asarray(rows)


def sample_points(model, per_triangle: int = 6) -> np.ndarray:
    rows = []
    for node in model["nodes"].values():
        points = np.asarray(node["points_m"], dtype=np.float64) * 1000.0
        for triangle in node["triangles"]:
            a, b, c = points[list(triangle)]
            for u, v in (
                (1 / 3, 1 / 3),
                (0.5, 0.0),
                (0.0, 0.5),
                (0.25, 0.25),
                (0.2, 0.6),
                (0.6, 0.2),
            )[:per_triangle]:
                rows.append(a + u * (b - a) + v * (c - a))
    return np.asarray(rows)


def point_to_triangle_distance(points: np.ndarray, tris: np.ndarray, chunk: int = 2048) -> np.ndarray:
    """Exact point-to-triangle distance, chunked over query points.

    A point outside the triangle's projection is closest to one of its three
    edges, and a segment distance already covers both of its endpoints, so the
    result is ``min(plane distance if inside, three segment distances)``. The
    inside test is a real barycentric test; an edge-only test would silently
    return the wrong surface.
    """
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, ac, bc = b - a, c - a, c - b
    normals = np.cross(ab, ac)
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-18)
    d00 = np.einsum("ki,ki->k", ab, ab)
    d01 = np.einsum("ki,ki->k", ab, ac)
    d11 = np.einsum("ki,ki->k", ac, ac)
    denom = np.maximum(d00 * d11 - d01 * d01, 1e-18)
    out = np.empty(len(points), dtype=np.float64)
    for start in range(0, len(points), chunk):
        block = points[start : start + chunk]
        d = block[:, None, :] - a[None, :, :]
        d20 = np.einsum("bki,ki->bk", d, ab)
        d21 = np.einsum("bki,ki->bk", d, ac)
        v = (d11[None, :] * d20 - d01[None, :] * d21) / denom[None, :]
        w = (d00[None, :] * d21 - d01[None, :] * d20) / denom[None, :]
        u = 1.0 - v - w
        inside = (u >= 0.0) & (v >= 0.0) & (w >= 0.0)
        plane = np.abs(np.einsum("bki,ki->bk", d, normals))
        best = np.where(inside, plane, np.inf)

        def segment(start_point, direction, squared):
            t = np.clip(
                np.einsum("bki,ki->bk", block[:, None, :] - start_point[None, :, :], direction)
                / np.maximum(squared, 1e-18)[None, :],
                0.0,
                1.0,
            )
            closest = start_point + t[:, :, None] * direction
            return np.linalg.norm(block[:, None, :] - closest, axis=2)

        best = np.minimum(best, segment(a, ab, d00))
        best = np.minimum(best, segment(b, bc, np.einsum("ki,ki->k", bc, bc)))
        best = np.minimum(best, segment(a, ac, d11))
        out[start : start + chunk] = best.min(axis=1)
    return out


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: {text!r}") from None
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference")
    parser.add_argument("candidate")
    parser.add_argument("--limit-mm", type=float, default=0.5)
    parser.add_argument(
        "--chunk",
        type=positive_int,
        default=2048,
        help="query points per block; lower it for dense meshes (memory is chunk x triangles)",
    )
    arguments = parser.parse_args(argv)

    reference = read_usdz(Path(arguments.reference))
    candidate = read_usdz(Path(arguments.candidate))
    reference_tris = triangles(reference)
    candidate_tris = triangles(candidate)

    forward = point_to_triangle_distance(
        sample_points(candidate), reference_tris, chunk=arguments.chunk
    )
    backward = point_to_triangle_distance(
        sample_points(reference), candidate_tris, chunk=arguments.chunk
    )

    print(f"reference triangles {len(reference_tris)}, candidate triangles {len(candidate_tris)}")
    print(f"candidate -> reference: {len(forward)} samples, max {forward.max():.4f} mm")
    print(f"reference -> candidate: {len(backward)} samples, max {backward.max():.4f} mm")
    worst = max(forward.max(), backward.max())
    print(f"worst sampled deviation {worst:.4f} mm (limit {arguments.limit_mm} mm)")
    if worst > arguments.limit_mm:
        print("SAMPLED COMPARISON FAILED")
        return 1
    print("sampled comparison passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
