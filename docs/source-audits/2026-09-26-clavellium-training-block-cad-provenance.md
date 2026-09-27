# Clavellium Training Block native CAD migration

Date: 2026-09-26. Package `clavellium-training-block`, revision
`2026-09-contact-first` (unchanged). The committed FCStd is the only source of
the board geometry and metadata. The one-off authoring script is workspace
scratch at `.context/mushy-dragon/author_clavellium.py`; rebuilding the package
uses only `Tools/HangboardCAD/compile_board.py`.

## Evidence

The operator supplied six images on 2026-09-26 while explicitly resuming the
CAD migration. The following three materially distinct views are retained:

| View | Retained file | SHA-256 | Supports |
| --- | --- | --- | --- |
| Loaded block, blue | `2026-09-26-clavellium-training-block-cad-evidence/load-view.webp` | `a031588da8d141a79c13e363c7c60d2d3d01a1527fd4dedd57063144709bd599` | Exterior form, sling in use, channel position |
| Side pull, red | `2026-09-26-clavellium-training-block-cad-evidence/side-pull.webp` | `231fc4e35fc6ecabc0de45ccf101d77e3011a5a153d62f59551393308c0c3ad0` | Side orientation, channel use |
| Channel close-up, blue | `2026-09-26-clavellium-training-block-cad-evidence/channel-view.webp` | `d6be696cca83299ee0677100221d7f71b4a18cc9f91936767d34c1c40ff1df5e` | Three visible square channel mouths and sling |

Publisher of the supplied imagery is not independently verifiable from the
file bytes. The exact product is shown on the [Clavellium Designs climbing
page](https://www.clavelliumdesigns.com/climbing) and its [Etsy listing](https://www.etsy.com/listing/1740404071).
The approved shipped asset `assets/primary.usdz` (prior SHA-256
`3516382e00321d5c831695e454e78b3185092f147ec46b1dbd2ac57b61413f5c`)
is the measured geometry reference. Its original upstream GLB is named
`cd-training-block-complete.glb` in the retained
`2026-09-13-model-cord-snapshots/clavellium-training-block.html` audit, but
that GLB is not present in this checkout. The prior model is a display
reconstruction, not manufacturer-certified CAD.

The photos and current manufacturer page establish that a sling can be used
through the channels. They conflict with the older closed cord audit's
`noDocumentedSuspension` ruling. This migration leaves suspension metadata
unchanged: the supplied views do not establish a complete ordered route or a
per-pose topology for the transient renderer. That audit needs a separate
human ruling before cord metadata is authored.

## Authored geometry and metadata

Published in the existing manifest and manufacturer listing: 80 × 90 × 100 mm
envelope, four crimp depths 8 / 10 / 15 / 20 mm, and three opposed pinch spans
80 / 90 / 100 mm. The complete prior `board.json` is embedded as
`HangTenBoardManifest` without changing any parsed field; the generated JSON
was compared equal to the retired file before deletion. All ten contact IDs
and importer-visible node IDs are retained.

Measured from the approved USDZ world meshes and deliberately drawn in the
native +X right, +Z up, front -Y frame:

- Main envelope: X ±40, Y ±45, Z ±50 mm. Outer edge round: R2 mm.
- Four side cavity floors: 20 and 10 mm on negative X; 15 and 8 mm on positive
  X. Their lower lip starts at Z 1.5 / 25.5 mm, rounds R2.3, then slopes 9°
  inward to the published depth. The lower cavity ceilings are at Z 21.6 mm;
  upper cavity ceilings at Z 42.6 mm. The mouth rises 0.9 mm at the outer face.
  Each cavity is swept over Y -40..40 mm.
- Three square channel mouths on the +Y broad face: center X ±12, Z -10.5..15.5;
  lower left/right X -31..-17 / 17..31, Z -41..-26 mm. Their 10 mm blind depth
  is a display estimate; the retained views do not establish an internal route.
- Six selectable pinch patches preserve the former descriptor's front-plane
  positions and sizes. A 0.05 mm relief splits each patch from its broad body
  face for gap-free mesh partitioning. The physical pinch spans remain 80 / 90 /
  100 mm; the relief is only presentation geometry.

The native source uses analytic Part B-reps, Boolean cuts and open contact
surfaces. The four crimp contacts explicitly use `HangTenDepthAxis=x`; the
compiler defaults to Y for all older sources. There are no materials or
textures in the compiled USDZ. The FCStd is tracked with Git LFS. No mounting
hardware, hook, sling, or cord is baked into it.

## Review and verification

The final prior and CAD front, side, and top previews were rendered next to
each other at `.context/mushy-dragon/compare-final.png` and presented in the
task conversation. The CAD source reproduces the overall bounds, four contact
placements, and six pinch positions. Side slot ends and the blind channel
interiors are simplified relative to the prior display mesh. On triangle
centroids, the nearest opposite-mesh distance is at most 0.59 mm from the
prior mesh to CAD, and 8.15 mm from CAD to prior; the latter maximum is on a
modeled blind channel floor, whose depth is an estimate. This is a sampling
comparison, not a whole-surface Hausdorff guarantee.

`compile_board.py --check` and publish both validate all ten bindings, the
source reopen, and exact X-axis grip depths. Reproducible compilation produced
byte-identical assets. Package validation and the model-delivery lock passed.
The new model and descriptor hashes are recorded in the delivery lock. The CAD
test suite excluding the native lattice pilot test file passed (66 tests);
the Clavellium package was separately rebuilt byte-identically. An iOS
Simulator app build passed twice, but the first capture was obscured by a
system deep-link confirmation and subsequent Simulator launches or screenshots
stalled. Those captures do not establish a visual app review. Both isolated
Simulator devices and their workspace build directories were removed by their
exit traps.
