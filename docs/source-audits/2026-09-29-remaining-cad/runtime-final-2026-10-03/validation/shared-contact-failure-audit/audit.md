# Shared-contact and live-scene failure audit

Read-only diagnosis from the current suite log and source. No runtime, test, CAD, model, descriptor, sidecar, or canonical metadata was changed. No Simulator/build/process/server was started. Only scoped audit artifacts were written; there are no persistent resources to clean up. Input identities are frozen in `input-sha256.json`; the running log excerpt and its observation identity are retained separately.

## Shared-contact failure: confirmed stale neutral-material expectations

`HangTenTests/BoardModelRealityTests.swift:1223–1288` uses **Metolius Contact**, not Stone Hanger Mini. It adds a secondary membership to one existing mesh in an in-memory descriptor. The chosen primary is `edge-16-center` / `contact_edge_16_center`; secondary is `edge-17-center` / `contact_edge_17_center`. Metolius Contact's current native display explicitly authors `surfaceFinish: plastic`.

The test's active assertions at 1278, 1279, 1281 and 1284 are consistent with runtime and did not fail. The failures are at 1282, 1286 and 1287: the test calls its PBR-only roughness helper at1275 after a mesh becomes unselected, then expects neutral roughness0.5. The actual restored material is a procedural **CustomMaterial**, so the cast itself fails. This is not evidence of incorrect shared selection or picking.

Runtime captures the authored material before contact binding (`BoardModelRealityTypes.swift:283–295`) and restores that entire material on deselection (`:1475–1490`). Material definitions are:

| Finish | Normal runtime material | Base roughness | Fallback without shader |
| --- | --- | --- | --- |
| wood | CustomMaterial / boardWoodSurfaceShader | 0.82 | PBR, same wood tint/roughness |
| plastic | CustomMaterial / boardPlasticSurfaceShader | 0.78 | PBR, same mint tint/roughness |
| granite | CustomMaterial / boardGraniteSurfaceShader | 0.92 | PBR, same dark tint/roughness |
| neutral | PhysicallyBasedMaterial | 0.5 | same |
| active selected, any finish | PhysicallyBasedMaterial / solid active tint | 0.8 | same |

Consequently the failure is not “plastic hardcoded for a wood board”; it is an old **neutral** assumption in a test that now uses an explicitly plastic catalog fixture. Wood contacts would also invalidate that old assertion. Material-free USDZ delivery is compatible with these runtime-authored finishes.

Minimal test-only correction: capture shared and secondary-only baseline CustomMaterials before the first highlight; preserve every active PBR0.8 assertion; replace exactly the three unselected0.5 assertions with checks that restored material has the captured type, roughness and base tint. This follows the existing `testPlasticContactsHighlightAndRestoreMintMaterial` pattern (`BoardModelRealityTests.swift:1415–1447`). The current Simulator supports the shaders and other finish tests explicitly require CustomMaterial. If this test is intended to cover devices without shaders, capture and compare either documented baseline type rather than forcing CustomMaterial universally. Do not force this fixture back to neutral merely to pass, weaken the union assertions, change runtime material generation, or change geometry.

Preserve these assertions: shared mesh picks primaryID; secondary-only mesh picks secondaryID; collision and InputTarget exist; secondary membership has no duplicate entities; selecting secondary highlights shared plus secondary-only; selecting primary leaves shared highlighted and restores secondary-only; selecting both highlights the union once; clearing restores both authored baselines.

## Exact accepted Mini shared-contact contract

Current native `nature.stone-hanger-mini` authors wood as board default, with only `nature_stone` explicitly granite. No plastic selector is authored. Current descriptor schema1 has:

| Node | Primary picking ID | Logical memberships | Baseline finish |
| --- | --- | --- | --- |
| nature_jug | pull-up-jug | pull-up-jug, pinch-60 | wood |
| nature_jug_ends | pull-up-jug | pull-up-jug | wood |
| nature_jug_pressure | pull-up-jug | pull-up-jug | wood |
| nature_pinch | pinch-60 | pinch-60 | wood |
| nature_stone | granite-edge-15 | granite-edge-15 | granite |
| nature_wood | wood-edge-15-incut | wood-edge-15-incut | wood |
| nature_body | none | none | wood |

`nature_jug` is the one genuinely overlapping existing upper crown region. The approved broader upper finger-pressure band and end shoulders remain jug-only; the original pinch logical coverage remains `nature_jug + nature_pinch`. This audit did not author or reassess geometric extent. The descriptor retains the accepted pressure-band node and full front/back jug wrap; no model or source correction is implicated by the failing synthetic test.

Expected Mini selection truth table:

| Selection | Highlighted physical nodes |
| --- | --- |
| empty | none; all authored finishes restored |
| pull-up-jug | nature_jug, nature_jug_ends, nature_jug_pressure |
| pinch-60 | nature_jug, nature_pinch |
| both | nature_jug, nature_jug_ends, nature_jug_pressure, nature_pinch |

Runtime V1 binding takes primary picking from node.contactID and memberships from complete descriptor contact node lists (`BoardModelRealityTypes.swift:1402–1439`). Highlight computes a Set union and updates each entity once (`:1117–1126`), preventing an unselected membership from clearing a shared selection. This is independent of wood/plastic/granite material types. The native Mini manifest and descriptor are retained verbatim as scoped metadata in this packet with source/model/descriptor hashes.

## Live-scene timeout: no render-host dependency established

`testLiveScenePausesThenPublishesAcceptedSettledFrame` at `BoardModelRealityTests.swift:553–589` manually loads/selects the live scene, pauses, verifies no movement, sets reduceMotion, resumes, and calls `advanceLiveRopes(elapsed:1/60)` directly. The log records a30-second predicate timeout at571, unsettled final frame at573 and zero notifications instead of1 at574; total test duration76.159seconds. Approximately46seconds therefore occurred before/around the30-second wait, consistent with costly initial preparation; this is not a measurement of the worker's settle duration.

Call path: `BoardModelRealityScene.advanceLiveRopes` (:1020) checks active position and no liveFailure, then invokes `LiveRopeController.advance` (LiveRopeController.swift:117). Its task awaits `LiveRopeWorker.advance` (:55), which calls `RopeDynamicsSolver.settled` when reduceMotion is true. That loop (:226–237) runs up to1200 numerical steps for maxDuration5; 5 means simulated seconds, not wall-clock seconds. Callback applies accepted frame and invokes onLiveFrame (:955–980).

No render subscription or root.isActive check gates that path. The RealityView SceneEvents.Update subscription merely supplies ordinary app ticks. This test already supplies its tick, so adding a render host is not a source-supported fix. The root.isActive guard elsewhere controls geometric tilt animation, a different path.

The current log cannot distinguish a still-running expensive solve from an asynchronously rejected solve: the test does not install onLiveFailure and the scene failure handler does not emit the solver error to this log. It also stops ropes only at the end rather than using defer. A stale/pause-invalidated delivery is theoretically another zero-notification path, but this exact test does not enqueue worker work before pausing, so there is no source evidence for that race here.

Smallest useful next diagnostic change, owned by root: install onLiveFailure before the resumed advance and fail/fulfill immediately; the existing callback has no error argument and liveFailure is private, so recording the concrete error requires a narrow debug/test accessor or error-bearing diagnostic callback (do not attempt direct access from the test); observe accepted completion with onLiveFrame while retaining the exactly1 delivery assertion; add `defer { scene.stopLiveRopes() }` immediately after load. Capture advance-to-result wall time. If an accepted settled result simply needs over30seconds, adjust that measured integration-test wall timeout while keeping numerical convergence/geometry gates; if it reports an error, diagnose that concrete solver failure. Do not silently skip, require a render host, or change accepted native/cached cord geometry on the present evidence. No implementation or successful rerun is claimed by this read-only audit.
