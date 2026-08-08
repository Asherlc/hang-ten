# Hold Preview Grip Cue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the next work step's grip cue during hold previews while keeping the workout board's layout stable between active work and rest.

**Architecture:** Add a pure `WorkoutHoldCuePolicy` beside the existing workout board-cue policy. It resolves the highlighted step's single-hold cue and effective grip type once, using the board-backed target resolver to verify that the supplied highlighted hold belongs to the step. `WorkoutView` passes that value to both portrait and landscape renderers. Landscape keeps the board's existing constrained cue-row footprint instead of applying a rest-only height.

**Tech Stack:** Swift 5, SwiftUI, XCTest, Xcode 26, iOS 17+.

## Global Constraints

- The minimum deployment target remains iOS 17.0.
- The resolver accepts the highlighted step, candidate hold, and board; it returns a cue only for the existing single-target case when the board-backed target resolver contains that hold.
- The highlighted/preview step is the grip metadata source; its explicit `gripType` overrides the board hold default.
- Countdown, completed-session, and final-rest states show no grip cue.
- Both portrait and landscape consume the same resolved hold and grip type.
- Remove only the landscape rest-only board height override; retain the existing board highlight modes and preview label/copy.
- No new dependencies, plan-library schema changes, persistence, audio, HealthKit, workout recording, or board mapping changes.
- Put derived test/build output under `.context` and leave shared or unknown simulators/resources untouched.

---

### Task 1: Add and test the shared hold-cue resolver

**Files:**
- Modify: `HangTen/Models/WorkoutTimeline.swift` beside `WorkoutBoardCue`
- Modify: `HangTenTests/WorkoutTimelineTests.swift` with focused resolver tests

**Interfaces:**
- Produces `WorkoutHoldCue`:

  ```swift
  struct WorkoutHoldCue: Equatable {
      let hold: BoardHold
      let gripType: GripType
  }
  ```

- Produces `WorkoutHoldCuePolicy.resolve(step:hold:on:)`:

  ```swift
  enum WorkoutHoldCuePolicy {
      static func resolve(
          step: WorkoutStep?,
          hold: BoardHold?,
          on board: TrainingBoard
      ) -> WorkoutHoldCue?
  }
  ```

- The resolver returns `nil` when the step or hold is absent, the step does not have exactly one target, or `BoardTargetResolver.resolveHoldIDs(for:on:)` cannot prove that the supplied hold belongs to that target. Otherwise it returns the supplied hold and `step.gripType ?? hold.gripType`.

- [ ] **Step 1: Write the failing tests**

  Add these tests to `WorkoutTimelineTests` before adding the production type. Use a board hold whose default grip is `.openHand`, create a `TrainingBoard` fixture containing the highlighted hold, and create ordinary `WorkoutStep` values with the existing initializer and one or two `.kind(...)` targets. The mismatch case should provide a board containing both the target hold and a different highlighted hold.

  ```swift
  func testHoldCuePrefersSingleTargetStepGripOverride() {
      let hold = BoardHold(
          id: "cue-edge",
          name: "Cue edge",
          shortLabel: "E",
          detail: "Edge",
          kind: .edge,
          frame: HoldFrame(x: 0, y: 0, width: 1, height: 1),
          gripType: .openHand
      )
      let step = WorkoutStep(
          id: "cue-step",
          number: 1,
          title: "Cue step",
          instruction: "Cue instruction",
          accessory: "Cue accessory",
          duration: 10,
          phase: .hang,
          targets: [.kind(.edge)],
          gripType: .halfCrimp
      )

      let cue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board)

      XCTAssertEqual(cue?.hold, hold)
      XCTAssertEqual(cue?.gripType, .halfCrimp)
  }

  func testHoldCueFallsBackToBoardHoldGrip() {
      let hold = BoardHold(
          id: "cue-pocket",
          name: "Cue pocket",
          shortLabel: "P",
          detail: "Pocket",
          kind: .pocket,
          frame: HoldFrame(x: 0, y: 0, width: 1, height: 1),
          gripType: .threeFingerPocket
      )
      let step = WorkoutStep(
          id: "cue-step",
          number: 1,
          title: "Cue step",
          instruction: "Cue instruction",
          accessory: "Cue accessory",
          duration: 10,
          phase: .hang,
          targets: [.kind(.pocket)]
      )

      let cue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board)

      XCTAssertEqual(cue?.gripType, .threeFingerPocket)
  }

  func testHoldCueIsUnavailableForMultiTargetSteps() {
      let hold = BoardHold(
          id: "cue-edge",
          name: "Cue edge",
          shortLabel: "E",
          detail: "Edge",
          kind: .edge,
          frame: HoldFrame(x: 0, y: 0, width: 1, height: 1)
      )
      let step = WorkoutStep(
          id: "cue-step",
          number: 1,
          title: "Cue step",
          instruction: "Cue instruction",
          accessory: "Cue accessory",
          duration: 10,
          phase: .hang,
          targets: [.kind(.edge), .kind(.jug)]
      )

      XCTAssertNil(WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board))
  }
  ```

  Also cover a matching single-target hold and a different highlighted hold;
  the latter must return `nil` even when both holds are present on the board.

- [ ] **Step 2: Run the focused tests and verify RED**

  Run:

  ```bash
  rtk xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen \
    -derivedDataPath .context/DerivedData \
    -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
    -only-testing:HangTenTests/WorkoutTimelineTests
  ```

  Expected: compilation fails because `WorkoutHoldCue` and
  `WorkoutHoldCuePolicy` do not exist yet; no production implementation has
  been written at this point.

- [ ] **Step 3: Implement the minimal resolver**

  Add the following production implementation to `WorkoutTimeline.swift`:

  ```swift
  struct WorkoutHoldCue: Equatable {
      let hold: BoardHold
      let gripType: GripType
  }

  enum WorkoutHoldCuePolicy {
      static func resolve(
          step: WorkoutStep?,
          hold: BoardHold?,
          on board: TrainingBoard
      ) -> WorkoutHoldCue? {
          guard let step,
                step.targets.count == 1,
                let target = step.targets.first,
                let hold,
                BoardTargetResolver.resolveHoldIDs(for: target, on: board).contains(hold.id)
          else {
              return nil
          }

          return WorkoutHoldCue(
              hold: hold,
              gripType: step.gripType ?? hold.gripType
          )
      }
  }
  ```

- [ ] **Step 4: Run the focused tests and verify GREEN**

  Run the exact focused command from Step 2. Expected: the resolver override,
  board-grip fallback, matching, mismatching, and multi-target tests plus all
  existing `WorkoutTimelineTests` pass with zero failures.

- [ ] **Step 5: Commit the model/test task**

  ```bash
  rtk git add HangTen/Models/WorkoutTimeline.swift HangTenTests/WorkoutTimelineTests.swift
  rtk git commit -m "Add shared workout hold cue resolver"
  ```

### Task 2: Wire previews into portrait and landscape workout layouts

**Files:**
- Modify: `HangTen/Views/RootView.swift` in `WorkoutView.body`, `portraitSession`, and `landscapeSession`

**Interfaces:**
- Consumes `WorkoutHoldCuePolicy.resolve(step:hold:on:)` and `WorkoutHoldCue` from Task 1.
- Produces one `holdCue: WorkoutHoldCue?` from `highlightedStep` and the first board hold in `WorkoutView.body`.
- `portraitSession` and `landscapeSession` receive `holdCue` instead of separate `showsGenericHoldCue` and `activeHold` arguments.

- [ ] **Step 1: Confirm the pre-wiring behavior**

  Run the focused resolver/timeline tests from Task 1 and inspect the current
  `RootView.swift` conditions. Confirm that both orientation branches still
  exclude cues when `isResting` is true and that landscape still contains
  `.frame(height: isResting ? 60 : nil)` on its board map. Do not change the
  production code before the Task 1 tests are green.

- [ ] **Step 2: Resolve the cue once in `WorkoutView.body`**

  Keep the existing board-cue and highlight-ID derivation, then replace the
  separate generic-cue flag/hold values with:

  ```swift
  let activeHold = board.holds.first { highlightedHoldIDs.contains($0.id) }
  let holdCue = WorkoutHoldCuePolicy.resolve(step: highlightedStep, hold: activeHold, on: board)
  ```

  Pass `holdCue` into both `portraitSession(...)` and `landscapeSession(...)`.
  Remove the `showsGenericHoldCue` and `activeHold` parameters from those two
  functions after all call sites use `holdCue`.

- [ ] **Step 3: Render the same cue for active work and previews**

  In `portraitSession`, replace the current active-only condition with:

  ```swift
  if let holdCue, countdown == 0, !isComplete {
      GripDiagramView(hold: holdCue.hold, gripType: holdCue.gripType)
  }
  ```

  In `landscapeSession`, keep both side slots mounted on either side of the
  board using the shared `landscapeHandCueSlot(...)` helper so the board keeps
  the same footprint during previews and active work. The helper should always
  reserve the 142-point slot width and only render the cue card when the cue is
  available:

  ```swift
  landscapeHandCueSlot(
      holdCue: holdCue,
      countdown: countdown,
      isComplete: isComplete,
      side: .left
  )
  ```

  Keep the mirrored `.right` slot on the other side of the board. Do not add a
  cue for multi-target steps, because the resolver returns `nil` for them.

- [ ] **Step 4: Remove the landscape rest-only board height**

  Keep `BoardMapView` in the existing landscape cue row and its outer
  `maxHeight: 132` constraint, but remove only this child modifier:

  ```swift
  .frame(height: isResting ? 60 : nil)
  ```

  The board must therefore use the same constrained footprint during active
  work, timed rest previews, explicit rest previews, and final rest.

- [ ] **Step 5: Build and run focused tests**

  Run:

  ```bash
  rtk xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen \
    -derivedDataPath .context/DerivedData \
    -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
    -only-testing:HangTenTests/WorkoutTimelineTests
  rtk xcodebuild build -quiet -project HangTen.xcodeproj -scheme HangTen \
    -derivedDataPath .context/DerivedData \
    -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
  ```

  Expected: all focused tests pass and the app target builds successfully.

- [ ] **Step 6: Commit the workout-layout task**

  ```bash
  rtk git add HangTen/Views/RootView.swift
  rtk git commit -m "Show grip cues during hold previews"
  ```

### Task 3: Whole-branch verification and simulator review

**Files:**
- No production file changes expected; place derived data and screenshots in `.context/`

- [ ] **Step 1: Run the complete XCTest target**

  ```bash
  rtk xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen \
    -derivedDataPath .context/DerivedData \
    -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
  ```

- [ ] **Step 2: Build and visually inspect both orientations**

  Use the `validate-hang-ten-ios` workflow with a simulator named using
  `CONDUCTOR_WORKSPACE_NAME`. Inspect an active single-target step, a timed
  rest preview, an explicit rest preview, a multi-target step, and final rest
  in portrait and landscape. Confirm the preview shows the next step's grip
  label/hand cues, active and preview board highlights retain their existing
  semantic colors, the board keeps one footprint through work/rest, and
  countdown/completion states remain cue-free.

- [ ] **Step 3: Check the final diff and repository state**

  ```bash
  rtk git diff origin/main...HEAD --check
  rtk git status --short --branch
  ```

  Confirm only the approved spec, plan, model/test, and workout-layout files
  changed; all workspace-owned simulator and `.context` artifacts have been
  cleaned up before reporting completion.
