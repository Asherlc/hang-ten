# VerticalBoard delivery CI follow-up

CI run [36621669794](https://github.com/Asherlc/hang-ten/actions/runs/36621669794)
failed in `InitialWeightSetupUITests.testInlineChoicesDefaultToSkipAndKeepManualDraft`:
the bodyweight switch remained off after a synthesized thumb tap on iOS 26.5.
The retained XCTest attachment showed a switch frame of `(303, 423, 61, 28)`
and an actual tap at `(321.3, 437)`, inside the off-state thumb. The recording
showed an unobstructed native switch. The unchanged test reproduced the same
assertion failure on a workspace-owned iPhone 17 Pro iOS 26.5 simulator.
Its runner was stopped after recording the assertion because result finalization
stalled; that red invocation did not exit normally.

An initial short drag also failed on repetition: XCTest used its default
500-pixel-per-second velocity with a 0.1-second press and no endpoint hold.
The interim fix in `d176de308` made both tests drag the thumb from normalized
`(0.3, 0.5)` to `(0.8, 0.5)` with a 0.5-second press, explicit slow velocity,
and a 0.2-second endpoint hold. The existing switch-value assertion, manual-draft
persistence checks, and purchased-workout weight-summary checks remain intact.
Production UI behavior and board geometry are unchanged.

Main's Whetstone migration (`b9d05c9e5`) was integrated while correcting CI.
Both native-model test functions, both sets of generated-manifest ignores,
and all four migrated package entries are retained. The combined delivery lock
is `ec63a290383db0b18f3c2604908325258494f3be90a45464da6bdfaff4b623fa`;
verification passed for 53 models and 122 files. The three VerticalBoard source,
descriptor, and USDZ bytes remain unchanged.

Validation on the combined branch:

- Rebuilt the iOS Simulator app and test targets successfully.
- All three `InitialWeightSetupUITests` and the purchased manual-weight summary
  test ran twice each: eight executions, zero failures.
- Python CAD/model/package suites: 492 passed, 14 skipped, 24 subtests.
- Full merged Swift unit suite: 1,235 tests, three skipped, zero failures.
- Delivery verification: 53 models, 122 files, exact locked identity confirmed.
- Both CI-fix simulators were shut down/deleted, ownership manifests consumed,
  and workspace DerivedData removed; deletion was verified against simulator
  inventory.

Local CI logs and result bundles are retained under
`.context/supreme-zebra-cad-validation/ci-fix-*`.

## Subsequent main integration

Main commit `d0e4e9519` updated the same tests with a fixed Original Grindstone
raster fixture and explicit fixture assertions, an initial off-state assertion,
a narrow switch-frame assertion, and a separate visible-label interaction test.
It also added a tap handler to the visible label. The merge retains those main
changes, including the normal `bodyweight.tap()` interaction, in place of the
interim drag. Both UI test files match main exactly; none of its assertions are
removed. Board geometry and the delivery lock are unchanged.

The merged build passed. All four weight-setup tests and the manual-weight
purchase-summary test passed twice each (ten executions, zero failures).
The full Swift unit suite passed 1,241 tests, three skipped, zero failures.
The exact post-test `simctl diagnose` collectors stalled after successful
testcase completion and were stopped; both xcodebuild invocations finalized
successfully with exit zero. Logs and result bundles are retained as
`.context/supreme-zebra-cad-validation/main-integration-*`.
The isolated simulator was deleted, ownership manifests consumed, and
DerivedData removed; deletion was verified.

## Distinct ODR project registrations

Post-merge review identified that Whetstone and VerticalBoard First both used
the `D100...31` build-file and `D200...31` file-reference identifiers. First now
uses the unused `...34` pair consistently in both definitions, its group entry,
and its Resources phase entry; Whetstone retains `...31`.

The existing ODR inventory test now rejects duplicate project object
definitions. It failed against the colliding identifiers before the fix.
All 29 package-staging tests passed after the fix. `plutil` validation and
`xcodebuild -list` passed; the parsed project confirms distinct file references,
resource-phase membership, paths, and ODR tags for both packages.

## Explicit non-AR camera for board maps

CI run `36644927341`, map-batch05-b job `109665698938`, failed the
Pro rendered-body check after its contact controls appeared. Decoding the
retained screen recording with FFmpeg confirms persistent blank geometry;
contact accessibility alone is not evidence that RealityKit renders the mesh.
The other Forge, Natural, and Owl cases in that shard passed.

The view added its authored `PerspectiveCamera` without requesting virtual
camera mode. Apple documents AR as the iOS default, with non-AR fallback when
the device camera or AR is unavailable:
https://developer.apple.com/documentation/realitykit/realityviewcameracontent
https://developer.apple.com/documentation/realitykit/realityviewcamera/virtual
Local diagnostics confirmed `RKARCameraEntity` in that fallback configuration.
A rapid-navigation baseline also reproduced a physical-picking failure.

RealityView initialization now explicitly selects `.virtual` before adding
the model and authored camera. This corrects the configuration gap without
changing the loader, geometry, materials, navigation, or visual thresholds.
The exact intermittent CI rendering cause is not independently established;
the new CI result remains the decisive validation. Opt-in DEBUG lifecycle
logging and a failure screenshot with viewport/sample diagnostics preserve
evidence if rendering still fails.

Local builds use SDK 27.0 with Simulator runtime 26.5; CI uses SDK 26.5.
An unrelated local startup deadlock was sampled in HealthKit and its simulator
background-task service. Only the owned simulator service was stopped to
allow board validation; no production HealthKit code was changed.

The changed build-for-testing succeeded. Evo passed its rendered-body, physical
picking, orbit, canonical-reset, and landscape assertions with explicit
virtual mode. Full shard and repeated Pro checks continue in the retained
`map-virtual-*` logs and result bundles under the workspace-owned validation
directory; these additional runs are not claimed complete here.
