# Pre-generation geometry and rendering cost — 30 September 2026

The user chose to retain every physical accuracy limit and try rendering
simplification first, with tolerance changes reserved for a later decision.
This checkpoint adds two unadopted geometry pilots and a small rendering
optimization. Live profile coverage, seated cords, CAD and package assets,
physical radii, material chains and solver selection stay unchanged.

The new owned `run_affine_geometry_screen.sh` tool tests the original-geometry
to frozen-affine bridge before generating contact normals or rows. For an
original outside segment, every triangle witness has distance at least the
original minimum surface distance. Its unit normal dotted with a correction
is bounded below by minus the correction magnitude. Each original material
fraction is a convex endpoint combination, so:

`C + J delta >= d_min - radius - clearance - max(|delta_a|, |delta_b|)`.

Corrections include coupled height in board coordinates. Omitted contact
multipliers must be zero. This bounds original frozen inequalities rather than
testing only nonlinear clearance at moved endpoints. It cannot replace working
contact complementarity, portal constraints, self/inter-cord contact or CCD.
Uncertain queries retain the original full triangle manifold calculation.

The first pilot obtains the original signed point/segment minimum distance.
The second traverses original triangle regions against the required bound,
without finding an exact nearest witness or generating normals. It retains
original inside classification and whole-segment intersections. Region AABB
lower bounds round every operation outward; uncertain leaves run the original
triangle closest-point, edge-pair and intersection calculations. The helper
rejects nonfinite/out-of-domain inputs and includes conservative numerical
padding. That padding has no derived general bound for every possible admitted
mesh conditioning, so this is a fixed-input experiment, not a general floating
certificate or authorization for production adoption.

Eight real geometry fixtures cover clear/inward motion, inside classification,
crossing segments, material fractions, uncertain thresholds, invalid input and
original manifold inequalities. Four fail against the empty implementation;
all eight pass with both methods. The corpus mesh and full-production frozen
QP hashes are pinned, as is the reviewed original-matrix certified solution.
The solution is one retained numerical candidate, not an accepted display frame.

The production pilot covers both 715-particle loops and all 2,858 original
point/segment wood queries. Both methods certify every query, avoiding all
119,693 generated wood rows for this candidate. Independent checks evaluate
every original manifold row and all 119,781 retained frozen support rows,
including 88 portal rows sharing those supports. Portal rows remain required
and are outside the wood-generation omission. Minimum checked wood affine gap
is 3.182306 µm; all corresponding retained multipliers are zero.

| Final reviewed one-run pilot | Original wood generation | Candidate |
| --- | ---: | ---: |
| Original signed nearest distance | 201.532 ms | 75.888 ms |
| Threshold triangle regions | 210.740 ms | 83.884 ms |

These are single host samples with different timing conditions, not p95 or a
controlled comparison of methods. Earlier samples of 92.187 ms and 71.420 ms
are retained. The construction-cost checkpoint rejects both candidates without
50 further replays or cap tuning. The experiment excludes portal/self/intercord
geometry, metrics, CCD, solver and mesh; neither result establishes the fixed
50× complete-geometry gate. No geometry method is adopted.

Review found two minor audit defects: the solution was not originally hash
pinned, and the retained-row cross-check regrouped sparse arithmetic into
per-particle dot products. Both are fixed. The cross-check now preserves the
original per-axis order and skips immobile variables. Review found no
Critical/Important defect for this fixed candidate; the general roundoff proof
limit remains explicit.

Rendering offers a much smaller opportunity than the measured contact work.
For both full material loops, 50 host samples of the original eight-sided tube
measure CPU vertex generation plus coordinate conversion at 0.108208 ms p95;
six sides measure 0.081208 ms and four sides 0.064625 ms. Six sides save about
0.027 ms, which cannot close the independently measured 374.019 ms cold-QP gap.
Mesh upload, RealityKit draw cost and device performance are not measured.

The application now computes each ring's identical Float sine/cosine once per
update instead of per material point. It keeps eight sides, every physical
point, radius, vertex order, normals and input guards. The native screen compares
every Float position and normal bit against the retained original function
through 50 runs of all three ring variants; all match. Original ring-count
experiments are not adopted and establish no actual-screen visual review.
Unchanged geometry does not require a new board-asset comparison.

In a paired alternating-order run, current/original eight-sided p95 is
78.042/107.708 µs. The final current-source replay is 98.625/136.250 µs. Its
current mean has a shared-host outlier and exceeds the reference mean; both
results are retained, so this is not a controlled device improvement claim.
The safe refactor preserves output and removes repeated trigonometric work.
Focused review found no correctness issue. The two pure application tube tests
pass natively; UIKit buffer/entity tests and a complete iOS suite are not run in
this checkpoint. The focused Python numerical/lifecycle suite passes 28 tests.
The previously attempted complete prototype suite remains 42 passed/3 failed
for the missing historical Bullet executable, as documented in the
[prior audit](2026-09-30-live-affine-schur-contact.md).

The [manifest](2026-09-30-live-pre-generation-contact-summary.json) binds current
source snapshots, immutable compiled bytes, fixed inputs, red/green fixtures,
compile failures, geometry/render results and verified exact owned cleanup.
No server, simulator or device installation was created. Live accuracy,
convergence, complete geometry and iPhone performance still require proof.
