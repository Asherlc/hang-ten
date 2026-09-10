# Task 8: cross-parser contract review

## Result

Python and Swift now consume one named, declarative model-package malformed
fixture matrix from `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`.
Each runner starts from the same shared model board, descriptor, and model
bytes, applies the same ordered mutations, writes the same declared extra
assets, and validates the resulting package through its production parser.
There were no parser changes.

The requested conditions already had scattered behavior coverage in both
suites, so this is characterization coverage rather than a manufactured RED
against an intentionally weakened parser. The matrix makes the documents and
the expected Swift error category explicit and shared.

## Shared malformed fixture matrix

| Named fixture | Mutation | Python | Swift |
| --- | --- | --- | --- |
| `wrong-schema-version` | Board schema version is `1` | `ValueError` | `.invalidPackage` |
| `unknown-media-type` | Model media tag is `video` | `ValueError` | `.malformedJSON` |
| `escaped-typed-path` | USDZ path is `assets/../primary.usdz` | `ValueError` | `.invalidPackage` |
| `extra-asset` | Declares no `assets/extra.usdz` but writes it | `ValueError` | `.invalidPackage` |
| `stale-sha` | Descriptor SHA-256 is all zeroes | `ValueError` | `.invalidPackage` |
| `omitted-node` | Removes the logical hold node | `ValueError` | `.invalidPackage` |
| `extra-node` | Adds a node bound to an unknown logical hold | `ValueError` | `.invalidPackage` |
| `body-with-hold-id` | Gives the body node a `holdID` | `ValueError` | `.invalidPackage` |
| `unbound-geometry` | Descriptor frame references `Unbound` rather than the bound node | `ValueError` | `.invalidPackage` |
| `invalid-camera` | Orthographic view direction is `[0, 0, 0]` | `ValueError` | `.invalidPackage` |
| `model-inversion` | Model presentation becomes derived/inverted | `ValueError` | `.invalidPackage` |

The Python test asserts the matrix's declared `ValueError` outcome for all
eleven packages. The Swift test asserts each declared `.invalidPackage` or
`.malformedJSON` category, rather than accepting an arbitrary error. Existing
single-rule tests retain their focused assertions for SHA binding, asset
inventory, descriptor validation, tagged media, camera validation, and model
derivation; the shared matrix supplies the cross-parser document identity.

## Verification

- `source .context/hangboard-packages-venv/bin/activate && rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q`
  - `42 passed in 0.23s`.
  - The initially literal proxy command could not import `pytest`; activating
    the existing workspace-owned package test environment before the same proxy
    invocation provided the repository test dependency without installing or
    changing dependencies.
- `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=1359DA1B-D90A-41EA-B45B-2399D34F144A" -derivedDataPath .context/DerivedData -resultBundlePath .context/task8-final-BoardPackageStoreTests.xcresult -only-testing:HangTenTests/BoardPackageStoreTests`
  - XCTest result: `107 passed`, `0 failed`, `0 skipped`, `result: Passed`.
- `git diff --check` passed.

## Simulator ownership and cleanup

The final verification used exactly this recorded device:

- Name: `Hang Ten Paseo shaky-rat Review`
- UUID: `1359DA1B-D90A-41EA-B45B-2399D34F144A`
- Device/runtime: iPhone 16, iOS 26.5 (23F77)

The UUID was appended to both pending and owned manifests before booting. The
runner used only that UUID, bounded launch-services polling to 40 attempts with
four-second command alarms, emitted an explicit xcresult summary, and archived
the exact UUID. Final inspection confirmed the UUID/name absent, both manifests
zero bytes, and the workspace-local `DerivedData`, xcresult bundle, and test
log absent.

Two preliminary setup UUIDs (`6D368565-D590-4E66-8B85-075151ABF255` and
`E181FEF9-9B5B-450E-877F-E0DC3DC8018B`) were created before an inline zsh
regex-lifecycle error, then each was name/UUID-verified and directly deleted.
A third recorded UUID (`8F4B5A59-D611-4CF1-8BFC-B12AC65EF1FC`) completed its
guarded cleanup before the tool session returned a result summary; it was also
absent before the final run. No shared or unknown simulator was touched.

## Reusable skill candidate

Add a cross-parser fixture-matrix pattern to the migration/validation guidance:
one declarative JSON mutation matrix, shared base documents and bytes, and
language-specific expected rejection categories. This preserves parity without
duplicating independently authored malformed packages.
