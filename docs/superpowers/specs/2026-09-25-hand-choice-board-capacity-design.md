# Hand choice by board capacity

## Problem

Starting a routine that needs a hand choice presents a blocking modal. Its
"Both hands" option is hard-coded as **two boards**, even though most boards fit
both hands on one board. The choice is not derived from the selected board's
hand capacity, and the modal interrupts the workout page.

Two built-in routines (`research.max-hangs`, `research.abrahangs`) are modeled
as `handUse: .either` with a note in the source audit that Hang Ten "lets the
athlete select one hand." The product owner has confirmed both are two-handed
prescriptions, not one-hand-at-a-time.

## Decisions

- The hand choice becomes an inline menu on the workout page, replacing the
  modal sheet.
- Default preference comes from the selected board's capacity: `handCapacity`
  2 → **Both hands**; `handCapacity` 1 → **Alternate hands**.
- On a capacity-2 board, a both-hands target resolves to the board's paired
  left/right holds on the one board. On a capacity-1 board it stays one hold per
  board (two boards).
- `research.max-hangs` and `research.abrahangs` are recoded to `handUse:
  .double` with `.bilateralPair` targets. The routine guide rule that
  `.bilateralPair` requires a source-prescribed pair is amended to cover a
  two-handed source, and the plan-cue source audit is corrected.

## Goals

1. Never tell an athlete to use two boards when the selected board fits both
   hands.
2. Default the hand choice from the board, not from a hard-coded option.
3. Keep workout start unblocked.
4. Encode the two-handed Lattice routines faithfully.

## Non-goals

- Changing how authored `.double` catalog steps other than the two recoded plans
  highlight (they keep their existing `.single` representative-hold behavior).
- Any change to hand semantics for fixed `.single` left/right steps.

## Design

### 1. Default preference (testable policy)

Add a pure policy, e.g. on `WorkoutSessionHandPreference`:

```swift
static func defaultPreference(boardHandCapacity: Int) -> WorkoutSessionHandPreference {
    boardHandCapacity <= 1 ? .alternate : .both
}
```

`RootView` applies it once when `planNeedsHandChoice` is true and no preference
has been set, materializes `sessionSteps`, and starts without the modal. When
`planNeedsHandChoice` is false the menu is hidden and `handPreference` stays nil,
exactly as today.

### 2. Capacity-aware both-hands materialization

- Add `ContactRequirement.bilateralSelection`: upgrades `.single` to
  `.bilateralPair`; no-op when already `.bilateralPair` or when an exact
  `contactID` pins the requirement (an exact hold cannot pair).
- `WorkoutSessionHandResolver.materializeBoth` becomes capacity-aware:
  - `boardIsOneHanded == false` (capacity 2): requirements →
    `.bilateralSelection`; step stays `handUse: .double`, `side: .both`.
  - `boardIsOneHanded == true` (capacity 1): unchanged — requirements →
    `.singleHandSelection`; one hold per board.

This makes an either-hand step selected as "Both hands" on a capacity-2 board
highlight the paired left/right holds on that one board.

### 3. Inline hand menu

Replace the `.sheet(isPresented: $showsHandSidePicker)` block in `RootView` with
a `Menu` beside the existing "Routine" button in `sessionHeader`:

- Options: Left hand, Right hand, Alternate hands, Both hands. The Both option
  is titled "Both hands" on capacity 2 and "Both hands (two boards)" on
  capacity 1.
- Explanatory copy mirrors the title ("Both hands means simultaneous on this
  board." vs "…on two boards.").
- The menu reflects the current preference and is enabled only before the first
  start; once running it stays visible but disabled.
- Shown only when `planNeedsHandChoice`.
- Keeps the `handSide.left/right/alternate/both` accessibility identifiers on
  items and adds `workout.handPicker` to the menu control.

Changing the choice rebuilds `sessionSteps` and reinitializes stopwatches; the
before-first-start gate prevents re-timing a live session.

### 4. Recoded Lattice plans

In `LegacyPlanSeedCatalog` (`TrainingModels.swift`):

- `research.max-hangs`: five steps change `handUse: .either` → `.double`.
- `research.abrahangs`: six steps change `handUse: .either` → `.double`.
- Their targets change to `.bilateralPair` (the 20 mm edge and the finger-
  capacity edge requirements).
- Regenerate `HangTen/Resources/PlanLibrary.json` and pass
  `scripts/export-plan-library.sh --check`.

Because the two-handed requirement is now on the steps themselves, these plans
no longer raise the hand question on a capacity-2 board; a capacity-1 board
still forces the choice (default Alternate).

### 5. Compatibility and recording

`AppStore.isIncompatible` / `handResolutionCandidates`,
`CustomRoutineBoardPreview`, and `WorkoutActivityRecorder` keep their shapes and
consume the capacity-aware materialization. Compatibility remains covered by
left/right resolvability for steps that need a hand choice.

## Testing

- Unit tests for `defaultPreference` (capacity 1 and 2).
- Unit tests for `ContactRequirement.bilateralSelection` (upgrade, no-op on
  pair, no-op with exact contact).
- Update `WorkoutTimelineTests.testSessionStepsBothKeepsDoubleBothWithSingleHandSelection`
  to assert capacity-2 → `.bilateralPair` and add a capacity-1 `.single` case.
- Board-resolution test that the recoded plans resolve their `.bilateralPair`
  targets on at least one registered board (per `docs/ADDING_A_ROUTINE.md`), and
  that they are hidden only where no pair exists.
- Update `GripCueSnapshotUITests` and any UI flow that tapped `handSide.left`
  for `research.max-hangs`: on a capacity-2 board the menu no longer appears, so
  the test starts directly; add a one-handed-board case that opens the menu.
- Run the unit/UI suites and the hangboard/plan-library validation scripts.

## Documentation

- Amend `docs/ADDING_A_ROUTINE.md:120` so `.bilateralPair` is allowed when the
  source prescribes both hands together, not only when it names a pair.
- Correct `docs/source-audits/2026-08-10-plan-cue-provenance.md:43-44` to record
  that both Lattice routines are two-handed and no longer present a one-hand
  selection.

## Risks

- `.bilateralPair` targets can hide a recoded plan on a board without a
  symmetric matching pair. This is accepted per the routine guide (a
  board-flexible plan is hidden when a target cannot resolve) and is verified by
  the board-resolution test.
- Defaulting capacity-2 either-hand steps to both hands is only reached by
  custom routines now that the two built-in either-hand plans are recoded.
