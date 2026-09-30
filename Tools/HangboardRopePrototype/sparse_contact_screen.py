"""Bounded sparse-primal contact experiment; never imported by either app.

Solve the same explicitly regularized frozen KKT as RopeContactSystem:
  H x + E.T lambda - A.T mu = force
  E x + ec - epsilon lambda = 0
  A x + cc + epsilon mu = slack >= 0, mu >= 0, slack * mu = 0.

The contact Newton block is eliminated into H + A.T D A. This retains every
row and the joint equality/height system, while avoiding a dense contact-space
response matrix. A Mehrotra predictor/corrector uses the same sparse factor for
both directions. Regularization is an input, never a conditioning knob.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import scipy
from scipy import sparse
from scipy.linalg import cholesky_banded
from scipy.sparse.linalg import splu


class ScreenFailure(RuntimeError):
    """No correction may be accepted after this failure."""


@dataclass
class FrozenQP:
    h: sparse.csc_matrix
    force: np.ndarray
    e: sparse.csr_matrix
    ec: np.ndarray
    a: sparse.csr_matrix
    cc: np.ndarray
    epsilon: float


@dataclass
class Result:
    x: np.ndarray
    lam: np.ndarray
    mu: np.ndarray
    slack: np.ndarray
    trace: list = field(default_factory=list)
    timings: dict = field(default_factory=dict)


def norm(v):
    return float(np.max(np.abs(v), initial=0))


def residuals(p, x, lam, mu, slack):
    contact = p.a @ x + p.cc
    equality = p.e @ x + p.ec
    gap = contact + p.epsilon * mu
    return {
        "stationarity": norm(p.h @ x - p.force + p.e.T @ lam - p.a.T @ mu),
        "regularizedEquality": norm(equality - p.epsilon * lam),
        "regularizedContact": norm(gap - slack),
        "regularizedComplementarity": norm(mu * gap),
        "dualViolation": float(max(0, -np.min(mu, initial=0))),
        "slackViolation": float(max(0, -np.min(slack, initial=0))),
        "allRowFeasibility": float(max(norm(equality), -np.min(contact, initial=0))),
        "objective": float(.5 * x @ (p.h @ x) - p.force @ x),
    }


def validate(p):
    n, ne, m = len(p.force), len(p.ec), len(p.cc)
    if (n == 0 or n > 50_256 or m > 100_000 or p.h.shape != (n, n)
            or p.e.shape != (ne, n) or p.a.shape != (m, n)
            or not np.isfinite(p.epsilon) or p.epsilon <= 0
            or any(not np.all(np.isfinite(v)) for v in
                   (p.h.data, p.force, p.e.data, p.ec, p.a.data, p.cc))
            or norm((p.h - p.h.T).data) > 1e-14):
        raise ScreenFailure("Invalid frozen QP")
    # Validation is included in cold timing. Contact curvature must not conceal
    # a bad inertial Hessian. This screen accepts only SPD H as in the solver.
    lower = sparse.tril(p.h).tocoo()
    bandwidth = int(np.max(lower.row - lower.col, initial=0))
    if n * (bandwidth + 1) > 8_000_000:
        raise ScreenFailure("Excessive inertial validation storage")
    band = np.zeros((bandwidth + 1, n))
    band[lower.row - lower.col, lower.col] = lower.data
    try:
        cholesky_banded(band, lower=True, check_finite=False)
    except np.linalg.LinAlgError as error:
        raise ScreenFailure("Inertial objective must be positive definite") from error


def factor_system(h, e, epsilon):
    """Diagonal congruence scales arithmetic without changing the KKT."""
    ne = e.shape[0]
    k = sparse.bmat([[h, e.T], [e, -epsilon * sparse.eye(ne)]], format="csc")
    row_max = np.asarray(abs(k).max(axis=1).toarray()).ravel()
    if np.any(row_max <= 0):
        raise ScreenFailure("Singular sparse primal system")
    scale = 1 / np.sqrt(row_max)
    scaling = sparse.diags(scale)
    lu = splu((scaling @ k @ scaling).tocsc(), permc_spec="COLAMD")

    def apply(rhs):
        answer = scale * lu.solve(scale * rhs)
        # Refinement uses the ORIGINAL KKT, not the scaled residual alone.
        for _ in range(3):
            error = rhs - k @ answer
            if norm(error) <= 1e-12 * max(1., norm(rhs)):
                break
            answer += scale * lu.solve(scale * error)
        if not np.all(np.isfinite(answer)):
            raise ScreenFailure("Nonfinite sparse correction")
        return answer

    return apply, k.nnz, lu.L.nnz + lu.U.nnz


def solve(p, *, max_iterations=50):
    if not 1 <= max_iterations <= 50:
        raise ScreenFailure("Invalid iteration bound")
    started = time.perf_counter()
    validate(p)
    n, m = len(p.force), len(p.cc)
    setup_started = time.perf_counter()
    equality_factor, _, _ = factor_system(p.h, p.e, p.epsilon)
    initial = equality_factor(np.r_[p.force, -p.ec])
    x, lam = initial[:n], initial[n:]
    mu = np.full(m, 1e-3)
    slack = np.maximum(1e-5, p.a @ x + p.cc + p.epsilon * mu)
    trace = []
    timings = {"validation": setup_started - started,
               "equalitySetup": time.perf_counter() - setup_started,
               "aggregation": 0., "factor": 0., "directions": 0., "residuals": 0.}

    for iteration in range(max_iterations + 1):
        stamp = time.perf_counter()
        checked = residuals(p, x, lam, mu, slack)
        timings["residuals"] += time.perf_counter() - stamp
        if (checked["stationarity"] <= 1e-10
                and checked["regularizedEquality"] <= 1e-10
                and checked["regularizedContact"] <= 1e-10
                and checked["regularizedComplementarity"] <= 1e-14
                and checked["allRowFeasibility"] <= 1e-8
                and checked["dualViolation"] == 0 and checked["slackViolation"] == 0):
            timings["total"] = time.perf_counter() - started
            return Result(x, lam, mu, slack, trace, timings)
        if iteration == max_iterations:
            raise ScreenFailure(f"Sparse primal iteration limit; last residuals={checked}")
        if m == 0:
            raise ScreenFailure("Equality-only correction fails all-row feasibility")

        rd = p.force - p.h @ x - p.e.T @ lam + p.a.T @ mu
        re = -p.ec - p.e @ x + p.epsilon * lam
        rp = -p.cc - p.a @ x - p.epsilon * mu + slack
        stamp = time.perf_counter()
        diagonal = 1 / (p.epsilon + slack / mu)
        augmented = p.h + p.a.T @ p.a.multiply(diagonal[:, None])
        timings["aggregation"] += time.perf_counter() - stamp
        stamp = time.perf_counter()
        apply, k_nnz, lu_nnz = factor_system(augmented, p.e, p.epsilon)
        timings["factor"] += time.perf_counter() - stamp

        def direction(rc):
            contact_rhs = rp + rc / mu
            answer = apply(np.r_[rd + p.a.T @ (diagonal * contact_rhs), re])
            dx, dl = answer[:n], answer[n:]
            dm = diagonal * (contact_rhs - p.a @ dx)
            ds = (rc - slack * dm) / mu
            return dx, dl, dm, ds

        def fraction(value, change, safety=1.):
            decreasing = change < 0
            return min(1., safety * float(np.min(-value[decreasing] / change[decreasing], initial=np.inf)))

        stamp = time.perf_counter()
        ax, al, am, ass = direction(-slack * mu)
        ap, ad = fraction(slack, ass), fraction(mu, am)
        mean = float(slack @ mu / m)
        predicted = float((slack + ap * ass) @ (mu + ad * am) / m)
        sigma = np.clip(predicted / mean, 0., 1.) ** 3
        dx, dl, dm, ds = direction(sigma * mean - slack * mu - ass * am)
        ap, ad = fraction(slack, ds, .995), fraction(mu, dm, .995)
        timings["directions"] += time.perf_counter() - stamp
        x += ap * dx
        slack += ap * ds
        lam += ad * dl
        mu += ad * dm
        if not all(np.all(np.isfinite(v)) for v in (x, lam, mu, slack)):
            raise ScreenFailure("Nonfinite sparse primal iterate")
        trace.append({"iteration": iteration + 1, "primalFraction": ap, "dualFraction": ad,
                      "meanComplementarity": mean, "matrixNonzeros": k_nnz,
                      "factorNonzeros": lu_nnz, **checked})
    raise AssertionError("unreachable")


def load_frozen(path):
    """Reconstruct the inertial/equality/contact problem; never use oracle IDs."""
    doc = json.loads(path.read_text())
    positions = [np.asarray(v) for v in doc["positions"]]
    predictions = [np.asarray(v) for v in doc["prediction"]]
    variables = {}
    n = 0
    for r, weights in enumerate(doc["weights"]):
        for i, inverse_mass in enumerate(weights):
            if inverse_mass > 0:
                variables[r, i] = np.arange(n, n + 3)
                n += 3
    height = n
    n += 1
    h = sparse.lil_matrix((n, n))
    force = np.zeros(n)
    h[height, height] = doc["boardMass"]
    force[height] = -doc["boardMass"] * (doc["boardHeight"] - doc["predictionHeight"])
    for (r, i), indices in variables.items():
        mass = 1 / doc["weights"][r][i]
        for axis, index in enumerate(indices):
            h[index, index] = mass
            force[index] = -mass * (positions[r][i, axis] - predictions[r][i, axis])
    for r, points in enumerate(positions):
        attachments = doc["attachments"][r]
        for i, tension in enumerate(doc["distanceTension"][r]):
            if tension <= 0:
                continue
            delta = points[i + 1] - points[i]
            length = np.linalg.norm(delta)
            tangent = delta / length
            k = tension / length * (np.eye(3) - np.outer(tangent, tangent))
            mapping = {}
            for particle, sign in ((i, -1), (i + 1, 1)):
                if (r, particle) in variables:
                    for axis, index in enumerate(variables[r, particle]):
                        mapping[int(index)] = sign * np.eye(3)[axis]
            attached = int(str(i + 1) in attachments) - int(str(i) in attachments)
            if attached:
                mapping[height] = np.array([0., attached, 0.])
            for a, va in mapping.items():
                for b, vb in mapping.items():
                    h[a, b] += va @ k @ vb
    jr, jc, jv = [], [], []
    for index, row in enumerate(doc["rows"]):
        for local, (particle, gradient) in enumerate(zip(row["particles"], row["gradients"], strict=True)):
            r = row["secondRope"] if local >= 2 and row["secondRope"] >= 0 else row["rope"]
            if (r, particle) in variables:
                for axis, column in enumerate(variables[r, particle]):
                    jr.append(index)
                    jc.append(column)
                    jv.append(gradient[axis])
        jr.append(index)
        jc.append(height)
        jv.append(row["boardGradient"])
    j = sparse.csr_matrix((jv, (jr, jc)), shape=(len(doc["rows"]), n))
    j.sum_duplicates()
    j.eliminate_zeros()
    eq = np.array([i for i, row in enumerate(doc["rows"]) if not row["contact"]], dtype=int)
    contacts = np.array([i for i, row in enumerate(doc["rows"]) if row["contact"]], dtype=int)
    c = np.array([row["residual"] for row in doc["rows"]])
    return FrozenQP(h.tocsc(), force, j[eq], c[eq], j[contacts], c[contacts], doc["regularization"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 50:
        parser.error("repeats must be in [1,50]")
    owner = Path(os.environ.get("PASEO_WORKTREE_PATH", str(Path.cwd()))).name
    output = args.output.resolve()
    allowed = Path.cwd() / ".context" / f"{owner}-sparse-contact"
    if not output.is_relative_to(allowed.resolve()):
        parser.error(f"output must be under {allowed}")
    report = {"owner": owner, "scope": "host frozen QP only; no geometry/complete-step/device claim",
              "inputSHA256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
              "oracleSHA256": hashlib.sha256(args.oracle.read_bytes()).hexdigest(),
              "sourceSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "numpy": np.__version__, "scipy": scipy.__version__, "host": platform.platform(),
              "excludedCosts": ["frozen input reconstruction (reported separately)",
                                "triangle witness/normal discovery", "nonlinear step", "mesh update"],
              "coldRuns": [], "numericallyAccepted": False, "runtimeAdoption": False}
    try:
        stamp = time.perf_counter()
        p = load_frozen(args.input)
        report["loadSeconds"] = time.perf_counter() - stamp
        report.update(variables=len(p.force), equalityRows=len(p.ec), contactRows=len(p.cc),
                      contactNonzeros=p.a.nnz, hessianNonzeros=p.h.nnz, regularization=p.epsilon)
        oracle = np.asarray(json.loads(args.oracle.read_text()))
        for _ in range(args.repeats):
            answer = solve(p)
            checked = residuals(p, answer.x, answer.lam, answer.mu, answer.slack)
            difference = norm(answer.x - oracle)
            if difference > 1e-6:
                raise ScreenFailure(f"Oracle primal mismatch {difference}")
            report["coldRuns"].append({"timings": answer.timings, "iterations": len(answer.trace),
                                       "primalDifference": difference, **checked})
        report["trace"] = answer.trace
        report["numericallyAccepted"] = True
        seconds = [r["timings"]["total"] for r in report["coldRuns"]]
        report["coldMaximumSeconds"] = max(seconds)
        # One correctness checkpoint has no p95. Fifty cold solves are the
        # fixed performance stage, conditional on the correctness checkpoint.
        if args.repeats == 50:
            report["coldP95Seconds"] = float(np.quantile(seconds, .95))
            report["kernel2msGate"] = report["coldP95Seconds"] <= .002
        else:
            report["kernel2msGate"] = None
    except (ScreenFailure, RuntimeError, ValueError) as error:
        report["failure"] = str(error)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("trace", "coldRuns")}, indent=2))
    return 0 if report["numericallyAccepted"] and report.get("kernel2msGate") is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
