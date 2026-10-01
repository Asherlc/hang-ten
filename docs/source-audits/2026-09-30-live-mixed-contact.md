# Direct mixed contact solve screen — 30 September 2026

Four bounded native experiments factor the original simultaneous material,
length-equality, board-height and admitted-contact KKT matrix directly with
Apple Sparse LDLT. They preserve the original `1e-8` regularization, fixed
frozen affine inequalities, strict final residual checks and physical gates.
They are rejected experiments under the workspace-owned `.context`, with no
application adoption or live profile promotion.

The fixed hard input is the retained 22,641-contact QP, SHA-256
`93d9f142cf8c8b6d42d7e540838665505beba1b076e85c6d6ec035308dfc0be7`.
Every run requested 50 cold solves. None accepted the first cold solve, so no
p95 or cold-QP performance pass exists.

| Update rule | Fixed-input rejection | Factors before rejection | Factor-only time |
| --- | --- | ---: | ---: |
| Drop the greatest positive multiplier; admit one violation | First working QP exhausts 50 iterations | 50 | 32.796 ms |
| Block release/admission without retained feasible duals | Active-set cycle | 14 | 9.267 ms |
| Dual-feasible first-zero blocking; serial admission | Second working QP exhausts 50 iterations | 86 | 51.883 ms |
| Dual-feasible first-zero blocking; batch admission | Third working QP exhausts 50 iterations | 111 | 70.687 ms |

The factor-only counters exclude matrix construction, solves, refinement,
source scans and certificates. They are diagnostic counters from rejected
prefixes, not completed cold-QP timings. The 50-iteration cap applies to each
admitted working QP; the unchanged outer admission cap is 20. Working contacts
remain at most 100,000, mixed dimension at most 50,256, nonlocal contacts plus
border at most 256, and matrix entries at most 8,000,000.

The failed update rules produced three useful regression cases: 61 dependent
inequalities, a coupled corner that cycles under naive simultaneous release,
and 61 initially clear independent rows activated by a shared height solve.
The corner came from a bounded synthetic QP search with an exhaustive active
subset oracle. These are numerical fixtures, not authored board geometry.
Each case has a closed-form solution to the same regularized KKT.

The dependent case first exhausted the serial release limit, then passed with
block release. The corner first reproduced the block cycle, then passed with
retained dual-feasible blocking. The height case first exhausted serial
admission, then passed with batch admission. Passing those cases did not make
the hard replay pass. All three are retained in the reusable native contact
fixture suite; the current interior-point screen passes all 18 fixtures.

The [machine-readable evidence](2026-09-30-live-mixed-contact-summary.json)
binds 68 retained sources, inputs, compiled-source provenance, logs and static
ownership snapshots. Exact owned child groups were deleted and verified by
their launchers. Historical resource files grant no cleanup authority.
Seated cords, application solver selection, CAD inputs and catalog coverage
are unchanged. Direct active-set pivoting is closed for this fixed screen;
raising iteration limits or selecting easier QPs would not resolve it.
