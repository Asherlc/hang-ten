# Accepted solver cost and stock-engine distinction

The instrumentation-only checkpoint passed whole-state bit identity against both
a same-binary unprofiled control and the preceding accepted original output.
No solver or app change follows from this profile. The rejected nonlinear-IP
initialization experiment remains closed.

The retained loaded-Clav step took 57.9457 ms with nested timing and 51.6498 ms
with timing disabled. Both accepted, with identical positions, velocities, board
motion, material, topology, history and tension. There were nine corrections,
21 merit evaluations, nine contact solves and zero full-KKT conditioning fallbacks.
The exclusive buckets sum to the root step clock exactly.

| Measured bucket | Calls | Inclusive ms | Exclusive ms |
|---|---:|---:|---:|
| Original segmentContacts | 10,890 | 35.249 | 22.263 |
| Original ray parity | 20,837 | 13.633 | 13.633 |
| Contact active set and responses | 9 | 8.043 | 8.043 |
| Original global merit | 21 | 23.925 | 0.890 |
| Equality backbone | 9 | 2.757 | 1.558 |
| Banded factorization | 9 | 1.199 | 1.199 |
| Final metrics | 1 | 1.942 | 0.087 |
| Wood swept queries | 210 | 3.464 | 0.442 |

Inclusive times overlap and must not be added. Timing adds 6.296 ms, about 12.2%
of the disabled run, so these numbers identify host cost distribution rather than
an unperturbed speed or a device/frame/p95 result. The existing parity memoization
in the closed triangle-slab/batch line is not a new hypothesis and is not repeated.

The first snapshot setup stopped because a method name matched both the contact
solver and its private Cholesky helper. The second compile failed for a missing
Foundation import in the checkpoint adapter and an implicit-return function whose
body was no longer one expression after instrumentation. Fresh snapshots retained
both failures; explicit scope selection, the import and return syntax fixed setup
before the single registered measurement. No measured configuration was tuned.

The user's off-the-shelf question is justified. Stock rope functionality exists:
[Obi 7.1 surface collisions](https://obi.virtualmethodstudio.com/manual/7.1/surfacecollisions.html)
uses continuous edge surfaces and describes CCD, while its
[collision framework](https://obi.virtualmethodstudio.com/manual/7.1/collisions.html)
provides self/inter-actor collisions and two-way rigidbody coupling. These are
capability descriptions, not evidence that our actual passage geometry, material
and physical gates pass. Its documented one-contact-per-simplex/collider limitation
still needs testing in narrow concave passages. Its
[CPU backend](https://obi.virtualmethodstudio.com/manual/7.1/backends.html) depends
on Unity Burst/jobs; [Obi 7 removed the old native Oni backend](https://obi.virtualmethodstudio.com/manual/7.1/whatsnew.html).
The standard Unity application paths checked here are absent, and no Obi package
was found in the source/package paths inspected. No license, install, engine run
or benchmark has been claimed.

[Jolt's current architecture](https://jrouwe.github.io/JoltPhysics/) documents XPBD
soft bodies, dynamic triangle meshes with supplied mass/inertia and restricted
translation degrees of freedom. It also documents missing soft-body-to-soft-body
collision response and unsupported generic constraints on soft bodies. That is a
setup gap for a direct stock deformable-loop baseline, not evidence against all
Jolt-based rope constructions. A rigid-link model would need a separate, explicit
model-equivalence assessment. Existing Bullet hull/pin/smaller-radius experiments
do not constitute a matched engine rejection.

A stock-engine diagnostic can be tested against original independent physical
checks without claiming it meets the retained exact inertia/KKT/global-merit
certificate. Passing physical checks is useful evidence; failure to expose our
internal certificate is not proof that game rope simulation is inadequate. Any
later app adoption must still satisfy the currently binding gates. The next stock
baseline must preserve mesh, radius, material/rest lengths, masses, initial
velocities, coupled height and sliding passages, and verify the actual swept path;
no hidden warm-up, extra pins, hull or radius substitution is a matched test.

Evidence root `.context/strong-owl-live-physics-accepted-profile`, current-source
snapshot instrumentation only. Paired summary binds outputs/source hashes and
verifies all exact newly owned command groups/drivers absent. No simulator,
HTTP server, tunnel, deployment or new screen recording was created.
