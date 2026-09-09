# Task 2 — Astra Beastmaker geometry and first-pass export

Status: authored first pass and actual-export verification complete; **human
visual approval and native SceneKit/app validation remain pending**. No live
package was promoted. This report covers Beastmaker only.

## Evidence received and inspected

The controlling session explicitly approved the exact four-image set before
the resumed refinement. Astra inspected every image at original detail and
recomputed each SHA-256:

| Board / image | Tier | SHA-256 |
| --- | --- | --- |
| Beastmaker `references/beastmaker-1000-tulip.jpg` | Manufacturer front | `b97c4a0fc1c6f8971cb7610a2ec2a979415e6c9018398c18ab76ed90034fdfae` |
| Beastmaker `references/fluxperfect-beastmaker-1000-ansicht-1.jpg` | FluxPerfect commerce-gap three-quarter | `959801633efd53b10dba145a659988290d5189ea2bcc171329fedd1e6d52a3ff` |
| Compact II `references/compact-training-board.jpg` | Manufacturer front | `d72c7027d82980306e0e2a50d94394c174dce8ba0fd9bb239c704f099f05ed03` |
| Compact II `references/bergfreunde-compact-ii-oblique.jpg` | Bergfreunde commerce-gap oblique | `1729ecad6eec3df71c9e8e06341c10cc936631edf47948fd17235ed9a5bd991a` |

The two Beastmaker images alone informed Beastmaker shape. Compact references
were received for the following Compact scope; no Compact geometry/code was
read or changed as a shape source. No legacy package PNG, canonical 2D hold
paths, prior candidate model, tracing, segmentation, vectorization, alignment,
cropping, or automatically extracted geometry was used.

Updated Beastmaker packet SHA-256:
`510def2516477dedb248ea85e3ec858129d0f298014b28c3e7ef9b19bd41cce0`.
Updated handoff SHA-256:
`444dc99cacf1e68fc8b564667a22b965d5e9a624b3e38953a6f98ab07edea5ea`.
Both full packets/briefs and the updated Beastmaker handoff were read. The
manufacturer supplies 580 × 150 mm face and the qualified 58 mm shared-layout
depth ruling. Commerce media gives qualitative additional view evidence; it
does not establish radii, measured depth, hidden back shape or cavity sections.

## Authored result

`Tools/HangboardModels/beastmaker_1000.py` directly authors symmetric lofted
body/jug/sloper sections and 17 mirrored analytic recesses. It produces one
body and 22 individually tagged hold meshes, with exact inherited stable IDs.
The physical carved surfaces are the selectable/highlighted meshes.

The newly approved true three-quarter view showed a more definite lower step
than the preserved first draft's broad S-shaped shoulder. Astra replaced that
shoulder with an estimated step wall and continuous 4 mm upper/3 mm lower
fillets. Pocket mouths have 2.8 mm rolls, true walls and back fillets up to
4 mm. The paired nominal 35° and centre 20° sections blend into the body;
outer jugs have continuous rounded sections. Exact positions, profile shapes,
all radii, cavity depths and tier/back sections remain authored estimates.
The original generic pale-wood texture is unrelated to the source photographs.

Screw holes, mounting holes, countersinks, mounting hardware and logos are
deliberately omitted from display geometry. This does not claim that the
physical product lacks mounting features.

Source bounds are `[0,0,0]` to
`[0.5799999833106995,0.15000000596046448,0.057999998331069946]` metres in
`hang-ten-board-v1`, within 1 µm of 580 × 150 × 58 mm. There are **111,740
triangles**, below the recorded 200,000 ceiling. All 22 mesh-derived head-on
centre rays hit the expected contact as the nearest surface.

The canonical `.blend` is Y-up/front +Z. The existing compiler explicitly
expects Blender-native Z-up/front −Y, so the generator also saves a rigid
+90° X-axis transport copy with unchanged local vertices, topology and
materials. Its exact matrix and hash are recorded in `model-report.json`.
The compiler converts that copy to the required canonical USDZ frame. Neither
source contains review cameras, lights or any non-mesh object.

## Artifacts and hashes

All generated artifacts remain owned under
`.context/shaky-rat-beastmaker-1000/` and are not committed.

| Artifact | SHA-256 |
| --- | --- |
| `beastmaker-1000.blend` | `91d9474dcd494e77849d0a8356d9a3f49b7eaa002e3a9f4519e7f780bdbd1c4d` |
| `beastmaker-1000-compiler-input.blend` | `21ac0de1c73a700f1847e1154bfddc1d505c9ebd753298477a6853a4ee08ec9c` |
| `package-first-pass/assets/primary.usdz` | `697ff2818c88803bda7323ddda9a21ac828807eda555434ce8ec213bdd78b78c` |
| `package-first-pass/assets/primary.model.json` | `517d18c480e3c499b8b42e643dfa1aa31a179dda956d8af01f6f5c17303f277e` |

Reports: `model-report.json`, `source-versus-estimate.md`, and
`export-verification.json`. Camera/light/engine/material settings and image
hashes are retained in those reports.

Source review images: `front.png`, `three-quarter.png`, `material-detail.png`,
`clay-front.png`, `clay-three-quarter.png`, `clay-detail.png`,
`selected-holds.png`, and `contact-overview.png`. Actual-export review images:
`usdz-front.png`, `usdz-three-quarter.png`, and `usdz-clay-detail.png`.
Cycles CPU with 48 samples and denoising is the recorded production engine;
Workbench provides inexpensive clay diagnostics. Astra inspected the source
images and all three actual-export images. The export preserves the reviewed
silhouette, pockets, step and generic wood visually.

## Verification performed

- The documented generator entrypoint completed with exit 0, including exact
  inventory/bounds/triangle assertions and 22 nearest-head-on hits.
- The existing `compile_model_package.py` CLI compiled the rigid transport
  copy to `package-first-pass`, reimported actual USDZ bytes and passed its
  material, triangle, exact source-piece correspondence and bounds checks.
- New `verify_beastmaker_1000.py` completed with exit 0 on those actual bytes.
  It begins with an empty scene and zero source images/materials, verifies
  embedded texture bytes, exact descriptor hash/node inventory, every source
  piece's role/ID, all 23 textured meshes, explicit 111,740 triangles, bounds
  within 1 µm, and all 22 nearest-head-on hits. It renders the actual imported
  artifact with matched source cameras. No shape repair occurs.
- `test_model_reports.py`: **6 passed**.
- `test_model_descriptor.py` through the existing workspace venv: **33 passed**.
- Real-Blender `test_compile_model_package_blender.py`: both
  `MODEL_COMPILER_BLENDER_TESTS passed` and `MODEL_COMPILER_EXPORT_TEST passed`.
- The retained invalid-hold fixture was freshly rerun and rejected with exit
  1 and `unknown hold_id`; no descriptor or compiler scratch survived.
- `git diff --check`: passed.

The preliminary sandbox Blender startup crashed before Python during graphics
initialization; approved unsandboxed Blender execution succeeds. A preliminary
descriptor test command used system Python without pytest; the existing venv
run above passes. The first isolated-render attempt exposed a missing world in
the deliberately empty scene; the verifier now creates its own review world,
and the complete repeat passes. None of these corrections changes shape.

## Remaining gate and resource cleanup

Human visual fidelity approval is still required before package promotion.
The shape is display geometry, not manufacturing CAD. Exact cavity sections,
rear profile, radii and physical per-ID depth mapping remain estimates; the
generic material does not claim species/grain fidelity. SceneKit/importer
node behavior, native materials/picking, bundled byte hashes and simulator
interaction are not proved by these Blender checks and remain integration
work. No `board.json`, raster asset, runtime source or training metadata was
changed in this task.

No external simulator, server or tunnel was created. All Blender invocations
completed. Compiler/test temporary directories were removed by their existing
`finally` cleanup; the exact `.package-first-pass.model-compiler-jjt22oie`,
`.context/shaky-rat-model-compiler-test-5gh467ju`, and
`compiler-scratch-invalid` paths were verified absent. Durable evidence,
sources, export and renders remain in the owned directory.
