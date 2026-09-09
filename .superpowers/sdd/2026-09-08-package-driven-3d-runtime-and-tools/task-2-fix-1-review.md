# Task 2 fix 1 independent runtime review

Reviewed commit: `175ecc9f1b16dc7bf8d954f8aa7fdc86d67174b4` (`fix: enforce generic model runtime contract`)

Reviewer: Terra independent runtime re-review

Scope: the Task 2 review at `c451b752`, original runtime Task 2, the lean R2/R3/R7 contract, approved model-first specification, repository instructions, `migrate-hangboard-to-3d`, `validate-hang-ten-ios`, the fix brief/report, retained build evidence, and the commit boundary.

## Disposition

**Static/build approval: approved. Runtime-execution approval: pending.**

All four findings from `task-2-review.md` are closed by the reviewed source and focused regression coverage. The later locked-package `build-for-testing` evidence compiles the repaired production and test targets. Focused XCTest execution remains an explicit gate: CoreSimulatorService refused connections during this review, so no additional simulator or device was created and no XCTest count is claimed.

## Findings re-reviewed

| Prior finding | Result | Evidence |
| --- | --- | --- |
| Raster fallback closure made model loading and unavailable states non-observable | Closed | `BoardModelSurface` has no fallback parameter or raster/image lookup. Its loading state is a non-interactive `ProgressView`; its failure state is `BoardModelUnavailableView`, which is non-interactive and exposes `boardModel.unavailable`. Both `BoardDetailMapView` and `BoardMapView` exhaustively switch `BoardPresentationMedia`, constructing `BoardPresentationImage` only in `.raster` and `BoardModelSurface` only in `.model`. `presentationImageURL` itself returns `nil` for model media, and the package-store regression removes a validated model asset, verifies that image URL is `nil`, and receives a `nil` model load. |
| Compact-II framing constants ignored descriptor bounds and display camera | Closed | `BoardModelLoader` passes `media.display`; `BoardModelScene.framing` validates descriptor bounds and orthographic camera data, derives target, view basis, projected extent, fit padding, camera distance, and light placement from them. There is no board-specific coordinate, scale, asset path, or board-ID branch in the renderer. The rebind regression uses materially different bounds, axes, and padding and verifies scene/camera replacement and different camera position/scale. |
| Production-path loader/package-store/cache/unavailable/native-hit coverage was missing | Closed for source/compile review; XCTest execution pending | Focused tests now cover unavailable selection, exact descriptor binding, root/unlisted/materialless rejection, cloned materials and restoration, distinct descriptor-hash keys, model-vs-image URL distinction, missing model bytes after package validation, camera rebind, closest native hit after `SCNTransaction.flush()`, and body nil selection. The cache key contains exactly board ID, presentation ID, and model SHA-256. The retained offline, locked-package `build-for-testing` log ends in `** TEST BUILD SUCCEEDED **`; its resolver is pinned to the four `Package.resolved` revisions. No new execution result or test count exists. |
| Geometry on imported root bypassed the descriptor node set | Closed | `BoardModelScene` rejects `modelRoot.geometry != nil` before traversal. Descendant geometry must have an exact `/`-joined importer-visible path; duplicate paths and invalid meshes are rejected; finally `Set(geometryByNodeID.keys) == Set(descriptorIDs)` is required. `testGenericModelBindingRejectsGeometryOnImportedRoot` covers the malformed-root case. |

## Generic runtime contract audit

- No `BoardModelIdentity`, board-name condition, standalone USDZ lookup, `Resources/BoardModels` lookup, or underscore/hyphen path normalization is present in the changed runtime path.
- `BoardModelAsset` accepts only a regular file URL and calls SceneKit; model bytes never go through ImageIO or a raster fallback.
- Detached decode tasks are keyed by the full `BoardModelKey`; every `BoardModelScene` clones its imported root, geometry, and materials. Highlight reset restores the retained cloned materials.
- Exact descriptor inventory, material presence, vertex-source presence, role/hold binding, body nonselection, nearest-hit `SCNTransaction.flush()`, scene/camera rebind, accessibility identifiers, and on-demand rendering are retained in the production path.
- `SRCROOT=/Users/asherlc/.paseo/worktrees/0h78jp9r/shaky-rat scripts/verify-board-source-boundary-manifest.sh` passed. `git diff --check c451b752 175ecc9f` and the current `git diff --check` are clean.

## Build and resource evidence

- Retained locked/offline compile record: `/Users/asherlc/Library/Application Support/rtk/tee/1788970736_xcodebuild_-project_HangTen_xcodeproj_-s.log`. It uses workspace-owned `shaky-rat-task2-fix-1-DerivedData`, `SourcePackages`, and package cache with automatic resolution disabled, resolved-file-only, and package updates skipped; it ends `** TEST BUILD SUCCEEDED **` after compiling `HangTen`, `HangTenTests`, and `HangTenUITests`.
- The earlier red compile records for SwiftUI/SceneKit type corrections remain distinguishable from that final green compile; they are not treated as passing execution evidence.
- The retained ownership record names only `Hang Ten Paseo shaky-rat Review` and its task-local DerivedData/source-package/cache/result paths. Both simulator manifests contain zero records; each exact fix-1 ephemeral path is absent. Current simulator absence cannot be re-queried while CoreSimulatorService is disconnected.

## Pending runtime gate

At review time, `xcrun simctl list devices` failed before discovery with `CoreSimulatorService connection became invalid` / `Connection refused`. Per the isolated-simulator contract, this review did not create, reuse, or target any simulator. When the service recovers, run the focused `BoardModelTests` and `BoardPackageStoreTests` on a newly recorded exact `Hang Ten Paseo shaky-rat Review` UUID, with workspace-owned locked package copies, full pending/owned-manifest lifecycle, result bundle, and cleanup/absence verification. Report actual XCTest counts separately from this compile/static approval.
