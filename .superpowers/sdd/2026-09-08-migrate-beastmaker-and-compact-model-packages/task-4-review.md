# Task 4 — promotion completion review

Date: 2026-09-09

## Reviewed range

Initial promotion reviewed: `95ab9661..ff27b2df`.

Fix re-review: `ff27b2df..9c8b891a`.

## Original blocker

The promotion artifacts were sound, but the first review found that
`Tools/HangboardPackages/tests/test_approved_board_packages.py` had been left
red: 7 failures and 21 passes. Its generic original-owner and asset-inventory
assertions assumed raster `holdGeometry`/a single PNG asset, while its Compact
cases still required the deleted PNG and raster-derived bounds. The Task 4
brief required model-package negative coverage before promotion and did not
authorize leaving those directly affected tracked tests stale. This was a
**SPEC FAIL / QUALITY FAIL** blocker for `ff27b2df`.

## Fix review

`9c8b891a` updates the approved-package suite without relaxing raster-board
coverage:

- Raster-only packages still require complete original raster ownership.
- A package containing model media must be model-only, and its declared asset
  inventory includes both `assetPath` and `descriptorPath`.
- Compact now asserts its exact three-file model package, stable logical hold
  inventory, model descriptor inventory/node bindings, approved USDZ and
  descriptor SHA-256 values, hash binding, coordinate frame, and non-empty
  model-derived frames.
- The negative test copies both Beastmaker 1000 and Compact II packages, adds
  `assets/primary.png`, and requires the loader to reject the undeclared
  fallback asset.
- The new `BoardSourceBoundaryTests` XCTest requires Compact's package-owned
  model and descriptor, verifies its package asset URL, verifies no image URL,
  and verifies that the legacy standalone `BoardModels` resource is absent.

The review verified that `ff27b2df..9c8b891a` has no production package,
model asset, standalone-resource, Xcode-project, or tracked-inventory changes.
The approved Beastmaker (`e15bae…` / `2c3928…`) and Compact
(`220c68…` / `300a268…`) production bytes therefore remain unchanged from the
promotion review.

## Evidence

The fix report records the intended RED result of 7 failures and 21 passes
(28 tests), followed by a 29-test GREEN suite after adding the target fallback
test. Fresh scoped re-review checks confirmed:

```text
Tools/HangboardPackages/tests/test_approved_board_packages.py   29 passed
Tools/HangboardPackages/tests/test_model_first_packages.py
Tools/HangboardModels/test_model_descriptor.py                  75 passed
Tools/HangboardModels/test_model_reports.py                     12 passed
scripts/hangboard-packages.sh validate --root Hangboards --final-inventory  pass
git diff --check ff27b2df..9c8b891a                             pass
```

The fix report also records a successful unsigned
`xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator
-configuration Debug ... build-for-testing`, producing the app and test
bundles, followed by cleanup of its exact workspace-owned DerivedData and log.

## Subsequent tracked scope

`BoardSourceBoundaryTests.testEveryCatalogBoardUsesItsDefaultPackagePresentationPNG`
is an older independently stale XCTest: it predates this range and still reads
legacy `default` and top-level `assetPath` JSON fields, then requires every
board to return a raster image URL. It was already inconsistent with the v2
typed-media schema before Task 4 and was not introduced or worsened by this
promotion/fix range. Track its conversion to typed raster/model presentation
semantics separately; it is not a reason to reopen this completed Task 4
checkpoint.

## Result

**SPEC PASS** — the model-only promotion's required package and standalone
fallback regressions are covered, while raster coverage remains intact.

**QUALITY PASS** — the original seven failing tracked tests are GREEN, the
production assets remain unchanged, and no blocker, critical, major, or minor
finding remains in the reviewed fix range.
