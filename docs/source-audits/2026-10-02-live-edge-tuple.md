# Per-face edge tuple allocation

Optimized WMO IR, including a separate module containing only original rope
types, confirms a 272-byte heap allocation for `[ab,bc,ca]` on the outside
narrowphase path. The native candidate retains the three original segmentPair
computations, then performs the same masked row/merit calls explicitly in their
original order. Its IR removes that allocation and deallocation. Arithmetic,
pruning, manifold order, parity, inside fallback and clearance receipts remain.

All 934 query and 2,802 moving-sweep bit-identity checks and their RED controls
passed. Twenty strict paired steps retained original complete state, conservative
per-link clearance bounds and rollback. Seven current-source alternating pairs
after 139 matching actual-seed prefix steps also retained complete checkpoint
and correction-schedule bit identity, with two corrections and zero caps/retries.

The complete-step median ratio was **0.873003**, failing the fixed **≤0.80** gate.
The line is closed without adopting the change, retrying timing, combining it
with another candidate, or changing the gate. Strict-test timings include prior
accepted optimizations relative to the pinned original and must not be presented
as this candidate's gain. Native comparison modules contain duplicate rope
types; their timings establish no app or iPhone performance result.

No product code changed. The adjacent JSON binds plans, snapshots, evidence and
nine exact child groups whose deletion was independently verified. The single
original-type IR also retains outlined triangleClosest, segmentPair, witness
consider and manifold merge calls; those are separate compiler boundaries,
not evidence that forcing inlining will improve runtime.
