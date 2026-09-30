# Transgression 2011 / 2013 native CAD provenance — 2026-09-29

Two new packages represent the distinct physical revisions:

- `surfaces-for-climbing-transgression-2011`: original polyester board.
- `surfaces-for-climbing-transgression-2013`: later polyurethane board.

The exact four retained images, source URLs, SHA-256 digests, human evidence-set
approval and field mappings are in
[`source-audits/2026-09-29-transgression-cad`](source-audits/2026-09-29-transgression-cad/README.md).
Both are new catalogue entries. There is no prior committed raster, USDZ or CAD
asset for either package, and therefore no measured reference mesh or before
model. Display estimates are deliberately authored from the approved views;
no pixels were traced, segmented, registered, converted into paths or measured
as a manufacturing drawing.

## Native construction

Each FCStd is self-contained. `Profile` is a fully constrained analytic
Sketcher section with straight lines and true semicircular nose arcs. A native
PartDesign `Pad` extrudes it symmetrically to a 540 mm width. This is a constant
section approximation of the moulded physical shell. It preserves the rear
concavity and upper/lower mounting flanges visible in the original designer's
oblique photograph, rather than filling the rear with a solid wedge.

Each contact uses a native `PartDesign::SubShapeBinder` referencing the two
corresponding live profile edges, followed by a non-solid `Part::Extrusion`.
Every region extrusion has `LengthFwd = Pad.Length`, symmetric extrusion and
direction -X so its normals agree with the outward native solid surface.
The regions consist of each upward shelf and its round front nose; the
inter-row connecting ramps belong to the body. There are nine logical physical
contacts, identically named in both packages: `jug-top` and
`edge-{18,14,12,10,9,8,7,6}`. Every contact is continuous across the full width.
No renderer-side geometry or hidden external Python feature proxy is needed.

The compiler partitions the body surface using those native regions.
`HangTenCurvedRegionPartition` and `HangTenSurfaceNormals` are enabled, with
native tessellation deflection 0.08 mm. The existing source-kind contract value
is `native-parametric-measured-profile`; this legacy enum identifies the native
profile workflow. It does not imply that this new board was measured from a
prior mesh. No material properties, textures or artwork are authored.

Throwaway authoring was performed with
`.context/slim-sheep/author-transgression.py` using pinned FreeCAD 1.1.3 / OCCT
7.8.1. That script is not a build dependency and is intentionally not retained
as supported repository tooling. The board manifests were separately embedded
with `Tools/HangboardCAD/set_board_manifest.py`; no `board.json` is committed.

## Published facts versus estimated dimensions

Only the eight nominal grip depths below are manufacturer/designer product
facts. Their CAD contact extents along native Y exactly equal those depths.
No top-jug depth or overall factual dimensions are placed in metadata.

All other numbers below are explicitly operator-selected display estimates.
The 540 × 400 × 150 mm envelope is shared between revisions to avoid claiming
an unverified physical size difference. It takes secondary historical commerce
measurements as a scale context, not a verified specification. Secondary
polyurethane sources disagree: the reviewer reports 23.5 × 16 × 6 inches,
while a retailer reports 50 × 38 × 15 cm. Exact URLs and conflicts are retained
in the source audit.

Native coordinates are millimetres, X right, Z up, front toward negative Y.
For the 2D section below, `d` means positive forward depth (`Y = -d`). The
width is X = -270 through +270 mm. Section coordinates are `(d, Z)`.

| Contact | Sourced nominal depth | Estimated shelf rear d | Estimated shelf Z | Estimated nose radius, 2011 / 2013 |
| --- | --- | --- | --- | --- |
| jug-top | omitted | 80 | 390 | 14 / 14 |
| edge-18 | 18 | 108 | 325 | 1 / 2 |
| edge-14 | 14 | 94 | 282 | 1 / 2 |
| edge-12 | 12 | 80 | 240 | 1 / 2 |
| edge-10 | 10 | 66 | 199 | 1 / 2 |
| edge-9 | 9 | 52 | 158 | 1 / 2 |
| edge-8 | 8 | 38 | 117 | 1 / 2 |
| edge-7 | 7 | 26 | 78 | 1 / 2 |
| edge-6 | 6 | 16 | 40 | 1 / 2 |

The display-only jug region extends 70 mm in depth. Its top flat spans d80 to
d136 at Z390, and its semicircle reaches d150 at Z376 before ending at
(d136, Z362). These are not a product depth claim. For every smaller edge, the
flat runs from the listed rear d to `rear + nominal depth - radius`. A true
semicircle then reaches `rear + nominal depth`, rounding down by twice its
radius. A straight ramp joins that nose end to the next row's shelf rear.
The eight `Flat_edge_*` sketch constraints drive the flat lengths; total
contact depth is that flat length plus its nose radius.

The rear and flange contour, traversed from the bottom-front point back to
the jug shelf rear, is deliberately authored as these straight segments:

```
(16,0) → (0,0) → (0,48) → (8,48) → (98,348) →
(92,366) → (0,366) → (0,400) → (18,400) → (18,390) → (80,390)
```

The lowest nose connects to `(16,0)`. The rear ramp leaves a continuous open
space behind the middle of the shell. The original oblique supports this
broad concave form; reproducing it on the 2013 board is an explicitly labeled
adaptation because the retained newer photographs do not expose the rear.
The numeric rear wall positions and shell thickness are estimates, not
measured manufacturing dimensions.

The 1 versus 2 mm lip radius is a modest display distinction implementing the
designer's statement that the 2013 edges became somewhat more rounded. Those
exact radii are not published. The top jug is the same on both models because
no retained evidence supports a different major silhouette. Small end rounds,
engraved depths and logos, surface texture and marbling are omitted. Mounting
holes, screws, and any backing board are omitted under the display policy;
this omission does not assert their absence from the physical product.

The model-only manifest uses aspect ratio 1.35 (540/400), a front orthographic
camera and fit padding 0.08, all presentation choices. `dimensions` is absent,
`gripTypes` stays empty, and no finger, capacity, pairing or routine
prescriptions are invented.

## Native verification

The saved documents were independently reopened and recomputed with the pinned
FreeCAD interpreter. Checks confirm:

- each profile is fully constrained and its pad is one valid solid;
- native bounds are 540 × 150 × 400 mm and the eight contact Y extents equal
  the sourced nominal depths;
- every contact binder still links to the profile, and sampled interior points
  of each analytic contact face lie on the pad's outer faces, and their midpoint
  surface normals agree with the corresponding pad faces (dot > 0.999);
- `(X0,Y-10,Z200)` is in the open rear void, while `(X0,Y-60,Z200)` is in the shell;
- editing `Pad.Length` from 540 to 600 mm changes all nine contact widths to
  600 mm without changing their cross-sections;
- increasing `Flat_edge_18` by 2 mm changes only that region's depth from 18 to
  20 mm, preserves all other contact bounds, changes the native solid, and
  keeps every contact on its surface;
- no checks alter the source bytes on disk.

The independent checker is retained as
`Tools/HangboardCAD/tests/transgression_native_source_checks.py`, with a pytest
wrapper in `test_transgression_packages.py`. Compiler, runtime,
package, staged delivery and visual review results are recorded by the main
integration task. Final shape review inspected all six regenerated front/side/top diagnostics
and the independently rendered OpenUSD Hydra oblique. The corrected contact
surfaces face outward, all eight continuous lips and the round jug remain
visible, and the rear shell is concave. Hydra confirms clean planar ramps;
diagonal shading/occlusion artifacts in the simple diagnostic painter are not
exported surface defects. The main task presents these visuals to the user.
Absence of a prior model is explicit rather than represented by an unrelated
board.

Final package, staging, rendered views and app checks are recorded in
[`source-audits/2026-09-29-transgression-cad/validation.md`](source-audits/2026-09-29-transgression-cad/validation.md).
