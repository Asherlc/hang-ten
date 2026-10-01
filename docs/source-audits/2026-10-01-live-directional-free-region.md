# Directional free-region proof and remaining wood-query cost

Owner `strong-owl-live-physics`, branch `feat/live-hangboard-physics`, base
`b0aea6c877fe418c29e9a79f32b72d38b17a09f4`. Experimental geometry evidence only;
no app change, collider replacement, force, pin, tolerance or accepted live step.

The previous link-local isotropic free-region certificate was insufficient for
18 source bend links. Their offset is primarily along Y, while the limiting wall
witness lies in the XZ plane. A narrower planar / wider Y free region addresses
that lost directional information without changing the original triangle surface
or the exact zero-wood-penalty semantics.

## Fixed hypothesis and complete geometric checks

Before any run, PLAN fixed planar semiaxis **3.690 mm**, Y semiaxis **3.698 mm**,
swept around the same finite U cores: centres `(±63,24,33)` mm, bend radius 6 mm,
straight mouths z=65.8 mm. These are a *sufficient empty-region certificate*, not
replacement collision geometry or a prescription for the cord. Neither axis was
tuned. Every actual mesh triangle, including foreign wood, must be outside this
region. Sampling alone cannot establish it.

Seven actual samples from each of 42,796 triangles gave minimum F=1.000389904 in
both channels. This ordinary-float falsifier passed. The corrected all-triangle
proof then certified **85,592 original triangle/channel pairs**, using exact
binary-input Fraction midpoint subdivision and outward 80-digit Interval bounds.
It visited 104,270 nodes / 94,931 leaves, maximum depth 10, with minimum certified
leaf F=**1.000000323116437786…**. Offline proof time was 32.131 s, inside fixed
depth14 / 300,000 nodes / 180 s limits. It is not a runtime timing.

For a lower-circle chart, F=((ρ−R)/a)²+(y/b)². On an entire triangle box with
ρ≥ρ_min>0, its planar Hessian is bounded below by −2k I, where
k=max(0,R/ρ_min−1)/a². Consequently the gradient support at the barycentre minus
k times planar squared displacement is a lower bound. That support is concave,
so checking its three vertex bounds covers the complete triangle. Finite-leg
squared distance is convex and uses the corresponding gradient support. Box
bounds cheaply certify distant triangles; unresolved triangles subdivide. For
z≥0 only the finite legs determine U distance; for z≤0 the lower circle does.
Crossing triangles require bounds for both charts.

The whole rope link is checked independently. Its planar distance maximum uses
piecewise finite-leg endpoint maxima and the exact quadratic radial minimum of
each lower-circle chord; its maximum |Y| is at an endpoint. This avoids adding a
planar chord bulge to the Y offset as an isotropic error. Let those bounds be d,e,
and use the full original capsule radius r=**3.6 mm**, including the 0.1 mm
clearance, without borrowing the 10 nm merit tolerance. With A=1/a², B=1/b² and
C=r e B−r²(A−B)>0, a valid disk-containment upper bound is
(r+e)²B+d²A+(r d A)²/C. Its derivation uses u1²+u2²=1 exactly for the quadratic
terms and u2≤1−u1²/2 only for the nonnegative linear Y term. The unrestricted
concave quadratic maximum over u1 is conservative. The independent isotropic
bound A(√(d²+e²)+r)² remains a fallback / additional upper bound.

Independent exact-binary board-frame endpoints, Fraction splits/radial extrema
and outward arithmetic certify **all 676 retained tube links in each state**.
Maximum capsule F upper bounds are **0.998739434260635567…** source and
**0.992840755289427756…** corrected. This proves containment of complete capsules,
not just endpoints or sample midpoints. The triangle and capsule proofs together
establish unsigned separation for these retained supports.

## Runtime discriminator: closed before candidate implementation

Opus recommended measuring the remaining original-query cost before investing in
a native certificate. The already-running offline proof was retained; the native
screen deliberately gives all 676 labelled tube links a *free* exclusion and also
excludes the same 602 root-separated links. Even that optimistic path still has
**150 original `segmentContacts` queries** per state:

| Fixed state | Original 1,428-link wood control | Remaining 150-query floor |
|---|---:|---:|
| Source | 85.598 ms | **2.289 ms** |
| Corrected | 85.895 ms | **2.308 ms** |

Both fail the unchanged **1 ms** gate before source transforms, tube/root mask
construction or runtime certificate cost. All original per-link maximum depths
and the summed wood penalty are bit-identical after the optimistic exclusions;
the penalty is zero in both states. All masked links are empty under the original
query and both endpoints are parity-outside. There were **zero candidate runs**.
The fixed ellipse plus unchanged original fallback is closed as a runtime
successor. These are measurements of that particular remaining-query path,
not a universal lower bound or a claim that no faster geometry algorithm exists.

Static collider construction was 82.742 ms and excluded from both clocks. As with
the prior exact wood floor, all other merit terms, contact-row generation, exact
positive clearance, CCD, QPs and full device steps are outside this screen. The
previous 43.72× geometry result and ~30 ms accurate cold QP remain failed.

## Errors, review and limits

First triangle proof stopped at depth14 on triangle4733; it was unaccepted. The
checker unnecessarily required an upper-circle extension for a triangle wholly
above the G1 plane but touching z=0. Correct equality-chart selection fixed this
without changing the shape or caps. Also `abs(Decimal)` silently rounds under the
ambient context; `copy_abs()` retains directed digits. Four proof fixtures ran
RED (two failures) → GREEN (four passes), including rejection of an inside
crossing triangle. Seven capsule fixtures ran RED (six failures) → GREEN (seven
passes), covering chord bulge, straight legs, G1, finite mouths and clipped disks.
The first independent-capsule invocation had a generator SyntaxError and no
result; the corrected fresh source changes only the required parentheses.

Opus agreed with the directional/disk argument and pointed out its thin margins
and load-direction limits. Its rational Y-scaling / Bernstein alternative was
not implemented because the retained support proof completed and the remaining
query floor failed. The exact binary axes used here need not equal the ideal
decimal ratio 1845/1849 exactly; the proof uses their actual retained values.

Unsigned surface separation does not by itself prove what the numerical parity
routine returns. The retained fixed-state parity agreement is required and is
not a general runtime sign certificate. A connected empty region extending past
the mesh root could give a topological exterior argument for a closed mesh; this
checkpoint does not establish manifold closure or general numerical parity.
There is no held-out jug coverage, accepted nonlinear correction or trajectory,
device performance, general CCD result or product adoption. Seated cords stay
available. The intentionally failing live catalog inventory remains untouched.

Evidence and exact owned-resource deletion receipts are bound in the companion
summary. The retained root becomes immutable at commit.
