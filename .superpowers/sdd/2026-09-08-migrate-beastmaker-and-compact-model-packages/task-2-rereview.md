# Task 2 — Beastmaker 1000 correction re-review checkpoint

Reviewed commits: rejected-pass base `d969b1eb`, physical correction
`c3a15af5`, and human-fidelity-gate record `8ebbdb78`.

## Scoped result

**SPEC PASS** — the scoped physical correction satisfies the Task 2 geometry
requirements. **QUALITY PASS** — the human visual-fidelity gate for the
corrected actual USDZ is now explicitly approved. This checkpoint is not
native SceneKit/app validation and does not promote a package.

## Correction evidence

The change is physical geometry, not a presentation adjustment:

- `pocket-middle-outer-left/right` changed symmetrically from 86 mm to 82 mm
  throat width and from X=57/523 mm to X=59/521 mm centre positions. The
  crowded outer end retracts 4 mm while its inner end/neighbour gap remains
  fixed.
- The upper-step edge/roll/lower-fillet positions are Y=47/43/40 mm and the
  step uses its own 30 mm end taper; the 65 mm overall body-end taper and
  overall board envelope are preserved.
- The archived rejected actual USDZ independently fails 42 of 160 two-mm
  wood-rim probes across both affected pockets. Its first left failure is at
  XY=(9.973307, 62.117531) mm, where the nearest body is Z=57.812050 mm
  rather than the 58 mm flat face.
- The corrected actual USDZ independently passes all 480 wood-rim probes:
  240 for each affected pocket over 2, 4, and 6 mm bands. Every checked point
  reaches the flat 58 mm body face.

## Export and identity evidence

Read-only import of `.context/shaky-rat-beastmaker-1000/package-round-2`
independently verified 23 importer-visible meshes, exact correspondence for
the body plus all 22 canonical hold IDs, 112,064 triangles, bounds within one
micrometre of 580 × 150 × 58 mm, embedded texture data on each material-bound
mesh, and all 22 nearest head-on hold-contact rays. The reviewed package hashes
are:

- `primary.usdz`: `0251193c0c32e620b9aa153b354ad976a55b63fecab43d18c9828ba1afdf894c`
- `primary.model.json`: `b09a66150dee26e295b09a6de0cd8b86abef7afd46f37a6d538bc191e1e769fe`

The rejected source/renders remain archived in `review-round-1/` and its actual
export remains under `package-first-pass/`. The correction did not alter a
verifier or test file: `d969b1eb..c3a15af5` changes only the generator and the
Task 2 report. Cameras, render settings, lights, and the generic pale-wood
texture hash are identical between the rejected and corrected review packets,
so the visible clearance change cannot be attributed to a render workaround.

## Human gate and remaining scope

Commit `8ebbdb78` records the human's explicit chat approval of the corrected
actual-USDZ front, three-quarter, and clay-detail renders after `c3a15af5`.
That closes the only pending human visual-fidelity gate identified in the
correction report. Native SceneKit/app validation and any package-promotion
decision remain subsequent, out-of-scope work.

## Review hygiene

`git diff --check` passed for the checkpoint. No geometry, verifier, test, or
Task 3 working file was changed by this review artifact.
