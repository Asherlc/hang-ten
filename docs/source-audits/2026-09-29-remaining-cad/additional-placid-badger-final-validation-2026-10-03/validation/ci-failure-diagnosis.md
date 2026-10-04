# Boards/grips/picker CI failure audit

Exact failed run: [37165839403](https://github.com/Asherlc/hang-ten/actions/runs/37165839403), job [111328802127](https://github.com/Asherlc/hang-ten/actions/runs/37165839403/job/111328802127), source `bad7500123243937db712f5b0139ab273e373836`. The job built successfully and ran 29 UI tests: 26 passed, 3 failed. Every failure is in `GripCueDiagnosticScreenshotUITests`. No board interaction or 30-second stable-projection assertion failed. Initial missing-Metal-toolchain preflight was repaired by the existing job before the successful build; it is not the test failure.

Current evidence-only head `6d9a7de223d0736279b5e780b67b8017c277feef` has no diff from the failing head in HangTen, tests, assets/project, Tools, workflows, or scripts. The prior green run [37156649527](https://github.com/Asherlc/hang-ten/actions/runs/37156649527) was source `7e12907150374f722446a0e8725123d1bc52b650`, boards job `111301436338`. The three UI test methods, session-clock/skip policy, plan library, and CI workflow are unchanged between the two source heads. New initial renderer preparation changes when the tests observe existing transient controls; this exposed previously timing-dependent test actions.

| Test / source line | Exact failure | Artifact and causal evidence |
| --- | --- | --- |
| `testContactOffsetTaskCanAdvanceWithoutSkippingMinute`, line 61 | Start tap: no matching button. Failed at 63.410 s; previously passed at 56.074 s. | The job checks Start at 59.56 s and taps at 59.71 s, but the retained failure hierarchy already contains Cancel countdown / step 9. Video frame 58 shows Preparing 3D views. This is an automatically starting route; the optional manual Start tap races the automatic countdown. |
| `testOneArmTaskLetsAthleteChooseSide`, line 105 | Immediate Hold 1 of 3 existence assertion after Right tap. Failed at 53.981 s; previously passed at 53.300 s. | Video frame 52 shows Preparing, Choose a hand, Right, and Hold 1 of 3. Frame 53 shows the initial countdown and those controls hidden. The test starts its tap at 52.57 s; the event is synthesized at 53.10 s. It attempts selection while the preparation controls are transitioning into countdown. |
| `testWorkoutPauseSurvivesRotationAndResumes`, line 196 | Strict Skip step 2: Rest predicate times out after its original 5 s. Failed at 87.917 s; previously passed at 69.649 s. | Both exact retained paused screenshots show the same 00:06 on set 1, so rotation preserved the clock. After Resume, frame 75 shows 00:02; frame 77 shows naturally reached Rest at 03:00. The delayed Skip then advances that rest to set 2 countdown (frame 82 and exact debug attachment: Skip step 3: Max hang · set 2, Disabled). This is the wrong starting step for the intended tap, not a missing Rest transition. |

## Launch and production contracts

The diagnostic class explicitly launches with free workouts used 0, review step 1, landscape 1, and board `tension.honestone`. Contact entry changes review step to 9 and removes the landscape override. One-arm additionally sets review plan `metolius.contact.intermediate`. Neither the test class nor the CI invocation sets `HANGTEN_REVIEW_AUTOSTART`. `WorkoutView.swift:418` independently auto-starts plans without the separate session-hand-choice sheet through `WorkoutSessionPolicy.shouldAutoStart` (`WorkoutSessionState.swift:237`). The preparation gate delays first start until the mounted renderer responses resolve; it does not turn these routes into manual-start flows.

`WorkoutView.swift:589` and `:605` display task-side and hold controls only with countdown zero. During renderer preparation, that is still zero. The initial countdown hides them until running; the test must use Pause as its existing running-state signal before selecting or advancing a task. The tested single-arm minute is still a full real minute after startup.

The real Max Hangs source in `HangTen/Resources/PlanLibrary.json:5928` is 10 s work plus 180 s rest. Runtime expansion exposes these as work step 1 / rest step 2. `WorkoutSessionState.swift:466` chooses a seek for destination Rest and a countdown for destination work. The clock and skip policy are byte-identical to the green source. Changing the source durations or raising a timeout would not fix the delayed tap on the wrong step.

## Isolated correction

[grip-cue-ui-races.patch](grip-cue-ui-races.patch) changes only three methods inside `GripCueDiagnosticScreenshotUITests` in `HangTenUITests/GripCueSnapshotUITests.swift`:

1. Remove the redundant Start attempt and retain the existing Pause wait of 20 s before Contact task assertions/actions.
2. Wait for Pause with the same existing startup budget of 20 s before choosing Right. Retain both exact Hold 1 of 3 and Hang • Right hand assertions.
3. While still paused after the rotation/clock-equality assertions, tap Skip and retain the exact Rest-step predicate with its original 5 s timeout. Assert Resume remains present, then resume on the sourced 180 s rest, retain Pause with its original 10 s timeout, and perform the existing next-work Skip / Cancel countdown / Resume assertions unchanged.

Every substantive previous assertion remains. No timeout is enlarged. No fixture, source timing, renderer, physics, settling check, package metadata, or native model changes. No production repair is supported by these failures.

The patch passes `git apply --check` against the unchanged file. This agent has not applied it, built, or run tests. Root should apply it and run the entire `-only-testing:HangTenUITests/GripCueDiagnosticScreenshotUITests` class on its exact owned CI-equivalent lane, followed by normal CI. Specific filters and source/proposed/patch SHA-256 are in [patch-receipt.json](patch-receipt.json).

## Retained evidence

- `boards-job-111328802127.log`, `green-boards-job-111301436338.log`: exact GitHub job logs.
- `boards-diagnostics-11289927451.zip`, `artifact/HangTenUITests-map-boards-grips-picker-run.xcresult`: exact downloadable CI artifact / extracted result bundle.
- `attachments-testContactOffsetTaskCanAdvanceWithoutSkippingMinute/A084EA80-2A12-48BE-A34E-2EB4126829B9.txt`: failed Start hierarchy.
- `attachments-testWorkoutPauseSurvivesRotationAndResumes/FAF1CE53-32E2-4CC3-84B6-AB822C67A250.txt`: exact actual set 2 Skip label.
- `attachments-testWorkoutPauseSurvivesRotationAndResumes/{1CDD3E9F-F959-4005-8007-69C807E653F2,FCD4630E-E8B1-4895-91DC-4A9CAA7D181C}.png`: original paused landscape / portrait screenshots.
- `frames-contact-offset/frame-58.png`, `frames-one-arm/frame-{52,53}.png`, `frames-pause-rotation/frame-{75,77,82}.png`: full frames decoded from the original recordings, inspected without cropping, pixel measurement, or visual edits. Original movie orientation is retained.
- Per-test `*-activities.json` and attachment manifests retain timestamps and payload provenance. `extract-frames.swift` is a local read-only media decoding helper; its compiler module cache is confined to this owned scratch lane.

Owner: placid-badger. Only this owned scratch lane was written. No external resources, Simulator/app operations, CI mutation, tracked-file changes, staging, commits, or peer-workspace access.
