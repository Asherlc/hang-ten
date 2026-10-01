# Native channel wood geometry: useful reduction, failed cost screen

Native tube proposals reduced the production wood manifold from **119,693
rows to 1,863**, and generation from **191.660 ms to 4.384 ms**. The measured
**43.72×** wood-generation speedup misses the fixed 50× discriminator.
Nonlinear point/full-link clearance took **5.731 ms** on the source and
**5.828 ms** on its corrected state, missing the 1 ms discriminator. This
implementation line stops before optimization, region certification or
nonlinear trajectory expansion. No app backend changes.

This experiment starts at `a14c36345` and measures the native geometry cost
missing from the earlier offline frozen-row replacement. It builds wood rows
directly from fixed production positions rather than scanning stored rows.
Both 715-particle material loops retain their radii and rest lengths. The two
U channels use the retained 6 mm core radius, 3.7 mm wall radius, centres
`(±63,24,33)` mm and a mouth cutoff at 65.8 mm. For both channels the pilot
uses the upward-rounded worst retained wall envelope, 16.319 micrometres;
this is slightly tighter than the earlier first-channel proposal. It is not
a new accepted QP representation.

Point rows subtract the original 3.5 mm rope radius, 0.1 mm clearance,
wall envelope and incident rest-link restriction. Their gradient allows
axial sliding and retains the coupled board-height derivative. On-core
points receive no arbitrary wall normal or pin. Row generation replaces
678 point supports and 676 complete links. The source satisfies the assumed
0.5% link-strain gate; rest links and endpoint offsets determine conservative
restrictions. Other supports retain original triangle manifolds, including
the existing material-fraction filtering. Portal, self/intercord and swept
constraints remain required and are outside this wood-only clock.

Nonlinear clearance evaluates the actual complete link, including the
corrected state's current geometry. The core is a unit-speed C1 curve with
curvature at most `1/R`. Interpolation error is bounded by core-arc-span
squared divided by `8R`; endpoint offsets add their maximum magnitude.
Same-leg links need no curvature allowance. Mouth, ambiguous, distant and
excessive-allowance cases fall back to original triangles. Midpoint-only
testing would miss the bend-interior fixture and is not used.

These are ordinary floating proposals. General ring coverage, foreign wood,
sign, transcendental rounding and motion-region validity are not certified.
All **2,858 original signed point/full-link queries** independently check
each of the two fixed states:

| State | Original minimum | Proposal minimum | Maximum absolute difference | Maximum overstatement | Native candidate time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Source | 3.603183 mm | 3.586741 mm | 16.447 µm | 0 | 5.731 ms |
| Corrected | 3.603605 mm | 3.597667 mm | 16.467 µm | 0 | 5.828 ms |

The isolated ≤100 micrometre comparison passes on these inputs, with zero
incorrectly clear supports at the isolated radius-minus-100-micrometre
threshold. This does not authorize a general sign shortcut or establish a
nonlinear-to-affine certificate. Corrected-state strain/material failure
from the earlier sparse-LDL checkpoint remains: no accepted timestep,
motion, bearing, self/intercord or CCD result is produced.

Each state uses 1,354 tube queries and **1,504 original triangle fallbacks**.
Their individual cost split was not measured; saying fallback dominates cost
is an inference, not a profiler result. Static collider/channel construction
took 91.368 ms and is excluded from both steady-state query clocks. Query
classification, link restrictions and full row coefficients are inside the
row-generation clocks. Checksums retain the constructed coefficients.
Exactly one control/candidate sample was run per operation; no p95, 50-run
or device result is claimed.

The report's `woodMeritCostPassed` field names a **clearance evaluation**
diagnostic. It does not time the app's merit function, which uses deepest
whole-link penetration and other physical terms. The committed tool retains
that historical field name so the captured report and source agree. These
wood-only costs cannot satisfy the complete-geometry, full-merit, cold-QP,
healthy/jug verification or iPhone gates.

Nine native physical fixtures yielded eight failures against the empty
implementation, then nine passes. A later coordinate-domain guard made the
first GREEN source stale; final-source fixtures were repeated under a fresh
label and all nine passed. The reviewer found no Critical or Important
experimental defect. This fixtures-only check did not repeat or expand the
timing pilot. The immutable summary binds inputs, source snapshots, RED/GREEN
and final-source evidence, review and exact resource-cleanup receipts.
All eight owned compiler/probe groups and four driver processes are verified
absent. No server, simulator, CAD asset or material was changed; seated cords
and the intentionally failing inventory WIP remain available and untouched.

The next discrimination concerns required outputs: whole-support separation
from the actual mesh root box can prove an empty manifold and zero wood
penalty without finding an exact nearest distance. Exact-rational coverage
analysis is separate from this stopped pilot. It is not performance evidence
or permission to omit uncertain geometry.
