# Shared cord constraints for board rotation

Status: approved by the user on 2026-10-01. The user approved the goal of making
cord support a shared physical rule and then approved this written design.
Implementation planning follows; implementation has not started.

## Intent and observable result

The user wants a corded board to tilt around its cord support when rotated
about X, including Clavellium and the other suspended models. The result must
come from the same rules for every board, rather than a Clavellium-specific
pivot correction.

Keep the selected board orientation as an explicit input. Solve the board's
translation and the continuous cord together so fixed overhead supports,
rope length, actual attachments, contact, and threading govern its position.
The apparent rotation axis follows the support arrangement. A threaded cord
can slide through a passage, so its mouth center is not a fixed hinge.

An attachment is fixed in board coordinates. It need not be fixed in world
coordinates: flexible cords permit the suspended board to move. The user's
request for steady cord points is exact for an ideal fixture that fixes those
points; ordinary suspended cords instead constrain them through tension and
contact. Do not manufacture a hinge to make every possible setup look alike.

## Existing implementation and boundary

At `3e97a226`, `RopeSimulationState` has prescribed orientation and one scalar
translation, `boardHeight`. `RopeDynamicsSolver.ConstraintRow` has a scalar
`boardGradient`; the banded system has one board border variable. Contact
and attachment corrections can move the board only vertically.

The recent pivot correction averages referenced attachment and portal centers.
Seed construction, collision queries, frame publication, rendering, and
framing share that transform. This improves the selected presentation, but
averaging passage centers does not derive a physical bearing or support axis.

Only Clavellium has a bundled `assets/primary.physics.json` in this checkout.
The other represented cords use validated static suspension metadata and
cached or static routes. Those routes cannot establish live constraint
behavior. The September 29 design already requires one shared solver and
catalog migration, but explicitly limits board translation to vertical motion.
This proposal supersedes that limitation and the averaged-pivot convention
for the live solver. The other evidence, fit, collision, ODR, lifecycle, and
performance requirements remain applicable.

## Approach and alternatives

Use three translational degrees of freedom with prescribed orientation.
This directly serves controlled tilt and existing grip selection, extends
the current coupled solver, and requires no invented rotational inertia or
grip torque. It is a constrained display simulation, not a complete model of
a freely tumbling board.

A geometric pivot inferred for every suspension is cheaper, but fixes a
bearing that must be able to slide and cannot handle asymmetric or multiple
supports consistently. A six-degree-of-freedom rigid body with a rotational
controller would also permit free tumbling, but adds inertia, torque, and
controller assumptions that the requested controlled rotation does not need.
Neither alternative is selected.

## Shared simulation contract

Replace board height and vertical velocity with `boardTranslation` and
`boardLinearVelocity`, both three-component vectors in the solver world.
Use one rigid transform everywhere:

```
worldPoint(local) = orientation.act(local) + boardTranslation
boardPoint(world) = orientation.inverse.act(world - boardTranslation)
```

There is no physical `rotationPivot` state. Changing the local coordinate
origin must change only the translation representation, not the resulting
world-space board or cord. A centroid may be used for numerical conditioning
or camera bounds; it must not constrain movement.

Predict translation using gravity and the existing explicitly estimated
damping. Continue bounded orientation interpolation toward the selected tilt.
Each accepted step jointly corrects the three translation components and the
free rope particles. Fixed support particles remain exact solver-world
positions; attachment particles are always derived from the board transform.
Portal crossings remain sliding material coordinates maintained by topology
refresh. Hidden links count toward the same immutable continuous rope length.

Generalize the board gradient in every constraint row to a vector. The board
mass block is `mass * identity(3)`; the three board variables remain a small
border on the existing banded particle system. Update both the primary contact
solve and its full working-set fallback, including tension curvature, merit,
inactive-contact checks, and line search. Contact gradients must include
relative motion between the rope and wood; attachment gradients must include
the body's translation in all three directions.

Retain the feature branch's relative-link correction guard. Attached endpoints
use the proposed vector board correction, supports use zero, and free particles
use their solved corrections. Common translation must not be constrained by an
unrelated shortest link. Swept collision includes the full board translation
and prescribed rotation relative to the rope. Revalidate length, topology,
finite-radius clearance, and cord contact after corrections.

An infeasible target orientation must never publish stretched or penetrating
geometry. Retain the last accepted frame during bounded retries; after those
retries fail, use the existing explicit live-suspension failure path. Do not
teleport, change rope length, or fall back to a decorative cord for an enabled
physics profile.

## Initialization, frames, and rendering

The current height-bracketed route can supply an initial candidate where it
is feasible. It is not the final universal placement solve. Admission must
allow three-dimensional body translation and require a fully validated chain;
asymmetric fixtures must not be rejected solely because their ropes cannot
share the old scalar seed height. Unsupported exterior winding still needs an
evidence-backed graph adapter rather than a guessed portal.

Frames publish the accepted translation directly. RealityKit composes the
instance base transform with that same physical transform. Tube particles,
wood contact queries, picking geometry, and camera framing use the accepted
state. Replace scalar height history with vector displacement history so
settling cannot ignore lateral drift. Keep generation cancellation, bounded
display work, pause/resume, independent paired instances, and Reduce Motion.

Continue requiring instance placements to preserve the solver's gravity
direction. Arbitrarily tilted instance worlds need an explicit gravity adapter
before admission; removing the current validation check is not that adapter.

The graph schema already distinguishes support, attachment, and passage nodes,
so this core change does not need a new manufacturer pivot field or a package
schema revision. Any graph extensions needed by later exterior adapters must
update Swift and Python validation together.

## Catalog adoption and scope

This specification covers the shared translation solver and its Clavellium
integration, with generic attachment and threaded fixtures. Catalog adoption
is the next workstream, required before calling the behavior universal in the
shipping catalog. Discover packages and current suspension evidence at
execution time; the September 29 inventory is a checklist, not current proof.

Migrate each supported attachment, internal-loop, and exterior-wrap setup to
the same graph and solver. Test curved Mini Bar channels and Helium Mobile,
then exterior routes and paired instances. Do not infer hidden bores from
legacy `pairedLeadCord` labels, or reclassify Captain Fingerfood's evidenced
upper-lip-to-recess route as a through-hole. Unknown dimensions remain labeled
display estimates; confirmed Clavellium and Mini Bar cord diameter stays 7 mm.

For each package, establish a hash-bound closed collision solid, its evidenced
connection graph, feasible rest length and radius, and accepted canonical pose
transitions before enabling it. Retain legacy rendering while a package has
no enabled physics descriptor. A broken enabled descriptor fails explicitly.
Record evidence, geometry, numerical, and performance gaps per package; a
shared engine test does not count as a migrated board.

No hold geometry, training content, model materials, or USDZ cord baking is
part of the core change. If a later migration needs CAD geometry changes,
follow direct authoring and show front/side/top before-and-after previews.

## Acceptance and completion evidence

Write failing regressions before replacing the scalar solver. In particular:

- A support arrangement requiring lateral translation under X tilt must settle
  with exact fixed supports and board-local attachments; the old scalar-height
  implementation must fail this fixture.
- Single and paired attachment arrangements, an asymmetric arrangement, and
  multiple continuous threaded loops use the same solver. A symmetric pair of
  taut vertical leads verifies that the settled attachment axis stays steady
  under X tilt without applying that rule to sliding portals or pinning the
  attachment particles in world coordinates.
- Changing the model coordinate origin produces the same accepted world-space
  result within the existing 0.2 mm determinism tolerance. This distinguishes
  constraint-driven support from an origin-dependent pivot shortcut.
- Clavellium X tilt, reversal, and return preserve the central channel and exact
  supports. Bearing can move on the passage surface. Do not retain the old
  assertion that the averaged mouth center must stay still.
- Both coupled-solve paths, relative correction bounds, swept contact, and
  lateral settling metrics have meaningful regression coverage.

Retain the September 29 engineering gates: total rope-length error at most
0.5 mm, local strain at most 0.5%, finite-radius segment clearance at least
radius minus 0.05 mm, convergence within five simulated seconds with speed
below 1 mm/s and displacement below 0.1 mm over the final half-second, and
half-step contact/endpoint differences below 0.2 mm. Preserve self/inter-cord
contact and topology checks throughout accepted motion, not only at rest.

Run the relevant pure Swift and iOS suites, package validation, and current
source native review. Show ordered X-rotation frames and front/side/top views
for Clavellium; check selected contacts, non-pickable cords, clear/reselect,
paired independence, pause/resume, framing, and Reduce Motion. Report build
configuration with timings. A physical iPhone measurement is required before
claiming the existing under-4-ms p95/60-fps target; host or optimized simulator
timings cannot establish it.

Core completion means the generic fixtures and Clavellium pass these checks.
Full user-goal completion additionally requires every represented cord setup
to be migrated and validated, with no unsupported packages silently counted.
This document alone establishes neither outcome.

## Repository references

- [Original live-cord design](2026-09-29-live-hangboard-cords-design.md)
- [Suspension and ODR contract](../../3D_SUSPENSION_AND_ODR.md)
- [CAD cord authoring](../../HANGBOARD_CORD_AUTHORING.md)
- [Current contact-initialization limitations](../../source-audits/2026-09-29-live-cord-contact-initialization.md)
- [Production relative correction guard](../../source-audits/2026-09-30-live-relative-trust.md)
