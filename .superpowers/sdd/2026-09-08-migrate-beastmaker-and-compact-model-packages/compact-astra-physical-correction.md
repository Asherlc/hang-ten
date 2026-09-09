# Compact II — Astra physical correction

Date: 2026-09-09. Owner: `shaky-rat`. Scope: physical portions of
`Tools/HangboardModels/wood_grips_compact_ii.py` and owned review artifacts.
No Beastmaker file, live package, schema, compiler, or production verifier was
changed by this geometry task.

## Evidence inspected before authoring

Both exact human-approved full images were opened at original detail and their
SHA-256 values verified. The evidence packet, brief, lower-cost prep, migration
plan, and migration skill were read before geometry work.

- Manufacturer front: `.context/shaky-rat-metolius-wood-grips-compact-ii/references/compact-training-board.jpg`,
  SHA-256 `d72c7027d82980306e0e2a50d94394c174dce8ba0fd9bb239c704f099f05ed03`.
  Source: <https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards>.
  Supports front inventory, relative placement, aperture families, stepped
  outline, and visible wood ligaments. Does not measure hidden sections or Z.
- Bergfreunde commerce-gap elevated oblique:
  `.context/shaky-rat-metolius-wood-grips-compact-ii/references/bergfreunde-compact-ii-oblique.jpg`,
  SHA-256 `1729ecad6eec3df71c9e8e06341c10cc936631edf47948fd17235ed9a5bd991a`.
  Source: <https://www.bergfreunde.eu/metolius-wood-grips-compact-ii-training-board/>.
  Supports substantial top-section thickness, outer rollover continuity and
  side/edge transitions. Neither measured body depth nor hidden back geometry
  is established; commerce evidence does not override manufacturer claims.

No legacy raster presentation, canonical hold path, pixel trace, crop,
segmentation, contour, vectorization, or generated-image geometry was used.

## Sourced facts versus authored estimates

| Item | Decision and provenance |
| --- | --- |
| Face dimensions | Preserve sourced 610 × 157 mm from the current manufacturer product page. |
| Contact inventory | Preserve exactly the existing 19 stable IDs and left/right symmetry. The numbered lower Compact diagram supplies the inventory mapping. |
| 56 mm | Preserve only the official lower Compact #2 flat-sloper and #9 round-sloper callouts. `SLOPER_CONTACT_DEPTH_MM` is separate from body depth. Applying this to an authored depth-direction profile run, and locating its back start, are display-section interpretations rather than additional manufacturer measurements. |
| Overall body depth | `BODY_DEPTH_MM = 64.0` is an independent Astra display estimate informed qualitatively by the oblique view. It is not a measured product dimension, a source claim, or fabrication CAD. The estimated profile places an 8 mm rear band before the 56 mm top contact run. |
| Top sections | Broad outer-jug plateau with continuous 34 mm front roll and 18 mm drop; flat-sloper pitch with 8 mm drop; central convex sloper with 16 mm drop. These section dimensions and all transition blends are estimated. |
| Pocket sections | Retain sourced 29/19 mm depth labels. Keep continuous 3.5 mm mouth fillets; use estimated 4.5 mm pocket back fillets. Open side edges retain their fuller 6 mm mouth/back fillets. |
| Outer-pocket wood | Shorten the inner ends of the open side recesses to leave 10 mm upper and 12 mm lower front ligaments to the closed outer pocket mouths. The complete wood margin is visible in both approved images; the numeric widths are authored estimates. |
| Lower apertures | Preserve the lower outer three-finger positions, with estimated 62 mm throat widths. Use 39 mm two-finger throats at mirrored x = 224.5 / 385.5 mm. This creates 6 mm wood ligaments between the lower three-/two-/four-finger mouths where the previous lower inner mouths touched the center mouth. |
| Curved strip facets | Explicit mirrored triangle diagonals make corresponding nonplanar top strips the same physical surface on both sides. This fixes source-shape ambiguity; export-only triangulation of Boolean cap n-gons remains unchanged. |
| Finish and omissions | Existing original generic pale wood is retained; no grain/species match is claimed. Screw holes, mount holes, countersinks, hardware, and logos are deliberately omitted from the display model, not claimed absent from the product. |

The legacy generator frame is metres, X centered left/right, Blender Z up,
and negative Blender Y toward the climber. Source bounds are therefore
610 × 64 × 157 mm in Blender XYZ order. Conversion into the compiler's
`hang-ten-board-v1` frame remains a lower-cost integration responsibility.

## RED and GREEN physical evidence

All paths below are beneath
`.context/shaky-rat-metolius-wood-grips-compact-ii/`.

RED retained the unmodified generator snapshot and generated clay mesh/views
under `astra-red/`. Its body bounds are 610 × 56 × 157 mm and the generated
report conflates the 56 mm sloper labels with whole-body depth. The complete
front/oblique rim check exits 1: **156 of 1,320 probes fail**. The first bounded
upper-outer-pocket check failed 14 of 132 front probes. The broader check also
exposes the lower-row touching-mouth defect. The unchanged curved source has
45 mismatches among 1,952 mirrored section pairs.

GREEN source evidence is `astra-reviewed-clay/geometry-review.blend` and
`source-physical-check.json`: **1,320 of 1,320 front/oblique rim probes pass**,
**1,952 of 1,952 mirrored section pairs pass**, bounds
610.000014 × 64.000003 × 157.000005 mm. The separate front-only geometry report
passes 660 of 660 probes. Astra inspected its full front, three-quarter and
clay-detail renders at original detail before the final texture/export run.

The rim check probes a complete exterior capsule ring at 1.5 times the authored
mouth-fillet radius (5.25 mm beyond the mouth). Every first hit must be on the
front body surface, including oblique rays. It checks actual mesh triangles,
not a camera mask. Symmetry uses matching interior front rays with a one
micrometre tolerance; exact tangent silhouette rays are excluded because a
single-precision boundary hit is not a physical section measurement. RED and
GREEN use the identical final check script.

Owned check scripts:

- `.context/shaky-rat-compact-astra-review.py` executes only the real generator's
  geometry prefix for inexpensive clay review and records its exact snapshot.
- `.context/shaky-rat-compact-astra-export-check.py` reads a saved source or
  actual USDZ in isolation, probes exterior rims/sections, and reports exact
  bounds, mesh count, hold IDs, triangles and file hash. It does not repair a
  mesh or change production verification logic.

Final generator/snapshot SHA-256:
`cd2293927891b06173f6a4d0a2eeb960df4d76b41a30e7fc54d7d9c0b57f432a`.

Final full generator output is `astra-reviewed/`. The documented entrypoint
completed with exit 0 without injected import paths. Astra inspected its
`front.png`, `three-quarter.png`, and `clay-detail.png` at original detail:
complete rim wood is visible, the lower mouths remain distinct, and the top
rolls/pitched sections are continuous. Human approval remains pending.

The actual exported USDZ was reimported after clearing source objects,
materials and images. `astra-reviewed/export-physical-check.json` exits 0:
**1,320/1,320 rim probes**, **1,952/1,952 mirrored sections**, exact expected
19 explicit imported hold IDs, 20 meshes, 65,424 triangles, and the same
610.000014 × 64.000003 × 157.000005 mm bounds. This is physical geometry
evidence; the separate compiler/material/native acceptance checks are still
required and are not claimed complete here.

Final artifact SHA-256 values:

- `wood-grips-compact-ii.blend`: `ee4bc45e23196582db9f9e9dd93cfd9a2ded3b07fec5f41d6da82efb676cc935`
- `wood-grips-compact-ii.usdz`: `53936bdc18e7a1a6aa69aaf56877fe9fdc7099e50fbf6926cf72bf3d11d1ef79`
- `front.png`: `d8b2fa2c21d19a51ee81a635431291b6e52f673edeb198d0f758c61815b789e9`
- `three-quarter.png`: `16ee0f86784ddfaef796ea685695f2ddc78c14a96d48680d3f2a7b89da5d4544`
- `clay-detail.png`: `875032fedb3620f355a52f28ce54020b7015b4ee659b111dff1063d44d687ef1`

Commands run from the repository root:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/wood_grips_compact_ii.py -- \
  --output .context/shaky-rat-metolius-wood-grips-compact-ii/astra-reviewed
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python .context/shaky-rat-compact-astra-export-check.py -- \
  .context/shaky-rat-metolius-wood-grips-compact-ii/astra-reviewed/wood-grips-compact-ii.usdz \
  .context/shaky-rat-metolius-wood-grips-compact-ii/astra-reviewed-clay/generator-snapshot.py \
  .context/shaky-rat-metolius-wood-grips-compact-ii/astra-reviewed/export-physical-check.json
rtk git diff --check
```

Intermediate `astra-green*`, `astra-final*` and earlier snapshots are retained
only as audit evidence and must not be promoted.

## Handoff gates and resources

Human visual approval of the final `astra-reviewed/` front, three-quarter and
clay-detail set remains mandatory before live package promotion. Source role
tags, remaining legacy report language, verifier contracts, deterministic
compiler/package output, coordinate-frame integration, native materials/picking,
bundle hashes and simulator validation remain assigned to Terra/controller.
All 19 logical IDs/source-backed metadata remain unchanged.

No HTTP server, tunnel, simulator or other persistent external resource was
created. Every Blender run is an owned foreground batch process; output
ownership is immediately recorded by the existing generator. The first
sandboxed launch crashed before Python in Metal device detection; its trace
was inspected and subsequent normal-graphics launches were explicitly approved
by automatic review. No geometry or package change was used to bypass a check.
Durable `.context` sources, images and reports are intentionally retained for
human review and are not committed. Every owned Blender session exited;
there is no background render process or external resource to clean up.
