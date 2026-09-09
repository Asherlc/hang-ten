# Task 5 implementation report

## Scope and result

Implemented the transitional Swift v1/v2 package loader and typed presentation
media contract. Legacy v1 packages remain readable and are normalized into
typed raster media. V2 packages decode logical holds plus either raster-owned
geometry or hash-bound model media. Model packages are rejected if they mix any
raster presentation into the package.

## Files changed

- `HangTen/Models/BoardPackageStore.swift`
  - dispatches on optional `schemaVersion` while retaining the v1 loader;
  - independently decodes closed v2 media, derivation, display, descriptor,
    node, hold, and bounds documents;
  - verifies exact typed assets, model/descriptors as regular readable files,
    raster PNG dimensions only for raster media, and exact USDZ SHA-256 with
    `CryptoKit`;
  - rejects mixed model/raster packages, non-raster derivation, malformed
    cameras, unknown fields/tags, invalid descriptor vectors and roles,
    duplicate nodes, and inventory drift;
  - adds presentation asset and descriptor URL routing.
- `HangTen/Models/TrainingModels.swift`
  - adds `BoardRasterMedia`, `BoardModelMedia`, `BoardPresentationMedia`, model
    descriptor/display value types, and `BoardHold.resolvedFrame(in:)`;
  - rounds descriptor-derived extents to the descriptor's nine-decimal
    precision at the resolver boundary;
  - makes every loaded presentation carry typed media.
- `HangTenTests/BoardPackageStoreTests.swift`
  - adds transitional model/raster acceptance and model-package rejection
    coverage;
  - updates the legacy normalization assertion to inspect typed raster media.
- `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`
  - adds a deterministic model board, descriptor, model bytes, and matching
    SHA-256 fixture.

## TDD evidence

The first production change named by the focused test was adding typed media,
descriptor-backed frame resolution, and typed URL routing. Before production
edits, the focused command was run:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenTests/BoardPackageStoreTests/testStoreLoadsV2ModelAndKeepsV1PackageReadableDuringTransition
```

RED result: build/test failed at Swift compilation for the expected absent
interfaces: `BoardPresentation.media`, `.model`, `BoardHold.resolvedFrame`,
`presentationAssetURL`, and `presentationDescriptorURL`.

After the initial implementation, the same focused test reached execution and
failed on a real precision defect: AABB subtraction produced
`0.30000000000000004` and `0.39999999999999997`. The resolver was changed to
round derived extents to nine decimal places. The focused command then exited
0.

The first complete group run exposed one legacy expectation that compared a
loaded presentation against the old media-less value. That expectation was
updated to assert the new typed raster normalization explicitly.

Final verification command:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenTests/BoardPackageStoreTests
```

Final result from `xcresulttool get test-results summary`: 83 passed, 0 failed,
0 skipped, result `Passed`. The build emitted existing project warnings about
an always-run script phase and an actor-isolation conformance in
`AppStoreTests.swift`; there were no Task 5 compile or test failures.

Cheap structural verification also passed:

```sh
rtk git diff --check
rtk proxy jq empty HangTenTests/Fixtures/BoardPackageValidationFixtures.json
```

## Fixture coverage

- v2 model loads without treating non-PNG model bytes as an image;
- v1 remains readable and is normalized into `BoardRasterMedia`;
- v2 raster geometry resolves from `media.holdGeometry` and unions pieces;
- stale USDZ hash and missing descriptor are rejected;
- extra body node, missing descriptor hold, duplicate node ID, invalid node
  role, invalid fixed-size vector, and unknown descriptor field are rejected;
- unknown media tag and derived/inverted model media are rejected;
- model plus raster presentation is rejected at package level;
- empty raster hold ownership is rejected;
- zero-vector model camera is rejected.

## Interfaces and decisions

- V2 logical holds have empty legacy geometry/presentation compatibility state;
  their canonical render/picking/frame source is presentation media. The v1
  loader temporarily retains its existing hold fields for transition safety,
  while also adapting those paths into typed raster media. Task 6 can remove
  v1 acceptance and the compatibility state after all packages are converted.
- `presentationImageURL` remains as a raster-only compatibility API and returns
  `nil` for model media. New consumers use `presentationAssetURL` and
  `presentationDescriptorURL`.
- Descriptor hashes bind the exact model bytes. Descriptor AABBs supply logical
  frames; no spatial values are copied into `board.json`.
- Raster image decoding is discriminator-gated. Model assets receive only
  regular-file/readability and descriptor hash validation in this loader.

## Simulator ownership and cleanup

- Name: `Hang Ten Paseo shaky-rat Review`
- UUID: `AFA29EA3-547E-4BE0-B5C1-0BE8E3DDABD5`
- The UUID was written first to `.context/paseo-pending-simulators`, then to
  `.context/paseo-owned-simulators`, before boot or XCTest.
- All XCTest destinations used the exact UUID; `booted` was never used.
- Cleanup used
  `PASEO_WORKTREE_PATH="$PWD" scripts/paseo-resource-cleanup.sh archive`, then
  removed only this task's `.context/DerivedData`.
- Verification: `simctl list devices` no longer contains the UUID, both
  manifests are empty, and `.context/DerivedData` is absent.

## Commit

Commit message: `feat: load transitional typed board media`.
The final immutable commit hash is reported to the controller after commit,
because embedding a commit's own hash in a file inside that commit is
self-referential.
