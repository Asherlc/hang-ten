"""Independent small KKT oracles for the workspace-only coupled QP screen."""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sparse_contact_screen import FrozenQP, ScreenFailure, load_frozen, solve, residuals


def problem(h, force, equality, ec, contacts, cc):
    n = len(force)
    return FrozenQP(sparse.csc_matrix(h), np.array(force, dtype=float),
                    sparse.csr_matrix(np.array(equality, dtype=float).reshape(-1, n)),
                    np.array(ec, dtype=float),
                    sparse.csr_matrix(np.array(contacts, dtype=float).reshape(-1, n)),
                    np.array(cc, dtype=float), 1e-8)


def oracle(p):
    """Enumerate active sets using the original full regularized KKT."""
    h, e, a = p.h.toarray(), p.e.toarray(), p.a.toarray()
    n, ne, m = len(p.force), len(p.ec), len(p.cc)
    for flags in itertools.product((False, True), repeat=m):
        ids = np.flatnonzero(flags)
        j = np.vstack((e, a[ids]))
        k = np.block([[h, j.T], [j, -p.epsilon * np.eye(len(j))]])
        answer = np.linalg.solve(k, np.r_[p.force, -p.ec, -p.cc[ids]])
        x, lam = answer[:n], answer[n:]
        mu = np.zeros(m)
        mu[ids] = -lam[ne:]
        gap = a @ x + p.cc + p.epsilon * mu
        if np.min(mu, initial=0) >= -1e-12 and np.min(gap, initial=0) >= -1e-10:
            return x, lam[:ne], mu
    raise AssertionError("No oracle active set")


@pytest.mark.parametrize("p", [
    problem([[2]], [-.2], [], [], [[1]], [0]),
    # The omitted stronger row must displace the weaker dependent row.
    problem([[1]], [-1], [], [], [[1], [1], [2]], [0, -.2, -.4]),
    problem([[1]], [2], [], [], [[1], [1]], [0, -.2]),
    # Both independent cord coordinates couple through one shared height.
    problem(np.diag([.2, .2, .3, .3, 2]), [0, 0, 0, 0, -.1],
            [[1, 1, 0, 0, -1], [0, 0, 1, 1, -1]], [-.1, -.2],
            [[1, 0, 0, 0, 0], [0, 0, 1, 0, 0], [0, 1, 0, -1, 0]],
            [0, 0, -.1]),
    problem(np.diag([2, 3]), [1, -2], [[1, 1]], [-.3],
            [[1, -1], [-1, 0]], [-.2, 2]),
    problem(np.diag([2, 3]), [1, -2], [[1, 1]], [-.3], [], []),
])
def test_original_kkt_and_all_rows(p):
    expected, _, _ = oracle(p)
    result = solve(p)
    np.testing.assert_allclose(result.x, expected, atol=2e-8, rtol=0)
    r = residuals(p, result.x, result.lam, result.mu, result.slack)
    assert r["stationarity"] < 1e-10
    assert r["regularizedEquality"] < 1e-10
    assert r["regularizedContact"] < 1e-10
    assert r["regularizedComplementarity"] < 1e-14
    assert r["dualViolation"] == 0


def test_bound_is_failure_not_partial_success():
    p = problem([[1]], [-1], [], [], [[1]], [0])
    with pytest.raises(ScreenFailure, match="iteration limit"):
        solve(p, max_iterations=1)


def test_reject_nonfinite_input():
    p = problem([[1]], [float("nan")], [], [], [[1]], [0])
    with pytest.raises(ScreenFailure, match="Invalid"):
        solve(p)


def test_reject_indefinite_inertial_objective():
    p = problem([[-1]], [0], [], [], [[1]], [0])
    with pytest.raises(ScreenFailure, match="positive definite"):
        solve(p)


def test_regularized_kkt_success_does_not_override_affine_feasibility():
    # The exact regularized solution has ~20 nm of penetration. Small KKT
    # residuals cannot promote it past the unchanged 10 nm all-row gate.
    p = problem([[2]], [-2], [], [], [[1]], [0])
    with pytest.raises(ScreenFailure, match="iteration limit"):
        solve(p)


@pytest.mark.parametrize("seed", range(12))
def test_coupled_non_diagonal_hessian_against_full_kkt(seed):
    rng = np.random.default_rng(seed)
    matrix = rng.normal(size=(4, 4))
    h = .1 * (matrix.T @ matrix + np.eye(4))
    e = np.array([[1., -.5, .7, .2]])
    a = rng.normal(size=(5, 4))
    feasible = .001 * rng.normal(size=4)
    p = problem(h, .01 * rng.normal(size=4), e, -e @ feasible,
                a, -a @ feasible + rng.uniform(.0001, .001, size=5))
    expected, _, _ = oracle(p)
    answer = solve(p)
    np.testing.assert_allclose(answer.x, expected, atol=2e-8, rtol=0)


def test_equality_only_cannot_override_feasibility():
    p = problem([[1]], [10], [[1]], [0], [], [])
    with pytest.raises(ScreenFailure, match="Equality-only"):
        solve(p)


def test_capture_loader_preserves_attachment_curvature_and_other_rope(tmp_path):
    doc = {
        "weights": [[0, 2, 0], [0, 4, 0]],
        "positions": [[[0, 0, 0], [1, 0, 0], [2, 0, 0]]] * 2,
        "prediction": [[[0, 0, 0], [1, .1, 0], [2, 0, 0]],
                       [[0, 0, 0], [1, .2, 0], [2, 0, 0]]],
        "boardMass": .15, "boardHeight": .1, "predictionHeight": .2,
        "attachments": [{"2": [2, 0, 0]}, {}],
        "distanceTension": [[.2, .3], [0, 0]], "regularization": 1e-8,
        "rows": [
            {"particles": [0, 1], "gradients": [[-1, 0, 0], [1, 0, 0]],
             "rope": 0, "secondRope": -1, "boardGradient": -1,
             "contact": False, "residual": -.01},
            {"particles": [1, 2, 0, 1],
             "gradients": [[1, 0, 0], [0, 0, 0], [0, 0, 0], [-1, 0, 0]],
             "rope": 0, "secondRope": 1, "boardGradient": .7,
             "contact": True, "residual": -.02},
        ],
    }
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(doc))
    p = load_frozen(path)
    expected = np.diag([.5, 1, 1, .25, .25, .25, .45])
    expected[1, 6] = expected[6, 1] = -.3
    np.testing.assert_allclose(p.h.toarray(), expected, atol=1e-15, rtol=0)
    np.testing.assert_allclose(p.force, [0, .05, 0, 0, .05, 0, .015], atol=1e-15, rtol=0)
    np.testing.assert_array_equal(p.e.toarray(), [[1, 0, 0, 0, 0, 0, -1]])
    np.testing.assert_array_equal(p.a.toarray(), [[1, 0, 0, -1, 0, 0, .7]])
    np.testing.assert_array_equal(p.ec, [-.01])
    np.testing.assert_array_equal(p.cc, [-.02])
    assert p.epsilon == 1e-8
