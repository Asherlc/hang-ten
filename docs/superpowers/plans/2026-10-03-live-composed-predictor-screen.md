# Composed-predictor 120 Hz screen (CLOSED: accuracy failure)

The authorized unchanged-integrator 120 Hz screen is CLOSED. Its first height
error is 123.756 µm; 123.755 µm is explained by one coarse versus two fine gravity
predictions. This proposal is a different numerical formulation, authorized by the user on2026-10-03 to change the predictor and velocity reconstruction. It does not reopen
that screen, change a failed result, or alter physical limits.

For h=1/240 and D=exp(-18h), construct the free target by composing the existing
fine predictor twice: v1=D(v0+g*h), v2=D(v1+g*h), xT=x0+h*v1+h*v2.
Run one coupled mass-metric correction at total duration2h. If its final correction
is d=x-xT, reconstruct free-particle and board endpoint velocities as
v=v2+((1+D)/(2+D))*d/h, rather than the coarse secant. This relation exactly matches
two fine steps when their constraint accelerations are constant; it is an
approximation when contacts or tensions change. The scalar fixtures verify that
algebra, with neither rope integration nor a speed claim.

Fine-step impulses d1=h²*a1,d2=h²*a2 give total response
(1+D)*d1+d2. With a1=a2 it becomes (2+D)*h²*a. The proposed curvature-tension carry
scale must therefore use effective response time-square h²*(2+D), divided by the
prior accepted state's response time-square, rather than silently using4h². This
is a derived consistency choice, fixed before testing, not a fitted constant.
Persist the effective response-square S in every candidate checkpoint. Before
restoring into an original240Hz strict reference, convert curvature tension to
h² units (multiply by h²/S) and set its stored duration to h; do not let the
original reference silently apply1/4 from a coarse stored duration. Validate
this adapter at the original rate and preserve all other persisted state.

A midpoint orientation is the original first fine slerp, then apply the original
second fine slerp for the final orientation. Supports stay fixed. Attachments stay
geometrically driven; their endpoint velocity uses final attachment worldPoint
minus midpoint worldPoint, divided by h. Midpoint board height uses its first free
prediction plus final board correction/(2+D), under the same constant-response
approximation. Material particles remain unchanged and no midpoint guide is pinned.
The inferred midpoint is used only for endpoint velocity reconstruction; it is
not accepted, rendered or claimed as a solved fine-step state. Original coarse
old-to-final CCD retains its existing linear-segment/rotation-deviation path
interpretation. It does not certify two reconstructed fine trajectories.

All mass, fixed lengths, diameter, coupled board height, original full triangle
rows, sliding passages, global merit/trust, caps, whole-mesh material metrics,
whole-link CCD/rollback and settling checks remain. Turning retains the authorized
50 µm full-correction stop; arrival uses 0.001*h/C=6.328088 µm, where
C=(1+D)/(2+D), so its reconstructed endpoint-velocity correction is below1 mm/s.
Arrival still requires an untruncated full step and the existing strain stop.
No Armijo or geometric cache is combined with this screen. No product source or
seated fallback changes. This is native-only until every numerical/speed gate passes.

First checkpoint: same prepared seed, one composed step versus two original240Hz
steps. Require original-mesh/material acceptance, zero cap/retry and pose<=50µm.
Stop on first failure. If it passes, run fixed20 composed steps against independent
fine control and strict same-input paired references, then fixed270 composed versus
540 fine turn/return steps. Require every comparison<=50µm, all physical/settling
checks, strict continuation at first settle, no caps/retries. Report velocity
errors and active-contact differences; do not infer accuracy from free fixtures.

Performance gates stay p95 complete step<8ms, total engine time<simulated2.25s,
then actual simulator normal-speed recording and continuous frame checks. Any
accuracy/cost failure closes this new screen with no formula/tolerance tuning,
rate fallback or video adoption. Count all correction, verification, CCD and
initialization work. The changing-force velocity defect h*(a1-a2)/(2+D) is the
principal known risk; acceleration of a contact impulse can violate50µm even
when the free predictor matches exactly.

The user subsequently authorized all isolated experiments; physical limits and
required validation remain fixed. No redundant experiment permission is needed.
Native preflight at240Hz must preserve20 complete persisted checkpoints and prior
control decisions before the120Hz screen starts. Curvature tension and carried
contact multiplier hints are both converted consistently for strict references.

Result: first comparison24.403µm; second173.901µm >50µm. Original-mesh physical
gates pass, caps/retries0. Closed without trajectory/simulator/adoption. See
docs/source-audits/2026-10-03-live-composed-predictor-screen.md.
