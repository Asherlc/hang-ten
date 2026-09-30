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
