# Frozen contact streaming and full-resolution Mini checkpoint

This follows the [native admission screen](2026-09-30-live-contact-admission.md).
The app backend, seated cords, catalog profiles, material, tolerances and
physical gates remain unchanged. The new
[native replay tool](../../Tools/HangboardRopePrototype/run_native_contact_screen.sh)
is experimental and does not build the app. The
[summary](2026-09-30-live-streamed-contact-summary.json) binds retained evidence
to SHA-256 hashes. All measurements are on a shared host, without a controlled
speedup or device-performance claim.

## Representation and bounds

One immutable frozen geometry/Jacobian source can contain more than 100,000
inequalities. It supplies rows to a simultaneous solve of both material loops,
the original equalities and board height. Only admitted rows enter the working
QP, whose existing 100,000-row budget is retained. Full affine scans validate
clear and omitted rows too. Variable-reference grouping selects initial
representatives only; it never establishes redundancy. Every coupled candidate
is checked against every original row. Streaming changes the QP input
representation; the current geometry producer still assembles all raw rows.

The CSC pattern is fixed only within an unchanged admitted linearization.
Every new Newton weight receives fresh numeric values and an Accelerate
`SparseRefactor`; changed rows or Jacobians rebuild the pattern. The 50 Newton
iterations, 20 admissions, 50,256 variables, 256 nonlocal/border budget and
8-million-entry guards remain bounded. Initial multipliers are validated but
do not initialize the interior-point state; no warm-state benefit is claimed.

Focused review found and corrected certification at the physical 10 nm cutoff:
the regularized contact residual instead requires 0.1 nm. A one-variable row
with a 5 nm initial violation reproduced rejection in the new fixture before
the fix. It now passes alongside 13 other fixtures. Independent full-matrix
validation retains stationarity/equality/contact limits of `1e-10`,
complementarity `1e-14`, physical feasibility `1e-8`, and the existing oracle
agreement requirement of 1 micrometre.

## Fixed checkpoints

| Workload | Numerical result | Host time | Limit |
| --- | --- | --- | --- |
| Original hard QP, fixed-pattern context prototype, 50 cold runs | Oracle difference 0.866 µm; strict residuals pass | p95 107.049 ms | Cold QP 2 ms: fails |
| Original hard QP, reviewed streamed tool, 50 cold runs | Oracle difference 0.866 µm; strict residuals pass; 8 admissions end at 402 working rows | p95 295.673 ms | Cold QP 2 ms: fails |
| Production Mini first frozen correction, reviewed tool, one cold run | All 119,953 affine rows checked; 158 working rows; strict residuals pass | 231.229 ms | No p95; performance unestablished |

The original hard input SHA-256 remains
`93d9f142cf8c8b6d42d7e540838665505beba1b076e85c6d6ec035308dfc0be7`.
The new production first-correction input SHA-256 is
`c43720bccda76df9df92c9a155f3d4a5a11195011a9eca17b7ba42b1e27d1f97`.
It contains two 715-particle loops with 3.5 mm radii, 1,428 material equalities,
4,279 physical variables including height, and 119,953 contacts (119,781
wood/portal, 112 self, 60 intercord). Capturing it deliberately throws before
solving: the capture itself accepts no frame. All frozen wood/portal residuals
are initially clear, illustrating why clear rows still require global scans
after a coupled correction.

The tool clocks equality assembly/factorization, row construction, discovery,
admission, numeric refactors, solves and full affine certification. Frozen
decoding and reference indexing are outside that clock. Geometry, mesh updates
and device execution are excluded. Python independently checks the final
reported solution against the original full matrix. Native working solves and
full-row scans certify every replay candidate. Performance rejection or fewer
than 50 cold runs produce exit status `3`, even when numerical checks pass.

## Full solver scope and limits

An experimental copy of the current production Mini solver, with only its
contact-QP frontend replaced, initialized both 715-particle, 7 mm loops in
five corrections. Rest lengths, radii and supports stayed identical. Setup
took 11.896 seconds including collider/seed/projection/verification, after
descriptor decoding. Total length error was 48.407 µm, maximum local strain
0.003327693, minimum whole-segment triangle clearance 3.598966 mm, and topology
was valid. This experiment used the pre-review streaming prototype; it is a
physical initialization checkpoint, not the reviewed backend's full-motion
acceptance or an independent full-KKT audit of every nonlinear correction.

A fresh motion attempt using that same full-resolution prototype accepted its
first upright step at `dt=1/240` with original material and geometry checks.
That step took 54.888 seconds. The next step was still solving when the exact
owned probe was stopped at the 15-minute wall checkpoint, after logs reached
480 contact corrections. This is a partial prefix: no completed phase, p95,
settling result, convergence failure, loaded-bearing proof or CAD error bound
is inferred. No final frames/report were emitted by the interrupted motion
probe; the retained log and explicit wall-checkpoint record are the evidence.

Thus neither the complete-geometry 50× screen, 1 ms verification screen nor
4 ms iPhone simulation-plus-mesh gate is met. No new live profile is enabled.
The successor should address repeated frozen-row construction and complete
geometry/merit costs using fixed inputs; a QP improvement alone cannot close
the measured full-step gap.

## Ownership and verification

Focused review also fixed surviving-descendant cleanup, stale shell PID
signaling and interruption during spawn/registration. The driver keeps its
private-session leader unreaped until TERM/KILL signaling completes, then
verifies group disappearance. Signal exceptions are deferred during ownership
registration and cleanup; child masks remain unblocked. Four real lifecycle
tests cover a TERM-resistant descendant, interrupted execution, exit-status
preservation and an actual signal at the spawn-registration boundary. The
descendant fixture failed before the fix and passed after it. Darwin zombie
EPERM cases are verified explicitly, rather than treating signal failure as
deletion. Historical ownership records are never used as cleanup authority.

The final focused re-review reported no further findings. Four lifecycle tests
and 14 optimized native numerical fixtures pass. Replay gates explicitly fail
performance as shown above. Newly created processes were deleted and verified;
no Simulator, device installation or HTTP server was created. The intentionally
red live-catalog inventory WIP remains uncommitted.
