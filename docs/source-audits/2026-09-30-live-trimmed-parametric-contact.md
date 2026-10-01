# Isolated 0.10 mm trimmed-contact preflight

The user explicitly authorized an isolated geometric/contact error experiment
at 0.10 mm after the rendering simplification did not close the runtime gap.
Cord diameters, material/rest lengths, sliding crossings, coupled motion,
swept collision checks and the remaining numerical/stability/performance gates
remain required. This checkpoint changes experimental tools only. It neither
selects a new app backend nor promotes Mini or other catalog profiles.

## Hypothesis and fixed checkpoints

The preceding actual-triangle slab/batch pilot took 23.532 ms for the frozen
production candidate. Ordinary-float allowance discrimination suggests about
90% of its original wood/portal support rows could be bounded cheaply at a
100 micrometre nominal affine allowance; the toroidal channel rims dominate
the remaining triangle work. That discrimination is not a runtime certificate
or permission to loosen KKT tolerances. Portal rows were never discarded.

The successor tests whether finite, trimmed analytic surface images can replace
facet searching in an isolated contact representation. First bound each image
against its actual triangle in both directions, then test conservative trim
membership and measure one native lookup construction/query checkpoint. A
nearest-distance, whole-capsule, coupled-QP and motion experiment still has to
follow before adoption. We did not repeat a failed solver or increase caps.

## Two-sided image enclosure

Every supported mesh triangle receives deliberately chosen binary64 parameter
coordinates. A cylinder uses `(angle, axial position)`; a torus uses two angles;
an axis-aligned plane uses its two other coordinates. The parameter triangle
is retained, including its trim boundary. The union is not an untrimmed whole
cylinder/torus substitute. The two oblique-plane triangles remain original
fallback inputs. All 42,796 original triangle IDs are partitioned exactly once.

For barycentric weights, pair the mesh point and the reference image of the
same parameter point. The interpolation remainder is at most `max(Q)/6`,
since `sum(i<j, lambda_i*lambda_j) <= 1/3`. With parameter-coordinate diameters
`du,dv`, cylinder `Q = r*du²`, and torus
`Q = (R+r)*du² + 2*r*du*dv + r*dv²`. These bound the norms of both pure
derivatives and the mixed derivative. Add the largest actual vertex residual.
This pairs every point in either triangle/image with a point in the other,
giving a two-sided Hausdorff envelope.

Directed 80-digit arithmetic evaluates the actual chosen coordinates, including
vertex residuals. `sin/cos` use Taylor polynomials through degree 159 and
remainder `|angle|^160/160!` for the bounded `[-10,10]` chart domain. Inverse
trigonometry and floating periodic shifts merely choose coordinates; they are
not presumed correctly rounded inverses or exact periodic translations.
A regression caught caller Decimal precision affecting absolute-value
operations; exact Decimal magnitude/sign operations corrected it.

The full retained mesh passes this enclosure checkpoint: 42,794 parametric
tiles plus two original fallback triangles. Maximum two-sided envelope is
**0.016318854 mm**, below the authorized 0.10 mm. This bound also fits within
0.05 mm; it does not establish that increasing tolerance caused a speedup.
The offline directed proof took 278.403 seconds. It is not an app runtime cost.
Native CAD tessellation accuracy, watertightness, orientation and continuity
across independently chosen charts remain unproved.

## Native trim lookup and cost discrimination

`ParametricUV.swift` builds a BVH over the retained parameter triangles. Strict
orientation predicates establish interior membership; uncertain edges and
degeneracies return no certificate. Under the 10-unit coordinate bound,
determinant rounding is below `gamma_7*800 < 6.22e-13`. Padding `1e-10` retains
ambiguous cases. A shifted query coordinate is returned with its witness so a
distance caller can evaluate that chosen point instead of assuming exact
periodicity. BVH boxes never fill trimmed holes.

The original all-patch exploration considered all 2,858 particle points/link
midpoints against 14 supported patches: 40,012 lookups, 7.662 ms, with 17,004
reported interior hits. This used the initial raw-number bridge and is retained
as exploratory evidence, not the final source-faithful checkpoint.

The bounded successor first tests separation between the actual complete
support's AABB and each actual patch's AABB. It uses the original contact window
`r + 0.10 mm + 0.05 mm`, conservatively extended by the authorized 0.10 mm
representation budget. This increases geometric admission; it does not reduce
a physical clearance requirement. Differences are bounded by 20 m and squared
sums by 1,200 m²; subtracting `2e-12 m²` gives the existing conservative box
bound. Crossing links cannot be pruned by checking just their midpoint.

The first broad-phase replay was rejected by its independent validator:
`JSONSerialization`'s untyped NSNumber-to-Double bridge changed input values
by an ulp. Typed `JSONDecoder` input now preserves the source binary64 values;
an observed RED/GREEN source-value regression covers that change. Earlier
replays/results were retained without being relabeled as accepted input proof.

Final isolated single-run construction/query checkpoint:

| Work | Result |
| --- | ---: |
| Point/link-support × supported-patch pairs considered | 40,012 |
| Whole-support box skips | 36,244 |
| Point/midpoint projection and trim lookups | 3,768 |
| Strict interior hits | 2,130 |
| Admitted pairs needing original fallback/further work | 1,638 |
| BVH/source-array/patch-box construction | 44.901 ms |
| Broad phase + projection + trim lookup | 2.971 ms |

The independent validator reconstructs the fixed whole-support endpoints and
thresholds, then checks every skipped AABB pair with exact rational arithmetic.
It also checks every reported interior hit against its original parameter
triangle with exact rational determinants. Both checks pass. Each rim has
151 interior hits among 215 admitted pairs; 64 remain unresolved per rim.

The 2.971 ms figure excludes JSON loading, signedness, actual closest-distance
and normal outputs, unresolved fallback, continuous whole-link minimization,
manifold generation, self/inter-cord checks, swept collision, the coupled QP,
mesh updates and rendering. It is not comparable as a complete replacement
for the preceding 23.532 ms pilot. Construction alone exceeds a 2 ms cold
budget if performed there. No 50-run, p95, full-geometry 50×, production-motion
or device gate has passed. Keep this implementation experimental.

## Verification, review and resource lifecycle

Directed-envelope fixtures: six expected missing-feature failures to six
passes; precision regression fails then all seven pass. Native trim fixtures:
six failures to seven passes; whole-support broad-phase regression fails then
nine pass; numeric-input regression fails then ten pass. Final native suite:
**10/10**. Final full prototype Python suite: **50 passed, three failed**:

- `test_rope_settles_around_outside_of_round_bar`
- `test_wrong_wrap_topology_is_rejected`
- `test_fresh_simulations_are_repeatable`

All three still hard-code the absent historical
`.context/frantic-kiwi/rope-build/rope_solver`. We did not recreate that old
resource. The intentionally failing, untracked live catalog inventory test is
untouched and excluded from this prototype suite.

Scoped review found a launcher ownership gap: the initial shell recorded an
RTK wrapper while the Python coordinator owned worker cleanup. It now starts
the coordinator directly, as the existing owned launchers do. A bounded real
TERM fixture with a non-forwarding proxy observed failure at 5.365 seconds
(waiting for the fixture alarm), then success at 0.337 seconds. The installed
RTK's forwarding characterization had passed; no observed production RTK leak
is claimed. Initial Bash 3.2 `BASHPID` fixture failure and an incomplete
wait-based fixture are separately retained. Final review found no Critical or
Important issue; its minor scope wording correction is included.

All current owned compiler/probe/driver groups exited and their exact cleanup
was verified. No server or Simulator was started for this experiment. The
earlier native visual review cleaned all three owned Simulator attempts:
Penta seated cords are visible in front/side/top; Clavellium remained at a
loading spinner and is not a visual pass. The loader awaits live initialization
after USDZ loading, so the spinner alone does not diagnose an ODR failure.

The companion JSON summary binds immutable source snapshots, fixed inputs,
results, RED/GREEN evidence, review and cleanup receipts. The next useful gate
is certified complete-link distances with original fallback, followed by a
simultaneous coupled contact solve against that experimental representation.
Retain the existing physical model and seated cords until the full gates pass.
