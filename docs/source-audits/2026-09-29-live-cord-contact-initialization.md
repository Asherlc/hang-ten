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
