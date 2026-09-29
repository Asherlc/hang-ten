# Mini Bar rope contact prototype

## Purpose

Find out whether a reusable rope simulation can place the Lattice Mini Bar's
two exterior loops against the actual board surface in all four canonical grip
poses. The cord remains transient geometry outside the FreeCAD source and USDZ.
This phase is a feasibility prototype, not an app renderer replacement.

The current renderer leaves a visible gap. `suspension.json` requests 5 mm of
clearance, and `MeshSectionWrapSolver` offsets a convex section by that amount
plus the cord radius. Its sampled route is then treated as fixed. Reducing the
clearance alone would not test whether physical contact can replace authored
route points for other corded boards.

## Inputs and ownership

- Use the committed Mini Bar USDZ and its descriptor hash as the collision
  source. Extract vertex positions and triangle indices from the mesh, never
  from screenshots. Keep the mesh and descriptor unchanged.
- Use the two approved exterior loop locations and one shared overhead pull
  point from the bundled suspension sidecar. The outside wrap side is a
  topology input; the solver must not guess whether a loop passes through or
  around the board.
- Treat cord radius, length, friction, stiffness, and damping as display
  parameters. Record every tested value and its origin. Do not present these
  parameters as measured Mini Bar specifications.
- Keep generated meshes, logs, measurements, and screenshots beneath the
  workspace-owned `.context/frantic-kiwi/` path. The prototype must not modify
  the FCStd, USDZ, descriptor, sidecar, or app renderer.

## Prototype architecture

1. A mesh adapter reads the validated Mini Bar body triangles in model
   coordinates and passes them to a Bullet collision body. Contact-test the
   same imported triangles that RealityKit renders, including their importer
   transforms.
2. A rope setup creates one particle chain per approved exterior loop. Both
   ends connect to the shared overhead pull point. The chain starts on the
   approved outside wrap side, with its two strand locations guiding the route
   near each end. This starting topology prevents a valid collision solver from
   settling on the wrong side of the board. The intermediate contact points
   come from simulation, not metadata or a baked curve.
3. Hold the board at each canonical grip pose and settle the ropes against its
   collision mesh under gravity and tension. Run the same setup from a fresh
   state for every pose. Capture settled particle positions and convergence
   data. Stop with an explicit failure if the rope crosses the board, slips
   off the approved wrap, or fails to settle.
4. Produce transient tube geometry from the settled centerlines for visual
   review. A RealityKit integration is a later decision; the prototype may
   render its own review images outside the app.

Bullet's soft-body rope and rigid-body contact examples make it a suitable
first engine to test. The adapter boundary keeps the board evidence and loop
metadata independent of Bullet, so a different solver can replace it if
contact quality or stability is inadequate. RealityKit's built-in rigid-body
joints do not supply a continuous rope. Its newer deformable cloth API is not
available to this app's iOS 18 deployment target.

## Measurements and acceptance

For each of the four Mini Bar poses, save front, oblique, and end-on review
images, together with a signed distance measurement from every simulated rope
segment to the board triangles. At the underside region where a taut exterior
loop should touch, the rendered tube surface should be within 1 mm of the
board, with no penetration greater than 0.5 mm. The loop must remain on the
approved exterior side, remain separate from the other loop, and converge at
the specified pull point. Record simulation time and iteration count.

Run two length conditions: the current 0.75 m per-loop display estimate and a
taut length derived from the fixed anchor, wrap topology, cord radius, and mesh.
Do not silently replace the published metadata. If the existing length is too
slack for contact with a fixed board pose, report that constraint explicitly.
The prototype succeeds only if contact is repeatable across fresh runs and all
four poses without a pose-specific hand-drawn path. A visual improvement alone
is insufficient if the measured cord penetrates the board.

## Decision after the prototype

- If Bullet meets the contact and stability checks, design a reusable runtime
  adapter that reads board mesh, exterior topology, pull point, and display
  parameters from package metadata, then supplies transient, non-pickable cord
  geometry to RealityKit. Address Android reuse at that integration stage.
- If it fails, retain the current shipping renderer and report which constraint
  failed. Evaluate a focused position-based rope solver with mesh-distance
  contact rather than tuning per-pose coordinates in `suspension.json`.

The prototype does not claim that specifying only a pull point and two passage
points determines a unique physical result. Wrap topology and cord length or
tension remain necessary constraints; contact locations do not.

## Sources

- [Apple RealityKit collision detection](https://developer.apple.com/documentation/realitykit/physics-collision-detection)
- [Apple RealityKit physics joints](https://developer.apple.com/documentation/realitykit/physics-joints-and-pins)
- [Apple RealityKit cloth simulation](https://developer.apple.com/documentation/realitykit/physics-cloth-simulation)
- [Bullet soft-body rope and attachment examples](https://github.com/bulletphysics/bullet3/blob/master/examples/SoftDemo/SoftDemo.cpp)
- [Bullet license](https://github.com/bulletphysics/bullet3/blob/master/LICENSE.txt)
