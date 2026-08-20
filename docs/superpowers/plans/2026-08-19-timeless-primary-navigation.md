# Timeless Primary Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Today and Progress with a timeless Train / Plans / History navigation centered on the selected board, favorite plans, and saved sessions.

**Architecture:** Keep `AppStore` as the single selected-board source of truth and persist the board by stable catalog ID. Replace the integer tab state with a typed `RootTab`, move the launchpad and shared full-page board picker into a focused SwiftUI file, keep Plans reactive to the same store, and turn the existing nested session list into the History tab root. Extract sensor and Apple Health controls from the old progress dashboard into a secondary Settings screen.

**Tech Stack:** SwiftUI, Combine, Foundation `UserDefaults`, HealthKit, CoreBluetooth-backed sensor services, XCTest, Xcode 26, iOS 17+, and the repository's isolated iOS Simulator workflow.

**Spec:** `docs/superpowers/specs/2026-08-19-timeless-primary-navigation-design.md`

## Global Constraints

- The primary tabs are exactly **Train**, **Plans**, and **History**, with Train selected by default.
- Train contains the full selected-board illustration before favorite plans and contains no marketing header or session-count card.
- Board choice uses one shared full-page picker from Train and Plans and persists by stable board ID.
- Plans retains filters, custom routines, favorites, plan details, and workout launch behavior.
- History opens directly to saved sessions and contains no progress ring, streak framing, duplicate board card, or intermediate history card.
- Sensor and Apple Health controls remain available from secondary Settings reached from Train.
- Do not change training-plan content, workout timing, hold-target resolution, session record formats, HealthKit recording policy, or sensor protocols.
- Preserve private API defaults: expose only members required by real callers and use native Swift access control consistently with the project.
- Prefix every shell command with `rtk`.
- Any simulator must be uniquely named with `CONDUCTOR_WORKSPACE_NAME`, recorded under `.context`, addressed by explicit UUID, and deleted before completion.

---

## File map

- `HangTen/Models/AppStore.swift` — restore and persist the selected board ID.
- `HangTen/Models/Telemetry.swift` — rename the approved tab vocabulary to Train / Plans / History.
- `HangTen/Views/RootView.swift` — own typed tab selection, keep the existing Plans implementation, and remove the old Home and Progress implementations after their replacements exist.
- `HangTen/Views/TrainView.swift` — own Train, the reusable full-page `BoardPickerView`, board preview, favorite plans, empty-favorites routing, and Settings navigation.
- `HangTen/Views/AppSettingsView.swift` — compose existing sensor connection/configuration and Apple Health controls.
- `HangTen/Views/WorkoutSummaryView.swift` — expose saved-session history as the History tab root while preserving read-only session details.
- `HangTen.xcodeproj/project.pbxproj` — register the two new Swift files in the app target.
- `HangTenTests/AppStoreTests.swift` — selected-board restore and invalid-ID fallback tests.
- `HangTenTests/TelemetryTests.swift` — exact timeless tab-value contract.

### Task 1: Persist board selection and rename telemetry vocabulary

**Files:**
- Modify: `HangTen/Models/AppStore.swift`
- Modify: `HangTen/Models/Telemetry.swift`
- Modify: `HangTenTests/AppStoreTests.swift`
- Modify: `HangTenTests/TelemetryTests.swift`

**Interfaces:**
- Produces: `AppStore.selectedBoard: TrainingBoard { get }`
- Produces: `AppStore.selectBoard(_ board: TrainingBoard)` that updates memory, persists `board.id`, and emits existing board telemetry.
- Produces: `HangTenTelemetryEvent.AppTab.train`, `.plans`, and `.history` with matching raw values.

- [ ] **Step 1: Write failing selected-board persistence tests**

Add a test-only key constant beside the existing Health authorization key:

```swift
private static let selectedBoardIDKey = "HangTen.selectedBoardID.v1"
```

Add these tests to `AppStoreTests`:

```swift
func testSelectedBoardPersistsAndRestoresByStableID() throws {
    let defaults = makeDefaults()
    let board = try XCTUnwrap(
        BoardCatalog.all.first { $0.id != BoardCatalog.defaultBoard.id }
    )

    AppStore(defaults: defaults).selectBoard(board)
    let restored = AppStore(defaults: defaults)

    XCTAssertEqual(defaults.string(forKey: Self.selectedBoardIDKey), board.id)
    XCTAssertEqual(restored.selectedBoard.id, board.id)
}

func testUnknownPersistedBoardFallsBackToCatalogDefault() {
    let defaults = makeDefaults()
    defaults.set("removed.board", forKey: Self.selectedBoardIDKey)

    let store = AppStore(defaults: defaults)

    XCTAssertEqual(store.selectedBoard.id, BoardCatalog.defaultBoard.id)
}
```

- [ ] **Step 2: Update the telemetry test to require timeless values**

Replace the `.today` assertion and add complete value coverage:

```swift
XCTAssertEqual(
    [
        HangTenTelemetryEvent.AppTab.train.rawValue,
        HangTenTelemetryEvent.AppTab.plans.rawValue,
        HangTenTelemetryEvent.AppTab.history.rawValue
    ],
    ["train", "plans", "history"]
)
XCTAssertEqual(
    HangTenTelemetryEvent.appTabSelected(tab: .train).properties,
    ["tab": "train"]
)
```

- [ ] **Step 3: Run the focused tests and confirm the intended red failures**

Use the explicit UUID of the owned simulator prepared for this implementation:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=$review_device_uuid" \
  -derivedDataPath .context/DerivedData-timeless-navigation \
  -only-testing:HangTenTests/AppStoreTests \
  -only-testing:HangTenTests/TelemetryTests
```

Expected: persistence assertions fail because selection is not stored/restored, and telemetry compilation fails because `.train` and `.history` do not exist.

- [ ] **Step 4: Implement selected-board restoration and persistence**

In `AppStore`, make the published selection read-only to outside callers and initialize it explicitly:

```swift
private static let selectedBoardIDKey = "HangTen.selectedBoardID.v1"

@Published private(set) var selectedBoard: TrainingBoard
```

After assigning `defaults` in `init`, resolve only exact catalog IDs:

```swift
let persistedBoardID = defaults.string(forKey: Self.selectedBoardIDKey)
selectedBoard = BoardCatalog.all.first { $0.id == persistedBoardID }
    ?? BoardCatalog.defaultBoard
```

Persist before emitting existing telemetry in `selectBoard`:

```swift
func selectBoard(_ board: TrainingBoard) {
    selectedBoard = board
    defaults.set(board.id, forKey: Self.selectedBoardIDKey)
    guard let family = telemetryBoardFamily(for: board) else { return }
    telemetry.tracking.track(.boardSelected(family: family))
}
```

- [ ] **Step 5: Rename the telemetry enum cases without adding new collection**

Change only the typed vocabulary in `Telemetry.swift`:

```swift
enum AppTab: String, Equatable {
    case train
    case plans
    case history
}
```

Do not add a new tab-tracking call in this task; preserve the current collection behavior.

- [ ] **Step 6: Run focused tests and commit**

Run the Step 3 command again. Expected: all `AppStoreTests` and `TelemetryTests` pass.

```bash
rtk git add HangTen/Models/AppStore.swift HangTen/Models/Telemetry.swift HangTenTests/AppStoreTests.swift HangTenTests/TelemetryTests.swift
rtk git commit -m "Persist selected training board"
```

### Task 2: Build the Train tab and shared full-page board picker

**Files:**
- Create: `HangTen/Views/TrainView.swift`
- Modify: `HangTen/Views/RootView.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `HangTenTests/TelemetryTests.swift`

**Interfaces:**
- Produces: `enum RootTab: Hashable, CaseIterable { case train, plans, history }`
- Produces: `RootTab.initial(environment: [String: String]) -> RootTab`
- Produces: `TrainView(onBrowsePlans: @escaping () -> Void)`
- Produces: `BoardPickerView()` backed by `AppStore.selectBoard(_:)`.
- Consumes: persisted `AppStore.selectedBoard` from Task 1.

- [ ] **Step 1: Write failing typed-navigation tests**

Add the following to `TelemetryTests`:

```swift
func testRootTabsUseTimelessOrderAndReviewRouting() {
    XCTAssertEqual(RootTab.allCases, [.train, .plans, .history])
    XCTAssertEqual(RootTab.initial(environment: [:]), .train)
    XCTAssertEqual(
        RootTab.initial(environment: ["HANGTEN_REVIEW_PLANS": "1"]),
        .plans
    )
    XCTAssertEqual(
        RootTab.initial(environment: ["HANGTEN_REVIEW_HISTORY": "1"]),
        .history
    )
}
```

- [ ] **Step 2: Run the focused test and confirm it fails to compile**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=$review_device_uuid" \
  -derivedDataPath .context/DerivedData-timeless-navigation \
  -only-testing:HangTenTests/TelemetryTests
```

Expected: `RootTab` is not in scope.

- [ ] **Step 3: Add typed tab selection and the timeless tab shell**

At file scope in `RootView.swift`, add:

```swift
enum RootTab: Hashable, CaseIterable {
    case train
    case plans
    case history

    static func initial(environment: [String: String]) -> RootTab {
        if environment["HANGTEN_REVIEW_HISTORY"] == "1" {
            return .history
        }
        if environment["HANGTEN_REVIEW_PLANS"] == "1" {
            return .plans
        }
        return .train
    }
}
```

Initialize `selectedTab` with `RootTab.initial(environment:)`. Replace integer tags and labels with:

```swift
TrainView { selectedTab = .plans }
    .tabItem { Label("Train", systemImage: "figure.climbing") }
    .tag(RootTab.train)

PlansView()
    .tabItem {
        Label("Plans", systemImage: "list.bullet.rectangle.portrait.fill")
    }
    .tag(RootTab.plans)

ProgressDashboardView()
    .tabItem { Label("History", systemImage: "clock.arrow.circlepath") }
    .tag(RootTab.history)
```

The temporary `ProgressDashboardView` host keeps this commit buildable; Task 4 replaces its content.

- [ ] **Step 4: Implement `TrainView` with board preview and favorites**

Move the plan-review and workout-review debug destinations from `HomeView` into `TrainView`. Its public initializer accepts only `onBrowsePlans`; all store and service dependencies remain environment objects.

Build the screen in this order:

```swift
ScrollView(showsIndicators: false) {
    VStack(alignment: .leading, spacing: 22) {
        selectedBoardCard
        favoritesSection
    }
    .padding(.horizontal, 20)
    .padding(.top, 18)
    .padding(.bottom, 30)
}
```

The selected-board card must show `store.selectedBoard.name`, dimensions, the full `BoardMapView`, product link, and a `NavigationLink("Change board")` to `BoardPickerView`. Remove the active-hold legend because no holds are active on this passive preview.

Reuse `FavoritePlanCard` and the existing favorite toggle. The empty state uses:

```swift
Button("Browse plans", action: onBrowsePlans)
    .buttonStyle(.borderedProminent)
    .tint(.hangGreenDark)
```

Add accessibility identifiers `train.board`, `train.changeBoard`, `train.browsePlans`, and `train.settings` to support simulator review.

- [ ] **Step 5: Implement the shared full-page picker**

In the same file, create `BoardPickerView`. Use a `ScrollView` and `LazyVStack`; each board card includes its full `BoardMapView`, name, dimensions, and a selected checkmark. On selection:

```swift
Button {
    store.selectBoard(board)
    dismiss()
} label: {
    BoardPickerCard(
        board: board,
        isSelected: board.id == store.selectedBoard.id
    )
}
```

Give cards `boardPicker.board.<board.id>` accessibility identifiers and the screen the inline title **Choose board**. Use only catalog data; do not add board-specific layout branches.

- [ ] **Step 6: Register `TrainView.swift` in the Xcode project**

Add one `PBXFileReference`, one `PBXBuildFile`, one Views-group child, and one HangTen app `PBXSourcesBuildPhase` entry, following the neighboring `RootView.swift` entries. Do not add a source-text regression test for this project-file edit.

- [ ] **Step 7: Remove `HomeView` and its private helper views from `RootView.swift`**

Delete the old `HomeView`, its board menu, marketing header, quick stats, and `StatCard`. Keep shared types such as `FavoritePlanCard`, `PlanCard`, and workout destinations in their existing locations.

- [ ] **Step 8: Run focused tests, parse the project, build, and commit**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=$review_device_uuid" \
  -derivedDataPath .context/DerivedData-timeless-navigation \
  -only-testing:HangTenTests/AppStoreTests \
  -only-testing:HangTenTests/TelemetryTests
rtk xcodebuild -list -project HangTen.xcodeproj
rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .context/DerivedData-timeless-navigation \
  CODE_SIGNING_ALLOWED=NO
```

Expected: tests pass, the project lists the HangTen scheme, and the app build succeeds.

```bash
rtk git add HangTen/Views/TrainView.swift HangTen/Views/RootView.swift HangTen.xcodeproj/project.pbxproj HangTenTests/TelemetryTests.swift
rtk git commit -m "Replace Today with Train launchpad"
```

### Task 3: Add board context to Plans

**Files:**
- Modify: `HangTen/Views/RootView.swift`

**Interfaces:**
- Consumes: `BoardPickerView()` from Task 2.
- Consumes: `AppStore.selectedBoard` from Task 1.
- Preserves: existing Plans filters, plan grouping, custom routines, favorite controls, plan details, and workout launch flow.

- [ ] **Step 1: Establish the pre-change visual checkpoint**

Launch the Plans review route on the owned simulator and capture `.context/timeless-navigation/plans-before.png`. Confirm the current header has no board-selection control. This is the red UI checkpoint for the task.

- [ ] **Step 2: Add the compact current-board control**

Insert `currentBoardControl` after the Plans explanatory copy and before routine creation/filtering. Implement it as a plain-styled `NavigationLink` to `BoardPickerView`:

```swift
private var currentBoardControl: some View {
    NavigationLink {
        BoardPickerView()
    } label: {
        HStack(spacing: 12) {
            Image(systemName: "rectangle.portrait.fill")
            VStack(alignment: .leading, spacing: 2) {
                Text("Training on")
                Text(store.selectedBoard.name)
            }
            Spacer()
            Image(systemName: "chevron.right")
        }
    }
    .buttonStyle(.plain)
    .accessibilityIdentifier("plans.changeBoard")
}
```

Style it with the existing Hang Ten colors, rounded typography, and a compact cream rounded rectangle. Do not duplicate the full board illustration on Plans.

- [ ] **Step 3: Build and exercise reactive selection**

```bash
rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .context/DerivedData-timeless-navigation \
  CODE_SIGNING_ALLOWED=NO
```

Then launch `HANGTEN_REVIEW_PLANS=1`, open the picker from
`plans.changeBoard`, select a different board, and confirm the Plans control
and plan cards update without returning through Train.

- [ ] **Step 4: Commit**

```bash
rtk git add HangTen/Views/RootView.swift
rtk git commit -m "Add board picker to Plans"
```

### Task 4: Make saved sessions the History root and move integrations to Settings

**Files:**
- Create: `HangTen/Views/AppSettingsView.swift`
- Modify: `HangTen/Views/WorkoutSummaryView.swift`
- Modify: `HangTen/Views/RootView.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:**
- Produces: `HistoryView()` consuming `AppStore.sessionHistory`, `AppStore.sessionPersistenceError`, and `MotherboardSettingsStore.forceUnit` from environment objects.
- Produces: `AppSettingsView()` consuming `AppStore`, `MotherboardBluetoothService`, and `MotherboardSettingsStore` from environment objects.
- Preserves: `WorkoutSummaryContent` as the read-only detail destination.

- [ ] **Step 1: Establish pre-change History and integration checkpoints**

Launch the current History tab and capture `.context/timeless-navigation/history-before.png`. Confirm it still contains the progress ring, motivational copy, nested history card, duplicate board card, sensor card, and Apple Health card.

- [ ] **Step 2: Promote the existing saved-session list to `HistoryView`**

In `WorkoutSummaryView.swift`, add a wrapper that supplies environment data and owns the `NavigationStack`:

```swift
struct HistoryView: View {
    @EnvironmentObject private var store: AppStore
    @EnvironmentObject private var settings: MotherboardSettingsStore
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        NavigationStack {
            WorkoutSessionHistoryView(
                sessions: store.sessionHistory,
                unit: settings.forceUnit,
                persistenceError: store.sessionPersistenceError
            )
        }
        .onAppear {
            store.refreshHealthAuthorization()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                store.refreshHealthAuthorization()
            }
        }
    }
}
```

Extend `WorkoutSessionHistoryView` with `var persistenceError: String? = nil`. When non-nil, show one inline error row before session rows. Change its navigation title from **Session history** to **History**. Preserve newest-first input order, row content, empty state, and read-only detail navigation.

- [ ] **Step 3: Extract Settings and Apple Health controls**

Create `AppSettingsView.swift` with a scroll view containing:

1. a **Training sensor** section using the existing `MotherboardCard`;
2. a `NavigationLink` to `MotherboardSettingsView`; and
3. an **Apple Health** section preserving the old status pill, detail, sync-source message, error, Connect action, and Open app settings action.

Move the Health action enum and computed state/tint/message helpers out of `ProgressDashboardView` into `AppSettingsView`. Refresh Health authorization on appearance and whenever the scene becomes active, matching the old behavior. Keep existing accessibility identifiers `health.historySource`, `health.connect`, and `health.settings`.

- [ ] **Step 4: Link Settings from Train and support review routes**

Add a trailing gear `NavigationLink` in Train with `train.settings`. In DEBUG, make `HANGTEN_REVIEW_SETTINGS=1`, `HANGTEN_REVIEW_HEALTH=1`, and `HANGTEN_REVIEW_MOTHERBOARD=1` present Settings from Train so existing review workflows remain usable. Make `HANGTEN_REVIEW_BOARD_PICKER=1` present the board picker.

- [ ] **Step 5: Replace and remove the old Progress dashboard**

Use `HistoryView()` for `.history` in `RootView`. Delete `ProgressDashboardView` in full, including its progress card, intermediate session-history card, duplicate board card, embedded sensor card, and embedded Apple Health card. Do not delete reusable sensor or session-summary components.

- [ ] **Step 6: Register `AppSettingsView.swift`, build, and run focused regressions**

Add one `PBXFileReference`, one `PBXBuildFile`, one Views-group child, and one
HangTen app `PBXSourcesBuildPhase` entry for `AppSettingsView.swift`, following
the neighboring `RootView.swift` entries. Do not add a source-text regression
test for this project-file edit. Then run:

```bash
rtk xcodebuild -list -project HangTen.xcodeproj
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=$review_device_uuid" \
  -derivedDataPath .context/DerivedData-timeless-navigation \
  -only-testing:HangTenTests/WorkoutSummaryTests \
  -only-testing:HangTenTests/LocalWorkoutHistoryStoreTests \
  -only-testing:HangTenTests/WorkoutHistoryServiceTests \
  -only-testing:HangTenTests/HealthKitServiceTests \
  -only-testing:HangTenTests/MotherboardBluetoothServiceTests
rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .context/DerivedData-timeless-navigation \
  CODE_SIGNING_ALLOWED=NO
```

Expected: project parsing, focused tests, and build all succeed.

- [ ] **Step 7: Commit**

```bash
rtk git add HangTen/Views/AppSettingsView.swift HangTen/Views/WorkoutSummaryView.swift HangTen/Views/RootView.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "Replace Progress with session History"
```

### Task 5: Full verification and visual review

**Files:**
- Verify: all implementation files from Tasks 1–4
- Generate only under: `.context/timeless-navigation/`

**Interfaces:**
- Consumes: completed Train / Plans / History implementation.
- Produces: test/build evidence, visual screenshots, and verified simulator cleanup; no committed product source is added in this task unless a defect is found.

- [ ] **Step 1: Run the full app test suite**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination "platform=iOS Simulator,id=$review_device_uuid" \
  -derivedDataPath .context/DerivedData-timeless-navigation \
  CODE_SIGNING_ALLOWED=NO
```

Expected: the complete HangTen test suite passes.

- [ ] **Step 2: Build, install, and launch on the owned simulator**

Use the repository's `validate-hang-ten-ios` workflow with the explicit owned simulator UUID. Build into `.context/DerivedData-timeless-navigation`, install the resulting app, and launch only against `$review_device_uuid`.

- [ ] **Step 3: Capture the visual checkpoints**

Capture these screenshots under `.context/timeless-navigation/`:

- `train.png` — full board preview first, favorite plans second, no marketing header or count card;
- `board-picker.png` — full-page picker with illustrations and selected checkmark;
- `plans.png` — compact current-board control and unchanged library affordances;
- `history.png` — saved-session list at root, with none of the old Progress content;
- `settings.png` — training sensor and Apple Health controls; and
- `train-empty-favorites.png` plus `history-empty.png` when deterministic DEBUG fixtures can produce those states without mutating shared user data.

Inspect portrait layout, Dynamic Type clipping at the default review size, tab labels/icons, navigation back behavior, board selection return behavior, and landscape workout review routes to ensure the navigation changes did not regress workout orientation.

- [ ] **Step 4: Verify exact simulator cleanup**

Shut down and delete only the UUID recorded for this workspace. Run the repository cleanup verifier and confirm the UUID no longer appears in `xcrun simctl list devices`. Leave shared, standard, and unknown devices untouched.

- [ ] **Step 5: Review the final diff and status**

```bash
rtk git diff --check 0e5f0ae..HEAD
rtk git status --short
rtk git log --oneline -5
```

Expected: no whitespace errors, only intended source/spec/plan commits plus ignored `.context` artifacts, and no owned simulator remains.
