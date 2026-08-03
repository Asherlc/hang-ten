# Routine Favorites Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Today tab's automatic next-up routine with persistent, board-compatible routine favorites.

**Architecture:** `AppStore` owns a published set of stable plan IDs, persists it through an injected `UserDefaults`, and derives `favoritePlans` by filtering the existing compatible `plans` collection. SwiftUI will share one reusable favorite-aware routine card between Plans and Today, while the existing featured-plan lookup remains only for DEBUG review navigation. Unit tests cover persistence and derived ordering; an isolated simulator review covers the visible flow.

**Tech Stack:** Swift 5, SwiftUI, `UserDefaults`, XCTest, Xcode project build settings, `xcodebuild`, `simctl`.

## Global Constraints

- Favorites are identified by stable `TrainingPlan.id` values.
- Favorite IDs persist across app launches using `UserDefaults`.
- The favorites set is global rather than board-specific.
- Today shows only favorite routines compatible with the selected board.
- Changing boards hides incompatible favorites without deleting them.
- Favorite routines retain the existing `PlanCatalog` order.
- The Today tab contains no `NEXT UP` presentation or automatic featured routine card.
- Existing plan detail, workout, board mapping, and DEBUG review routes must continue to work.
- Do not change the bundled plan library or its metadata.
- Follow the repository's `rtk` command prefix for shell commands.

---

## File map

- Modify `HangTen/Models/AppStore.swift` — own, load, persist, toggle, and derive favorites.
- Create `HangTenTests/AppStoreFavoritesTests.swift` — test persistence, toggling, filtering, and order.
- Modify `HangTen.xcodeproj/project.pbxproj` — register the new test source file in the existing unit-test target.
- Modify `HangTen/Views/RootView.swift` — replace Today's featured card, add star controls, and preserve DEBUG review navigation.
- Do not modify `HangTen/Resources/PlanLibrary.json` — favorites are user state, not library data.

## Interfaces between tasks

Task 1 produces these `AppStore` interfaces for Task 2:

```swift
@Published private(set) var favoritePlanIDs: Set<String>
var favoritePlans: [TrainingPlan] { get }
func isFavorite(_ plan: TrainingPlan) -> Bool
func toggleFavorite(_ plan: TrainingPlan)
init(healthKitService: HealthKitService = HealthKitService(), userDefaults: UserDefaults = .standard)
```

`favoritePlans` must preserve `plans` order and therefore must be derived by
filtering `plans`, not by iterating the persisted set.

### Task 1: Add persistent favorites state and tests

**Files:**
- Create: `HangTenTests/AppStoreFavoritesTests.swift`
- Modify: `HangTen/Models/AppStore.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:**
- Consumes: existing `AppStore.plans`, `TrainingPlan.id`, and `UserDefaults`.
- Produces: the four favorite APIs listed above for the SwiftUI task.

- [ ] **Step 1: Register the new test file without changing production code.**

Add a `PBXFileReference`, `PBXBuildFile`, `HangTenTests` group child, and
unit-test `PBXSourcesBuildPhase` entry for `AppStoreFavoritesTests.swift`.
Keep the existing test target settings and source registration intact.

- [ ] **Step 2: Write the failing persistence and filtering tests.**

Use an isolated suite per test so the app's standard defaults never receive
test data. The test file should exercise real `AppStore` behavior:

```swift
import XCTest
@testable import HangTen

final class AppStoreFavoritesTests: XCTestCase {
    func testTogglePersistsAcrossStoreInstancesAndCanRemoveFavorite() {
        let defaults = UserDefaults(suiteName: "AppStoreFavoritesTests.toggle")!
        defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.toggle")
        defer { defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.toggle") }

        let plan = PlanCatalog.all[0]
        let store = AppStore(userDefaults: defaults)

        XCTAssertFalse(store.isFavorite(plan))
        store.toggleFavorite(plan)
        XCTAssertTrue(store.isFavorite(plan))

        let reloadedStore = AppStore(userDefaults: defaults)
        XCTAssertTrue(reloadedStore.isFavorite(plan))

        reloadedStore.toggleFavorite(plan)
        XCTAssertFalse(reloadedStore.isFavorite(plan))
    }

    func testFavoritePlansUseCompatiblePlanOrderAndIgnoreUnknownIDs() {
        let defaults = UserDefaults(suiteName: "AppStoreFavoritesTests.order")!
        defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.order")
        defer { defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.order") }

        let expectedPlans = Array(PlanCatalog.all.prefix(3)).reversed()
        defaults.set(expectedPlans.map(\.id) + ["missing.plan"], forKey: "favoritePlanIDs")

        let store = AppStore(userDefaults: defaults)

        XCTAssertEqual(store.favoritePlans.map(\.id), expectedPlans.reversed().map(\.id))
        XCTAssertFalse(store.favoritePlans.contains { $0.id == "missing.plan" })
    }
}
```

The initial test run is expected to fail because `AppStore` does not yet
provide the favorite initializer, properties, or methods. The failure must
identify those missing favorites APIs rather than an unrelated project-file
or test-target error.

- [ ] **Step 3: Run the focused test to confirm the red state.**

Run:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/AppStoreFavoritesTests test
```

Expected: the test target fails to compile with missing `AppStore` favorites
symbols. If the project cannot find the new test file, fix only the project
registration from Step 1 and rerun until the failure reaches the intended
missing-API red state.

- [ ] **Step 4: Implement the minimal `AppStore` favorites API.**

Add a private defaults key and injected defaults property:

```swift
private static let favoritePlanIDsKey = "favoritePlanIDs"
private let userDefaults: UserDefaults
@Published private(set) var favoritePlanIDs: Set<String>
```

Initialize `favoritePlanIDs` from
`userDefaults.stringArray(forKey: Self.favoritePlanIDsKey) ?? []`.
Implement:

```swift
var favoritePlans: [TrainingPlan] {
    plans.filter { favoritePlanIDs.contains($0.id) }
}

func isFavorite(_ plan: TrainingPlan) -> Bool {
    favoritePlanIDs.contains(plan.id)
}

func toggleFavorite(_ plan: TrainingPlan) {
    if !favoritePlanIDs.insert(plan.id).inserted {
        favoritePlanIDs.remove(plan.id)
    }
    userDefaults.set(favoritePlanIDs.sorted(), forKey: Self.favoritePlanIDsKey)
}
```

Keep the current HealthKit initializer behavior unchanged while adding the
`userDefaults` parameter with `.standard` as its default. Do not make the
persisted set determine order; the compatible `plans` array remains the source
of truth for display order.

- [ ] **Step 5: Run the focused tests to confirm green.**

Run the same `-only-testing:HangTenTests/AppStoreFavoritesTests` command from
Step 3. Expected: both favorite tests pass with no unrelated test or compiler
warnings.

- [ ] **Step 6: Commit the state and test slice.**

```sh
rtk git add HangTen/Models/AppStore.swift HangTenTests/AppStoreFavoritesTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: persist routine favorites"
```

### Task 2: Replace Today next-up UI and add favorite controls

**Files:**
- Modify: `HangTen/Views/RootView.swift`

**Interfaces:**
- Consumes: `AppStore.favoritePlans`, `isFavorite(_:)`, and
  `toggleFavorite(_:)` from Task 1.
- Produces: Plans and Today screens with consistent, independent navigation
  and favorite controls.

- [ ] **Step 1: Run the existing focused tests before UI work.**

Run the AppStore favorites test command from Task 1 and confirm the state API
is green before touching `RootView.swift`.

- [ ] **Step 2: Add a reusable favorite-aware routine card wrapper.**

Keep `PlanCard` as the existing routine presentation. Add a private wrapper
that receives `plan`, `board`, `isFavorite`, and an `onToggle` closure. Render a
`NavigationLink(destination: PlanDetailView(plan: plan))` beside a separate
44-point minimum hit-target `Button`, so the star cannot trigger navigation.
Use `star`/`star.fill`, a filled/outlined treatment consistent with the design
system, and accessibility text that names the plan and add/remove action.

- [ ] **Step 3: Replace the HomeView featured section.**

Replace the `featuredPlan` view with a `favoritesSection` that renders:

```swift
if store.favoritePlans.isEmpty {
    // SectionLabel("Favorites") plus the approved empty-state explanation.
} else {
    ForEach(store.favoritePlans) { plan in
        // Reusable favorite-aware routine card wrapper.
    }
}
```

Place this section where the old featured card appeared. Remove the user-facing
`NEXT UP` pill and do not show an automatic fallback routine. Keep the existing
board card, stats, and empty-compatible-plan behavior otherwise unchanged.

- [ ] **Step 4: Add favorite controls to PlansView.**

Render the same wrapper for every `store.plans` item, passing
`store.board(for: plan)`, `store.isFavorite(plan)`, and a closure calling
`store.toggleFavorite(plan)`. Preserve the existing plan ordering and detail
navigation.

- [ ] **Step 5: Preserve DEBUG review routes independently of Today favorites.**

Update `HomeView`'s DEBUG navigation destinations to use a clearly named
review-plan helper (or retain the existing helper with no normal UI consumer).
It must continue honoring `HANGTEN_REVIEW_PLAN_ID` and default to the first
compatible plan for the existing `HANGTEN_REVIEW_PLAN` and
`HANGTEN_REVIEW_WORKOUT` routes. A normal Today launch must not use this helper
to populate the favorites section.

- [ ] **Step 6: Build and run the existing unit suite.**

Run:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' test
```

Expected: the app and all unit tests compile and pass, with no nested-control
compiler warnings or accessibility identifier regressions introduced by the
new star controls.

- [ ] **Step 7: Commit the UI slice.**

```sh
rtk git add HangTen/Views/RootView.swift
rtk git commit -m "feat: show routine favorites on Today"
```

### Task 3: Validate persistence, compatibility, and review routes on a simulator

**Files:**
- No source changes expected.
- Review: `docs/IOS_SIMULATOR_VALIDATION.md` and
  `docs/IOS_RUNTIME_SERVICES.md` before running simulator commands.

**Interfaces:**
- Consumes: the committed AppStore and RootView changes from Tasks 1–2.
- Produces: fresh build, test, and runtime evidence for the acceptance criteria.

- [ ] **Step 1: Resolve a simulator owned by this workspace.**

List available device types and runtimes, create a uniquely named Hang Ten
favorites review device if one does not already exist, and record its explicit
UUID. Use that UUID for every boot, build destination, install, launch,
screenshot, and shutdown command; never use `booted`.

With the currently installed simulator catalog, create it with:

```sh
rtk xcrun simctl create "Hang Ten Favorites Review" \
  com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro \
  com.apple.CoreSimulator.SimRuntime.iOS-26-5
```

In each later shell session, resolve the recorded UUID into the same explicit
variable before running commands:

```sh
export favorites_simulator_uuid="$(rtk xcrun simctl list devices | awk -F '[()]' '/Hang Ten Favorites Review/ {print $2; exit}')"
test -n "$favorites_simulator_uuid"
```

- [ ] **Step 2: Run the full unit suite on the explicit simulator.**

Run the full `xcodebuild ... test` command from Task 2 with
`-destination "platform=iOS Simulator,id=$favorites_simulator_uuid"` and a
workspace-specific `-derivedDataPath .context/DerivedData-favorites`.
Expected: all tests pass, including both new favorite tests.

- [ ] **Step 3: Build, install, and launch the exact app artifact.**

Build Debug with the explicit simulator destination and
`.context/DerivedData-favorites`, install the resulting
`HangTen.app`, confirm the installed container for
`com.hangten.training`, and launch that exact app.

- [ ] **Step 4: Exercise the no-favorites and Plans flows.**

On a clean defaults state, inspect Today and confirm the `FAVORITES` empty
state is present and `NEXT UP` is absent. Open Plans, verify every routine has
an accessible star control, favorite one routine, and confirm the star changes
to filled without navigating away from Plans.

- [ ] **Step 5: Exercise Today, removal, and relaunch persistence.**

Return to Today and confirm the favorited routine appears with its existing
detail navigation. Toggle its star off from Today and confirm it disappears
and the empty state returns. Favorite it again, terminate/relaunch the app,
and confirm it remains visible.

- [ ] **Step 6: Exercise compatibility and DEBUG review routes.**

Use the available board selector to verify that an incompatible favorite is
hidden rather than deleted; if the current catalog exposes only one board,
verify the derived filtering path through the unit test and record that a
second physical board is not available in this build. Launch the existing
`HANGTEN_REVIEW_PLAN=1`, `HANGTEN_REVIEW_WORKOUT=1`, and
`HANGTEN_REVIEW_PLAN_ID=research.max-hangs` routes and confirm they still open
the requested plan/workout independently of the favorites list.

- [ ] **Step 7: Capture evidence and shut down only the owned simulator.**

Capture Today, Plans, and the empty-state screens if the validation workflow
requires screenshots. Inspect text clipping, star hit targets, and card
navigation. Shut down only the recorded workspace UUID and report the exact
build/test command, simulator identity, states inspected, and any limitation
caused by the current board catalog.

## Final review checklist

- [ ] The spec's eight acceptance criteria are each covered by a task or
  validation step.
- [ ] No production code was written before the Task 1 red test run.
- [ ] Both implementation slices have focused commits.
- [ ] Full tests and simulator validation have fresh, recorded evidence.
