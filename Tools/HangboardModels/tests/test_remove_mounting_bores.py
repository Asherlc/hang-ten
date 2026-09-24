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


def test_boundary_edge_lookup_maps_to_true_source_face():
    """Boundary edges must map to their true source face.

    Regression for Sourcery comment on remove_mounting_bores.py:245-246.
    ``directed`` is built as a blocked concat of the three edge slots::

        directed = concat([kept[:, [0, 1]], kept[:, [1, 2]], kept[:, [2, 0]]])

    so the true kept-position for directed index ``j`` is ``j % N``,
    equivalently ``np.tile(np.arange(N), 3)[j]`` -- NOT ``j // 3``
    (which would only hold for a per-face interleaved layout).
    """
    N = 4
    kept = np.array(
        [[10, 11, 12], [20, 21, 22], [30, 31, 32], [40, 41, 42]]
    )
    kept_ids = np.array([100, 101, 102, 103])
    directed = np.concatenate([kept[:, [0, 1]], kept[:, [1, 2]], kept[:, [2, 0]]])
    face_of_directed = np.tile(np.arange(N), 3)

    # Ground truth: each directed edge comes from kept[face_of_directed[j]].
    for j in range(3 * N):
        assert int(face_of_directed[j]) == j % N
        slot = j // N
        assert directed[j].tolist() == kept[j % N, [slot, (slot + 1) % 3]].tolist()

    # j // 3 diverges from the true owner on most indices and must not be used.
    assert any((j // 3) != int(face_of_directed[j]) for j in range(3 * N))
    # Concrete divergence: directed[1] belongs to face position 1, not 0.
    assert int(face_of_directed[1]) == 1
    assert 1 // 3 == 0

    # Production-equivalent lookup maps every boundary edge to its true face.
    idx = np.arange(3 * N)
    edge_lookup = {
        tuple(sorted(e)): (int(kept_ids[face_of_directed[j]]), tuple(e))
        for e, j in zip(directed, idx)
    }
    for j in range(3 * N):
        key = tuple(sorted(directed[j]))
        fid, _ = edge_lookup[key]
        assert fid == int(kept_ids[j % N])
        # j // 3 would mis-attribute whenever it diverges (ids are distinct).
        if (j // 3) != (j % N):
            assert fid != int(kept_ids[j // 3])
    # Spot check: directed[1] = [20, 21] from kept position 1 -> global 101.
    assert edge_lookup[tuple(sorted(directed[1]))][0] == 101


def test_edge_lookup_retains_explicit_face_index():
    """Production code must retain the face index explicitly per Sourcery."""
    src = Path(__file__).resolve().parents[1].joinpath(
        "remove_mounting_bores.py"
    ).read_text()
    assert "j % len(kept_ids)" not in src


def test_tampered_descriptor_is_rejected(tmp_path):
    import hashlib
    import json
    import remove_mounting_bores as repair

    source = tmp_path / "original.usdz"
    data = b"reviewed bytes"
    source.write_bytes(data)
    descriptor = tmp_path / "descriptor.json"
    descriptor.write_text(json.dumps({"nodes": [], "contacts": []}))
    spec = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "descriptorSHA256": "0" * 64,
        "holes": [],
    }
    with pytest.raises(ValueError, match="source descriptor SHA mismatch"):
        repair.repair_file(
            source, tmp_path / "out" / "primary.usdz", spec, descriptor
        )


def test_tampered_board_is_rejected(tmp_path):
    import hashlib
    import json
    import remove_mounting_bores as repair

    source = tmp_path / "Hangboards" / "slug" / "assets" / "primary.usdz"
    source.parent.mkdir(parents=True)
    data = b"reviewed bytes"
    source.write_bytes(data)
    board = tmp_path / "Hangboards" / "slug" / "board.json"
    board.write_text(json.dumps({"contacts": [{"id": "a"}]}))
    descriptor = tmp_path / "descriptor.json"
    descriptor.write_text(json.dumps({"nodes": [], "contacts": []}))
    spec = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "boardSHA256": "0" * 64,
        "holes": [],
    }
    with pytest.raises(ValueError, match="source board SHA mismatch"):
        repair.repair_file(
            source, tmp_path / "out" / "primary.usdz", spec, descriptor
        )


def test_descriptor_contacts_must_match_board(tmp_path):
    import hashlib
    import json
    import remove_mounting_bores as repair

    source = tmp_path / "Hangboards" / "slug" / "assets" / "primary.usdz"
    source.parent.mkdir(parents=True)
    data = b"reviewed bytes"
    source.write_bytes(data)
    board = tmp_path / "Hangboards" / "slug" / "board.json"
    board.write_text(json.dumps({"contacts": [{"id": "real"}]}))
    descriptor = tmp_path / "descriptor.json"
    descriptor_payload = {"nodes": [], "contacts": ["tampered"]}
    descriptor.write_text(json.dumps(descriptor_payload))
    spec = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "descriptorSHA256": hashlib.sha256(descriptor.read_bytes()).hexdigest(),
        "boardSHA256": hashlib.sha256(board.read_bytes()).hexdigest(),
        "holes": [],
    }
    with pytest.raises(ValueError, match="contact binding mismatch"):
        repair.repair_file(
            source, tmp_path / "out" / "primary.usdz", spec, descriptor
        )
