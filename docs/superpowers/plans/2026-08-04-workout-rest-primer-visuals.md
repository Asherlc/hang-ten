# Workout Rest Preview and Board Primer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make rest visually distinct while showing the next work holds during recovery, and replace the shared three-minute warm-up with a 60-second, actionable board primer.

**Architecture:** Add a pure `WorkoutBoardCue` policy to `WorkoutTimeline` so rest/active/suppressed board state is testable before wiring it into `WorkoutView`. Thread a two-case `BoardHighlightMode` through the bespoke and generic board renderers, using the existing active treatment for work and a cool blue preview treatment for rest. Update the source-audited warm-up seed, the shared-block detection, and the generated plan library independently.

**Tech Stack:** Swift 5, SwiftUI, XCTest, Xcode 26, iOS 17+, `xcodebuild`, the existing plan-library export script, and the repository's isolated-simulator validation workflow.

## Global Constraints

- The minimum deployment target remains iOS 17.0.
- Active work uses the existing bright red board highlight; rest preview uses a distinct cool blue treatment.
- Timed rest and explicit `.rest` steps preview the next non-rest step's resolved hold IDs.
- Countdown and completed-session states suppress all board highlights.
- A final rest step has no preview highlights but retains the rest presentation.
- The portrait and landscape layouts receive identical hold IDs and highlight mode from one elapsed position.
- The shared default warm-up is exactly 60 seconds with the approved board-primer instruction; unrelated three-minute recovery steps remain unchanged.
- The bundled `HangTen/Resources/PlanLibrary.json` must be regenerated from the source seed and pass `scripts/export-plan-library.sh --check`.
- No new dependencies, plan-library schema changes, persistence, audio, HealthKit, or workout-recording changes are in scope.
- Use `rtk` for repository shell commands and run a failing test before each production behavior implementation.
- Keep derived data, logs, screenshots, simulator manifests, and review notes under `.context`.
- Any validation simulator must be named with `CONDUCTOR_WORKSPACE_NAME`, recorded as workspace-owned before use, addressed by its explicit UUID for every operation, and shut down and deleted before completion.

## Files and responsibilities

- `HangTen/Models/WorkoutTimeline.swift`: pure workout board-cue state and the existing next-work-step lookup.
- `HangTen/Views/BoardDesignLanguage.swift`: Compact II highlight rendering for active and preview modes.
- `HangTen/Views/BoardMapView.swift`: public highlight-mode plumbing and generic-board fallback rendering.
- `HangTen/Views/DesignSystem.swift`: preview highlight colors if the existing rest palette needs a board-specific companion.
- `HangTen/Views/RootView.swift`: shared elapsed-state derivation, both workout layouts, rest preview label, and recovery copy.
- `HangTen/Models/TrainingModels.swift`: source-audited shared warm-up definition.
- `HangTen/Models/PlanStorage.swift`: reusable shared-warm-up detection.
- `HangTen/Resources/PlanLibrary.json`: generated runtime plan document.
- `HangTenTests/WorkoutTimelineTests.swift`: red/green coverage for board-cue policy and rest edge cases.
- `HangTenTests/PlanStorageTests.swift`: red/green coverage for the 60-second primer source and resolved built-in plan.

---

### Task 1: Make rest previews visible and visually distinct

**Files:**
- Modify: `HangTenTests/WorkoutTimelineTests.swift` near the existing `restPreviewSteps` fixture and `WorkoutTimelineTests` methods.
- Modify: `HangTen/Models/WorkoutTimeline.swift` after `holdPreviewStep(at:)`.
- Modify: `HangTen/Views/BoardDesignLanguage.swift` in `BoardDesign.draw` and its private hold shading helper.
- Modify: `HangTen/Views/BoardMapView.swift` in `BoardMapView`, `DesignedBoardMap`, `GenericVectorBoardMap`, and `GenericHoldVisual`.
- Modify: `HangTen/Views/DesignSystem.swift` only if a distinct board preview companion color is needed alongside `Color.restBlue`.
- Modify: `HangTen/Views/RootView.swift` in `WorkoutView.body`, `portraitSession`, `landscapeSession`, `cueCard`, and `landscapeCueCard`.

**Interfaces:**
- `BoardHighlightMode` is an internal `Hashable` enum with exactly `.active` and `.preview` cases. Define it in the Foundation-only workout timeline/model layer so both tests and SwiftUI board renderers can use the same type.
- `WorkoutBoardCue` is an internal `Equatable` value with `step: WorkoutStep?`, `mode: BoardHighlightMode`, `isResting: Bool`, and `isSuppressed: Bool` properties.
- `WorkoutTimeline.boardCue(at:countdown:isComplete:) -> WorkoutBoardCue` returns the current step and `.active` during work, the next non-rest step and `.preview` during timed/explicit rest, and a suppressed cue for countdown/completion. A final rest returns `step == nil`, `.preview`, `isResting == true`, and `isSuppressed == false`.
- `BoardMapView` gains `var highlightMode: BoardHighlightMode = .active` and passes it through both renderer branches. Existing callers that provide only `highlightedHoldIDs` keep active styling.

- [ ] **Step 1: Write the failing board-cue tests.**

Append these focused tests to `HangTenTests/WorkoutTimelineTests.swift`, using
the existing `restPreviewSteps` fixture:

```swift
func testBoardCueUsesNextWorkStepAndPreviewModeDuringRest() {
    let timeline = WorkoutTimeline(steps: restPreviewSteps)

    let cue = timeline.boardCue(at: 35, countdown: 0, isComplete: false)

    XCTAssertEqual(cue.step?.id, "next-work")
    XCTAssertEqual(cue.mode, .preview)
    XCTAssertTrue(cue.isResting)
    XCTAssertFalse(cue.isSuppressed)
}

func testBoardCueUsesActiveModeDuringWork() {
    let timeline = WorkoutTimeline(steps: restPreviewSteps)

    let cue = timeline.boardCue(at: 5, countdown: 0, isComplete: false)

    XCTAssertEqual(cue.step?.id, "work")
    XCTAssertEqual(cue.mode, .active)
    XCTAssertFalse(cue.isResting)
    XCTAssertFalse(cue.isSuppressed)
}

func testBoardCueSuppressesCountdownAndCompletion() {
    let timeline = WorkoutTimeline(steps: restPreviewSteps)

    let countdownCue = timeline.boardCue(at: 5, countdown: 3, isComplete: false)
    XCTAssertNil(countdownCue.step)
    XCTAssertTrue(countdownCue.isSuppressed)

    let completionCue = timeline.boardCue(at: 72, countdown: 0, isComplete: true)
    XCTAssertNil(completionCue.step)
    XCTAssertTrue(completionCue.isSuppressed)
}

func testBoardCueKeepsFinalRestAsRecoveryWithoutPreviewStep() {
    let timeline = WorkoutTimeline(steps: restPreviewSteps)

    let cue = timeline.boardCue(at: 72, countdown: 0, isComplete: false)

    XCTAssertNil(cue.step)
    XCTAssertEqual(cue.mode, .preview)
    XCTAssertTrue(cue.isResting)
    XCTAssertFalse(cue.isSuppressed)
}
```

- [ ] **Step 2: Run the focused tests and verify the red state.**

Use the explicit UUID recorded in the workspace-owned simulator manifest and
export it as `HANGTEN_REVIEW_SIMULATOR_UDID` before running:

```sh
rtk xcodebuild \
  -project HangTen.xcodeproj \
  -scheme HangTen \
  -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANGTEN_REVIEW_SIMULATOR_UDID" \
  -derivedDataPath .context/DerivedData-rest-preview \
  test \
  -only-testing:HangTenTests/WorkoutTimelineTests
```

Expected red result: compilation fails because `WorkoutTimeline` does not yet
define `boardCue(at:countdown:isComplete:)`. If the test passes, the test is
not exercising the missing behavior; correct the test before writing
production code.

- [ ] **Step 3: Implement the minimal pure board-cue policy.**

Add the two-case mode, the value type, and this policy shape to
`HangTen/Models/WorkoutTimeline.swift`:

```swift
enum BoardHighlightMode: Hashable {
    case active
    case preview
}

struct WorkoutBoardCue: Equatable {
    let step: WorkoutStep?
    let mode: BoardHighlightMode
    let isResting: Bool
    let isSuppressed: Bool
}

extension WorkoutTimeline {
    func boardCue(
        at elapsed: TimeInterval,
        countdown: Int,
        isComplete: Bool
    ) -> WorkoutBoardCue {
        guard countdown == 0,
              !isComplete,
              let currentStep = step(at: elapsed) else {
            return WorkoutBoardCue(
                step: nil,
                mode: .active,
                isResting: false,
                isSuppressed: true
            )
        }

        let stepElapsed = elapsedInStep(at: elapsed)
        let isResting = currentStep.phase == .rest
            || (currentStep.hasRestInterval && stepElapsed >= currentStep.activeDuration)

        return WorkoutBoardCue(
            step: holdPreviewStep(
                currentStep: currentStep,
                stepElapsed: stepElapsed
            ),
            mode: isResting ? .preview : .active,
            isResting: isResting,
            isSuppressed: false
        )
    }
}
```

Keep `holdPreviewStep(at:)` and `holdPreviewStep(currentStep:stepElapsed:)`
unchanged; the new method only makes the view's suppression and mode policy
pure and testable.

- [ ] **Step 4: Run the focused tests and verify the green state.**

Run the focused command from Step 2 again. Expect the four new board-cue tests
and all existing `WorkoutTimelineTests` to pass with exit code 0.

- [ ] **Step 5: Thread highlight mode through both board renderers.**

Update `BoardMapView` so its new `highlightMode` property is passed to
`DesignedBoardMap` and `GenericVectorBoardMap`. Update `BoardDesign.draw` and
its private hold draw function to accept the mode. Preserve the current active
shading exactly for `.active`; for `.preview`, use the existing cool rest
palette (`Color.restBlue`) with a slightly darker companion or opacity
gradient so preview holds are legible but quieter than `Color.holdActive`.

Update `GenericHoldVisual` to use the same semantic mapping: `.active` keeps
`Color.holdActive`/`Color.holdActiveDeep`, and `.preview` uses the rest-blue
fill and a darker rest-blue stroke. Keep labels readable in both modes. Do not
change hold geometry, hit regions, animation duration, or any non-workout
board caller.

The bespoke renderer should retain the existing hold geometry and select its
shading only at the existing highlight branch:

```swift
private func highlightShading(
    mode: BoardHighlightMode,
    in rect: CGRect
) -> GraphicsContext.Shading {
    switch mode {
    case .active:
        return activeShading(in: rect)
    case .preview:
        return .linearGradient(
            Gradient(colors: [Color.restBlue, Color.restBlue.opacity(0.72)]),
            startPoint: CGPoint(x: rect.midX, y: rect.minY),
            endPoint: CGPoint(x: rect.midX, y: rect.maxY)
        )
    }
}
```

Pass the same `highlightMode` to every existing `highlighted ? ... : ...`
branch for surface, shelf contact, and recessed contact fills. The generic
fallback can use a computed color switch with the same two mode cases.

- [ ] **Step 6: Wire the pure cue into `WorkoutView`.**

In `WorkoutView.body`, keep the existing `step` value for headers and cues but
replace the duplicated board/rest derivation with:

```swift
let boardCue = timeline.boardCue(
    at: elapsed,
    countdown: countdown,
    isComplete: isComplete
)
let isResting = boardCue.isResting
let highlightedStep = boardCue.step
let previewHoldIDs = highlightedStep.map { store.holdIDs(for: $0, on: board) } ?? []
let highlightedHoldIDs = boardCue.isSuppressed ? [] : Set(previewHoldIDs)
let highlightMode = boardCue.mode
let showsHoldPreview = isResting && !highlightedHoldIDs.isEmpty
```

Preserve the separate `isTimedResting` value for `WorkoutAudioCuePolicy` so
audio semantics do not change. Pass `highlightMode` and `showsHoldPreview`
through both `portraitSession` and `landscapeSession` to their `BoardMapView`
and cue-card calls. Keep the existing no-hand-diagram guards tied to
`!isResting`.

Show `SectionLabel(title: "Next hold preview", tint: WorkoutPhase.rest.textTint)`
immediately above the board only when `showsHoldPreview` is true. Use the same
label placement in both portrait and landscape without changing board size or
centering. For final rest, omit the label.

Change rest recovery copy to:

```text
Step off the board, shake out, and breathe. The blue board preview shows what’s next; wait for the timer before loading it.
```

Use that copy only when `showsHoldPreview` is true. For final rest, retain
short recovery copy that does not promise another hold. The rest pill, timer
label, recovery tint, recorder pause behavior, and audio classification remain
unchanged.

- [ ] **Step 7: Run focused and full tests after the UI wiring.**

Run the timeline tests again, then the complete target with the same explicit
workspace simulator and derived-data directory:

```sh
rtk xcodebuild \
  -project HangTen.xcodeproj \
  -scheme HangTen \
  -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANGTEN_REVIEW_SIMULATOR_UDID" \
  -derivedDataPath .context/DerivedData-rest-preview \
  test
```

Both commands must exit 0. Do not commit a renderer change that has only been
compiled if the focused tests or full target fail.

- [ ] **Step 8: Self-review and commit the rest-preview task.**

Review the diff for duplicated elapsed-state logic, accidental active-state
changes outside rest, missing mode propagation in either layout, and any
remaining copy that says the next cue appears only after rest. Run
`rtk git diff --check`, then commit:

```sh
rtk git add \
  HangTen/Models/WorkoutTimeline.swift \
  HangTen/Views/BoardDesignLanguage.swift \
  HangTen/Views/BoardMapView.swift \
  HangTen/Views/DesignSystem.swift \
  HangTen/Views/RootView.swift \
  HangTenTests/WorkoutTimelineTests.swift
rtk git commit -m "feat: show rest previews with distinct board cues"
```

Only stage `DesignSystem.swift` if it was actually modified.

---

### Task 2: Shorten and clarify the shared board primer

**Files:**
- Modify: `HangTenTests/PlanStorageTests.swift` near the built-in source-seed tests.
- Modify: `HangTen/Models/TrainingModels.swift` in `LegacyPlanSeedCatalog.warmUpStep`.
- Modify: `HangTen/Models/PlanStorage.swift` in shared warm-up extraction and plan block matching.
- Modify: `HangTen/Resources/PlanLibrary.json` only through `scripts/export-plan-library.sh`.

**Interfaces:**
- `LegacyPlanSeedCatalog.warmUpStep(id:duration:)` keeps its current signature and defaults to `duration: 60`.
- The shared warm-up remains titled `Progressive warm-up`, targets `outer-jugs`/`jug-left` and `jug-right`, and uses `.openHand`.
- The approved instruction is exactly: `Start with easy 5-, 10-, and 20-second hangs on the outer jugs. Step off between hangs, keep an open grip, and stop if anything hurts. Do a broader warm-up before training.`
- The accessory is exactly: `Board primer · warm up generally first`.
- `PlanStorage` recognizes the shared warm-up with the new 60-second duration; three-minute recovery steps elsewhere are not changed.

- [ ] **Step 1: Write the failing warm-up source tests.**

Add this test to `HangTenTests/PlanStorageTests.swift`:

```swift
func testSharedWarmUpIsSixtySecondBoardPrimer() throws {
    let seedStep = try XCTUnwrap(LegacyPlanSeedCatalog.metoliusEntry.steps.first)

    XCTAssertEqual(seedStep.title, "Progressive warm-up")
    XCTAssertEqual(seedStep.duration, 60)
    XCTAssertEqual(
        seedStep.instruction,
        "Start with easy 5-, 10-, and 20-second hangs on the outer jugs. Step off between hangs, keep an open grip, and stop if anything hurts. Do a broader warm-up before training."
    )
    XCTAssertEqual(seedStep.accessory, "Board primer · warm up generally first")
    XCTAssertEqual(seedStep.gripType, .openHand)
    XCTAssertEqual(seedStep.targets, [.ids("jug-left", "jug-right")])

    let store = try PlanLibraryStore(definition: BuiltInPlanLibraryDefinition.document)
    let resolvedStep = try XCTUnwrap(
        store.plan(id: LegacyPlanSeedCatalog.metoliusEntry.id)?.steps.first
    )
    XCTAssertEqual(resolvedStep.duration, 60)
    XCTAssertEqual(resolvedStep.instruction, seedStep.instruction)
}
```

- [ ] **Step 2: Run the focused test and verify the red state.**

Run the PlanStorage tests with the explicit workspace simulator:

```sh
rtk xcodebuild \
  -project HangTen.xcodeproj \
  -scheme HangTen \
  -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANGTEN_REVIEW_SIMULATOR_UDID" \
  -derivedDataPath .context/DerivedData-warmup \
  test \
  -only-testing:HangTenTests/PlanStorageTests/testSharedWarmUpIsSixtySecondBoardPrimer
```

Expected red result: the existing 180-second seed and old copy fail the
assertions. Do not weaken the exact values.

- [ ] **Step 3: Update the source-audited seed and shared-block matching.**

In `TrainingModels.swift`, change only the default value and content of
`warmUpStep`:

```swift
private static func warmUpStep(id: String, duration: TimeInterval = 60) -> WorkoutStep {
    WorkoutStep(
        id: id,
        number: 0,
        title: "Progressive warm-up",
        instruction: "Start with easy 5-, 10-, and 20-second hangs on the outer jugs. Step off between hangs, keep an open grip, and stop if anything hurts. Do a broader warm-up before training.",
        accessory: "Board primer · warm up generally first",
        duration: duration,
        phase: .warmUp,
        targets: [.ids("jug-left", "jug-right")],
        segments: [fixedWork(.ids("jug-left", "jug-right"), duration)],
        gripType: .openHand
    )
}
```

In `PlanStorage.swift`, change both shared-warm-up duration comparisons from
`180` to `60`: the reusable block discovery in `makeDocument()` and the first
step matching in `makeDefinition(from:sharedWarmUp:sharedCoolDown:existingBlockIDs:)`.
Do not change the `sharedCoolDown` comparison or any recovery-step duration.

- [ ] **Step 4: Regenerate and verify the bundled plan document.**

Run the existing exporter so the runtime JSON is derived from the updated seed:

```sh
rtk scripts/export-plan-library.sh
rtk scripts/export-plan-library.sh --check
```

The check must print that `PlanLibrary.json` matches the source-audited
definitions. Inspect the generated diff to confirm the shared warm-up is 60
seconds with the new instruction/accessory and that unrelated three-minute
recovery records remain unchanged.

- [ ] **Step 5: Run the focused tests and source check.**

Run the focused PlanStorage test again and then the full PlanStorage test class:

```sh
rtk xcodebuild \
  -project HangTen.xcodeproj \
  -scheme HangTen \
  -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANGTEN_REVIEW_SIMULATOR_UDID" \
  -derivedDataPath .context/DerivedData-warmup \
  test \
  -only-testing:HangTenTests/PlanStorageTests
rtk scripts/export-plan-library.sh --check
```

Both test and source-check commands must exit 0.

- [ ] **Step 6: Self-review and commit the primer task.**

Review the generated JSON rather than hand-editing it, confirm the explicit
`warmUpStep(id:duration:)` call for Abrahangs still resolves to its declared
120-second duration, run `rtk git diff --check`, and commit:

```sh
rtk git add \
  HangTen/Models/TrainingModels.swift \
  HangTen/Models/PlanStorage.swift \
  HangTen/Resources/PlanLibrary.json \
  HangTenTests/PlanStorageTests.swift
rtk git commit -m "feat: clarify and shorten the board primer"
```

---

## Final verification and review

After both task reviews are clean:

1. Run `rtk scripts/export-plan-library.sh --check` and the complete XCTest target with workspace-local derived data.
2. Use `validate-hang-ten-ios` after reading `docs/IOS_SIMULATOR_VALIDATION.md` and `docs/IOS_RUNTIME_SERVICES.md` completely. Install its cleanup traps before creating the simulator. Create exactly one simulator named `Hang Ten Conductor $CONDUCTOR_WORKSPACE_NAME Review`, record its UUID in `.context/conductor-pending-simulators` and `.context/conductor-owned-simulators`, and use only that UUID.
3. Build and install the exact Debug app under `.context/DerivedData-final-review`.
4. Inspect a timed-rest preview in portrait using a DEBUG workout route with `HANGTEN_REVIEW_PLAN_ID=research.force-feedback-f100`, `HANGTEN_REVIEW_STEP=2`, `HANGTEN_REVIEW_AUTOSTART=1`, and `HANGTEN_REVIEW_PORTRAIT=1`. Capture `.context/rest-preview-portrait.png` only after the step enters rest.
5. Inspect an explicit-rest preview in landscape using `HANGTEN_REVIEW_PLAN_ID=research.force-feedback-f80`, `HANGTEN_REVIEW_STEP=14`, `HANGTEN_REVIEW_AUTOSTART=1`, and `HANGTEN_REVIEW_LANDSCAPE=1`. Capture `.context/rest-preview-landscape.png` and inspect both images with `view_image`.
6. Confirm active work is red, rest preview is blue and labeled `Next hold preview`, the board remains aligned in both orientations, the hand diagram/cards are absent during rest, the final rest has no preview, and the shared primer shows 60 seconds with the approved instruction.
7. Shut down and delete only the exact workspace-owned simulator through the validation cleanup trap. Verify the owned and pending manifests no longer contain that UUID; if cleanup fails, retain the manifests and continue remediation before reporting completion.
8. Run the final whole-branch review using the subagent-driven-development review package and record all task/review commits in the plan-owned `.superpowers/sdd/2026-08-04-workout-rest-primer-visuals/progress.md` ledger.

All generated artifacts remain under `.context`; no workspace-owned simulator,
manifest, derived-data directory, screenshot, or review file is left behind at
completion.
