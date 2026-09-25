# Hand Choice by Board Capacity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the blocking hand-choice sheet with an inline menu that defaults from the selected board's hand capacity, and make a both-hands choice resolve to paired holds on a two-hand-capable board.

**Architecture:** A pure default-preference policy and a capacity-aware `both` materialization drive the session hand model. `RootView` presents the choice as a header `Menu` instead of a sheet and applies the default on appear. The two Lattice routines are recoded from `either` to `double` with `.bilateralPair` targets, regenerating `PlanLibrary.json` and correcting the routine guide and source audit.

**Tech Stack:** Swift, SwiftUI, XCTest/XCUITest, Xcode 26, `scripts/export-plan-library.sh`.

**Reference spec:** `docs/superpowers/specs/2026-09-25-hand-choice-board-capacity-design.md`

---

## File structure

- `HangTen/Models/PlanStorage.swift` — add `ContactRequirement.bilateralSelection`.
- `HangTen/Models/TrainingModels.swift` — add `WorkoutSessionHandPreference.defaultPreference` and `HandChoiceCopy`; recode the two Lattice plans.
- `HangTen/Models/WorkoutTimeline.swift` — capacity-aware `materializeBoth`.
- `HangTen/Views/RootView.swift` — inline hand `Menu`, default application, remove the sheet.
- `HangTen/Resources/PlanLibrary.json` — regenerated, committed.
- `HangTenTests/WorkoutTimelineTests.swift` — model/materialization tests.
- `HangTenTests/AppStoreTests.swift` — recoded-plan board-resolution test.
- `HangTenUITests/GripCueSnapshotUITests.swift` — flows that tapped the removed sheet.
- `docs/ADDING_A_ROUTINE.md` — amend the `.bilateralPair` rule.
- `docs/source-audits/2026-08-10-plan-cue-provenance.md` — correct the two Lattice rows.

Define this test helper once in the shell, then use `ht_test` in every step
below (adjust the simulator destination to an isolated device for this
workspace):

```sh
ht_test() {
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
    -derivedDataPath .context/DerivedData "$@"
}
```

---

### Task 1: `ContactRequirement.bilateralSelection`

**Files:**
- Modify: `HangTen/Models/PlanStorage.swift:248-259` (after `singleHandSelection`)
- Test: `HangTenTests/WorkoutTimelineTests.swift`

- [ ] **Step 1: Write the failing test**

Add to `WorkoutTimelineTests`:

```swift
func testBilateralSelectionWidensSingleRequirementToPair() {
    let single = ContactRequirement(kind: .edge, fingerCapacity: 4, selection: .single)
    XCTAssertEqual(single.bilateralSelection.selection, .bilateralPair)
    XCTAssertEqual(single.bilateralSelection.kind, .edge)
    XCTAssertEqual(single.bilateralSelection.fingerCapacity, 4)

    let alreadyPaired = ContactRequirement(kind: .edge, selection: .bilateralPair)
    XCTAssertEqual(alreadyPaired.bilateralSelection, alreadyPaired)

    let pinned = ContactRequirement(contactID: "left-edge", kind: .edge, selection: .single)
    XCTAssertEqual(
        pinned.bilateralSelection,
        pinned,
        "An exact contact cannot form a pair and must stay single"
    )
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `ht_test -only-testing:HangTenTests/WorkoutTimelineTests/testBilateralSelectionWidensSingleRequirementToPair`
Expected: FAIL to compile — value of type `ContactRequirement` has no member `bilateralSelection`.

- [ ] **Step 3: Write minimal implementation**

In `PlanStorage.swift`, immediately after the `singleHandSelection` property (ends at line 259), add:

```swift
    /// A copy of this requirement widened to a two-hand paired selection. Used
    /// when a both-hands choice is materialized on a board that fits two hands:
    /// the step resolves to the board's paired left/right holds. An exact
    /// contact pin cannot form a pair, so it keeps its single selection.
    var bilateralSelection: ContactRequirement {
        guard selection != .bilateralPair, contactID == nil else { return self }
        return ContactRequirement(
            kind: kind,
            shape: shape,
            depth: depth,
            fingerCapacity: fingerCapacity,
            handCapacity: handCapacity,
            selection: .bilateralPair
        )
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `ht_test -only-testing:HangTenTests/WorkoutTimelineTests/testBilateralSelectionWidensSingleRequirementToPair`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add HangTen/Models/PlanStorage.swift HangTenTests/WorkoutTimelineTests.swift
git commit -m "feat: add bilateral contact selection"
```

---

### Task 2: default preference and capacity-aware copy

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:1551-1566` (after `WorkoutSessionHandPreference`)
- Test: `HangTenTests/WorkoutTimelineTests.swift`

- [ ] **Step 1: Write the failing test**

Add to `WorkoutTimelineTests`:

```swift
func testDefaultHandPreferenceFollowsBoardCapacity() {
    XCTAssertEqual(WorkoutSessionHandPreference.defaultPreference(boardHandCapacity: 2), .both)
    XCTAssertEqual(WorkoutSessionHandPreference.defaultPreference(boardHandCapacity: 1), .alternate)
}

func testHandChoiceCopyOnlySaysTwoBoardsForOneHandedBoards() {
    XCTAssertEqual(HandChoiceCopy.bothHandsTitle(boardIsOneHanded: false), "Both hands")
    XCTAssertEqual(HandChoiceCopy.bothHandsTitle(boardIsOneHanded: true), "Both hands (two boards)")
    XCTAssertEqual(
        HandChoiceCopy.bothHandsHint(boardIsOneHanded: false),
        "Both hands simultaneously on this board."
    )
    XCTAssertEqual(
        HandChoiceCopy.bothHandsHint(boardIsOneHanded: true),
        "Both hands simultaneously on two boards."
    )
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `ht_test -only-testing:HangTenTests/WorkoutTimelineTests/testDefaultHandPreferenceFollowsBoardCapacity`
Expected: FAIL to compile — no member `defaultPreference` / type `HandChoiceCopy`.

- [ ] **Step 3: Write minimal implementation**

In `TrainingModels.swift`, after the `WorkoutSessionHandPreference` enum (line 1566), add:

```swift
extension WorkoutSessionHandPreference {
    /// Start-of-session default derived from the selected board's hand capacity.
    /// A board that fits one hand at a time defaults to alternating sides; a
    /// board that fits both hands defaults to a simultaneous both-hands set.
    static func defaultPreference(boardHandCapacity: Int) -> WorkoutSessionHandPreference {
        boardHandCapacity <= 1 ? .alternate : .both
    }
}

/// User-facing wording for the start-of-session hand choice. Only a one-handed
/// board ever asks the athlete to set up two boards.
enum HandChoiceCopy {
    static func bothHandsTitle(boardIsOneHanded: Bool) -> String {
        boardIsOneHanded ? "Both hands (two boards)" : "Both hands"
    }

    static func bothHandsHint(boardIsOneHanded: Bool) -> String {
        boardIsOneHanded
            ? "Both hands simultaneously on two boards."
            : "Both hands simultaneously on this board."
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `ht_test -only-testing:HangTenTests/WorkoutTimelineTests/testDefaultHandPreferenceFollowsBoardCapacity -only-testing:HangTenTests/WorkoutTimelineTests/testHandChoiceCopyOnlySaysTwoBoardsForOneHandedBoards`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add HangTen/Models/TrainingModels.swift HangTenTests/WorkoutTimelineTests.swift
git commit -m "feat: add capacity-aware hand choice default and copy"
```

---

### Task 3: capacity-aware `materializeBoth`

**Files:**
- Modify: `HangTen/Models/WorkoutTimeline.swift:91-119`
- Test: `HangTenTests/WorkoutTimelineTests.swift:417-444` (replace `testSessionStepsBothKeepsDoubleBothWithSingleHandSelection`)

- [ ] **Step 1: Replace the existing test with the new expectations**

Replace the whole `testSessionStepsBothKeepsDoubleBothWithSingleHandSelection` method with:

```swift
func testSessionStepsBothPairsHoldsOnTwoHandedBoardsAndUsesSingleHoldOnOneHandedBoards() throws {
    let either = WorkoutStep(
        id: "either", number: 1, title: "Both", instruction: "Hang.",
        accessory: "", duration: 7, phase: .hang,
        segments: [WorkoutSegment(
            kind: .work,
            target: .fromLegacyTargets([ContactRequirement(kind: .jug, selection: .single)]),
            timing: .fixed,
            duration: 7
        )],
        handUse: .either, side: .both
    )

    let twoHanded = try XCTUnwrap(
        WorkoutSessionHandResolver.sessionSteps(
            from: [either],
            preference: .both,
            boardIsOneHanded: false
        ).first
    )
    XCTAssertEqual(twoHanded.handUse, .double)
    XCTAssertEqual(twoHanded.side, .both)
    XCTAssertEqual(twoHanded.workRequirements.map(\.selection), [.bilateralPair])
    XCTAssertEqual(
        twoHanded.segments.first?.contactRequirements.map(\.selection),
        [.bilateralPair]
    )

    let oneHanded = try XCTUnwrap(
        WorkoutSessionHandResolver.sessionSteps(
            from: [either],
            preference: .both,
            boardIsOneHanded: true
        ).first
    )
    XCTAssertEqual(oneHanded.handUse, .double)
    XCTAssertEqual(oneHanded.side, .both)
    XCTAssertEqual(oneHanded.workRequirements.map(\.selection), [.single])
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `ht_test -only-testing:HangTenTests/WorkoutTimelineTests/testSessionStepsBothPairsHoldsOnTwoHandedBoardsAndUsesSingleHoldOnOneHandedBoards`
Expected: FAIL — `twoHanded` still resolves `.single`, assertion `[.bilateralPair]` fails.

- [ ] **Step 3: Write minimal implementation**

In `WorkoutTimeline.swift`, replace the body of `materializeBoth` (lines 91-119) with:

```swift
    private static func materializeBoth(
        _ step: WorkoutStep,
        boardIsOneHanded: Bool
    ) -> WorkoutStep {
        guard stepNeedsHandResolution(step, boardIsOneHanded: boardIsOneHanded) else {
            return step
        }
        // A two-hand-capable board holds both hands on its paired left/right
        // holds; a one-hand board resolves one hold, performed on two boards.
        let transform: (ContactRequirement) -> ContactRequirement = boardIsOneHanded
            ? { $0.singleHandSelection }
            : { $0.bilateralSelection }
        let bothHandedSegments = step.segments.map { segment in
            segment.mappingRequirements(transform)
        }
        return WorkoutStep(
            id: step.id,
            number: step.number,
            title: step.title,
            instruction: step.instruction,
            accessory: step.accessory,
            duration: step.duration,
            phase: step.phase,
            segments: bothHandedSegments,
            gripType: step.gripType,
            fingerConfiguration: step.fingerConfiguration,
            handUse: .double,
            side: .both,
            action: step.action,
            repetitions: step.repetitions,
            externalLoadKGF: step.externalLoadKGF,
            timedWorkDuration: step.timedWorkDuration
        )
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `ht_test -only-testing:HangTenTests/WorkoutTimelineTests/testSessionStepsBothPairsHoldsOnTwoHandedBoardsAndUsesSingleHoldOnOneHandedBoards`
Expected: PASS.

- [ ] **Step 5: Run the surrounding suite**

Run: `ht_test -only-testing:HangTenTests/WorkoutTimelineTests`
Expected: PASS (all timeline tests, including one-handed materialization tests).

- [ ] **Step 6: Commit**

```bash
git add HangTen/Models/WorkoutTimeline.swift HangTenTests/WorkoutTimelineTests.swift
git commit -m "feat: resolve both hands to paired holds on two-hand boards"
```

---

### Task 4: recode the two Lattice routines

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:2830-2835` (`maxHangs20mmEdgeTarget`)
- Modify: `HangTen/Models/TrainingModels.swift:2934-2993` (max-hangs steps)
- Modify: `HangTen/Models/TrainingModels.swift:3305-3312` (abrahangs grips)
- Modify: `HangTen/Models/TrainingModels.swift:3314-3328` (abrahangs step hand use)
- Regenerate: `HangTen/Resources/PlanLibrary.json`
- Modify: `docs/ADDING_A_ROUTINE.md:120-121`
- Modify: `docs/source-audits/2026-08-10-plan-cue-provenance.md:32-44`
- Test: `HangTenTests/AppStoreTests.swift`

- [ ] **Step 1: Write the failing test**

Add to `AppStoreTests`:

```swift
func testTwoHandedLatticePlansResolvePairedHoldsOnAtLeastOneBoard() throws {
    let store = AppStore(defaults: makeDefaults())

    for planID in ["research.max-hangs", "research.abrahangs"] {
        let plan = try XCTUnwrap(store.plans.first { $0.id == planID })

        let compatibleBoards = BoardCatalog.all.filter { !store.isIncompatible(plan, on: $0) }
        XCTAssertFalse(
            compatibleBoards.isEmpty,
            "\(planID) must resolve on at least one registered board"
        )

        let resolvesAPair = compatibleBoards.contains { board in
            plan.steps.contains { step in
                guard !step.isRestStep else { return false }
                let contacts = (try? ContactResolver.resolve(
                    step.workRequirements,
                    step: step,
                    board: board
                )) ?? []
                return contacts.count == 2
            }
        }
        XCTAssertTrue(resolvesAPair, "\(planID) should resolve a two-hold pair on a compatible board")
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `ht_test -only-testing:HangTenTests/AppStoreTests/testTwoHandedLatticePlansResolvePairedHoldsOnAtLeastOneBoard`
Expected: FAIL — the steps are still `.either` with `.single` targets, so no step resolves two contacts.

- [ ] **Step 3: Change the max-hangs target to a pair**

In `TrainingModels.swift`, replace `maxHangs20mmEdgeTarget` (lines 2830-2835) with:

```swift
    /// Lattice Half 4 Max Hang names a 20 mm edge and is a two-handed hang.
    /// `.bilateralPair` resolves the board's paired left/right 20 mm holds.
    private static let maxHangs20mmEdgeTarget = ContactRequirement.edge(
        depth: .range(.init(minimum: 20, maximum: 20)),
        selection: .bilateralPair
    )
```

- [ ] **Step 4: Change the max-hangs steps to `.double`**

In `TrainingModels.swift`, for each of the five max-hangs steps (lines 2934-2993), change `handUse: .either` to `handUse: .double`. There are five occurrences inside the `maxHangs` plan; leave the `abrahangs` occurrence for Step 6. Each changed step now reads `handUse: .double` where it previously read `handUse: .either`.

- [ ] **Step 5: Run the test to verify max-hangs now passes its half**

Run: `ht_test -only-testing:HangTenTests/AppStoreTests/testTwoHandedLatticePlansResolvePairedHoldsOnAtLeastOneBoard`
Expected: FAIL only on `research.abrahangs` (max-hangs half passes).

- [ ] **Step 6: Change the abrahangs targets and step hand use**

In `TrainingModels.swift`, replace the `grips` array (lines 3305-3312) with:

```swift
            let grips: [(title: String, targets: [ContactRequirement], grip: GripType, fingerConfiguration: FingerConfiguration?)] = [
                ("Half 4 Hang", [ContactRequirement(kind: .edge, fingerCapacity: 4, selection: .bilateralPair)], .halfCrimp, nil),
                ("F3 Open Hang", [ContactRequirement(kind: .edge, fingerCapacity: 3, selection: .bilateralPair)], .openHand, FingerConfiguration(engagedFingers: [.index, .middle, .ring])),
                ("M2 Open Hang", [ContactRequirement(kind: .edge, fingerCapacity: 2, selection: .bilateralPair)], .openHand, FingerConfiguration(engagedFingers: [.middle, .ring])),
                ("F2 Open Hang", [ContactRequirement(kind: .edge, fingerCapacity: 2, selection: .bilateralPair)], .openHand, FingerConfiguration(engagedFingers: [.index, .middle])),
                ("B3 Half Hang", [ContactRequirement(kind: .edge, fingerCapacity: 3, selection: .bilateralPair)], .halfCrimp, FingerConfiguration(engagedFingers: [.middle, .ring, .pinky])),
                ("F3 Half Hang", [ContactRequirement(kind: .edge, fingerCapacity: 3, selection: .bilateralPair)], .halfCrimp, FingerConfiguration(engagedFingers: [.index, .middle, .ring]))
            ]
```

Then in the abrahangs `hangStep` call (line 3326) change `handUse: .either` to `handUse: .double`.

- [ ] **Step 7: Run the test to verify it passes**

Run: `ht_test -only-testing:HangTenTests/AppStoreTests/testTwoHandedLatticePlansResolvePairedHoldsOnAtLeastOneBoard`
Expected: PASS.

- [ ] **Step 8: Regenerate and check the bundled plan library**

Run:
```sh
scripts/export-plan-library.sh
scripts/export-plan-library.sh --check
```
Expected: the exporter rewrites `HangTen/Resources/PlanLibrary.json`, and `--check` prints that the JSON matches the source-audited definitions (exit 0).

- [ ] **Step 9: Amend the routine guide rule**

In `docs/ADDING_A_ROUTINE.md`, replace lines 120-121:

```
- `.bilateralPair` only when the source prescribes the pair; otherwise
  `.single` resolves one stable geometry-selected contact.
```

with:

```
- `.bilateralPair` when the source prescribes both hands together or names a
  pair; otherwise `.single` resolves one stable geometry-selected contact.
```

- [ ] **Step 10: Correct the source audit**

In `docs/source-audits/2026-08-10-plan-cue-provenance.md`, replace the section body at lines 32-44 (heading through the two table rows) with:

```
## Two-handed capability correction — 2026-09-25

`research.max-hangs` and `research.abrahangs` are both-handed prescriptions.
Their work steps previously carried `WorkoutHandUse.either` with the note that
Hang Ten materializes a single athlete-selected hand. They are recoded to
`handUse: .double` with `.bilateralPair` targets so both hands resolve to the
board's paired holds. No one-hand selection remains for these plans.

| Plan ID | Source URL | Two-handed encoding | Rationale |
| --- | --- | --- | --- |
| `research.max-hangs` | [Lattice Half 4 — Hang — Max](https://latticetraining.com/workout/1c4cc25a-ebe8-4930-8541-5b604a831c5f/half-4-hang-max/) | All five work steps are `double` / `both`; recovery remains `double` / `both`; target is `.bilateralPair` on the 20 mm edge. | The source prescribes a two-handed near-maximal 20 mm four-finger half-crimp hang; the five 7-second tasks and their recoveries are unchanged. |
| `research.abrahangs` | [Lattice Abrahangs Protocol](https://latticetraining.com/workout/1832c13b-14c1-444c-82a2-e72b22a6fb13/abrahangs-protocol) | All six work steps are `double` / `both`; targets are `.bilateralPair` on the indicated finger-capacity edges. | The source's six two-handed finger-position hangs, low-intensity feet-supported prescription, and the 10/50 app timing adaptation are retained. |
```

- [ ] **Step 11: Run the full model suites**

Run: `ht_test -only-testing:HangTenTests/WorkoutTimelineTests -only-testing:HangTenTests/AppStoreTests -only-testing:HangTenTests/PlanStorageTests`
Expected: PASS.

- [ ] **Step 12: Commit**

```bash
git add HangTen/Models/TrainingModels.swift HangTen/Resources/PlanLibrary.json \
  docs/ADDING_A_ROUTINE.md docs/source-audits/2026-08-10-plan-cue-provenance.md \
  HangTenTests/AppStoreTests.swift
git commit -m "feat: encode Lattice max-hang routines as two-handed pairs"
```

---

### Task 5: inline hand menu on the workout page

**Files:**
- Modify: `HangTen/Views/RootView.swift:1895-1898` (state)
- Modify: `HangTen/Views/RootView.swift:2138-2183` (remove sheet)
- Modify: `HangTen/Views/RootView.swift:2643-2650` (header menu insertion)
- Modify: `HangTen/Views/RootView.swift:2976-2986` (`chooseHandPreference` → `applyHandPreference`)
- Modify: `HangTen/Views/RootView.swift:2995-3036` (`toggleRunning` gate)
- Modify: `HangTen/Views/RootView.swift:2184-2210` (`onAppear` default)
- Modify: `HangTen/Models/WorkoutTimeline.swift` (add resolution-aware default)
- Test: `HangTenTests/WorkoutTimelineTests.swift`

- [ ] **Step 1: Remove the sheet state and sheet**

Delete the line `@State private var showsHandSidePicker = false` (line 1898).

Delete the entire `.sheet(isPresented: $showsHandSidePicker) { ... }` block and its `.interactiveDismissDisabled()` (lines 2138-2183).

- [ ] **Step 2: Add the header menu**

In `sessionHeader`, immediately after the `Button("Routine") { ... }` block (ends line 2650), insert:

```swift
            if planNeedsHandChoice {
                handPreferenceMenu()
            }
```

- [ ] **Step 3: Add menu helpers next to `handPreferenceButton`**

Replace the existing `handPreferenceButton` and `chooseHandPreference` (lines 2952-2986) with:

```swift
	private func handPreferenceMenu() -> some View {
		Menu {
			handPreferenceMenuButton(.left, title: "Left hand", accessibilityID: "handSide.left")
			handPreferenceMenuButton(.right, title: "Right hand", accessibilityID: "handSide.right")
			handPreferenceMenuButton(.alternate, title: "Alternate hands", accessibilityID: "handSide.alternate")
			handPreferenceMenuButton(
				.both,
				title: HandChoiceCopy.bothHandsTitle(boardIsOneHanded: boardIsOneHanded),
				accessibilityID: "handSide.both"
			)
		} label: {
			HStack(spacing: 6) {
				Image(systemName: "hand.raised")
				Text(handChoiceLabel)
			}
			.font(.system(size: 13, weight: .bold, design: .rounded))
			.foregroundStyle(Color.hangGreenDark)
		}
		.disabled(!WorkoutSessionPolicy.isFirstStart(routineStartedAt: sessionState.routineStartedAt))
		.accessibilityLabel("Hand choice, \(handChoiceLabel)")
		.accessibilityHint(HandChoiceCopy.bothHandsHint(boardIsOneHanded: boardIsOneHanded))
		.accessibilityIdentifier("workout.handPicker")
	}

	private func handPreferenceMenuButton(
		_ preference: WorkoutSessionHandPreference,
		title: String,
		accessibilityID: String
	) -> some View {
		Button {
			applyHandPreference(preference)
		} label: {
			if handPreference == preference {
				Label(title, systemImage: "checkmark")
			} else {
				Text(title)
			}
		}
		.accessibilityIdentifier(accessibilityID)
	}

	private var handChoiceLabel: String {
		switch handPreference {
		case .left: "Left hand"
		case .right: "Right hand"
		case .alternate: "Alternate hands"
		case .both, .none: HandChoiceCopy.bothHandsTitle(boardIsOneHanded: boardIsOneHanded)
		}
	}

	private func applyHandPreference(_ preference: WorkoutSessionHandPreference) {
		handPreference = preference
		sessionSteps = WorkoutSessionHandResolver.sessionSteps(
			from: plan.steps,
			preference: preference,
			boardIsOneHanded: boardIsOneHanded
		)
		initializeStopwatches()
	}
```

- [ ] **Step 3b: Add a resolution-aware default and its tests**

A capacity-2 default of `.both` must not break custom either-hand routines on a board where a both-hands target cannot pair: recording fails closed for custom provenance, so the default must downgrade to `.alternate` when the both materialization does not resolve. Add to `HangTen/Models/WorkoutTimeline.swift`, in an `extension WorkoutSessionHandResolver` after the enum:

```swift
extension WorkoutSessionHandResolver {
    /// The capacity default, downgraded to `.alternate` when a both-hands
    /// materialization cannot resolve every work requirement on this board.
    static func defaultPreference(
        plan: TrainingPlan,
        board: BoardRevision
    ) -> WorkoutSessionHandPreference {
        let capacityDefault = WorkoutSessionHandPreference.defaultPreference(
            boardHandCapacity: board.handCapacity
        )
        guard capacityDefault == .both else { return capacityDefault }
        let steps = sessionSteps(
            from: plan.steps,
            preference: .both,
            boardIsOneHanded: board.isOneHanded
        )
        let resolvesEveryStep = steps.allSatisfy { step in
            guard !step.isRestStep else { return true }
            let requirements = step.workRequirements
            guard !requirements.isEmpty else { return true }
            return (try? ContactResolver.resolve(
                requirements,
                step: step,
                board: board
            ))?.isEmpty == false
        }
        return resolvesEveryStep ? .both : .alternate
    }
}
```

Add these tests to the `WorkoutTimelineTests` class:

```swift
func testResolutionAwareDefaultFallsBackToAlternateWhenBothCannotResolve() {
    let board = BoardRevision(
        id: "fixture.single-contact",
        revisionID: "test",
        manufacturer: "Fixture",
        name: "Single contact",
        subtitle: "",
        dimensions: nil,
        aspectRatio: 1,
        handCapacity: 2,
        contacts: [
            PhysicalContact(id: "only-edge", name: "Only edge", kind: .edge, handCapacity: 1)
        ],
        productURL: URL(string: "https://example.com/board")!,
        photoAssetName: nil
    )
    let plan = TrainingPlan(
        id: "fixture.either",
        title: "Either",
        subtitle: "",
        level: "",
        sourceLabel: "",
        sourceURL: URL(string: "https://example.com/plan")!,
        provenance: .adapted,
        boardID: board.id,
        steps: [
            WorkoutStep(
                id: "either", number: 1, title: "Either", instruction: "",
                accessory: "", duration: 7, phase: .hang,
                segments: [WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([ContactRequirement(kind: .edge, selection: .single)]),
                    timing: .fixed,
                    duration: 7
                )],
                handUse: .either, side: .both
            )
        ]
    )

    XCTAssertEqual(
        WorkoutSessionHandResolver.defaultPreference(plan: plan, board: board),
        .alternate
    )
}

func testResolutionAwareDefaultKeepsBothWhenAPairResolves() throws {
    let plan = try XCTUnwrap(PlanCatalog.all.first { $0.id == "research.max-hangs" })
    let board = try XCTUnwrap(
        BoardCatalog.all.first { board in
            plan.steps.allSatisfy { step in
                guard !step.isRestStep else { return true }
                let requirements = step.workRequirements
                guard !requirements.isEmpty else { return true }
                return (try? ContactResolver.resolve(requirements, step: step, board: board))?.isEmpty == false
            }
        },
        "Expected at least one registered board where Max Hangs resolves its pair"
    )

    XCTAssertEqual(
        WorkoutSessionHandResolver.defaultPreference(plan: plan, board: board),
        .both
    )
}
```

Run: `ht_test -only-testing:HangTenTests/WorkoutTimelineTests/testResolutionAwareDefaultFallsBackToAlternateWhenBothCannotResolve -only-testing:HangTenTests/WorkoutTimelineTests/testResolutionAwareDefaultKeepsBothWhenAPairResolves`
Expected: 2 tests, 0 failures. If the real-board test cannot find a paired contact, report it rather than guessing a different board.

- [ ] **Step 4: Apply the default on appear**

In `onAppear` (line 2184), immediately after `configureRecorder()`, add:

```swift
			if planNeedsHandChoice, handPreference == nil {
				applyHandPreference(
					.defaultPreference(plan: plan, board: board)
				)
			}
```

- [ ] **Step 5: Remove the pre-start sheet gate in `toggleRunning`**

Replace the block at lines 2995-3002:

```swift
		if sessionState.activeStartUptime == nil,
		   WorkoutSessionPolicy.isFirstStart(routineStartedAt: sessionState.routineStartedAt),
		   planNeedsHandChoice,
		   handPreference == nil {
			showsHandSidePicker = true
			return
		}
```

with:

```swift
		if sessionState.activeStartUptime == nil,
		   WorkoutSessionPolicy.isFirstStart(routineStartedAt: sessionState.routineStartedAt),
		   planNeedsHandChoice,
		   handPreference == nil {
			applyHandPreference(
				.defaultPreference(plan: plan, board: board)
			)
		}
```

- [ ] **Step 6: Build to verify it compiles**

Run:
```sh
xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator \
  -configuration Debug -derivedDataPath .context/DerivedData build
```
Expected: BUILD SUCCEEDED with no references to `showsHandSidePicker` or `chooseHandPreference`.

- [ ] **Step 7: Run the unit suites again**

Run: `ht_test -only-testing:HangTenTests/WorkoutTimelineTests -only-testing:HangTenTests/AppStoreTests`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add HangTen/Views/RootView.swift
git commit -m "feat: replace hand-choice sheet with a capacity-aware header menu"
```

---

### Task 6: update the UI flows that used the removed sheet

**Files:**
- Modify: `HangTenUITests/GripCueSnapshotUITests.swift:48-79, 190-228`

These flows use `research.max-hangs`, which is now two-handed on the default (capacity-2) board, so the hand menu no longer appears and the start goes straight to the workout.

- [ ] **Step 1: Remove the hand tap in the landscape test**

In `testLandscapeManualWorkoutHidesStreamingSensorMeter`, replace:

```swift
        tapStartRoutine()
        XCTAssertTrue(app.buttons["handSide.left"].waitForExistence(timeout: 10))
        app.buttons["handSide.left"].tap()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
```

with:

```swift
        tapStartRoutine()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
```

- [ ] **Step 2: Make the deep-link helper prefer the running session**

Replace the body of `openWorkoutDeepLinkAndChooseLeftHandIfNeeded` with:

```swift
    private func openWorkoutDeepLinkAndChooseLeftHandIfNeeded(
        perAttemptTimeout: TimeInterval = 20
    ) {
        waitForTrainShellReady(timeout: 20)
        let handChoice = app.buttons["handSide.left"]
        let pause = app.buttons["Pause"]
        app.open(workoutDeepLink)
        if !pause.waitForExistence(timeout: perAttemptTimeout), !handChoice.exists {
            waitForTrainShellReady(timeout: 10)
            app.open(workoutDeepLink)
        }
        if handChoice.exists {
            handChoice.tap()
        }
        XCTAssertTrue(pause.waitForExistence(timeout: perAttemptTimeout))
    }
```

- [ ] **Step 3: Remove the two remaining hand taps**

In `testInlineScaleConnectionStartsWithExistingSensorPreparation`, replace:

```swift
        tapStartRoutine()
        XCTAssertTrue(app.buttons["handSide.left"].waitForExistence(timeout: 10))
        app.buttons["handSide.left"].tap()
        let skip = app.buttons["Skip preparation"]
```

with:

```swift
        tapStartRoutine()
        let skip = app.buttons["Skip preparation"]
```

In `testScaleSelectionDoesNotBlockStartWhenDisconnected`, replace:

```swift
        tapStartRoutine()
        XCTAssertTrue(app.buttons["handSide.left"].waitForExistence(timeout: 10))
        app.buttons["handSide.left"].tap()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
```

with:

```swift
        tapStartRoutine()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
```

- [ ] **Step 4: Run the UI suite**

Run: `ht_test -only-testing:HangTenUITests/GripCueSnapshotUITests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add HangTenUITests/GripCueSnapshotUITests.swift
git commit -m "test: update UI flows for the inline hand menu"
```

---

### Task 7: full verification

**Files:** none (verification only)

- [ ] **Step 1: Regenerate and check the plan library**

Run:
```sh
scripts/export-plan-library.sh
scripts/export-plan-library.sh --check
git diff --exit-code HangTen/Resources/PlanLibrary.json
```
Expected: exit 0 for all three; the working tree shows no uncommitted JSON change.

- [ ] **Step 2: Run the targeted unit suites**

Run: `ht_test -only-testing:HangTenTests/WorkoutTimelineTests -only-testing:HangTenTests/AppStoreTests -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/WorkoutActivityRecordingTests`
Expected: PASS.

- [ ] **Step 3: Confirm no stale references**

Run:
```sh
rg -n "showsHandSidePicker|chooseHandPreference" HangTen HangTenTests HangTenUITests
```
Expected: no matches.

- [ ] **Step 4: Validate the menu visually on an isolated simulator**

Use the `validate-hang-ten-ios` skill. Check:
- On a capacity-2 board with a routine that needs a choice, the header shows a "Both hands" menu defaulting to Both, and no sheet blocks start.
- The Both option reads "Both hands" (never "two boards").
- On a one-handed board, the Both option reads "Both hands (two boards)" and the default is "Alternate hands".
- The menu disables after the first start.

- [ ] **Step 5: Final commit if the validation produced fixes**

```bash
git add -A
git commit -m "fix: address inline hand menu validation feedback"
```

---

## Self-review notes

- Spec coverage: default policy (Task 2), capacity-aware both materialization (Tasks 1, 3), inline menu + copy (Tasks 2, 5), recoded plans (Task 4), docs (Task 4), tests (Tasks 1-4, 6, 7).
- Type consistency: `defaultPreference(boardHandCapacity:)`, `bilateralSelection`, `HandChoiceCopy.bothHandsTitle(boardIsOneHanded:)` / `bothHandsHint(boardIsOneHanded:)`, `applyHandPreference(_:)`, and `workout.handPicker` are used with the same signatures across tasks.
- Known acceptance: recoded plans become hidden on boards without a symmetric matching pair; verified to resolve on at least one registered board in Task 4.
