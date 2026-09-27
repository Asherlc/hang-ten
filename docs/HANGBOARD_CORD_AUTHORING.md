# Authoring cords on CAD hangboards

This is the reusable authoring contract learned from the Lattice Mini Bar
migration. Read the [suspension and ODR guide](3D_SUSPENSION_AND_ODR.md) for
package delivery and the [Mini Bar source audit](source-audits/2026-09-27-lattice-mini-bar-cord-passages-correction.md)
for the product-specific evidence. The approved [Lattice end view](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-2.jpg)
and [loaded view](https://latticetraining.com/app/uploads/2021/05/Mini-Bar-Web-1.jpg)
were decisive: the lower curve belongs to the same loop as the two rising
legs. The user confirmed that two mouths at each end connect inside the wood.

## Establish the threading before choosing a solver

Draw a route graph from evidence. Name every visible endpoint, bore mouth,
hidden connection, free leg, and overhead support. Decide which parts are
one continuous piece of cord. Do not infer an internal channel from a dark
spot in a photo; obtain another view or an owner correction. Retain exact
manufacturer images and record which observations are sourced and which
dimensions are display estimates.

For the Mini Bar there are **two separate loops, one at each end**. Each loop
is one continuous cord: overhead support → first exterior leg → first mouth →
hidden connected U channel → second mouth → second exterior leg → overhead
support. The channel is a void in the FreeCAD wood solid. Its centerline is
not drawn as a visible cord. The material-free USDZ contains the board only.

The preceding solid-bar and exterior-wrap interpretations were wrong because
they lacked the observed mouths and the connected passage. A plausible
silhouette is insufficient evidence for a cord route. Compare a loaded
manufacturer side/end photo with the same CAD pose and approximate camera;
inspect the mouths, both legs, lower bearing, and occlusion, then rotate the
model through every supported grip. The Mini Bar matched-photo review is
described in its source audit.

## What the shipped solver does

`suspension.json` stores two point mouths per loop, their body node, branch
pairing, one overhead anchor, estimated radius and rest length, canonical
board poses, a positive clearance, and `internalLoop.windingByPassageID`.
The passage IDs and pair order are part of the topology. The sidecar is bound
to the model descriptor's `modelSHA256` and covered by the delivery lock;
`board.json` is generated from the FCStd manifest plus this sidecar.

At runtime, `BoardModelRealityScene.wrapSection()` reads vertices from the
imported USDZ body node and projects them into the board's Y/Z section. The
`MeshInternalLoopSolver` takes that section's convex hull and offsets it by
cord radius plus clearance. For the selected board rotation, it transforms
the fixed world anchor into board space, finds the two exterior tangent
sides, then follows the **authored winding direction** from each tangent to
its mouth. The second route is reversed so the branch runs from the support
through the first mouth and back from the second mouth to the support. The
existing suspension solver then samples the visible spans and creates
transient, non-pickable RealityKit geometry. Each pose is solved from the
loaded mesh; there is no list of per-pose contact coordinates in the package.

This is deterministic geometric contact, **not a live physics simulation**.
The current runtime does not settle a deformable rope against arbitrary
triangles with gravity, friction, or changing load. RealityKit renders the
result; the app code computes the path. An offline Bullet experiment tried
to settle an earlier solid-bar surrogate and failed exact-mesh acceptance in
all eight cases. That experiment did not contain the now-confirmed channel,
so it cannot establish whether a correctly constrained physical simulation
would work. See [the experiment and its measured limits](../Tools/HangboardRopePrototype/README.md).

Live simulation remains possible engineering work. RealityKit provides
[rigid-body physics](https://developer.apple.com/documentation/realitykit/physics-simulations-and-motion),
[joints](https://developer.apple.com/documentation/realitykit/physics-joints-and-pins),
and [cloth simulation](https://developer.apple.com/documentation/realitykit/physics-cloth-simulation),
but these APIs do not infer a threaded, continuous rope through hidden
channels from mouth and anchor positions. A rope implementation would still
need the route graph, attachment and bore constraints, a collision shape
faithful at the mouths and grip recesses, a stable tension/length model, and
repeatable settling across all poses. Test exact CAD-solid clearance and
motion before replacing the deterministic renderer; the old surrogate's
failure is evidence about that experiment, not a proof against simulation.

Mouth and anchor coordinates **do not uniquely determine a route**. Between
one mouth and an external support, cord can travel around either side of the
section. The winding choice records how the physical cord was threaded. It
is a discrete topology input, not a manually placed contact point. The
solver can calculate bearing only after that ambiguity is resolved.

## When to reuse `internalLoop`

Use the current method only when all of these hold:

1. Source evidence supports two connected mouths per loop and a continuous
   cord returning to the same support.
2. The CAD source contains the connected void, and mouth coordinates refer
   to that void in the descriptor/importer coordinate basis.
3. The relevant body has a nearly constant, convex Y/Z section along X, so
   projecting all body vertices to one section and using its convex hull is
   a faithful exterior envelope near every mouth.
4. The model has two branches, four distinct point mouths, and one winding
   choice for each mouth. Each branch's `passageIDs` lists its paired mouths
   in traversal order.

For a tapered, twisted, strongly concave, or locally different section,
the current whole-body projected hull may float above a recess or mask a
collision. For an external wrap without connected internal mouths, use the
appropriate exterior topology; do not label it `internalLoop`. For a
different connection graph or moving anchor, extend the schema and solver
with evidence and tests. No solver choice can recover hidden threading from
the mesh alone.

## Authoring sequence for another board

1. Inspect the exact product revision from several manufacturer views and
   record the route graph and unknowns in a source audit. Confirm whether
   each cord is one piece, where it enters and exits, and whether any segment
   is hidden in the board. Request owner input for genuinely occluded facts.
2. Author the body and connected channel in the native FCStd. Confirm the
   shape recomputes, the mouths open at the declared coordinates, and the
   exported USDZ has neither cord nor material bindings. Record estimated
   diameters and offsets as estimates.
3. Put suspension in the adjacent `suspension.json` for a CAD package. Bind
   all mouths to the body node, pair each loop, supply the overhead anchor,
   and choose each winding from the evidence. Keep the route free of
   pose-specific control points. Generate `board.json` through the normal
   CAD package process; never commit that generated file.
4. Validate the schema, model SHA, delivery lock, package inventory, and
   byte-for-byte CAD rebuild. Add a focused parser and native solver test for
   every pose and a negative test for malformed topology.
5. Measure cord-centerline clearance against the **actual FreeCAD solid**,
   including the segment entering each mouth. A hull-only check cannot prove
   it avoids the wood. Inspect front, side, top, and loaded-photo-matched app
   screenshots for every grip. Check that the cord remains invisible to
   picking and accessibility, that selection and orbit still work, and that
   clearing/reselecting a pose removes/recreates the transient cord.

The Mini Bar's final native check found at least 2.09 mm exterior
centerline-to-wood clearance with a 2 mm estimated rope radius. Those numbers
are specific to its display model; they are not a general rope or safety
specification.
