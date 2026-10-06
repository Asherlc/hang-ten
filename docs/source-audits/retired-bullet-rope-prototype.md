# Retired Mini Bar Bullet rope experiment

This retains the findings of the 2026-09-27 offline Bullet experiment. The
prototype code, build recipe, tests, and generated USDZ fixture were retired
when runtime artifacts became source-only build outputs. They remain in Git
history at commit `769817bcc`.

The experiment used an earlier Lattice Mini Bar display asset with no local
holes and pinned inferred exterior guide points. The current native CAD body
has two connected channels, one per end, and a different model hash. These
results concern a **solid-bar surrogate**. They do not establish that Bullet
would fail on the actual corrected board, and they did not authorize replacing
the product's cord renderer. Current topology and clearance requirements are
in [the native CAD cord guide](../HANGBOARD_CORD_AUTHORING.md).

## Retained input provenance

- Descriptor and suspension fixture: historical exterior-loop revision from
  commit `f559563f7`.
- Matching historical USDZ: 32,354 bytes, SHA-256
  `5f6744d3aeede10cc2b3c5f6f9dc19df1bb985c94991192ec8f2044c32932c46`.
- Body triangles: the `mini_bar_body` mesh with its USD importer transform
  applied, 592 vertices and 584 triangles, in metres.
- Cord inputs: two sidecar passage pairs, 2 mm radius, a 0.75 m original
  length estimate per loop, a shared bounds-relative display anchor, and four
  canonical poses. `wrap_side=opposite-anchor` recorded the selected winding;
  no intermediate contact coordinates were specified.
- Solver: official [Bullet Physics 3.25](https://github.com/bulletphysics/bullet3/tree/3.25),
  commit `2c204c49e56ed15ec5fcfa71d199ab6d6570b3f5`, zlib license.
  JSON parser: [nlohmann/json 3.12.0](https://github.com/nlohmann/json/releases/tag/v3.12.0),
  single-header SHA-256
  `aaf127c04cb31c406e5b04a63f1ae89369fccde6d8fa7cdda1ed4f32dfc5de63`.

## Method and limits

The board was rigid. Rope-chain seed nodes were no more than 3 mm apart, with
the overhead point and two guide points pinned. Gravity was `(0,-9.81,0)` m/s².
The solver used 1 mm sparse signed-distance voxels, a 0.25 mm added collision
margin around the 2 mm cord, 30 position iterations, damping `0.08`, friction
`0.5`, 1/240 s steps, and at most 3,000 steps. Convergence required less than
0.02 mm displacement over 120 steps after at least 480 steps.

Bullet's soft-body `SDF_RS` path evaluated signed distance only for convex
collision shapes in [the pinned implementation](https://github.com/bulletphysics/bullet3/blob/3.25/src/BulletSoftBody/btSparseSDF.h).
The prototype therefore collided with a convex hull of the body vertices. That
hull spanned the recessed grip profile, so even a successful hull solve needed
validation against the original triangles. The evaluator used those triangles
for point and segment distances. Open, duplicated boundary edges required a
local nearest-face penetration sign, with reduced reliability deep inside the
shape.

Eight conditions combined four poses with two loop lengths. `original` kept
the 0.75 m sidecar estimate. `taut` used the length of a collision-free seed at
one cord radius from the section; it was an experimental length and was never
written to package metadata. Front, side, and oblique views were generated for
each condition in the original workspace.

## Findings

A synthetic round-bar test passed outside winding, tube contact, separate
loops, fixed guides, and repeatability. All eight surrogate-board conditions
reproduced in an independent second run, but **zero of eight met the exact
mesh acceptance criteria**. Six did not converge within 3,000 steps. The
ergonomic-jug taut condition settled with a maximum expected contact gap of
6.1 mm against a 1 mm limit. The edge-20 taut gap was 11.2 mm and that condition
did not converge. The original 0.75 m estimate was slack relative to the taut
estimate and produced visibly hanging spans.

These outcomes did not support replacing the product cord renderer. A further
experiment would first need the actual passage topology represented, passage
constraints, and a collider capable of handling that geometry. The current
native source and solver evidence govern the shipped board.
