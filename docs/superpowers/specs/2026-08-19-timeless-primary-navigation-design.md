# Timeless Primary Navigation Design

## Goal

Replace Hang Ten's date- and progress-oriented top-level navigation with a
timeless structure centered on the three things users return to the app to do:
confirm their board, choose a training plan, and review previous sessions.

The primary tabs become **Train**, **Plans**, and **History**. Train remains the
default tab.

## Train

Train is a focused launchpad rather than a daily dashboard. It contains, in
order:

1. A full illustrated preview of the selected board.
2. The board name, dimensions, product link, and a clear **Change board** action.
3. The user's favorite plans, using the existing plan-card interactions.

The current marketing header, date-oriented tab label, and session-count card
are removed. When there are no favorites, Train shows a compact explanation
and a **Browse plans** action that switches to the Plans tab.

## Board selection

Train's **Change board** action and the current-board control in Plans open the
same full-page board picker. Each picker row or card shows the board's
illustration, name, and dimensions. The selected board is visibly checked.

Choosing a board:

1. updates `AppStore.selectedBoard`;
2. persists the board's stable ID;
3. returns to the screen that opened the picker; and
4. immediately refreshes board-specific plan availability, hold mappings, and
   previews throughout the app.

On launch, the app restores a saved board ID when it still exists in the board
catalog. A missing, invalid, or removed ID falls back to
`BoardCatalog.defaultBoard` without blocking launch.

## Plans

Plans remains the complete training library and retains its existing filters,
custom-routine creation, custom-plan grouping, favorite controls, plan details,
and workout launch flow.

A compact **Training on [board name]** control appears near the top of the
screen and opens the shared full-page board picker. Users can therefore change
boards while browsing plans without returning to Train.

## History

History replaces Progress and opens directly to the existing chronological
saved-session list, newest first. Each row shows the plan title, date and time,
and recorded sensor profile. Selecting a row opens the existing read-only
measured-load summary. When no saved sessions exist, the list presents a clear
empty state.

The progress ring, streak and motivation copy, duplicate board card, and
intermediate **Session history** card are removed. History continues to display
session-persistence errors inline when saved history cannot be read or written.

## Settings and integrations

A gear action on Train opens a secondary Settings screen. Settings contains:

- the current training-sensor connection card;
- navigation to the existing sensor configuration controls; and
- Apple Health authorization, sync status, errors, and available actions.

Moving these controls preserves every current integration while keeping them
out of the primary History experience. History still refreshes authorization
and history state as needed, but does not present progress or sync status as its
main content.

## View and state boundaries

- `RootView` uses a named tab-selection type for Train, Plans, and History rather
  than integer tags. This state also lets Train's empty-favorites action switch
  directly to Plans.
- `HomeView` becomes `TrainView` and owns only the board preview, board-picker
  navigation, favorites, and empty-favorites action.
- A shared board-picker view is reachable from Train and Plans.
- `PlansView` keeps the library behavior and adds the compact current-board
  control.
- The root History screen reuses the existing session-list and session-summary
  presentation instead of wrapping the list in another navigation step.
- A secondary Settings view composes the existing sensor and Apple Health
  controls extracted from the old progress dashboard.
- `AppStore` owns selected-board persistence and safe catalog fallback so every
  view observes one board source of truth.

No training-plan content, workout timing, hold-target resolution, session
record format, HealthKit record policy, or sensor protocol changes are in scope.

## Errors and empty states

- An invalid persisted board ID falls back to the default board.
- An empty board-compatible plan set continues to use the existing Plans empty
  state.
- No favorites produces a compact Train empty state with **Browse plans**.
- No saved sessions produces the existing History empty state.
- Session persistence, Apple Health, Bluetooth, and sensor errors remain visible
  beside the controls or content they affect.

## Telemetry

The existing `app tab selected` event keeps its name, but its tab values become
`train`, `plans`, and `history`. Existing board-selection and plan interaction
events retain their current behavior.

## Validation

Implementation follows test-driven development for state behavior and then
validates the assembled UI:

- add tests that a selected board ID persists and restores;
- add a fallback test for an unknown persisted board ID;
- retain and run existing favorite-plan, plan-filtering, session-history,
  HealthKit, sensor, and telemetry tests;
- build the iOS app and run the relevant test suite; and
- validate Train, the board picker, Plans, History, Settings, and representative
  empty states on an isolated iOS Simulator with screenshots.

