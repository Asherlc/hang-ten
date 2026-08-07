# Custom Routines Design

**Date:** 2026-08-05

## Goal

Let athletes create routines from scratch or duplicate any built-in routine,
store them locally, edit/reorder/delete them, and run them through exactly the
same plan, board, timer, audio, activity-recording, favorites, filtering, and
session interfaces as built-in routines.

## Scope and decisions

- Custom routines are local-only in v1. No export, import, sync, or sharing.
- Users can create from scratch or duplicate a built-in or custom routine.
- Custom routines can be edited, reordered, and deleted. Built-in routines
  remain read-only.
- A routine has a required name, an optional description, optional difficulty,
  optional category, and optional comma-separated tags.
- Difficulty and category use the existing picker vocabularies. Tags are free
  text, normalized by trimming, removing empty entries, and de-duplicating.
- A routine has a fixed target mode chosen at creation:
  - A board-specific routine names a board and stores exact hold IDs.
  - A generic routine has no board ID and stores broad hold kinds or specific
    hold features. Compatibility is resolved against each board at runtime.
- The target mode cannot change after creation. A duplicate inherits its
  source mode; making a different mode is a new routine.
- A simple custom step contains a title, instruction, phase, duration, target
  selection, optional grip type, and a simple timing choice. Fixed and
  stopwatch timing are authorable; duplicated open/undefined source timing is
  preserved as a step-level timing value.
- Steps can be added, edited, deleted, and drag-reordered.
- Multi-part source steps are literalized before they become custom data.
  Repetition is represented by repeated step rows rather than a repeat count.
- Maximum-effort source steps retain stopwatch behavior. Their source duration
  remains the timer cap.

## Architecture

Built-in plans continue to come from the validated bundled plan library. A
separate `CustomRoutineStore` owns only user-created definitions and their
versioned local persistence. The custom store resolves definitions into the
existing `TrainingPlan` runtime model; it does not introduce a custom workout
view or a second activity-recording path.

`AppStore.plans` combines built-in and custom plans and applies the same board
compatibility check to both. Existing `board(for:)`, `holdIDs(for:on:)`,
favorites, filters, `PlanDetailView`, `WorkoutView`, session logging, HealthKit
recording, audio cues, and board highlighting remain shared interfaces.

The store exposes metadata for both sources through one app-store lookup used
by the Plans view. Built-in metadata continues to come from `PlanCatalog`;
custom metadata comes from the matching custom definition. This keeps the
existing `PlanFilters` contract while allowing custom difficulty, category,
and tags to participate in the same filters.

`RoutineProvenance` gains a `custom` case. A custom plan uses the source label
`Created in Hang Ten` and has no external source URL. The detail view renders a
local-origin card for custom plans and retains the linked source card for
built-in plans. The shared plan metadata source URL becomes optional; built-in
validation still requires an HTTP(S) URL, while custom plans intentionally
omit one.

## Persisted model

The custom store persists a versioned Codable collection, for example:

```swift
struct CustomRoutineDefinition: Codable, Hashable, Identifiable {
    let id: String
    var title: String
    var subtitle: String
    var difficulty: String?
    var category: String?
    var tags: [String]
    let targetMode: CustomRoutineTargetMode
    var steps: [WorkoutStepDefinition]
}

enum CustomRoutineTargetMode: Codable, Hashable {
    case boardSpecific(boardID: String)
    case generic
}
```

The exact storage wrapper carries a schema version and the definitions array.
Custom step definitions reuse the existing `WorkoutStepDefinition` target and
timing vocabulary. Board-specific steps use `.holdIDs`; generic steps use
`.kind` or `.feature`, preserving any existing feature fallback data when a
routine is duplicated.

The store provides CRUD operations with stable IDs for edits and new UUID-backed
IDs for duplicates. Each save encodes and replaces the complete collection in
one UserDefaults write. The AppStore receives the store through an injectable
protocol so unit tests can use isolated persistence.

## Literal-step normalization

All plan sources pass through one normalization boundary before becoming the
runtime plans consumed by `AppStore`. The existing `TrainingPlan` and
`WorkoutStep` contracts remain the shared runtime interfaces. After
normalization, every runtime step contains at most one timing segment.

The normalization rules are:

1. A fixed work segment becomes one work step with the segment's target,
   phase, grip, and duration.
2. A fixed rest segment becomes one rest step with no targets, rest phase, and
   the segment's duration.
3. Segments are expanded in their original order. A source step with multiple
   fixed segments therefore becomes multiple literal rows, and the total
   duration is unchanged.
4. A stopwatch work segment remains one stopwatch step. Its source step
   duration remains the cap used by the routine timeline; observed stopwatch
   time continues to be recorded through the existing stopwatch key path.
5. An open/undefined source segment remains one ordinary step-level timing
   value using the source step's scheduled duration. It is not turned into a
   multi-part editor construct.
6. A source step with no explicit segments uses the existing compatibility
   target behavior and becomes one literal step.
7. Repeated source work is expanded into repeated literal rows with stable,
   deterministic derived IDs. Step numbers are assigned after expansion.

The normalizer is used for built-in definitions and for duplicated routines.
Custom routines are persisted in the already-flat representation. This
removes the distinction between custom and built-in routines at runtime while
preserving fixed work/rest order, total duration, and stopwatch behavior.

## User flow

The Plans screen adds a `Create routine` action and a `My routines` section.
Custom cards navigate through the same detail view as built-in cards. The
detail view adds actions to start, edit, duplicate, and delete when the plan is
custom; built-in detail views expose duplicate but not edit/delete.

The editor flow is:

1. Choose `Board-specific` or `Generic` target mode.
2. For board-specific mode, choose a board. For generic mode, continue
   without a board assignment.
3. Enter routine metadata: name, description, optional difficulty, optional
   category, and tags.
4. Add or edit steps. Board-specific steps use a tappable board map to select
   exact holds. Generic steps choose one or more broad hold kinds or specific
   features from the existing vocabulary.
5. Reorder or delete steps.
6. Save after validation and return to the custom routine detail view.

Duplicating first literalizes the source plan, assigns a new custom ID, copies
metadata and target mode, and opens the editor. There is no advanced timing
indicator or separate segment editor. Stopwatch steps remain single simple
steps and retain their stopwatch timing.

## Validation and failure behavior

The custom validator rejects:

- a blank name;
- a routine with no steps;
- a non-finite or non-positive step duration;
- a non-rest step without at least one target;
- a rest step with any target;
- an unknown board ID;
- an unknown board-specific hold ID;
- a generic target that cannot resolve on any registered board; or
- an invalid timing/duration combination.

The target-mode choice is immutable after the definition is created. A
board-specific routine is compatible only with its assigned board. A generic
routine is compatible with any board for which every step target resolves,
using the same `BoardTargetResolver` behavior as built-in plans.

Invalid custom data never prevents built-in plans from loading. If the custom
collection cannot be decoded, the store loads an empty custom collection and
publishes a user-visible persistence warning. A failed save returns a
localized validation or encoding error to the editor without replacing the
last valid collection.

## Verification

Unit tests cover:

- fixed work/rest literal expansion, order, derived IDs, and duration totals;
- repeated source steps becoming literal rows;
- stopwatch preservation and observed duration recording;
- open/undefined step normalization;
- custom definition Codable round trips;
- custom store create, edit, duplicate, delete, atomic replacement, and
  corrupt-data recovery;
- board-specific and generic target compatibility;
- metadata normalization and shared plan filtering; and
- AppStore composition through the same `TrainingPlan` interfaces.

The iOS Simulator validation covers creating a board-specific routine,
creating a generic routine, duplicating a built-in routine, editing and
reordering steps, deleting a custom routine, switching boards to verify
generic compatibility, and starting a custom workout through the existing
timer and summary flow.
