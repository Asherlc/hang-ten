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

## Stable surface lifecycle

The virtual-camera variant reproduced the blank Pro map locally. Its
`map-virtual-pro-app.log` records scene attachment followed by repeated
load/disappear events; selecting virtual mode alone did not resolve the fault.
The container was `Group`, so its `.task` and `.onDisappear` modifiers apply
to the changing placeholder/model children. Replacing the placeholder can
therefore cancel the load or run the disappearance handler that clears the
just-loaded scene. Apple explicitly documents this modifier distribution:
https://developer.apple.com/documentation/swiftui/group

The surface now uses a persistent `ZStack`; lifecycle modifiers belong to the
surface container across loading/ready/unavailable state changes. Actual
navigation disappearance still clears the model.

The long failed visual wait also exposed a sampler crash when XCTest returned
nonfinite or empty frames: the retained runner crash report identifies a
NaN-to-Int conversion in `modelBodySampleCount`. Sampling now rejects missing,
nonfinite, empty, and out-of-screenshot viewports as zero visible-body samples.
This preserves the visibility threshold and timeout while preventing a stale
accessibility snapshot from crashing the test runner.

The stable-container build and all eight map UI cases passed, including
Pro and Evo rendered-body checks, physical picking, orbit and canonical reset,
and the four Owl map/layout cases. The xcodebuild invocation finalized with
exit zero. Results are retained in `map-lifecycle-shard.xcresult` and its log.
Additional picker and three independent Pro repetitions are recorded in
`map-lifecycle-picker` and `map-lifecycle-repeat-*` artifacts as they complete.

## CI follow-up: DoorMount reset tap and unit timeout

Run `36654455929` passed Pro and Evo after the lifecycle change, along with
the purchase/settings/workout shard and Python checks. The board shard ran
21 UI cases with one failure: DoorMount's post-orbit physical reset tap.
The selected contact remained present, but its projected center stayed
10.33 points to the right of the canonical frame. The screen recording
also retained the orbit pose after the tap. Selection remaining present
does not establish that the second physical tap hit anything.

The synthesized event records the reset tap at `(328.413, 261.867)` points.
The existing `0.82, 0.55` offset biases the tap toward the pocket's right rim.
The accessibility overlay supplies a fixed 44-point target rather than actual
pocket bounds, so that offset adds 14.08 horizontal points irrespective of
the pocket's visible width.
A projected-center reset was tested as a candidate, but failed in the combined
11-case run. It was rejected. DoorMount's original initial surface point,
original drag direction, and `0.82, 0.55` reset offset are retained.

Native diagnostic runs found agreement between manual and RealityKit contact
projection (under 0.12 points for the measured DoorMount pose) and native hits
at the projected center. These measurements do not establish hit delivery at
another screen point. Removing the per-update virtual-camera assignment did
not fix a callback-free initial tap and was also rejected. The diagnostic
runs additionally reproduced an Evo initial tap with no targeted callback;
a later run delivered the expected callback. Source-hull containment alone
cannot establish the runtime collider or gesture result.

The completed screenshot comparisons exposed an assertion race. Selection
could change the hold label while the captured model still had its previous
highlight. That delayed material update could satisfy pixel inequality after
orbit, and the projected camera could reset before the rendered frame did.
The test now establishes visible body geometry before selection, waits for
the selected surface's rendered highlight before recording the canonical
reference, and requires restoration of that rendered reference after the
single physical reset tap. Landscape also requires visible body geometry.
These are bounded waits for visual conditions, with the original physical
interaction and navigation preserved.

A DoorMount diagnostic run with rendered-selection synchronization showed a
correct highlight, visible geometric orbit, and an RGB-identical canonical
reset, with native projected X `270.157 -> 280.286 -> 270.157` and camera
revisions `2 -> 3 -> 4`. A subsequent run passed with the original initial
surface point as well. No proposed snapshot-based production invalidation
change was applied. Final validation removes temporary native projection,
entity-hit, callback, and parameter tracing. The local SDK remains 27.0
versus CI's 26.5; CI verification remains necessary.

The sampling helper uses saved screen geometry because asking XCTest for a
RealityView coordinate's `screenPoint` can fail even while the hosted view is
queryable. Its sampling window includes the visible pocket rim, and rejects
invalid crops while polling instead of recording an intermediate assertion
failure. The corrected sampling run passed Pro/Evo's portrait selection, orbit, and
rendered canonical reset. Its landscape visibility assertions failed. A live
simulator screenshot (`live-landscape-sampling.png`) confirmed that Pro's map
was actually blank after the long wait, independently of the sampler. The
landscape sampler also required using the normalized screenshot's scale,
because Springboard's accessibility width can remain in portrait orientation.

The next isolated candidate makes `BoardDetailMapSizeModifier` a single
modifier chain with an optional width limit. Its previous nil/non-nil height
branches replaced the content hierarchy when compact-height metrics arrived
or orientation changed. The candidate preserves the fitted-map accessibility
node and the compact width limit while keeping the model surface's structural
identity stable. Camera, model geometry, contact binding, and loader behavior
are unchanged. The trace-free focused run passed both Evo and Pro, including physical
selection, rendered highlight, visible orbit, exact rendered canonical reset,
and visible landscape body. The first complete affected suite passed ten of
eleven cases, including all five other Batch05 boards and their landscape
checks. Pro failed its initial physical selection. Its retained synthesized
event tapped (183.5535, 247.5154), while its live target frame was
(179, 225.3, 44, 44), with center (201, 247.3). The screenshot places the
old normalized fixture on the gap beside the narrow center pocket after
main’s default viewing-angle change. Pro now picks the live contact center;
a separate orbit-start argument preserves the original drag trajectory.
This keeps one physical initial tap and one physical reset tap, with no
retries. The subsequent trace-free complete suite passed nine of eleven cases.
DoorMount’s physical reset did not return its projected center; Pro’s
selection succeeded, but reset did not advance camera revision 3 and the
rendered board remained orbited. The old three-point AX tolerance masked
that Pro failure; the new exact rendered-reset assertion caught it.

A focused temporary native-query run exposed an instrumentation confound:
publishing the entire changing hit-query string through SwiftUI changed
synchronization. A second, logging-only run kept the original short AX
diagnostic and passed both DoorMount and Pro, with two fresh native callbacks
per board, rendered canonical restoration, and landscape geometry. Native
queries also show Pro’s former fixed fixture misses while its live center
hits. These results establish intermittent native interaction/presentation
behavior, not a proved camera defect. All temporary hit-query and callback
tracing was removed before the delivery build. No snapshot invalidation,
camera-mode experiment, retries, weakened reset checks, or production
picking changes were retained.

Local builds use SDK 27.0 with Simulator runtime 26.5; CI builds use SDK 26.5.
The trace-free integrated build and full unit suite passed: 1,245 tests,
three skipped, zero failures. Python’s integrated suite passed 437 tests;
the delivery lock validates 53 models and 122 authored files. CI on the
pushed branch must supply the remaining interaction validation. The local trace-free UI failures are retained and
are not described as a full-suite pass.

The retained before/after landscape screenshots show the actual blank map
and the same board rendered with its selected contact:

![Pro landscape before](../pr-screenshots/yy-verticalboards/ci-map-pro-landscape-before.png)

![Pro landscape after](../pr-screenshots/yy-verticalboards/ci-map-pro-landscape-after.png)

The unit shard's sole failure was
`AppStoreTests.testFailedSessionPersistenceDoesNotConsumeCredit`: a two-second
expectation expired while the test took 19.658 seconds. Its simulator app log
shows a HealthKit connection activated at `04:56:32.268` and cancelled at
`04:56:51.916`, matching the stalled interval. This supports investigating a
transient simulator stall; the exact blocking call is not established. A
single targeted rerun was requested after the full workflow completed;
replacement unit job `109756688319` passed at `06:14:36Z` on the unchanged
commit. A subsequent local diagnostic launch also stalled in
`HealthKitService.authorizationState`; its process sample identifies
`HKHealthStore.authorizationStatusForType` waiting for a synchronous XPC
reply on the main thread (`AppStore.init`, line 93). That launch never
reached a board interaction and was cancelled with exact-resource cleanup.
This corroborates the environment hypothesis without establishing that the
original unit failure blocked in the same call. No expectation timeout or
production persistence code was changed. The original logs, result bundle,
exported diagnostics, screenshots, and synthesized events are retained under
`.context/supreme-zebra-cad-validation/ci-6296-*`.

### SDK 26.5 rendering and menu-event investigation

Run `36689422401` on `119306ca3` passed Python, Swift units, and the
purchase/settings/workout shard. Its board shard ran 21 tests with five
failures: Forge retained its orbit after reset; Megalith, Natural, and Pro
retained their canonical geometry after dragging; the one-handed Left menu
selection retained Alternate hands. DoorMount and Evo passed their complete
rendered interaction sequence. Pro's independent recording corroborates the
frozen canonical pose while RealityView's diagnostic revision advances from
2 to 11. Megalith advances from 2 to 8. Active root/camera membership and AX
projection changes therefore do not certify the presented camera pose.

The Left-menu synthesized event targets Springboard PID 4670, while Hang Ten
is PID 57460. The recording shows the menu remaining open after that event.
The finite-frame helper now takes the owning application explicitly and
anchors the coordinate in that application; the menu-window workaround and
single tap remain intact. CI must establish the behavioral result.

Two read-only reviewers independently recommended one diagnostic invocation
that compares camera transforms, native projections, and engine-frame
callbacks. The temporary DEBUG trace was guarded by the existing board-review
diagnostics environment flag and wrote only logs. After retaining CI's result
bundle, attachments and 363 trace records, its state, subscription, logging,
projection helper, disappearance cleanup and class definition were removed.
No trace wiring remains in the delivered application source.

The local picker baseline and subsequent diagnostic invocation were
interrupted before their interactions because startup blocked in
`HealthKitService.authorizationState`. Owned-process samples identify the
main-thread synchronous HealthKit XPC wait; the owned daemon sample identifies
its background-task submission wait. Rebooting the exact owned simulator did
not establish a valid comparison. No permission policy, authorization state,
assertion, or retry loop was changed. CI's SDK 26.5 run must supply the
remaining evidence. Local compilation and the 22 CI-contract tests passed;
no successful local UI result is claimed for this investigation.

Run `36696460939` on diagnostic head `2512db816` passed Python and Swift
units. The application-owned Left-menu tap passed its complete test in
97.187 seconds. All six Batch05 boards failed rendered orbit checks. Their
native projections follow the changed camera transforms before and after
synchronization and in subsequent engine-frame callbacks, while their
presented geometry remains frozen. This weakens camera-math, missing-update,
and deterministic mode-rebinding explanations. The diagnostic subscription
may affect scheduling, so this run does not establish an exact internal
RealityKit fault or make the observed failure rate comparable to the prior
trace-free run.

The controlled candidate preserves normalized orbit state in gesture
callbacks, but defers the camera entity write to `frame(in:)` inside
`RealityView.update`. This submits the changed transform at the host's
synchronization boundary and lets the existing before/after detector observe
it. Unhosted callers retain immediate camera updates. The camera unit test
also verifies deferred orbit/reset leave the entity transform unchanged
until framing submits them. Camera calculations, mode configuration, native
picking, navigation, rendered assertions, and single-tap behavior are
unchanged. This candidate requires fresh trace-free CI interaction validation;
no successful rendering fix is claimed before that result.

The trace-free `dfbf13842` unit shard ran 1,245 tests with three skips. Its
sole failing case was successful session persistence: the one-second
condition wait expired before the asynchronously dispatched main-actor
completion consumed the credit (two failed assertions). The deferred-camera
unit case passed. Purchase/settings/workout UI also passed; the board shard
is still pending.

The paired persistence tests previously pumped `RunLoop.main` from a
synchronous main-actor test while the production append callback scheduled a
main-actor task. The candidate test correction suspends between condition
checks, allowing that executor to run normally. It retains the one-second
deadline, the controlled storage completion, the pre-completion zero-credit
assertion, and the final success/failure credit assertions. Credit policy and
application persistence code are unchanged. The exact CI scheduling delay is
not proved; fresh CI must validate this test correction.

Run `36699899387` completed. All six Batch05 boards failed the rendered orbit
assertion; the remaining 15 board/grip/picker cases passed. The deferred
camera-submission candidate therefore did not correct the observed failure
and was removed, including its optional model API and candidate-only unit
assertions. The previous immediate-camera behavior is restored; temporary
presentation tracing remains removed. The prepared persistence-test wait
correction is delivered separately. Rendering investigation remains open,
and auto merge remains disabled.

Two fresh read-only rendering-host reviewers agreed to a one-variable
post-failure diagnostic before another camera or hosting change. The first
proposal used root translation; the counter-review initially proposed a
material probe plus clipping A/B. They converged on root translation first,
leaving clipping and ARView comparisons dependent on the observed result.
Both exact owned reviewer agents were archived and verified.

The temporary Pro-only DEBUG probe changes the existing root's X position
once by six percent of its current model width, after the original rendered
orbit wait times out. It does not change camera state, cameraRevision,
SwiftUI state, or subscriptions. The original timeout remains the result
asserted by the acceptance test. A fixed five-second diagnostic capture
window avoids treating the Probe button's press appearance as movement.
Sparse mode/synchronization logs record any intervening camera writes, and
existing attachment logs identify host recreation. Extra camera/host/layout
activity makes attribution inconclusive. Geometry and viewpoint must be
judged separately, excluding the temporary control from pixel comparisons.

Visible displacement with a canonical viewpoint supports a camera-specific
path; displacement revealing the pending orbit supports camera-only render
invalidation. Neither movement leaves rendering versus presentation open
and selects a clip-only comparison. Failure to reproduce is inconclusive.
This is an interim investigation change, not a rendering fix. All temporary
probe state, methods, overlays, logs, launch environment and test branch must
be removed before delivery; this diagnostic head must not merge even if its
checks pass. No local UI pass is claimed.

The trace-free baseline run `36703970064` on `9e18e68b3` passed all 1,245
unit tests with three skips; the successful-session persistence test passed
in 0.021 seconds. Python and purchase/settings/workout UI passed. The board
shard ran 21 cases with six failures: DoorMount, Evo, and Natural reached
rendered orbit but failed canonical reset; Forge, Megalith, and Pro failed
rendered orbit. This preserves a fresh Pro freeze for comparison with the
post-failure root-translation probe. The baseline logs are retained, and the
diagnostic must not be interpreted as a passing acceptance run.

The final probe arm64 Simulator build-for-testing and 22 CI-contract tests
passed. Its exact DerivedData was deleted by the exit trap and deletion
verified. No local Simulator or UI execution was attempted.
