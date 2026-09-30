# Live cord initialization: simultaneous contact audit

This is an intermediate solver audit. The Mini Bar remains on its reviewed
static 7 mm cord routes; this change does not enable its live profile or finish
the all-board rollout.

## Reproduction and cause

The current 7 mm Mini Bar CAD source has two curved channels. A source-derived
candidate follows each native spine and wraps the exterior leg below the wood
in the authored winding class. Its initial two loops each retain 0.82 m of
material, but their finite-radius return legs overlap near the common support.
The centerlines do not cross and the wood clearance is valid.

The first-pair-only correction and merit were insufficient. The trace reached
a nearly separated first pair, then its merit jumped from approximately
0.000025 to 0.003114 when another overlapping pair became first. Enumerating all
pairs for the merit alone removed that discontinuity but still failed: the
correction was constrained by only one of the simultaneous overlaps. Supplying
the complete candidate manifold exposed the old 32-row border capacity; the
first Mini Bar correction had 112 nonlocal candidate contacts.

The solver now enumerates the complete self-contact manifold in both constraint
assembly and nonlinear merit. Nonlocal candidates start inactive; the existing
active-set solve adds any violated inequality before accepting its correction.
This avoids initially treating all redundant capsule witnesses as equalities.
The bordered linear solve permits at most 256 rows and eight million working
entries. Those are computational bounds, not softer physical constraints.

## Initialization and material accounting

`projectInitialization` is transactional and bounded. It may separate overlapping
finite-radius collars, but rejects an invalid wood/threading preflight and
proper centerline crossings. It publishes only a state satisfying the normal
length, strain, clearance and topology gates. It is not yet called by the scene
for additional catalog boards.

When several loops share a height, the seed preserves each declared material
budget exactly. It chooses the highest compatible seed height and distributes
the tiny discretization slack over that loop's immutable rest lengths. The
single-loop Clavellium path keeps its previous rest-length construction.

Curved-channel initialization follows the native spine and checks every segment
against the actual wood collider. For same-face exits, the exterior search
tracks the selected lower wrap in a bounded winding state and preserves that
winding when simplifying its route. No cord contact coordinates are authored.

## Verification

- The source-backed curved-pipe exporter suite passes all four tests, including
  repeatable native voids, safe interior crossing sections and unchanged
  Clavellium straight-channel export.
- All 35 host physics tests pass in 219.710 seconds, including Clavellium
  determinism, half-step agreement, physical rotations and repeated reversals.
- All 19 focused iOS Simulator tests pass on the workspace-owned iPhone 17 Pro,
  iOS 26.4. The tests cover simultaneous overlaps, continuity at first-pair
  separation, immutable material budgets, 40 coupled border rows, computational
  rejection bounds, initialization and transactional rejection of crossings
  and invalid geometry.
- The Mini Bar diagnostic accepts its candidate after 70 initialization
  corrections: maximum local strain 0.00002310, minimum wood clearance
  3.600085 mm, radius 3.5 mm and both full 0.82 m material budgets. Starting
  nonlocal candidates inactive reaches the same acceptance with 1,499 linear
  solves instead of 6,137 in the initially active diagnostic.

Diagnostic logs are workspace artifacts under
`.context/strong-owl-live-cords/mini-seven-mm/seed-probe/`.

## Remaining gates

The first diagnostic above measures self-contact within each loop. The
subsequent change below adds contact between separate loops. Mini Bar settling,
grip transitions and live app screenshots remain required. The other catalog
profiles and the physical-device performance gate are also unfinished;
simulator acceptance does not establish 60 fps or a device worker budget.

## Separate material chains

`RopeCordContacts` now supplies contact witnesses between distinct cords and
conservative swept collision checks between frames. The coupled correction
tracks which rope owns each particle gradient; contacts between two ropes are
always border rows, even when their local segment indices happen to match.
Both the nonlinear merit and final acceptance include these contacts.

A shared support denotes an idealized joined knot. Links are split at its
material neighborhood boundary (four radii from the support), so a long link
cannot hide exterior overlap. Within that neighborhood, finite tube collars
may overlap, but proper or coincident centerline crossings remain invalid.
Only the coincident mathematical support endpoint is trimmed by one micrometre.
Initialization rejects crossings between cords transactionally.

Seven new regression tests cover finite-radius contact, shared-support bounds,
proper and coincident crossings near a knot, swept crossing between clear
endpoint frames, coupled initialization, exact material budgets and immutable
supports. All **42 host physics tests** pass in 218.415 seconds, including the
existing Clavellium rotation, reversal and numerical agreement tests. All
**26 focused iOS Simulator tests** pass on the same owned iOS 26.4 simulator.

The current Mini Bar candidate also passes initialization with cross-cord
contact included: maximum local strain 0.00003142 and minimum wood clearance
3.600084 mm. The measured initialization took about 70 wall seconds in the host
diagnostic. This is numerical evidence for the candidate, not a real-time
performance result or authorization to promote an unverified live profile.

## Collision-query traversal and diameter policy follow-up

The operator confirmed that Clavellium and Mini Bar use 7 mm cord and that
other boards must use documented real cord diameters where available; unknown
sizes must be labeled as estimates. This supersedes the earlier threefold
thickness request throughout the remaining catalog rollout.

Nearest-first traversal now visits the closer BVH child before the farther
child in point and segment closest-surface queries. Triangle geometry and
contact acceptance are unchanged. A controlled benchmark using 97 Mini Bar
channel/exterior samples repeated ten times measured identical point/segment
distances (maximum difference zero), 0.07631 seconds for prior traversal and
0.05164 seconds for nearest-first traversal, about 1.48 times faster. This is
a query benchmark, not a frame-rate or device-performance measurement.

Verification after this change: 42 host physics tests passed (160.99 seconds),
and 22 selected native iOS Simulator tests passed (iOS 26.4, workspace-owned
strong-owl review device). The inter-cord initialization regression now also
checks five subsequent gravity steps. The native build initially rejected a
stale tracked-source boundary manifest; adding the already committed
RopeCordContacts.swift entry restored the exact git-tracked source list.
Mini Bar live simulation remains pending: a diagnostic dual-feasible contact
selection passed its previously cycling third frame, but sustained settling
and acceptable runtime performance have not been demonstrated.

## Dual-feasible contact selection

The Mini Bar diagnostic identified a cycling inequality working set: the
same contact rows were added and released more than 40,000 times within one
correction. A separate nine-plane, four-dimensional feasible contact fixture
reproduced the greatest-tensile-multiplier release algorithm's cycle. Its
regression failed with the old rule and passed with first-zero dual blocking.

The solver now retains dual-feasible multipliers within a linearized solve,
interpolates only to the first contact multiplier reaching zero, releases
that row, and solves again. Equality multipliers remain unrestricted. Wood
contacts begin inactive, like other inequalities; every violated candidate
is reconsidered. Each working-set solve is bounded to at most 2,048 iterations
and still fails transactionally if it does not converge. This bound does not
prove convergence for every feasible configuration.

The first full regression run exposed a Clavellium return-to-upright failure:
line search rejected 19–112 nm corrections despite negligible strain. A
controlled diagnostic matched the contact merit's deadzone to the existing
10 nm inactive-contact feasibility threshold and then passed all six
orientation transitions. Distance penalties, immutable rest lengths, physical
clearance/strain acceptance and continuous collision checks are unchanged.
The existing 1e-8 linear-system rank regularization still allows active-row
residuals proportional to their multipliers; exact geometry acceptance remains
mandatory and is not replaced by the merit tolerance.

Verification of the production fix: all 43 host physics tests passed in
243.296 seconds; 28 native iOS Simulator tests, including the four Clavellium
settling/determinism/rotation tests, passed. Independent read-only review found
no Critical or Important issues. Its two Minor test suggestions were addressed:
the projection fixture additionally exercises both signs of an unrestricted
equality multiplier, unequal mass metrics, redundant active contacts, inactive
10 nm feasibility, and active regularization residuals. These strengthened
eight-test inter-contact suites passed on both host and native Simulator after
the full-suite run; production code was unchanged during the strengthening.

Mini Bar remains a diagnostic candidate. A CAD-certified coarser seed reduced
its loops from 715 to 210 particles each, preserving 820 mm per loop and full
radius capsule clearance. The cold working-set candidate settled upright at
frame 130 (0.546 simulated seconds, 1,046.7 wall seconds); a scratch cache keyed
by native contact features reached the same frame/height within 0.04 micrometres
in 520.9 wall seconds. Jug rotation and return remain under investigation.
These timings are far too slow for live use; neither scratch seed/cache nor
the Mini Bar live profile is enabled in the app.

The contact-membership lookup now uses indexed Boolean flags instead of a
hash set. A 124-frame replay of the same Mini Bar checkpoint produced exactly
matching heights and strains. All 43 host physics tests passed in 257.138
seconds and all 24 selected native Simulator tests passed. This optimization
does not enable Mini Bar live settling or establish real-time performance.

Sliding portal boundaries now participate in the coupled correction. A
frozen Mini Bar jug transition failed with 1–3 micrometres of aperture merit
after the other constraints had converged: the merit checked conservative
planar sections that wood-only rows could not enforce. Each boundary's
derivative includes the changing geometric intersection fraction, so it
permits material feed and does not pin a material particle. World-space
gradients include board-height and board-fixed endpoint motion. Portal merit
uses the existing 10 nm linear feasibility deadzone; physical acceptance and
CCD remain unchanged.

An integration regression reduces Clavellium's planar aperture by 0.1 percent
while retaining its original certified seed. Before the correction, the step
accepted a crossing approximately 13 micrometres outside the requested
erosion; the new regression fails twice on that implementation and passes
with the new rows. Independent finite differences cover all endpoint axes,
three rotations, four attachment combinations, and material transfer across
segments. All 45 host physics tests passed in 250.854 seconds and 29 native
Simulator tests passed. After review-requested test strengthening, four
focused host tests and two native tests passed; production was unchanged.
Read-only review found no Critical or Important issues and its Minor coverage
request was addressed.

The scratch Mini Bar candidate passes the previously failing jug frame 46
and advances to frame 134, then rejects frame 135 at its swept self-contact
gate. This is diagnostic progress, not complete jug settling, a live profile
enablement, or real-time performance proof.

Both self-contact and independent-cord CCD now check an endpoint reached on
the final permitted conservative advancement. Previously, reaching t=1 on
iteration 256 left `certified` false because the loop ended before checking
that endpoint. Two rigid-translation regressions with constant 0.5 mm
clearance fail on the prior source and pass with the endpoint check. The
check uses the same distance threshold plus 1 nm, adds no advancement, and
still rejects exhaustion before t=1. All 48 host physics tests passed in
237.757 seconds and the selected native suite passed. Independent review
found no issues.

The Mini Bar checkpoint replay then identifies further uncertain sweeps near
the common knot: some reach only t=0.90 before the bounded iteration limit.
The endpoint fix does not claim to resolve those separate cases.

Self-contact CCD also has a conservative separation certificate for the first
and last legs leaving an exactly shared, fixed support. The generic sweep
can otherwise exhaust because trimmed endpoints remain about a micrometre
from the support while far-end velocity bounds are hundreds of micrometres.
The certificate bounds the minimum chord radii and cross-product angle
throughout the linear sweep. Its midpoint cross-product bound uses the
endpoint maximum of the affine derivative. It applies only when all four
old/new support endpoints exactly equal the same support and only accepts
a lower bound above the existing threshold plus 1 nm. Uncertified motion
retains the full sweep. No knot exemption or trim length changed.

A rigidly rotating same-quadrant ray fixture falsely rejects on the earlier
source and passes with the certificate. Swapping the rays remains rejected.
A further 32 motion paths sampled at 65 times confirm the computed lower
bound never exceeds exact truncated-segment distance. Independent mathematical
review found no issues. All 51 host physics tests passed in 250.059 seconds
and the selected native suite passed.

Mini Bar's scratch replay advances through frame 157 and then rejects
independent-cord CCD at frame 158. Its diagnostic identifies the same
conservative-bound exhaustion between two legs of separate loops leaving
the shared support; no crossing was reported. This does not establish full
rotation settling or runtime readiness.

The shared-support certificate now also covers independent-cord knot pieces.
It recognizes the exactly fixed support in either segment direction and uses
the piece's nearer material fraction after the unchanged support trim.
Each finite piece is a subset of the certified truncated ray, so its upper
fraction cannot weaken the lower separation bound. Other pieces and any
nonexact or moving support retain ordinary CCD. Four safe rigid-rotation
cases fail on the prior source (all traversal directions) and pass with the
extension; swapping the rays remains rejected. All 53 host physics tests
passed in 227.268 seconds and 37 selected native tests passed. Independent
review found no issues. Mini Bar's scratch candidate now advances past the
previously rejected frame 158; full rotation settling and performance remain
pending.

## Immutable channel-collider cache and frozen-step cost experiment

The solver now constructs channel BVHs once and shares the immutable cache
across transactional copies. Metrics bind the cache to the complete channel
region values, including portal IDs, spines, vertices, and triangle indices;
a mismatch throws before a collider is reused. Callers without a cache keep
the same cold construction behavior. Acceptance calculations and thresholds
are unchanged.

Two tests compare cached and uncached metrics for both a valid seed and an
invalid channel state, and reject shifted channel solids with unchanged IDs.
All 55 host physics tests passed in 319.063 seconds; all 39 selected native
tests passed on the owned iPhone 17 Pro Simulator. Independent scoped review
found no issues. Five isolated Mini Bar measurements were identical, with
mean cold verification 98.333 ms versus cached 35.918 ms (2.738×). An earlier
concurrent-test run measured 398.243/171.486 ms (2.322×). These are host
verification timings, not device or complete-step performance claims.

The read-only performance committee agreed to retain immutable material
chains, sliding crossings, jointly coupled board height and separate cords,
global merit, final geometry gates, and swept collision checks. Its next
discriminating experiment was one frozen Mini Bar jug step and replay of
one identical linearized constraint problem with equality-only, warm, and
diagnostic oracle contact starts. The scratch candidate contains a certified
coarse seed and experimental contact warm-starting; this is not a production
runtime benchmark.

At frame 227, the profiled step used 36 nonlinear corrections and 1,279
runtime linear solves, with 677 contact insertions and 566 releases. Runtime
linear assembly/band/Schur times were 0.410/1.229/3.268 seconds. Constraint
assembly took 1.711 seconds; 192 merit evaluations took 4.938 seconds. The
whole profiled step, including diagnostic QP replays, took 14.775 seconds.
The accepted physical checkpoint matches the baseline exactly after sorting
the serialized contact-cache entries; profiling does not alter its state.

For the captured problem, the oracle final set required one solve (3.390 ms),
the warm start 156 solves (677.206 ms), and equality-only 303 solves
(938.461 ms). Warm and oracle primal solutions and objectives were identical;
the equality start differed by at most 0.2513 µm, with the same objective to
4.9e-18. All three had zero positive contact multipliers; maximum linearized
feasibility error was 7.494 nm and complementarity error below 6.6e-19.
The final active sets differ by one row under the 10 nm inactive-row tolerance.

The captured problem contains 418 length equalities and 22,641 candidate
contact inequalities, including 22,521 wood witnesses. None are exact
duplicate rows when particle references, gradients, board gradients, and
residuals are compared. Linear dependence does not justify dropping these
inequalities. The evidence favors reusing a chain/equality factorization and
updating contact selection, with complete separation checks for omitted
candidates. It also shows that contact discovery is only part of the cost:
geometry, globalization, and verification remain far above the step budget.

Retained logs, frozen checkpoint, reconstructible QP coefficients, toolchain
and source hashes, and committee reports are under the workspace-owned
`.context/strong-owl-live-cords/mini-dynamics-probe/`. Full Mini Bar rotation
and return settling, catalog rollout, the CAD-to-mesh error budget, shared
settled-bearing checks, and actual-device throughput remain pending.

## Reusable equality-factorization foundation

`RopeBandedSystem.factorized` now snapshots band and Schur factors for
changing right-hand sides. Every coefficient and border column is fixed
for the lifetime of this value; rebuilding a linearization requires a new
factor. LAPACK DGBTRS/DGETRS read the stored factors and mutate only local
load buffers. The existing runtime solve remains unchanged.

Three new tests exercise distinct noncollinear loads, a mutated authoring
matrix after factor creation, immutable factor copies, two coupled borders,
no-border solves, invalid dimensions/nonfinite values, and singular band or
border matrices. All seven band-system tests passed on the host and the
owned native Simulator. Independent scoped review found no issues.

A scratch Python/SciPy contact-space prototype reproduced the captured QP's
active-set iteration counts, objectives, feasibility, and complementarity
with one equality-backbone factorization and lazy contact responses. A Swift
prototype using the new API also checked every omitted contact inequality.
Its backbone factor took 0.355 ms; oracle/warm/equality runs took
12.281/46.671/77.877 ms including response construction. The warm start kept
156 iterations, 78 insertions and 77 releases, matching the original replay;
its primal solution differed from the Python oracle by at most 4.8e-16 m.
Maximum feasibility error remained 7.494 nm. Cold-start primal difference
was 0.2496 micrometers under the same inactive-row tolerance.

The earlier warm replay was 677.206 ms, so factor/response reuse substantially
reduces this frozen problem's cost. It does not establish full-step speed or
real-time performance: the Swift warm replay alone is over eleven times the
4 ms complete-step budget. Geometry/globalization/CCD costs and nonlinear
iteration count remain. Neither prototype is enabled in production.


## Production equality-factor reuse — September 30

The frozen-QP experiment above supports replacing repeated full KKT
factorizations during contact discovery. `RopeContactSystem` now factors the
joint equality/inertial/board-height system once per nonlinear correction,
computes contact response columns lazily, and updates a contact-space Cholesky
factor on insertion or release. Runtime starts equality-only. Factors and
responses never survive a change of linearization. Separate cords share the
same board-height solve, and inter-cord constraints participate jointly.
Every inactive candidate inequality is checked before accepting the result;
no manifold is reduced by assuming dependent inequalities are redundant.
Prediction, tension curvature, numerical regularization, nonlinear merit,
trust bound, geometry acceptance, CCD and transactional rollback are unchanged.

Independent review identified a scaled-row conditioning failure: for mass
0.005 and contact gradients 2000 and 1000, the contact Schur diagonals are
8e8 and 2e8. Adding 1e-8 rounds away, and a dependent insertion can have zero
Cholesky pivot despite feasible inequalities. The new regression reproduces
this case. Only contact-factor conditioning failures fall back to the original
explicitly regularized full KKT working set, retaining dual-feasible releases
and complete inactive separation. Invalid inputs, computational limits and
nonconvergence do not become successful fallback results. Review found no
remaining Important issues after this repair.

Six analytic/direct-KKT tests cover joint board/cord inertia, dependent and
omitted stronger inequalities, stale contact release, changed coefficients,
equality coupling, scaled-row fallback and fail-closed inputs. The refreshed
complete host physics suite passes 64 tests in 139.950 seconds. The focused
iOS Simulator run passes 49 tests on the owned strong-owl iPhone 17 Pro,
iOS 26.4. Full app validation is recorded separately after it finishes.

The production helper replayed the same retained Mini Bar QP with
oracle/warm/equality starts in 11.353/42.644/72.896 ms, including contact
response construction. Warm/oracle primal differences from the independent
Python oracle were below 4.8e-16 m; cold differed by 0.2496 micrometres under
the existing inactive-row tolerance. Maximum feasibility error was 7.494 nm.
The earlier cold replay took 938.461 ms. These are host frozen-problem
measurements, not complete-step or device performance.

A scratch complete-step replay using this production helper, the retained
coarse seed and previous diagnostic globalization accepts Mini jug frame227.
Immutable rest lengths match exactly; maximum particle difference from the
original accepted frame is 0.294 micrometres and height difference is below
0.0001 micrometres. It still needs 36 nonlinear corrections and took 9.478
wall seconds while other validation ran. The Mini Bar remains unpromoted;
this does not demonstrate rotation settling, live throughput or completion of
the catalog rollout.

An independent scratch experiment reduced the hard merit penalty floor to a
multiplier-scaled value. It used 28 corrections and 5.661 seconds for the same
frame but still required repeated short line-search steps. It is not adopted:
one frame does not establish convergence, and multiplier bounds must account
for the merit's aggregated maximum penetration terms. Closest-only merit,
endpoint certificates, bounded verification and bulk contact activation also
showed no useful complete-step improvement and remain workspace experiments.


Full current-source app and UI validation subsequently passed: 1,355 tests
passed, three skipped, zero failures (1,358 total). The two live StoreKit tests
require their explicitly enabled environment; the existing plan cue coverage
test skips because historical source-audit records were removed. The result
retains Xcode QoS priority-inversion warnings, including diagnostics in
WorkoutSessionStoreTests; it establishes no device throughput claim. Its
summary is retained at
`.context/strong-owl-live-cords/mini-dynamics-probe/contact-system-full-native-summary.json`.
After staging the new source membership and refreshing the strict tracked-path
manifest, all 18 BoardSourceBoundaryTests also passed in a fresh native run.
At this validation checkpoint Mini Bar jug/return diagnostics and the all-board
rollout remained unfinished; the later diagnostic result is recorded below.

### Per-triangle allocation removal

Steady-state sampling after collider initialization attributed 2,539 of 2,639
verification samples to wood segment clearance. Its closest-segment leaf loop
allocated a three-edge array for every triangle. Three explicit edge calls now
preserve the same arithmetic, ordering and tie handling without that allocation.
Independent review found no issues with this scoped change.

An alternating same-state comparison used accepted Mini return frame 79, 300
complete cached verification calls per variant, and 1,254 exact segment/contact
witness comparisons. All metric fields and witnesses were identical. Mean
verification time fell from 37.825 to 27.445 ms (1.378x) on the host while the
transition diagnostic also ran. This is neither complete-step nor device timing,
and remains above the 4 ms step target. Evidence is retained in
`.context/strong-owl-live-cords/mini-dynamics-probe/no-edge-array-comparison.report.json`.
All 64 host physics tests passed in 130.539 seconds; all 36 focused Simulator
collider, dynamics and inter-cord tests passed with zero failures or skips.
Their retained summary is `mini-dynamics-probe/edge-array-native-summary.json`
under the same workspace context directory.

### Paired-board live placement

Scene review found that profile array order determined the live instance, while
frame delivery replaced the authored instance transform. Both boards and cords
could therefore overlap at the origin. Live preparation now matches profiles by
instance ID, composes base placement with the physical board transform, places
cords in that same world, and includes every instance's rotation envelope in
camera framing. Selection validates each instance's suspension pose before
updating any controller, including presentations without top-level suspension.

The local solver's gravity remains vertical: a base placement that changes this
direction is rejected until a physics coordinate adapter exists. No catalog
profiles were enabled by this repair. A synthetic two-instance regression first
reproduced reversed-profile/placement failures and then the instance-only pose
failure. It now passes across deselection and reselection, verifying board
positions, rope ownership and world-space tube radius. All 31 focused native
scene/controller/mesh tests passed; independent review found no important issues.
The retained result summary is
`.context/strong-owl-live-cords/mini-dynamics-probe/paired-placement-native-summary.json`.

### Inside-endpoint penetration witness

When both capsule endpoints were inside wood, segment contact returned the first
endpoint's penetration even when the other endpoint was deeper. It now examines
both and returns the deeper endpoint with its matching surface, normal and
material fraction. The regression reproduces 0.106 m versus 0.606 m penetration
in a synthetic box and checks both segment directions and manifold delegation.
This repairs endpoint selection; it does not establish maximum penetration over
the whole segment. Existing exact acceptance and CCD gates remain required.

Independent scoped review found no important issues. All 37 focused native
collider/dynamics/inter-cord tests passed, and all 65 host physics tests passed in
128.462 seconds with the refreshed suite-count guard. The first host invocation
passed its tests but failed its stale 64-test runner guard; it is not counted as
a successful command. Retained evidence is `inside-endpoints-native-summary.json`
and `inside-endpoints-full-host-refreshed.log` under
`.context/strong-owl-live-cords/mini-dynamics-probe/`.

### Completed coarse Mini jug and return diagnostic

The production contact helper, inside the retained coarse-seed and relative-trust
diagnostic, completed the jug rotation and upright return. Each of two independent
0.82 m material loops used 210 particles; this is not the production seed or full
production configuration. Rest lengths were checked on every accepted frame, and
wood, self-contact, inter-cord, CCD and transactional acceptance gates remained.
Across 757 retained accepted frames, maximum local strain was 0.000302662 and
minimum mesh clearance was 3.599369 mm for a 3.5 mm radius. Jug and return reached
the diagnostic settling criterion at frames 491 and 492, about 2.05 simulated
seconds per transition, with speeds 0.1314 and 0.1134 mm/s respectively.

The final upright return checkpoint was retained with SHA-256
`922f7992fa0dddf6b37d02b15b7ff751eba854e5fa6be0c489e20457982577be`.
An exact native CAD check of all 418 segments found minimum clearances of
3.595383 and 3.593076 mm, with no endpoints inside wood. That establishes
clearance for this frozen state only. It does not establish a global 50 micrometre
mesh-to-CAD bound or the shared designated-bearing acceptance gate. The final jug
checkpoint was overwritten by the return and has no equivalent retained native
CAD check.

Performance remains unsuitable for live use: the final return step took 0.6724
host seconds, and the largest accepted step took 103.256 seconds including CCD
retries. No device throughput or Mini live-profile readiness is claimed. Evidence
is retained in `mini-jug-return-summary.json`, `mini-return-settled-checkpoint.json`
and `native-return-settled-clearance.json` under the same workspace context path.
Catalog rollout remains unfinished.

### Post-backbone settled-step profile

One frozen upright return step (492 to 493) used the current contact helper,
geometry-bound channel cache, allocation-free triangle edge queries and corrected
inside-endpoint selection inside the retained coarse/relative-trust diagnostic.
It took 502.704 host milliseconds: three QPs used 182.132 ms, row assembly
120.387 ms, seven merit calls 160.895 ms, cached final metrics 26.880 ms, and CCD
plus velocity update 1.143 ms. There were 60,804 cumulative rows over three
corrections and no full-KKT fallback. Both contact solving and geometry therefore
independently exceed the complete 4 ms step budget. Uncached metrics took
86.775 ms; the cached and uncached physical state, metrics and contact cache
were identical after normalizing dictionary serialization order. This is one
host screening sample, not a p95 or production/device measurement.

The report and code/checkpoint SHA manifest are retained as
`strong-owl-settled-profile-checkpoint.json.report.json` and
`strong-owl-settled-profile-inputs.json` in the same workspace probe directory.

Read-only native inspection uniquely partitioned all 42,796 approved Mini wood
triangles into 15 CAD faces. Two toroidal channel patches account for 39,254
triangles (91.7%). The partition retains the exact mesh and provides no permission
to substitute untrimmed analytic surfaces for collision geometry. Native guidance
and exploratory triangle-to-support-surface bounds are recorded in
`strong-owl-mini-native-patches.json`; outward-rounded bounds, trims, reverse
CAD-to-mesh coverage and solid-side certification are not yet established.

A bounded Python/SciPy matrix-free complementarity screening retained the frozen
inertial objective, joint equality/height system and explicit regularization.
With a mass-diagonal preconditioner, its cold start activated 7,288 candidates,
reached the 500-CG-iteration bound, and failed complementarity line search. It
returned no accepted correction and was not adopted. This rejects that simple
preconditioner/initialization experiment, not matrix-free methods generally.
Evidence is `strong-owl-matrix-free-screen.report.json`.

### Bounded toroidal patch screening: not adopted

Astra and Sol reconciled the next screening into two stages: geometry correctness
first, then one bounded coupled contact-kernel attempt; geometry performance does
not gate that second attempt, but correctness does. Joint continuation targets
are 50x complete geometry improvement, verification p95 at most 1 ms, and cold
QP p95 at most 2 ms. These are experiment targets, not device readiness claims.
The independent reports and final consensus are retained under the workspace
probe's `committee/strong-owl-*-post-backbone-*.md` paths. All three owned committee
resources, including the failed privacy-restricted Muse attempt, were archived
by their owner exit trap and their archived statuses verified.

The supported triangle-to-untrimmed-reference envelopes use directed 80-digit
Decimal arithmetic, adjacent correctly-rounded square-root results and upward
binary64 conversion. Independent mathematical review confirmed the Hessian
bounds and the barycentric interpolation constant Mh-squared/6. Ring-torus
radius and unsupported-patch uniqueness guards were added and the proof rerun.
Maximum toroidal envelopes are 18.902 and 20.583 micrometres. These are one-sided
bounds against the actual triangles, not reverse CAD, trim, solid-side or global
CAD-to-mesh certificates. Evidence is `strong-owl-mini-patch-envelopes.json`.

A single healthy-step replay retained 6,167 top-level geometry requests with
complete mesh snapshots and stage tags, SHA-256
`1e5b25f15d18d6af215fa7942dad13addd644267741336856f8838409eee1f14`:
2,514 assembly manifold queries, 2,926 merit manifold queries, 418 wood-clearance
queries and 309 channel signed-distance queries. It is retained as
`strong-owl-healthy-query-corpus.json`.

The workspace adapter applied outward binary64 whole-segment torus lower bounds
to immutable node masks, retaining triangle witnesses, containment and complete
unsupported traversal. All 6,323 corpus and actual-torus penetration/crossing/
sweep comparisons were bit-identical to the reference. However, independent
review identified a missing numerical bridge between mathematical distance
bounds and ordinary floating triangle-kernel comparisons near ties. Corpus
equivalence does not prove general floating-output preservation, so the Stage A
correctness gate remains incomplete.

Fifty alternating complete corpus replays measured reference mean 304.377 ms
and candidate mean 305.702 ms, a 0.9957x speedup. After 20 warmups, 100 alternating
complete cached verification replays measured candidate p95 30.127 ms versus
reference 31.791 ms. Both performance targets failed. The report was explicitly
qualified after review as corpus-tested output equivalence, not a general
output-preservation certificate. This screening ends without adoption or a
Stage B attempt because the correctness prerequisite remains unresolved. No
production collider, acceptance threshold, cord geometry or catalog profile was
changed. Evidence is `strong-owl-certified-patch-screen.report.json`; the exact
owned probe exited and process absence was verified.

### Scene display initialization now uses the guarded projection

The scene previously constructed a solver but measured and published its raw
seed directly. Consequently, separable finite-radius cord overlap was rejected
before `projectInitialization()` could run. `RopeDynamicsSolver.prepareDisplay`
now returns the corrected solver and its accepted first frame together, and the
scene calls that preparation on its existing detached worker before allocating
cord meshes or publishing a frame. Wood penetration, lost threading and proper
centerline crossings still fail the existing transactional preflight.

The regression uses two distinct overlapping cords with fixed, separated
supports. The previous display behavior failed with `Invalid initial display
geometry`; guarded preparation passes with matching solver/frame positions,
unchanged rest-length arrays and supports, and separated finite-radius cords.
All 12 host inter-cord tests and all 33 focused native scene/inter-cord tests
passed. A scoped independent review found no actionable issues. Evidence is
`display-preparation/behavior-{red,green}.log` and
`display-preparation-native-summary.json` under the retained live-cord context.

A proposed end-to-end synthetic scene fixture hit unrelated RealityKit/ODR
asset-loading errors and was removed; those failed runs are not validation of
the rope fix. Existing native scene tests validate the integration, while the
new regression targets solver-to-display preparation directly. This change
does not enable Mini or any new catalog profile, establish real-time performance,
or close the CAD error and designated-bearing proof gaps.
