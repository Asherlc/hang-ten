# Axis-aligned clearance primitive: closed speed screen

The separate axis primitive selects a coordinate only when all three actual
triangle vertices have exactly equal Double coordinates on that axis. It avoids
generic projection arithmetic without inferring exact geometry from a rounded
normal. The absent primitive failed its scalar fixture (RED), then its implementation
passed same-side, crossing, invalid, and non-axis triangle checks (GREEN).

An independent exact-rational audit passed 10,000 arbitrary-direction support
bounds, 10,000 axis bounds, and 10,000 BVH cases (6,916 pruned cases). Among generic
support cases, 3,986 bounds were positive. Stored triangle supports enclose exact
vertex projections; stored norm upper bounds dominate the exact squared norm;
every bound squared times the exact direction norm squared is at most the exact
support gap squared. Axis bounds are at most the exact one-coordinate gap.
The same optimized scalar build's LLVM contains no unsafe floating arithmetic
flags. This is a bounded corpus audit, not generic bit-equivalence to the original
rounded narrow phase or full trajectory acceptance.

The BVH argument is separate from the scalar fixture: bounded input/node
coordinates imply exact component gaps <=1 m. Each subtraction has absolute
rounding error <=u plus subnormal allowance (u=2^-53); max/min add none. Each
rounded square differs from the exact squared gap by <=3u plus O(u²)/subnormal
terms. Three squares plus two nonnegative additions contribute below 20u m²;
rounding radius² adds at most u*1e-4 m². The registered 32*ulpOfOne=64u allowance
dominates these terms. At radius>=1 mm, the squared distance lost by the 1 nm
guard is >=1.999999e-12 m², over 280 times that allowance. Thus a rounded box
rejection still establishes the guarded floor under this finite coordinate/radius
domain. Unknown domains retain original queries. No fast-arithmetic claim for
the entire app or per-face rounded candidate kernels is made.

At original-rate step140, all 279 receipts pass the original clearance oracle;
candidate/current poses are identical, strict difference 1.728 µm, two QPs each,
no caps/retries and all independent physical/material checks pass. Seven complete
cold pairs give median ratio **0.997786**, failing the fixed **<=0.80** speed gate.
Pair variability is large (ratios 0.779–1.833); this supplies no stable speed gain.
The version closes without additional sampling, threshold tuning, trajectory,
simulator adoption or video claim.

All seven newly owned fixture/proof/checkpoint compiler/run groups were cleaned
and independently verified absent. Source and result hashes, exact-rational audit,
LLVM and lifecycle receipts are retained in the companion JSON. The pre-registered
successor plan is `.context/strong-owl-live-physics-clearance-bounds-proposal/AXIS_PLAN.md`.
