# Contact Requirement Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove overlapping fields from `ContactRequirement` and `PhysicalContact`, replacing `requiredFeatures`/`compatibleGripTypes`/`allMatching` with clean `shape`/`depth`/`selection` fields.

**Architecture:** Define new enums (`HoldShape`, `TargetDepth`, `HoldSize`), rewrite `ContactRequirement` to use them, remove `HoldFeature` entirely, update `ContactResolver` matching logic, migrate all JSON data, and update the custom routine editor UI.

**Tech Stack:** Swift, Codable, SwiftUI, JSON board packages

---

## File Structure

| File | Change |
|------|--------|
| `HangTen/Models/TrainingModels.swift` | Add `HoldShape`, `HoldSize`; remove `HoldFeature` enum (~100 lines); remove `features` from `PhysicalContact`; remove `matches(anyOf:)`; update `BundledPlanContactRequirements` |
| `HangTen/Models/PlanStorage.swift` | Add `TargetDepth`; rewrite `ContactRequirement` (remove `requiredFeatures`, `compatibleGripTypes`, `depthRangeMillimeters`; add `shape`, `depth`); remove `.feature()` factory; remove `allMatching` from `ContactSelectionPolicy`; update Codable |
| `HangTen/Models/WorkoutActivityRecording.swift` | Rewrite `ContactResolver.matches(_:contact:)` and `isDocumentedPair`; remove `.allMatching` case |
| `HangTen/Models/BoardPackageStore.swift` | Update `BoardPackageContactDocument` — remove `features`, add `shape` |
| `HangTen/Models/BoardPackageWriter.swift` | Update `BoardEditableContact` — remove `features`, add `shape`; remove feature validation |
| `HangTen/Views/CustomRoutineEditorView.swift` | Replace `GenericTargetChoice.feature(HoldFeature)` with shape-based picker |
| `HangTen/Resources/PlanLibrary.json` | Re-export after model changes |
| `Hangboards/*/board.json` | Migrate contacts: remove `features`, add `shape` where applicable |
| `Tools/HangboardWorkbench/src/types.ts` | Update `PhysicalContact` interface |
| `Tools/HangboardWorkbench/src/components/ContactInspector.tsx` | Replace features input with shape picker |
| 12 test files | Update fixtures and assertions |

---

## Task 1: Define new enums

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift` (after `HoldKind` enum, ~line 477)

- [ ] **Step 1: Add `HoldShape` enum**

```swift
enum HoldShape: String, Codable, Hashable, CaseIterable, Identifiable {
    case flat
    case round
    case incut
    case slot

    var id: String { rawValue }

    var label: String {
        switch self {
        case .flat: "Flat"
        case .round: "Round"
        case .incut: "Incut"
        case .slot: "Slot"
        }
    }
}
```

- [ ] **Step 2: Add `HoldSize` enum**

```swift
enum HoldSize: String, Codable, Hashable, CaseIterable, Identifiable {
    case tiny
    case small
    case medium
    case large

    var id: String { rawValue }

    var label: String {
        switch self {
        case .tiny: "Tiny"
        case .small: "Small"
        case .medium: "Medium"
        case .large: "Large"
        }
    }

    /// Community-convention depth range in millimeters for this size category.
    var depthRange: ClosedRange<Double> {
        switch self {
        case .tiny: 0...8
        case .small: 8...15
        case .medium: 15...25
        case .large: 25...50
        }
    }
}
```

- [ ] **Step 3: Add `TargetDepth` enum**

Add to `PlanStorage.swift` after `MillimeterRange` (after line 208):

```swift
enum TargetDepth: Codable, Hashable {
    case category(HoldSize)
    case range(MillimeterRange)

    /// True when this target depth overlaps with the given physical depth range.
    func overlaps(_ contactDepth: ClosedRange<Double>?) -> Bool {
        switch self {
        case let .category(size):
            guard let contactDepth else { return true }
            return size.depthRange.overlaps(contactDepth)
        case let .range(targetRange):
            guard let contactDepth else { return true }
            return targetRange.minimum <= contactDepth.upperBound
                && targetRange.maximum >= contactDepth.lowerBound
        }
    }
}
```

- [ ] **Step 4: Build to verify new types compile**

Run: `xcodebuild build -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -5`
Expected: BUILD SUCCEEDED

- [ ] **Step 5: Commit**

```bash
git add HangTen/Models/TrainingModels.swift HangTen/Models/PlanStorage.swift
git commit -m "feat: add HoldShape, HoldSize, TargetDepth enums"
```

---

## Task 2: Rewrite ContactRequirement and ContactSelectionPolicy

**Files:**
- Modify: `HangTen/Models/PlanStorage.swift:210-351`

- [ ] **Step 1: Remove `allMatching` from `ContactSelectionPolicy`**

Change the enum at line 210 to:

```swift
enum ContactSelectionPolicy: String, Codable, Hashable {
    case single
    case bilateralPair
}
```

- [ ] **Step 2: Rewrite `ContactRequirement` struct**

Replace lines 216-351 with:

```swift
struct ContactRequirement: Codable, Hashable {
    let kind: HoldKind?
    let shape: HoldShape?
    let depth: TargetDepth?
    let fingerCapacity: Int?
    let handCapacity: Int?
    let selection: ContactSelectionPolicy

    init(
        kind: HoldKind? = nil,
        shape: HoldShape? = nil,
        depth: TargetDepth? = nil,
        fingerCapacity: Int? = nil,
        handCapacity: Int? = nil,
        selection: ContactSelectionPolicy = .single
    ) {
        if let fingerCapacity {
            precondition(PhysicalContact.validFingerCapacityRange.contains(fingerCapacity))
        }
        if let handCapacity {
            precondition(PhysicalContact.validHandCapacityRange.contains(handCapacity))
        }
        self.kind = kind
        self.shape = shape
        self.depth = depth
        self.fingerCapacity = fingerCapacity
        self.handCapacity = handCapacity
        self.selection = selection
    }

    static func kind(
        _ kind: HoldKind,
        fingerCapacity: Int? = nil,
        selection: ContactSelectionPolicy = .single
    ) -> ContactRequirement {
        .init(kind: kind, fingerCapacity: fingerCapacity, selection: selection)
    }

    static func edge(
        depth: TargetDepth? = nil,
        selection: ContactSelectionPolicy = .single
    ) -> ContactRequirement {
        .init(kind: .edge, depth: depth, selection: selection)
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case kind, shape, depth, fingerCapacity, handCapacity, selection
    }

    init(from decoder: Decoder) throws {
        let rawContainer = try decoder.container(keyedBy: PlanLibraryCodingKey.self)
        let allowedKeys = Set(CodingKeys.allCases.map(\.rawValue))
        if let unknownKey = rawContainer.allKeys.first(where: { !allowedKeys.contains($0.stringValue) }) {
            throw DecodingError.dataCorruptedError(
                forKey: unknownKey,
                in: rawContainer,
                debugDescription: "Unsupported contact requirement field \(unknownKey.stringValue)."
            )
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        kind = try container.decodeIfPresent(HoldKind.self, forKey: .kind)
        shape = try container.decodeIfPresent(HoldShape.self, forKey: .shape)
        depth = try container.decodeIfPresent(TargetDepth.self, forKey: .depth)
        fingerCapacity = try container.decodeIfPresent(Int.self, forKey: .fingerCapacity)
        handCapacity = try container.decodeIfPresent(Int.self, forKey: .handCapacity)
        selection = try container.decode(ContactSelectionPolicy.self, forKey: .selection)

        if let fingerCapacity,
           !PhysicalContact.validFingerCapacityRange.contains(fingerCapacity) {
            throw DecodingError.dataCorruptedError(
                forKey: .fingerCapacity,
                in: container,
                debugDescription: "Contact requirement fingerCapacity must be in \(PhysicalContact.validFingerCapacityRange)."
            )
        }
        if let handCapacity,
           !PhysicalContact.validHandCapacityRange.contains(handCapacity) {
            throw DecodingError.dataCorruptedError(
                forKey: .handCapacity,
                in: container,
                debugDescription: "Contact requirement handCapacity must be in \(PhysicalContact.validHandCapacityRange)."
            )
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(kind, forKey: .kind)
        try container.encodeIfPresent(shape, forKey: .shape)
        try container.encodeIfPresent(depth, forKey: .depth)
        try container.encodeIfPresent(fingerCapacity, forKey: .fingerCapacity)
        try container.encodeIfPresent(handCapacity, forKey: .handCapacity)
        try container.encode(selection, forKey: .selection)
    }
}
```

- [ ] **Step 3: Build — expect compile errors from callers of removed fields**

Run: `xcodebuild build -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -20`
Expected: BUILD FAILED with errors referencing `requiredFeatures`, `compatibleGripTypes`, `allMatching`, `.feature(`, `depthRangeMillimeters` on ContactRequirement

- [ ] **Step 4: Commit**

```bash
git add HangTen/Models/PlanStorage.swift
git commit -m "feat: rewrite ContactRequirement with shape+depth, remove allMatching"
```

---

## Task 3: Update PhysicalContact

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:852-914`

- [ ] **Step 1: Remove `features` and `matches(anyOf:)` from `PhysicalContact`**

Remove the `features` property (line 857), the `features` init parameter (line 873), and the `self.features = features` assignment (line 898). Remove the `matches(anyOf:fingerCapacity:)` method (lines 907-914).

Add a `shape` property:

```swift
struct PhysicalContact: Identifiable, Hashable {
    let id: String
    let equipmentObjectID: String
    let name: String
    let kind: HoldKind
    let shape: HoldShape?
    let fingerCapacity: Int?
    let handCapacity: Int?
    let depthRangeMillimeters: ClosedRange<Double>?
    let gripTypes: Set<GripType>
    let side: ContactSide?
    let pairedContactID: String?

    static let validFingerCapacityRange = 1...4
    static let validHandCapacityRange = 1...2

    init(
        id: String,
        equipmentObjectID: String = "primary",
        name: String,
        kind: HoldKind,
        shape: HoldShape? = nil,
        fingerCapacity: Int? = nil,
        handCapacity: Int? = nil,
        depthRangeMillimeters: ClosedRange<Double>? = nil,
        gripTypes: Set<GripType> = [],
        side: ContactSide? = nil,
        pairedContactID: String? = nil
    ) {
        if let fingerCapacity {
            precondition(
                Self.validFingerCapacityRange.contains(fingerCapacity),
                "PhysicalContact fingerCapacity must be in \(Self.validFingerCapacityRange)."
            )
        }
        if let handCapacity {
            precondition(
                Self.validHandCapacityRange.contains(handCapacity),
                "PhysicalContact handCapacity must be in \(Self.validHandCapacityRange)."
            )
        }

        self.id = id
        self.equipmentObjectID = equipmentObjectID
        self.name = name
        self.kind = kind
        self.shape = shape
        self.fingerCapacity = fingerCapacity
        self.handCapacity = handCapacity
        self.depthRangeMillimeters = depthRangeMillimeters
        self.gripTypes = gripTypes
        self.side = side
        self.pairedContactID = pairedContactID
    }
```

Keep `resolvedFrame(in:)` unchanged.

- [ ] **Step 2: Build — expect errors from callers using `features` on PhysicalContact**

Run: `xcodebuild build -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -20`
Expected: BUILD FAILED — errors in BoardPackageStore, BoardPackageWriter, CustomRoutineEditorView, WorkoutActivityRecording

- [ ] **Step 3: Commit**

```bash
git add HangTen/Models/TrainingModels.swift
git commit -m "feat: replace features with shape on PhysicalContact"
```

---

## Task 4: Rewrite ContactResolver

**Files:**
- Modify: `HangTen/Models/WorkoutActivityRecording.swift:350-461`

- [ ] **Step 1: Rewrite `matches(_:contact:)`**

Replace the `matches` method (lines 406-428) with:

```swift
private static func matches(_ requirement: ContactRequirement, contact: PhysicalContact) -> Bool {
    if let kind = requirement.kind, contact.kind != kind { return false }
    if let shape = requirement.shape, contact.shape != shape { return false }
    if let depth = requirement.depth, !depth.overlaps(contact.depthRangeMillimeters) { return false }
    if let fingerCapacity = requirement.fingerCapacity,
       contact.fingerCapacity != fingerCapacity { return false }
    if let handCapacity = requirement.handCapacity,
       contact.handCapacity != handCapacity { return false }
    return true
}
```

- [ ] **Step 2: Remove `.allMatching` case from selection switch**

In the `resolve` method (line 364-378), change:

```swift
switch requirement.selection {
case .allMatching:
    guard !candidates.isEmpty else { throw ContactResolutionError.noMatches }
case .single:
    guard candidates.count == 1 else {
        throw ContactResolutionError.ambiguousSingle(candidateCount: candidates.count)
    }
case .bilateralPair:
    guard step.handUse == .double,
          step.side == .both,
          candidates.count == 2,
          isDocumentedPair(candidates[0], candidates[1]) else {
        throw ContactResolutionError.invalidBilateralPair(candidateCount: candidates.count)
    }
}
```

- [ ] **Step 3: Update `isDocumentedPair`**

Replace lines 447-460 with:

```swift
private static func isDocumentedPair(_ first: PhysicalContact, _ second: PhysicalContact) -> Bool {
    guard let pairedID = first.pairedContactID, pairedID == second.id else { return false }
    return first.kind == second.kind
        && first.shape == second.shape
        && first.depthRangeMillimeters == second.depthRangeMillimeters
}
```

- [ ] **Step 4: Build — expect errors from remaining callers of removed fields**

Run: `xcodebuild build -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -20`
Expected: BUILD FAILED — remaining errors in BoardPackageStore, BoardPackageWriter, CustomRoutineEditorView, BundledPlanContactRequirements, tests

- [ ] **Step 5: Commit**

```bash
git add HangTen/Models/WorkoutActivityRecording.swift
git commit -m "feat: rewrite ContactResolver matching for shape+depth"
```

---

## Task 5: Fix remaining compile errors in models

**Files:**
- Modify: `HangTen/Models/BoardPackageStore.swift` (~line 2713)
- Modify: `HangTen/Models/BoardPackageWriter.swift` (~line 391)
- Modify: `HangTen/Views/CustomRoutineEditorView.swift` (~lines 405-483)
- Modify: `HangTen/Models/TrainingModels.swift` (~lines 1759-1905, BundledPlanContactRequirements)

- [ ] **Step 1: Update `BoardPackageContactDocument` in BoardPackageStore.swift**

Remove the `features` field and its decode logic. Add optional `shape` field. The contact document should decode `shape` as `HoldShape?` and continue decoding `depthRangeMillimeters` as before.

- [ ] **Step 2: Update `BoardEditableContact` in BoardPackageWriter.swift**

Remove the `features` field. Add `shape: HoldShape?`. Update init, CodingKeys, decode, and the `serialize()` method. Remove the duplicate-feature validation.

- [ ] **Step 3: Update `CustomRoutineEditorView.swift`**

Replace `GenericTargetChoice.feature(HoldFeature)` with a shape-based choice. Update `genericTargetBinding` to read/write `shape` and `depth` instead of `requiredFeatures`. Update `toggleHold` to construct `ContactRequirement` with `shape` and `depth` from `PhysicalContact`.

The picker should present:
1. Kind picker (edge, sloper, pocket, etc.)
2. Shape picker (shown when kind supports shape — not for pocket/gaston)
3. Depth picker: size category (tiny/small/medium/large) or exact mm

- [ ] **Step 4: Update `BundledPlanContactRequirements` in TrainingModels.swift**

Replace all `.feature(.mediumEdge, ...)` calls with `.kind(.edge, depth: .category(.medium), ...)`. Replace `.feature(.roundSloper, ...)` with `.kind(.sloper, shape: .round, ...)`. Replace `.feature(.outerJug, ...)` with `.kind(.jug, ...)`. Replace `.feature(.flatSloper, ...)` with `.kind(.sloper, shape: .flat, ...)`. Replace all `selection: .allMatching` with `selection: .single`. Replace `depthRangeMillimeters:` with `depth: .range(...)`.

- [ ] **Step 5: Build — should compile (tests will fail)**

Run: `xcodebuild build -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -5`
Expected: BUILD SUCCEEDED

- [ ] **Step 6: Commit**

```bash
git add HangTen/Models/BoardPackageStore.swift HangTen/Models/BoardPackageWriter.swift HangTen/Views/CustomRoutineEditorView.swift HangTen/Models/TrainingModels.swift
git commit -m "feat: update board package and editor for normalized ContactRequirement"
```

---

## Task 6: Migrate JSON data

**Files:**
- Modify: `HangTen/Resources/PlanLibrary.json`
- Modify: All `Hangboards/*/board.json` files (contacts arrays)

- [ ] **Step 1: Re-export PlanLibrary.json**

Run the export script (or manually update): replace all `"requiredFeatures": ["mediumEdge"]` with `"shape": "edge", "depth": {"category": "medium"}` patterns. Replace `"requiredFeatures": ["roundSloper"]` with `"shape": "round"`. Replace `"requiredFeatures": ["flatSloper"]` with `"shape": "flat"`. Replace `"requiredFeatures": ["outerJug"]` with nothing (just kind: jug). Replace all `"selection": "allMatching"` with `"selection": "single"`. Remove all `"compatibleGripTypes"` arrays. Replace `"depthRangeMillimeters": {...}` with `"depth": {"range": {...}}`.

- [ ] **Step 2: Migrate board.json contacts**

For each board, in each contact object: remove `"features": [...]`, add `"shape": "flat"` or `"shape": "round"` or `"shape": "incut"` or `"shape": "slot"` where the old features indicated shape. Where features were empty `[]`, leave `shape` absent (nil).

- [ ] **Step 3: Verify JSON validity**

Run: `python3 -c "import json; [json.load(open(f)) for f in __import__('glob').glob('Hangboards/*/board.json')]; print('All board.json valid')"`
Run: `python3 -c "import json; json.load(open('HangTen/Resources/PlanLibrary.json')); print('PlanLibrary.json valid')"`

- [ ] **Step 4: Commit**

```bash
git add HangTen/Resources/PlanLibrary.json Hangboards/
git commit -m "feat: migrate JSON data to normalized schema"
```

---

## Task 7: Update tests

**Files:**
- Modify: `HangTenTests/PlanStorageTests.swift`
- Modify: `HangTenTests/WorkoutActivityRecordingTests.swift`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `HangTenTests/BoardTargetSubstitutionTests.swift`
- Modify: `HangTenTests/CustomRoutineStoreTests.swift`
- Modify: `HangTenTests/CustomRoutineDraftTests.swift`
- Modify: `HangTenTests/AppStoreTests.swift`
- Modify: `HangTenTests/WorkoutStepNormalizationTests.swift`
- Modify: `HangTenTests/CustomRoutineAppStoreTests.swift`

- [ ] **Step 1: Update PlanStorageTests.swift**

Replace all `requiredFeatures:` with `shape:`/`depth:`. Replace all `selection: .allMatching` with `selection: .single`. Replace `.feature(.mediumEdge)` with `.kind(.edge, depth: .category(.medium))`. Update inline JSON fixtures to use new field names.

- [ ] **Step 2: Update WorkoutActivityRecordingTests.swift**

Replace `requiredFeatures: [.roundSloper]` with `shape: .round`. Replace `selection: .allMatching` with `selection: .single`. Update JSON serialization test strings.

- [ ] **Step 3: Update remaining test files**

Apply same patterns: `requiredFeatures` → `shape`/`depth`, `allMatching` → `single`, `.feature(...)` → `.kind(...)` with appropriate shape/depth.

- [ ] **Step 4: Run tests**

Run: `xcodebuild test -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -20`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add HangTenTests/
git commit -m "feat: update tests for normalized ContactRequirement"
```

---

## Task 8: Update Workbench (TypeScript)

**Files:**
- Modify: `Tools/HangboardWorkbench/src/types.ts`
- Modify: `Tools/HangboardWorkbench/src/components/ContactInspector.tsx`
- Modify: `Tools/HangboardWorkbench/src/editor-model.ts`
- Modify: `Tools/HangboardWorkbench/src/workbench-controller.ts`
- Modify: `Tools/HangboardWorkbench/src/useContactEditor.ts`
- Modify: `Tools/HangboardWorkbench/tests/` (6 test files)

- [ ] **Step 1: Update `PhysicalContact` interface in types.ts**

Remove `features: string[]`. Add `shape?: string`. Keep `depthRangeMillimeters`.

- [ ] **Step 2: Update ContactInspector.tsx**

Replace the features text input with a shape dropdown (flat/round/incut/slot).

- [ ] **Step 3: Update editor-model.ts**

Remove `features` from the clone function. Add `shape`.

- [ ] **Step 4: Update workbench-controller.ts**

Remove `features` from required keys. Add `shape` as optional.

- [ ] **Step 5: Update useContactEditor.ts**

Remove feature prompt. Add shape prompt.

- [ ] **Step 6: Update test files**

Remove `features` from test fixtures. Add `shape` where needed.

- [ ] **Step 7: Run Workbench tests**

Run: `cd Tools/HangboardWorkbench && npm test`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add Tools/HangboardWorkbench/
git commit -m "feat: update Workbench for normalized contact schema"
```

---

## Task 9: Remove HoldFeature and clean up

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift` (remove HoldFeature enum, lines 623-721)
- Modify: `HangTen/Models/PlanStorage.swift` (remove `strippingUnsupportedCustomCueFields` if no longer needed)
- Modify: `docs/ADDING_A_ROUTINE.md`
- Modify: `.codex/skills/add-training-routine/SKILL.md`

- [ ] **Step 1: Remove `HoldFeature` enum from TrainingModels.swift**

Delete the entire `HoldFeature` enum (lines 623-721), including `FeatureGroup`, `Physicality`, `physicality`, `featureGroup`, and `holdKind` computed properties.

- [ ] **Step 2: Evaluate `strippingUnsupportedCustomCueFields()`**

This function strips `gripType` and `fingerConfiguration` from `WorkoutStepDefinition`. Those fields still exist on `WorkoutStepDefinition` (they're step-level coaching cues, not requirement fields). The function is still needed. Leave it unchanged.

- [ ] **Step 3: Update documentation**

Update `docs/ADDING_A_ROUTINE.md` to reference `shape` and `depth` instead of `requiredFeatures` and `HoldFeature`. Update `.codex/skills/add-training-routine/SKILL.md` similarly.

- [ ] **Step 4: Build and run all tests**

Run: `xcodebuild test -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -quiet 2>&1 | tail -10`
Expected: BUILD SUCCEEDED, all tests pass

- [ ] **Step 5: Commit**

```bash
git add HangTen/Models/TrainingModels.swift HangTen/Models/PlanStorage.swift docs/ADDING_A_ROUTINE.md .codex/skills/add-training-routine/SKILL.md
git commit -m "feat: remove HoldFeature enum and clean up"
```
