# Compact II lower-cost follow-up prep

Date: 2026-09-09
Scope: static audit only; no Blender startup and no edits to geometry, packages,
evidence, or `Tools/HangboardModels/beastmaker_1000.py`.

## Result

The lower-cost follow-up is not ready to run against the current Compact II
generator without two contract corrections after Astra's physical-shape review:
add explicit `role` tags to the source meshes, and remove the verifier's
whole-body 56 mm assertion. These are tooling/validation changes, not geometry
changes. The current package is still raster-only; no Compact model package or
descriptor is present.

## A. Required source tags

`Tools/HangboardModels/wood_grips_compact_ii.py:317-324` splits the body into
one body object and one object per hold material, sets `hold_id` on hold objects,
but never sets `role`. The body is named `wood-body` and receives neither
`role="body"` nor a `hold_id`; hold objects receive `hold_id` but no
`role="hold"`.

This cannot satisfy the compiler contract: `compile_model_package.py:88-101`
requires every authored mesh to have `role` equal to `body` or `hold`, requires
hold meshes to have a known `hold_id`, and rejects a body `hold_id`;
`compile_model_package.py:103-111` requires exactly one body and a set of hold
IDs equal to the logical inventory. After Astra's geometry correction, the
safe lower-cost change is to tag the existing generated objects at this same
boundary (`body` on the one body object, `hold` plus the existing ID on each
hold object), then validate the saved `.blend` with the compiler. Do not infer
tags from imported names or pixels.

The current generator does save the authored scene at
`wood_grips_compact_ii.py:426`, so it can be handed to the compiler once its
tags and geometry have both been reviewed. The compiler's model-only output
contract is documented at `Tools/HangboardPackages/README.md:19-34,150-163`:
`assets/primary.usdz` plus generated `assets/primary.model.json`.

## B. Whole-body 56 mm assumptions to remove or quarantine

The approved evidence explicitly limits 56 mm to the lower Compact depth
diagram's flat/round sloper callouts and says overall body/display Z depth is
unknown (`.context/shaky-rat-metolius-wood-grips-compact-ii/evidence-brief.md:19-23`;
the same ruling is in `evidence-packet.json:121-127`). Therefore:

* `verify_wood_grips_compact_ii.py:42-47` hard-codes `expected_dims=(.610,.056,.157)`
  and compares the imported model's entire bounding box to it. This is an
  obsolete whole-body assumption. After Astra supplies a reviewed physical
  shape, either assert the explicitly reviewed body-depth value from that
  handoff or leave depth out of this check until it is source/resolution
  approved; do not substitute 56 mm.
* `wood_grips_compact_ii.py:349-355` reports
  `display_estimate_depth_mm: 56`. That field must be removed or renamed to
  make clear that it is not a board/body dimension. The report may retain an
  explicitly scoped sloper/profile parameter only if it is clearly not the
  overall body depth.
* `wood_grips_compact_ii.py:103-129` and `:180-195` use 56 as the generator's
  depth coordinate for authored top profiles, body rings, and recesses. These
  are Astra-owned physical-shape assumptions, not a lower-cost worker's repair
  target. The lower-cost worker must not change these values speculatively;
  after Astra's correction, update only the tags, report fields, and validation
  expectations needed to match the reviewed geometry.

The package's `board.json:8,23-46` uses 24 × 6.2 in / 610 × 157 mm for the
published board dimensions and names three logical slopers 56 mm. Those are
logical/source labels and must not be rewritten as a body-depth fix. The
package test freezes the current raster-only contents at
`Tools/HangboardPackages/tests/test_approved_board_packages.py:368-374`.

The verifier's ID fallback (`verify_wood_grips_compact_ii.py:38-41`) also
allows normalized object names to stand in for `hold_id`. For the model-first
compiler path, the follow-up should validate explicit imported `hold_id`
properties and role/body counts rather than silently deriving IDs from names.

## C. Stable logical inventory (19 IDs, board/evidence order)

The exact set is frozen by `board.json:15-172` and independently mapped in
`evidence-packet.json:43-62`:

```text
jug-left
sloper-flat-left
sloper-round-center
sloper-flat-right
jug-right
edge-29-left
pocket-29-three-left
pocket-29-two-left
pocket-29-four-center
pocket-29-two-right
pocket-29-three-right
edge-29-right
edge-19-left
pocket-19-three-left
pocket-19-three-right
pocket-19-two-left
pocket-19-two-right
pocket-19-four-center
edge-19-right
```

The canonical raster presentation currently owns all 19 IDs through
`board.json:174-195` and the package has exactly `board.json`,
`assets/primary.png` (`test_approved_board_packages.py:368-374`). There is no
tracked Compact `assets/primary.usdz` or `.model.json` in the package. The
separately tracked `HangTen/Resources/BoardModels/wood-grips-compact-ii.usdz`
is a legacy app resource, not proof that the current model-first package or
descriptor exists; migration cleanup must be handled as a separate, explicitly
verified integration step.

## D. Deterministic post-Astra verification sequence

Do not run these commands until Astra's reviewed physical shape and source
tags are available. Replace `PATH/board.blend` and the output paths with
workspace-owned paths; keep the compiler output directory nonexistent before
invocation.

1. Export the reviewed tagged source, if the board-specific generator remains
   the source of the `.blend`:

   ```sh
   rtk proxy blender --background --factory-startup --python-exit-code 1 \
     --python Tools/HangboardModels/wood_grips_compact_ii.py -- \
     --output .context/<owner>-wood-grips-compact-ii
   ```

2. Compile the reviewed `.blend` into the model-first package (the preferred
   package boundary):

   ```sh
   rtk proxy blender --background --factory-startup --python-exit-code 1 \
     --python Tools/HangboardModels/compile_model_package.py -- \
     --blend PATH/board.blend \
     --board-json Hangboards/metolius-wood-grips-compact-ii/board.json \
     --output-directory PATH/compiled-package
   ```

3. Validate the package and exact inventory:

   ```sh
   rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
   rtk proxy .context/hangboard-packages-venv/bin/python -B -m pytest \
     Tools/HangboardPackages/tests/test_approved_board_packages.py \
     Tools/HangboardModels/test_model_descriptor.py -q
   ```

4. Run the actual-export roundtrip only after the verifier has been updated to
   use the reviewed body-depth contract (not 56 mm):

   ```sh
   rtk proxy blender --background --factory-startup --python-exit-code 1 \
     --python Tools/HangboardModels/verify_wood_grips_compact_ii.py -- \
     PATH/compiled-or-export-output --format usdz --skip-renders
   ```

The compiler must remain the authority for descriptor generation: it reads the
logical IDs from `board.json`, validates explicit body/hold tags, reimports the
USDZ, and derives the descriptor from the actual exported mesh. No raster
tracing, segmentation, mask/contour generation, source registration, or
geometry proposal/refinement workflow is permitted.

## Checks run in this audit

No Blender process was started. Static/focused checks passed:

```text
39 passed, 3 subtests passed in 0.10s
6 passed, 22 deselected in 0.05s
```

The first result is `test_model_reports.py` plus `test_model_descriptor.py`;
the second is the Compact selection of
`test_approved_board_packages.py`. The package validator also completed with
61 live packages and 0 drafts, including
`metolius.wood-grips-compact-ii`.
