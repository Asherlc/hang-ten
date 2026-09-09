# Task 5 — native SceneKit package semantics

Date: 2026-09-09

## Scope

Added focused SceneKit semantic coverage for the promoted package-owned
Beastmaker 1000 and Metolius Wood Grips Compact II models. The tests resolve
both boards and their model URLs only through `BoardCatalog.packageStore`,
then load them through `BoardModelLoader.load`. They do not use a standalone
resource, fake model, raster fallback, or per-board renderer branch.

The actual-package checks require the literal 22-ID Beastmaker inventory and
literal 19-ID Compact inventory. Across all 41 contacts they require one bound
hold node per logical hold, nonempty materials with diffuse contents, exact
closest native hits from parallel head-on rays, and a non-selectable body hit.
Each hold ray comes from the center of its descriptor `facePlaneAABB`,
denormalized through the descriptor `modelBounds`. `SCNTransaction.flush()`
precedes picking. The existing focused generic material test continues to
cover independent scene clones and exact active restoration, and now also
covers preview/rest coloring and restoration without duplicating those generic
semantics over all 41 imported nodes.

The existing post-validation missing-model loader test now also covers corrupt
USDZ bytes. Each mutation uses a unique valid board ID, so the asynchronous
model cache cannot satisfy a later case with an earlier scene.

## Binding defect and minimum fix

The actual-package XCTest was authored before the production change. Native
simulator execution was not available for a RED run, as recorded below. A
read-only host SceneKit import of the exact promoted bytes nevertheless proved
the warned production defect:

- Beastmaker geometry imported under paths such as
  `root/Hold_jug_left/BeastmakerBody_024`.
- Compact geometry imported under paths such as
  `root/edge_19_left/Wood_Grips_Compact_II_020`.
- Both validated descriptors intentionally contain the exact bare geometry
  node IDs (`BeastmakerBody_024`, `Wood_Grips_Compact_II_020`, and peers).

`BoardModelScene` previously constructed full hierarchy paths unconditionally,
so its geometry inventory could not equal either descriptor inventory and both
package loads failed closed. The minimum generic correction selects one exact
binding mode from the descriptor: a uniformly bare descriptor binds exact,
unique geometry-node names, while descriptors containing paths retain the
existing exact hierarchy-path behavior. Existing duplicate, missing,
materialless, unlisted-geometry, and mixed/path mismatch rejection remains in
place.

The new actual-package test catches these concrete release failures: either
package cannot load through the catalog/loader bridge, the logical or bound
inventory differs from the approved 22/19 IDs, a body or hold mesh lacks a
diffuse material, a body becomes selectable, or body geometry occludes any
hold's descriptor-center nearest hit. The expanded existing material test
catches an incorrect preview/rest color or a failure to reinstall original
cloned materials. The missing/corrupt test catches a runtime asset failure
escaping as a loaded model; its unique board IDs ensure cache reuse cannot hide
either mutation.

## Native evidence and execution blocker

The mandated one-time preflight was:

```text
rtk xcrun simctl list devices
exit 1
CoreSimulatorService connection became invalid
NSPOSIXErrorDomain Code=61 "Connection refused"
```

Per `validate-hang-ten-ios`, no simulator was created or retried after this
failure. Therefore no simulator UUID exists, and focused XCTest execution is
blocked rather than claimed.

A read-only host-native SceneKit diagnostic against the exact promoted USDZ
and descriptor files completed successfully. It found all 22 Beastmaker and
all 19 Compact closest face-center rays on their exact expected mesh IDs, with
zero failures. Beastmaker exposed the exact 23-node descriptor inventory and
Compact the exact 20-node inventory; every imported geometry had nonempty
materials and diffuse contents. The normalized `[0.5, 0.02]` body probe hit
unbound body geometry for both boards. This establishes that the export
geometry supports the test's picking contract and isolates the observed runtime
defect to node binding; it does not substitute for the pending iOS Simulator
XCTest run. The exact diagnostic script, command/options, outputs, and the
corrected front-to-back versus reversed-span reconciliation are retained in
`.context/shaky-rat-task5-diagnostic-reconciliation.md` and the linked
`.context/shaky-rat-native-occlusion/` packet.

## Verification

The compile-only iOS Simulator build-for-testing completed successfully after
resolving the project's pinned Swift packages:

```text
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Debug -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .context/DerivedData build-for-testing \
  CODE_SIGNING_ALLOWED=NO
exit 0
```

The first compile attempt exposed and corrected test-source syntax/concurrency
errors; the command above is the subsequent successful compile. Focused
`BoardModelTests` and `BoardPackageStoreTests` still require execution on the
exact prescribed simulator once CoreSimulatorService is healthy.

`git diff --check` passed. Workspace-local DerivedData and host Swift module
cache plus the two exact automatic failed-build result bundles were removed,
and their absence was verified. No simulator, HTTP server, tunnel, or other
external resource was created.
