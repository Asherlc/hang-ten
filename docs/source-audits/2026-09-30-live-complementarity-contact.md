# Coupled complementarity contact solve — 30 September 2026

The reusable native contact tool now has an experimental `--complementarity`
backend. It addresses the hard-QP pivot failures retained in the
[mixed-contact audit](2026-09-30-live-mixed-contact.md), without raising caps,
discarding inequalities or changing the physical model. Application solver
selection and live profile coverage are unchanged.

For each contact it uses the Fischer–Burmeister equation
`hypot(force, gap) - force - gap = 0`, where force is the compressive multiplier
scaled by a positive local diagonal response estimate. Gap retains the original
`C + Jx - 1e-8 * multiplier`. Scaling and the changing Newton contact diagonals
are numerical derivatives, not a changed model penalty or separate loop solve.
Every Newton direction factors one simultaneous original material,
length-equality, board-height and contact matrix. Exact inactive-force
elimination preserves stationarity. A combined merit function bounds each
line search to 20 trials and each working QP to 50 Newton iterations.

Acceptance still checks the original full stationarity, equality, contact,
complementarity and force-sign residuals together with physical equality and
inequality tolerances. Every frozen source inequality is scanned after each
admitted solve. The working QP retains its 100,000-contact cap; dimension
including contact unknowns is at most 50,256, nonlocal inputs plus border at
most 256, and working-array/matrix budgets at most 8,000,000 entries. Invalid
local diagonals or exhausted bounds reject the experiment.

The final reviewed tool, compiled from current source, passes all 50 cold
replays of the fixed 22,641-contact hard QP. Eight admission passes finish with
407 working contacts. Independent Python checks use the original full frozen
matrix, every source row and the retained primal oracle.

| Hard replay result | Measured value |
| --- | ---: |
| Stationarity residual | 2.73134e-20 |
| Regularized equality residual | 8.60006e-20 |
| Regularized contact residual | 5.08743e-11 |
| Complementarity residual | 1.65985e-17 |
| Dual violation | 9.47434e-15 |
| Maximum physical inequality violation | 5.08743e-11 m |
| Maximum primal difference from oracle | 0.249547 µm |
| Cold QP p95 | 487.418 ms |

The numerical screen passes; the immutable 2 ms cold-QP screen fails. Replay
exits `3`. Timed work includes equality assembly/factorization, source packing,
admission, every Newton matrix/solve/refinement, merit checks and full affine
certificates. Input decoding and oracle comparison are outside the clock.
The shared macOS host is not device performance evidence.

The first full production-size Mini frozen QP also passes independent numerical
checks: both 715-particle material loops, 1,428 equalities, height and all
119,953 source contacts remain in the original coupled problem. The admitted
QP has 158 contacts and takes 169.815 ms in one cold run. Stationarity is
1.44757e-23, regularized contact residual 7.66468e-19, complementarity
2.91508e-18 and physical inequality violation 6.06149e-16 m. There is no
production primal oracle, no p95 and no initialization, motion or settled-frame
claim from this one frozen replay. Its exit code is also `3`.

Focused review found a cancellation bug in the direct evaluation order of the
Fischer–Burmeister value. A valid clear contact with residual 100 and a warm
multiplier `-1e-15` rounded the value to zero while the required force-gap
product still exceeded tolerance. The real fixture reproduced rejection with
zero merit. Subtracting the larger term first preserves that small residual;
the fixture then passes. All 19 native fixtures pass with each backend, and
the four real lifecycle tests pass with the updated driver. No further review
findings remain.

The earlier context-only prototype also completed 50 hard replays, agreeing
with the oracle within 0.250 µm, but failed performance at 465.438 ms p95.
Its diagnostic counters averaged 144 sparse factors per cold replay; factor
time alone averaged 113.526 ms. Those counters exclude matrix construction,
solves, merit and source scans and do not describe the final tool's p95. The
predecessor's fixed replay rejection and all pre-review outcomes are retained.

The [machine-readable evidence](2026-09-30-live-complementarity-contact-summary.json)
binds immutable tested-source snapshots, inputs, compiled-source provenance,
red/green fixture logs, replay outputs, independent validation and static
ownership snapshots. Exact owned compiler/probe groups were deleted and
verified. Seated cords stay available; the accepted CAD PR remains frozen.
Geometry, CAD-error, complete motion, native visual, device performance and
catalog promotion gates remain unresolved. This backend is a numerical
successor for experimentation, not a live rollout.
