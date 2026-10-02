# Stock Jolt rigid-link discriminator

Status: completed, **FAIL**, no app adoption. Branch
`feat/live-hangboard-physics`; accepted CAD/seated-cord PR #529 remains frozen.

The user requested continuing live implementation and investigating why this is
not an off-the-shelf capability. The approved design permits a native rigid-link
alternative. This test adds an isolated dependency to a prototype, not the app.
It does not change physical tolerances or the accepted solver's numerical gates.

## Fixed input and implementation

The retained loaded Clavellium checkpoint has 280 particles, 279 immutable material
links, one continuous 550 mm loop, radius 3.5 mm, density 0.01 kg/m, and a 1 kg
display-estimate board. The only fixed endpoints are its existing overhead
supports. Its actual 10,200-triangle board mesh includes the rectangular channel.
The imported mesh has 15,300 edges with opposite incident orientations and positive
signed volume 0.0005492751587301993 m³. There is no hull or channel remesh.

Frozen input hashes:

- Checkpoint: `cad349812c3c0c33384378fe368abff97411f2a0c9aeb385d99edebef151c464`.
- Descriptor: `c60fbd6dfaf59bfd5fb7e6aa8d806f78af7e828a7f64074d326865e08f13e853`.

Freshly built Jolt revision `5830c342b90fa087f118aa0f086d541a4950b1d9`
provides stock capsules, point joints, dynamic meshes and TranslationY-only bodies.
Its mesh requires supplied mass properties when dynamic. These are actual library
capabilities, not a claim that its soft-body collision pipeline satisfies our rope
requirements. [Pinned mesh source](https://github.com/jrouwe/JoltPhysics/blob/5830c342b90fa087f118aa0f086d541a4950b1d9/Jolt/Physics/Collision/Shape/MeshShape.h),
[body settings](https://github.com/jrouwe/JoltPhysics/blob/5830c342b90fa087f118aa0f086d541a4950b1d9/Jolt/Physics/Body/BodyCreationSettings.h).

Each capsule's centerline uses its original individual rest length. Point joints
join neighboring centerline endpoints and only the original supports join the
fixed world. Link mass is density × rest length. Transverse inertia is mL²/4,
equivalent to two half-mass endpoints in the rigid limit. An auxiliary axial moment
of 1e−6 times that value makes the spin mode invertible; capsule spin is geometrically
unobservable, but this remains a model-equivalence limitation. All 1,741 excluded
capsule pairs match the original intrinsic πr and common-support 4r neighborhoods.
Their centerline-crossing exception is verified externally rather than solved by
the library. This fixture has one loop: no inter-cord coverage is claimed.

The board stays dynamically free in world Y, with the original bounded prescribed
rotation. Original gravity/damping is applied to initial link and board velocities;
engine gravity/damping is off. Initial endpoint mapping error is 4.138 nm. Projecting
endpoint velocities onto rigid-link translation and angular velocity is a distinct
rigid-limit model, not proof of the original regularized inertial objective.

Fixed settings: single worker; double positions (other Jolt arithmetic remains
float); 10 velocity / 2 position iterations; no warm start; zero friction and
restitution; LinearCast; 10 µm penetration slop and 50 µm speculative distance.
These are stock-engine configuration values, not relaxed acceptance gates.

## Setup failures retained, not performance evidence

The first C++ build used the wrong spelling of `SLERP`. The first runtime arena
was insufficient for the unchanged 65,536-contact capacity; it was increased from
32 to 128 MiB before any completed update. A bounded 45-second debugger attempt
timed out without a backtrace. All exact process groups were cleaned.

The first completed metre-unit runs were **invalid matched-inertia setups**.
Jolt silently replaces a tensor whose principal moments are near zero with a
unit-radius sphere. All 279 requested link inertias, 2.5e−12…2e−11 kg·m², trigger
that predicate. Their apparent 0.69/0.49 ms update and 1.34% strain cannot be used
to judge the intended lumped-chain model. A driver reproduction reproduced that
invalid result; it is not an additional accepted performance sample.
[Pinned inertia installation](https://github.com/jrouwe/JoltPhysics/blob/5830c342b90fa087f118aa0f086d541a4950b1d9/Jolt/Physics/Body/MotionProperties.cpp).

A millimetre-unit import cleared the fallback but failed the complete installed
inverse-tensor check because principal-axis quaternion roundoff produced unwanted
off-diagonal components in the strongly anisotropic tensor. It stopped before an
update. No numerical result from that attempt was accepted or tuned.

The final setup uses original metre units and the stock public `SetInverseInertia`
API with the requested diagonal and identity principal axes, before adding bodies.
No engine code or threshold was modified. Every installed inverse mass and complete
local inverse tensor is checked: maximum relative error 2.219e−8, below the fixed
1e−5 float-storage check. This is an import check, not a physical-tolerance change.
The same binary's constructor-only RED fixture rejects the earlier substitution
before producing a proposal; the explicit-installation GREEN import passes.
[Pinned setter](https://github.com/jrouwe/JoltPhysics/blob/5830c342b90fa087f118aa0f086d541a4950b1d9/Jolt/Physics/Body/MotionProperties.h).

## Matched-inertia result

Two independently constructed cold steps from the identical checkpoint:

| Measure | First | Repeat | Gate/result |
| --- | ---: | ---: | --- |
| Stock update | 0.508 ms | 0.379 ms | Host kernel only |
| Mesh/chain setup | 1.580 ms | 1.308 ms | Excludes arena allocation |
| Maximum reconstructed strain | 1.3404265% | identical | FAIL, limit 0.5% |
| Total material error | 0.307606 mm | identical | PASS, limit 0.5 mm |
| Original-mesh segment clearance | 3.564685 mm | identical | PASS, minimum 3.45 mm |
| Actual unaveraged capsule clearance | 3.564692 mm | identical | PASS |
| Maximum joint endpoint gap | 38.72963 µm | identical | FAIL, faithful-import screen 10 nm |
| Passage/topology refresh | valid | identical | PASS |
| Reconstructed wood/self sweeps | valid | identical | PASS |
| Original metrics | 1.696 ms | 1.619 ms | Not a device measurement |
| Diagnostic sweep verifier | 13.005 ms | 12.934 ms | Includes wrapper allocation overhead |

The recorded update + reconstructed metrics + diagnostic sweep verification is
15.21 ms on the first run. The sweep wrapper unnecessarily reconstructed the whole
checkpoint dictionary per link to read one scalar, unlike production's direct
scalar access. Consequently this is not an isolated sweep-kernel measurement or a
lower bound on an optimized complete step. The committed wrapper hoists that read.
A subsequent verifier-only check on the same retained states gave 3.568/3.537 ms
for the hoisted sweep wrapper and 1.659/1.614 ms for metrics, with all physical
outputs bit-identical. It retains a separate output and does not rerun the stock
engine or replace the original samples. The fast stock update does not establish
the complete 4 ms device target. No p95 or iPhone measurement exists.

Full stock link transforms, linear/angular velocities, actual capsule endpoints,
and reconstructed checkpoint match exactly between the two cold runs. An additional
instrumentation-only pair counted 55 wood contact manifolds and no rope manifolds;
it preserved all those states exactly. Its slower 1.011/0.687 ms times are reported
separately, not substituted into the uninstrumented timing. Added manifolds do not
establish nonzero load-supporting impulses: the board's first-step vertical velocity
matches its free-fall predictor. This is not a loaded-settling or bearing proof.

Reconstruction averages the two incident link endpoints and restores mathematical
support endpoints, so its strain is not a measurement of a perfectly connected
capsule chain. The 38.73 µm gap is exposed separately; averaging cannot hide it.
The reconstructed motion sweeps do not certify every actual rotating stock capsule.
Nor does LinearCast certify the externally prescribed board rotation. Original
KKT/merit/convergence, full capsule CCD, load bearing, repeated transitions and
catalog/device gates remain unproven. No trajectory or app recording was produced
from this rejected state, and seated cords remain available.

## Evidence, ownership and conclusion

Retained roots:

- `.context/strong-owl-live-physics-jolt-chain/`: original registered plan, setup
  failures, invalid first result, unit/direct-installation continuation decisions.
- `.context/strong-owl-live-physics-stock-chain-reproduction/`: invalid-inertia
  reproduction, source snapshots and resource manifest.
- `.context/strong-owl-live-physics-stock-chain-matched-mm/`: rejected import and
  installed-tensor diagnostic, no successful update.
- `.context/strong-owl-live-physics-stock-chain-exact-inertia/`: valid installed
  properties, cold result, original verifier, counter identity check and snapshots.

The new `run_stock_chain_screen.sh` driver rebuilds pinned sources in a fresh owned
directory, validates input hashes, retains RED/GREEN checks and output, and uses
the existing reserved-process-group lifecycle. Source/evidence hashes and exact
resource-absence verification are retained with this audit. No simulator or HTTP
server was started and no shared or historical process was targeted.

The registered default point-joint screen is closed without tuning iteration
counts or slop. Standard machinery demonstrably handles this small discrete
collision workload cheaply, but this configuration fails continuity and strain.
A structural articulated-chain successor can test elimination of internal joint
drift, while retaining the original supports, mesh and independent validation.
That is a next hypothesis, not an implemented or accepted replacement here.

The articulated successor is now implemented and measured in
[the stock Bullet audit](2026-10-02-live-stock-articulated-chain.md). It eliminates
internal joint drift, but its contact-enabled default step still fails closing
support continuity and runtime. Neither stock configuration is adopted.
