# Packed numerical primitives — measured continuation screen failed

Base `6b5bed65f`, branch `feat/live-hangboard-physics`. One focused Opus consultation recommended measuring packed numerical primitives before implementing a complete packed primal interior-point solver. This checkpoint implements that isolated discriminator only. It does not change app sources, physical equations, contact rows, tolerances, regularization, iteration/admission caps or seated cords.

The favorable 15-refactor/30-solve/30-product sequence took **6.439 ms**, failing the predeclared **1 ms** continuation cutoff. The observed 15/46/46 schedule took **7.914 ms**. Both include fresh workspace allocation and initialization. This measured packing line is stopped; there is no full-IP implementation or adoption from this result. It is not a proof that every packed implementation or every accurate contact algorithm must fail.

## Exact-reference discriminator

The input is the previously captured first Newton pattern: dimension 5,707, 14,864 lower CSC entries, inverse SDK order, equality sign mask and 18,904 L+D entries. Its SHA-256 remains `b9ab3794ceb32de076e1399d097aca0aea7f651a15fcfd6bcd907827275e237e`.

The driver snapshots the committed `SparseLDL.swift` and appends a read-only, same-file extension exposing its private symbolic pattern and numerical state. Its arithmetic is not changed. The packed primitive uses preallocated buffers, Int32 pattern indices and a byte sign mask. Numeric loops allocate nothing and preserve the reference's arithmetic order, finite checks and pivot-sign rejection. The original lower-CSC product order is retained.

Fifteen deterministic, strictly diagonal-dominant quasi-definite matrices use the actual pattern and normal floating-point values. They change diagonal values between refactors. For each, D, L, scales, solve outputs and original-matrix products must match the reference **bit for bit** before any timing is accepted. The rejecting scaffold was observed RED, exit 4. The completed implementation passed all 15 comparisons. Separate reviewed validation also passes malformed sizes, NaN/infinity input rejection, validation-only retention of the prior factor, numerical-failure invalidation, wrong-sign rejection and successful recovery. It exits 0 and takes no additional timings.

## Measured scope

| Fresh-workspace sequence | Favorable 15/30/30 | Observed 15/46/46 |
| --- | ---: | ---: |
| Combined | 6.439 ms | 7.914 ms |
| Refactors | 2.839 ms | 2.751 ms |
| Solves | 2.336 ms | 3.391 ms |
| CSC products | 1.207 ms | 1.763 ms |
| Workspace allocation / initialization | 0.054875 ms | 0.006833 ms |

The correctness preflight warms **code, pattern and inputs** before timing; the observed schedule follows the favorable schedule. Fresh workspace initialization does not establish cold CPU caches or new OS pages. Symbolic construction, input packing, row processing, IP bookkeeping, original-factor preparation, recovery, complete KKT certification, geometry and rendering are excluded. Each sequence was measured once, without warm-repeat expansion or a statistical/device claim.

The synthetic matrices do not model late-IP conditioning, subnormal values or the exact locations of the 16 observed refinement solves. The observed schedule adds those extra solves/products after the 15 normal iterations and is diagnostic, not a faithful IP trace. Its checksum prevents discarding the work; the timing does not consume oracle answers or an accepted physical correction.

Opus's throughput assumptions and architecture estimates remain inference. This failure closes the measured implementation under the fixed continuation rule; it does not establish an inherent mathematical lower bound or justify weakening any gate. The next successor must address solve-pass count or another concretely different mechanism, with closed experiments recovered before implementation.

## Review and ownership

Scoped read-only review found no Critical or Important defect for this fixed, reference-exported pattern. Both Minor findings were addressed: explicit warmed-cache/fresh-workspace metadata and a shell symlink check for the Python cache before launch. `PrimitiveBuffer` assumes nonempty arrays from this fixed validated export; it is not a general product input API. The corrected launcher passes `bash -n`.

The owned shell launcher traps driver exit and the existing reserved-process-group helper traps compiler/probe cleanup. All six current child groups and three drivers were cleaned and their exact absences verified. No server, simulator, device or advisor resource was created for these runs. Evidence, exact compiled snapshots, RED/rejected outputs, review and receipts are under `.context/strong-owl-live-physics-packed-primitives`; the companion summary binds them by SHA-256. Previously bound evidence remains unchanged, including the intentionally failing catalog WIP.

The full cold QP still fails 2 ms; no new nonlinear physical timestep, general region certificate, healthy/jug verification, complete geometry speedup or iPhone result exists. The live-settling task remains active and unfinished.
