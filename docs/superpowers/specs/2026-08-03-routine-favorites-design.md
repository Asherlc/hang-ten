# Routine favorites design

## Goal

Replace the Today tab's automatic "NEXT UP" routine with a user-controlled
favorites experience. People can favorite routines from Plans and see their
compatible favorites on Today.

## Approved behavior

- Favorites are identified by stable `TrainingPlan.id` values.
- Favorite IDs persist across app launches using `UserDefaults`.
- The favorites set is global rather than board-specific.
- Today shows only favorite routines compatible with the selected board.
- Changing boards hides incompatible favorites without deleting them; changing
  back makes them visible again when compatible.
- Favorite routines retain the existing `PlanCatalog` order.
- Toggling a favorite updates Plans and Today immediately.
- Removing the final compatible favorite leaves an empty-state card on Today.
- The existing automatic next-up selection no longer drives the Today UI.

## User experience

The Plans tab adds a star control beside each routine card. An unfavorited
routine uses `star`; a favorited routine uses `star.fill`. The star is a
separate control from the routine navigation target, so tapping it toggles the
favorite without opening plan details. Accessibility labels identify whether
the action will add or remove the named routine from favorites.

The Today tab removes the `NEXT UP` card and replaces it with a `FAVORITES`
section. Each compatible favorite uses the existing plan-card styling and
navigates to the existing plan detail screen. The section exposes the same star
toggle so a favorite can be removed without leaving Today.

When no compatible favorites exist, Today shows a concise empty-state card
explaining that routines can be favorited from Plans. No automatic fallback
routine is shown.

## State and data flow

`AppStore` owns the published favorite ID set and a `toggleFavorite(_:)`
operation. The store loads IDs from `UserDefaults` during initialization and
writes the updated set after every toggle. A default `UserDefaults` dependency
may be injected for isolated unit tests.

The derived Today collection is equivalent to:

```swift
plans.filter { favoritePlanIDs.contains($0.id) }
```

`plans` already filters `PlanCatalog.all` by selected-board compatibility, so
the favorites collection inherits exact hold resolution, fallback mappings,
and existing library ordering. Unknown IDs stored by an older or changed
library are ignored by the derived collection.

The bundled plan library and its metadata remain unchanged. The existing
featured-plan lookup is retained only as a deterministic helper for DEBUG
review routes (`HANGTEN_REVIEW_PLAN`, `HANGTEN_REVIEW_WORKOUT`, and
`HANGTEN_REVIEW_PLAN_ID`); it is removed from normal Today presentation.

## Testing and validation

Add focused unit coverage for favorite behavior using an isolated
`UserDefaults` suite:

- toggling an unfavorited plan adds its ID;
- toggling a favorited plan removes its ID;
- a new store instance reloads persisted IDs;
- derived favorites preserve plan-library order; and
- only favorites already present in the compatible `plans` collection are
  exposed to Today.

Build and inspect the installed app on a dedicated iOS Simulator. Verify:

- Today with no favorites;
- star controls and accessibility state on Plans;
- a favorited routine appearing on Today;
- removal from Today and Plans;
- persistence after relaunch; and
- incompatible favorites being hidden while retained in storage.

## Acceptance criteria

1. The Today tab contains no `NEXT UP` presentation or automatic featured
   routine card.
2. A person can favorite and unfavorite every routine from Plans.
3. Favorites survive app relaunches.
4. Today lists all and only compatible favorites, in library order.
5. Favorite toggles work from both Plans and Today without accidentally opening
   routine details.
6. The no-favorites state clearly explains how to add a favorite.
7. Existing plan detail, workout, board mapping, and DEBUG review routes still
   work.
8. Focused tests, the project build, and simulator checks pass.
