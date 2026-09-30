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
