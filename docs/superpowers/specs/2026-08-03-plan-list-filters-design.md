# Plans list filters design

## Problem

The Plans tab currently shows every routine compatible with the selected board, but users cannot narrow the list by the routine metadata already present in the bundled plan library. The list should support quick discovery without changing compatibility rules or adding a second source of truth for plan metadata.

## Goals

- Let users filter compatible plans by every structured discovery field already available in `PlanMetadata`:
  - difficulty (`level`)
  - source type (`provenance`, displayed as Official or Adapted)
  - category (`category`)
  - tags (`tags`)
  - equipment (`equipment`)
- Keep the interaction small and easy to understand on the existing Plans screen.
- Preserve board compatibility as the first filtering step.
- Make the filter matching rules independently unit-testable.
- Keep the bundled plan library as the source of truth for filter values.

## Non-goals

- Search, sorting, saved filter presets, or persisted filter state.
- Editing plan metadata or changing the bundled plan library.
- Changing which plans are compatible with a board.
- Adding new metadata solely to support this feature.

## User experience

The Plans header gains one `Filters` control. Tapping it opens a lightweight sheet containing selectable rows grouped into five sections: Difficulty, Type, Category, Tags, and Equipment.

Each section supports multiple selections. A section is omitted when there are no values available for the currently compatible plans. The sheet includes a `Clear` action when any filter is active and a `Done` action to dismiss it. The Plans screen shows the number of active filter groups on the control; no filter count is shown when all groups are empty.

The list updates from the selected filters when the sheet is dismissed. Filter state lives only in the Plans view for the current view lifetime; it is not persisted.

There are two distinct empty states:

1. If no plans are compatible with the selected board, keep the existing compatibility message.
2. If compatible plans exist but the selected filters exclude all of them, show a concise “No routines match these filters” message and a reset action that clears every filter.

The source/evidence card remains at the bottom of the Plans screen in both cases.

## Filtering semantics

Filtering starts with `AppStore.plans`, which already applies board compatibility. The filter model then applies the user selections:

- No selected values in a facet means that facet imposes no restriction.
- Multiple selected values within one facet use OR semantics. For example, selecting Intermediate and Advanced includes either difficulty.
- Selections across different facets use AND semantics. For example, Advanced plus Research includes only plans satisfying both conditions.
- Tags and equipment match when a plan contains at least one selected value.
- Values are compared by their stored raw values; display labels are formatting only.

The available values in the sheet are derived from all currently compatible plans, not from the already-filtered result. This keeps options stable while the user is making a combination of selections.

## Data flow and implementation boundary

The runtime `TrainingPlan` already carries difficulty and provenance. The remaining filter fields are retained in the validated `PlanLibraryDefinition` metadata. Add a small `PlanCatalog` lookup by plan ID so the Plans view can retrieve the original `PlanMetadata` without duplicating or inferring category, tags, or equipment from IDs.

Add a pure `PlanFilters` value type that stores the selected values for each facet and exposes matching behavior against a `TrainingPlan` plus its `PlanMetadata`. Add a small options helper (or equivalent view-local derivation) that produces sorted, unique values from the compatible plans. The UI should depend on these interfaces rather than on JSON details.

`PlansView` owns the transient filter state and derives `filteredPlans` from `store.plans`. A private sheet view renders the five sections and mutates the bound `PlanFilters`. Existing plan navigation and `PlanCard` rendering continue to receive the original `TrainingPlan` values.

If a metadata lookup unexpectedly fails, an unfiltered plan remains visible; a selected metadata facet simply cannot match that plan. The validated built-in library should make this path unreachable during normal operation.

## Testing and validation

Add unit tests for the pure filter model covering:

- no selections include every compatible plan;
- multiple values in one facet use OR semantics;
- selections across facets use AND semantics;
- category, tag, and equipment values come from plan metadata;
- a plan with no matching selected value is excluded.

Run the existing plan-library export check to confirm the bundled JSON is unchanged. Build and test the Hang Ten target, then launch the Plans review route in an isolated iOS Simulator and verify the filter sheet, active count, clear action, navigation links, and both empty states in portrait orientation.

## Files likely to change

- `HangTen/Models/PlanStorage.swift` — expose metadata lookup from the validated catalog.
- `HangTen/Models/PlanFilters.swift` — pure filter state, matching, and option derivation.
- `HangTen/Views/RootView.swift` — filter control, sheet, filtered list, and filter empty state.
- `HangTenTests/PlanFiltersTests.swift` — filter behavior tests.

No changes are expected in `PlanLibrary.json` or the plan definitions.
