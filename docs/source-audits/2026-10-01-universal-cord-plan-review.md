# Opus review of the cord-support implementation plan

The user requested an Opus review of the implementation plan. A read-only
Paseo advisor using `claude/claude-opus-5-5`, high thinking, reviewed commit
`4777344d0`, its approved spec, the existing Swift solver/tests, and the retained
Clavellium side-view screenshot. No runtime implementation or package changes
were performed for this review.

Opus's verdict was **revise before implementing**. It endorsed prescribed
orientation with three-dimensional translation, the vector constraint
derivatives, and the three-variable board mass block. It identified plan gaps
in initialization, test ownership, and coordinate-reference consistency.

## Verified findings and revisions

- `RopeDynamicsSolverTests.testSlidingPortalGradientsIncludeBoardHeightAndAttachments`
  recomputes the body derivative in the test; it does not exercise private
  production constraint assembly. Task 1 now exposes and tests the actual
  assembly and fallback mapping, including all three translation components.
- `projectInitialization` admits only geometry accepted by the full preflight,
  then corrects contact without a swept-motion check between those iterations.
  The revised plan retains its existing length/strain gate rather than admitting
  arbitrary length error that could carry a rope across a rim during recovery.
- `RopeThreadedSeed.exteriorPath` uses a discrete route search. Finite differences
  of repeatedly rebuilt routes are an expensive and unreliable placement
  derivative. The revised plan uses analytic endpoint-segment gradients with
  bounded exact route rebuilds, a specified minimum-norm placement correction,
  and explicit rejection of unsupported slack initialization.
- A solver-private reference would leave seed and camera transforms inconsistent.
  The shared collision-bounds reference now governs seed candidates, prediction,
  velocity/history, sweep bounds, and framing. It remains a numerical estimate,
  with no fixed hinge constraint. Coordinate-origin tests include a large offset.
- Task 1 now owns the old pivot-assertion replacement, single-attachment and
  tilted-translation fixtures, and native build-for-testing/affected UI tests
  before its commit. Physical motion checks precede the broader seed extension.

## Interpretation and limits

Flat passage bearings can permit sideways movement with no restoring force.
The plan records that expected behavior and forbids artificial centering.
Opus suggested comparing invariant quantities in such cases. The revised plan
retains the approved strict positional checks for equivalent initial conditions,
coordinate-origin changes, and symmetric half-step fixtures, and records any
other positional failure explicitly alongside the invariant metrics. It does
not declare that a differing neutral trajectory has passed the positional gate.

The advisor proposed a tilted fixture with attachments at unequal depths. Two
non-collinear local attachment points cannot both remain world-fixed under an
arbitrary X rotation. The revised fixture instead uses a known feasible tilted
support arrangement; separate symmetric-axis tests verify steady attachments
after settlement. Flexible cords are not converted into world-space pins.

General slack seeding remains a catalog rollout gap. This bounded plan must not
count rejected setups as universal coverage. No tolerances were relaxed, no
device performance was established, and the revised text has not received a
second Opus review.

See the [revised implementation plan](../superpowers/plans/2026-10-01-universal-cord-support.md)
and [approved design](../superpowers/specs/2026-10-01-universal-cord-support-design.md).
The complete advisor response is retained locally in
`.context/opus-review/review.md`.
