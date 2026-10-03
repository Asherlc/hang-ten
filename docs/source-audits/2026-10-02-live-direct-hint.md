# One-shot freshly factored contact hints

Incoming contact hints select rows only. The native candidate assembles and
factors the complete current regularized KKT, retaining inertia, length
curvature, board height, nonlocal borders and the original −1e−8 multiplier
diagonals. It checks the original matrix, selected equations, multiplier signs
and every fresh affine row. A failed trial leaves state and hints unchanged and
runs the original Schur path; there is no new active-set update algorithm.

The factor-only ceiling passed narrowly: median optimistic complete-step ratio
0.790472 against 0.80. Fourteen fresh factor/RHS trials passed the same-QP Schur
comparison and full certificate. Matrix assembly and validation were free in
that estimate, so it established only permission to measure the full candidate.

The complete candidate failed the unchanged fixed step-140 speed discriminator:
median ratio **0.945935**, rather than ≤0.80, over seven alternating pairs. Every
pair used two successful direct trials, matched the two-correction schedule and
had zero caps or retries. The maximum propagated positional/height difference
was 1.678e−11 m. This closes the line without optimizing assembly, changing
activation, retrying performance, adjusting thresholds or expanding to 540 steps.

Twenty actual-seed paired steps also passed the 1 µm pose gate, material/binding
identity, physical metrics and correction/cap/retry schedule. Only 11 of 83
hinted trials were accepted; the remainder used the unchanged fallback. Review
found that reducing residuals before checking finiteness could conceal NaNs.
The helper now rejects every nonfinite component before its maximum reduction.
A separate corrected 20-step run passed, including finite GREEN and nonfinite
base/border RED checks, with maximum pose difference 1.118e−14 m. The performance
run predates that additional conservative guard and is retained honestly; no
performance rerun attempted to rescue the failed gate.

No product code changed. The adjacent JSON binds source, plan, results and eight
exact native groups whose deletion was independently verified. The existing
normal-speed simulator video remains valid evidence of motion, while the
real-time gate remains unmet.
