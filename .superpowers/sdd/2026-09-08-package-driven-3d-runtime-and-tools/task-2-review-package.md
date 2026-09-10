# Task 2 Independent Review Package

Reviewed commit: `ac7b10a625950740fe80c2dcdf60fda8db2b5384` (`feat: render package-owned board models`)

Reviewer: Terra independent runtime review

Scope: original runtime Task 2, lean delta R2, the approved 3D model specification, repository instructions, the 3D migration and iOS-validation skills, the Task 2 report, and retained Task 2 evidence.

## Contract examined

- The generic loader must resolve only typed model media through `BoardPackageStore`, use `(boardID, presentationID, modelSHA256)` as its decode-cache identity, and never use a board registry, static asset path, node-name normalization, or raster/model fallback.
- Scene binding must clone the decoded scene and materials per view, bind every importer-visible geometry node by its exact `/`-joined ancestor path, reject bad material/vertex/inventory inputs, and make body geometry nonselectable.
- The existing nearest-hit, `SCNTransaction.flush()`, highlight-restore, scene/camera rebind, accessibility, and on-demand render behaviors must remain intact.
- R2 requires focused failures and PASS coverage for exact IDs, cache isolation, all semantic states, and nearest-hit behavior. R7 later applies the same mechanisms to actual package assets and all 41 contacts.

## Evidence examined

- Source diff and current source: `HangTen/Views/BoardModelView.swift`, `HangTenTests/BoardModelTests.swift`, and `HangTen/Models/BoardPackageStore.swift`.
- `task-2-report.md` and retained result bundles:
  - `.context/shaky-rat-task2-board-models.xcresult`: 5 passed, 0 failed, 0 skipped on `Hang Ten Paseo shaky-rat Review` (`D693EB9B-26F5-4465-ABCF-51108D36512F`).
  - `.context/shaky-rat-task2-package-tests.xcresult`: 108 passed, 0 failed, 0 skipped on the same device.
- Task script and logs show the required workspace-local resolver/cache paths and exact simulator identity. Both simulator manifests are presently empty; Task 2's local DerivedData, package-cache, and source-package directories are absent. The review-time `simctl` query could not connect to CoreSimulatorService, so current UUID absence cannot be independently re-queried; the retained Task 2 report's cleanup claim is otherwise consistent with empty manifests and absent ephemeral paths.

## Positive checks

- `BoardModelKey` contains exactly the three required identity fields, and `BoardModelLoader` obtains the model URL through `BoardPackageStore.presentationAssetURL` only.
- The renderer contains no board-ID conditional, static model URL, or underscore/hyphen normalization. `BoardModelAsset.load` accepts only a regular file URL and uses SceneKit decode; it does not invoke raster decoding.
- The cache is keyed by the full `BoardModelKey`; decoding is detached; every `BoardModelScene` clones the root then geometry/material instances.
- Child geometry paths are exact named ancestor components joined with `/`; child-node set equality, duplicate-path rejection, nonempty material arrays, vertex-source presence, and body nonselection are implemented.
- The retain/rebind/on-demand/accessibility code remains present, and selection explicitly calls `SCNTransaction.flush()` before closest-hit SceneKit picking.

## Review disposition

**Not approved.** The implementation has a sound generic-binding core, but the findings in the companion report leave the mandated unavailable/no-fallback behavior, descriptor-driven camera behavior, and R2 test contract unproven or violated. The 5/5 and 108/108 result bundles are valid PASS evidence for the tests that ran, not evidence that the missing R2 behaviors work.
