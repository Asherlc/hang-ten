# Grip Cue Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate hand posture, board finger capacity, and exact finger engagement so Hang Ten’s grip cues never infer a particular finger set from a pocket or sloper.

**Architecture:** Keep `GripType` as the three hand postures. Add a codable `FingerConfiguration` for exact workout prescriptions and a scalar `BoardHold.fingerCapacity` for physical capacity. Carry optional posture/configuration fields through plan definitions, runtime steps, custom routines, and cue views; resolve explicit step values before hold metadata.

**Tech Stack:** Swift 6 / SwiftUI, Foundation Codable, XCTest, Xcode simulator validation, the existing `PlanLibrary.json` exporter.

## Global Constraints

- `GripType` contains only `openHand`, `halfCrimp`, and `fullCrimp`.
- A `BoardHold` declares how many fingers can fit, but no individual finger set.
- `FingerConfiguration` can represent one arbitrary finger, any combination, or all four fingers.
- Hold targets/features continue to use pocket/sloper terminology; those terms are not grip postures.
- When only board capacity is available, the cue reports the number without naming or highlighting particular fingers.
- When an exact configuration is present, the cue highlights and labels those individual fingers.
- New output uses only the posture values and exact finger vocabulary; old combined values remain decodable.
- Grip pose glyphs come only from `GripType`; cue rendering must not inspect `BoardHold.kind` to choose a posture.
- All shell commands use the repository’s `rtk` wrapper; derived build and review output stays under `.context`.
- Do not add third-party dependencies or change the plan schema version; the new field is optional and legacy decoding is field-compatible.

---

## File map

- Modify `HangTen/Models/TrainingModels.swift`: posture/finger domain types, board capacity metadata, runtime step propagation, and source-audited seed values.
- Modify `HangTen/Models/PlanStorage.swift`: persisted exact-finger field, legacy grip decoding, resolver propagation, and runtime-to-definition conversion.
- Modify `HangTen/Models/WorkoutStepNormalization.swift`: preserve exact finger configuration while expanding work segments.
- Modify `HangTen/Models/CustomRoutineDraft.swift`: retain and edit optional exact finger configurations in draft conversion.
- Modify `HangTen/Views/GripDiagramView.swift`: render posture independently and distinguish capacity-only from exact finger cues.
- Modify `HangTen/Views/RootView.swift`: pass finger configuration through plan preview/session layouts and add deterministic DEBUG finger review input.
- Modify `HangTen/Views/CustomRoutineEditorView.swift`: expose posture and optional exact finger selection separately.
- Regenerate `HangTen/Resources/PlanLibrary.json` with `scripts/export-plan-library.sh`.
- Extend existing tests in `HangTenTests/PlanStorageTests.swift`, `HangTenTests/WorkoutStepNormalizationTests.swift`, `HangTenTests/CustomRoutineDraftTests.swift`, and `HangTenTests/CustomRoutineStoreTests.swift`.

## Task 1: Add the posture, capacity, and exact-finger model

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:85-180, 340-455`
- Modify: `HangTen/Models/PlanStorage.swift:260-370`
- Test: `HangTenTests/PlanStorageTests.swift`

**Interfaces:**
- `GripType` produces only `.openHand`, `.halfCrimp`, and `.fullCrimp`.
- `FingerSlot` remains `.index`, `.middle`, `.ring`, `.pinky` and becomes `Codable`.
- `FingerConfiguration` exposes `engagedFingers: Set<FingerSlot>`, `count`, and a stable `orderedFingers` array in `FingerSlot.allCases` order.
- `BoardHold` exposes `fingerCapacity: Int` with a default of 4.
- `WorkoutStep`, `WorkoutStepDefinition`, and `MetoliusTaskDefinition` expose optional `fingerConfiguration` fields with nil defaults.

- [ ] **Step 1: Write failing model and migration tests.** Add tests that:

  1. decode `"sloper"`, `"twoFingerPocket"`, `"threeFingerPocket"`, and `"fourFingerPocket"` as `.openHand` through `GripType` Codable;
  2. round-trip `FingerConfiguration(engagedFingers: [.pinky])` and a non-contiguous set such as `[.index, .ring]`;
  3. decode and re-encode a `WorkoutStepDefinition` containing `fingerConfiguration`, asserting the new key is present and the posture raw value is new vocabulary.

  Use real `JSONDecoder`/`JSONEncoder` data and XCTest assertions; do not test mocks.

- [ ] **Step 2: Run the focused tests and verify the expected failure.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/PlanStorageTests
  ```

  Expected: compile/test failure because `FingerConfiguration`, the new persisted field, and the legacy posture decoder do not exist yet.

- [ ] **Step 3: Implement the minimal domain and persistence surface.**

  Define `FingerConfiguration` in `TrainingModels.swift` with a codable `engagedFingers` set, a non-empty decoding guard, `count`, and deterministic `orderedFingers`. Implement its Codable methods explicitly: decode an `engagedFingers` array into a set, reject an empty array, and encode `orderedFingers` so generated JSON is stable. Add a custom `GripType` Codable implementation that accepts current posture values and maps legacy hold-combined values to `.openHand`, while encoding only current raw values. Remove the old combined enum cases.

  Add `fingerCapacity` to `BoardHold`; keep `gripType` as posture metadata. Add optional `fingerConfiguration` to the runtime and definition structs, including coding keys, initializers, `withNumber`, and `WorkoutStepDefinition.from`. The decoder must accept an absent exact configuration and encode it only when present.

- [ ] **Step 4: Run the focused tests and verify green.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/PlanStorageTests
  ```

- [ ] **Step 5: Commit the model boundary.**

  ```sh
  rtk git add HangTen/Models/TrainingModels.swift HangTen/Models/PlanStorage.swift HangTenTests/PlanStorageTests.swift
  rtk git commit -m "Separate grip posture from finger configuration"
  ```

## Task 2: Migrate board/source data and propagate exact configuration

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:170-180, 520-730, 840-890, 1190-1265`
- Modify: `HangTen/Models/PlanStorage.swift:1035-1090, 1130-1185`
- Modify: `HangTen/Models/WorkoutStepNormalization.swift:35-90`
- Modify: `HangTenTests/WorkoutStepNormalizationTests.swift`
- Modify: `HangTenTests/CustomRoutineStoreTests.swift`
- Modify: `HangTen/Resources/PlanLibrary.json`

**Interfaces:**
- `BoardHold.defaultFeatures` receives `fingerCapacity`, not a combined grip value.
- `PlanDefinitionResolver` copies `stepDefinition.fingerConfiguration` into every resolved `WorkoutStep`.
- `WorkoutStepNormalizer.expand` copies exact configuration to work segments and clears it on generated rest steps.
- `WorkoutStepDefinition.from(_:)` round-trips both optional posture and exact configuration.

- [ ] **Step 1: Add failing propagation and capacity tests.** Add assertions that:

  - Compact II two-, three-, and four-finger pockets expose capacities 2, 3, and 4 while their posture is `.openHand` and no exact finger set is attached;
  - a resolved definition with `fingerConfiguration: .init(engagedFingers: [.index])` retains that value in `TrainingPlan.steps`;
  - compound-step expansion retains the exact value on work segments and sets it to nil on rest segments;
  - custom routine save/load preserves a non-contiguous exact configuration.

- [ ] **Step 2: Run the focused tests and verify they fail.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/WorkoutStepNormalizationTests -only-testing:HangTenTests/CustomRoutineStoreTests
  ```

- [ ] **Step 3: Update board and source-audited metadata.** Replace board `.sloper`, `.twoFingerPocket`, `.threeFingerPocket`, and `.fourFingerPocket` grip assignments with `.openHand` plus `fingerCapacity: 2/3/4` where applicable. Update default pocket features to use capacity. Replace legacy seed grip values with `.openHand`; do not add exact finger configurations unless a source explicitly prescribes individual fingers.

  Update `MetoliusTaskDefinition` construction and cycle builders to pass the optional exact configuration. Update resolver and normalizer conversions so the field follows work steps through all plan paths and is cleared for rest.

- [ ] **Step 4: Regenerate and audit the bundled plan library.** Run:

  ```sh
  rtk scripts/export-plan-library.sh
  rtk scripts/export-plan-library.sh --check
  rtk rg -n '"gripType"\s*:\s*"(sloper|twoFingerPocket|threeFingerPocket|fourFingerPocket)"' HangTen/Resources/PlanLibrary.json
  ```

  Expected: exporter check succeeds and the final search returns no matches.

- [ ] **Step 5: Run all model/persistence tests and commit.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/WorkoutStepNormalizationTests -only-testing:HangTenTests/CustomRoutineStoreTests
  rtk git add HangTen/Models/TrainingModels.swift HangTen/Models/PlanStorage.swift HangTen/Models/WorkoutStepNormalization.swift HangTen/Resources/PlanLibrary.json HangTenTests/WorkoutStepNormalizationTests.swift HangTenTests/CustomRoutineStoreTests.swift
  rtk git commit -m "Migrate board grip metadata to finger capacity"
  ```

## Task 3: Render independent posture and finger cues

**Files:**
- Modify: `HangTen/Views/GripDiagramView.swift:1-210`
- Modify: `HangTen/Views/RootView.swift:810-945, 1750-1840`
- Modify: `HangTen/Views/CustomRoutineEditorView.swift:270-325`
- Modify: `HangTen/Models/CustomRoutineDraft.swift:1-245`
- Test: `HangTenTests/CustomRoutineDraftTests.swift`

**Interfaces:**
- `GripDiagramView(hold:gripType:fingerConfiguration:)` resolves posture from explicit step value or `hold.gripType`, and resolves exact fingers from explicit step value or capacity from `hold.fingerCapacity`.
- `GripHandCueCard` accepts resolved posture and a capacity/exact-finger cue; it does not accept or inspect `hold.kind`.
- `CustomRoutineStepDraft` stores optional `fingerConfiguration` and can toggle a `FingerSlot` without mutating posture.

- [ ] **Step 1: Add failing draft/view-facing semantic tests.** Extend `CustomRoutineDraftTests` to verify that duplicating/editing a step preserves its exact finger configuration, and that converting a rest step clears both posture and exact finger configuration.

- [ ] **Step 2: Run the focused test and verify failure.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/CustomRoutineDraftTests
  ```

- [ ] **Step 3: Implement resolution and rendering.** Remove all `hold.kind` branches from posture glyph selection. Use palm/grabbing/fist for open/half/full crimp. Add a SwiftUI finger cue that renders a capacity-only count without selecting a finger, and an exact configuration view that highlights the ordered individual finger slots, including a lone pinky or a non-contiguous set. Keep hold name/kind text in the separate target label. Update combined accessibility labels to distinguish “up to N fingers” from named exact fingers.

- [ ] **Step 4: Wire every preview and workout layout.** Pass `step.fingerConfiguration` into portrait, landscape, plan preview, and both landscape hand cards. Add a DEBUG-only `HANGTEN_REVIEW_FINGERS` comma-separated parser using `FingerSlot.rawValue` so one-finger and arbitrary-set review routes can be exercised without changing production data.

- [ ] **Step 5: Add the custom routine control.** Keep the existing posture picker but add an exact-finger menu/toggle group with “Use hold capacity” plus index, middle, ring, and pinky toggles. Prevent an empty selection from becoming a `FingerConfiguration`; selecting the last active finger returns to nil. Rest-phase normalization clears this field as it already clears targets and posture.

- [ ] **Step 6: Run the focused test and commit the UI/data integration.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/CustomRoutineDraftTests
  rtk git add HangTen/Views/GripDiagramView.swift HangTen/Views/RootView.swift HangTen/Views/CustomRoutineEditorView.swift HangTen/Models/CustomRoutineDraft.swift HangTenTests/CustomRoutineDraftTests.swift
  rtk git commit -m "Render posture and finger cues independently"
  ```

## Final verification (controller session)

- [ ] Run the complete test target and exporter check:

  ```sh
  rtk scripts/export-plan-library.sh --check
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test
  ```

- [ ] Use the `validate-hang-ten-ios` skill. Read `docs/IOS_SIMULATOR_VALIDATION.md` and `docs/IOS_RUNTIME_SERVICES.md` first, create and register an exact workspace-owned simulator with cleanup traps, then inspect portrait and landscape capacity-only cues plus DEBUG exact configurations for `pinky` and `index,ring`. Confirm accessibility labels, mirrored hand cards, board highlights, countdown behavior, and cleanup of the owned simulator and exact `.context` artifacts.

- [ ] Run `rtk git diff origin/main... --check` and review the complete diff before reporting completion.
