# Task 2 Runtime Review

Reviewed commit: `ac7b10a625950740fe80c2dcdf60fda8db2b5384`

Disposition: **changes requested; not approved**.

## Findings

### P1 — model loading and failure still execute the raster fallback closure

The R2 plan requires generic package-only model loading and states `.loading`, `.ready`, and `.unavailable`; the lean R2/R3 contract prohibits passing an image/raster closure to a model failure branch. `BoardModelSurface` still stores `fallback` ([BoardModelView.swift](/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat/HangTen/Views/BoardModelView.swift:84)) and invokes it for every state other than `.ready` ([BoardModelView.swift](/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat/HangTen/Views/BoardModelView.swift:91)). Thus both initial model loading and the explicit `result = .unavailable` failure path ([BoardModelView.swift](/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat/HangTen/Views/BoardModelView.swift:113)) reach the closure. `BoardMapView` supplies that closure from its existing raster-map content ([BoardMapView.swift](/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat/HangTen/Views/BoardMapView.swift:291), [BoardMapView.swift](/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat/HangTen/Views/BoardMapView.swift:483)).

This contradicts the no-fallback global constraint and makes the declared `.unavailable` state non-observable. Split raster/model routing exhaustively: only raster may receive the raster closure; model loading needs a non-raster loading view and model failure needs a generic inaccessible unavailable view. Add a test which proves neither a supplied fallback closure nor raster-image lookup is evaluated for invalid/missing model media.

### P1 — camera remains Compact-II constants instead of package descriptor data

`BoardModelScene` receives a descriptor but ignores `descriptor.modelBounds`; `BoardModelLoader` also does not pass `media.display` to scene setup. The scene is framed with hard-coded position/target coordinates and a `0.335` scale formula ([BoardModelView.swift](/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat/HangTen/Views/BoardModelView.swift:232), [BoardModelView.swift](/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat/HangTen/Views/BoardModelView.swift:274)). The approved specification requires presentation `display.camera` plus validated model bounds to drive camera target/scale; the new generic renderer must support the two package-owned revisions without a hidden Compact-specific frame.

Thread validated bounds and display camera into scene construction, derive a head-on orthographic camera target/scale from them (including fit padding), and cover two materially different descriptor bounds/configurations in the rebind/frame test.

### P1 — required R2 runtime tests were removed rather than replaced with production-path coverage

The retained model result is genuinely 5/5, but its only cases are the five synthetic-scene tests listed by its xcresult: exact IDs, unlisted/materialless geometry, highlight cloning, scene/camera rebind, and tap-enable boolean. The replacement test file has no test that calls `BoardModelLoader.load`, `BoardModelAsset.load`, or the cache; no cache-SHA separation test; no unavailable-state test; and no nearest-hit ray test ([BoardModelTests.swift](/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat/HangTenTests/BoardModelTests.swift:8)).

The test helper correction did narrow coverage materially: the prior file's actual USDZ material/inventory test and its pocket nearest-hit regression were deleted, while the new helper creates two `SCNBox` nodes only ([BoardModelTests.swift](/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat/HangTenTests/BoardModelTests.swift:117)). The 108/108 package result includes a synthetic model-package parser fixture, but it does not exercise SceneKit runtime loading or any actual model asset. This fails R2's explicit focused-test gate and cannot substantiate the Task 2 report's claims of cache behavior, unavailable behavior, or preserved native picking.

Restore coverage through production APIs: use a temporary package bundle/store and model file for `BoardModelLoader`, prove distinct SHA values produce isolated decoded sources and cloned scenes, prove invalid/missing model media reaches unavailable with no raster callback, and retain a CPU SceneKit closest-hit regression after `SCNTransaction.flush()`. R7 must then move those checks to both actual package-local assets and every logical contact.

### P2 — an unbound geometry attached to the imported root is silently excluded from the node-set check

The traversal starts at `modelRoot.enumerateChildNodes` ([BoardModelView.swift](/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat/HangTen/Views/BoardModelView.swift:162)), which visits descendants but not `modelRoot` itself. Geometry on the imported root is then rendered when that root is added to the scene ([BoardModelView.swift](/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat/HangTen/Views/BoardModelView.swift:219)) yet is absent from `geometryByNodeID`; set equality at line 184 still passes. This violates the requirement that every importer-visible geometry node be descriptor-bound.

Reject root geometry explicitly (a root has no valid descriptor path under this contract), or include it in the validation walk and prove the malformed-root case fails.

## Boundary and evidence notes

- No active production reference to the old standalone Compact model remains in this commit, and no board-specific branch or name normalization survives in `BoardModelView.swift`.
- The 5.6 MiB `HangTen/Resources/BoardModels/wood-grips-compact-ii.usdz` remains tracked and compiled by `HangTen.xcodeproj`. The lean plan assigns its deletion to M1 once package promotion removes every tracked member, so this is an outstanding final-boundary obligation rather than an R2 source-routing defect.
- `git diff --check ac7b10a^ ac7b10a` is clean. Retained test summaries confirm 5/5 and 108/108 on the prescribed simulator. Both Task 2 manifests are empty and the named task-local ephemeral directories are absent; current `simctl` re-query was unavailable because CoreSimulatorService was disconnected.

