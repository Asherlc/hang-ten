# Next three native CAD boards: CI follow-up

CI run [36629793095](https://github.com/Asherlc/hang-ten/actions/runs/36629793095) failed in `InitialWeightSetupUITests.testInlineChoicesDefaultToSkipAndKeepManualDraft`: the Add bodyweight switch remained off after a synthesized thumb tap on iOS 26.5. The retained recording showed an unobstructed switch. XCTest reported the named switch frame `(303, 423, 61, 28)` and a tap at `(321.3, 437)`, with its value still `0`. Python, Swift unit tests, map batch05-b and paywall CI jobs passed.

Integrated origin/main at `d0e4e9519`, including its existing correction for the same weight-flow failure. Both UI test files retain main’s normal switch tap, explicit off-state checks, narrow frame assertion, label interaction coverage and fixed Original Grindstone fixture. Comments now describe that fixture as a native model bundled in DEBUG simulator builds. All assertions remain intact. Main’s Whetstone package, ODR registration and native regression coverage were preserved together with this batch’s three packages.

All nine source/model/descriptor hashes for Evo, Honestone and Original Grindstone remain unchanged. Final delivery-lock integration still awaits PR524’s merge; the lock brought in from main covers its existing deliveries.

Local validation: Python CAD/model/package suites passed 492 tests, 11 optional checks skipped, and 24 subtests. Simulator build-for-testing succeeded. The local Xcode 27 / iOS 26.5 simulator attempts stalled before the UI runner launched. Bounded boot-status and screenshot probes also timed out. Both attempts were stopped and their exact workspace-owned simulators deleted by the cleanup traps; no local UI or full merged Swift runtime pass is claimed. GitHub CI uses Xcode 26.5 and will validate the pushed change.

## Follow-up after the tap correction failed in CI

Run [36645711814](https://github.com/Asherlc/hang-ten/actions/runs/36645711814) reproduced the switch failure after the normal tap. Its event attachment records `(333.5, 437)`, with the named switch still off and the parent window snapshot reporting zero/nonfinite bounds. Recording frames before and after the interaction show an unobstructed, unchanged switch. The tap synthesis took 18 seconds. The independent visible-label interaction passed.

Both weight-flow tests now use a sustained native switch drag: 0.5-second press, explicit slow velocity from normalized `(0.3, 0.5)` to `(0.8, 0.5)`, and 0.2-second endpoint hold. This is the gesture previously validated in the parent batch before main replaced it with the shorter tap. The initial off-state, enabled-state, manual draft persistence, purchase summary and separate label interaction assertions remain intact. No production or CAD geometry changes are included.
