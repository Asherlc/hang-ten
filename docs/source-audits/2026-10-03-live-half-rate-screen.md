# Authorized 120 Hz experiment: closed after accuracy failure

The user authorized this isolated screen on 2026-10-03. The first 1/120-second
candidate differed by **133.731 µm** from two independently propagated 1/240-second
control steps, exceeding the unchanged 50 µm comparison limit. The screen stopped
at that checkpoint; no product change or simulator/video claim follows.

Original-mesh and material checks passed: clearance margin +99.829 µm, strain
0.016116%, material-length error 0.718 µm. Neither path capped or retried. The
candidate used six QPs and 12.411 ms; the two control steps used seven QPs and
15.169 ms. One timing sample cannot establish p95; it exceeds the 8 ms sample
budget, but the accuracy failure already closes the experiment.

The board-height mismatch was 123.756 µm. A read-only calculation using the actual
predictor's gravity and exponential damping gives 123.755 µm for the difference
between one coarse and two fine free predictions. Those differences agree within
0.983 nm; each corrected height is within 6 nm of its free prediction. This
strongly attributes this checkpoint's height error to integration discretization,
rather than early solver stopping. Tightening convergence cannot recover the
missing 124 µm without changing the step formulation.

The plan's fixed stop applies. No 1/60 fallback, predictor modification, tolerance
change or rescue run was performed. No complete trajectory, settling, strict
comparison stage, device speed or new recording was reached. The staged experiment
and its provenance remain workspace-owned evidence. Exact compile/run groups
55457 and 55690 were cleaned and independently verified absent.

Machine-readable numbers and SHA-256 evidence bindings are in the accompanying
`2026-10-03-live-half-rate-screen.json`.
