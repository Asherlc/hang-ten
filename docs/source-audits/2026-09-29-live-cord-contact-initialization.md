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

This diagnostic measures self-contact within each loop. Contact and swept
collision **between** separate loops still need implementation before a
two-loop live profile can be promoted. Mini Bar grip transitions and live app
screenshots remain required. The other catalog profiles and the physical-device
performance gate are also unfinished; simulator acceptance does not establish
60 fps or a device worker budget.
