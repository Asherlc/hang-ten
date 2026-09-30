# Sparse primal live-contact screen — closed without adoption

Work took place only on `feat/live-hangboard-physics`, based on `52c3595b5`,
in `strong-owl-live-physics`. The accepted CAD/seated-cord PR #529 remains
frozen. No app source, board package, material budget, cord radius, loaded
pose, physical tolerance or live catalog profile changed.

## Hypothesis and bounded checkpoints

The previous mass-diagonal matrix-free screen exhausted 500 CG iterations
on 7,288 activated facets and failed globalization. This successor tests
whether eliminating the contact Newton block into a sparse primal matrix can
avoid the dense contact-response representation while preserving the original
coupled problem. Geometry admission remains a separate prerequisite; a contact
kernel failing its own 2 ms screen cannot close the complete 4 ms step target.

The fixed first checkpoint is the existing hard Mini Bar frozen QP, not a
newly selected easier state. It has 1,249 primal variables, 418 equality rows
and 22,641 contact rows. Its SHA-256 is
`93d9f142cf8c8b6d42d7e540838665505beba1b076e85c6d6ec035308dfc0be7`.
The independent Python primal oracle has SHA-256
`f1eeb72eaeedb93dde3d3ca7e1a1c09b5fe3930845174f2811f5d39fdcf3618c`.
Neither its active IDs nor historical warm multipliers initialize this screen.

Checkpoint one requires full-row regularized KKT residuals, positive slack and
dual variables, unregularized affine feasibility at the existing 10 nm threshold,
and agreement with that oracle within 1 µm. The screen stops after 50 Newton
iterations if those checks fail. Only a numerical pass permits checkpoint two:
50 cold solves of this same immutable problem, with fresh factors and dual/slack
initialization each time. The existing 2 ms kernel target is retained.

## Implementation and model preservation

`Tools/HangboardRopePrototype/sparse_contact_screen.py` implements an infeasible
start primal-dual predictor/corrector. Its equations are

```text
H x + Eᵀ λ − Aᵀ μ = f
E x + cE − ε λ = 0
A x + cA + ε μ = s ≥ 0
μ ≥ 0, μᵢ sᵢ = 0
```

The Newton matrix is the joint equality system with
`H + Aᵀ diag(1 / (ε + s / μ)) A`. The input regularizer remains exactly
`1e-8`; it is not adjusted to condition the solve. All triangle, self-contact
and inter-cord rows remain in `A`. Independent material-chain coordinates and
shared board height remain in one solve. The original inertial objective,
tension curvature, equality residuals and contact Jacobians are reconstructed
from the capture. No loop is solved independently.

The final sparse Newton KKT has 18,853 nonzeros rather than a stored dense
contact-response array. Each predictor/corrector shares one sparse factor.
Diagonal congruence and bounded iterative refinement use the original matrix
residual; they do not change its equations. Banded Cholesky validates the
inertial Hessian before solving. The first version used a slow eigenvalue
validation; its 3.322 s checkpoint and exact source snapshot are retained,
not discarded. Cholesky reduced that incidental cost without changing the
Newton iterates, iteration bound or gates.

This is an offline Python/SciPy implementation, isolated from both apps.
Frozen-row replay preserves the captured contact problem, but does not generate
new geometry witnesses or certify a changing nonlinear state. No wood, sign,
threading, whole-segment CCD, convergence or transactional gate is replaced.

## Results

All 50 final cold solves passed the numerical checkpoint in exactly 36 Newton
iterations. Maximum primal difference from the independent oracle was
**0.601 µm**, maximum all-row affine infeasibility **1.066e-13 m**, stationarity
**8.883e-11**, and regularized complementarity **1.161e-15**. These measured
residuals establish the frozen numerical checkpoint only.

Final host solve p95 was **371.332 ms**, maximum **386.069 ms**. The earlier
50-run checkpoint measured p95 355.529 ms; both reports are retained. The
performance command exits 1 because the 2 ms gate fails, even though the
numerical checkpoint passes. Mean final solve cost was 317.018 ms:

| Component | Mean time |
| --- | ---: |
| Inertial validation | 0.422 ms |
| Equality factor and initial solve | 2.012 ms |
| Contact aggregation | 92.335 ms |
| Sparse Newton factorization | 133.592 ms |
| Predictor/corrector directions | 55.355 ms |
| All-row residual checks | 17.358 ms |

The total also includes remaining bookkeeping. Frozen input reconstruction
took 209.618 ms once, outside those solve timings. Triangle witness/normal
discovery, nonlinear geometry queries, CCD and mesh updates are excluded. Even
this incomplete kernel misses the target by more than 180 times; no complete
geometry speedup, complete step, production-resolution or device result follows.
This implementation is not adopted. It does not establish that every sparse
primal implementation must fail: it shows that this all-row, 36-factorization
implementation does not solve the measured runtime problem.

Twenty-four focused tests pass. Their independent oracle enumerates full
regularized KKT active sets. Fixtures cover a stronger dependent inequality,
stale contacts, unequal masses, unrestricted equality multipliers, coupled
height and independent cord coordinates, inter-cord constraints, twelve
deterministic non-diagonal Hessians, nonfinite/indefinite inputs, iteration
limits and equality-only problems. A separate fixture rejects a mathematically
converged regularized solution with 20 nm penetration: small stationarity and
complementarity cannot override the existing affine feasibility gate.
The untracked intentionally failing live-inventory WIP is untouched and is
not included in this test count. An independent capture fixture also checks
attachment tension curvature, the board-height border and other-rope ownership.
Native/UI tests are not claimed for this
offline-only change.

## Reproduction and retained evidence

From this dedicated checkout, install the pinned screen environment:

```sh
screen_owner="${PASEO_WORKTREE_PATH:-$PWD}"
screen_owner="${screen_owner##*/}"
rtk proxy uv venv ".context/$screen_owner-sparse-contact/venv"
rtk proxy env UV_CACHE_DIR="$PWD/.context/$screen_owner-sparse-contact/uv-cache" uv pip install --python ".context/$screen_owner-sparse-contact/venv/bin/python" -r Tools/HangboardRopePrototype/requirements-sparse-contact-screen.txt
rtk proxy bash Tools/HangboardRopePrototype/run_sparse_contact_screen.sh --input .context/strong-owl-live-physics-handoff/mini-dynamics-probe/frozen-qp.json --oracle .context/strong-owl-live-physics-handoff/mini-dynamics-probe/persistent-qp-python-primal.json --output ".context/$screen_owner-sparse-contact/replay.report.json" --repeats 50
rtk proxy env PYTHONPYCACHEPREFIX="$PWD/.context/$screen_owner-sparse-contact/pycache" ".context/$screen_owner-sparse-contact/venv/bin/python" -m pytest Tools/HangboardRopePrototype/tests/test_sparse_contact_screen.py -q -o "cache_dir=.context/$screen_owner-sparse-contact/pytest-cache"
```

The benchmark's expected exit is 1 for the retained failed performance gate.
Source, test, dependency, input and report hashes are retained under
`.context/strong-owl-live-physics-sparse-contact/inputs.json`; complete traces
and 50 individual run measurements are in `final-fixed-50.report.json`.
Earlier reports and source snapshots remain in the same owner directory.
The [compact committed JSON summary](2026-09-30-live-sparse-primal-contact-summary.json)
accompanies this audit.

All 626 evidence payloads listed by the copied SHA-256 manifest verified
unchanged (627 files counting that manifest). Actual Mini Bar and Clavellium
FCStd files were verified as ZIP objects, not Git LFS pointers. Copied binaries
and historical owner manifests were not executed. The initial correctness run
completed as finite tool session 40179 before the explicit PID trap was added.
Subsequent benchmark and validation processes were registered by exact PID,
exit-trap cleaned and verified absent. Both initial finite tool sessions
(39705 for environment setup, 40179 for correctness) completed; a final process
inspection found no remaining workspace probe or installer. No server,
Simulator or external agent was created. Environment and retained evidence
remain within this workspace's owner directory.

The next contact representation must reduce repeated global factorizations
and row processing while retaining full affine separation. A triangle-authority
admission path must also address the independently measured assembly/merit
costs; frozen QP success cannot validate it. The rotation verification fallback,
production-resolution convergence, CAD error/bearing certificates, catalog
promotion and physical iPhone throughput remain open.
