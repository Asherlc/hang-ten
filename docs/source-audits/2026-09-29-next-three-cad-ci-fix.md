# Next three native CAD boards: CI follow-up

CI run [36629793095](https://github.com/Asherlc/hang-ten/actions/runs/36629793095) failed in `InitialWeightSetupUITests.testInlineChoicesDefaultToSkipAndKeepManualDraft`: the Add bodyweight switch remained off after a synthesized thumb tap on iOS 26.5. The retained recording showed an unobstructed switch. XCTest reported the named switch frame `(303, 423, 61, 28)` and a tap at `(321.3, 437)`, with its value still `0`. Python, Swift unit tests, map batch05-b and paywall CI jobs passed.

Integrated origin/main at `d0e4e9519`, including its existing correction for the same weight-flow failure. Both UI test files retain main’s normal switch tap, explicit off-state checks, narrow frame assertion, label interaction coverage and fixed Original Grindstone fixture. Comments now describe that fixture as a native model bundled in DEBUG simulator builds. All assertions remain intact. Main’s Whetstone package, ODR registration and native regression coverage were preserved together with this batch’s three packages.

All nine source/model/descriptor hashes for Evo, Honestone and Original Grindstone remain unchanged. Final delivery-lock integration still awaits PR524’s merge; the lock brought in from main covers its existing deliveries.

Local validation: Python CAD/model/package suites passed 492 tests, 11 optional checks skipped, and 24 subtests. Simulator build-for-testing succeeded. The local Xcode 27 / iOS 26.5 simulator attempts stalled before the UI runner launched. Bounded boot-status and screenshot probes also timed out. Both attempts were stopped and their exact workspace-owned simulators deleted by the cleanup traps; no local UI or full merged Swift runtime pass is claimed. GitHub CI uses Xcode 26.5 and will validate the pushed change.

## Follow-up after the tap correction failed in CI

Run [36645711814](https://github.com/Asherlc/hang-ten/actions/runs/36645711814) reproduced the switch failure after the normal tap. Its event attachment records `(333.5, 437)`, with the named switch still off and the parent window snapshot reporting zero/nonfinite bounds. Recording frames before and after the interaction show an unobstructed, unchanged switch. The tap synthesis took 18 seconds. The independent visible-label interaction passed.

Both weight-flow tests now use a sustained native switch drag: 0.5-second press, explicit slow velocity from normalized `(0.3, 0.5)` to `(0.8, 0.5)`, and 0.2-second endpoint hold. This is the gesture previously validated in the parent batch before main replaced it with the shorter tap. The initial off-state, enabled-state, manual draft persistence, purchase summary and separate label interaction assertions remain intact. No production or CAD geometry changes are included.

## Merge main and correct keyboard-active purchase setup

Integrated main commit `8687bd6b2` (PR522). CI run `36651684102` passed the grip-and-picker suite, but the manual-weight purchase test failed after trying to drag the bodyweight switch while the decimal keyboard was active. The later summary failure follows from the switch remaining off.

Resolved both UI test conflicts by retaining main’s tested control-targeting implementation. It enables bodyweight before focusing the decimal field, verifies the on-state after input, and uses a SpringBoard screen coordinate computed from finite, visible control bounds. This avoids the invalid parent-window bounds seen in the earlier CI attachment. Fixture comments continue to describe the Original Grindstone native model correctly. All three migrated CAD packages and contact-picking regressions are unchanged. Main’s consolidated CI jobs and contract tests are included. PR525 remains open; merging this branch into main is outside this request.

CI runner contracts and package staging: 51 tests passed after the merge. All nine source/model/descriptor hashes remain unchanged.

## Integrate main's validated switch and countdown fixes

Run [36666713400](https://github.com/Asherlc/hang-ten/actions/runs/36666713400) passed Python, Swift unit tests and all purchase/paywall tests, but failed two UI cases. The inline-weight case raised XCTest's invalid activation-point error while the screen-coordinate helper queried switch hittability. The guided-hang cancellation case could no longer find Cancel after the ten-second default hang expired during slow accessibility queries.

Merged main at `06d57f117` (PR520, including PR514). Main already corrects both failures: an accessible Add bodyweight label button toggles the same state while preserving switch-state and draft assertions; the cancellation test enters a 120-second duration and dismisses its keyboard before starting, retaining the unchecked-set and absent-rest assertions. Both UI suites passed on these fixes in [36666589397](https://github.com/Asherlc/hang-ten/actions/runs/36666589397). The merged branch still requires its own CI confirmation.

Local validation after this merge: simulator build-for-testing succeeded; all 51 CI contract and staging tests passed; all nine batch CAD delivery hashes are unchanged. The build cleanup trap removed this workspace's DerivedData. No simulator or external service was created. PR525 remains open, with no outstanding review threads. PR524 remains unmerged, so the final shared delivery-lock refresh is still pending.

## Preserve free-workout field accessibility

Run [36719288184](https://github.com/Asherlc/hang-ten/actions/runs/36719288184) passed Python, Swift unit tests, the entire boards/grips/picker suite and all paywall cases. Its only failing case was guided-hang cancellation, before the hang started: the duration field failed the finite/hittable-frame readiness check. The retained recording at 78 seconds shows the empty duration input fully visible beside the weight field; XCTest reports its identifier as the enclosing `freeWorkout.set.<UUID>` rather than `freeWorkout.set.duration.<UUID>`.

The set row now explicitly contains its accessibility children, matching the exercise card's container semantics and preserving distinct field identifiers. The cancellation test targets the duration field by its identifier prefix and uses the existing screen-coordinate helper with enabled, finite, visible bounds instead of querying XCTest's hit-point machinery. The exact 120-second entered-value assertion and the post-cancellation unchecked-set and absent-rest assertions remain intact. CAD assets and manifests are unchanged.

Local validation: simulator build-for-testing succeeded and all 51 CI contract/staging checks passed. The build trap removed the workspace's DerivedData; no simulator or external service was created. Full UI runtime confirmation is delegated to the pushed GitHub CI run because local simulator installation previously stalled under Xcode 27.

## Keyboard activation points and shallow-viewport orbit gestures

Local iOS 26.3 validation subsequently passed the focused cancellation case and all six free-workout cases (428.8 seconds). Both exact owned simulators and DerivedData were removed and deletion verified. Run [36726227836](https://github.com/Asherlc/hang-ten/actions/runs/36726227836) passed Python and Swift unit tests, but exposed the same invalid XCTest activation-point error on the keyboard Done button. The cancellation case now uses enabled, finite, visible screen-coordinate taps consistently for Done, Start Set and Cancel. The input-value, unchecked-set and absent-rest assertions are retained.

That run also failed DoorMount's rendered-orbit assertion. Retained screenshots show a rendered board, and diagnostics advance from revision 2 to 7 with root/camera active in the same scene. Its old gesture crossed only 44 by 11 points in a 334 by 59-point viewport at 500 points/second. The test now makes a sustained slow drag, with a larger horizontal displacement on DoorMount and an endpoint hold. The rendered-pixel assertion remains mandatory, with a 60-second budget for screenshot capture on the slow runner. This addresses gesture/timing uncertainty without treating projected contact movement as proof of rendering.

The outstanding native-wrapper review finding is also corrected: Evo and Original Grindstone resolve `HANGTEN_FREECAD_CMD` and explicitly pass that executable to the runner, matching Honestone's skip and execution behavior. No CAD source, model or descriptor is changed.

Validation on Xcode 27 / isolated iPhone 17 Pro / iOS 26.3: test build succeeded; DoorMount passed its rendered-orbit and reset assertions (82.4 seconds); guided-hang cancellation passed (80.3 seconds). All three native FreeCAD regressions and all 51 CI contract/staging checks passed. All nine batch delivery hashes are unchanged. GitHub's Xcode 26.5 / iOS 26.5 confirmation remains required.

## Integrate the new board-finish contract from main

Run [36739743631](https://github.com/Asherlc/hang-ten/actions/runs/36739743631) reported a new Python failure against main's native-board finish coverage test. Main had advanced to `6566d8e82` (PR526), requiring every native manifest to declare `surfaceFinish`. Merged that commit into this branch and used `set_board_manifest.py` to declare `neutral` for all three new boards, preserving their prior appearance. This is a display choice, not a new manufacturer material claim. The setter verifies every non-Document.xml archive member byte-identically; no geometry is re-saved, and all six USDZ/descriptor hashes remain unchanged. Current FCStd hashes are updated in the individual board audits; the source archive changes only for embedded display metadata.

The complete Python package suite now passes 426 tests. The earlier local seven-case UI run passed all six free-workout cases and DoorMount's pixel/reset checks, but xcodebuild exceeded its 600-second bound during result finalization after those case results; its cleanup trap deleted the exact owned simulator and DerivedData, and deletion was verified. Focused UI validation is repeated after the main integration. PR525 remains open, and shared delivery-lock finalization still awaits PR524.

After integration, cancellation passed and DoorMount's rendered orbit passed, but the stronger rotation clipped the outer end of the selected edge and its old reset coordinate missed the surface. The retained screenshot confirms this clipping. The reset tap now aims at the visible inner floor of that same projected contact (offset 0.25, 0.55). Its focused rerun passed physical picking, rendered orbit, canonical camera reset, selection preservation and landscape assertions, with xcodebuild exit 0. The main-integrated cancellation case also passed. All three updated native source regressions passed again. Exact owned simulator and DerivedData deletion were verified after each run. The failed run's slow, workspace-owned simctl diagnostic collector was stopped only after case results were recorded, allowing the xcresult to finalize; no shared resources were touched.

## Free-workout navigation toolbar activation points

Run [36742466398](https://github.com/Asherlc/hang-ten/actions/runs/36742466398) passed Python, Swift unit tests and the entire boards/grips/picker suite. All 15 purchase/paywall cases and guided-hang cancellation passed. The two remaining failures were the workout-history cases: Finish timed out in the hittability predicate, and Close raised XCTest’s invalid activation-point error. Retained recordings at 167 seconds and 85 seconds respectively show both toolbar buttons fully visible and unobstructed; the Finish recording also confirms the set is completed and rest has been dismissed.

Both Finish call sites and Close now use the existing SpringBoard screen-coordinate helper, which requires an enabled control with a finite frame and a target inside the screen without requesting the invalid activation point. All close/resume, zero-set discard, completed-set finish, sheet dismissal and Last-workout assertions remain. No production code or CAD assets change.

Focused validation on Xcode 27 / iOS 26.3 / isolated iPhone 17 Pro: both history tests passed, with xcodebuild exit 0. The exact workspace-owned simulator and DerivedData were deleted by the exit trap and deletion verified. Hosted Xcode 26.5 CI must still confirm the branch.
