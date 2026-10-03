# Mass-only SQP: closed on convergence and work

Candidate only replaces the positive tensile-curvature numerical Hessian term
with zero. Predictor, mass-weighted objective gradient, all fresh rows, shared
height/inter-cord coupling, regularization, contact backend, inactive separation,
merit, trust, stops, original-mesh metrics, CCD and rollback remain unchanged.
No geometry, relaxation or warm prediction experiment was combined.

Native matrix-rule fixtures observed RED then GREEN, including disabled identity
and rejection of negative/nonfinite stiffness. The fresh actual-seed first20
screen stopped at step2. Step1 already needs71 QPs (versus the original schedule),
with current difference9.390µm. Step2 fails the fixed cap/retry/reference gate.
This worsened direction/convergence behavior closes the hypothesis without
implementing a structured dual backend or tuning curvature/caps/stops.

The companion JSON retains complete per-correction traces, references, physical
metrics, source hashes and exact resource cleanup. All six newly owned native
compiler/run groups were independently verified absent. App physics, seated
cords, model assets, catalog WIP, original workspace and frozen PR529 are unchanged.
No speed improvement, accepted full trajectory or new workable video is claimed.
