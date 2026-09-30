# Live contact admission and native CAD checkpoints

The bounded successor uses contact representatives to seed discovery, then
checks every original frozen affine inequality after each simultaneous solve.
Representatives are grouped by their variable references. That grouping does
not assert redundancy: stronger dependent rows and different witnesses are
admitted when the complete separation check finds a violation. Material
equalities, inertial/tension terms, independent physical loops, board height,
nonlocal rope contact and the original 1e-8 KKT regularizer remain coupled.

The retained hard Mini checkpoint has 1,249 physical primal variables, 418
material equalities and 22,641 contact rows. None of these experiments uses the
retained oracle or historical active IDs to discover contacts. The native
screens rebuild the equality matrix and factor on each cold run, including
discovery, contact solves and complete affine separation. Frozen input decoding,
variable/reference preprocessing, geometry queries and mesh updates are outside
that clock. All final numerical comparisons independently reconstruct the full
frozen problem in Python.

| Native backend | Cold runs | Admissions | Final admitted rows | Host p95 ms | Maximum primal difference from retained oracle |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing equality-projected dual Schur solve | 50 | 9 | 406 | 1678.147 | 0.250 um |
| Chain-band primal interior point with nonlocal Schur border | 50 | 9 | 402 | 2514.230 | 0.866 um |
| Compressed sparse-column primal interior point | 50 | 9 | 402 | 302.554 | 0.866 um |

All three pass the original complete numerical checks and the 1 um oracle
comparison; all fail the cold 2 ms checkpoint. These are separate shared-host
runs, so their timing differences do not establish device performance or a
controlled speedup. No backend is adopted in the app and no profile is promoted.

The primal implementations use the same Mehrotra equations and 50-iteration
bound, with at most 20 verified admissions. The band implementation preserves
nonlocal contacts as auxiliary rows in its joint Schur border. A single
instrumented replay performed 111 Newton factors and 222 predictor/corrector
directions: factorization consumed approximately 0.811 seconds, directions
0.210 seconds, assembly 0.010 seconds and complete separation 0.0046 seconds of
1.054 seconds total. The largest nonlocal border added 61 contact rows. This
motivated representing the same original Newton matrix directly as CSC rather
than forming that dense border. Apple's Accelerate sparse LDLT with threshold
partial pivoting supplies the native factorization; no physics engine or new
library dependency is introduced. [Apple sparse factor documentation](https://developer.apple.com/documentation/accelerate/sparse-matrix-factor-functions).

Both native primal implementations passed six independent hand-checked tests:
loop/height coupling, stronger dependent constraints, material-equality/height
coupling, distant-particle coupling, rejecting excessive physical penetration
despite a regularized algebraic solution, and input/budget rejection. The sparse
implementation was first run against a zero-direction stub: four physical cases
failed and the two rejection cases passed. All six pass after implementation.
The same positive-case/red-stub discipline was used for the earlier native band
and admission prototypes. These fixture counts are separate from the committed
production trust-rule suite.

Production Mini initialization remains rejected before publishing a frame. A
throwing diagnostic at its first correction found 119,953 finite, dimensionally
valid contact rows, exceeding the unchanged 100,000-row resource guard. The
production seed retains 715 particles in each of its two 7 mm loops. No cap was
raised, no smaller radius or coarse seed substituted, and this larger workload
has not passed the native prototype.

## Independent native CAD check

The six settled destinations from the committed relative-trust Clavellium run
were checked against the actual native `Pinch100BottomReliefCut` solid, with
source/descriptor hashes verified. The independently implemented quaternion and
coordinate-basis conversion maps every complete material segment into CAD
coordinates. Exact `distToShape` segment queries and inside tests check wood
clearance; reconstructed unique aperture crossings check expected upper bearing
within 0.2 mm and actual CAD surface gap within radius plus 0.3 mm.

All six production-resolution destinations pass. The minimum whole-segment CAD
clearance is 3.599397 mm for the unchanged 3.5 mm radius; the largest expected
upper-bearing offset is approximately 0.047055 mm. Rest lengths remain fixed and
the independent local/global length checks pass. This covers those six settled
states only. It does not certify transient motion, global mesh-to-CAD error,
shared runtime bearing acceptance, native visual review or device performance.
The actual solid includes 72 planar, 16 cylindrical and 8 spherical faces, so
its entire tessellation cannot be assigned zero planar approximation error.

[Machine-readable results and retained source/evidence hashes](2026-09-30-live-contact-admission-summary.json).
The owner-bound probes, source, frozen outputs and logs remain under
`.context/strong-owl-live-physics-execution/`. All seated cords remain available.
Complete geometry acceleration, production Mini convergence, the global 50 um
CAD error proof, shared bearing certification, physical-device runtime and the
16 pending live setups remain unfinished.
