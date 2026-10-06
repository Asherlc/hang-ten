# Dead-code audit — 2026-10-05

The audit started from the latest `origin/main`,
`4ed88fc3daa518d74ba054be4bd043d93464e95b`. It covered the Swift application,
its test callers, Python tooling, and shell entry points. Generated assets and
third-party dependencies were excluded from authored-code findings.

## Confirmed removals

- The superseded plan filters and their presentation model, the retired free-workout
  draft-to-plan builder, the old standalone workout clock, and the old timeline
  live-edit API. The current workout browser, session state, free-workout log,
  and legacy draft migration remain the active implementations.
- Uncalled initializers, forwarding methods, routine lookup aliases, rendering
  helpers, error cases, color constants, and former sloper metadata types.
- An unused feature-flag interface, an undisplayed migration-notice flow, stored
  values with no reader, and unused parameters in private methods.
- Redundant Bluetooth and settings dependencies in `AppStore`. Removing them
  also eliminates the extra default Bluetooth transport it constructed.
- The unused Python helpers `flattened_shape_bounds` and `_is_phase2_keep`,
  unused imports, and unused local variables.
- Six unused local bindings/computations reported by the Swift test compiler.
  Their assertions and fixture setup remain intact.

Climbro and Entralpi have protocol research tests but no live transport. Their
reference adapters/parsers now compile only into `HangTenTests`. Their research
coverage and persisted profile identifiers remain available. Tests solely for
retired implementations were removed; active browser, workout, migration,
Bluetooth, and rendering tests were retained.

## Reachability review

Periphery 3.8.0 consumed the compiler index produced by Xcode 27.0's
`build-for-testing`. Both test modules were included as callers. A second scan
excluded tests to identify retired features kept alive only by their own tests.
Declarations used for dependency injection, fixtures, or algorithm diagnostics
were reviewed separately from those retired features.

The initial scan reported 147 candidates. Synthesized equality, decoding,
SwiftUI projected bindings, and ARC resource ownership explained some reports.
The configuration retains serialized properties, equality properties, and
previews. A separate scan without equality retention verified that its remaining
reports were stored equality/cache-key fields rather than unused computed code.
Four narrow source annotations explain the navigation bindings and ODR owners.

Xcode `clean` preserves compiler index units, which can carry removed
declarations from older builds. The final build and analysis use an initially
empty DerivedData directory containing only the current arm64 application and
test units.

Python review combined Ruff's unused-import/local checks, Vulture, AST reference
inspection, and a search for CLI entry points and dynamic framework hooks.
Unused callback parameters and Blender/FreeCAD registration side effects were
kept where their external contracts require them. Shell functions and scripts
were checked against their entry points and callers.

## Validation

- Python package, model, CAD helper, and script contract suites: **970 tests and
  7 subtests passed**.
- Ruff checks `F401,F811,F821,F841,RET505,RET506,RET507,RET508`: passed.
- Fresh Swift `build-for-testing`: passed.
- Strict Periphery scan: **zero findings**. The scan without equality retention
  reported 34 stored equality/cache-key fields and no unused functions or
  computed properties.
- SwiftLint duplicate-condition and unused-closure-parameter checks: passed.
- Final simulator regression: **1,407 unit tests, three skipped, zero failures**.
- **Three UI tests passed**: workout browsing/detail return, combined filter
  apply/cancel/clear behavior, and starting the minimal free-workout log.
- The isolated camera perspective/viewport framing test passed. The isolated
  retry of the rendering frame-delivery timeout reproduced the failure.
- Rebuilt after the final test-local cleanup; **six focused model-loading,
  framing, and package-validation tests passed**. The rebuilt test files have
  no unused-local compiler warnings.

Broader simulation validation exposed two 30-second frame-delivery timeouts:
`BoardModelRealityTests.testLiveScenePausesThenPublishesAcceptedSettledFrame`
and `LiveRopeControllerTests.testReduceMotionDeliversOnlyAcceptedSettledFrame`.
Each timeout produced three assertion failures. These tests were not weakened
or changed to make validation pass. The full numerical simulation run was
interrupted during `ClavelliumRopePhysicsTests.testDeterminismAndHalfTimeStep`.
The regression run excludes `BoardModelRealityTests`,
`ClavelliumRopePhysicsTests`, `LiveRopeControllerTests`,
`RopeDynamicsSolverTests`, and `RopeThreadedSeedTests`; its passing result is
limited to that explicit scope. The broader run completed 69 rendering tests,
including 68 passes and the first timeout, before interruption. Simulation math
was not changed by the cleanup. The timeout cause is unconfirmed.

The workspace-owned simulator and both DerivedData directories were deleted
after validation, with deletion verified.
Xcode stalled in simulator diagnostic collection after the successful regression
cases finished. The exact diagnostic child belonging to this test command and
simulator was stopped; Xcode then completed with `TEST EXECUTE SUCCEEDED`.
The isolated follow-up disabled verbose diagnostic collection and exited normally.
Runtime assets came from the source-identical main CI artifact
[`37396674659`](https://github.com/Asherlc/hang-ten/actions/runs/37396674659);
67 source hashes and 156 output hashes were verified before staging them.
Board source geometry and the audited training-plan resource were not edited.

## Repeat the Swift check

Use Periphery **3.8.0** and prepare runtime assets through the repository's
normal workflow. Build all targets into a fresh index directory; reusing an old
index can retain declarations removed from earlier source revisions.

```sh
audit_owner=$(basename "${PASEO_WORKTREE_PATH:-$PWD}")
audit_data=".context/$audit_owner-dead-code-index"
rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Debug -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath "$audit_data" ARCHS=arm64 ONLY_ACTIVE_ARCH=YES \
  COMPILER_INDEX_STORE_ENABLE=YES CODE_SIGN_IDENTITY=- build-for-testing
rtk proxy env PERIPHERY_BIN=/path/to/periphery-3.8.0 \
  bash scripts/audit-swift-dead-code.sh "$audit_data"
```

The command fails on findings and saves its JSON report under the current
workspace's `.context` directory. Review new reports against framework entry
points and serialized/equality contracts before deleting code. Static
reachability cannot prove every possible runtime configuration.
