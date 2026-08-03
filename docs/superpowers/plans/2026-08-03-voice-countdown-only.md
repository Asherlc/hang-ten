# Numeric-only workout audio cues Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Hang Ten speak only numeric `3`, `2`, and `1` countdown cues during workouts, removing spoken labels, set/rep titles, rest prompts, and completion text.

**Architecture:** Keep workout-state derivation in `WorkoutView`, but move the pure decision about whether a numeric audio moment exists into an internal `WorkoutAudioCuePolicy`. The policy returns a keyed `WorkoutAudioMoment` or `nil` and has no AVFoundation or SwiftUI dependency, while the existing `WorkoutAudioCoach` remains the only speech-synthesis boundary.

**Tech Stack:** Swift 5, SwiftUI, XCTest, AVFoundation, Xcode 26, iOS 17+.

## Global Constraints

- Every spoken workout cue must be a numeric countdown value: `3`, `2`, or `1`.
- The initial countdown and existing interval timing remain intact, but the app must not speak segment names, exercise titles, set/rep identifiers, rest prompts, or completion text.
- Audio enable/disable behavior, speech synthesis configuration, and the visible workout countdown are unchanged.
- The policy has no dependency on AVFoundation or view state.
- This change does not alter workout durations, interval calculations, the audio toggle, speech rate/voice configuration, or the visual countdown UI.

---

## File Map

- `HangTen/Views/RootView.swift` — expose the audio moment value type internally, add the pure numeric cue policy, and route `WorkoutView.audioMoment` through it.
- `HangTenTests/WorkoutTimelineTests.swift` — add focused XCTest coverage for initial, interval, short-interval, suppressed-start, and suppressed-completion cues without adding a new project-file entry.
- `README.md` — update the audio feature summary so it no longer promises task or completion speech.

## Task 1: Implement and test numeric-only audio cue selection

**Files:**

- Modify: `HangTen/Views/RootView.swift:858-870` for `WorkoutAudioMoment` and the new `WorkoutAudioCuePolicy`.
- Modify: `HangTen/Views/RootView.swift:1511-1575` for `WorkoutView.audioMoment` and removal of `spokenStartPhrase(for:)`.
- Test: `HangTenTests/WorkoutTimelineTests.swift` by adding `WorkoutAudioCuePolicyTests`.
- Modify: `README.md:25` to describe countdown-only speech.

**Interfaces:**

- Consumes: the existing `WorkoutView` values `step.id`, `isResting`, `countdown`, `stepElapsed`, `step`, and `isComplete`.
- Produces: `WorkoutAudioMoment` with `key: String` and `phrase: String`, plus the internal policy method below for the view and tests.

```swift
enum WorkoutAudioCuePolicy {
    static func moment(
        stepID: String,
        segmentName: String,
        initialCountdown: Int,
        intervalSecondsRemaining: Int,
        isComplete: Bool
    ) -> WorkoutAudioMoment?
}
```

### Steps

- [ ] **Step 1: Add the failing policy tests first.**

Append this test class to `HangTenTests/WorkoutTimelineTests.swift`. The
tests intentionally reference the not-yet-implemented policy, and the first
focused test run must fail because the production policy does not exist yet.

```swift
final class WorkoutAudioCuePolicyTests: XCTestCase {
    private let stepID = "f80-set-2-rep-3"

    func testInitialCountdownReturnsOnlyNumericValues() {
        for countdown in [3, 2, 1] {
            let moment = WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: countdown,
                intervalSecondsRemaining: 60,
                isComplete: false
            )

            XCTAssertEqual(
                moment,
                WorkoutAudioMoment(
                    key: "initial-\(countdown)",
                    phrase: "\(countdown)"
                )
            )
        }
    }

    func testIntervalCountdownReturnsNumericValuesWithStableSegmentKeys() {
        for secondsRemaining in [3, 2, 1] {
            let moment = WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 0,
                intervalSecondsRemaining: secondsRemaining,
                isComplete: false
            )

            XCTAssertEqual(
                moment,
                WorkoutAudioMoment(
                    key: "\(stepID)-active-\(secondsRemaining)",
                    phrase: "\(secondsRemaining)"
                )
            )
        }
    }

    func testSegmentStartAndNormalIntervalReturnNoCue() {
        XCTAssertNil(
            WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "rest",
                initialCountdown: 0,
                intervalSecondsRemaining: 60,
                isComplete: false
            )
        )
    }

    func testCompletionReturnsNoCueEvenDuringTheFinalThreeSeconds() {
        XCTAssertNil(
            WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 0,
                intervalSecondsRemaining: 3,
                isComplete: true
            )
        )
    }

    func testShortIntervalReturnsOnlyTheApplicableNumber() {
        let moment = WorkoutAudioCuePolicy.moment(
            stepID: stepID,
            segmentName: "rest",
            initialCountdown: 0,
            intervalSecondsRemaining: 2,
            isComplete: false
        )

        XCTAssertEqual(
            moment,
            WorkoutAudioMoment(
                key: "\(stepID)-rest-2",
                phrase: "2"
            )
        )
    }
}
```

- [ ] **Step 2: Run the focused test to verify the red state.**

Run:

```bash
rtk xcodebuild \
  -project HangTen.xcodeproj \
  -scheme HangTen \
  -destination 'platform=iOS Simulator,OS=26.5,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/WorkoutAudioCuePolicyTests \
  test
```

Expected: the build/test command fails because `WorkoutAudioCuePolicy` is not
defined. Do not change the tests to make this first run pass.

- [ ] **Step 3: Add the minimal pure policy implementation.**

Replace the current private audio-moment declaration near the top of
`RootView.swift` with this internal value type and policy:

```swift
struct WorkoutAudioMoment: Hashable {
    let key: String
    let phrase: String
}

enum WorkoutAudioCuePolicy {
    static func moment(
        stepID: String,
        segmentName: String,
        initialCountdown: Int,
        intervalSecondsRemaining: Int,
        isComplete: Bool
    ) -> WorkoutAudioMoment? {
        if (1...3).contains(initialCountdown) {
            return WorkoutAudioMoment(
                key: "initial-\(initialCountdown)",
                phrase: "\(initialCountdown)"
            )
        }

        guard !isComplete, (1...3).contains(intervalSecondsRemaining) else {
            return nil
        }

        return WorkoutAudioMoment(
            key: "\(stepID)-\(segmentName)-\(intervalSecondsRemaining)",
            phrase: "\(intervalSecondsRemaining)"
        )
    }
}
```

- [ ] **Step 4: Route `WorkoutView.audioMoment` through the policy.**

Keep the existing `startedAt` guard and method signature, then replace the
current segment-start/completion branches with this complete method body. The
existing `intervalRemaining(step:stepElapsed:)` helper supplies the same
interval timing used by the visible timer.

```swift
private func audioMoment(
    step: WorkoutStep,
    stepElapsed: TimeInterval,
    countdown: Int,
    isResting: Bool,
    isComplete: Bool
) -> WorkoutAudioMoment? {
    guard startedAt != nil else { return nil }

    let secondsRemaining = Int(
        ceil(intervalRemaining(step: step, stepElapsed: stepElapsed))
    )

    return WorkoutAudioCuePolicy.moment(
        stepID: step.id,
        segmentName: isResting ? "rest" : "active",
        initialCountdown: countdown,
        intervalSecondsRemaining: secondsRemaining,
        isComplete: isComplete
    )
}
```

Delete `spokenStartPhrase(for:)` after this wiring change because no code
should construct a verbal start label.

- [ ] **Step 5: Run the focused tests to verify green.**

Run the same focused `xcodebuild` command from Step 2. Expected: all five
`WorkoutAudioCuePolicyTests` tests pass with zero failures or warnings that
indicate a test/build problem.

- [ ] **Step 6: Update the README audio summary.**

Change the feature list in `README.md` so the sentence describing workout
audio says that the app has a spoken 3-2-1 start countdown and final
three-second countdown cues, without mentioning task cues or completion audio.

- [ ] **Step 7: Run the complete XCTest target.**

Run:

```bash
rtk xcodebuild \
  -project HangTen.xcodeproj \
  -scheme HangTen \
  -destination 'platform=iOS Simulator,OS=26.5,name=iPhone 17 Pro' \
  test
```

Expected: the full `HangTenTests` target passes with zero test failures.

- [ ] **Step 8: Review the diff and commit the implementation.**

Run:

```bash
rtk git diff --check
rtk git diff -- HangTen/Views/RootView.swift HangTenTests/WorkoutTimelineTests.swift README.md
```

Confirm that the diff changes only countdown cue selection, its tests, and
the now-accurate README sentence. Then commit:

```bash
rtk git add HangTen/Views/RootView.swift HangTenTests/WorkoutTimelineTests.swift README.md
rtk git commit -m "fix: limit workout speech to countdown cues"
```

## Post-implementation validation

After Task 1 is reviewed, run the repository's isolated iOS validation
workflow from `.codex/skills/validate-hang-ten-ios/SKILL.md`. Read
`docs/IOS_SIMULATOR_VALIDATION.md` and `docs/IOS_RUNTIME_SERVICES.md` before
running it. Use a simulator owned by this workspace and inspect the initial
countdown, a normal interval's final countdown, a short interval, audio-off
behavior, and session completion. The runtime check must confirm that spoken
output is limited to numeric countdown values.
