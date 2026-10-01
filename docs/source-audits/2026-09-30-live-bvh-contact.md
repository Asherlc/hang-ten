# GPU BVH contact candidate screen — 30 September 2026

The reusable [native geometry screen](../../Tools/HangboardRopePrototype/run_native_geometry_screen.sh)
implements a bounded successor to the earlier flat GPU broadphase. It traverses
the current triangle collider's immutable BVH using outward one-micrometre
integer bounds, counts candidates, then emits a compact list of original
triangle indices. It does not change collision geometry or the application.

CPU queries retain the current inside/outside classification and inside-solid
fallback. A generated same-file adapter preserves the current triangle
distance, witness, normal and manifold code verbatim, replacing only candidate
gathering. Exact output construction remains on the CPU. Every source triangle
must belong to exactly one leaf, and malformed trees, stack/emission failures
and an eight-million-candidate budget fail closed.

The fixed SHA-bound healthy corpus contains all 6,167 queries from the retained
coarse Mini step: 5,440 segment-contact queries, 418 segment-clearance queries
and 309 signed-distance queries across the body and two channel meshes. The
last two query families retain their original implementation. The input hash
is `1e5b25f15d18d6af215fa7942dad13addd644267741336856f8838409eee1f14`.
No prefix or easier fixture replaced the complete frozen workload.

The final current-source tool replay on the shared Apple M1 Max host measured
50 repetitions after ten warmups. Query packing, allocation, command
submission, waits, candidate readback/sorting and all exact CPU outputs are
inside the accelerated clock. Static mesh, tree and pipeline setup are excluded
equally from the two steady-state query clocks. No output result cache is used.

| Measured work | p95 |
| --- | ---: |
| Original complete CPU geometry corpus | 298.027 ms |
| GPU candidates plus complete exact CPU output corpus | 177.473 ms |
| Packing, traversal, compaction and readback | 58.909 ms |
| Exact CPU output work, including unchanged metrics | 119.797 ms |
| Two GPU command durations | 28.702 ms |

Component percentiles do not add to the total percentile. The ratio of the two
complete p95 measurements is 1.679×, which fails the immutable 50× screen.
The replay exits `3`. This is a same-process host comparison, not a controlled
hardware speedup or device-performance claim.

Two complete output passes, 12,334 query outputs in total, match the current CPU
reference exactly: contact counts/order, centerline and surface witnesses,
normals, fractions, penetration depths and scalar clearances/distances. The
compact list contains 1,005,583 candidates per replay. Exact matching does not
establish convergence, frozen affine-row correctness or a CAD tessellation
error bound, and this healthy corpus has no jug or CCD query coverage.

The fixtures verify conservative candidate emission, multiple leaves,
whole-segment/vertex witnesses, inside-solid fallback, coordinate bounds and
malformed trees. A missing leaf slot was reproduced as a failing real fixture;
exact leaf-slot coverage and overlap rejection now pass. Focused independent
review confirmed that correction and found no further issues. The six fixture
checks pass, the native contact suite passes 18 tests, and the reused process
lifecycle suite passes four real tests.

The [machine-readable evidence](2026-09-30-live-bvh-contact-summary.json)
binds 38 retained inputs, sources, generated current-source snapshots,
provenance, logs and a static ownership snapshot. Every exact owned compiler
and probe group was deleted and verified. No Simulator, HTTP server, device
installation or old/shared resource was created or modified.

This implementation stays experimental. It shows that replacing candidate
search alone leaves too much exact output work for the required geometry gate.
Seated cords remain available, the frozen accepted CAD PR stays untouched, and
no pending board gains a live profile. Cold-QP, complete motion, CAD-error,
native visual and iPhone performance gates remain unresolved.
