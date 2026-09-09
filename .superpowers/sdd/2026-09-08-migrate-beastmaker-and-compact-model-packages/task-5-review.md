# Task 5 — native SceneKit package semantics review

Date: 2026-09-09

## Reviewed range

`cc03eea8..2e9b67b2`

## Result

**SPEC FAIL** — the required exact nearest-hit contract is contradicted by an
independent host-native SceneKit reproduction. **QUALITY FAIL** — the committed
Task 5 report records passing host-native results that the independent check
does not reproduce.

## BLOCKER — actual descriptor-center rays nearest-hit the body

Using the committed package USDZs and descriptors directly, the review created
the same host-native SceneKit conditions that the task test uses:

- `SCNScene(url:options: [.convertToYUp: true])` loaded each package-owned
  `assets/primary.usdz`;
- the imported root was cloned and attached to a fresh scene, as
  `BoardModelScene` does;
- `SCNTransaction.flush()` completed before selection; and
- parallel rays used the center of every descriptor `facePlaneAABB`, denormalized
  through `modelBounds`, from `maxZ + 2 * maxSpan` to `minZ - 2 * maxSpan`, with
  SceneKit's closest-hit mode.

The result was zero expected-hold resolutions from 22 Beastmaker rays and 19
Compact II rays. Each closest result is unbound body geometry. For example,
Beastmaker `jug-left`'s descriptor-center ray is `(x: 0.0704999984,
y: 0.1318302117)`, lies in `BeastmakerBody_024`'s world bounds, and closest-hits
the body node `BeastmakerBody_023`. The body spans the board face through the
same front depth, occluding the contact mesh for picking.

This contradicts the Task 5 report's claimed 41/41 host-native ray success.
It also means the newly added actual-package XCTest has correctly targeted a
release-blocking integration defect; it must not be declared passing without
execution evidence.

The non-picking native checks did pass:

| Board | Imported meshes / descriptor nodes | Node IDs | Materials | Body probe |
| --- | ---: | --- | --- | --- |
| Beastmaker 1000 | 23 / 23 | exact | all meshes have nonempty diffuse contents | unselectable |
| Metolius Wood Grips Compact II | 20 / 20 | exact | all meshes have nonempty diffuse contents | unselectable |

The required correction is to the physical export geometry, not a runtime
selection filter, fallback, camera adjustment, or package workaround. Per the
3D migration skill, geometry/fidelity correction is routed to Astra; that
handoff is already underway.

## MAJOR — verification evidence is inaccurate

`task-5-report.md` says the read-only host-native diagnostic found all 41
descriptor-center rays on their exact expected mesh IDs. The independent
reproduction above, against the same committed files and SceneKit operations,
does not support that statement. The report must remain rejected until rerun
results are retained after the corrected export is promoted.

## Simulator gate

The report's single read-only `xcrun simctl list devices` preflight failed with
the CoreSimulator service unavailable. It correctly created no device and
recorded no UUID; the workspace-owned simulator manifest is empty and no
pending manifest exists. That is an honest external infrastructure gate, not a
reason to create or retry a simulator.

It nevertheless blocks Task 5 acceptance. The task brief and migration skill
require focused `BoardModelTests` and `BoardPackageStoreTests` XCTest execution
on the prescribed owned simulator. The recorded `build-for-testing` success is
compile-only and cannot replace native XCTest. After Astra corrects the export,
rerun the host-native proof and the focused simulator XCTest before reopening
this checkpoint.

## Scope assessment

The reviewed range changes only the Task 5 report, generic bare importer-ID
binding, and focused tests. It does not change hangboard packages, geometry,
raster fallbacks, model resources, or Xcode project staging. The test design is
otherwise judicious: it covers actual catalog/package loading, literal 22/19
inventories, 23/20 mesh/material inventories, all 41 required rays, body
non-selection, preview/rest material restoration, and cache-isolated
missing/corrupt model failures. Exact full-path binding and the pre-existing
mixed/path mismatch rejection remain covered.
