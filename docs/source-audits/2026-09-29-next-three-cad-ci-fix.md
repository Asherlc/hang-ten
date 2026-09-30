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
