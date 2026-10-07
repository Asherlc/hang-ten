# Native CAD geometry authoring precautions

Use [the CAD guide](../Tools/HangboardCAD/README.md) for the source contract,
metadata editors, pinned compiler, and review commands. This guide covers
construction failures that compilation or a static render alone may miss.
[AGENTS.md](../AGENTS.md) governs evidence and geometry authoring.

## Evidence and profiles

Review primary manufacturer images, dimensions, depth guides, and physical
feature counts before measuring a display reference. A logical contact inventory
need not equal the number of physical cavities: several grips can share one
trough. Record source conflicts and distinguish published facts from display
estimates. A closer fit to an old mesh does not settle a disagreement with
primary evidence.

An approved 3D display mesh can supply an ordered cross-section boundary for a
deliberately authored native Sketcher profile. Check that the section is
constant along the intended extrusion axis before choosing a pad. Use native
lines, arcs, or Béziers where justified, constrain their dimensions, and record
approximation error. Do not infer profiles or primitives from pixels, or use
image-driven detection, alignment, vectorization, cropping, or automatic path
simplification.

A prismatic silhouette has the same side-wall normal throughout its depth. If
primary evidence shows a rounded crest or a changing section, author that
sectional geometry explicitly. A small perimeter fillet does not change the
middle of a flat extrusion. Choose round-overs from evidence rather than a
universal radius or a brightness metric.

## Live sketches and contact bindings

Bind contacts to the native geometry that creates their surface. For a swept
profile, use the profile's own sketch-edge runs with expressions for their
extrusion length. Resolve sketch sub-elements by their actual geometry:
`Edge<n>` follows `Shape.Edges` ordering, not necessarily geometry index `n-1`.

Fillet-face names can become unstable after an edit. A binder that silently
falls back to the whole solid is invalid. Use a stable native feature selection
or a geometric split, with the same split applied to the body and region. Test
an edit that moves the affected region; an unrelated dimension edit does not
prove the binding survives.

For Sketcher cubic Béziers, exposing internal geometry already adds pole weight
constraints. An extra `Weight` can be redundant. A fully constrained sketch
also does not prove G1 continuity: check one-sided endpoint tangents and
constrain handles explicitly where necessary. Keep Bézier handle lengths
positive at kinks.

## Contact boundaries and orientation

A region normally exports its own native surface. A pocket contact must include
the intended walls and floor without an opening cap; an extruded band is an
open surface. Keep the closed cutting tool separate. Contact and attachment
boundaries must exactly match the area removed from the body partition.

Split large planar body faces at hold boundaries. Centroid classification on a
coarse face can remove an oversized triangle that the region cannot fill. Keep
`Refine = False` where authored coplanar boundaries must survive pads, pockets,
or cuts. Avoid coincident surface overlays. If a region extends outside the
body, clip that construction deliberately; a coincident `Part::Common(shell,
body)` can instead produce fragments.

Extruded normals follow stored edge direction. Mirroring or clipping a B-spline
shell can change its orientation. Review the final region's outward normals and
use live `Part::Reverse` or corrected section order when needed. A static
reversed Shape does not provide edit propagation. Intentional internal seam
faces of a solid split are distinct from outward contact faces.

Set `HangTenCurvedRegionPartition` for curved contact regions and check that the
compiled body retains no duplicated contact coverage. A contact using
`HangTenUseBodyTriangles` still needs a valid native face binder and complete
partition/depth checks. Use the CAD guide's
[surface-normal options](../Tools/HangboardCAD/README.md#surface-normals) when
crease averaging bands a planar face beside a tangent fillet.

## OCCT construction checks

- Keep loft sections in matching start order and direction; independently
  ordered sections can twist. A uniform inward offset can collapse a corner
  whose radius is smaller than the inset. Author corresponding opening and
  floor sections deliberately.
- Do not create non-planar quadrilateral faces. Use an appropriate native
  surface or explicitly planar faces where the construction requires them.
- Use `shape.check(True)` as well as `isValid()` for changed booleans. Extended
  checks can expose inflated edge tolerances or slivers that `isValid()` misses.
- Keep cut/common tools on matching spans when they partition a replacement
  region. Limit cutting planes to the intended area and keep them off tangencies
  with unrelated curved surfaces.
- Diagnose failed fillets edge by edge. Separate front/back operations can
  avoid an invalid combined result; neither fillets nor chamfers are reliable
  at every tangent or concave kink. Keep changes supported by the evidence.
- Small toroidal and B-spline fillets can tessellate densely regardless of a
  coarser deflection. Inspect triangle counts and exported size before delivery.
- `Shape.BoundBox` can be loose around fillets and B-splines. Use
  `optimalBoundingBox()` for native envelope checks where exact bounds matter.

## Depth and review

Use the source-backed grip dimensions and the compiler's axis or lip/floor
witness contract. A contact's whole extent may include a tilted floor, stepped
mouth, or neighboring surface and therefore exceed the intended grip depth.
Inspect the actual lip/floor pair before changing geometry to satisfy a gate.
Keep configured depths and published depth-range endpoints explicitly audited.

Reopen and recompute the saved source, then exercise a relevant native dimension
edit and verify contact propagation, body-surface membership, node inventory,
and bounds. Build with the pinned producer; a skipped native integration test
is not evidence of these checks.

Compare front, side, and top previews with an export from the unchanged prior
committed source, present the images, and review selected holds in the app.
Normal shading helps distinguish reversed faces from holes, but a lit patch or
sampled distance alone cannot establish correct geometry. Keep primary evidence
beside the comparison. Shipping meshes remain unbound, with no materials or
textures.
