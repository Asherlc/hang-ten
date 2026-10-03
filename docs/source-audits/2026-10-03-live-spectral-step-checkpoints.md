# Guarded inverse-secant checkpoint passes

Native-only. User authorized all experiments; original240Hz model, full triangle
QP, global merit/trust, convergence and mesh/material/CCD checks remain. No app
adoption or new video. This differs from the signature-gated Anderson census:
activation requires no unchanged facet signature and begins at correction3.

Use free-particle coordinates plus boardHeight once. With actual accepted state
displacement s and difference y of unscaled QP directions, omega=-s.y/y.y minimizes
norm(s+omega*y)². Only finite0<omega<1 below original trust alpha is used. The next
correction restores ordinary trust/backtracking and must satisfy the unchanged
actual full-step arrival stop. Accepted-only history resets every advance/retry.
Changing curvature/contacts make this a guarded heuristic, not a convergence proof.
Astra reviewed formula, coordinate consistency, reset and history implementation.

Scalar overshoot fixture first failed under original full-step behavior (RED),
then passed with omega.4 for d=-2.5x and undefined/nonfinite/wrong-sign guards.
The step109 control prefix matches108 historical correction-count, alpha,
movement and strain decisions. This is not complete prefix checkpoint identity.

Checkpoint109:4 candidate QPs versus11 original; alphas1,1,0.555219,1. Final fresh
full QP norm0.520311µm; current difference0.319177µm, strict difference0.243274µm.
Original mesh/material checks pass. Seven alternating timings median ratio0.38327,
passing≤.8. Complete serialized checkpoints are deterministic across paired runs.

Ordinary checkpoint140:2 QPs for both, exactly equal candidate/control final pose;
strict difference1.728µm. The spectral path cannot activate before correction3.
Median paired ratio0.8514 passes the pre-registered≤1.10 overhead gate, but is not
an algorithmic speed gain on this unchanged step. Both strict references converge
without retries. Complete turn/return trajectory, p95, simulator and video gates
remain pending. Adjacent JSON binds evidence and independently absent resources.
