# Task 5 fix round 2 report

## Outcome

Closed the three remaining Swift media-parity gaps without changing the schema:

- Nine-decimal rounding now returns a finite `Double` unchanged once its ULP
  exceeds the decimal quantum, avoiding the lossy multiply/divide path for
  `1e20` and all larger-precision values. Values below that transition retain
  the existing FMA-assisted ties-to-even implementation. Descriptor validation
  remains finite-only and normalized face bounds remain restricted to `0...1`.
- Removed both `BoardHold` compatibility initializers that accepted and
  discarded geometry, frame, presentation, and legacy display arguments.
  Compiler-discovered spatial test fixtures now place geometry in typed
  `BoardRasterMedia`; metadata-only fixtures construct logical holds directly.
- Raw descriptor member-order scanning now accepts leading JSON whitespace,
  preserves JSONDecoder-backed string escape handling, and limits recursive
  container descent to 128 levels. It still validates the raw `holds` member
  order before dictionary conversion and rejects unsorted maps.

## Review counterexample verification and TDD

All XCTest commands used simulator UUID
`369023CB-2F59-4BCA-BC75-12EEEAD59063` and
`.context/DerivedData`.

Before production edits, this focused command ran the cited target-substitution
case plus the new rounding and whitespace regressions:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=369023CB-2F59-4BCA-BC75-12EEEAD59063" \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenTests/BoardTargetSubstitutionTests/testUntaggedThreeFingerPocketSubstitutionKeepsOneHoldPerHand \
  -only-testing:HangTenTests/BoardPackageStoreTests/testDescriptorRoundingMatchesPythonAcrossDoublePrecisionTransition \
  -only-testing:HangTenTests/BoardPackageStoreTests/testStoreAcceptsDescriptorWithLeadingAndTrailingJSONWhitespace
```

RED: exit 65. All three named tests failed for the intended old behavior. The
rounding table includes the cited midpoint, the `2^22`/`2^23` precision
transition, `1e20`, `1e300`, and `Double.greatestFiniteMagnitude`. The existing
finite/non-finite descriptor fixture continues to prove that `1e300` is
accepted and `1e999` is rejected.

The bounded-scanner regression was then enabled separately. RED: exit 65 at
test compilation because `BoardPackageJSONMemberOrder` was private and exposed
no explicit maximum-nesting contract. The test also includes an escaped quote
and closing brace before `holds`, so a broken string scanner cannot satisfy it.

After removing the silent overloads, repeated `build-for-testing` runs exposed
every remaining source caller. The compiler identified only test fixtures in
`BoardTargetSubstitutionTests`, `WorkoutActivityRecordingTests`,
`WorkoutTimelineTests`, `WorkoutSegmentTests`, `PlanStorageTests`, and
`CustomRoutineStoreTests`. Spatially meaningful fixtures were migrated to
typed raster presentation media; callers that only exercised logical metadata
stopped supplying irrelevant spatial/display arguments. A final
`build-for-testing` compile probe emitted no Swift errors.

The focused GREEN command covered seven regression methods: the Python-rounding
table, canonical midpoint, finite/non-finite validation, padded descriptor,
bounded/escape-correct scanner, unsorted hold map, and the cited target
substitution. It exited 0.

## Verification

Required affected suites were run together:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=369023CB-2F59-4BCA-BC75-12EEEAD59063" \
  -derivedDataPath .context/DerivedData \
  -resultBundlePath .context/task5-fix2-tests.xcresult \
  -only-testing:HangTenTests/BoardPackageStoreTests \
  -only-testing:HangTenTests/BoardTargetSubstitutionTests \
  -only-testing:HangTenTests/WorkoutActivityRecordingTests
```

`xcresulttool get test-results summary` reported `Passed`: 188 passed, 0
failed, 0 skipped, on the exact owned simulator.

The other suites containing compile-migrated fixtures were also run:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=369023CB-2F59-4BCA-BC75-12EEEAD59063" \
  -derivedDataPath .context/DerivedData \
  -resultBundlePath .context/task5-fix2-migration-tests.xcresult \
  -only-testing:HangTenTests/PlanStorageTests \
  -only-testing:HangTenTests/CustomRoutineStoreTests \
  -only-testing:HangTenTests/WorkoutTimelineTests \
  -only-testing:HangTenTests/WorkoutSegmentTests
```

The second result summary reported `Passed`: 168 passed, 0 failed, 0 skipped.
Both runs emitted only existing project warnings for always-run build phases and
the test environment's empty Sentry DSN.

Static checks passed:

```sh
rtk git diff --check
rtk env SRCROOT="$PWD" scripts/verify-board-source-boundary-manifest.sh
```

A source search found no remaining `BoardHold` compatibility declaration that
accepts discarded `geometry`, `frame`, `presentationID`, `shortLabel`, or
`detail` arguments.

## Simulator ownership and cleanup

- Name: `Hang Ten Paseo shaky-rat Review`
- UUID: `369023CB-2F59-4BCA-BC75-12EEEAD59063`
- Runtime/device: iOS 26.5, iPhone 17 Pro
- The exact UUID was validated, appended to
  `.context/paseo-pending-simulators`, then appended to
  `.context/paseo-owned-simulators` before boot or XCTest.
- Every simulator and XCTest command used the exact UUID; `booted` was never a
  destination.
- The installed EXIT/INT/TERM lifecycle invoked
  `PASEO_WORKTREE_PATH="$PWD" scripts/paseo-resource-cleanup.sh archive` and
  removed only this task's exact workspace-local generated artifacts.
- Final verification found neither the UUID nor the exact name in
  `simctl list devices`; both manifests are 0 bytes; `.context/DerivedData`,
  both result bundles, the lifecycle script, and the temporary Swift module
  cache are absent.

## Reusable migration rules proven

- Before decimal scaling, return a finite value unchanged when its own ULP is
  wider than the rounding quantum; otherwise an unnecessary round trip can
  move canonical large values to an adjacent Double.
- Never retain overloads that accept spatial package data without storing it.
  Removing them turns forgotten typed-media migrations into compiler errors.
- Hand-built spatial fixtures must mirror production ownership: logical holds
  in `TrainingBoard.holds`, geometry in `BoardPresentation.media`.
- Enforce deterministic JSON object ordering from raw bytes, not keyed-decoder
  iteration, and bound every recursive parser even when a strict decoder runs
  afterward.

## Commit

Commit message: `fix: close Swift media parity gaps`.

The immutable commit hash is reported after commit; embedding a commit's own
hash in the file contained by that commit would change the hash.
