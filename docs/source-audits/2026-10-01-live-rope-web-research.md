# Live rope solver: primary-source research, 1 October 2026

**There is an untested solver mechanism.** The closed block-impulse experiments
do not test nonlinear augmented-Lagrangian position minimization. Published work
supports investigating that distinction, but establishes neither our physical
acceptance nor our iPhone budget. This is research and a proposed discriminator;
no new solver is adopted or run, and no gate is changed.

The user requested web research after questioning the approach. I read author
papers, official engine documentation and pinned reference code, and asked the
already authorized Astra advisor for a focused, read-only comparison. This
reassessment does not reopen any failed screen or change PR529/seated cords.

## What the literature actually supplies

### Augmented Vertex Block Descent, SIGGRAPH 2025

[Giles, Diaz and Yuksel's paper](https://www.cemyuksel.com/research/papers/Augmented_VBD-SIGGRAPH25.pdf),
§§2.2, 3.1–3.7, 4 and 6: alternate small primal position solves with multiplier
and finite penalty updates. Constraints and force directions can follow current
positions; an augmented Lagrangian handles hard constraints without using an
infinite penalty. Quasi-Newton local Hessians improve robustness. With line search,
primal energy decrease is possible; this is not a proof of decrease of our merit.

Important limits: bounded iterations do not guarantee satisfied constraints.
The paper shifts constraints by a fraction of the previous error (alpha=0.95),
warm-starts force/penalty values (gamma=0.99), and uses GPU execution. It explicitly
notes that propagation along long chains can take multiple frames. Its reported
solver timings also omit substantial separately reported collision costs.

The useful mechanism is primal/dual nonlinear progress, not the headline object
count. Its demonstrated defaults are not a drop-in implementation of our rules.

### Author's AVBD implementation, pinned rather than assumed

[Reference repository](https://github.com/savant117/avbd-demo3d) commit
`7701bd427d55ca5d03ea1fdf331912ded9169f4b` is the fetched main commit.
I retained and read `solver.cpp`, `joint.cpp`, `spring.cpp`, `manifold.cpp`, headers
and README. No downloaded code was built or executed.

[`solver.cpp`](https://github.com/savant117/avbd-demo3d/blob/7701bd427d55ca5d03ea1fdf331912ded9169f4b/source/solver.cpp)
updates each body position using inertia plus constraint terms, then updates dual
variables. Joints/springs use current geometry. Default alpha=0.99 and gamma=0.999
differ from the paper; penalty parameters explicitly depend on units. The README
describes an understandable demonstration rather than an optimized implementation.

[`manifold.cpp`](https://github.com/savant117/avbd-demo3d/blob/7701bd427d55ca5d03ea1fdf331912ded9169f4b/source/manifold.cpp)
uses persisted feature contacts and a Taylor approximation, with an eight-contact
array. That supplies neither our whole-capsule triangle clearance nor complete
wood/self/intercord CCD. Do not copy its collision model or force persistence as
an accuracy certificate.

### Direct Position-Based Solver for Stiff Rods, 2018

[Deul et al.'s paper](https://animation.rwth-aachen.de/media/papers/2018-CGF-Rods.pdf),
§4.2: solve the complete acyclic rod constraints with sparse Newton/KKT work;
alternate this with nonlinear Gauss–Seidel collision and loop-closing constraints.
The linear-time result applies to the tree backbone, not to arbitrary contact
cycles. The paper explicitly calls out ropes fixed at both ends and rods touching
the environment twice as loop cases outside the direct tree solve.

Our coupled banded chain/height backbone already addresses the same propagation
problem in a different representation. The untested distinction is interleaving
nonlinear positional contact progress, rather than requiring a complete frozen
contact QP first. This paper is not a ready-made replacement for threaded loops,
and introducing its Cosserat bending/twist parameters would change our model.

### Small Steps in Physics Simulation, 2019

[Macklin et al.'s paper](https://mmacklin.com/smallsteps.pdf), §§4.2 and 6.1:
many smaller time steps, each with one XPBD iteration, outperform equivalent work
spent iterating one larger step in their tests. Adaptive rejection/retry of our
tightly solved steps is not that method.

The 20-particle, 1:100000 mass-ratio stress test still reports 3.2m maximum error
with 100 substeps, versus 322.1m with 100 iterations. Those numbers demonstrate
relative improvement, not millimetre accuracy. Collision detection is amortized
over a frame; the paper acknowledges missed contacts after trajectories change.
Its GPU demonstrations and substep counts cannot establish our <=8 steps/frame,
physical gates or whole-motion CCD. Merely taking more substeps is not a supported
successor under our current budget.

### A Multi-layer Solver for XPBD, 2024

[Mercier-Aubin and Kry's paper](https://www.alexandremercieraubin.com/Work/papers/SCA2024MultiLayerXPBD.pdf),
§§2 and 4: temporary rigid/elastic layers accelerate distant error propagation;
the final layer returns to the complete elastic model. This differs from replacing
the production material chain with a coarser chain. Extra permanent long-range
constraints would alter the problem; temporary acceleration must be removed.

It is evidence for a hierarchy as solver acceleration, not permission to publish
rigidified rope motion. Their tests use vectorized MATLAB on CPU and relative
performance measures. Pinned portions can immobilize a fully rigid layer (§4.3),
which matters to our supported ropes. No claimed speedup transfers directly to
our implementation or hardware. Treat this as a secondary propagation remedy,
not a second simultaneous implementation experiment.

### Official PhysX documentation: persistent contacts and TGS

[PhysX 5.7 collision documentation](https://nvidia-omniverse.github.io/PhysX/physx/5.7.0/docs/AdvancedCollisionDetection.html#persistent-contact-manifold-pcm)
describes refreshing cached contact features, generating additional contacts after
relative motion, and rebuilding a manifold when too many contacts are dropped.
It also states that generating fewer contacts can reduce stacking stability.
[Rigid-body documentation](https://nvidia-omniverse.github.io/PhysX/physx/5.7.0/docs/RigidBodyDynamics.html)
describes TGS's convergence and mass-ratio improvements.

This gives a concrete engine practice, rather than speculation about all games.
Our Jacobian-response cache exists only within a frozen solve; it is not a
persisted geometric contact manifold. Caching candidates could preserve geometry
if an authoritative separation/CCD query verifies coverage. Plain contact
reduction does not certify omitted old affine rows; the prior deepest-only
failure remains closed. Neither engine feature promises our exact workload.

### Relevant alternatives that do not justify rerunning closed screens

[Non-Smooth Newton Methods, 2019](https://arxiv.org/pdf/1907.04587), §§7–8,
uses scaled complementarity and symmetric systems, including inexact conjugate
residual solves. Its examples use damped updates that may increase its residual
merit. The underlying complementarity family is already represented in our
closed Fischer–Burmeister experiments; the complete nonlinear schedule differs.
Renaming the failed frozen solve after this paper would not be a new experiment.

[Primal/Dual Descent Methods, 2020](https://mmacklin.com/primaldual.pdf), §5,
shows the numerical distinction between primal penalty contact and dual hard
contact. Its relaxed contact permits penetration, so its examples are not proof
that a direct transplant meets our fixed physical or numerical limits.

[Fast Simulation of Inextensible Hair and Fur, 2012](https://matthias-research.github.io/pages/publications/FTLHairFur.pdf),
§3, guarantees geometric length with follow-the-leader but explains its inherent
uneven effective mass behavior and compensating velocity correction/damping.
Length preservation alone does not establish our inertia, coupled board load,
two supported branches or contact fidelity. Do not substitute this hair algorithm.

## Diagnosis grounded in our source and measurements

The following are repository findings/inferences, not results imported from a
paper. `RopeDynamicsSolver.correctConstraints` assembles all nearby facet rows,
solves a global frozen contact/equality problem, and only then changes positions
through global L1-merit trials. `BlockImpulse.solve` changes multipliers with the
same frozen rows/backbone. It does not refresh nonlinear geometry between its
16 contact sweeps. Its name does not make it primal vertex block descent.

The [strict](2026-10-01-live-solver-foundation.md) and
[inexact](2026-10-01-live-inexact-outer.md) outcomes therefore reject those
specified frozen-response methods, not nonlinear AVBD or the published
chain/contact alternation. Inexact proposals already failed globalization before
the 10nm convergence check, so removing only that stop is not supported.

Our latest complete matched Clavellium control accepts in53.748ms; the isolated
inexact attempts reject in191.897/192.979ms. Original-mesh checking and geometry
costs also remain. A better nonlinear direction alone would not establish speed.

There are two distinct contracts: physical fidelity of accepted motion, and exact
reproduction/certification of the previous frozen QP at intermediate corrections.
A primal nonlinear algorithm can seek the same inertial constrained state while
not satisfying the second contract during its iterations. This observation is
not authorization to drop it. Current handoff and numerical gates still govern.
User approval of one now-closed inexact experiment is not general permission.

## One next discriminator to prepare

Research prioritizes an **unshifted nonlinear augmented-Lagrangian position
experiment**, before another frozen-QP variant or geometry micro-optimization.
This is an adaptation inference requiring its own numerical contract, not a
claim that stock AVBD is equivalent or ready. Prepared boundary:

1. Use the identical full accepted Clavellium60-step private checkpoint, including
   velocities, material, sliding crossings, board state, tensions and history.
   Do not interpolate a Mini trajectory or use an unaccepted frozen correction.
2. Keep original prediction/masses/gravity/damping/orientation and full material
   chains. Use current-position length functions and three-coordinate particle
   blocks plus one shared board-height block. Include all participating rope,
   board, portal and nonlocal terms; do not solve each loop with height fixed.
3. Preserve unshifted constraint targets: alpha=0 semantics, without injecting
   reference-demo error offsets. Derive time/unit scaling and the relationship
   to the existing epsilon before choosing finite penalty/update rules. Publish
   those rules and a16-sweep cap before execution. No parameter/fixture search.
4. One candidate, identical replay, original matched control. Record full proposed
   states, nonlinear gradients/multipliers and separate inertial/length/wood/
   portal/self/intercord scores, covering the evidence absent from the last trace.
   Reject/rollback any invalid final radius, length, strain, original-mesh whole
   link clearance, topology or swept collision. No partial step is published.

Before a native build, resolve exactly which **intermediate** numerical checks
apply to nonlinear positional updates. Old frozen stationarity/equality and1um
oracle equivalence are not automatic invariants of those updates. Nonlinear
stationarity at the final candidate and original-merit acceptance are different
checks; augmented-energy decrease proves neither. Retaining original merit as a
guard is possible, but cannot inherit the paper's convergence claim. The cold2ms
QP,50x geometry,1ms healthy+jug and device4ms gates are not redefined by research.

If local propagation is the measured failure, evaluate a complete-chain/hierarchy
accelerator later as a separately bounded hypothesis. Do not start two new solver
families at once. Before adoption, accepted nonlinear trajectories, half-step,
determinism, loaded bearing, complete geometry and device performance all remain
required. A single Clavellium step would establish only that checkpoint.

## Evidence and lifecycle

Author PDFs, official HTML, pinned reference source, retrieval manifests, PDFKit
text, scripts and ownership receipts are retained under
`.context/strong-owl-live-physics-web-research`. Download errors from the web
reader (size/timeout) were resolved by verified-TLS primary downloads; all recorded
downloads succeeded. A PDFKit/CoreGraphics warning is retained; all six parsed
papers produced their expected page counts and text. Source URLs/hashes and local
model/checkpoint hashes are bound in the accompanying summary. Reference-code
licenses are retained; downloaded code is evidence, not app code or execution.

The one fresh owned PDF-extraction worker group and shell driver are absent and
verified. No HTTP server, tunnel, simulator, device, native physics probe or
external advisor process was started. Existing authorized Astra supplied focused
read-only advice; no app/model files or numerical gates were changed. The only
pre-existing untracked inventory test remains untouched. This root becomes
immutable after the research commit. Requested live settling remains unfinished.
