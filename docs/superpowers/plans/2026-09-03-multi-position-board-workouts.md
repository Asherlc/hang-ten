# Multi-Position Board Workouts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve a board position for every target-bearing workout step, minimize disruptive position changes, and gate playback safely when a transition cannot fit transparently into normal rest.

**Architecture:** Extend canonical board content with positions and directed coarse transitions while retaining presentations as the rendering layer. Pure, deterministic resolvers on iOS and Android produce equivalent immutable resolved workouts; separate playback coordinators own readiness gates and setup-wait accounting so timer and UI code consume decisions rather than reimplementing them.

**Tech Stack:** Swift 6-compatible Foundation/SwiftUI/XCTest, Kotlin/JVM/Jetpack Compose/JUnit, Python 3.11/pytest, JSON board packages, Xcode 26, Gradle/JDK 17

**Spec:** `docs/superpowers/specs/2026-09-03-multi-position-board-workouts-design.md`

## Global Constraints

- Holds remain canonical and must not be duplicated for a rotated or flipped position.
- Transition kinds are exactly `seamless`, `setupRequired`, and `unsupported`; there are no numeric setup estimates.
- Same-position transitions are free, omitted directed edges mean `setupRequired`, and `unsupported` edges are explicit.
- Generic plan content never gains board mechanics or invented setup instructions.
- Existing board packages, semantic mappings, plan files, and workout history must continue to decode.
- Authored work/rest duration and Health workout segments remain unchanged; extra setup wait is recorded separately.
- Position and transition evidence must satisfy `AGENTS.md` source-fidelity rules. Unknown transitions remain omitted and therefore conservative.
- iOS and Android must resolve identical position sequences from equivalent inputs.
- Add focused files for resolution and playback coordination instead of expanding `RootView.swift` or `WorkoutScreen.kt` with policy logic.
- New iOS files must be added to `HangTen.xcodeproj/project.pbxproj` in the application and test targets as appropriate.
- Generated build output must remain workspace-owned. iOS Derived Data stays under `.context/DerivedData`. Every Android Gradle command sets `GRADLE_USER_HOME` to `$PWD/.context/gradle-home`; `Android/app/build` is an approved workspace-owned output path. When the workflow ends, cleanup removes exactly `.context/gradle-home` and `Android/app/build`, in addition to the required isolated-Simulator resources.

---

### Task 1: Canonical board-position schema and Python validation

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`
- Modify: `Tools/HangboardPackages/tests/test_board_catalog.py`
- Modify: `Tools/HangboardPackages/tests/_board_package_helpers.py`

**Interfaces:**
- Produces: `BoardPosition`, `BoardPositionTransitionKind`, and `BoardPositionTransition` Python value types.
- Produces: `BoardDocument.positions`, `BoardDocument.position_transitions`, `BoardDocument.hold_ids_for_position(position_id)`, and `BoardDocument.transition_kind(from_id, to_id)`.
- Compatibility rule: absent `positions` synthesizes one position per presentation in declaration order; absent edges resolve as `setupRequired`.

- [ ] **Step 1: Write failing schema tests**

Add tests with explicit assertions, including this valid document fragment and invalid mutations:

```python
document["positions"] = [
    {"id": "front", "presentationID": "primary"},
    {"id": "flipped", "presentationID": "front-inverted"},
]
document["positionTransitions"] = [
    {
        "fromPositionID": "front",
        "toPositionID": "flipped",
        "kind": "seamless",
    }
]
module = load_board_catalog_module()
board = module._load_board(document)
assert [position.id for position in board.positions] == ["front", "flipped"]
assert board.hold_ids_for_position("flipped") == board.hold_ids_for_position("front")
assert board.transition_kind("front", "front") == "same"
assert board.transition_kind("front", "flipped") == "seamless"
assert board.transition_kind("flipped", "front") == "setupRequired"
```

Cover duplicate position IDs, unknown presentation IDs, duplicate directed edges, unknown endpoints, self-edges, unsupported kind strings, and positions whose canonical presentation owns no holds. Add a legacy fixture with two presentations and assert that two implicit positions are synthesized.

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
cd Tools/HangboardPackages
rtk python -m pytest tests/test_board_catalog.py -q
```

Expected: FAIL because `positions`, transition decoding, and lookup helpers do not exist and the closed board schema rejects the new keys.

- [ ] **Step 3: Implement the canonical schema**

Add exact frozen value types and lookup behavior:

```python
@dataclass(frozen=True)
class BoardPosition:
    id: str
    presentation_id: str


class BoardPositionTransitionKind(StrEnum):
    SEAMLESS = "seamless"
    SETUP_REQUIRED = "setupRequired"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class BoardPositionTransition:
    from_position_id: str
    to_position_id: str
    kind: BoardPositionTransitionKind
```

Parse `positions` and `positionTransitions` as closed objects. Compute a position's canonical presentation using `source_presentation_id or id`, and return the IDs of holds owned by that canonical presentation. Make same-position lookup return the internal sentinel `"same"`; explicit lookup returns its raw kind; a missing edge returns `"setupRequired"`.

- [ ] **Step 4: Run the focused tests and canonical package validator**

Run:

```bash
cd Tools/HangboardPackages
rtk python -m pytest tests/test_board_catalog.py -q
cd ../..
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

Expected: PASS, including all unchanged legacy packages.

- [ ] **Step 5: Commit the canonical schema**

```bash
git add Tools/HangboardPackages/src/hangboard_packages/board_catalog.py Tools/HangboardPackages/tests/test_board_catalog.py Tools/HangboardPackages/tests/_board_package_helpers.py
git commit -m "Add canonical board position schema"
```

### Task 2: iOS board models, decoding, writing, and semantic constraints

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Models/BoardPackageStore.swift`
- Modify: `HangTen/Models/BoardPackageWriter.swift`
- Modify: `HangTen/Models/PlanStorage.swift`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `HangTenTests/BoardPackageWriterTests.swift`
- Modify: `HangTenTests/PlanStorageTests.swift`
- Modify: `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`

**Interfaces:**
- Produces: `BoardPosition`, `BoardPositionTransitionKind`, and `BoardPositionTransition` Swift types.
- Produces: `TrainingBoard.positions`, `TrainingBoard.positionTransitions`, `holdIDs(inPosition:)`, and `transitionKind(from:to:)`.
- Produces: `SemanticHoldMappingDefinition.positionIDs: [String]` with absent JSON decoded as `[]`.
- Preserves position fields through `BoardEditableDocument` decode/encode without adding editor inference.

- [ ] **Step 1: Write failing iOS model and package tests**

Add fixtures equivalent to Task 1 and assert:

```swift
XCTAssertEqual(board.positions.map(\.id), ["front", "flipped"])
XCTAssertEqual(board.holdIDs(inPosition: "front"), board.holdIDs(inPosition: "flipped"))
XCTAssertEqual(board.transitionKind(from: "front", to: "front"), .same)
XCTAssertEqual(board.transitionKind(from: "front", to: "flipped"), .seamless)
XCTAssertEqual(board.transitionKind(from: "flipped", to: "front"), .setupRequired)
```

Add rejection tests matching every Python validation case. Add a writer round-trip assertion for explicit positions/transitions and a legacy two-presentation assertion for synthesized positions. Add plan-library decoding tests for `positionIDs`, unknown position IDs, duplicates, and absent-field compatibility.

- [ ] **Step 2: Run focused iOS tests and verify failure**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardPackageWriterTests -only-testing:HangTenTests/PlanStorageTests
```

Expected: FAIL on missing types/properties and rejected JSON keys.

- [ ] **Step 3: Implement iOS types and lookup APIs**

Add the exact public model shape:

```swift
enum BoardPositionTransitionKind: String, Codable, Hashable {
    case seamless
    case setupRequired
    case unsupported
}

enum ResolvedBoardPositionTransitionKind: Hashable {
    case same
    case seamless
    case setupRequired
    case unsupported
}

struct BoardPosition: Identifiable, Codable, Hashable {
    let id: String
    let presentationID: String
}

struct BoardPositionTransition: Codable, Hashable {
    let fromPositionID: String
    let toPositionID: String
    let kind: BoardPositionTransitionKind
}
```

Extend `TrainingBoard` with nonoptional arrays, synthesizing positions from all presentations when package positions are absent. `holdIDs(inPosition:)` must follow only one canonical `sourcePresentationID` hop, matching current package validation. Implement directed transition lookup with same/missing defaults.

- [ ] **Step 4: Extend iOS readers, writer, and semantic mappings**

Decode and validate the two optional board keys in `BoardPackageStore`; preserve them in `BoardPackageWriter`. Add `positionIDs` to `SemanticHoldMappingDefinition`, validate against the mapped board after packages load, encode it only when nonempty, and leave existing mappings byte-compatible in meaning.

- [ ] **Step 5: Run focused tests and commit**

Run the Step 2 command and expect PASS, then:

```bash
git add HangTen/Models/TrainingModels.swift HangTen/Models/BoardPackageStore.swift HangTen/Models/BoardPackageWriter.swift HangTen/Models/PlanStorage.swift HangTenTests/BoardPackageStoreTests.swift HangTenTests/BoardPackageWriterTests.swift HangTenTests/PlanStorageTests.swift HangTenTests/Fixtures/BoardPackageValidationFixtures.json
git commit -m "Decode board positions on iOS"
```

### Task 3: Android board-model parity

**Files:**
- Modify: `Android/app/src/main/java/com/hangten/android/content/BoardModels.kt`
- Modify: `Android/app/src/main/java/com/hangten/android/content/BoardRepository.kt`
- Modify: `Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt`

**Interfaces:**
- Produces Kotlin equivalents of the Task 2 board types and lookup methods.
- Adds `BoardPresentation.sourcePresentationId: String?` and `isInverted: Boolean`.
- Adds `SemanticHoldMapping.positionIds: List<String>`.
- Must match the iOS/Python compatibility and validation rules exactly.

- [ ] **Step 1: Write failing Android content tests**

Use in-memory assets with explicit and legacy multi-presentation packages. Assert:

```kotlin
assertEquals(listOf("front", "flipped"), board.positions.map { it.id })
assertEquals(board.holdIdsInPosition("front"), board.holdIdsInPosition("flipped"))
assertEquals(ResolvedPositionTransition.SAME, board.transitionKind("front", "front"))
assertEquals(ResolvedPositionTransition.SEAMLESS, board.transitionKind("front", "flipped"))
assertEquals(ResolvedPositionTransition.SETUP_REQUIRED, board.transitionKind("flipped", "front"))
```

Repeat the canonical invalid cases and assert semantic `positionIDs` validation.

- [ ] **Step 2: Run the focused Android test and verify failure**

```bash
rtk env GRADLE_USER_HOME="$PWD/.context/gradle-home" ./Android/gradlew -p Android :app:testDebugUnitTest --tests com.hangten.android.content.BoardRepositoryTest
```

Expected: FAIL because Android does not decode presentation aliases, positions, transitions, or semantic position constraints.

- [ ] **Step 3: Implement Android parity**

Add exact Kotlin shapes:

```kotlin
enum class PositionTransitionKind { SEAMLESS, SETUP_REQUIRED, UNSUPPORTED }
enum class ResolvedPositionTransition { SAME, SEAMLESS, SETUP_REQUIRED, UNSUPPORTED }
data class BoardPosition(val id: String, val presentationId: String)
data class BoardPositionTransition(
    val fromPositionId: String,
    val toPositionId: String,
    val kind: PositionTransitionKind,
)
```

Decode portable lower-camel JSON values explicitly rather than relying on enum names. Add `Board.holdIdsInPosition(positionId)` and `Board.transitionKind(fromId, toId)` with the same canonical-source and fallback behavior as Swift/Python.

- [ ] **Step 4: Run tests and commit**

Run the Step 2 command and expect PASS, then:

```bash
git add Android/app/src/main/java/com/hangten/android/content/BoardModels.kt Android/app/src/main/java/com/hangten/android/content/BoardRepository.kt Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt
git commit -m "Decode board positions on Android"
```

### Task 4: Deterministic iOS workout-position resolver

**Files:**
- Create: `HangTen/Models/WorkoutPositionResolution.swift`
- Create: `HangTenTests/WorkoutPositionResolutionTests.swift`
- Modify: `HangTen/Models/AppStore.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`

**Interfaces:**
- Consumes: `TrainingBoard.holdIDs(inPosition:)`, directed transition lookup, and semantic `positionIDs`.
- Produces: `ResolvedWorkout`, `ResolvedWorkoutStep`, `WorkoutPositionResolutionError`, and `WorkoutPositionResolver.resolve(plan:on:)`.
- Produces: `AppStore.resolveWorkout(_:) -> Result<ResolvedWorkout, WorkoutPositionResolutionError>`.

- [ ] **Step 1: Write failing resolver tests**

Define fixture builders in the test file and cover rest-step nil positions, same-position preference, any number of seamless edges beating one setup edge, directed edges, explicit unsupported rejection, missing-edge setup fallback, semantic constraints, no common position for multiple targets/segments, and stable default/declaration-order ties.

Use the intended API directly:

```swift
let resolved = try WorkoutPositionResolver.resolve(plan: plan, on: board)
XCTAssertEqual(resolved.steps.map(\.positionID), ["front", nil, "flipped"])
XCTAssertEqual(resolved.steps[0].holdIDs, Set(["edge-20"]))
XCTAssertEqual(resolved.steps[2].holdIDs, Set(["edge-15"]))
```

- [ ] **Step 2: Run the resolver test and verify failure**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/WorkoutPositionResolutionTests
```

Expected: FAIL because the new source and test types are absent.

- [ ] **Step 3: Add exact resolved-workout interfaces**

```swift
struct ResolvedWorkoutStep: Identifiable, Hashable {
    var id: WorkoutStep.ID { step.id }
    let step: WorkoutStep
    let holdIDs: Set<String>
    let positionID: String?
}

struct ResolvedWorkout: Hashable {
    let plan: TrainingPlan
    let boardID: String
    let steps: [ResolvedWorkoutStep]
}

enum WorkoutPositionResolutionError: Error, Equatable {
    case unresolvableTarget(stepID: String)
    case noCommonPosition(stepID: String)
    case noValidTransitionPath
}

enum WorkoutPositionResolver {
    static func resolve(plan: TrainingPlan, on board: TrainingBoard) throws -> ResolvedWorkout
}
```

For each target-bearing normalized step, resolve every target against holds visible in each candidate position; accept a candidate only when every top-level and segment target resolves there. Intersect semantic `positionIDs` constraints. Derive the default position as the first declared position whose `presentationID` is the board's default presentation; declaration order selects it when multiple positions map to that presentation. If no authored position maps to the default presentation, use the first declared position. Use dynamic programming with score tuple `(setupRequiredCount, seamlessCount, defaultPositionPenalty, declarationOrderPath)` and retain predecessors to reconstruct the globally optimal path. There is no assumed prior physical position: initialize every candidate for the first target-bearing step with zero transition costs. Accumulate `defaultPositionPenalty` per target-bearing selected position, adding `0` for the derived default and `1` otherwise; rest-only steps add no penalty. Keep the declaration-order path as the final tie-break. Never mutate `TrainingPlan`.

- [ ] **Step 4: Wire launch-time resolution without changing playback yet**

Add `AppStore.resolveWorkout(_:)` using `board(for:)`. Keep existing compatibility helpers for previews, but route new launch preparation through this method in the later playback task.

- [ ] **Step 5: Run focused tests and commit**

Run the Step 2 command and expect PASS, then:

```bash
git add HangTen/Models/WorkoutPositionResolution.swift HangTen/Models/AppStore.swift HangTenTests/WorkoutPositionResolutionTests.swift HangTen.xcodeproj/project.pbxproj HangTenTests/BoardSourceBoundaryTrackedPaths.txt
git commit -m "Resolve workout board positions on iOS"
```

### Task 5: Deterministic Android resolver and parity fixtures

**Files:**
- Create: `Android/app/src/main/java/com/hangten/android/workout/WorkoutPositionResolver.kt`
- Create: `Android/app/src/test/java/com/hangten/android/workout/WorkoutPositionResolverTest.kt`
- Modify: `Android/app/src/main/java/com/hangten/android/board/HoldTargetResolver.kt`
- Create: `SharedTests/MultiPositionWorkoutFixtures.json`
- Modify: `HangTenTests/WorkoutPositionResolutionTests.swift`

**Interfaces:**
- Consumes: Task 3 board APIs and existing Android target resolution.
- Produces: `ResolvedWorkout`, `ResolvedWorkoutStep`, `WorkoutPositionResolutionException`, and `WorkoutPositionResolver.resolve(plan, board)` in Kotlin.
- Produces: one checked-in fixture table consumed by both platform test suites.

- [ ] **Step 1: Add a shared parity fixture and failing Android tests**

The JSON fixture must contain complete miniature boards/plans plus expected step position IDs and hold IDs for these named cases: `legacy-single`, `same-position`, `seamless-over-setup`, `directed-reverse`, `missing-edge`, `unsupported-path`, `semantic-constraint`, and `declaration-order-tie`. Make Swift decode the same table instead of duplicating expected paths.

Add Kotlin assertions such as:

```kotlin
val resolved = WorkoutPositionResolver.resolve(plan, board)
assertEquals(listOf("front", null, "flipped"), resolved.steps.map { it.positionId })
assertEquals(setOf("edge-20"), resolved.steps.first().holdIds)
```

- [ ] **Step 2: Run both parity suites and verify Android failure**

```bash
rtk env GRADLE_USER_HOME="$PWD/.context/gradle-home" ./Android/gradlew -p Android :app:testDebugUnitTest --tests com.hangten.android.workout.WorkoutPositionResolverTest
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/WorkoutPositionResolutionTests
```

Expected: Android FAIL on missing resolver; Swift PASS after reading the shared cases.

- [ ] **Step 3: Implement the Kotlin resolver with matching scoring**

Expose exact shapes:

```kotlin
data class ResolvedWorkoutStep(
    val step: TrainingStep,
    val holdIds: Set<String>,
    val positionId: String?,
)
data class ResolvedWorkout(
    val plan: TrainingPlan,
    val boardId: String,
    val steps: List<ResolvedWorkoutStep>,
)
object WorkoutPositionResolver {
    fun resolve(plan: TrainingPlan, board: Board): ResolvedWorkout
}
```

Port the same candidate filtering, lexicographic score, predecessor reconstruction, and deterministic tie-breaking. Extend `HoldTargetResolver` with a position-limited internal resolver used by this object while preserving `resolveTargets` for existing callers.

- [ ] **Step 4: Run both parity suites and commit**

Run both Step 2 commands and expect PASS, then:

```bash
git add Android/app/src/main/java/com/hangten/android/workout/WorkoutPositionResolver.kt Android/app/src/main/java/com/hangten/android/board/HoldTargetResolver.kt Android/app/src/test/java/com/hangten/android/workout/WorkoutPositionResolverTest.kt SharedTests/MultiPositionWorkoutFixtures.json HangTenTests/WorkoutPositionResolutionTests.swift
git commit -m "Match workout position resolution across platforms"
```

### Task 6: iOS readiness coordinator and position-aware playback

**Files:**
- Create: `HangTen/Models/WorkoutPositionCoordinator.swift`
- Create: `HangTenTests/WorkoutPositionCoordinatorTests.swift`
- Create: `HangTen/Views/WorkoutPositionSetupView.swift`
- Modify: `HangTen/Views/WorkoutAccessGate.swift`
- Modify: `HangTen/Views/BoardMapView.swift`
- Modify: `HangTen/Views/WorkoutStepPickerView.swift`
- Modify: `HangTen/Views/RootView.swift`
- Modify: `HangTenTests/WorkoutTimelineTests.swift`
- Modify: `HangTenTests/GripHandCueCardTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`

**Interfaces:**
- Consumes: immutable `ResolvedWorkout` and directed transition lookup.
- Produces: `WorkoutPositionCoordinator`, `WorkoutPositionGate`, and `WorkoutPositionEvent` pure state APIs.
- Changes: `WorkoutView` accepts `ResolvedWorkout`; `BoardMapView` accepts `allowsPresentationSelection` defaulting to `true`.

- [ ] **Step 1: Write failing coordinator tests**

Cover initial gate, confirmation, seamless transition during rest, setup confirmation before rest expiry, setup gate at expiry, seamless gate with no rest, accumulated wait, repeated pause/resume, forward/reverse navigation, and unsupported navigation.

Drive this exact interface:

```swift
var coordinator = WorkoutPositionCoordinator()
XCTAssertEqual(coordinator.prepareInitial(positionID: "front", at: 10), .showGate(.initial("front")))
XCTAssertEqual(coordinator.confirmReady(at: 12), .resume(positionID: "front"))
XCTAssertEqual(
    coordinator.beginTransition(to: "back", kind: .setupRequired, hasInterveningRest: true, at: 20),
    .showCue(positionID: "back", requiresConfirmation: true)
)
XCTAssertEqual(coordinator.restExpired(at: 30), .pauseForGate(.transition(from: "front", to: "back")))
XCTAssertEqual(coordinator.confirmReady(at: 34), .resume(positionID: "back"))
XCTAssertEqual(coordinator.accumulatedSetupWait, 4)
```

- [ ] **Step 2: Run focused tests and verify failure**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/WorkoutPositionCoordinatorTests -only-testing:HangTenTests/WorkoutTimelineTests
```

Expected: FAIL because coordinator and position-aware timeline behavior are absent.

- [ ] **Step 3: Implement the pure coordinator**

Add explicit state and events:

```swift
enum WorkoutPositionGate: Equatable {
    case initial(String)
    case transition(from: String, to: String)
}

enum WorkoutPositionEvent: Equatable {
    case none
    case showCue(positionID: String, requiresConfirmation: Bool)
    case showGate(WorkoutPositionGate)
    case pauseForGate(WorkoutPositionGate)
    case resume(positionID: String)
    case unsupported
}
```

Keep established position, pending destination, pending gate, gate start uptime, accumulated setup wait, and gate count private(set). Only time spent after an actual pause gate begins contributes to setup wait.

- [ ] **Step 4: Resolve before navigation and render setup state**

Make `WorkoutAccessGate` resolve after access is allowed and before navigation. Pass the frozen result into `WorkoutView`; show an alert for each resolution error without consuming a free workout. Add `WorkoutPositionSetupView` with position name, locked presentation image, `Ready`, and accessibility identifier `workout.position.ready`.

At initial appearance, show the initial gate before sensor preparation and countdown. After `Ready`, preserve the existing motherboard-preparation flow, so any bodyweight capture occurs in the established board position.

- [ ] **Step 5: Integrate rest and navigation transitions**

Use the resolved step's hold IDs and position ID for board cues. Pass `selectedPresentationID` and `allowsPresentationSelection: false` to workout maps. At a setup-required rest, show the nonblocking cue and Ready control; clamp elapsed time to the next work step's exact start offset and pause if rest expires unconfirmed. Route skip/jump through the coordinator before seeking. Navigating to a rest-only step with resolved `positionID == nil` retains the current confirmed position and performs no transition lookup or gate; a later target-bearing navigation evaluates its transition from that retained confirmed position. Disable unsupported rows in `WorkoutStepPickerView` with the text `This board position cannot be reached during the workout.` Rewind must use the reverse directed edge.

- [ ] **Step 6: Add position audio and run focused tests**

Call the existing `WorkoutAudioCoach.speak(_:)` once per transition using only the sourced presentation name: `audioCoach.speak("Move board to \(position.name)")`. Do not put coaching or timing claims into generated copy.

Run the Step 2 command plus:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/GripHandCueCardTests
```

Expected: PASS.

- [ ] **Step 7: Commit iOS playback**

```bash
git add HangTen/Models/WorkoutPositionCoordinator.swift HangTen/Views/WorkoutPositionSetupView.swift HangTen/Views/WorkoutAccessGate.swift HangTen/Views/BoardMapView.swift HangTen/Views/WorkoutStepPickerView.swift HangTen/Views/RootView.swift HangTenTests/WorkoutPositionCoordinatorTests.swift HangTenTests/WorkoutTimelineTests.swift HangTenTests/GripHandCueCardTests.swift HangTen.xcodeproj/project.pbxproj HangTenTests/BoardSourceBoundaryTrackedPaths.txt
git commit -m "Gate iOS workouts on board position changes"
```

### Task 7: Android readiness coordinator and position-aware playback

**Files:**
- Create: `Android/app/src/main/java/com/hangten/android/workout/WorkoutPositionCoordinator.kt`
- Create: `Android/app/src/test/java/com/hangten/android/workout/WorkoutPositionCoordinatorTest.kt`
- Modify: `Android/app/src/main/java/com/hangten/android/workout/WorkoutSession.kt`
- Modify: `Android/app/src/main/java/com/hangten/android/workout/WorkoutViewModel.kt`
- Modify: `Android/app/src/main/java/com/hangten/android/ui/WorkoutScreen.kt`
- Modify: `Android/app/src/main/java/com/hangten/android/board/BoardCanvas.kt`
- Modify: `Android/app/src/androidTest/java/com/hangten/android/ui/WorkoutScreenTest.kt`
- Modify: `Android/app/src/test/java/com/hangten/android/workout/WorkoutSessionTest.kt`

**Interfaces:**
- Mirrors Task 6 coordinator semantics in Kotlin.
- Changes `WorkoutScreen` to resolve once with `remember(plan.id, board.id)` and use the frozen result.
- Changes `WorkoutSession` to accept `ResolvedWorkout` while retaining `val plan = resolvedWorkout.plan` for existing sensor and completion consumers.
- Adds a session hold at exact work boundaries without advancing `elapsedPlanMs` or rewriting plan duration.

- [ ] **Step 1: Write failing Kotlin coordinator/session tests**

Port every Task 6 state case using millisecond timestamps. Assert that a setup gate freezes `elapsedPlanMs` at the next work step boundary and that confirmation resumes without adding setup milliseconds to `totalPlanMs`.

- [ ] **Step 2: Run unit tests and verify failure**

```bash
rtk env GRADLE_USER_HOME="$PWD/.context/gradle-home" ./Android/gradlew -p Android :app:testDebugUnitTest --tests com.hangten.android.workout.WorkoutPositionCoordinatorTest --tests com.hangten.android.workout.WorkoutSessionTest
```

Expected: FAIL on missing coordinator and boundary-hold behavior.

- [ ] **Step 3: Implement coordinator and session integration**

Use sealed equivalents of Task 6's gate/events. Add `WorkoutViewModel.confirmPositionReady()` and expose pending position UI state in `WorkoutSnapshot`. Persist pending gate, established position, setup-wait milliseconds, and gate count through `SavedStateHandle`, while keeping the plan clock frozen during a blocking gate.

- [ ] **Step 4: Implement Compose setup UI and locked presentation**

Resolve once at screen entry. Show resolution failure instead of starting a session. Render initial and blocking setup as a full setup card; render setup-required rest as a nonblocking cue with `Ready`. Navigating to a rest-only step with resolved `positionId == null` retains the current confirmed position and performs no transition lookup or gate; a later target-bearing navigation evaluates its transition from that retained confirmed position. Pass resolved `positionId` to `BoardCanvas`, select its presentation, and remove workout-time presentation switching. Call `audioCoach.speakInstruction("Move board to ${position.name}")` once per transition.

Add Compose assertions for `Set board position`, the presentation name, `Ready`, rest continuing before expiry, and pause at expiry.

- [ ] **Step 5: Run Android unit and instrumented tests**

```bash
rtk env GRADLE_USER_HOME="$PWD/.context/gradle-home" ./Android/gradlew -p Android :app:testDebugUnitTest
rtk env GRADLE_USER_HOME="$PWD/.context/gradle-home" ./Android/gradlew -p Android :app:connectedDebugAndroidTest
```

Expected: PASS. If no Android emulator is available locally, run the unit suite, record the exact instrumented command as pending CI verification, and do not claim instrumented success.

- [ ] **Step 6: Commit Android playback**

```bash
git add Android/app/src/main/java/com/hangten/android/workout/WorkoutPositionCoordinator.kt Android/app/src/main/java/com/hangten/android/workout/WorkoutSession.kt Android/app/src/main/java/com/hangten/android/workout/WorkoutViewModel.kt Android/app/src/main/java/com/hangten/android/ui/WorkoutScreen.kt Android/app/src/main/java/com/hangten/android/board/BoardCanvas.kt Android/app/src/test/java/com/hangten/android/workout/WorkoutPositionCoordinatorTest.kt Android/app/src/test/java/com/hangten/android/workout/WorkoutSessionTest.kt Android/app/src/androidTest/java/com/hangten/android/ui/WorkoutScreenTest.kt
git commit -m "Gate Android workouts on board position changes"
```

### Task 8: Additive session position and setup diagnostics

**Files:**
- Modify: `HangTen/Models/MotherboardModels.swift`
- Modify: `HangTen/Views/RootView.swift`
- Modify: `HangTenTests/MotherboardModelsTests.swift`
- Modify: `HangTenTests/WorkoutSessionStoreTests.swift`
- Modify: `Android/app/src/main/java/com/hangten/android/workout/WorkoutSession.kt`
- Modify: `Android/app/src/main/java/com/hangten/android/workout/SessionHistoryRepository.kt`
- Modify: `Android/app/src/test/java/com/hangten/android/workout/SessionHistoryRepositoryTest.kt`

**Interfaces:**
- Adds `positionID: String?` to iOS `WorkoutStepMeasurement` and `resolvedPositionIDsByStepID: Map<String, String>` to Android `CompletedSession`.
- Adds `setupWaitDuration`/`setupGateCount` on iOS and `setupWaitDurationMs`/`setupGateCount` on Android completed sessions.
- Legacy records decode with nil/zero defaults.

- [ ] **Step 1: Write failing compatibility and round-trip tests**

On Swift, decode an old JSON record and assert nil/zero, then round-trip:

```swift
XCTAssertEqual(decoded.steps.first?.positionID, "front-inverted")
XCTAssertEqual(decoded.setupWaitDuration, 4)
XCTAssertEqual(decoded.setupGateCount, 1)
```

On Android, retain 3-, 5-, and 6-field history fixtures and add the 9-field version: setup-wait milliseconds at index 6, gate count at index 7, and a base64-encoded sorted `stepID|positionID` list at index 8. Assert a malformed or negative new record is dropped without affecting other history records.

- [ ] **Step 2: Run focused persistence tests and verify failure**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/WorkoutSessionStoreTests
rtk env GRADLE_USER_HOME="$PWD/.context/gradle-home" ./Android/gradlew -p Android :app:testDebugUnitTest --tests com.hangten.android.workout.SessionHistoryRepositoryTest
```

Expected: FAIL on missing record fields.

- [ ] **Step 3: Implement additive persistence**

Add optional/defaulted coding keys in Swift. Populate positions from `ResolvedWorkoutStep` and setup totals from `WorkoutPositionCoordinator` when finalizing. Add `resolvedPositionIDsByStepID` to Android `CompletedSession`. Extend Android's append-only comma format to 9 fields using the exact indices in Step 1; accept only historical counts 3, 5, 6, and 9.

- [ ] **Step 4: Run focused tests and commit**

Run the Step 2 commands and expect PASS, then:

```bash
git add HangTen/Models/MotherboardModels.swift HangTen/Views/RootView.swift HangTenTests/MotherboardModelsTests.swift HangTenTests/WorkoutSessionStoreTests.swift Android/app/src/main/java/com/hangten/android/workout/WorkoutSession.kt Android/app/src/main/java/com/hangten/android/workout/SessionHistoryRepository.kt Android/app/src/test/java/com/hangten/android/workout/SessionHistoryRepositoryTest.kt
git commit -m "Record workout board positions"
```

### Task 9: Conservative Port-A-Board migration and full verification

**Files:**
- Modify: `Hangboards/frictitious-port-a-board/board.json`
- Create: `docs/source-audits/2026-09-03-port-a-board-position-transitions.md`
- Create: `Tools/HangboardPackages/tests/test_port_a_board_positions.py`

**Interfaces:**
- Consumes the canonical schema and both platform implementations.
- Produces the first audited explicit-position package without changing hold IDs, paths, measurements, or presentation assets.

- [ ] **Step 1: Use the `add-hangboard` skill and audit primary evidence**

Read `.codex/skills/add-hangboard/SKILL.md` completely before changing the package. Record the manufacturer URL already carried by the package, every position-to-presentation mapping, and the evidence for each explicit edge. Apply this fail-closed decision rule: author `seamless` or `unsupported` only when primary evidence supports that exact directed pair; otherwise omit the edge so runtime behavior is `setupRequired`.

- [ ] **Step 2: Write the failing package migration test**

Assert exact position IDs mapped one-to-one to the six existing presentations:

```python
assert [(position.id, position.presentation_id) for position in board.positions] == [
    ("front-upright", "primary"),
    ("front-inverted", "front-inverted"),
    ("cord-option-4-20mm-incut", "cord-option-4-20mm-incut"),
    ("back-upright", "back"),
    ("back-inverted", "back-inverted"),
    ("pinch-side", "side"),
]
assert set(board.hold_ids_for_position("front-upright")) == set(board.hold_ids_for_position("front-inverted"))
assert set(board.hold_ids_for_position("back-upright")) == set(board.hold_ids_for_position("back-inverted"))
```

Also assert that every explicit transition appears in the audit table with direction, kind, primary URL, and supporting evidence. Do not assert that any edge must be seamless; conservative omission is valid.

- [ ] **Step 3: Run the focused test and verify failure**

```bash
cd Tools/HangboardPackages
rtk python -m pytest tests/test_port_a_board_positions.py -q
```

Expected: FAIL because the package does not yet declare positions and the audit does not exist.

- [ ] **Step 4: Author positions and the audit without touching geometry**

Add the six exact position IDs from Step 2. Add only evidence-supported directed edges. The audit must explicitly list omitted pairs as `defaults to setupRequired` and state that absence is deliberate, not missing research. Confirm `git diff -- Hangboards/frictitious-port-a-board/board.json` changes only top-level position/transition arrays.

- [ ] **Step 5: Run catalog and source-boundary verification**

```bash
cd Tools/HangboardPackages
rtk python -m pytest tests/test_port_a_board_positions.py tests/test_board_catalog.py tests/test_approved_board_packages.py -q
cd ../..
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

Expected: PASS with unchanged canonical hold inventory and geometry.

- [ ] **Step 6: Run full platform verification**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData
rtk env GRADLE_USER_HOME="$PWD/.context/gradle-home" ./Android/gradlew -p Android :app:stageCanonicalAssets :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
```

Expected: PASS.

- [ ] **Step 7: Visually validate iOS and commit**

Use the `validate-hang-ten-ios` skill with an isolated simulator. Validate portrait and landscape initial setup, seamless/rest cue when the audited package has such an edge, blocking setup-required behavior, locked presentation, spoken position cue, Dynamic Type, and VoiceOver labels. If no Port-A-Board edge is evidence-supported as seamless, use a DEBUG-only in-memory fixture for that visual state rather than changing production metadata.

After simulator teardown and resource-deletion verification:

```bash
rtk rm -rf .context/gradle-home Android/app/build
git add Hangboards/frictitious-port-a-board/board.json docs/source-audits/2026-09-03-port-a-board-position-transitions.md Tools/HangboardPackages/tests/test_port_a_board_positions.py
git commit -m "Add audited Port-A-Board positions"
```

- [ ] **Step 8: Push and verify CI**

```bash
git push
gh pr checks --watch=false
```

Expected: branch push succeeds and all required checks are either passing or still running without an immediate configuration failure. Investigate any failure before reporting completion.
