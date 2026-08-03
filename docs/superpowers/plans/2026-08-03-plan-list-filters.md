# Plans List Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add compact inline multi-select dropdown filters to the Plans tab for difficulty, source type, category, tags, and equipment while preserving board compatibility filtering.

**Architecture:** Keep `AppStore.plans` as the first-stage board-compatible collection. Expose validated `PlanMetadata` by plan ID through `PlanCatalog`, then apply a pure `PlanFilters` value type to that metadata. `PlansView` owns transient filter state, renders a horizontal row of native menus, and renders either the filtered cards or a filter-specific empty state.

**Tech Stack:** Swift 6-compatible SwiftUI, Foundation, XCTest, Xcode 16 project format, iOS deployment target 17.0.

## Global Constraints

- Filter every existing structured discovery field: difficulty (`level`), source type (`provenance`), category (`category`), tags (`tags`), and equipment (`equipment`).
- Board compatibility remains the first filtering step.
- Multiple selected values within one facet use OR semantics; selections across facets use AND semantics.
- Do not add search, sorting, saved presets, persistence, new metadata, or changes to `PlanLibrary.json`.
- Keep filter state transient to the Plans view lifetime.
- Preserve the existing source/evidence card and plan navigation behavior.
- Use test-first development: run the new filter tests while they fail before adding the production filter implementation.
- Add new Swift files to the manually maintained `HangTen.xcodeproj/project.pbxproj` source groups and source build phases.

---

## File map

- `HangTen/Models/PlanStorage.swift` — add the catalog metadata lookup by plan ID; the validated library remains the metadata source of truth.
- `HangTen/Models/PlanFilters.swift` — new pure filter state, matching semantics, and available-value derivation.
- `HangTen/Views/RootView.swift` — add inline Plans filter menus, the filtered collection, and filter-specific empty state.
- `HangTenTests/PlanFiltersTests.swift` — new unit tests for matching, facet semantics, options, and clear behavior.
- `HangTen.xcodeproj/project.pbxproj` — register the new model source and test source with the existing targets.

## Task 1: Add tested plan metadata lookup and pure filter model

**Files:**
- Create: `HangTen/Models/PlanFilters.swift`
- Create: `HangTenTests/PlanFiltersTests.swift`
- Modify: `HangTen/Models/PlanStorage.swift:1131-1148`
- Modify: `HangTen.xcodeproj/project.pbxproj` in the PBXBuildFile, PBXFileReference, Models group, HangTenTests group, and both PBXSourcesBuildPhase sections.

**Interfaces:**
- Produces `PlanCatalog.metadata(for id: String) -> PlanMetadata?`.
- Produces `PlanFilters` with `levels`, `provenances`, `categories`, `tags`, and `equipment` sets; `isEmpty`, `activeFacetCount`, `matches(_:)`, `clear()`, and one toggle method per facet.
- Produces `PlanFilterOptions(metadata: [PlanMetadata])` with sorted unique `levels`, `provenances`, `categories`, `tags`, and `equipment` arrays.
- `PlanFilters.matches(_ metadata:)` returns true when every active facet matches. A facet with no selections matches all metadata; a facet with multiple selections matches when at least one selected value is present.

- [x] **Step 1: Register the new test file in the Xcode project and write the failing tests.**

Add `PlanFiltersTests.swift` to the HangTenTests group and test source phase using build-file ID `AA0000000000000000000020` and file-reference ID `BB0000000000000000000023`. Add these behavior tests before adding `PlanFilters.swift` to the app target:

```swift
import Foundation
import XCTest
@testable import HangTen

final class PlanFiltersTests: XCTestCase {
    private func metadata(
        level: String = "Intermediate",
        provenance: RoutineProvenance = .official,
        category: String = "manufacturer",
        tags: [String] = ["built-in", "manufacturer"],
        equipment: [String] = ["hangboard"]
    ) -> PlanMetadata {
        PlanMetadata(
            title: "Test plan",
            subtitle: "Test subtitle",
            level: level,
            sourceLabel: "Test source",
            sourceURL: URL(string: "https://example.com/source")!,
            provenance: provenance,
            category: category,
            tags: tags,
            equipment: equipment
        )
    }

    func testEmptyFiltersMatchEveryMetadata() {
        let filters = PlanFilters()

        XCTAssertTrue(filters.matches(metadata(level: "Entry")))
        XCTAssertTrue(filters.matches(metadata(level: "Expert", provenance: .adapted)))
    }

    func testMultipleValuesWithinDifficultyUseOrSemantics() {
        var filters = PlanFilters()
        filters.levels = ["Intermediate", "Advanced"]

        XCTAssertTrue(filters.matches(metadata(level: "Intermediate")))
        XCTAssertTrue(filters.matches(metadata(level: "Advanced")))
        XCTAssertFalse(filters.matches(metadata(level: "Entry")))
    }

    func testSelectionsAcrossFacetsUseAndSemantics() {
        var filters = PlanFilters()
        filters.levels = ["Advanced"]
        filters.categories = ["research"]

        XCTAssertTrue(filters.matches(metadata(level: "Advanced", category: "research")))
        XCTAssertFalse(filters.matches(metadata(level: "Advanced", category: "coach")))
        XCTAssertFalse(filters.matches(metadata(level: "Intermediate", category: "research")))
    }

    func testTagsAndEquipmentMatchAnySelectedValue() {
        var filters = PlanFilters()
        filters.tags = ["endurance", "strength"]
        filters.equipment = ["hangboard", "weights"]

        XCTAssertTrue(filters.matches(metadata(tags: ["built-in", "strength"], equipment: ["hangboard"])))
        XCTAssertTrue(filters.matches(metadata(tags: ["endurance"], equipment: ["weights"])))
        XCTAssertFalse(filters.matches(metadata(tags: ["mobility"], equipment: ["hangboard"])))
    }

    func testFilterOptionsAreUniqueAndSorted() {
        let options = PlanFilterOptions(metadata: [
            metadata(level: "Advanced", provenance: .adapted, category: "research", tags: ["strength", "shared"], equipment: ["hangboard"]),
            metadata(level: "Entry", provenance: .official, category: "manufacturer", tags: ["shared", "built-in"], equipment: ["weights"]),
            metadata(level: "Advanced", provenance: .adapted, category: "research", tags: ["strength"], equipment: ["hangboard"])
        ])

        XCTAssertEqual(options.levels, ["Advanced", "Entry"])
        XCTAssertEqual(Set(options.provenances), Set([.official, .adapted]))
        XCTAssertEqual(options.categories, ["manufacturer", "research"])
        XCTAssertEqual(options.tags, ["built-in", "shared", "strength"])
        XCTAssertEqual(options.equipment, ["hangboard", "weights"])
    }

    func testClearRemovesSelectionsAndActiveFacetCount() {
        var filters = PlanFilters()
        filters.levels = ["Advanced"]
        filters.tags = ["strength"]

        XCTAssertEqual(filters.activeFacetCount, 2)

        filters.clear()

        XCTAssertTrue(filters.isEmpty)
        XCTAssertEqual(filters.activeFacetCount, 0)
    }

    func testCatalogMetadataPreservesBundledFilterFields() {
        let metadata = PlanCatalog.metadata(for: "research.max-hangs")

        XCTAssertEqual(metadata?.level, "Advanced")
        XCTAssertEqual(metadata?.provenance, .adapted)
        XCTAssertEqual(metadata?.category, "research")
        XCTAssertEqual(metadata?.tags, ["built-in", "research"])
        XCTAssertEqual(metadata?.equipment, ["hangboard"])
    }
}
```

- [ ] **Step 2: Run the focused test target and verify the failure is caused by the missing filter model.**

Run:

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,OS=26.5,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/PlanFiltersTests test
```

Expected: compilation fails because `PlanFilters`, `PlanFilterOptions`, and `PlanCatalog.metadata(for:)` do not exist yet. Do not change the test assertions to make this failure disappear.

- [x] **Step 3: Add the minimal production implementation.**

Create `PlanFilters.swift` with this shape:

```swift
import Foundation

struct PlanFilters: Equatable {
    var levels: Set<String> = []
    var provenances: Set<RoutineProvenance> = []
    var categories: Set<String> = []
    var tags: Set<String> = []
    var equipment: Set<String> = []

    var isEmpty: Bool { activeFacetCount == 0 }

    var activeFacetCount: Int {
        [levels.isEmpty, provenances.isEmpty, categories.isEmpty, tags.isEmpty, equipment.isEmpty]
            .filter { !$0 }
            .count
    }

    func matches(_ metadata: PlanMetadata) -> Bool {
        (levels.isEmpty || levels.contains(metadata.level)) &&
        (provenances.isEmpty || provenances.contains(metadata.provenance)) &&
        (categories.isEmpty || categories.contains(metadata.category)) &&
        (tags.isEmpty || !tags.isDisjoint(with: metadata.tags)) &&
        (equipment.isEmpty || !equipment.isDisjoint(with: metadata.equipment))
    }

    mutating func clear() {
        levels.removeAll()
        provenances.removeAll()
        categories.removeAll()
        tags.removeAll()
        equipment.removeAll()
    }

    mutating func toggle(level: String) { toggle(level, in: &levels) }
    mutating func toggle(provenance: RoutineProvenance) { toggle(provenance, in: &provenances) }
    mutating func toggle(category: String) { toggle(category, in: &categories) }
    mutating func toggle(tag: String) { toggle(tag, in: &tags) }
    mutating func toggle(equipment value: String) { toggle(value, in: &equipment) }

    private mutating func toggle<Value: Hashable>(_ value: Value, in values: inout Set<Value>) {
        if !values.insert(value).inserted {
            values.remove(value)
        }
    }
}

struct PlanFilterOptions: Hashable {
    let levels: [String]
    let provenances: [RoutineProvenance]
    let categories: [String]
    let tags: [String]
    let equipment: [String]

    init(metadata: [PlanMetadata]) {
        levels = Self.sortedUnique(metadata.map(\.level))
        provenances = Array(Set(metadata.map(\.provenance))).sorted { $0.label < $1.label }
        categories = Self.sortedUnique(metadata.map(\.category))
        tags = Self.sortedUnique(metadata.flatMap(\.tags))
        equipment = Self.sortedUnique(metadata.flatMap(\.equipment))
    }

    private static func sortedUnique(_ values: [String]) -> [String] {
        Array(Set(values)).sorted {
            $0.localizedCaseInsensitiveCompare($1) == .orderedAscending
        }
    }
}
```

Add `PlanCatalog.metadata(for:)` beside the existing `plan(id:)` helper:

```swift
static func metadata(for id: String) -> PlanMetadata? {
    store.definition.plans.first { $0.id == id }?.metadata
}
```

Register `PlanFilters.swift` in the app target using build-file ID `AA0000000000000000000019` and file-reference ID `BB0000000000000000000022`, and place it in the Models group and HangTen source phase.

- [ ] **Step 4: Run the focused tests and verify they pass.**

Run:

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,OS=26.5,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/PlanFiltersTests test
```

Expected: all seven `PlanFiltersTests` pass with zero failures.

- [ ] **Step 5: Run the full unit-test target.**

Run:

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,OS=26.5,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test
```

Expected: the existing workout timeline tests and all plan filter tests pass.

- [ ] **Step 6: Commit the model task.**

Run:

```bash
rtk git add HangTen/Models/PlanFilters.swift HangTen/Models/PlanStorage.swift HangTenTests/PlanFiltersTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "Add plan metadata filters"
```

## Task 2: Integrate inline quick dropdowns into the Plans screen

**Files:**
- Modify: `HangTen/Views/RootView.swift` in `PlansView`; remove the private sheet-only view.

**Interfaces:**
- Consumes `PlanFilters`, `PlanFilterOptions`, and `PlanCatalog.metadata(for:)` from Task 1.
- Produces a transient `@State` filter interaction with inline native menus and existing plan navigation unchanged.

- [x] **Step 1: Retain transient state and derived collections in `PlansView`.**

Keep `filters`, `compatiblePlans`, `availableMetadata`, `filterOptions`, and `filteredPlans` as the existing data layer. Do not change the model or its tests.

- [x] **Step 2: Add the inline quick-dropdown bar.**

Place a horizontally scrolling row of native SwiftUI `Menu` controls immediately below the Plans explanatory text. Render a menu only when its options are available. The five facets are Difficulty, Type, Category, Tags, and Equipment; every menu starts with `All`, which clears that facet, followed by every raw option. Selecting an option toggles it and selected options use a checkmark.

Each menu has a meaningful accessibility label such as `Filter by difficulty`. Labels show the facet name with no selection, the single selected display label with one selection, and `N selected` with multiple selections. Use `RoutineProvenance.label` for Type and the existing hyphen-to-space, capitalized display convention for category, tags, and equipment. Tint and outline active menu pills, and render a `Clear` button whenever any facet is active. Keep the existing navigation stack, hidden navigation bar, background, padding, and source card styling intact.

- [x] **Step 3: Preserve compatible, filtered, and empty states.**

Keep the compatible-plans branch first, then `NoMatchingPlansCard` when selected filters produce no results, then the existing plan cards and navigation links. The filter empty state must display `No routines match these filters` and retain its `Clear filters` recovery. Keep `sourceCard` after this branch in all cases.

- [x] **Step 4: Remove obsolete sheet-only UI.**

Delete `showsFilters`, the `.sheet` presentation, and `PlanFiltersSheet`. The menus may dismiss after each choice; users reopen a menu to make another selection.

- [ ] **Step 5: Build and run the full test target after the UI change.**

Run:

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,OS=26.5,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test
```

Expected: the app target compiles and all unit tests pass with zero failures.

- [x] **Step 6: Run the plan-library export check.**

Run:

```bash
rtk scripts/export-plan-library.sh --check
```

Expected: the check exits successfully and reports that `HangTen/Resources/PlanLibrary.json` is current. Do not regenerate or edit the JSON for this UI-only feature.

- [ ] **Step 7: Commit the Plans UI task.**

Run:

```bash
rtk git add HangTen/Views/RootView.swift docs/superpowers/specs/2026-08-03-plan-list-filters-design.md docs/superpowers/plans/2026-08-03-plan-list-filters.md
rtk git commit -m "Use inline plan filter menus"
```

## Final validation

- [ ] Create a dedicated simulator owned by the current Conductor workspace on
  the available iOS 26.5 runtime, assign its returned identifier to
  `review_device_uuid`, record it before boot/build, and use that exact UUID for
  every validation command.
- [ ] Build with a workspace-specific derived-data directory:

```bash
set -euo pipefail

workspace_path="$PWD"
workspace_name="$CONDUCTOR_WORKSPACE_NAME"
test -n "$workspace_name"
mkdir -p "$workspace_path/.context"
simulator_name="Hang Ten Conductor $workspace_name Plans Filters Review"

cleanup() {
  CONDUCTOR_WORKSPACE_PATH="$workspace_path" \
  CONDUCTOR_WORKSPACE_NAME="$workspace_name" \
  "$workspace_path/scripts/conductor-resource-cleanup.sh" archive
}
signal_exit() {
  trap - INT TERM
  exit "$1"
}
trap cleanup EXIT
trap 'signal_exit 130' INT
trap 'signal_exit 143' TERM

simulator_uuid="$(rtk xcrun simctl create "$simulator_name" 'com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro' 'com.apple.CoreSimulator.SimRuntime.iOS-26-5')"
if ! printf '%s\n' "$simulator_uuid" >> "$workspace_path/.context/conductor-owned-simulators"; then
  xcrun simctl delete "$simulator_uuid" || true
  exit 1
fi
review_device_uuid="$simulator_uuid"

rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination "platform=iOS Simulator,id=${review_device_uuid}" -derivedDataPath .context/DerivedData build
```

- [ ] Boot the dedicated device, wait for readiness, install the resulting app, and launch it through the Plans review route:

```bash
rtk xcrun simctl boot "${review_device_uuid}"
rtk xcrun simctl bootstatus "${review_device_uuid}" -b
rtk xcrun simctl install "${review_device_uuid}" .context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app
SIMCTL_CHILD_HANGTEN_REVIEW_PLANS=1 rtk xcrun simctl launch "${review_device_uuid}" com.hangten.training
```

- [ ] Confirm the inline quick-dropdown bar exposes every available facet, supports multiple selections across repeated menu opens, shows selected-value labels and checkmarks, clears either a single facet with `All` or every facet with `Clear`, and preserves plan-card navigation.
- [ ] Confirm selecting an impossible combination shows `No routines match these filters`, and clearing filters restores the compatible plan cards.
- [ ] Confirm a board with no compatible plans still shows the original compatibility empty state.
- [ ] Delete the dedicated review-device UUID after validation through the
  ownership-aware archive cleanup command:

```bash
CONDUCTOR_WORKSPACE_PATH="$workspace_path" \
CONDUCTOR_WORKSPACE_NAME="$workspace_name" \
"$workspace_path/scripts/conductor-resource-cleanup.sh" archive
```
