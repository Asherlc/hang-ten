# Stock candidate discovery with original rope physics

Status: frozen-snapshot identity **PASS**; stricter intermediate gap certificate
**FAIL in both reference and candidate**; no product adoption or real-time claim.
This is a geometry experiment, separate from the failed stock dynamics screens.

Jolt supplies triangle IDs only. Every normal, witness, material fraction,
penetration depth, contact row, sign query and coupled correction is rebuilt with
the original Swift kernels. Masses, rest lengths, predictor, shared board height,
sliding passages, self/intercord rows, solver tolerances, merit, final checks and
rollback remain in the original solver. No stock impulses or rigid-body dynamics
are used. The accepted CAD/seated-cord PR #529 remains frozen.

## Registered checkpoint and discriminator

The loaded Clavellium checkpoint and descriptor are identical to the stock-chain
screens (SHA-256 `cad349812c3c0c33384378fe368abff97411f2a0c9aeb385d99edebef151c464`
and `c60fbd6dfaf59bfd5fb7e6aa8d806f78af7e828a7f64074d326865e08f13e853`). The existing
accepted control is `.context/strong-owl-live-physics-accepted-profile/native/after-1.json`.
Current core source is snapshotted before adding diagnostic hooks; the app files
are unchanged.

The first original contact-bearing linearization has 559 point/link wood queries,
248 returned wood witnesses and 468 complete constraints. Snapshot-only metadata
records the original triangle ID of each returned witness. Unknown inside-wood
triangle provenance or a missing returned witness fails the screen before solving.
Baseline capture preserves the prior accepted final checkpoint byte for byte.

Jolt revision `5830c342b90fa087f118aa0f086d541a4950b1d9` is freshly fetched and
built. Mesh triangle user data preserves original IDs despite internal reordering.
Raw shape-versus-mesh queries collect all hits, both triangle sides and all edges.
Spheres represent point queries; capsules use each queried segment's current
length, not its rest length. A pre-registered 1 µm discovery padding allows
overgeneration only: the original query radius, row kernels and physical gates
are unchanged. This finite float padding has no general completeness certificate.
The original oracle decides this snapshot's coverage.
[Pinned mesh metadata](https://github.com/jrouwe/JoltPhysics/blob/5830c342b90fa087f118aa0f086d541a4950b1d9/Jolt/Physics/Collision/Shape/MeshShape.h),
[query settings](https://github.com/jrouwe/JoltPhysics/blob/5830c342b90fa087f118aa0f086d541a4950b1d9/Jolt/Physics/Collision/CollideShape.h).

The 290 returned query/triangle candidates cover all 248 original witnesses. The
same captured Swift program then replaces only the first linearization's BVH
candidate list with these IDs, in original triangle order. It retains the original
ray-parity, Double triangle distance and duplicate-merge code. All 559 reconstructed
query results, all 468 rows, the complete correction and every multiplier are
identical to reference. There is no row reduction, independent loop solve, new
contact normal or change in the inertia objective. Subsequent corrections in the
step use the original discovery path. The final accepted checkpoint still matches
reference byte for byte; this is not a complete candidate-driven trajectory.

Two negative controls make the identity check meaningful:

- Removing triangle 5055 from query 185, associated with reference compressive
  multiplier −4.29566456e−6, produces that exact missing query/triangle pair and is
  rejected before solving. Nothing is added adaptively.
- Altering the expected candidate-injection source hook causes source capture to
  reject before compilation. Every transformation requires one exact match, and
  the replay additionally reports consuming all 559 candidate lists. A silent
  fallback to the original BVH cannot count as a pass.

## Numerical limits exposed

An independent Python reconstruction of the original inertial/curvature forces
and **every** equality/contact row gives the same certificate for both runs:

| Quantity | Reference and candidate | Gate/result |
| --- | ---: | --- |
| Stationarity | 8.519e−18 | PASS, ≤1e−10 |
| Regularized equality | 9.032e−18 | PASS |
| Physical affine equality | 8.291e−13 | PASS, ≤1e−8 |
| Minimum contact q | −2.033e−9 m | PASS, ≥−1e−8 |
| Minimum regularized gap | −2.033e−9 m | **FAIL**, ≥−1e−10 |
| Positive contact multiplier | 0 | PASS |
| Complementarity | 5.254e−21 | PASS, ≤1e−14 |

The staged 0.1 nm gap limit is stricter than the original solver's 10 nm inactive
admission tolerance. The original reference already fails that staged certificate;
the candidate neither creates nor repairs the failure. The physical accepted-state
identity and geometry-discovery identity remain measured facts. No numerical gate
was relaxed, and this is not a revived inexact solver experiment. These results
cannot be reported as a passing complete staged KKT screen.

## Costs and conclusion

The final guarded reproduction measures the following on the host:

| Stage | Original | Candidate |
| --- | ---: | ---: |
| New native mesh setup | excluded | 0.944 ms, separate |
| Native discovery, shape creation and ID decoding | — | 0.362 ms |
| Original row assembly, including sign and witness reconstruction | 2.059 ms | 1.184 ms |
| Original coupled correction | 1.470 ms | 1.500 ms |

With an existing native mesh, query plus instrumented assembly improves about
**1.33×** (2.059 → 1.547 ms). The earlier fresh reproduction measured 1.26×
(2.065 → 1.640 ms), with all the same identities. Report both rather than selecting
a favorable timing. These sums exclude process/file transport and serialization.
Baseline mesh setup is also outside its clock. Neither comparison is complete cold
performance, a frame benchmark, p95, or an iPhone result.

An earlier exploratory solve clock also included preparing captured row/reference
metadata. The reproducible tool stops it immediately after the original solve;
old exploratory samples are retained separately. Query/assembly instrumentation
still includes diagnostic witness capture in both configurations.

This establishes a narrow useful fact: stock collision machinery can discover
the exact triangles needed by this original correction without changing its
physics. It saves roughly half a millisecond of first-correction geometry work,
not the complete accepted step's remaining performance gap. Exact merit,
positive-clearance consumers, swept motion, later states, Mini production
resolution and complete geometry/device gates are unmeasured here. It is neither
a stock dynamics solution nor a real-time rollout. Seated cords remain available.

## Reproduction and ownership

Run `rtk proxy python3 Tools/HangboardRopePrototype/run_candidate_discovery_screen.py
--label <fresh-label>` from this dedicated workspace. The driver requires the
registered retained inputs/control and builds pinned native sources plus current
original Swift checks. A completed diagnostic can report a failed strict
certificate; `runtimeAdoption` stays false. Source drift, missing witnesses or
identity failures stop the driver.

Retained roots:

- `.context/strong-owl-live-physics-jolt-discovery/`: registered plan, original
  exploratory capture/native build, certificate discovery, replay and source-hook RED.
- `.context/strong-owl-live-physics-candidate-discovery-verified/`: first fresh
  reproducible run and missing-compressive-witness RED.
- `.context/strong-owl-live-physics-candidate-discovery-reviewed/`: guarded fresh
  reproduction with candidate-consumption evidence.

The summary and SHA-256 manifest bind inputs, original/generated sources,
dependency snapshots, pinned source revision/cleanliness, native binaries, commands
and comparison outputs. All exact registered process groups were removed and
their absence verified. No simulator, HTTP server, shared or historical process
was used. Product physics and rendering are unchanged.
