# Four-lane Double narrowphase: closed

This experimental kernel packs four independent triangle calculations into `SIMD4<Double>`. It preserves candidate BVH masks, ordered face emission, original normal/witness reductions, branch precedence and per-query cutoffs. It changes actual closest-point/ray/edge arithmetic execution; it is not the previously closed immutable edge/ray cache or container-layout experiment. Geometry, precision, radii, physical solver, stop settings and acceptance are unchanged. App source is untouched.

All 934 original contact query bits/signs/witnesses and 2,802 moving swept witnesses/TOI bits match, including RED controls. Twenty strict steps retain full physical-checkpoint identity, independently checked clearance lower bounds and invalid-dt rollback. Those strict comparisons use the older pinned solver, so their timings include already adopted speedups and do not isolate this kernel.

The decisive same-binary comparison uses independent current-source solver/collider types. Both propagate the identical actual-seed upright-to-30-degree prefix through 139 steps, matching every physical checkpoint and correction/cap/retry schedule. Seven alternating copies of complete step 140 retain two corrections and zero caps/retries. Median candidate/control ratio is **0.965623**, failing the registered **0.80** maximum. All pairs are retained in the adjacent JSON; no packet-width, branch-activation, fixture, cap or threshold change followed.

The line is closed, unadopted. A roughly 3.4% host checkpoint saving cannot establish real-time app performance. There is no new app recording or rollout from this experiment. All compiler/probe groups were freshly rebuilt, owned, deleted and verified.

Evidence roots and source/provenance hashes are in the adjacent JSON. The prior actual app recording remains physically accepted, normal-speed and honestly below the real-time target. Its app was built with `-O` incremental compilation, whereas native screens use whole-module optimization; the build log establishes that distinction, but not a claimed speedup from changing compilation mode.
