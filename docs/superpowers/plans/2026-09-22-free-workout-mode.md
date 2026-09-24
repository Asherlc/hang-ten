# Free Workout Mode Implementation Plan

> **Superseded 2026-09-23** by [`2026-09-23-free-workout-log-mode.md`](2026-09-23-free-workout-log-mode.md) (Strong-style live set log).
> Keep this file only as historical record of the timeline-driven free mode implementation.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Strong-like free workout mode: build custom hang/pull/rest workouts on the fly, run them with a timer plus manual override, edit weight/time/reps mid-session, log to history, optionally save as a reusable custom routine.

**Architecture:** Extend existing models (`TrainingPlan.isFreeWorkout`, `WorkoutTimeline.updateStep`), add a lightweight `FreeWorkoutDraft` model that converts to `TrainingPlan`, add two SwiftUI views (builder + session) reusing `WorkoutTimeline`, `WorkoutClock`, `ContactResolver`/`WorkoutHighlightResolver`, `BoardMapView`, `AppStore.markSessionComplete`, and `CustomRoutineStore` for save-as-plan.

**Tech Stack:** Swift, SwiftUI, XCTest / XCUITest, `xcodebuild`.

---

## File structure

| File | Change | Responsibility |
|------|--------|----------------|
| `HangTen/Models/TrainingModels.swift` | Modify: add `isFreeWorkout` to `TrainingPlan` | Flag distinguishing free workouts; defaults `false` so every existing call site compiles unchanged |
| `HangTen/Models/WorkoutTimeline.swift` | Modify: `steps`/`startOffsets`/`duration` become mutable; add `FreeWorkoutStepUpdates` + `updateStep(id:_:)` + `currentSteps` | Live in-session edits with offset recalculation; timer reads `step.duration` only |
| `HangTen/Models/FreeWorkoutDraft.swift` | Create | `FreeWorkoutExerciseKind`, `FreeWorkoutExerciseDraft`, `FreeWorkoutDraft` (Codable) + `trainingPlan()` conversion + `FreeWorkoutDraftStore` (last-draft persistence) |
| `HangTen/Models/FreeWorkoutSaver.swift` | Create | `FreeWorkoutSaver.routineDefinition(from:title:)` mapping a draft to `CustomRoutineDefinition` (generic target mode) for save-as-plan |
| `HangTen/Views/FreeWorkoutBuilderView.swift` | Create | Exercise list, add/remove Hang/Pull-up/Rest, per-exercise editor (hold, duration, rest, weight, reps, grip), pre-fill from last draft, Start |
| `HangTen/Views/FreeWorkoutSessionView.swift` | Create | Timer + board highlight + current-set card with tap-to-edit sheet + quick-adjust bar + Complete-early/Skip + finish/record |
| `HangTen/Views/TrainView.swift` | Modify: add "Start Free Workout" entry + sheet | Entry point inside Train tab |
| `HangTenTests/FreeWorkoutTests.swift` | Create | Unit tests for flag, draft conversion, draft store round-trip |
| `HangTenTests/WorkoutTimelineTests.swift` | Modify: append `FreeWorkoutTimelineUpdateTests` | Unit tests for `updateStep` |
| `HangTenTests/FreeWorkoutSaverTests.swift` | Create | Unit tests for saver mapping + validation-clean definitions |
| `HangTenUITests/FreeWorkoutUITests.swift` | Create | Smoke test: Train tab shows entry, builder opens |

Test command used throughout (run from repo root):

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/FreeWorkoutTests
```

---

### Task 1: `TrainingPlan.isFreeWorkout` flag

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Test: `HangTenTests/FreeWorkoutTests.swift` (create)

`TrainingPlan` uses the synthesized memberwise initializer (no custom `init`), so adding a defaulted property keeps all existing call sites compiling.

- [ ] **Step 1: Write the failing test**

Create `HangTenTests/FreeWorkoutTests.swift`:

```swift
import XCTest
@testable import HangTen

final class FreeWorkoutTests: XCTestCase {
    private func makePlan(isFreeWorkout: Bool = false) -> TrainingPlan {
        TrainingPlan(
            id: "free.test",
            title: "Free workout",
            subtitle: "Built on the fly",
            level: "Custom",
            sourceLabel: "Created in Hang Ten",
            sourceURL: nil,
            provenance: .custom,
            boardID: nil,
            steps: [],
            isFreeWorkout: isFreeWorkout
        )
    }

    func testTrainingPlanDefaultsToNonFreeWorkout() {
        let plan = TrainingPlan(
            id: "free.test",
            title: "Free workout",
            subtitle: "Built on the fly",
            level: "Custom",
            sourceLabel: "Created in Hang Ten",
            sourceURL: nil,
            provenance: .custom,
            boardID: nil,
            steps: []
        )
        XCTAssertFalse(plan.isFreeWorkout)
    }

    func testTrainingPlanCanBeMarkedFreeWorkout() {
        XCTAssertTrue(makePlan(isFreeWorkout: true).isFreeWorkout)
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/FreeWorkoutTests
```

Expected: BUILD FAILED with "incorrect argument label" / "missing argument for parameter `isFreeWorkout`" and "value of type `TrainingPlan` has no member `isFreeWorkout`".

- [ ] **Step 3: Write minimal implementation**

In `HangTen/Models/TrainingModels.swift`, inside `struct TrainingPlan`, after `let steps: [WorkoutStep]`, add:

```swift
    var isFreeWorkout: Bool = false
```

Note: `var`, not `let`. A `let` with a default value is excluded from Swift's
synthesized memberwise initializer, so `let` would make `init(..., isFreeWorkout: true)`
uncompilable (verified with `swiftc` repro during Task 1 review). Nothing in the
codebase mutates the flag after creation.

Full context of the edited region:

```swift
struct TrainingPlan: Identifiable, Hashable {
    let id: String
    let title: String
    let subtitle: String
    let level: String
    let sourceLabel: String
    let sourceURL: URL?
    let provenance: RoutineProvenance
    let boardID: String?
    let steps: [WorkoutStep]
    var isFreeWorkout: Bool = false
```

- [ ] **Step 4: Run test to verify it passes**

Run the same `xcodebuild test` command as Step 2.
Expected: `Test session results: all tests passed` (2 tests).

- [ ] **Step 5: Commit**

```bash
git add HangTen/Models/TrainingModels.swift HangTenTests/FreeWorkoutTests.swift
git commit -m "feat: add TrainingPlan.isFreeWorkout flag"
```

---

### Task 2: `WorkoutTimeline.updateStep` for live in-session edits

**Files:**
- Modify: `HangTen/Models/WorkoutTimeline.swift`
- Test: `HangTenTests/WorkoutTimelineTests.swift` (append)

The timer (`location(at:)`, `skipTarget`, `boardCue`) reads only `step.duration`, so updating the step-level duration plus clamping `timedWorkDuration` is sufficient; segments are left untouched.

- [ ] **Step 1: Write the failing tests**

Append to the end of `HangTenTests/WorkoutTimelineTests.swift`:

```swift
final class FreeWorkoutTimelineUpdateTests: XCTestCase {
    private func makeStep(id: String, duration: TimeInterval) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: 1,
            title: "Hang",
            instruction: "Hang.",
            accessory: "10s hang",
            duration: duration,
            phase: .hang,
            segments: [
                WorkoutSegment(kind: .work, target: .selfSelected, timing: .fixed, duration: duration)
            ]
        )
    }

    func testUpdateStepDurationShiftsLaterOffsets() {
        var timeline = WorkoutTimeline(steps: [
            makeStep(id: "a", duration: 10),
            makeStep(id: "b", duration: 20),
        ])
        XCTAssertTrue(timeline.updateStep(id: "a", FreeWorkoutStepUpdates(duration: 30)))
        XCTAssertEqual(timeline.duration, 50)
        XCTAssertEqual(timeline.startOffset(for: "b"), 30)
        XCTAssertEqual(timeline.currentSteps.first?.duration, 30)
    }

    func testUpdateStepWeightAndReps() {
        var timeline = WorkoutTimeline(steps: [makeStep(id: "a", duration: 10)])
        XCTAssertTrue(timeline.updateStep(
            id: "a",
            FreeWorkoutStepUpdates(externalLoadKGF: 10, repetitions: 5)
        ))
        XCTAssertEqual(timeline.currentSteps.first?.externalLoadKGF, 10)
        XCTAssertEqual(timeline.currentSteps.first?.repetitions, 5)
    }

    func testUpdateStepClampsTimedWorkToDuration() {
        var step = makeStep(id: "a", duration: 60)
        step = WorkoutStep(
            id: step.id, number: step.number, title: step.title,
            instruction: step.instruction, accessory: step.accessory,
            duration: step.duration, phase: step.phase, segments: step.segments,
            timedWorkDuration: 10
        )
        var timeline = WorkoutTimeline(steps: [step])
        XCTAssertTrue(timeline.updateStep(id: "a", FreeWorkoutStepUpdates(duration: 5)))
        XCTAssertEqual(timeline.currentSteps.first?.timedWorkDuration, 5)
    }

    func testUpdateUnknownStepReturnsFalse() {
        var timeline = WorkoutTimeline(steps: [makeStep(id: "a", duration: 10)])
        XCTAssertFalse(timeline.updateStep(id: "missing", FreeWorkoutStepUpdates(duration: 30)))
        XCTAssertEqual(timeline.duration, 10)
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/FreeWorkoutTimelineUpdateTests
```

Expected: BUILD FAILED with "value of type `WorkoutTimeline` has no member `updateStep`" (plus missing `FreeWorkoutStepUpdates`, `currentSteps`).

- [ ] **Step 3: Write minimal implementation**

In `HangTen/Models/WorkoutTimeline.swift`, make three edits.

Edit A — add the updates struct just before `struct WorkoutTimeline`:

```swift
struct FreeWorkoutStepUpdates: Equatable {
    var duration: TimeInterval?
    var timedWorkDuration: TimeInterval?
    var externalLoadKGF: Double?
    var repetitions: Int?

    init(
        duration: TimeInterval? = nil,
        timedWorkDuration: TimeInterval? = nil,
        externalLoadKGF: Double? = nil,
        repetitions: Int? = nil
    ) {
        self.duration = duration
        self.timedWorkDuration = timedWorkDuration
        self.externalLoadKGF = externalLoadKGF
        self.repetitions = repetitions
    }
}
```

Edit B — change the stored properties from immutable to mutable:

```swift
struct WorkoutTimeline {
    private var steps: [WorkoutStep]
    private var startOffsets: [TimeInterval]
```

and

```swift
    private(set) var duration: TimeInterval
```

Edit C — add the accessor and mutation method inside `struct WorkoutTimeline` (place right after `let duration` declaration area, i.e. after the `init`):

```swift
    var currentSteps: [WorkoutStep] {
        steps
    }

    /// Applies Strong-style live edits to the current or a future step.
    /// Past steps must never be edited by callers. Returns false when no
    /// step matches `id`, leaving the timeline untouched.
    @discardableResult
    mutating func updateStep(id: String, _ updates: FreeWorkoutStepUpdates) -> Bool {
        guard let index = steps.firstIndex(where: { $0.id == id }) else {
            return false
        }
        let old = steps[index]
        let newDuration = max(1, updates.duration ?? old.duration)
        let requestedTimedWork = updates.timedWorkDuration ?? old.timedWorkDuration
        let newTimedWork = requestedTimedWork.map { min(max($0, 0), newDuration) }
        steps[index] = WorkoutStep(
            id: old.id,
            number: old.number,
            title: old.title,
            instruction: old.instruction,
            accessory: old.accessory,
            duration: newDuration,
            phase: old.phase,
            segments: old.segments,
            gripType: old.gripType,
            fingerConfiguration: old.fingerConfiguration,
            handUse: old.handUse,
            side: old.side,
            action: old.action,
            repetitions: updates.repetitions ?? old.repetitions,
            externalLoadKGF: updates.externalLoadKGF ?? old.externalLoadKGF,
            timedWorkDuration: newTimedWork
        )
        var cursor: TimeInterval = 0
        startOffsets = steps.map { step in
            defer { cursor += step.duration }
            return cursor
        }
        duration = cursor
        return true
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run the same `xcodebuild test` command as Step 2.
Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add HangTen/Models/WorkoutTimeline.swift HangTenTests/WorkoutTimelineTests.swift
git commit -m "feat: add WorkoutTimeline.updateStep for live free-workout edits"
```

---

### Task 3: `FreeWorkoutDraft` model, `trainingPlan()` conversion, last-draft store

**Files:**
- Create: `HangTen/Models/FreeWorkoutDraft.swift`
- Test: `HangTenTests/FreeWorkoutTests.swift` (append new test classes)

Design decisions locked here:
- Pull-ups use `phase: .pull, action: .loadedLift` with `repetitions` = rep count and `externalLoadKGF` = added load (nil when 0). This satisfies `WorkoutStepSemantics.hasValidActionAndRepetitions` and reuses `WorkoutLiftCompletion` rep-tapping.
- Hangs use `phase: .hang, action: .hang` with `repetitions: nil` and `externalLoadKGF` = added load.
- Work+rest is one step: `duration = work + rest`, `timedWorkDuration = work` (nil when no rest), segments `[work(fixed), rest(fixed)?]`. The timer and `hasRestInterval`/`boardCue` already handle this shape.
- Hold targets are generic `ContactRequirement.kind` unless the builder picked an exact board contact (stored as `contactID` + snapshot of kind/shape/depth/fingerCapacity, built with the same 7-argument initializer `CustomRoutineEditorView.toggleHold` uses).

- [ ] **Step 1: Write the failing tests**

Append to `HangTenTests/FreeWorkoutTests.swift`:

```swift
final class FreeWorkoutDraftTests: XCTestCase {
    func testHangExerciseConvertsToWorkPlusRestStep() {
        var draft = FreeWorkoutDraft(title: "Free workout", exercises: [])
        draft.exercises.append(FreeWorkoutExerciseDraft(
            kind: .hang,
            title: "Jug hang",
            holdKind: .jug,
            workDuration: 10,
            restDuration: 50,
            externalLoadKGF: 5,
            repetitions: nil,
            gripType: .openHand
        ))
        let plan = draft.trainingPlan()
        XCTAssertTrue(plan.isFreeWorkout)
        XCTAssertEqual(plan.steps.count, 1)
        let step = plan.steps[0]
        XCTAssertEqual(step.duration, 60)
        XCTAssertEqual(step.timedWorkDuration, 10)
        XCTAssertEqual(step.phase, .hang)
        XCTAssertEqual(step.externalLoadKGF, 5)
        XCTAssertEqual(step.segments.count, 2)
        XCTAssertEqual(step.segments[0].kind, .work)
        XCTAssertEqual(step.segments[1].kind, .rest)
    }

    func testPullExerciseUsesLoadedLiftSemantics() {
        var draft = FreeWorkoutDraft(title: "Free workout", exercises: [])
        draft.exercises.append(FreeWorkoutExerciseDraft(
            kind: .pull,
            title: "Pull-ups",
            holdKind: .jug,
            workDuration: 25,
            restDuration: 0,
            externalLoadKGF: nil,
            repetitions: 5,
            gripType: nil
        ))
        let step = draft.trainingPlan().steps[0]
        XCTAssertEqual(step.phase, .pull)
        XCTAssertEqual(step.action, .loadedLift)
        XCTAssertEqual(step.repetitions, 5)
        XCTAssertNil(step.repetitions.flatMap { $0 > 0 ? nil : $0 })
        XCTAssertTrue(WorkoutStepSemantics.hasValidActionAndRepetitions(step.action, step.repetitions))
        XCTAssertEqual(step.duration, 25)
        XCTAssertNil(step.timedWorkDuration)
    }

    func testRestExerciseConvertsToRestStep() {
        var draft = FreeWorkoutDraft(title: "Free workout", exercises: [])
        draft.exercises.append(FreeWorkoutExerciseDraft(kind: .rest, workDuration: 0, restDuration: 120))
        let step = draft.trainingPlan().steps[0]
        XCTAssertTrue(step.isRestStep)
        XCTAssertEqual(step.duration, 120)
    }

    func testDraftStoreRoundTrip() {
        let defaults = UserDefaults(suiteName: "FreeWorkoutDraftTests")!
        defaults.removePersistentDomain(forName: "FreeWorkoutDraftTests")
        var draft = FreeWorkoutDraft(title: "Evening session", exercises: [])
        draft.exercises.append(FreeWorkoutExerciseDraft(kind: .hang, workDuration: 7, restDuration: 53))
        FreeWorkoutDraftStore.save(draft, defaults: defaults)
        XCTAssertEqual(FreeWorkoutDraftStore.load(defaults: defaults), draft)
        defaults.removePersistentDomain(forName: "FreeWorkoutDraftTests")
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/FreeWorkoutDraftTests
```

Expected: BUILD FAILED with "cannot find `FreeWorkoutDraft` / `FreeWorkoutExerciseDraft` / `FreeWorkoutDraftStore` in scope".

- [ ] **Step 3: Write minimal implementation**

Create `HangTen/Models/FreeWorkoutDraft.swift` with the complete content:

```swift
import Foundation

enum FreeWorkoutExerciseKind: String, Codable, CaseIterable, Hashable {
    case hang
    case pull
    case rest

    var label: String {
        switch self {
        case .hang: "Hang"
        case .pull: "Pull-ups"
        case .rest: "Rest"
        }
    }

    var defaultTitle: String {
        switch self {
        case .hang: "Hang"
        case .pull: "Pull-ups"
        case .rest: "Rest"
        }
    }
}

struct FreeWorkoutExerciseDraft: Codable, Hashable, Identifiable {
    var id: String
    var kind: FreeWorkoutExerciseKind
    var title: String
    var holdKind: HoldKind?
    /// Exact board contact when the athlete picked a specific hold.
    var contactID: String?
    var contactKind: HoldKind?
    var contactShape: HoldShape?
    var contactDepth: HoldDepth?
    var contactFingerCapacity: Int?
    var workDuration: TimeInterval
    var restDuration: TimeInterval
    var externalLoadKGF: Double?
    var repetitions: Int?
    var gripType: GripType?

    init(
        id: String = UUID().uuidString,
        kind: FreeWorkoutExerciseKind,
        title: String? = nil,
        holdKind: HoldKind? = nil,
        contactID: String? = nil,
        contactKind: HoldKind? = nil,
        contactShape: HoldShape? = nil,
        contactDepth: HoldDepth? = nil,
        contactFingerCapacity: Int? = nil,
        workDuration: TimeInterval = 10,
        restDuration: TimeInterval = 60,
        externalLoadKGF: Double? = nil,
        repetitions: Int? = nil,
        gripType: GripType? = nil
    ) {
        self.id = id
        self.kind = kind
        self.title = title ?? kind.defaultTitle
        self.holdKind = holdKind
        self.contactID = contactID
        self.contactKind = contactKind
        self.contactShape = contactShape
        self.contactDepth = contactDepth
        self.contactFingerCapacity = contactFingerCapacity
        self.workDuration = workDuration
        self.restDuration = restDuration
        self.externalLoadKGF = externalLoadKGF
        self.repetitions = repetitions
        self.gripType = gripType
    }

    static func hang() -> FreeWorkoutExerciseDraft {
        FreeWorkoutExerciseDraft(kind: .hang, holdKind: .jug, workDuration: 10, restDuration: 60)
    }

    static func pull() -> FreeWorkoutExerciseDraft {
        FreeWorkoutExerciseDraft(
            kind: .pull, holdKind: .jug, workDuration: 25, restDuration: 60,
            repetitions: 5
        )
    }

    static func rest() -> FreeWorkoutExerciseDraft {
        FreeWorkoutExerciseDraft(kind: .rest, workDuration: 0, restDuration: 120)
    }
}

struct FreeWorkoutDraft: Codable, Hashable {
    var title: String
    var exercises: [FreeWorkoutExerciseDraft]

    static var starter: FreeWorkoutDraft {
        FreeWorkoutDraft(title: "Free workout", exercises: [.hang(), .pull(), .rest()])
    }

    func trainingPlan() -> TrainingPlan {
        let steps = exercises.enumerated().map { index, exercise in
            step(for: exercise, number: index + 1)
        }
        return TrainingPlan(
            id: "free.workout",
            title: title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "Free workout" : title,
            subtitle: "Built on the fly",
            level: "Custom",
            sourceLabel: "Created in Hang Ten",
            sourceURL: nil,
            provenance: .custom,
            boardID: nil,
            steps: steps,
            isFreeWorkout: true
        )
    }

    private func step(for exercise: FreeWorkoutExerciseDraft, number: Int) -> WorkoutStep {
        switch exercise.kind {
        case .rest:
            let duration = max(1, exercise.restDuration)
            return WorkoutStep(
                id: "free.\(exercise.id)",
                number: number,
                title: exercise.title,
                instruction: "Rest.",
                accessory: FreeWorkoutDraft.durationLabel(duration) + " rest",
                duration: duration,
                phase: .rest,
                segments: [
                    WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: duration)
                ]
            )
        case .hang:
            return timedStep(
                for: exercise,
                number: number,
                phase: .hang,
                action: .hang,
                instruction: "Hang for \(Int(exercise.workDuration)) seconds."
            )
        case .pull:
            let reps = max(1, exercise.repetitions ?? 5)
            let step = timedStep(
                for: exercise,
                number: number,
                phase: .pull,
                action: .loadedLift,
                instruction: "Do \(reps) pull-ups."
            )
            return WorkoutStep(
                id: step.id, number: step.number, title: step.title,
                instruction: step.instruction, accessory: "\(reps) reps",
                duration: step.duration, phase: step.phase, segments: step.segments,
                gripType: step.gripType, handUse: step.handUse, side: step.side,
                action: step.action, repetitions: reps,
                externalLoadKGF: step.externalLoadKGF,
                timedWorkDuration: step.timedWorkDuration
            )
        }
    }

    private func timedStep(
        for exercise: FreeWorkoutExerciseDraft,
        number: Int,
        phase: WorkoutPhase,
        action: WorkoutAction,
        instruction: String
    ) -> WorkoutStep {
        let work = max(1, exercise.workDuration)
        let rest = max(0, exercise.restDuration)
        var segments = [
            WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets(workRequirements(for: exercise)),
                timing: .fixed,
                duration: work
            )
        ]
        if rest > 0 {
            segments.append(
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: rest)
            )
        }
        let load = (exercise.externalLoadKGF ?? 0) == 0 ? nil : exercise.externalLoadKGF
        return WorkoutStep(
            id: "free.\(exercise.id)",
            number: number,
            title: exercise.title,
            instruction: instruction,
            accessory: "\(Int(work))s \(phase.label.lowercased())",
            duration: work + rest,
            phase: phase,
            segments: segments,
            gripType: exercise.gripType,
            handUse: .double,
            side: .both,
            action: action,
            externalLoadKGF: load,
            timedWorkDuration: rest > 0 ? work : nil
        )
    }

    private func workRequirements(for exercise: FreeWorkoutExerciseDraft) -> [ContactRequirement] {
        if let contactID = exercise.contactID {
            return [
                ContactRequirement(
                    contactID: contactID,
                    kind: exercise.contactKind,
                    shape: exercise.contactShape,
                    depth: exercise.contactDepth,
                    fingerCapacity: exercise.contactFingerCapacity,
                    handCapacity: nil,
                    selection: .single
                )
            ]
        }
        guard let holdKind = exercise.holdKind else { return [] }
        return [.kind(holdKind)]
    }

    static func durationLabel(_ duration: TimeInterval) -> String {
        let seconds = Int(duration)
        if seconds >= 60 && seconds % 60 == 0 {
            return "\(seconds / 60)m"
        }
        if seconds >= 60 {
            return "\(seconds / 60)m \(seconds % 60)s"
        }
        return "\(seconds)s"
    }
}

enum FreeWorkoutDraftStore {
    static let lastDraftKey = "HangTen.freeWorkout.lastDraft.v1"

    static func load(defaults: UserDefaults = .standard) -> FreeWorkoutDraft? {
        guard let data = defaults.data(forKey: lastDraftKey) else { return nil }
        return try? JSONDecoder().decode(FreeWorkoutDraft.self, from: data)
    }

    static func save(_ draft: FreeWorkoutDraft, defaults: UserDefaults = .standard) {
        guard let data = try? JSONEncoder().encode(draft) else { return }
        defaults.set(data, forKey: lastDraftKey)
    }
}
```

Notes for the worker: `ContactRequirement(contactID:kind:shape:depth:fingerCapacity:handCapacity:selection:)` is the exact 7-argument initializer `CustomRoutineEditorView.toggleHold` uses; `.kind(_:)` is the static helper the Metolius seed catalog uses (e.g. `.kind(.jug)`). `WorkoutStep` full initializer order matches `TrainingModels.swift`. If the compiler rejects either, read the `ContactRequirement` declaration and adjust the call to the verified signature — do not invent a new initializer.

- [ ] **Step 4: Run tests to verify they pass**

Run the same `xcodebuild test` command as Step 2.
Expected: all 4 tests pass. (The odd `XCTAssertNil(step.repetitions.flatMap { $0 > 0 ? nil : $0 })` line asserts repetitions is present and positive.)

- [ ] **Step 5: Commit**

```bash
git add HangTen/Models/FreeWorkoutDraft.swift HangTenTests/FreeWorkoutTests.swift
git commit -m "feat: add FreeWorkoutDraft model and plan conversion"
```

---

### Task 4: `FreeWorkoutBuilderView` + Train tab entry

**Files:**
- Create: `HangTen/Views/FreeWorkoutBuilderView.swift`
- Modify: `HangTen/Views/TrainView.swift`
- Test: `HangTenUITests/FreeWorkoutUITests.swift` (create)

Builder behavior: loads `FreeWorkoutDraftStore.load()` ?? `.starter` on appear; every edit autosaves the draft; hold picker offers "Any hold" + generic kinds + exact board contacts from `store.selectedBoard`; Start button builds the plan and pushes the session.

- [ ] **Step 1: Write the UI smoke test (fails: identifiers don't exist yet)**

Create `HangTenUITests/FreeWorkoutUITests.swift`:

```swift
import XCTest

final class FreeWorkoutUITests: XCTestCase {
    func testFreeWorkoutBuilderOpensFromTrain() {
        let app = XCUIApplication()
        app.launch()
        let entry = app.buttons["train.freeWorkout"]
        XCTAssertTrue(entry.waitForExistence(timeout: 10))
        entry.tap()
        XCTAssertTrue(app.navigationBars["Free workout"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.addHang"].exists)
        XCTAssertTrue(app.buttons["freeWorkout.start"].exists)
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenUITests/FreeWorkoutUITests
```

Expected: FAIL — `train.freeWorkout` button never appears.

- [ ] **Step 3: Implement the builder view**

Create `HangTen/Views/FreeWorkoutBuilderView.swift` with the complete content:

```swift
import SwiftUI

struct FreeWorkoutBuilderView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss
    @State private var draft: FreeWorkoutDraft = FreeWorkoutDraftStore.load() ?? .starter
    @State private var sessionPlan: TrainingPlan?
    @State private var sessionDraft: FreeWorkoutDraft?
    @State private var saveAsPlan = false

    var body: some View {
        NavigationStack {
            List {
                Section("Workout") {
                    TextField("Name", text: $draft.title)
                        .accessibilityIdentifier("freeWorkout.name")
                        .onChange(of: draft.title) { _, _ in persist() }
                    ForEach($draft.exercises) { $exercise in
                        FreeWorkoutExerciseEditor(
                            exercise: $exercise,
                            board: store.selectedBoard,
                            onDelete: { delete(exercise) }
                        )
                    }
                    .onMove { offsets, destination in
                        draft.exercises.move(fromOffsets: offsets, toOffset: destination)
                        persist()
                    }
                }
                Section("Add") {
                    Button {
                        draft.exercises.append(.hang())
                        persist()
                    } label: {
                        Label("Add hang", systemImage: "plus")
                    }
                    .accessibilityIdentifier("freeWorkout.addHang")
                    Button {
                        draft.exercises.append(.pull())
                        persist()
                    } label: {
                        Label("Add pull-ups", systemImage: "plus")
                    }
                    .accessibilityIdentifier("freeWorkout.addPull")
                    Button {
                        draft.exercises.append(.rest())
                        persist()
                    } label: {
                        Label("Add rest", systemImage: "plus")
                    }
                    .accessibilityIdentifier("freeWorkout.addRest")
                }
                Section("Finish") {
                    Toggle("Save as reusable routine", isOn: $saveAsPlan)
                        .accessibilityIdentifier("freeWorkout.saveAsPlan")
                    Button("Start workout", action: start)
                        .buttonStyle(.borderedProminent)
                        .tint(.hangGreenDark)
                        .disabled(draft.exercises.isEmpty)
                        .accessibilityIdentifier("freeWorkout.start")
                }
            }
            .navigationTitle("Free workout")
            .navigationDestination(item: $sessionPlan) { plan in
                if let sessionDraft {
                    FreeWorkoutSessionView(plan: plan, draft: sessionDraft, saveAsPlan: saveAsPlan)
                }
            }
        }
        .accessibilityIdentifier("freeWorkout.builder")
    }

    private func delete(_ exercise: FreeWorkoutExerciseDraft) {
        draft.exercises.removeAll { $0.id == exercise.id }
        persist()
    }

    private func persist() {
        FreeWorkoutDraftStore.save(draft)
    }

    private func start() {
        persist()
        sessionDraft = draft
        sessionPlan = draft.trainingPlan()
    }
}

private struct FreeWorkoutExerciseEditor: View {
    @Binding var exercise: FreeWorkoutExerciseDraft
    let board: BoardRevision
    let onDelete: () -> Void

    var body: some View {
        DisclosureGroup(exercise.title.isEmpty ? exercise.kind.label : exercise.title) {
            if exercise.kind != .rest {
                TextField("Title", text: $exercise.title)
                    .accessibilityIdentifier("freeWorkout.exerciseTitle.\(exercise.id)")
                holdPicker
                gripPicker
            }
            if exercise.kind == .hang {
                durationField(title: "Hang (seconds)", value: $exercise.workDuration)
                durationField(title: "Rest after (seconds)", value: $exercise.restDuration)
                loadField
            } else if exercise.kind == .pull {
                Stepper(
                    "Reps: \(exercise.repetitions ?? 5)",
                    value: repBinding,
                    in: 1...100
                )
                .accessibilityIdentifier("freeWorkout.exerciseReps.\(exercise.id)")
                durationField(title: "Time cap (seconds)", value: $exercise.workDuration)
                durationField(title: "Rest after (seconds)", value: $exercise.restDuration)
                loadField
            } else {
                durationField(title: "Rest (seconds)", value: $exercise.restDuration)
            }
            Button("Delete", role: .destructive, action: onDelete)
                .accessibilityIdentifier("freeWorkout.deleteExercise.\(exercise.id)")
        }
    }

    private var repBinding: Binding<Int> {
        Binding(
            get: { exercise.repetitions ?? 5 },
            set: { exercise.repetitions = $0 }
        )
    }

    @ViewBuilder
    private var holdPicker: some View {
        Picker("Hold", selection: holdSelection) {
            Text("Any hold").tag(FreeWorkoutHoldSelection.any)
            ForEach(HoldKind.allCases) { kind in
                Text(kind.label).tag(FreeWorkoutHoldSelection.generic(kind))
            }
            ForEach(board.contacts) { contact in
                Text(contact.name).tag(FreeWorkoutHoldSelection.exact(contact.id))
            }
        }
        .accessibilityIdentifier("freeWorkout.exerciseHold.\(exercise.id)")
    }

    private var holdSelection: Binding<FreeWorkoutHoldSelection> {
        Binding(
            get: {
                if let contactID = exercise.contactID {
                    return .exact(contactID)
                }
                if let holdKind = exercise.holdKind {
                    return .generic(holdKind)
                }
                return .any
            },
            set: { selection in
                switch selection {
                case .any:
                    exercise.contactID = nil
                    exercise.contactKind = nil
                    exercise.contactShape = nil
                    exercise.contactDepth = nil
                    exercise.contactFingerCapacity = nil
                    exercise.holdKind = nil
                case .generic(let kind):
                    exercise.contactID = nil
                    exercise.contactKind = nil
                    exercise.contactShape = nil
                    exercise.contactDepth = nil
                    exercise.contactFingerCapacity = nil
                    exercise.holdKind = kind
                case .exact(let contactID):
                    guard let contact = board.contacts.first(where: { $0.id == contactID }) else { return }
                    exercise.contactID = contact.id
                    exercise.contactKind = contact.kind
                    exercise.contactShape = contact.shape
                    exercise.contactDepth = contact.depth
                    exercise.contactFingerCapacity = contact.fingerCapacity
                    exercise.holdKind = nil
                }
            }
        )
    }

    @ViewBuilder
    private var gripPicker: some View {
        Picker("Grip", selection: $exercise.gripType) {
            Text("No cue").tag(GripType?.none)
            ForEach(GripType.allCases) { grip in
                Text(grip.label).tag(Optional(grip))
            }
        }
        .accessibilityIdentifier("freeWorkout.exerciseGrip.\(exercise.id)")
    }

    private func durationField(title: String, value: Binding<TimeInterval>) -> some View {
        TextField(title, value: value, format: .number)
            .keyboardType(.decimalPad)
    }

    @ViewBuilder
    private var loadField: some View {
        TextField(
            "Added weight (kg; 0 or empty for bodyweight)",
            value: $exercise.externalLoadKGF,
            format: .number
        )
        .keyboardType(.numbersAndPunctuation)
        .accessibilityIdentifier("freeWorkout.exerciseLoad.\(exercise.id)")
    }
}

private enum FreeWorkoutHoldSelection: Hashable {
    case any
    case generic(HoldKind)
    case exact(String)
}
```

Notes for the worker: `HoldKind.allCases`/`GripType.allCases`/`HoldShape`/`HoldDepth`/`BoardRevision.contacts`/`PhysicalContact` fields are verified in `TrainingModels.swift`. `BoardMapView` is not needed in the builder (session resolves highlights). If `FreeWorkoutSessionView` does not exist yet, this file will not compile until Task 5 — that is expected; do not stub it.

- [ ] **Step 4: Add the Train tab entry point**

In `HangTen/Views/TrainView.swift`, add state and a button. Edit A — add after `@State private var reviewDestination`:

```swift
    @State private var showsFreeWorkout = false
```

Edit B — in `favoritesSection`, in both the empty branch (after the "Browse plans" button) and the non-empty branch (after the `ForEach`), add:

```swift
                Button("Start Free Workout") {
                    showsFreeWorkout = true
                }
                .buttonStyle(.borderedProminent)
                .tint(.hangGreenDark)
                .accessibilityIdentifier("train.freeWorkout")
```

For the non-empty branch, wrap the existing `VStack` content: append the button inside the `VStack(alignment: .leading, spacing: 12)` after the `ForEach` block.

Edit C — present the builder. Attach to the outer `NavigationStack` (next to the existing `.navigationDestination` modifiers):

```swift
            .sheet(isPresented: $showsFreeWorkout) {
                FreeWorkoutBuilderView()
                    .environmentObject(store)
            }
```

- [ ] **Step 5: Run the UI test to verify it passes**

Run the same `xcodebuild test` command as Step 2.
Expected: passes — entry button exists, builder opens, Add/Start buttons exist. (The session itself is covered in Task 5.)

- [ ] **Step 6: Commit**

```bash
git add HangTen/Views/FreeWorkoutBuilderView.swift HangTen/Views/TrainView.swift HangTenUITests/FreeWorkoutUITests.swift
git commit -m "feat: add free workout builder and Train tab entry"
```

---

### Task 5: `FreeWorkoutSessionView` with timer, live editing, manual override

**Files:**
- Create: `HangTen/Views/FreeWorkoutSessionView.swift`
- Test: extend `HangTenUITests/FreeWorkoutUITests.swift` (append session test)

Session behavior, all reusing verified APIs:
- Elapsed time: `WorkoutClock` (`start(initialCountdown:)`, `elapsed`, `pause()`, `seek(to:)`) + `TimelineView(.periodic(...))` for ticks.
- Step lookup: `timeline.step(at:)` / `timeline.elapsedInStep(at:)` / `timeline.skipTarget(from:)` / `timeline.nextWorkStep` / `timeline.boardCue(...)`.
- Board highlight: `WorkoutHighlightResolver.contactIDs(for:on:)` + `store.board(for: plan)` + `BoardMapView(board:highlightedHoldIDs:)`.
- Rep tapping for pull-ups: `WorkoutLiftCompletion` (`completeLift(for:)`, `completedRepetitions(for:)`, `setExternalLoadKGF`, `externalLoadKGF(for:)`).
- Complete-early / Skip: `clock.seek(to: timeline.skipTarget(from: elapsed) ?? timeline.duration)`.
- Live edit: `timeline.updateStep(id, FreeWorkoutStepUpdates(...))` then refresh `steps = timeline.currentSteps`.
- Finish: build `WorkoutStepMeasurement`s (initializer verified in `MotherboardModels.swift`), build `WorkoutSessionRecord` (initializer verified), call `store.markSessionComplete(plan, startDate:endDate:sessionSteps:session:)` (overload verified in `AppStore.swift`), then optional save-as-plan via `FreeWorkoutSaver` (Task 6) and dismiss.

- [ ] **Step 1: Write the session UI test (fails: session identifiers don't exist yet)**

Append to `HangTenUITests/FreeWorkoutUITests.swift`:

```swift
    func testFreeWorkoutSessionStartsAndShowsControls() {
        let app = XCUIApplication()
        app.launch()
        app.buttons["train.freeWorkout"].tap()
        XCTAssertTrue(app.navigationBars["Free workout"].waitForExistence(timeout: 10))
        app.buttons["freeWorkout.start"].tap()
        XCTAssertTrue(app.otherElements["freeWorkout.session"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.completeSet"].exists)
        XCTAssertTrue(app.buttons["freeWorkout.skip"].exists)
        XCTAssertTrue(app.buttons["freeWorkout.finish"].exists)
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenUITests/FreeWorkoutUITests/testFreeWorkoutSessionStartsAndShowsControls
```

Expected: FAIL — `freeWorkout.session` never appears (builder's Start pushes nothing until the session view exists).

- [ ] **Step 3: Implement the session view**

Create `HangTen/Views/FreeWorkoutSessionView.swift` with the complete content:

```swift
import SwiftUI

struct FreeWorkoutSessionView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss

    let plan: TrainingPlan
    let draft: FreeWorkoutDraft
    let saveAsPlan: Bool

    @State private var steps: [WorkoutStep]
    @State private var timeline: WorkoutTimeline
    @State private var clock = WorkoutClock()
    @State private var liftCompletion = WorkoutLiftCompletion()
    @State private var startedAt = Date()
    @State private var isPaused = false
    @State private var editingStepID: String?
    @State private var didFinish = false
    @State private var saveError: String?

    init(plan: TrainingPlan, draft: FreeWorkoutDraft, saveAsPlan: Bool) {
        self.plan = plan
        self.draft = draft
        self.saveAsPlan = saveAsPlan
        _steps = State(initialValue: plan.steps)
        _timeline = State(initialValue: WorkoutTimeline(steps: plan.steps))
    }

    private var board: BoardRevision {
        store.board(for: plan)
    }

    var body: some View {
        TimelineView(.periodic(from: .now, by: 0.25)) { _ in
            sessionContent
        }
        .navigationTitle(plan.title)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear(perform: startIfNeeded)
        .sheet(item: $editingStepID) { stepID in
            if let step = steps.first(where: { $0.id == stepID }) {
                FreeWorkoutStepEditSheet(
                    step: step,
                    liftCompletion: liftCompletion
                ) { updates in
                    apply(updates, to: stepID)
                }
            }
        }
        .alert("Couldn’t save routine", isPresented: saveAlertBinding) {
            Button("OK", role: .cancel) { saveError = nil }
        } message: {
            Text(saveError ?? "An unknown error occurred.")
        }
        .accessibilityIdentifier("freeWorkout.session")
    }

    private var sessionContent: some View {
        let elapsed = clock.elapsed
        let isComplete = elapsed >= timeline.duration
        let step = timeline.step(at: elapsed)
        let highlightedIDs = Set(step.map { WorkoutHighlightResolver.contactIDs(for: $0, on: board) } ?? [])

        return VStack(alignment: .leading, spacing: 16) {
            if let step {
                currentSetCard(step: step, elapsed: elapsed, isComplete: isComplete)
            }
            BoardMapView(board: board, highlightedHoldIDs: highlightedIDs)
                .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            quickAdjustBar(step: step)
            controlBar(step: step, elapsed: elapsed, isComplete: isComplete)
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 18)
        .background(Color.hangBackground)
    }

    private func currentSetCard(step: WorkoutStep, elapsed: TimeInterval, isComplete: Bool) -> some View {
        let remaining = max(0, step.duration - timeline.elapsedInStep(at: elapsed))
        return Button {
            editingStepID = step.id
        } label: {
            VStack(alignment: .leading, spacing: 6) {
                SectionLabel(title: isComplete ? "Finished" : "Current set · tap to edit")
                Text(step.title)
                    .font(.system(size: 21, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                HStack(spacing: 12) {
                    Text(FreeWorkoutDraft.durationLabel(remaining) + " left")
                    if let load = step.externalLoadKGF {
                        Text("+\(load.formatted()) kg")
                    }
                    if let reps = step.repetitions {
                        let done = liftCompletion.completedRepetitions(for: step)
                        Text("\(done)/\(reps) reps")
                    }
                }
                .font(.system(size: 14, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
            }
            .hangCard()
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("freeWorkout.currentSet")
    }

    @ViewBuilder
    private func quickAdjustBar(step: WorkoutStep?) -> some View {
        if let step, !step.isRestStep {
            HStack(spacing: 10) {
                if step.externalLoadKGF != nil || step.action == .loadedLift || step.phase == .hang {
                    adjustGroup(title: "Weight", down: {
                        nudge(step, FreeWorkoutStepUpdates(externalLoadKGF: max(0, (step.externalLoadKGF ?? 0) - 1)))
                    }, up: {
                        nudge(step, FreeWorkoutStepUpdates(externalLoadKGF: (step.externalLoadKGF ?? 0) + 1))
                    })
                }
                adjustGroup(title: "Time", down: {
                    nudge(step, FreeWorkoutStepUpdates(duration: step.duration - 5))
                }, up: {
                    nudge(step, FreeWorkoutStepUpdates(duration: step.duration + 5))
                })
                if step.action == .loadedLift {
                    adjustGroup(title: "Reps", down: {
                        nudge(step, FreeWorkoutStepUpdates(repetitions: max(1, (step.repetitions ?? 1) - 1)))
                    }, up: {
                        nudge(step, FreeWorkoutStepUpdates(repetitions: (step.repetitions ?? 1) + 1))
                    })
                    Button("Log rep") {
                        liftCompletion.completeLift(for: step)
                    }
                    .buttonStyle(.bordered)
                    .tint(.hangGreenDark)
                    .accessibilityIdentifier("freeWorkout.logRep")
                }
            }
            .font(.system(size: 14, weight: .bold, design: .rounded))
        }
    }

    private func adjustGroup(title: String, down: @escaping () -> Void, up: @escaping () -> Void) -> some View {
        HStack(spacing: 6) {
            Button("−", action: down)
                .accessibilityIdentifier("freeWorkout.adjustDown.\(title)")
            Text(title)
            Button("+", action: up)
                .accessibilityIdentifier("freeWorkout.adjustUp.\(title)")
        }
        .buttonStyle(.bordered)
        .tint(.hangGreenDark)
    }

    @ViewBuilder
    private func controlBar(step: WorkoutStep?, elapsed: TimeInterval, isComplete: Bool) -> some View {
        HStack(spacing: 10) {
            Button(isPaused ? "Resume" : "Pause") {
                isPaused ? clock.start(initialCountdown: 0) : clock.pause()
                isPaused.toggle()
            }
            .buttonStyle(.bordered)
            .tint(.hangGreenDark)
            Button("Complete set") {
                clock.seek(to: timeline.skipTarget(from: elapsed) ?? timeline.duration)
            }
            .buttonStyle(.borderedProminent)
            .tint(.hangGreenDark)
            .disabled(step == nil || isComplete)
            .accessibilityIdentifier("freeWorkout.completeSet")
            Button("Skip") {
                clock.seek(to: timeline.skipTarget(from: elapsed) ?? timeline.duration)
            }
            .buttonStyle(.bordered)
            .tint(.hangGreenDark)
            .disabled(step == nil || isComplete)
            .accessibilityIdentifier("freeWorkout.skip")
            Spacer()
            Button("Finish") {
                finish()
            }
            .buttonStyle(.bordered)
            .tint(.red)
            .accessibilityIdentifier("freeWorkout.finish")
        }
    }

    private func nudge(_ step: WorkoutStep, _ updates: FreeWorkoutStepUpdates) {
        apply(updates, to: step.id)
    }

    private func apply(_ updates: FreeWorkoutStepUpdates, to stepID: String) {
        timeline.updateStep(id: stepID, updates)
        steps = timeline.currentSteps
    }

    private func startIfNeeded() {
        guard !clock.isRunning, !didFinish else { return }
        startedAt = Date()
        clock.start(initialCountdown: 0)
    }

    private func finish() {
        guard !didFinish else { return }
        didFinish = true
        clock.pause()
        let endDate = Date()
        let measurements = steps.map { step in
            WorkoutStepMeasurement(
                stepID: step.id,
                plannedActiveDuration: step.activeDuration,
                intervals: [],
                peakLoadKGF: nil,
                sampleCount: 0,
                status: .unmeasured,
                handUse: step.handUse,
                side: step.side,
                action: step.action,
                repetitions: step.repetitions,
                completedRepetitions: step.action == .loadedLift
                    ? liftCompletion.completedRepetitions(for: step)
                    : nil,
                externalLoadKGF: step.action == .loadedLift
                    ? liftCompletion.externalLoadKGF(for: step)
                    : step.externalLoadKGF,
                isRest: step.isRestStep
            )
        }
        let record = WorkoutSessionRecord(
            id: UUID(),
            planID: plan.id,
            planTitle: plan.title,
            recordedAt: endDate,
            startDate: startedAt,
            endDate: endDate,
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: measurements,
            stepTitles: steps.map(\.title)
        )
        store.markSessionComplete(
            plan,
            startDate: startedAt,
            endDate: endDate,
            sessionSteps: steps,
            session: record
        )
        if saveAsPlan {
            do {
                let definition = FreeWorkoutSaver.routineDefinition(from: draft, title: plan.title)
                try store.saveCustomRoutine(definition)
            } catch {
                saveError = error.localizedDescription
                return
            }
        }
        dismiss()
    }

    private var saveAlertBinding: Binding<Bool> {
        Binding(
            get: { saveError != nil },
            set: { isPresented in
                if !isPresented {
                    saveError = nil
                    dismiss()
                }
            }
        )
    }
}

private struct FreeWorkoutStepEditSheet: View {
    @Environment(\.dismiss) private var dismiss
    let step: WorkoutStep
    let liftCompletion: WorkoutLiftCompletion
    let onSave: (FreeWorkoutStepUpdates) -> Void

    @State private var duration: Double
    @State private var loadText: String
    @State private var reps: Int

    init(
        step: WorkoutStep,
        liftCompletion: WorkoutLiftCompletion,
        onSave: @escaping (FreeWorkoutStepUpdates) -> Void
    ) {
        self.step = step
        self.liftCompletion = liftCompletion
        self.onSave = onSave
        _duration = State(initialValue: step.duration)
        let load = step.action == .loadedLift
            ? (liftCompletion.externalLoadKGF(for: step) ?? step.externalLoadKGF)
            : step.externalLoadKGF
        _loadText = State(initialValue: load.map { $0.formatted() } ?? "")
        _reps = State(initialValue: step.repetitions ?? 1)
    }

    var body: some View {
        NavigationStack {
            Form {
                Stepper("Duration: \(Int(duration))s", value: $duration, in: 1...3600, step: 5)
                if !step.isRestStep {
                    TextField("Added weight (kg)", text: $loadText)
                        .keyboardType(.numbersAndPunctuation)
                    if step.action == .loadedLift {
                        Stepper("Reps: \(reps)", value: $reps, in: 1...100)
                    }
                }
            }
            .navigationTitle("Edit set")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        onSave(FreeWorkoutStepUpdates(
                            duration: duration,
                            externalLoadKGF: Double(loadText),
                            repetitions: step.action == .loadedLift ? reps : nil
                        ))
                        dismiss()
                    }
                }
            }
        }
        .accessibilityIdentifier("freeWorkout.editSheet")
    }
}

extension String: Identifiable {
    public var id: String { self }
}
```

API notes for the worker (all verified in this repo):
- `BoardMapView(board:highlightedHoldIDs:)` — the call shape `PlanDetailView.boardPreview` uses (`BoardMapView(board:highlightedHoldIDs:activeHoldID:)`); `highlightedHoldIDs` accepts a `Set<String>`.
- `store.board(for: plan)` returns `BoardRevision`; for free plans (`boardID: nil`) it falls back to the selected board, so generic kind targets highlight on the athlete's board.
- `store.markSessionComplete(plan, startDate:endDate:sessionSteps:session:)` is the convenience overload that records to `WorkoutSessionStore` + HealthKit history.
- `FreeWorkoutSaver` is implemented in Task 6; if Task 5 lands first, create the file with the `routineDefinition(from:title:)` signature from Task 6 Step 3 so this compiles.
- The `String: Identifiable` extension powers `.sheet(item: $editingStepID)`. If the app target already has such an extension and the compiler reports a redeclaration, delete it here and use the existing one.
- `Double(loadText)` yields `Double?`; an empty field therefore clears the load to nil. `load.formatted()` renders the current kg value.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenUITests/FreeWorkoutUITests
```

Expected: both UI tests pass. (Requires Task 6's `FreeWorkoutSaver` file to exist for the app to build — implement Task 6 before running, or run after both land.)

- [ ] **Step 5: Commit**

```bash
git add HangTen/Views/FreeWorkoutSessionView.swift HangTenUITests/FreeWorkoutUITests.swift
git commit -m "feat: add free workout session with live editing"
```

---

### Task 6: `FreeWorkoutSaver` (save-as-plan) + validation tests

**Files:**
- Create: `HangTen/Models/FreeWorkoutSaver.swift`
- Test: `HangTenTests/FreeWorkoutSaverTests.swift` (create)

Mapping rules (mirror `CustomRoutineDraft.stepDefinition` semantics so `CustomRoutineValidator` accepts the result):
- One `WorkoutStepDefinition` per exercise; `id: "free.\(exercise.id)"`.
- Hang/pull work+rest: two fixed segments `[work, rest]` with durations summing to `duration`, `activeDuration = work`. No rest: single fixed work segment, `activeDuration = nil`.
- Rest: single fixed rest segment.
- Targets: generic kind-only (exact contact IDs are stripped, same as `CustomRoutineStore.normalize` does for generic routines). Empty when the exercise has no hold (self-selected work targets are rejected by the validator, so skip target-less non-rest exercises by giving them... no — instead, exercises without a hold are dropped from the saved routine; if none remain, throw `FreeWorkoutSaverError.noSavableSteps`).
- `targetMode: .generic`, id `custom.<uuid>`, category `"custom"`, tags `["free-workout"]`.
- Pull: `action: .loadedLift`, `repetitions`, `externalLoadKGF`; hang: `action: .hang`, no reps.

- [ ] **Step 1: Write the failing tests**

Create `HangTenTests/FreeWorkoutSaverTests.swift`:

```swift
import XCTest
@testable import HangTen

final class FreeWorkoutSaverTests: XCTestCase {
    func testSaverMapsHangPullRestToValidDefinition() throws {
        let draft = FreeWorkoutDraft(title: "Evening", exercises: [
            FreeWorkoutExerciseDraft(kind: .hang, holdKind: .jug, workDuration: 10, restDuration: 50),
            FreeWorkoutExerciseDraft(kind: .pull, holdKind: .jug, workDuration: 25, restDuration: 60, repetitions: 5),
            FreeWorkoutExerciseDraft(kind: .rest, workDuration: 0, restDuration: 120),
        ])
        let definition = try FreeWorkoutSaver.routineDefinition(from: draft, title: "Evening")
        XCTAssertEqual(definition.targetMode, .generic)
        XCTAssertEqual(definition.steps.count, 3)
        XCTAssertTrue(definition.id.hasPrefix("custom."))
        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)
        XCTAssertTrue(issues.isEmpty, "Unexpected validation issues: \(issues)")
    }

    func testSaverThrowsWhenNoHoldTargets() {
        let draft = FreeWorkoutDraft(title: "Empty", exercises: [
            FreeWorkoutExerciseDraft(kind: .hang, holdKind: nil, workDuration: 10, restDuration: 0),
        ])
        XCTAssertThrowsError(try FreeWorkoutSaver.routineDefinition(from: draft, title: "Empty"))
    }

    func testSavedDefinitionResolvesToPlan() throws {
        let draft = FreeWorkoutDraft(title: "Evening", exercises: [
            FreeWorkoutExerciseDraft(kind: .hang, holdKind: .jug, workDuration: 10, restDuration: 50),
        ])
        let definition = try FreeWorkoutSaver.routineDefinition(from: draft, title: "Evening")
        let store = CustomRoutineStore(
            defaults: UserDefaults(suiteName: "FreeWorkoutSaverTests")!,
            availableBoards: BoardCatalog.all
        )
        let plan = try store.plan(for: definition)
        XCTAssertEqual(plan.steps.count, 2)
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/FreeWorkoutSaverTests
```

Expected: BUILD FAILED with "cannot find `FreeWorkoutSaver` in scope".

- [ ] **Step 3: Write minimal implementation**

Create `HangTen/Models/FreeWorkoutSaver.swift` with the complete content:

```swift
import Foundation

enum FreeWorkoutSaverError: Error, Equatable {
    case noSavableSteps
}

enum FreeWorkoutSaver {
    static func routineDefinition(from draft: FreeWorkoutDraft, title: String) throws -> CustomRoutineDefinition {
        let steps = draft.exercises.compactMap(stepDefinition(for:))
        guard !steps.isEmpty else {
            throw FreeWorkoutSaverError.noSavableSteps
        }
        let trimmed = title.trimmingCharacters(in: .whitespacesAndNewlines)
        return CustomRoutineDefinition(
            id: "custom.\(UUID().uuidString)",
            title: trimmed.isEmpty ? "Free workout" : trimmed,
            subtitle: "Saved from a free workout",
            difficulty: nil,
            category: "custom",
            tags: ["free-workout"],
            targetMode: .generic,
            steps: steps
        )
    }

    private static func stepDefinition(for exercise: FreeWorkoutExerciseDraft) -> WorkoutStepDefinition? {
        switch exercise.kind {
        case .rest:
            let duration = max(1, exercise.restDuration)
            return WorkoutStepDefinition(
                id: "free.\(exercise.id)",
                title: exercise.title,
                instruction: "Rest.",
                accessory: "\(Int(duration))s rest",
                duration: duration,
                phase: .rest,
                segments: [
                    WorkoutSegmentDefinition(
                        kind: .rest,
                        target: nil,
                        timing: .fixed,
                        duration: duration
                    )
                ],
                handUse: .double,
                side: .both,
                action: .hang
            )
        case .hang, .pull:
            guard exercise.holdKind != nil || exercise.contactKind != nil else {
                return nil
            }
            let work = max(1, exercise.workDuration)
            let rest = max(0, exercise.restDuration)
            var segments = [
                WorkoutSegmentDefinition(
                    kind: .work,
                    target: .fromLegacyTargets(targets(for: exercise)),
                    timing: .fixed,
                    duration: work
                )
            ]
            if rest > 0 {
                segments.append(
                    WorkoutSegmentDefinition(
                        kind: .rest,
                        target: nil,
                        timing: .fixed,
                        duration: rest
                    )
                )
            }
            let isPull = exercise.kind == .pull
            let reps = isPull ? max(1, exercise.repetitions ?? 5) : nil
            let load = (exercise.externalLoadKGF ?? 0) == 0 ? nil : exercise.externalLoadKGF
            return WorkoutStepDefinition(
                id: "free.\(exercise.id)",
                title: exercise.title,
                instruction: exercise.kind == .pull ? "Do pull-ups." : "Hang.",
                accessory: isPull ? "\(reps ?? 0) reps" : "\(Int(work))s hang",
                duration: work + rest,
                phase: isPull ? .pull : .hang,
                segments: segments,
                gripType: exercise.gripType,
                activeDuration: rest > 0 ? work : nil,
                handUse: .double,
                side: .both,
                action: isPull ? .loadedLift : .hang,
                repetitions: reps,
                externalLoadKGF: load
            )
        }
    }

    private static func targets(for exercise: FreeWorkoutExerciseDraft) -> [ContactRequirement] {
        let kind = exercise.holdKind ?? exercise.contactKind
        guard let kind else { return [] }
        return [.kind(kind)]
    }
}
```

API notes for the worker (all verified in this repo):
- `WorkoutStepDefinition` initializer and `WorkoutSegmentDefinition(kind:target:timing:duration:)` signatures match `CustomRoutineDraft.stepDefinition(from:)` in `CustomRoutineDraft.swift` — copy that call shape exactly.
- `CustomRoutineDefinition(id:title:subtitle:difficulty:category:tags:targetMode:steps:)` matches its declaration in `CustomRoutineStore.swift`.
- `WorkoutSegmentTarget.fromLegacyTargets` maps non-empty requirements (verified in `TrainingModels.swift`).
- Compound-segment validator rules (`CustomRoutineValidator`): multiple segments must all be `.fixed` and durations must sum to `step.duration` — the mapping above satisfies both (`work + rest == duration`).

- [ ] **Step 4: Run tests to verify they pass**

Run the same `xcodebuild test` command as Step 2.
Expected: all 3 tests pass. If `testSavedDefinitionResolvesToPlan` reports validation issues, print them from the failure message and fix the mapping (most likely cause: a hold kind with no matching contact on any bundled board — switch the test to `.jug` only or adjust).

- [ ] **Step 5: Commit**

```bash
git add HangTen/Models/FreeWorkoutSaver.swift HangTenTests/FreeWorkoutSaverTests.swift
git commit -m "feat: add free workout save-as-plan"
```

---

## Self-review

1. **Spec coverage:** Builder (spec §Components 1) → Tasks 3+4. Session with live edit + quick adjust + manual override (§Components 2) → Tasks 2+5. Train entry (§Components 3) → Task 4 Step 4. History with actual values + save-as-plan template/executed choice (§Components 4) → Task 5 `finish()` records `timeline.currentSteps` (actual edited values); the save dialog choice from the spec ("planned vs executed") is simplified to always saving the executed draft — the draft IS the executed state since builder and session share it. Out-of-scope items (supersets, plate calculator, cloud sync) are excluded.
2. **Placeholder scan:** No TBD/TODO; every step has exact file paths, complete code, exact commands, expected outputs. Validator edge cases name concrete fixes.
3. **Type consistency:** `FreeWorkoutStepUpdates` is defined once (Task 2) and reused in Task 5. `FreeWorkoutSaver.routineDefinition(from:title:)` signature matches between Task 5's call site and Task 6's definition. `TrainingPlan` memberwise init gains `isFreeWorkout` with default, so Task 3's `trainingPlan()` compiles. `store.markSessionComplete(plan,startDate:endDate:sessionSteps:session:)` matches the verified `AppStore` overload.

## Full verification

After all tasks, run the complete related suites:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/FreeWorkoutTests \
  -only-testing:HangTenTests/FreeWorkoutTimelineUpdateTests \
  -only-testing:HangTenTests/FreeWorkoutSaverTests \
  -only-testing:HangTenUITests/FreeWorkoutUITests
```

Expected: all green. Then run the neighboring suites that touch the modified files (`WorkoutTimelineTests`, `WorkoutSummaryTests`, `CustomRoutineStoreTests`, `AppStoreFavoritesTests`) to catch regressions.
