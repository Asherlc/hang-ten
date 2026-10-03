# Isolated 120 Hz live-rope screen

Status: proposed; the 1/120 experiment requires explicit user authorization.
The immutable handoff currently requires 1/240 steps. No product adoption,
1/60 fallback, physical tolerance change, interpolation or new solver is included.

Reason: the contact Armijo trajectory passed accuracy but used 4.765 seconds
for 2.25 simulated seconds, with 13.754 ms p95 steps. Its 5% total saving fails
real time. Fewer integration steps are a distinct accuracy/performance tradeoff.

Use the original solver and existing authorized physical convergence experiment,
without Armijo. Keep mass/inertial objective, fixed material, particle resolution,
diameter, coupled board height, sliding passages, complete original triangle
contacts, global merit, trust, caps, CCD and rollback. The arrived correction
limit remains the existing speed-derived 1 mm/s times dt. Physical limits and
the 50 µm reference comparison remain unchanged.

1. Before authorization, validate the new matched-time driver at 1/240: the
   original candidate and independent control must match complete persisted
   physics checkpoints and the retained original correction decisions.
2. If authorized, first20 candidate steps at 1/120, with independently propagated
   1/240 control taking two steps per candidate step. Preserve the same motion
   trajectory and 2.25-second duration. Stop immediately on physical failure,
   pose difference >50 µm, candidate cap/retry, or strict-reference failure.
3. Take strict same-input references from each candidate input in stage1 and
   every10 candidate steps afterward. Each reference takes two original 1/240
   steps; require zero caps/retries and <=50 µm pose difference.
4. Only after stage1 passes, complete fixed270 candidate steps: 120 toward30deg,
   then150 upright. The independent control completes540 steps at matching
   timestamps. Check uncached original-mesh/material metrics every candidate
   step. Preserve elapsed settling times in seconds: each final0.25s tail has
   30 candidate samples. Both must remain settled; confirm each first declared
   settle with two strict original1/240 continuation steps and existing speed/
   history-displacement settling checks.
5. Count all solves, retries and subdivisions in complete engine times. Require
   total engine time below simulated time, p95 candidate step <8 ms and p95
   estimated two-step60Hz engine cost <16.667 ms. The estimate sums separately
   timed steps and is not measured continuous batch/frame latency. This changes the step budget together
   with its frequency; it does not claim the old <4 ms per1/240 gate passed.
   Report max latency. Any failure closes this screen without a1/60 fallback.
6. Only if accuracy and engine speed pass, build the simulator app behind the
   isolated DEBUG option and record actual normal-speed continuous turn/return.
   Measure actual continuous batches and rendering/frame latency; check visible clipping, stability and actual settles
   before any adoption. Keep seated cords and default product behavior available.

All generated outputs and exact owned resource manifests stay under
`.context/strong-owl-live-physics-*`; clean and independently verify owned
processes/simulator/build resources. Push every new commit. Do not touch PR529.
