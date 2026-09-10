# Task 5 fix round 1 report

## Outcome

All three Important review findings were reproduced and fixed.

- Native descriptor rounding now matches canonical Python `round(value, 9)`
  ties-to-even behavior. A fused multiply-add residual distinguishes values
  which land on a scaled floating-point midpoint only because multiplication
  rounded, while values too large to scale are returned unchanged (their ULP
  already exceeds nine-decimal precision). Non-finite inputs still fail.
- `BoardHold` now stores logical metadata only. Schema-v1 geometry and
  presentation ownership are held in a loader-private adapter until they are
  normalized into `BoardPresentation.media`. Rendering, selection, position
  inventory, marker placement, and target-resolution geometry use typed media
  and `resolvedFrame(in:)`.
- Descriptor `holds` member names are scanned from the raw JSON bytes before
  `JSONDecoder` dictionary conversion, then required to be sorted.

## Review verification

1. Confirmed. Python derives the cited `0.1...0.100000023` center as
   `0.100000011`; the former Swift multiply/`.rounded()` path derived
   `0.100000012`. Multiplying a finite value near `1e300` by `1e9` also
   overflowed and caused a false rejection.
2. Confirmed. `BoardHold` stored `geometry`, cached `frame`, and
   `presentationID`; the v2 initializer filled empty/zero sentinel values and
   several consumers still read them.
3. Confirmed. Python compares raw mapping iteration order against sorted keys,
   while Swift decoded directly to a dictionary and lost source member order.
   `JSONDecoder` keyed-container `allKeys` is not a source-order API.

## TDD evidence

Simulator: `Hang Ten Paseo shaky-rat Review`, UUID
`5B46ABB7-5D73-4298-811B-EF63E9618341`. Every XCTest destination used this
exact UUID and `.context/DerivedData`.

Focused command:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=5B46ABB7-5D73-4298-811B-EF63E9618341" \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenTests/BoardPackageStoreTests/testModelPresentationContentUsesTypedMediaHoldInventory \
  -only-testing:HangTenTests/BoardPackageStoreTests/testStoreAcceptsCanonicalTieToEvenDescriptorCenter \
  -only-testing:HangTenTests/BoardPackageStoreTests/testStoreHandlesFiniteScaleOverflowAndRejectsNonFiniteDescriptorValues \
  -only-testing:HangTenTests/BoardPackageStoreTests/testStoreRejectsUnsortedDescriptorHoldMembers
```

RED: status 65 after 175.101 seconds; all four named regressions failed for the
expected old behavior. GREEN: status 0; all four passed.

Complete required group:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=5B46ABB7-5D73-4298-811B-EF63E9618341" \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenTests/BoardPackageStoreTests
```

GREEN: status 0, 87 passed, 0 failed, 0 skipped.

Downstream verification necessitated by the logical-only hold change:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=5B46ABB7-5D73-4298-811B-EF63E9618341" \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenTests/WorkoutActivityRecordingTests
```

GREEN: status 0, 35 passed, 0 failed, 0 skipped. One initial run exposed a
hand-built test board that supplied frames only through the retired hold API;
its frames were moved to typed raster presentation media.

A non-required `BoardSourceBoundaryTests` probe found one unrelated existing
failure: the source audit flags `BoardRasterMedia(assetPath: "", ...)` in
`TrainingModels.swift`. `git show HEAD` proves that exact literal predates this
fix. The directly affected physical-path boundary assertion was updated.

## Resource lifecycle

The cleanup trap was installed before simulator creation. The simulator UUID
was appended to `.context/paseo-pending-simulators` and
`.context/paseo-owned-simulators`; the archive cleanup owns exact-UUID deletion.
Final deletion verification is recorded below after final XCTest.

Archive cleanup exited 0. A post-cleanup `simctl list devices` search returned
no matching name or UUID; both ownership manifests were 0 bytes; and
`.context/DerivedData` did not exist.

Setup transparency: an initial shell attempt created UUID
`5B4DF924-CAC1-4111-BC0F-EA95141B9CA4` under the exact same required name, but
ran no XCTest. Its already-booted-state error immediately invoked archive
cleanup, and its absence was verified before the test simulator above was
created. Both UUIDs are deleted; only `5B46ABB7-5D73-4298-811B-EF63E9618341`
was ever used as an XCTest destination.

## Commit

Commit message: `fix: align Swift board media validation`.

The commit hash is the Git object containing this report; embedding that hash
inside the same object is not possible because it changes the object hash.

## Reusable migration rules proven

- Never use keyed-decoder iteration to enforce canonical JSON member order;
  inspect raw bytes before dictionary conversion.
- Decimal-place parity across languages requires matching tie behavior and
  guarding the scaling operation itself, not merely checking the input for
  finiteness.
- Logical hold inventories should not carry sentinel spatial values. Resolve
  membership, geometry, and frames from the selected typed presentation.
