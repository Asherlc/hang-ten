# Task 2 — Astra Beastmaker geometry, human-feedback correction round 2

Status: human-rejected first pass corrected in physical geometry and verified
through actual USDZ export; **renewed human visual approval and native
SceneKit/app validation remain pending**. No live package was promoted. This
report covers Beastmaker only.

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
`hang-ten-board-v1`, within 1 µm of 580 × 150 × 58 mm. There are **112,064
triangles**, below the recorded 200,000 ceiling. All 22 mesh-derived head-on
centre rays hit the expected contact as the nearest surface.

The canonical `.blend` is Y-up/front +Z. The existing compiler explicitly
expects Blender-native Z-up/front −Y, so the generator also saves a rigid
+90° X-axis transport copy with unchanged local vertices, topology and
materials. Its exact matrix and hash are recorded in `model-report.json`.
The compiler converts that copy to the required canonical USDZ frame. Neither
source contains review cameras, lights or any non-mesh object.

## Human-feedback round 2 — outer middle pocket clearance

The human rejected the displayed first pass from commit `d969b1eb`: the
far-left and far-right middle-row pockets were almost cut off/crowded by the
rounded body ends. This was treated as a physical geometry defect, not a
presentation issue. Its sources, reports and all review images are preserved
under `review-round-1/`; its actual export remains in `package-first-pass/`.

The broad 65 mm body-end taper had also lifted the stepped front-face boundary
into these pockets' outer rims. Against the approved manufacturer front and
FluxPerfect three-quarter, Astra made these symmetric authored adjustments:

- `pocket-middle-outer-left/right` throat widths: 86 → 82 mm; centres:
  X=57/523 → 59/521 mm. Each outer end retracts 4 mm while its inner end and
  neighbour gap stay fixed. Height, Y position, cavity depth and fillets stay
  unchanged.
- Upper flat's step edge: Y=52 → 47 mm; upper-roll/wall join: Y=48 → 43 mm;
  lower-fillet end: Y=45 → 40 mm. The same 4 mm upper and 3 mm lower fillets
  remain continuous.
- The step alone now uses a 30 mm horizontal end taper. The body's 65 mm
  outer silhouette taper, 6 mm side-depth roll and exact overall bounds remain
  unchanged, as do all canonical IDs and the mirrored construction.

A targeted guard in the generator probes actual geometry in 2, 4 and 6 mm
bands outside both complete mouths. Before geometry changes, the old actual
USDZ failed at the 2 mm band: a left-pocket probe at XY=(9.973307,62.117531)
mm reached Z=57.812050 mm on the rounded transition instead of the flat
58 mm front. After correction, both source and actual USDZ pass all **480
nearest flat-body hits**, 240 per pocket, in addition to all 22 hold-contact
rays. These clearance bands are display checks, not physical strength claims
or manufacturer measurements.

Astra inspected the corrected source front, three-quarter, clay front,
clay three-quarter and material detail, plus actual USDZ front, three-quarter
and clay detail. Both outer middle mouths now read fully formed with clear
wood margins in the whole-board views. The source/export appearance agrees.
Clay diagnostic detail exposes tessellated rim edges more strongly than the
material views; no camera-based concealment or source-to-export shape repair
was used. A direct comparison of the archived/current JSON confirmed identical
camera definitions, render engines/settings, lights and wood image/material.
The remaining fidelity judgment belongs to the human gate.

Only the generator and this report were edited in this round. The existing
standalone verifier was invoked without modification; no test file was
changed. Per technical review, verifier ownership and its planned
`test_model_reports.py` coverage move to Terra's lower-cost Task 3.

## Artifacts and hashes

All generated artifacts remain owned under
`.context/shaky-rat-beastmaker-1000/` and are not committed.

| Artifact | SHA-256 |
| --- | --- |
| `beastmaker-1000.blend` | `2c2052b67ed98a4cc8b55090efd785217be3ff96f5090b14b2927f7ac5178567` |
| `beastmaker-1000-compiler-input.blend` | `7eb8ee485b4dc3bd286bb74f9cd53664a7b318103500d3a742b4b44d77b1b779` |
| `package-round-2/assets/primary.usdz` | `0251193c0c32e620b9aa153b354ad976a55b63fecab43d18c9828ba1afdf894c` |
| `package-round-2/assets/primary.model.json` | `b09a66150dee26e295b09a6de0cd8b86abef7afd46f37a6d538bc191e1e769fe` |

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

## Verification performed — correction round 2

- The documented generator entrypoint completed with exit 0, including exact
  inventory/bounds/triangle assertions, 22 nearest-head-on hits and 480 flat
  wood-rim hits. The material rerender using the preserved corrected source
  also completed with exit 0.
- The existing `compile_model_package.py` CLI compiled the rigid transport
  copy to `package-round-2`, reimported actual USDZ bytes and passed its
  material, triangle, exact source-piece correspondence and bounds checks.
- Existing `verify_beastmaker_1000.py` completed with exit 0 on those actual bytes.
  It begins with an empty scene and zero source images/materials, verifies
  embedded texture bytes, exact descriptor hash/node inventory, every source
  piece's role/ID, all 23 textured meshes, explicit 112,064 triangles, bounds
  within 1 µm, all 22 nearest-head-on hits and the generator's 480 rim hits.
  It rendered the actual imported artifact with matched source cameras.
  No shape repair occurred.
- Current SHA-256 values were independently recomputed for both `.blend`
  files, actual USDZ and descriptor and match the reports.
- Archived/current renderer, lights, material and all camera definitions are
  identical by JSON comparison.
- `git diff --check`: passed.

Reproduction entrypoints (run from repository root):

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/beastmaker_1000.py -- --output .context/shaky-rat-beastmaker-1000
rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/compile_model_package.py -- --blend .context/shaky-rat-beastmaker-1000/beastmaker-1000-compiler-input.blend --board-json Hangboards/beastmaker-1000/board.json --output-directory .context/shaky-rat-beastmaker-1000/package-round-2
rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/verify_beastmaker_1000.py -- --output .context/shaky-rat-beastmaker-1000/package-round-2
```

The following broader checks passed during the first-pass task and were not
rerun for this narrowly scoped geometry correction:

- `test_model_reports.py`: **6 passed**.
- `test_model_descriptor.py` through the existing workspace venv: **33 passed**.
- Real-Blender `test_compile_model_package_blender.py`: both
  `MODEL_COMPILER_BLENDER_TESTS passed` and `MODEL_COMPILER_EXPORT_TEST passed`.
- The retained invalid-hold fixture was freshly rerun and rejected with exit
  1 and `unknown hold_id`; no descriptor or compiler scratch survived.

During the first-pass task, preliminary sandbox Blender startup crashed before Python during graphics
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

The correction-round compiler scratch
`.context/shaky-rat-beastmaker-1000/.package-round-2.model-compiler-i0wbp_cw`
was likewise verified absent after export. Ownership of the retained rejected
pass and new `package-round-2/` is recorded in the root/archive ownership files.
No material artifact was deleted. The prior remote push was rejected by
automatic approval review; this correction is committed locally without
retrying that denied external export. The controller owns its authorization
gate and subsequent human fidelity review.
