"""Regression tests for explicit, review-scoped hardware removal."""

import sys
from pathlib import Path
import numpy as np
import pytest

pytest.importorskip("pxr")
pytest.importorskip("shapely")
pytest.importorskip("networkx")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_mounting_bore_repair_closes_through_opening():
    import remove_mounting_bores as repair

    # Annular planar surface with a square aperture; only the specified aperture
    # may be repaired. The exterior boundary is deliberately left untouched.
    v = np.array(
        [
            [-2, -2, 0],
            [2, -2, 0],
            [2, 2, 0],
            [-2, 2, 0],
            [-0.2, -0.2, 0],
            [0.2, -0.2, 0],
            [0.2, 0.2, 0],
            [-0.2, 0.2, 0],
        ],
        float,
    )
    f = np.array(
        [
            [0, 1, 5],
            [0, 5, 4],
            [1, 2, 6],
            [1, 6, 5],
            [2, 3, 7],
            [2, 7, 6],
            [3, 0, 4],
            [3, 4, 7],
        ]
    )
    # This fixture exercises the explicit boundary-patch generator independently
    # of an exporter: no outside vertices or unrelated components are changed.
    patch_v, patch_f = repair.patch_loop(v[[4, 5, 6, 7]])
    assert np.allclose(patch_v[:4], v[[4, 5, 6, 7]])
    assert np.isfinite(patch_v).all()
    area = (
        np.linalg.norm(
            np.cross(
                patch_v[patch_f[:, 1]] - patch_v[patch_f[:, 0]],
                patch_v[patch_f[:, 2]] - patch_v[patch_f[:, 0]],
            ),
            axis=1,
        ).sum()
        / 2
    )
    assert area == pytest.approx(0.16)
    assert (patch_v[:, 2] == 0).all()


def test_invalid_non_simple_boundary_is_rejected():
    import remove_mounting_bores as repair

    with pytest.raises(ValueError):
        repair.patch_loop(np.array([[0, 0, 0], [1, 1, 0], [0, 1, 0], [1, 0, 0]], float))


def test_explicit_nonplanar_patch_preserves_boundary_topology():
    import remove_mounting_bores as repair

    p = np.array(
        [[0, 0, 0], [1, 0, 0], [1, 0, 1], [1, 1, 1], [0, 1, 1], [0, 1, 0]], float
    )
    v, f = repair.patch_loop(p, nonplanar=True)
    assert np.array_equal(v, p)
    edges = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    unique, count = np.unique(edges, axis=0, return_counts=True)
    boundary = {tuple(e) for e in unique[count == 1]}
    assert boundary == {tuple(sorted((i, (i + 1) % len(p)))) for i in range(len(p))}
    assert count.max() == 2


def test_source_sha_mismatch_does_not_create_output(tmp_path):
    import remove_mounting_bores as repair

    source = tmp_path / "original.usdz"
    source.write_bytes(b"not the reviewed revision")
    target = tmp_path / "out" / "primary.usdz"
    with pytest.raises(ValueError, match="source SHA mismatch"):
        repair.repair_file(
            source, target, {"sha256": "0" * 64}, tmp_path / "descriptor.json"
        )
    assert not target.exists()


def test_dangling_boundary_is_rejected_instead_of_filled():
    import remove_mounting_bores as repair

    with pytest.raises(ValueError, match="dangling"):
        repair._loops(np.array([[0, 1], [1, 2], [2, 0], [2, 3]]))


def test_inline_overwrite_is_rejected(tmp_path):
    import remove_mounting_bores as repair

    path = tmp_path / "primary.usdz"
    with pytest.raises(ValueError, match="separate output"):
        repair.repair_file(path, path, {}, tmp_path / "primary.model.json")
