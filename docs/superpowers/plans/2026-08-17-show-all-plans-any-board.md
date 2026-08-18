# Show All Plans on Any Board

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show every training plan on every hangboard, substituting functionally similar holds when exact targets don't resolve.

**Architecture:** Add a `substituteHoldIDs` method to `BoardTargetResolver` that finds the closest hold by kind, feature group, and finger capacity. Remove the compatibility filter from `store.plans`. Update workout recording and hold cue resolution to fall back to substitutes. Plans with `boardID` set still filter to their board; only generic plans (`boardID: nil`) show everywhere.

**Tech Stack:** Swift, SwiftUI, XCTest

---

## Substitution Rules

When a target doesn't resolve on the current board, find the closest hold by:
1. Same `HoldKind` + same feature group (e.g., `smallEdge` → `mediumEdge`)
2. Same `HoldKind` + any feature
3. Cross-kind with matching `fingerCapacity` (e.g., 2-finger pocket ↔ 2-finger edge)
4. Same `HoldKind` + no feature match at all

Feature groups for cross-kind matching:
- **Edge group:** `smallEdge`, `mediumEdge`, `largeEdge`, `fourFingerFlatEdge`, `fourFingerIncutEdge`, `thinCrimp`, `shallowThreeFingerSlot`
- **Pocket group:** `pocket`, `twoFingerPocket`, `threeFingerPocket`, `fourFingerPocket`, `deepTwoFingerPocket`
- **Sloper group:** `roundSloper`, `largeSlope`
- **Pinch group:** `widePinch`, `mediumPinch`, `smallPinch`

---

## File Map

| File | Change |
|------|--------|
| `HangTen/Models/WorkoutActivityRecording.swift` | Add `substituteHoldIDs` and `substituteHolds` to `BoardTargetResolver` |
| `HangTen/Models/AppStore.swift` | Remove compatibility filter from `plans`, update `holdIDs(for:on:)` |
| `HangTen/Models/WorkoutTimeline.swift` | Update `WorkoutHoldCuePolicy.resolve` to use substitutes |
| `HangTen/Views/RootView.swift` | Add "Not on this board" badge to PlanCard for incompatible plans, update copy |
| `HangTenTests/BoardTargetSubstitutionTests.swift` | New: tests for substitute resolution |
| `HangTenTests/WorkoutActivityRecordingTests.swift` | Update: test that recording uses substitutes |
| `HangTenTests/PlanStorageTests.swift` | Update: remove/adjust compatibility assertions |

---

### Task 1: Add `HoldFeature.group` helper

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:168-212`

- [ ] **Step 1: Add the feature group enum and computed property**

After the `HoldFeature` enum's `label` property (around line 212), add:

```swift
    enum FeatureGroup: Hashable {
        case edge
        case pocket
        case sloper
        case pinch
        case other
    }

    var featureGroup: FeatureGroup {
        switch self {
        case .smallEdge, .mediumEdge, .largeEdge,
             .fourFingerFlatEdge, .fourFingerIncutEdge,
             .thinCrimp, .shallowThreeFingerSlot:
            .edge
        case .pocket, .twoFingerPocket, .threeFingerPocket,
             .fourFingerPocket, .deepTwoFingerPocket:
            .pocket
        case .roundSloper, .largeSlope:
            .sloper
        case .widePinch, .mediumPinch, .smallPinch:
            .pinch
        case .jug, .largeOpenHandRail:
            .other
        }
    }
```

- [ ] **Step 2: Build and verify**

Run: `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -5`
Expected: BUILD SUCCEEDED

- [ ] **Step 3: Commit**

```bash
git add HangTen/Models/TrainingModels.swift
git commit -m "feat: add HoldFeature.featureGroup for cross-kind hold matching"
```

---

### Task 2: Add `BoardTargetResolver.substituteHoldIDs`

**Files:**
- Modify: `HangTen/Models/WorkoutActivityRecording.swift:81-104`

- [ ] **Step 1: Write the failing test**

Create `HangTenTests/BoardTargetSubstitutionTests.swift`:

```swift
import XCTest
@testable import HangTen

final class BoardTargetSubstitutionTests: XCTestCase {
    private func hold(
        id: String,
        kind: HoldKind = .edge,
        feature: HoldFeature? = nil,
        fingerCapacity: Int? = nil
    ) -> BoardHold {
        BoardHold(
            id: id,
            name: id,
            shortLabel: id,
            detail: id,
            kind: kind,
            frame: HoldFrame(x: 0, y: 0, width: 0.1, height: 0.1),
            fingerCapacity: fingerCapacity,
            features: feature.map { [$0] }
        )
    }

    private func board(holds: [BoardHold]) -> TrainingBoard {
        TrainingBoard(
            id: "test-board",
            manufacturer: "Test",
            name: "Test Board",
            subtitle: "",
            dimensions: "30x60",
            aspectRatio: 0.5,
            holds: holds,
            productURL: URL(string: "https://example.com")!,
            photoAssetName: nil
        )
    }

    func testExactMatchStillWorks() {
        let board = board(holds: [
            hold(id: "a", kind: .edge, feature: .smallEdge)
        ])
        let target = HoldTarget.feature(.smallEdge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["a"])
    }

    func testSameKindDifferentFeature() {
        let board = board(holds: [
            hold(id: "a", kind: .edge, feature: .mediumEdge)
        ])
        let target = HoldTarget.feature(.smallEdge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["a"])
    }

    func testCrossKindMatchingFingerCapacity() {
        let board = board(holds: [
            hold(id: "p2", kind: .pocket, feature: .twoFingerPocket, fingerCapacity: 2)
        ])
        let target = HoldTarget.feature(.smallEdge, fallback: .mediumEdge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["p2"])
    }

    func testCrossKindMismatchedFingerCapacityExcluded() {
        let board = board(holds: [
            hold(id: "p4", kind: .pocket, feature: .fourFingerPocket, fingerCapacity: 4)
        ])
        let target = HoldTarget.feature(.smallEdge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertTrue(result.isEmpty)
    }

    func testSameKindNoFeatureMatch() {
        let board = board(holds: [
            hold(id: "j", kind: .edge, feature: nil)
        ])
        let target = HoldTarget.feature(.smallEdge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["j"])
    }

    func testKindTargetSubstitutesByKind() {
        let board = board(holds: [
            hold(id: "e1", kind: .edge, feature: .largeEdge)
        ])
        let target = HoldTarget.kind(.edge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertEqual(result, ["e1"])
    }

    func testEmptyBoardReturnsEmpty() {
        let board = board(holds: [])
        let target = HoldTarget.feature(.smallEdge)
        let result = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
        XCTAssertTrue(result.isEmpty)
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardTargetSubstitutionTests -quiet 2>&1 | tail -10`
Expected: FAIL (method `substituteHoldIDs` does not exist)

- [ ] **Step 3: Implement `substituteHoldIDs`**

In `HangTen/Models/WorkoutActivityRecording.swift`, after the existing `resolveHolds` method (line ~103), add:

```swift
    static func substituteHoldIDs(for target: HoldTarget, on board: TrainingBoard) -> [String] {
        let primary = resolveHoldIDs(for: target, on: board)
        if !primary.isEmpty { return primary }
        return closestMatch(for: target, on: board)
    }

    static func substituteHolds(for target: HoldTarget, on board: TrainingBoard) -> [BoardHold] {
        let ids = Set(substituteHoldIDs(for: target, on: board))
        return board.holds.filter { ids.contains($0.id) }
    }

    private static func closestMatch(for target: HoldTarget, on board: TrainingBoard) -> [String] {
        if let feature = target.feature {
            return byFeatureGroup(feature, on: board)
        }
        if let kind = target.kind {
            return board.holds.filter { $0.kind == kind }.map(\.id)
        }
        if !target.holdIDs.isEmpty {
            return []
        }
        return []
    }

    private static func byFeatureGroup(_ feature: HoldFeature, on board: TrainingBoard) -> [String] {
        let group = feature.featureGroup
        let groupFeatures = Set(HoldFeature.allCases.filter { $0.featureGroup == group })

        let sameGroup = board.holds.filter { hold in
            guard let features = hold.features else { return false }
            return !features.isDisjoint(with: groupFeatures)
        }
        if !sameGroup.isEmpty { return sameGroup.map(\.id) }

        let sameKind = board.holds.filter { $0.kind == feature.holdKind }
        if !sameKind.isEmpty { return sameKind.map(\.id) }

        return []
    }
```

Also add this extension near the top of the file (or in `TrainingModels.swift` if preferred):

```swift
extension HoldFeature {
    var holdKind: HoldKind {
        switch self {
        case .jug: .jug
        case .roundSloper, .largeSlope: .sloper
        case .largeEdge, .mediumEdge, .smallEdge,
             .fourFingerFlatEdge, .fourFingerIncutEdge,
             .thinCrimp, .shallowThreeFingerSlot: .edge
        case .pocket, .twoFingerPocket, .threeFingerPocket,
             .fourFingerPocket, .deepTwoFingerPocket: .pocket
        case .widePinch, .mediumPinch, .smallPinch: .pinch
        case .largeOpenHandRail: .edge
        }
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardTargetSubstitutionTests -quiet 2>&1 | tail -10`
Expected: TEST PASSED

- [ ] **Step 5: Commit**

```bash
git add HangTen/Models/WorkoutActivityRecording.swift HangTen/Models/TrainingModels.swift HangTenTests/BoardTargetSubstitutionTests.swift
git commit -m "feat: add BoardTargetResolver.substituteHoldIDs for cross-board hold matching"
```

---

### Task 3: Remove compatibility filter from `store.plans`

**Files:**
- Modify: `HangTen/Models/AppStore.swift:157-161`

- [ ] **Step 1: Update `plans` to show all board-generic plans**

Change the `plans` computed property from:

```swift
    var plans: [TrainingPlan] {
        (PlanCatalog.all + customPlans).filter { plan in
            isCompatible(plan, with: selectedBoard)
        }
    }
```

To:

```swift
    var plans: [TrainingPlan] {
        (PlanCatalog.all + customPlans).filter { plan in
            plan.boardID == nil || plan.boardID == selectedBoard.id
        }
    }
```

This keeps board-specific plans scoped to their board but shows all generic plans everywhere.

- [ ] **Step 2: Update `holdIDs(for:on:)` to use substitutes**

Change `holdIDs(for:on:)` from:

```swift
    func holdIDs(for step: WorkoutStep, on board: TrainingBoard) -> Set<String> {
        let ids = step.targets.flatMap { BoardTargetResolver.resolveHoldIDs(for: $0, on: board) }
        return Set(ids)
    }
```

To:

```swift
    func holdIDs(for step: WorkoutStep, on board: TrainingBoard) -> Set<String> {
        let ids = step.targets.flatMap { BoardTargetResolver.substituteHoldIDs(for: $0, on: board) }
        return Set(ids)
    }
```

- [ ] **Step 3: Build and verify**

Run: `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -5`
Expected: BUILD SUCCEEDED

- [ ] **Step 4: Commit**

```bash
git add HangTen/Models/AppStore.swift
git commit -m "feat: show all generic plans on any board with hold substitution"
```

---

### Task 4: Update workout recording to use substitutes

**Files:**
- Modify: `HangTen/Models/WorkoutActivityRecording.swift:136-141`

- [ ] **Step 1: Update recording to use `substituteHolds`**

Change lines 136–139 from:

```swift
                let holdsByTarget = segment.targets.map {
                    BoardTargetResolver.resolveHolds(for: $0, on: board)
                }
                guard holdsByTarget.allSatisfy({ !$0.isEmpty }) else { throw WorkoutActivityRecordingError.unresolvedTarget(stepID: step.id, segmentIndex: index) }
```

To:

```swift
                let holdsByTarget = segment.targets.map {
                    BoardTargetResolver.substituteHolds(for: $0, on: board)
                }
                guard holdsByTarget.allSatisfy({ !$0.isEmpty }) else { throw WorkoutActivityRecordingError.unresolvedTarget(stepID: step.id, segmentIndex: index) }
```

- [ ] **Step 2: Build and verify**

Run: `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -5`
Expected: BUILD SUCCEEDED

- [ ] **Step 3: Commit**

```bash
git add HangTen/Models/WorkoutActivityRecording.swift
git commit -m "feat: use substitute holds in workout activity recording"
```

---

### Task 5: Update hold cue resolution to use substitutes

**Files:**
- Modify: `HangTen/Models/WorkoutTimeline.swift:103-125`

- [ ] **Step 1: Update `WorkoutHoldCuePolicy.resolve`**

Change line 113 from:

```swift
              BoardTargetResolver.resolveHoldIDs(for: target, on: board).contains(hold.id),
```

To:

```swift
              BoardTargetResolver.substituteHoldIDs(for: target, on: board).contains(hold.id),
```

- [ ] **Step 2: Build and verify**

Run: `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -5`
Expected: BUILD SUCCEEDED

- [ ] **Step 3: Commit**

```bash
git add HangTen/Models/WorkoutTimeline.swift
git commit -m "feat: use substitute holds in workout cue resolution"
```

---

### Task 6: Add "Substituted" badge to PlanCard

**Files:**
- Modify: `HangTen/Models/AppStore.swift:268-275` (add `isIncompatible` method)
- Modify: `HangTen/Views/RootView.swift:740-781` (update `PlanCard`)
- Modify: `HangTen/Views/RootView.swift:450-456` (pass flag from list)

- [ ] **Step 1: Add `isIncompatible` to AppStore**

After the existing `usesFallbackMapping` method (line ~275), add:

```swift
    func isIncompatible(_ plan: TrainingPlan, on board: TrainingBoard) -> Bool {
        plan.steps.flatMap(\.targets).contains { target in
            BoardTargetResolver.substituteHoldIDs(for: target, on: board).isEmpty
        }
    }
```

- [ ] **Step 2: Update PlanCard to accept and show the flag**

Change `PlanCard` from:

```swift
private struct PlanCard: View {
    let plan: TrainingPlan
    let board: TrainingBoard

    var body: some View {
        VStack(alignment: .leading, spacing: 15) {
            HStack {
                Pill(title: plan.level, tint: Color.hangGreenDark, fill: Color.hangGreen.opacity(0.25))
                Pill(
                    title: plan.provenance.label,
                    tint: Color.hangGreenDark,
                    fill: Color.hangGreen.opacity(0.16)
                )
                Spacer()
                Text(plan.durationLabel)
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
            .padding(.trailing, 52)
```

To:

```swift
private struct PlanCard: View {
    let plan: TrainingPlan
    let board: TrainingBoard
    var isIncompatible: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 15) {
            HStack {
                Pill(title: plan.level, tint: Color.hangGreenDark, fill: Color.hangGreen.opacity(0.25))
                Pill(
                    title: plan.provenance.label,
                    tint: Color.hangGreenDark,
                    fill: Color.hangGreen.opacity(0.16)
                )
                if isIncompatible {
                    Pill(title: "Not on this board", tint: .orange, fill: Color.orange.opacity(0.12))
                }
                Spacer()
                Text(plan.durationLabel)
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
            .padding(.trailing, 52)
```

- [ ] **Step 3: Update FavoritePlanCard to accept and forward the flag**

Change `FavoritePlanCard` struct to add `isIncompatible`:

```swift
private struct FavoritePlanCard: View {
    let plan: TrainingPlan
    let board: TrainingBoard
    let isFavorite: Bool
    let isIncompatible: Bool
    let onToggle: () -> Void

    var body: some View {
        ZStack(alignment: .topTrailing) {
            NavigationLink(destination: PlanDetailView(plan: plan)) {
                PlanCard(plan: plan, board: board, isIncompatible: isIncompatible)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity)

            Button(action: onToggle) {
                Image(systemName: isFavorite ? "star.fill" : "star")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(isFavorite ? Color.hangGreenDark : Color.hangMuted)
                    .frame(width: 34, height: 34)
                    .background(
                        isFavorite ? Color.hangGreen.opacity(0.28) : Color.hangCream,
                        in: Circle()
                    )
                    .overlay {
                        Circle()
                            .stroke(Color.hangLine.opacity(0.8), lineWidth: 1)
                    }
                    .frame(width: 44, height: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(
                isFavorite
                    ? "Remove \(plan.title) from favorites"
                    : "Add \(plan.title) to favorites"
            )
            .padding(.top, 8)
            .padding(.trailing, 8)
        }
    }
}
```

- [ ] **Step 4: Update all FavoritePlanCard call sites to pass `isIncompatible`**

There are three call sites: favorites section (line ~251), `myRoutines` (line ~451), and `libraryPlans` (line ~478). Update all three:

Favorites:
```swift
                    FavoritePlanCard(
                        plan: plan,
                        board: store.board(for: plan),
                        isFavorite: store.isFavorite(plan),
                        isIncompatible: store.isIncompatible(plan, on: store.selectedBoard)
                    ) {
                        store.toggleFavorite(plan)
                    }
```

My routines:
```swift
                                FavoritePlanCard(
                                    plan: plan,
                                    board: store.board(for: plan),
                                    isFavorite: store.isFavorite(plan),
                                    isIncompatible: store.isIncompatible(plan, on: store.selectedBoard)
                                ) {
                                    store.toggleFavorite(plan)
                                }
```

Library plans:
```swift
                                FavoritePlanCard(
                                    plan: plan,
                                    board: store.board(for: plan),
                                    isFavorite: store.isFavorite(plan),
                                    isIncompatible: store.isIncompatible(plan, on: store.selectedBoard)
                                ) {
                                    store.toggleFavorite(plan)
                                }
```

- [ ] **Step 5: Update the subtitle copy**

Change line 402 from:

```swift
                        Text("Official manufacturer sequences and source-linked adapted protocols, matched to your board.")
```

To:

```swift
                        Text("Official manufacturer sequences and source-linked adapted protocols. Hold targets are matched to your board.")
```

- [ ] **Step 6: Build and verify**

Run: `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -5`
Expected: BUILD SUCCEEDED

- [ ] **Step 7: Commit**

```bash
git add HangTen/Models/AppStore.swift HangTen/Views/RootView.swift
git commit -m "feat: show Not on this board badge for plans with unresolved holds"
```

---

### Task 7: Update existing tests

**Files:**
- Modify: `HangTenTests/PlanStorageTests.swift:1159`
- Modify: `HangTenTests/BoardSourceBoundaryTests.swift:55`

- [ ] **Step 1: Update PlanStorageTests**

In `PlanStorageTests.swift`, the test around line 1159 asserts that `BoardTargetResolver.resolveHoldIDs` returns empty for incompatible holds. Update to use `substituteHoldIDs` and assert non-empty (since substitutes are found):

Find the assertion and change from checking `resolveHoldIDs` returns empty to checking `substituteHoldIDs` returns a result, OR leave as-is if the test is specifically about exact resolution. Review the test context to decide.

- [ ] **Step 2: Update BoardSourceBoundaryTests**

In `BoardSourceBoundaryTests.swift` around line 55, the test checks `resolveHoldIDs` returns empty. This test validates that exact resolution fails — leave it as-is since `resolveHoldIDs` still exists and still returns empty for no-match cases.

- [ ] **Step 3: Run all tests**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -10`
Expected: ALL TESTS PASSED

- [ ] **Step 4: Commit**

```bash
git add HangTenTests/
git commit -m "test: update tests for cross-board plan visibility"
```

---

### Task 8: Final verification

- [ ] **Step 1: Run full test suite**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -15`
Expected: ALL TESTS PASSED

- [ ] **Step 2: Run linter if configured**

Check for lint configuration and run if available.

- [ ] **Step 3: Final commit if needed**

```bash
git status
```
