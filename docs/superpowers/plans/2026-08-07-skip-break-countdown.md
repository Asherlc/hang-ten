# Skip-to-break Countdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Skip directly into a rest step without the three-second preparation countdown while preserving the session's running or paused state.

**Architecture:** Keep `WorkoutSessionState.skipCurrentStep` as the single transition owner. After `WorkoutTimeline.skipTarget(from:)` resolves the boundary, use the existing direct `seek` path for a rest destination and retain `startSkipCountdown` for work destinations. No UI, timer, audio, or timeline-model changes are needed.

**Tech Stack:** Swift, SwiftUI, XCTest, Xcode project `HangTen.xcodeproj`.

## Global Constraints

- A skip whose destination step has `phase == .rest` transitions immediately.
- The immediate transition preserves the session's current running or paused state.
- A skip whose destination step is a work step continues to use the existing three-second countdown.
- Skipping the final step continues to seek directly to completion without a countdown.
- No new timer, UI state, audio policy, or timeline representation is needed.
- Use test-first development: write a failing regression test, verify the failure, implement the smallest fix, then verify focused and full tests.
- Keep generated build products under `.context`; use `-derivedDataPath .context/derived-data` for Xcode commands.

---

### Task 1: Bypass skip countdown for rest destinations

**Files:**
- Modify: `HangTenTests/WorkoutTimelineTests.swift:1140-1370` in `WorkoutSessionStateTests`
- Modify: `HangTen/Views/RootView.swift:1393-1405` in `WorkoutSessionState.skipCurrentStep`

**Interfaces:**
- Consumes: `WorkoutTimeline.skipTarget(from:)`, `WorkoutTimeline.step(at:)`, and `WorkoutSessionState.seek(to:planDuration:at:)`.
- Produces: `skipCurrentStep(timeline:planDuration:at:)` that immediately seeks to `.rest` destinations and otherwise retains the existing `.skip` countdown.

- [ ] **Step 1: Add the failing running-session regression test**

Add this test to `WorkoutSessionStateTests`, using the existing `steps` fixture where `second` is a `.rest` step beginning at elapsed `60`:

```swift
func testRunningSkipIntoRestTransitionsImmediatelyAndKeepsRunning() {
    let now: TimeInterval = 100
    let timeline = WorkoutTimeline(steps: steps)
    var state = WorkoutSessionState(
        activeStartUptime: now - 10,
        pausedElapsed: 10,
        routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
    )

    XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))

    XCTAssertNil(state.countdownKind)
    XCTAssertEqual(state.activeStartUptime, now)
    XCTAssertEqual(state.pausedElapsed, 60)
    XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now), 60)
    XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now + 1), 61)
}
```

- [ ] **Step 2: Add the failing paused-session regression test**

Add this test next to the running-session test:

```swift
func testPausedSkipIntoRestTransitionsImmediatelyAndKeepsPaused() {
    let now: TimeInterval = 100
    let timeline = WorkoutTimeline(steps: steps)
    var state = WorkoutSessionState(
        activeStartUptime: nil,
        pausedElapsed: 10,
        routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
    )

    XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))

    XCTAssertNil(state.countdownKind)
    XCTAssertNil(state.activeStartUptime)
    XCTAssertEqual(state.pausedElapsed, 60)
    XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now + 10), 60)
}
```

- [ ] **Step 3: Run the focused tests and verify they fail for the missing behavior**

Run the focused tests on the workspace-owned simulator:

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=C1B82F8E-687F-41EB-8487-3CAA9C52005E' -derivedDataPath .context/derived-data -parallel-testing-enabled NO CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO -only-testing:HangTenTests/WorkoutSessionStateTests test
```

Expected result before the production change: the two new tests fail because the implementation starts a `.skip` countdown and sets `activeStartUptime` three seconds in the future instead of seeking immediately.

- [ ] **Step 4: Implement the minimal destination-phase branch**

Update `WorkoutSessionState.skipCurrentStep` after the existing final-step branch so that a non-final rest destination reuses `seek`:

```swift
if target >= planDuration {
    seek(to: target, planDuration: planDuration, at: uptime)
} else if timeline.step(at: target)?.phase == .rest {
    seek(to: target, planDuration: planDuration, at: uptime)
} else {
    startSkipCountdown(to: target, at: uptime)
}
```

Do not change `startSkipCountdown`, `WorkoutSessionPolicy.skipCountdownDuration`, UI countdown rendering, or final-step behavior.

- [ ] **Step 5: Update existing skip lifecycle tests to keep work-destination coverage**

The existing fixture's first skip target is now a rest step, so update tests that intentionally verify countdown cancellation, interruption, direct seek, and expiry to begin at elapsed `65` and target the third work step at `80`. Use a paused state with `pausedElapsed: 65` for paused cases, or a running state with `activeStartUptime: now - 65` and `pausedElapsed: 0` for running cases. Preserve their current assertions about `.skip`, three-second expiry, cancellation, interruption, and running-state preservation, changing only target values from `60` to `80` where required.

The existing `testFinalSkipSeeksDirectlyToCompletion` remains unchanged and continues to cover the plan-duration branch.

- [ ] **Step 6: Run focused tests and then the complete test target**

Run the focused class again on the workspace-owned simulator:

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=C1B82F8E-687F-41EB-8487-3CAA9C52005E' -derivedDataPath .context/derived-data -parallel-testing-enabled NO CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO -only-testing:HangTenTests/WorkoutSessionStateTests test
```

Then run all `HangTenTests` through the cleanup wrapper; this final command
shuts down and deletes the exact owned simulator in its exit trap:

```bash
rtk zsh .context/run-owned-xcode-tests.zsh test
```

Expected result: both commands exit `0`; the focused suite covers immediate running and paused rest transitions, work-destination countdown behavior, cancellation/interruption, direct seek, and final completion, and the full target has zero failures.

- [ ] **Step 7: Review the diff and commit the task**

Run:

```bash
rtk git diff --check
rtk git diff -- HangTen/Views/RootView.swift HangTenTests/WorkoutTimelineTests.swift
```

Confirm the diff contains only the destination-phase branch and focused test updates, then commit:

```bash
rtk git add HangTen/Views/RootView.swift HangTenTests/WorkoutTimelineTests.swift
rtk git commit -m "Skip countdown when entering a rest step"
```
