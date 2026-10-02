# Stock Bullet articulated-chain discriminator

Status: completed, **FAIL**, no app adoption. The point-joint Jolt screen
failed continuity and strain. This successor tests a structural change: stock
reduced-coordinate spherical joints keep neighboring rigid links connected by
construction. The remaining closed-loop endpoint is measured separately. No
iteration count, timestep, material length or acceptance tolerance was tuned.

## Fixed model and setup

The same loaded Clavellium checkpoint contains 280 particles, 279 nonuniform
1–2 mm links, radius 3.5 mm, a 550 mm loop, density 0.01 kg/m and a 1 kg
display-estimate board. Only the two original, coincident overhead supports are
fixed. There are no channel pins. The actual 10,200-triangle descriptor is retained.

- Checkpoint SHA-256: `cad349812c3c0c33384378fe368abff97411f2a0c9aeb385d99edebef151c464`.
- Descriptor SHA-256: `c60fbd6dfaf59bfd5fb7e6aa8d806f78af7e828a7f64074d326865e08f13e853`.
- Fresh Bullet revision: `63c4d67e337017f9d8b298c900e9aabdb69296e7`.

The prototype builds stock Bullet in double precision, with one thread and the
unchanged default 10 solver iterations. Warm starting, friction and restitution
are off. Each capsule has its original material centerline length and physical
radius. Mass and inertia installation are checked exactly: m = density × rest
length, transverse I = mL²/4, auxiliary axial I = 1e−6 times transverse I.

A collisionless fixed dummy sits at the first original support. The first physical
link has a spherical joint and can rotate freely. The last link closes to the
second original support through stock `btMultiBodyPoint2Point`; that closure is
iteratively enforced. Self-collision remains enabled, with the original intrinsic
πr/common-support 4r exclusions. This single-loop fixture supplies no inter-cord
coverage. The centerline-crossing exception is checked externally.

The board's actual GImpact mesh has zero triangle margin. Its only dynamic
coordinate is a prismatic multibody joint along world Y; its bounded rotation is
prescribed at the original 2.1 rad/s rate. This representation was selected before
the first run: the pinned multibody contact code's rigid-body denominator does not
honor a rigid body's restricted translational `linearFactor`. No engine patch was
made. [Pinned multibody solver](https://github.com/bulletphysics/bullet3/blob/63c4d67e337017f9d8b298c900e9aabdb69296e7/src/BulletDynamics/Featherstone/btMultiBodyConstraintSolver.cpp).

The original board gravity/damping predictor is applied to its joint velocity.
The articulated chain's old generalized velocities are damped and physical gravity
forces applied once; world gravity and engine damping are off. Initial endpoint
mapping error is 0.0936 nm. Projecting original endpoint velocities onto an exact
articulated tree leaves a measured maximum discrepancy of 0.122 mm/s. The rigid
limit, auxiliary axial inertia and velocity projection are explicit model limits;
this screen does not prove equivalence to the original regularized inertial KKT.
Stock contact also uses actual radius rather than the original 100 µm clearance
skin. Final original physical checks remain unchanged.

## Invalid collision registration retained

The first dynamic import omitted explicit collider group/mask arguments. The
inherited dynamics-world defaults are `StaticFilter` / `AllFilter ^ StaticFilter`,
so all board/link pairs were rejected by the callback. `addMultiBody` does not
repair those collider masks. Its apparent 0.324/0.294 ms updates, zero manifolds
and final penetration are **not** evidence of the intended contact-enabled model.
[Pinned defaults](https://github.com/bulletphysics/bullet3/blob/63c4d67e337017f9d8b298c900e9aabdb69296e7/src/BulletDynamics/Dynamics/btDiscreteDynamicsWorld.h),
[link collider flags](https://github.com/bulletphysics/bullet3/blob/63c4d67e337017f9d8b298c900e9aabdb69296e7/src/BulletDynamics/Featherstone/btMultiBodyLinkCollider.h).

Separate fixed-pose collision worlds with compatible groups detected contacts in
both the initial and retained final poses. This falsified the proposed explanation
that no contact existed before integration. The invalid run is retained verbatim
under `invalid-collision-groups`. The corrected import uses explicit
`DefaultFilter` / `AllFilter` and verifies every installed proxy before stepping.
The same binary's RED fixture rejects the inherited defaults before producing any
proposal; GREEN is the explicit stock API registration. A wrapper return-code
error was caught by the driver, fixed, and its log retained; it did not change
physics arithmetic or justify adoption.

## Contact-enabled result

Fresh tracked-driver reproduction builds pinned sources, checks input hashes and
installed properties, and runs two independently constructed cold copies:

| Measure | First | Repeat | Gate/result |
| --- | ---: | ---: | --- |
| Stock update | 50.138 ms | 50.715 ms | FAIL, host screen limit 4 ms |
| Mesh/chain setup | 8.584 ms | 7.969 ms | Separate from update |
| Internal endpoint gap | 3.33e−15 m | identical | PASS, screen limit 10 nm |
| Closing support gap | 116.125 µm | identical | FAIL, screen limit 10 nm |
| Reconstructed strain | 4.952343% | identical | FAIL, physical limit 0.5% |
| Total material error | 0.098620 mm | identical | PASS, physical limit 0.5 mm |
| Original-mesh segment clearance | 3.459804 mm | identical | PASS, minimum 3.45 mm |
| Actual capsule clearance | 3.459804 mm | identical | PASS |
| Passage/topology refresh | valid | identical | PASS |
| Reconstructed wood/self sweep | valid | identical | PASS |
| Original metrics | 1.841 ms | 1.740 ms | Host verification only |
| Reconstructed sweep wrapper | 4.169 ms | 3.882 ms | Host verification only |

The complete retained stock state, actual capsules, reconstructed checkpoint and
closure impulses match exactly between cold copies and the earlier correctly
registered run. The latter's update times were 55.143/47.213 ms and are retained
separately rather than selected as a faster benchmark. Neither pair is p95/device
evidence.

Each corrected step records 83 wood manifolds / 82 contact points, one positive
wood impulse totaling 1.8764e−6 N·s, and **30,580 empty self manifolds with zero
self-contact points**. There are 30,831 broadphase pairs in the retained final
count, sampled after untimed `forward()/updateAabbs()`, not a peak measured within
the update clock. Manifolds are candidate
storage, not solved contact rows. Stock `updateSingleAabb` expands each shape box
by the 20 mm global contact-breaking threshold on each side. That is a plausible
cause of the excessive empty candidate workload at 1–2 mm spacing, but no runtime
split attributes the 50 ms to that stage. The threshold was not tuned.
[Pinned AABB expansion](https://github.com/bulletphysics/bullet3/blob/63c4d67e337017f9d8b298c900e9aabdb69296e7/src/BulletCollision/CollisionDispatch/btCollisionWorld.cpp),
[threshold definition](https://github.com/bulletphysics/bullet3/blob/63c4d67e337017f9d8b298c900e9aabdb69296e7/src/BulletCollision/NarrowPhaseCollision/btPersistentManifold.cpp).

Internal rigid links do not stretch. The reported reconstructed strain includes
restoring the displaced last capsule endpoint to its mathematical fixed support.
That reconstruction is exposed as an error, not accepted as a connected chain.
One positive wood impulse establishes response, not sustained load bearing: the
board velocity is slightly more downward than its free-fall predictor.

GImpact's TOI implementation returns 1, so the stock step does not provide the
required swept-mesh guarantee. External checks here cover reconstructed material
segments, not every actual rotating capsule. Original KKT, merit, convergence,
actual-capsule CCD, rollback, bearing, repeated transitions, Mini production
resolution and catalog/device gates remain unproven. No app trajectory or screen
recording was made from a rejected state. Seated cords remain available.
[Pinned GImpact TOI](https://github.com/bulletphysics/bullet3/blob/63c4d67e337017f9d8b298c900e9aabdb69296e7/src/BulletCollision/Gimpact/btGImpactCollisionAlgorithm.cpp).

## Reproduction and conclusion

`Tools/HangboardRopePrototype/run_articulated_chain_screen.py` fetches the pinned
library and JSON header, builds native programs and current original Swift checks,
and retains RED/GREEN import checks, both cold proposals, fixed-pose probes and
source/input/binary hashes in a fresh owned directory. Generated outputs belong
under `.context/strong-owl-live-physics-*`. Every exact registered process group
is cleaned in `finally` and its absence independently verified. No simulator,
HTTP server or shared/historical resource was used.

Final review added the imported stock-driver constants/digest dependency to the
snapshot list. Its unchanged source is additionally bound to the reproduced run;
this provenance-only correction required no repeat of the physical step.

Retained roots are `.context/strong-owl-live-physics-bullet-articulated/` for the
registered plan and setup diagnosis, and
`.context/strong-owl-live-physics-articulated-chain-verified/` for the fresh driver
reproduction. The accompanying summary and SHA-256 manifest bind that evidence.

This closes the registered stock articulated screen without tuning. It confirms
that reduced coordinates eliminate internal joint drift, but the stock tree plus
iterative closing joint does not meet our support accuracy. It does not prove that
an accurate native solution is impossible. A stock library is not yet a verified
drop-in solution for this closed material loop and moving concave board.
