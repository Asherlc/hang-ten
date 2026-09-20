# Batch 03 Workout Configuration Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry one exact, accessible board configuration from board detail and custom-routine editing through frozen workout preparation, setup confirmation, playback, navigation, and activity recording.

**Architecture:** Package metadata and runtime resolution remain owned by the finalized sibling plans. This plan adds presentation state keyed by the exact model hash, an atomic editor command, a pre-session frozen target plan, and a setup reducer whose timer/audio/navigation integrations land as separately reviewable changes. UI, highlights, setup prompts, and recording all consume the same frozen `ResolvedBoardTarget` values and fail closed when any identity check fails.

**Tech Stack:** Swift 6, SwiftUI, SceneKit, XCTest/XCUITest, Xcode project build phases, Apple On-Demand Resources, repository `validate-hang-ten-ios` workflow.

**Spec:** `docs/superpowers/specs/2026-09-20-hangboards-batch-03-3d-migration-design.md`

## Global Constraints

- Read the spec and finalized sibling plans: `docs/superpowers/plans/2026-09-20-batch-03-configuration-runtime.md` and `docs/superpowers/plans/2026-09-20-batch-03-model-packages.md`.
- Runtime owns `ContactRequirement`, `CustomRoutineDraft.swift`, `CustomRoutineStore.swift`, every preserve/strip transformation and validator, plus `PlanStorageTests`, `CustomRoutineDraftTests`, `CustomRoutineStoreTests`, and `WorkoutActivityRecordingTests`. This plan consumes but never edits them.
- Package numbering is stable: Aelith Task 8, NUG Task 9, Port Task 10, Oak Task 11, Karma Task 12, Plateau Task 13, reimport Task 14, cord Task 15, ODR Task 16, native Task 17, and final handoff Task 18.
- Tasks 1–7 require runtime Tasks 2–5. Tasks 1–3 require package Task 13 because their RED/GREEN fixtures load the real Plateau package. Task 1 additionally requires package Task 16 only for ODR-backed loading checks; its pure reducer tests need Task 13 but not ODR. Task 8 begins only after runtime Task 7 and package Task 18.
- Schema remains version 3. `BoardPosition` is the sole configuration authority; experience code does not duplicate package inventory.
- Plateau is one `edge-18` contact with positions/presentations `depth-18mm`, `depth-15mm`, and `depth-10mm`. Eighteen millimeters is a browsing default only.
- Generic requirements remain configuration-neutral. Ambiguity requires athlete choice; declaration order and default presentation never select a workout target.
- Board-specific editor selection writes `contactID`, `positionID`, and semantic `depth` as one replacement. Missing/stale/mismatched identity blocks preview, Save, and Start.
- Rendering, highlights, prompts, navigation, and recording use the frozen per-segment map. Playback never resolves again or exposes a presentation picker.
- Setup Ready remains disabled until the exact frozen target's `BoardModelKey` and `positionID` report `.ready` after pose, suspension, highlight, and accessibility application.
- Setup waiting is outside authored time. Boundary overshoot clamps exactly, accrues zero work/rest/stopwatch/sensor time, and stops countdown/spoken audio.
- Missing resources, cancellation, hash mismatch, stale revision, mismatched presentation, unsupported transition, and missing frozen entries show `workout.configurationUnavailable`; no default/first/raster/stale/deleted-ID fallback is allowed.
- UI copy names only package-evidenced equipment state. Do not add training prescriptions, exercise names, counts, or durations.
- Use `rtk`; preserve unrelated changes. Every task ends in one commit, one push, and a fresh review checkpoint.
- Final validation follows `.codex/skills/validate-hang-ten-ios/SKILL.md`, `docs/IOS_SIMULATOR_VALIDATION.md`, and `docs/IOS_RUNTIME_SERVICES.md` with one workspace-owned simulator and cleanup trap.
- No HTTP server is required. If execution unexpectedly starts one, set `server_port` to that server's exact numeric port, run `/Users/asherlc/bin/paseo-quick-tunnel "$server_port"` for its full lifetime, and report only the emitted `https://…trycloudflare.com` URL.

## Review Focus

1. A late callback with wrong board, presentation, hash, or position must never commit; Task 1 tests each field, cancellation, and out-of-order delivery.
2. Editor selection must never expose/save a position paired with another depth; Task 2 tests atomic replacement and unchanged state after rejection.
3. Frozen segments may union highlights only when board/revision/position/presentation/model-key identities match; Task 3 tests each mismatch.
4. Ready cannot confirm before exact model readiness, and rest overshoot must clamp with audio stopped; Tasks 4–5 test both reducers.
5. Port's unmeasured contacts must record `{}` without invented depth while removed legacy IDs remain immutable; Task 8 owns package-backed acceptance.

---

## Finalized Dependency Interfaces

Runtime Tasks 2–5 produce:

```swift
struct ResolvedBoardTarget: Hashable {
    let boardID: String
    let revisionID: String
    let contactIDs: [String]
    let positionID: String
    let presentationID: String
    let effectiveDepths: [String: HoldDepth]
    let modelSHA256: String?
}

enum BoardTargetResolution: Hashable {
    case resolved(ResolvedBoardTarget)
    case positionChoiceRequired([ResolvedBoardTarget])
}

enum ContactResolver {
    static func resolveTarget(_ requirements: [ContactRequirement], step: WorkoutStep, board: BoardRevision) throws -> BoardTargetResolution
    static func resolveTarget(_ requirements: [ContactRequirement], step: WorkoutStep, board: BoardRevision, positionID: String) throws -> ResolvedBoardTarget
}

struct ContactRequirement: Codable, Hashable {
    let contactID: String?
    let positionID: String?
    let depth: HoldDepth?
    func strippingExactContactIdentity() -> ContactRequirement
    var singleHandSelection: ContactRequirement { get }
}

struct WorkoutActivitySegmentKey: Hashable {
    let stepID: String
    let segmentIndex: Int
}
```

`WorkoutActivityRecorder.segments` and `.metadata` accept `resolvedTargets: [WorkoutActivitySegmentKey: ResolvedBoardTarget]? = nil` immediately after `sessionSteps`. A non-`nil` map is complete and runtime Task 5 alone revalidates/writes configuration snapshots and selected-presentation hashes.

## File Map

- Task 1 creates `BoardConfigurationPresentation.swift`, `BoardConfigurationPicker.swift`, shared DEBUG review-launch parsing, and the board-detail UI-test slice; modifies model/map/detail views.
- Task 2 creates `CustomRoutineBoardSelection.swift`, focused tests, and the editor DEBUG/UI-test slice; modifies only editor behavior plus the shared UI-test file.
- Task 3 creates frozen-target planning/preparation UI/tests and the ambiguity-choice DEBUG/UI-test slice; modifies launch state.
- Task 4 creates setup-gate/readiness state and tests.
- Task 5 integrates exact boundary timing/audio and focused tests.
- Task 6 creates confirmation UI/navigation tests, setup DEBUG injection, and the setup/failure UI-test slice.
- Task 7 modifies AppStore/WorkoutView handoff and creates handoff tests.
- Task 8 solely owns `Batch03WorkoutExperienceIntegrationTests.swift`; it consumes the completed DEBUG/UI-test surfaces and owns final package/full simulator acceptance only.

### Task 1: Keyed Atomic Board-Detail Presentation

**Prerequisites:** Runtime Tasks 2–5 and package Task 13. The pure option/reducer RED/GREEN work consumes Task 13 only; Step 4 and the ODR-backed renderer/store checks in Step 6 additionally wait for package Task 16.

**Files:**
- Create: `HangTen/Models/BoardConfigurationPresentation.swift`
- Create: `HangTen/Models/BoardConfigurationReviewLaunch.swift` (`#if DEBUG`)
- Create: `HangTen/Views/BoardConfigurationPicker.swift`
- Create: `HangTenTests/BoardConfigurationPresentationTests.swift`
- Create: `HangTenUITests/BoardConfigurationUITests.swift`
- Create: `scripts/wait-for-simulator-accessibility.sh`
- Modify: `HangTen/Views/BoardModelView.swift:7-12,414-500,1915-1985`
- Modify: `HangTen/Views/BoardMapView.swift:52-86,282-650`
- Modify: `HangTen/Views/TrainView.swift:223-341`
- Modify: `HangTen.xcodeproj/project.pbxproj:1-1015`

**Interfaces:**

```swift
struct BoardModelConfigurationIdentity: Hashable {
    let key: BoardModelKey
    let positionID: String
}
struct BoardConfigurationOption: Identifiable, Hashable {
    let contactID: String
    let positionID: String
    let presentationID: String
    let effectiveDepth: HoldDepth
    let expectedModelKey: BoardModelKey
    var id: String { positionID }
    var modelIdentity: BoardModelConfigurationIdentity { get }
}
extension HoldDepth {
    var exactMillimeters: Double? { get }
}
enum BoardModelLoadEvent: Equatable {
    case loading(BoardModelConfigurationIdentity)
    case ready(BoardModelConfigurationIdentity)
    case unavailable(BoardModelConfigurationIdentity)
    case cancelled(BoardModelConfigurationIdentity)
}
enum BoardConfigurationLoadPhase: Equatable {
    case loading
    case ready
    case unavailable
}
struct BoardConfigurationPresentationState: Equatable {
    private(set) var requested: BoardConfigurationOption
    private(set) var committed: BoardConfigurationOption?
    private(set) var phase: BoardConfigurationLoadPhase
    init(requested: BoardConfigurationOption)
    mutating func request(_ option: BoardConfigurationOption)
    mutating func receive(_ event: BoardModelLoadEvent) -> Bool
}
#if DEBUG
enum BoardConfigurationReviewSurface: String { case boardDetail = "board-detail", editor, choice, setup }
enum BoardConfigurationReviewWorkflowState: String {
    case selected, selectionSwitch = "selection-switch", ambiguousChoice = "ambiguous-choice"
    case initialSetup = "initial-setup", restPreview = "rest-preview", restWait = "rest-wait"
    case naturalBoundary = "natural-boundary", skip, jump, rewind, restart
    case resumePaused = "resume-paused", resumeRunning = "resume-running", unavailable
}
enum BoardConfigurationReviewLoadMode: String {
    case production, exactReady = "exact-ready", wrongIdentity = "wrong-identity"
    case missingResource = "missing-resource", hashMismatch = "hash-mismatch", cancelled, unavailable
}
enum BoardConfigurationReviewLaunchError: LocalizedError, Equatable {
    case missingEnvironmentValue(String)
    case invalidEnvironmentValue(key: String, value: String)
    case boardNotFound(String)
    case positionNotFound(boardID: String, positionID: String)
    case invalidPositionPresentation(positionID: String, presentationID: String)
    case presentationIsNotModel(String)
}
struct BoardConfigurationReviewLaunch: Equatable {
    let boardID: String; let presentationID: String; let positionID: String
    let surface: BoardConfigurationReviewSurface
    let workflowState: BoardConfigurationReviewWorkflowState
    let loadMode: BoardConfigurationReviewLoadMode
    init(environment: [String: String]) throws
}
struct BoardConfigurationReviewTarget {
    let board: BoardRevision
    let position: BoardPosition
    let presentation: BoardPresentation
    let modelIdentity: BoardModelConfigurationIdentity
    let highlightedContactIDs: Set<String>
    static func resolve(
        launch: BoardConfigurationReviewLaunch,
        boards: [BoardRevision] = BoardCatalog.all
    ) throws -> BoardConfigurationReviewTarget
}
struct BoardModelReviewCameraSignals {
    let requestFixedOrbit: () -> Void
    let orbitDidSettle: (BoardModelConfigurationIdentity) -> Void
    let resetDidSettle: (BoardModelConfigurationIdentity, String) -> Void
}
#endif
```

`BoardModelSurface` gains `onLoadEvent`; `BoardMapView` gains explicit `selectedPositionID`, `allowsPresentationSelection`, and callback parameters. `BoardHoldSpecifications.entries(for:effectiveDepth:)` replaces the base Depth row. Under `#if DEBUG`, `review.model.orbit` calls the same camera reducer used by the production drag gesture with fixed deltas `yaw:+0.35` and `pitch:-0.18`; after the renderer reports that transform applied it exposes `review.model.orbit-complete`. A tap on the existing production highlighted-contact element whose identifier is `"boardModel.contact." + contactID` continues through the production contact-selection camera-reset path; only its real reset completion callback exposes `review.model.reset-complete`. Do not add or rename a contact accessibility identifier. Both completion elements have value `boardID|presentationID|positionID|modelSHA256`, disappear on the next camera/model mutation, and cannot directly mutate camera state.

- [ ] **Step 1: Write the RED identity-event matrix.** Derive options from real Plateau. Add `private func replacing(_ key: BoardModelKey, boardID: String? = nil, presentationID: String? = nil, modelSHA256: String? = nil) -> BoardModelKey`.

| Current request | Event | Exact result |
| --- | --- | --- |
| 15 | exact 15 ready | commits 15; returns true |
| 15 | wrong board ready | no commit; loading; false |
| 15 | wrong presentation ready | no commit; loading; false |
| 15 | wrong hash ready | no commit; loading; false |
| 15 | exact key, 18 position | no commit; loading; false |
| 15 after 18 | late exact 18 ready | no commit; loading; false |
| 15 | exact cancelled | no commit; unavailable; true |
| 15 | exact unavailable | no commit; unavailable; true |

```swift
func testWrongHashCannotCommitRequestedPosition() throws {
    let fixture = try plateauConfigurationFixture()
    var state = BoardConfigurationPresentationState(requested: fixture.depth15)
    let wrong = replacing(fixture.depth15.expectedModelKey, modelSHA256: String(repeating: "f", count: 64))
    XCTAssertFalse(state.receive(.ready(.init(key: wrong, positionID: "depth-15mm"))))
    XCTAssertNil(state.committed)
}
```

Also create `final class BoardConfigurationUITests: XCTestCase` and RED `testBoardDetailSwitchCommitsOnlyExactReady`. It launches `board-detail/selection-switch/production` on real Plateau depth 15, waits for `review.model.ready`, taps depth 10, waits again, and asserts the model/spec/accessibility value all become `10 millimeters` with no 15 mm content. Add `testReviewOrbitAndHighlightedContactTapUseProductionCameraPaths`: wait for exact ready, tap `review.model.orbit`, require `review.model.orbit-complete` with the exact identity value, tap existing production element `boardModel.contact.edge-18`, require `review.model.reset-complete` with that same identity value, and assert the production camera reducer recorded fixed orbit then canonical reset in that order. Later tasks append methods to this same class and reuse this exact helper:

```swift
private func launchReview(
    surface: String,
    state: String,
    positionID: String = "depth-15mm",
    loadMode: String = "production",
    landscape: Bool = false
) -> XCUIApplication {
    let app = XCUIApplication()
    app.launchEnvironment = [
        "HANGTEN_REVIEW_BOARD_ID": "plateau.lifting-edge",
        "HANGTEN_REVIEW_PRESENTATION_ID": positionID,
        "HANGTEN_REVIEW_POSITION_ID": positionID,
        "HANGTEN_REVIEW_CONFIGURATION_UI": surface,
        "HANGTEN_REVIEW_WORKFLOW_STATE": state,
        "HANGTEN_REVIEW_MODEL_LOAD_MODE": loadMode,
        landscape ? "HANGTEN_REVIEW_LANDSCAPE" : "HANGTEN_REVIEW_PORTRAIT": "1",
    ]
    app.launch()
    return app
}
```

- [ ] **Step 2: Run RED.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/BoardConfigurationPresentationTests -only-testing:HangTenUITests/BoardConfigurationUITests/testBoardDetailSwitchCommitsOnlyExactReady
```

Expected: compile failure for new option/identity/event/reducer types.

- [ ] **Step 3: Implement exact option construction.** Enumerate authored positions; require membership, model presentation, and exact effective depth. Construct `expectedModelKey` from selected board/presentation/descriptor hash. `receive` requires full identity equality before mutation.

```swift
guard board.contactIDs(inPosition: position.id).contains(contact.id),
      let presentation = board.presentation(id: position.presentationID),
      case .model(let media) = presentation.media,
      let depth = position.effectiveDepth(for: contact), depth.exactMillimeters != nil else { return nil }
let key = BoardModelKey(boardID: board.id, presentationID: presentation.id, modelSHA256: media.descriptor.modelSHA256)
```

- [ ] **Step 4: Emit ready only after scene application.** Emit loading before acquisition; select pose, apply suspension/highlights/accessibility, then ready only if all succeed. Current cancellation emits cancelled; missing/hash/scene failure emits unavailable. Asset download alone never emits ready. Route the DEBUG fixed-orbit control through the production orbit reducer, and route highlighted-contact reset through the existing production contact-tap/reset callback; emit their review completion identifiers only after renderer settlement for the still-current full identity.

- [ ] **Step 5: Integrate accessible detail and the general DEBUG board route.** Plateau shows `Edge depth` and exact identifiers `boardDetail.edgeDepth.depth-18mm`, `boardDetail.edgeDepth.depth-15mm`, and `boardDetail.edgeDepth.depth-10mm`. Loading hides old scene/spec; accepted ready commits all and announces `Edge depth, 15 millimeters, selected.` Failure clears stale content. `BoardConfigurationReviewTarget.resolve` must find the exact catalog board and position, require `position.presentationID == launch.presentationID`, find that exact model presentation and descriptor/hash, and set `highlightedContactIDs = Set(board.contactIDs(inPosition: position.id))`. General B01–B19 review routes pass that set plus locked presentation/position directly to `BoardMapView`; they never construct `BoardConfigurationOption`. Only a board-detail/editor route whose selected contact has an authored exact `position.effectiveDepth(for:)` (Plateau B20–B22) calls the option factory and exposes `Edge depth`.

After pose, suspension, exact highlights, and accessibility are applied, expose `review.model.ready` with accessibility label `Model ready` and value `boardID|presentationID|positionID|modelSHA256`; remove it on loading, cancellation, unavailable, or identity change. `testBoardDetailSwitchCommitsOnlyExactReady` asserts both existence and the exact Plateau value prefix.

Implement this exact wait-helper interface:

```text
scripts/wait-for-simulator-accessibility.sh --udid UUID --identifier AXUniqueId --timeout-seconds SECONDS [--value-prefix TEXT] [--value-contains TEXT] [--value-suffix TEXT]
```

Require `--udid`, `--identifier`, and a positive `--timeout-seconds`; accept `--value-prefix`, `--value-contains`, and `--value-suffix` at most once each and apply every supplied matcher with AND semantics. Reject unknown flags, missing or empty prefix/contains/suffix arguments, duplicate matcher flags, or malformed UUID/timeout with exit 2. Every 0.25 seconds run `/opt/homebrew/bin/axe describe-ui --udid "$udid"`, parse its JSON with `/usr/bin/jq --arg identifier "$identifier" '[.. | objects | select(.AXUniqueId? == $identifier)]'`, require the resulting array count to equal one, and read only `(.[0].AXValue // "" | tostring)` from that array (never grep a different element or the hierarchy globally). Evaluate prefix, contains, and suffix only against that uniquely scoped value, and return 0 only when the element exists and every supplied predicate matches. Factor those three AND checks into sourceable `wait_value_matches actual prefix contains suffix -> exit status`; guard `main "$@"` with `[[ "${BASH_SOURCE[0]}" == "$0" ]]` so Step 6 can test the pure predicate. On timeout return 1 and print the requested identifier, all supplied predicates, last matched value, and last hierarchy. Identity-bearing `review.model.ready`, `review.model.orbit-complete`, and `review.model.reset-complete` calls must always supply the exact `boardID|presentationID|positionID|` value prefix; terminal `review.workflow.*` calls supply that prefix plus an exact `|elapsed|running` or `|elapsed|paused` suffix so trailing content fails.

- [ ] **Step 6: Run GREEN.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/BoardConfigurationPresentationTests -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/BoardPackageStoreTests
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenUITests/BoardConfigurationUITests/testBoardDetailSwitchCommitsOnlyExactReady -only-testing:HangTenUITests/BoardConfigurationUITests/testReviewOrbitAndHighlightedContactTapUseProductionCameraPaths
rtk bash -n scripts/wait-for-simulator-accessibility.sh
rtk bash -c 'source "$1"; wait_value_matches "plateau.lifting-edge|depth-15mm|depth-15mm|hash|10.00|running" "plateau.lifting-edge|depth-15mm|depth-15mm|" "depth-15mm" "|10.00|running"' _ scripts/wait-for-simulator-accessibility.sh
rtk bash -c 'source "$1"; if wait_value_matches "plateau.lifting-edge|depth-15mm|depth-15mm|hash|10.00|running|trailing" "plateau.lifting-edge|depth-15mm|depth-15mm|" "depth-15mm" "|10.00|running"; then exit 1; fi' _ scripts/wait-for-simulator-accessibility.sh
rtk bash -c 'set +e; /bin/bash "$1" --udid 00000000-0000-0000-0000-000000000000 --identifier review.workflow.test --timeout-seconds 1 --value-suffix >/dev/null 2>&1; status=$?; test "$status" -eq 2' _ scripts/wait-for-simulator-accessibility.sh
rtk bash -c 'set +e; /bin/bash "$1" --udid 00000000-0000-0000-0000-000000000000 --identifier review.workflow.test --timeout-seconds 1 --value-suffix "" >/dev/null 2>&1; status=$?; test "$status" -eq 2' _ scripts/wait-for-simulator-accessibility.sh
rtk bash -c 'set +e; /bin/bash "$1" --udid 00000000-0000-0000-0000-000000000000 --identifier review.workflow.test --timeout-seconds 1 --value-suffix one --value-suffix two >/dev/null 2>&1; status=$?; test "$status" -eq 2' _ scripts/wait-for-simulator-accessibility.sh
```

Expected: eight event rows, adjacent renderer tests, and the production-path orbit/reset test pass; combined prefix/contains/suffix accepts the exact terminal value, rejects trailing content, and missing/empty/duplicate suffix arguments return 2.

- [ ] **Step 7: Commit and push.**

```bash
rtk git add HangTen/Models/BoardConfigurationPresentation.swift HangTen/Models/BoardConfigurationReviewLaunch.swift HangTen/Views/BoardConfigurationPicker.swift HangTen/Views/BoardModelView.swift HangTen/Views/BoardMapView.swift HangTen/Views/TrainView.swift HangTenTests/BoardConfigurationPresentationTests.swift HangTenUITests/BoardConfigurationUITests.swift scripts/wait-for-simulator-accessibility.sh HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: present board configurations atomically"
rtk git push
```

**Review checkpoint:** Verify descriptor-derived expected keys, all identity comparisons, and no stale scene/spec after failure.

### Task 2: Atomic Custom-Routine Editor Command and Preview

**Prerequisites:** Experience Task 1, runtime Tasks 2–5, package Task 13, and package Task 16. The editor consumes Task 1's validated option/model target, every RED/GREEN fixture loads the real Plateau board, and its production preview must acquire the exact ODR-backed model before exposing `review.model.ready`.

**Files:**
- Create: `HangTen/Models/CustomRoutineBoardSelection.swift`
- Create: `HangTenTests/CustomRoutineBoardSelectionTests.swift`
- Modify: `HangTen/Views/CustomRoutineEditorView.swift:1-225,259-600`
- Modify: `HangTen/Views/RootView.swift:320-470` (DEBUG editor route only)
- Modify: `HangTenUITests/BoardConfigurationUITests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj:1-1015`

**Interfaces:** Consumes runtime's initializer, `strippingExactContactIdentity()`, `CustomRoutineDraft.retargeted(to:)`, and `CustomRoutineValidator.issues`; does not edit their owners.

```swift
enum CustomRoutineBoardSelectionError: LocalizedError, Equatable {
    case contactNotOnBoard(contactID: String)
    case positionNotOnBoard(positionID: String)
    case contactNotInPosition(contactID: String, positionID: String)
    case presentationNotOnBoard(presentationID: String)
    case effectiveDepthUnavailable(contactID: String, positionID: String)
}
enum CustomRoutineBoardSelection {
    static func selecting(contact: PhysicalContact, option: BoardConfigurationOption, in step: CustomRoutineStepDraft, on board: BoardRevision) throws -> CustomRoutineStepDraft
    static func selecting(option: BoardConfigurationOption, in step: CustomRoutineStepDraft, on board: BoardRevision) throws -> CustomRoutineStepDraft
    static func previewTarget(for step: CustomRoutineStepDraft, on board: BoardRevision) throws -> ResolvedBoardTarget?
}
```

- [ ] **Step 1: Write RED matrix.** Define `private func exactDepth(_ value: Double) -> HoldDepth` as `.range(.init(minimum:value, maximum:value))` and `private func plateauEditorFixture() throws -> PlateauEditorFixture` from the real catalog package.

| Input | Exact result |
| --- | --- |
| empty + 18 option | edge-18/depth-18mm/exact18 |
| configured18 + 15 | same contact/depth-15mm/exact15 |
| configured15 + 10 | same contact/depth-10mm/exact10 |
| wrong contact option | throws contactNotInPosition; draft equal |
| unknown position | throws positionNotOnBoard; draft equal |
| cross-wired presentation | throws presentationNotOnBoard; draft equal |
| stale preview | propagates resolver error; no fallback |

```swift
func testSwitchToFifteenReplacesIdentityAndDepthTogether() throws {
    let f = try plateauEditorFixture()
    let changed = try CustomRoutineBoardSelection.selecting(option: f.depth15, in: f.depth18Step, on: f.board)
    XCTAssertEqual(changed.targets.first?.contactID, "edge-18")
    XCTAssertEqual(changed.targets.first?.positionID, "depth-15mm")
    XCTAssertEqual(changed.targets.first?.depth, exactDepth(15))
}
```

Add UI RED `testEditorSwitchReplacesDepthAndPreviewTogether`: launch `editor/selection-switch/production` at Plateau depth 15, wait for `review.model.ready`, choose depth 10, wait again, and assert preview plus the draft's visible `contactID`, `positionID`, and semantic depth become `edge-18`, `depth-10mm`, and exact 10 together before Save enables.

- [ ] **Step 2: Run RED.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/CustomRoutineBoardSelectionTests -only-testing:HangTenUITests/BoardConfigurationUITests/testEditorSwitchReplacesDepthAndPreviewTogether
```

Expected: command/test class absent.

- [ ] **Step 3: Implement validate-then-replace.** Resolve every dependency to locals, then replace once with the exact `ContactRequirement` initializer. Position-only selection reads the existing contact and delegates. Preview calls explicit-position resolver and never catches errors.

- [ ] **Step 4: Integrate UI/runtime transformations and the editor review slice.** Tap selects 18 atomically and reveals picker; switching calls one command. Give its exact options identifiers `customRoutine.edgeDepth.depth-18mm`, `.depth-15mm`, and `.depth-10mm`. Save disables on runtime target issues. Target-mode changes call `draft.retargeted(to:)`, whose runtime implementation uses `strippingExactContactIdentity()`; the view never reconstructs generic requirements. The DEBUG `editor` route consumes Task 1's validated Plateau `BoardConfigurationReviewTarget`, derives `BoardConfigurationOption` only because the selected contact/position has exact authored effective depth, and opens the real editor/preview without persistence.

- [ ] **Step 5: Add consumption assertions.** Actual runtime board-specific15→generic yields nil IDs and exact15; single-hand copy retains both IDs. Keep assertions in the new experience test only.

- [ ] **Step 6: Run GREEN.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/CustomRoutineBoardSelectionTests -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/CustomRoutineDraftTests -only-testing:HangTenTests/CustomRoutineStoreTests
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenUITests/BoardConfigurationUITests/testEditorSwitchReplacesDepthAndPreviewTogether
```

Expected: experience and unchanged runtime suites pass.

- [ ] **Step 7: Commit and push.**

```bash
rtk git add HangTen/Models/CustomRoutineBoardSelection.swift HangTen/Views/CustomRoutineEditorView.swift HangTen/Views/RootView.swift HangTenTests/CustomRoutineBoardSelectionTests.swift HangTenUITests/BoardConfigurationUITests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: edit board setup as one atomic value"
rtk git push
```

**Review checkpoint:** Confirm no runtime-owned file changes and every rejected command preserves the draft.

### Task 3: Freeze Complete Targets and Explicit Choices

**Prerequisites:** Experience Task 1, runtime Tasks 2–5, and package Task 13 because preparation and identity RED/GREEN tests use Task 1's validated launch parser/target and the real three-position Plateau package. The choice route does not render or acquire a model, so it does not require package Task 16; a future choice preview that waits for `review.model.ready` would require Task 16 explicitly.

**Files:**
- Create: `HangTen/Models/WorkoutBoardTargetPlan.swift`
- Create: `HangTen/Views/WorkoutConfigurationPreparationView.swift`
- Create: `HangTenTests/WorkoutBoardTargetPlanTests.swift`
- Modify: `HangTen/Views/WorkoutAccessGate.swift:3-90`
- Modify: `HangTen/Views/RootView.swift:1876-2310,2980-3160`
- Modify: `HangTenUITests/BoardConfigurationUITests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj:1-1015`

**Interfaces:**

```swift
struct WorkoutBoardTargetIdentity: Hashable {
    let boardID: String; let revisionID: String; let positionID: String; let presentationID: String
    let modelKey: BoardModelKey?
    let modelSHA256: String?
    init(target: ResolvedBoardTarget)
}
struct WorkoutBoardRenderTarget: Equatable {
    let configuration: ResolvedBoardTarget
    let highlightedContactIDs: Set<String>
}
struct WorkoutBoardTargetChoice: Identifiable, Equatable {
    let key: WorkoutActivitySegmentKey
    let stepID: String
    let options: [ResolvedBoardTarget]
    var id: WorkoutActivitySegmentKey { key }
}
struct WorkoutBoardTargetSelections: Equatable {
    private(set) var positionIDsByKey: [WorkoutActivitySegmentKey: String]
    init(positionIDsByKey: [WorkoutActivitySegmentKey: String] = [:])
    subscript(key: WorkoutActivitySegmentKey) -> String? { get }
    mutating func select(positionID: String, for key: WorkoutActivitySegmentKey)
}
enum WorkoutBoardTargetPreparation: Equatable {
    case choiceRequired([WorkoutBoardTargetChoice])
    case ready(WorkoutBoardTargetPlan)
}
enum WorkoutBoardTargetPlanner {
    static func prepare(
        sessionSteps: [WorkoutStep],
        board: BoardRevision,
        selections: WorkoutBoardTargetSelections = .init()
    ) throws -> WorkoutBoardTargetPreparation
}
struct WorkoutBoardTargetPlan: Equatable {
    let boardID: String
    let revisionID: String
    let targetKeysByStepID: [String: [WorkoutActivitySegmentKey]]
    let resolvedTargets: [WorkoutActivitySegmentKey: ResolvedBoardTarget]
    func renderTarget(forStepID stepID: String, on board: BoardRevision) throws -> WorkoutBoardRenderTarget?
}
enum WorkoutBoardTargetPlanningError: LocalizedError, Equatable {
    case missingFrozenTarget(WorkoutActivitySegmentKey)
    case boardMismatch(expected: String, actual: String)
    case staleBoardRevision(expected: String, actual: String)
    case invalidFrozenPresentation(stepID: String, positionID: String, presentationID: String)
    case invalidFrozenModelHash(stepID: String, presentationID: String)
    case incompatibleStepConfigurations(stepID: String)
    case unresolved(key: WorkoutActivitySegmentKey, error: ContactResolutionError)
}
```

- [ ] **Step 1: Write the RED preparation API and result matrix.** Load the real Plateau Task 13 package. Keep `@State private var targetSelections = WorkoutBoardTargetSelections()` in preparation UI and pass that exact value to every planner call.

| Requirements / explicit selection input | Exact output or error |
| --- | --- |
| `edge-18`, exact 15, empty selections | `.ready`; key maps to position/presentation `depth-15mm` |
| `edge-18`, no depth, empty selections | `.choiceRequired` with one choice and options `depth-18mm`, `depth-15mm`, `depth-10mm` in authored position order; selection subscript remains `nil` |
| same broad requirement, `selections[key] == "depth-10mm"` | `.ready`; key maps to `depth-10mm` |
| same broad requirement, `selections[key] == "missing"` | `.unresolved(key:error:.invalidExplicitPosition(positionID:"missing"))` |
| `edge-18`, exact 12 | `.unresolved(key:error:.noMatches)` |
| self-selected/no board requirement | `.ready`; no target key is created |
| frozen plan with the required map entry removed | `renderTarget` throws `.missingFrozenTarget(key)` |

```swift
func testBroadDepthReturnsOrderedChoicesWithoutImplicitSelection() throws {
    let f = try plateauPreparationFixture(depth: nil)
    let result = try WorkoutBoardTargetPlanner.prepare(
        sessionSteps: f.steps,
        board: f.board,
        selections: .init()
    )
    guard case .choiceRequired(let choices) = result else { return XCTFail("expected choiceRequired") }
    XCTAssertEqual(choices.map(\.key), [f.key])
    XCTAssertEqual(choices[0].options.map(\.positionID), ["depth-18mm", "depth-15mm", "depth-10mm"])
}
```

Add UI RED `testAmbiguousPreparationRequiresExplicitChoice`: launch `choice/ambiguous-choice/production` with validated Plateau inputs, assert `workout.configuration.choice.depth-18mm`, `.depth-15mm`, and `.depth-10mm` appear in that order, no choice is selected, and `workout.configuration.continue` remains disabled until explicitly selecting depth 15.

- [ ] **Step 2: Write direct per-step validation tests.**

| A/B difference in one step | Exact preparation/render result |
| --- | --- |
| no identity difference; contacts left/right | ready, then union `{left,right}` |
| `positionID` only | `.incompatibleStepConfigurations(stepID:"work")` |
| `presentationID` only | `.incompatibleStepConfigurations(stepID:"work")` |
| `modelSHA256` and therefore full `BoardModelKey` only | `.incompatibleStepConfigurations(stepID:"work")` |
| `boardID` only | `.boardMismatch(expected:f.board.id, actual:"wrong.board")` before union |
| `revisionID` only | `.staleBoardRevision(expected:f.board.revisionID, actual:"stale-revision")` before union |

```swift
func testRenderTargetRejectsDifferentPresentationWithinStep() throws {
    let f = try twoSegmentPlanFixture()
    let plan = f.replacingSecondTarget(presentationID: "depth-10mm")
    XCTAssertThrowsError(try plan.renderTarget(forStepID: "work", on: f.board)) {
        XCTAssertEqual($0 as? WorkoutBoardTargetPlanningError, .incompatibleStepConfigurations(stepID: "work"))
    }
}
```

- [ ] **Step 3: Run RED.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/WorkoutBoardTargetPlanTests -only-testing:HangTenUITests/BoardConfigurationUITests/testAmbiguousPreparationRequiresExplicitChoice
```

Expected: planning/render APIs absent.

- [ ] **Step 4: Implement complete preparation plus the post-resolution pass.** Iterate session steps and their target-bearing segments in authored order. For each key call the unqualified runtime resolver first. Store `.resolved` immediately. For `.positionChoiceRequired`, append the ordered candidates when the selection subscript is nil; otherwise call the runtime `positionID:` overload and wrap any `ContactResolutionError` as `.unresolved(key:error:)`. Return all choices together and no partial plan; once no choices remain, require one resolved entry for every targeted key. Before constructing `.ready`, group those targets by step and compare `boardID`, `revisionID`, `positionID`, `presentationID`, `modelSHA256`, and descriptor-derived `BoardModelKey`; throw `.boardMismatch`, `.staleBoardRevision`, or `.incompatibleStepConfigurations` as the table specifies. `renderTarget` repeats this defense for decoded/injected plans. Only a group whose complete identity set has count one may union contact IDs.

```swift
for (stepID, keys) in targetKeysByStepID {
    let targets = try keys.map { key -> ResolvedBoardTarget in
        guard let target = resolvedTargets[key] else { throw WorkoutBoardTargetPlanningError.missingFrozenTarget(key) }
        return target
    }
    guard Set(targets.map(WorkoutBoardTargetIdentity.init)).count <= 1 else {
        throw WorkoutBoardTargetPlanningError.incompatibleStepConfigurations(stepID: stepID)
    }
}
```

- [ ] **Step 5: Implement strict render validation.** Check plan board/revision, each required key, position→presentation relation, presentation existence, and descriptor hash. Rerun identity equality, then union frozen contact IDs. Never resolve requirements.

- [ ] **Step 6: Build choice UI/launch ordering and its DEBUG slice.** Paywall→weight→hand→prepare→sensor→setup. No preselection; Continue requires every choice. Cancel changes no timer/audio/sensor/date. Errors show `workout.configurationUnavailable`. The DEBUG `choice/ambiguous-choice` route consumes Task 1's validated board target only to establish the real Plateau package, initializes `WorkoutBoardTargetSelections()` empty, calls the real broad `edge-18` resolver path, and renders the production preparation view without a persisted or user-visible synthetic workout. After a real tap updates `targetSelections` and re-preparation returns `.ready`, expose DEBUG `review.workflow.choice-selected` with value `depth-15mm`; it is absent before selection and in Release.

- [ ] **Step 7: Run GREEN.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/WorkoutBoardTargetPlanTests -only-testing:HangTenTests/WorkoutTimelineTests -only-testing:HangTenUITests/WorkoutPaywallUITests
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenUITests/BoardConfigurationUITests/testAmbiguousPreparationRequiresExplicitChoice
```

Expected: preparation and all six per-step identity rows pass.

- [ ] **Step 8: Commit and push.**

```bash
rtk git add HangTen/Models/WorkoutBoardTargetPlan.swift HangTen/Views/WorkoutConfigurationPreparationView.swift HangTen/Views/WorkoutAccessGate.swift HangTen/Views/RootView.swift HangTenTests/WorkoutBoardTargetPlanTests.swift HangTenUITests/BoardConfigurationUITests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: freeze workout board targets"
rtk git push
```

**Review checkpoint:** Confirm render has no resolver, missing keys remain detectable, and union follows full identity equality.

### Task 4: Setup Reducer and Exact Keyed Readiness

**Files:**
- Create: `HangTen/Models/WorkoutSetupGate.swift`
- Create: `HangTenTests/WorkoutSetupGateTests.swift`
- Modify: `HangTen/Views/RootView.swift:1710-1870`
- Modify: `HangTen.xcodeproj/project.pbxproj:1-1015`

**Interfaces:**

```swift
enum WorkoutSetupModelReadiness: Equatable {
    case loading(BoardModelConfigurationIdentity)
    case ready(BoardModelConfigurationIdentity)
    case unavailable(BoardModelConfigurationIdentity)
}
enum WorkoutSetupDestinationAction: Equatable {
    case initial
    case restart
    case naturalBoundary
    case seek
    case jump
    case rewind
    case skip
    case resume
}
struct WorkoutSetupContinuation: Equatable {
    let action: WorkoutSetupDestinationAction
    let targetElapsed: TimeInterval
    let wasRunning: Bool
}
enum WorkoutSetupStage: Equatable {
    case previewDuringRest
    case waitNow
}
enum WorkoutSetupRequestError: LocalizedError, Equatable {
    case boardMismatch(expected: String, actual: String)
    case staleRevision(expected: String, actual: String)
    case invalidPositionPresentation(positionID: String, presentationID: String)
    case missingModelHash(presentationID: String)
    case modelHashMismatch(expected: String, actual: String)
}
struct WorkoutSetupRequest: Identifiable, Equatable {
    let target: ResolvedBoardTarget
    let modelIdentity: BoardModelConfigurationIdentity
    let boundaryElapsed: TimeInterval
    let continuation: WorkoutSetupContinuation
    var id: BoardModelConfigurationIdentity { modelIdentity }
    init(
        target: ResolvedBoardTarget,
        on board: BoardRevision,
        boundaryElapsed: TimeInterval,
        continuation: WorkoutSetupContinuation
    ) throws
}
struct WorkoutSetupGate: Equatable { let request: WorkoutSetupRequest; var readiness: WorkoutSetupModelReadiness }
enum WorkoutSetupGateState: Equatable { case none; case preview(WorkoutSetupGate); case waiting(WorkoutSetupGate) }
enum WorkoutSetupGateEffect: Equatable {
    case noAction
    case blockedUntilReady
    case stopAudio
    case requestInitialCountdown
    case requestSkipCountdown(targetElapsed: TimeInterval)
    case resumeRunning(targetElapsed: TimeInterval)
    case remainPaused(targetElapsed: TimeInterval)
}
extension WorkoutSessionState {
    mutating func stageSetup(
        _ request: WorkoutSetupRequest,
        stage: WorkoutSetupStage,
        at uptime: TimeInterval
    ) -> WorkoutSetupGateEffect
    mutating func receiveSetupModelEvent(_ event: BoardModelLoadEvent) -> Bool
    mutating func confirmSetup(at uptime: TimeInterval) -> WorkoutSetupGateEffect
}
```

Add stored `private(set) var setupGateState: WorkoutSetupGateState = .none` and `private(set) var confirmedModelIdentity: BoardModelConfigurationIdentity?` directly to the existing `WorkoutSessionState`; the extension above is the exact callable API used by Tasks 5–7.

- [ ] **Step 1: Write the RED request/readiness matrix.** Build requests with `WorkoutSetupRequest(target:on:boundaryElapsed:continuation:)`, never by memberwise initialization. The constructor requires matching board/revision, an authored position whose presentation is the target presentation, a model descriptor hash, and target hash equality; each failed guard throws its named `WorkoutSetupRequestError`. For a valid depth-15 request, none/loading, wrong board, wrong presentation, wrong hash, wrong position, exact unavailable, exact cancelled, and late depth-18 after a depth-15 request all leave Ready disabled and make `confirmSetup(at:)` return `.blockedUntilReady`. Only exact depth-15 `.ready` enables confirmation.

- [ ] **Step 2: Write the RED continuation table.** Use this one value for every entry path; `targetElapsed` is the exact authored destination and `wasRunning` is captured before staging.

| Action | targetElapsed | wasRunning | Exact post-confirmation effect |
| --- | ---: | --- | --- |
| initial | 0 | false | `.requestInitialCountdown` |
| restart | 0 | false | `.requestInitialCountdown` |
| naturalBoundary | 30 | true | `.resumeRunning(targetElapsed:30)` |
| naturalBoundary | 30 | false | `.remainPaused(targetElapsed:30)` |
| seek | 45 | true | `.resumeRunning(targetElapsed:45)` |
| jump | 45 | true | `.resumeRunning(targetElapsed:45)` |
| rewind | 10 | false | `.remainPaused(targetElapsed:10)` |
| skip | 45 | true | `.requestSkipCountdown(targetElapsed:45)` |
| resume | 45 | true | `.resumeRunning(targetElapsed:45)` |
| resume | 45 | false | `.remainPaused(targetElapsed:45)` |

- [ ] **Step 3: Run RED.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/WorkoutSetupGateTests
```

Expected: gate/readiness APIs absent.

- [ ] **Step 4: Implement request construction and identity/event reduction.** Locate the target's exact position and presentation on `board`, require model media, compare the descriptor hash to `target.modelSHA256`, and construct `BoardModelConfigurationIdentity(key:BoardModelKey(boardID:presentationID:modelSHA256:),positionID:)` from descriptor data. `stageSetup(.previewDuringRest)` preserves authored time and returns `.noAction`; `stageSetup(.waitNow)` clamps to `boundaryElapsed`, clears active countdown/running state, preserves matching preview readiness, and returns `.stopAudio` unless this exact identity was already confirmed during preview, in which case it dispatches the continuation immediately. `receiveSetupModelEvent` mutates only when the entire identity equals the active request; exact cancelled/unavailable becomes `.unavailable`, while every stale event returns false without mutation.

- [ ] **Step 5: Guard confirmation and dispatch the single continuation contract.**

```swift
guard case .ready(let identity) = gate.readiness, identity == gate.request.modelIdentity else {
    return .blockedUntilReady
}
```

Only this branch may update `confirmedModelIdentity`. Confirmation during preview returns `.noAction` and keeps authored rest running; waiting confirmation clears the gate and maps action exactly as the RED table specifies. A later `stageSetup(.waitNow)` for an already-confirmed exact identity clears the gate and returns the same continuation effect without showing a second prompt.

- [ ] **Step 6: Run GREEN.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/WorkoutSetupGateTests -only-testing:HangTenTests/BoardConfigurationPresentationTests
```

Expected: request failures, nine readiness cases, and all ten continuation rows pass.

- [ ] **Step 7: Commit and push.**

```bash
rtk git add HangTen/Models/WorkoutSetupGate.swift HangTen/Views/RootView.swift HangTenTests/WorkoutSetupGateTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: require exact model readiness for setup"
rtk git push
```

**Review checkpoint:** Trace Ready to reducer; prove no view Boolean bypasses keyed readiness.

### Task 5: Exact Rest-Boundary Timing and Audio

**Files:**
- Create: `HangTenTests/WorkoutSetupBoundaryTests.swift`
- Modify: `HangTen/Models/WorkoutTimeline.swift:238-245,421-530`
- Modify: `HangTen/Views/RootView.swift:1398-1430,1601-1870,1876-2310,3170-3290`
- Modify: `HangTen.xcodeproj/project.pbxproj:1-1015`

**Interfaces:**

```swift
struct WorkoutConfigurationBoundary: Equatable {
    let sourceStepID: String?
    let destinationKey: WorkoutActivitySegmentKey
    let boundaryElapsed: TimeInterval
    let source: WorkoutBoardRenderTarget?
    let destination: WorkoutBoardRenderTarget
}
enum WorkoutConfigurationTransitionError: LocalizedError, Equatable {
    case unsupportedTransition(fromPositionID: String, toPositionID: String)
    case transitionDoesNotRequireSetup(
        fromPositionID: String,
        toPositionID: String,
        actual: ResolvedBoardPositionTransitionKind
    )
}
enum WorkoutConfigurationPlaybackError: LocalizedError, Equatable {
    case planning(WorkoutBoardTargetPlanningError)
    case request(WorkoutSetupRequestError)
    case transition(WorkoutConfigurationTransitionError)
}
extension WorkoutTimeline {
    func nextConfigurationBoundary(
        after committedElapsed: TimeInterval,
        through sampledElapsed: TimeInterval,
        frozenPlan: WorkoutBoardTargetPlan,
        on board: BoardRevision
    ) throws -> WorkoutConfigurationBoundary?
    func configurationPreview(
        enteringRestStepID restStepID: String,
        frozenPlan: WorkoutBoardTargetPlan,
        on board: BoardRevision
    ) throws -> WorkoutConfigurationBoundary?
}
```

`WorkoutAudioCueAction` gains `.stop`. `WorkoutView` adds exact paths `private func stageRestPreview(enteringRestStepID: String, at uptime: TimeInterval)`, `private func processConfigurationBoundary(after committedElapsed: TimeInterval, through sampledElapsed: TimeInterval, at uptime: TimeInterval)`, and `private func stageBoundary(_ boundary: WorkoutConfigurationBoundary, at uptime: TimeInterval) throws`. All consume the frozen plan/current board or a boundary already validated from them; none accepts a keys-only dictionary. `stageBoundary` captures `wasRunning = sessionState.activeStartUptime != nil` before any `.waitNow` mutation and constructs `WorkoutSetupContinuation(action:.naturalBoundary,targetElapsed:boundary.boundaryElapsed,wasRunning:wasRunning)`.

- [ ] **Step 1: Write the RED rest and no-rest timing matrix.** Use Plateau Task 13 targets with exact model hashes.

| Timeline / sample | Exact result |
| --- | --- |
| work18 `[0,20)`, rest `[20,30)`, work15 at 30; tick 29.75 | depth-15 preview may be ready; rest continues and authored elapsed remains 29.75 |
| same; tick 30.25 | clamp `pausedElapsed` to 30, clear active/countdown, enter waiting, stop audio once, accrue zero after 30 |
| same; later tick 999 while waiting | authored elapsed, sensor, stopwatch, and all segment durations remain exactly 30-boundary values |
| same; confirm exact ready at 25 | record confirmed identity, return `.noAction`, and leave rest clock running |
| work18 `[0,10)`, work15 `[10,20)` with no rest; tick 10.25 | immediately clamp to 10 and enter waiting before any depth-15 work/sensor/stopwatch accrues; stop audio once |
| work18 `[0,10)`, work18 `[10,20)` | no gate; destination work begins normally |
| already-confirmed exact destination | no repeated gate; apply continuation at exact boundary |
| transition metadata is unsupported | set `workout.configurationUnavailable`; do not enter destination |
| running at a 30 boundary | request stores `.naturalBoundary`, exact `30`, `wasRunning:true`; exact-ready confirmation returns `.resumeRunning(targetElapsed:30)` |
| paused at a 30 boundary | request stores `.naturalBoundary`, exact `30`, `wasRunning:false`; exact-ready confirmation returns `.remainPaused(targetElapsed:30)` |

```swift
private struct WorkoutSetupBoundaryFixture {
    let board: BoardRevision
    let timeline: WorkoutTimeline
    let frozenPlan: WorkoutBoardTargetPlan
    let sourceKey: WorkoutActivitySegmentKey
    let destinationKey: WorkoutActivitySegmentKey
    let planDuration: TimeInterval
}
private func boundaryFixture(
    sourcePositionID: String,
    destinationPositionID: String,
    restDuration: TimeInterval
) throws -> WorkoutSetupBoundaryFixture

private struct BoundaryEntryCallProbe {
    private(set) var recorderCalls: [String: Int] = [:]
    private(set) var sensorCalls: [String: Int] = [:]
    private(set) var stopwatchCalls: [WorkoutActivitySegmentKey: Int] = [:]

    mutating func recorderWillConsume(stepID: String) { recorderCalls[stepID, default: 0] += 1 }
    mutating func sensorWillEnter(stepID: String) { sensorCalls[stepID, default: 0] += 1 }
    mutating func stopwatchWillStart(key: WorkoutActivitySegmentKey) { stopwatchCalls[key, default: 0] += 1 }
}

private struct WorkoutSetupBoundaryHarness {
    var sessionState: WorkoutSessionState
    var recorder: MotherboardWorkoutRecorder
    var stopwatches: [WorkoutActivitySegmentKey: WorkoutStopwatch]
    let fixture: WorkoutSetupBoundaryFixture
    private(set) var entryProbe = BoundaryEntryCallProbe()
    private(set) var lastScannedElapsed: TimeInterval
    private(set) var audioStopCount = 0

    init(fixture: WorkoutSetupBoundaryFixture, elapsed: TimeInterval, uptime: TimeInterval) {
        self.fixture = fixture
        self.sessionState = WorkoutSessionState(
            activeStartUptime: uptime - elapsed,
            pausedElapsed: 0,
            routineStartedAt: Date(timeIntervalSince1970: 1)
        )
        self.recorder = MotherboardWorkoutRecorder(configuration: .init(debounceDuration: 0))
        self.stopwatches = [fixture.sourceKey: WorkoutStopwatch(), fixture.destinationKey: WorkoutStopwatch()]
        self.lastScannedElapsed = elapsed
        self.entryProbe.recorderWillConsume(stepID: fixture.sourceKey.stepID)
        self.entryProbe.sensorWillEnter(stepID: fixture.sourceKey.stepID)
        self.entryProbe.stopwatchWillStart(key: fixture.sourceKey)
        self.stopwatches[fixture.sourceKey]?.start(at: uptime - elapsed)
        self.recorder.consume(
            MotherboardMeasurement(
                timestamp: Date(timeIntervalSince1970: elapsed - 0.75),
                sampleNumber: 1,
                batteryValue: 90,
                sensorLoadsKGF: [5, 0, 0, 0],
                aggregateLoadKGF: 5
            ),
            stepID: fixture.sourceKey.stepID,
            plannedActiveDuration: 10,
            workoutElapsed: elapsed - 0.75,
            isActive: true
        )
    }

    mutating func enterRest(stepID: String, at uptime: TimeInterval) throws -> WorkoutSetupGateEffect
    mutating func sample(through sampledElapsed: TimeInterval, at uptime: TimeInterval) throws -> WorkoutSetupGateEffect
    mutating func attemptDestinationEntry(at uptime: TimeInterval) {
        guard case .none = sessionState.setupGateState else { return }
        entryProbe.recorderWillConsume(stepID: fixture.destinationKey.stepID)
        entryProbe.sensorWillEnter(stepID: fixture.destinationKey.stepID)
        entryProbe.stopwatchWillStart(key: fixture.destinationKey)
        stopwatches[fixture.destinationKey]?.start(at: uptime)
    }
    mutating func receive(_ event: BoardModelLoadEvent) -> Bool { sessionState.receiveSetupModelEvent(event) }
    mutating func confirm(at uptime: TimeInterval) -> WorkoutSetupGateEffect { sessionState.confirmSetup(at: uptime) }
    func elapsed(at uptime: TimeInterval) -> TimeInterval {
        sessionState.currentElapsed(planDuration: fixture.planDuration, at: uptime)
    }
    func stopwatchElapsed(for key: WorkoutActivitySegmentKey, at uptime: TimeInterval) -> TimeInterval? {
        stopwatches[key]?.elapsed(at: uptime)
    }
    mutating func loadedDuration(for stepID: String) -> TimeInterval? {
        recorder.finish(at: sessionState.pausedElapsed)
            .first(where: { $0.stepID == stepID })?.actualLoadedDuration
    }
}

func testNoRestConfigurationChangeStopsBeforeDestinationWorkAccrues() throws {
    let fixture = try boundaryFixture(
        sourcePositionID: "depth-18mm",
        destinationPositionID: "depth-15mm",
        restDuration: 0
    )
    var harness = WorkoutSetupBoundaryHarness(fixture: fixture, elapsed: 9.75, uptime: 99.75)
    let effect = try harness.sample(through: 10.25, at: 100.25)
    harness.attemptDestinationEntry(at: 100.25)
    XCTAssertEqual(harness.elapsed(at: 100.25), 10)
    XCTAssertGreaterThan(harness.stopwatchElapsed(for: fixture.sourceKey, at: 100.25) ?? 0, 0)
    XCTAssertGreaterThan(harness.loadedDuration(for: fixture.sourceKey.stepID) ?? 0, 0)
    XCTAssertEqual(harness.entryProbe.recorderCalls[fixture.sourceKey.stepID], 1)
    XCTAssertEqual(harness.entryProbe.sensorCalls[fixture.sourceKey.stepID], 1)
    XCTAssertEqual(harness.entryProbe.stopwatchCalls[fixture.sourceKey], 1)
    XCTAssertEqual(harness.entryProbe.recorderCalls[fixture.destinationKey.stepID, default: 0], 0)
    XCTAssertEqual(harness.entryProbe.sensorCalls[fixture.destinationKey.stepID, default: 0], 0)
    XCTAssertEqual(harness.entryProbe.stopwatchCalls[fixture.destinationKey, default: 0], 0)
    XCTAssertFalse(harness.stopwatches[fixture.destinationKey]?.hasStarted ?? true)
    XCTAssertEqual(effect, .stopAudio)
    guard case .waiting = harness.sessionState.setupGateState else { return XCTFail("expected waiting") }
}
```

Implement the harness methods with the same production order: call the throwing timeline lookup; validate the board transition; build `WorkoutSetupRequest` from `boundary.destination.configuration`; reuse a matching preview request or stage a new request; capture `wasRunning` before staging; compute `boundaryUptime = uptime - max(0, sampledElapsed - boundary.boundaryElapsed)`; call `recorder.pause(at: boundary.boundaryElapsed)` and `pause(at: boundaryUptime)` on each running `WorkoutStopwatch` only when `.stopAudio` is returned; increment `audioStopCount`; never invoke any of the three destination-entry probes while the gate is waiting. `enterRest` calls `configurationPreview` then `stageSetup(request, stage:.previewDuringRest, at:uptime)`. The seeded source stopwatch, source load interval, and source probe counts make the negative destination assertions nonvacuous.

- [ ] **Step 2: Add explicit fail-closed frozen target tests.** Destination key exists in every fixture:

| Mutation | Exact result |
| --- | --- |
| required map entry missing | missingFrozenTarget→unavailable |
| stale revision | staleBoardRevision→unavailable |
| wrong descriptor hash | invalidFrozenModelHash→unavailable |
| mismatched position/presentation | invalidFrozenPresentation→unavailable |
| request constructor rejects exact destination | request error→unavailable |
| `transitionKind(18,15) == .unsupported` | unsupportedTransition→unavailable |

The boundary lookup itself performs throwing frozen render validation for both source and destination. Only unwrap its optional result; missing/stale/hash/presentation failures must reach the unavailable catch path:

```swift
do {
    guard let boundary = try timeline.nextConfigurationBoundary(
        after: committedElapsed,
        through: sampledElapsed,
        frozenPlan: frozenTargetPlan,
        on: board
    ) else { return }
    try stageBoundary(boundary, at: uptime)
} catch let error as WorkoutBoardTargetPlanningError {
    configurationPlaybackError = .planning(error)
    audioCoach.stop()
} catch let error as WorkoutSetupRequestError {
    configurationPlaybackError = .request(error)
    audioCoach.stop()
} catch let error as WorkoutConfigurationTransitionError {
    configurationPlaybackError = .transition(error)
    audioCoach.stop()
}
```

Every catch also clears the stale scene, sets the visible accessibility identifier `workout.configurationUnavailable`, and returns before recorder/sensor/stopwatch destination entry. Optional `try` and keys-only comparison are forbidden here.

- [ ] **Step 3: Write RED rest-preview, audio, and time tests.** At entry to rest `[20,30)`, `configurationPreview` returns nil for 18→18 and returns the exact depth-15 destination/boundary30 for 18→15. The latter stages `.previewDuringRest`. Exact ready at elapsed24 followed by `confirmSetup` at25 returns `.noAction`, leaves `activeStartUptime` nonnil, and makes `sessionState.currentElapsed(planDuration: fixture.planDuration, at: 115) == 25`. Without early confirmation, expiry promotion captures the prior running state, calls `.waitNow` with `.naturalBoundary/30/true`, preserves `.ready(exactIdentity)`, clamps30, and returns `.stopAudio`; exact-ready confirmation then returns `.resumeRunning(targetElapsed:30)`. In the parallel paused fixture, expiry captures `false`, stores `.naturalBoundary/30/false`, and confirmation returns `.remainPaused(targetElapsed:30)`. Early confirmation still enters the `.waitNow` path at expiry and immediately dispatches `.resumeRunning(targetElapsed:30)`. Stop calls coach once; waiting yields no audio moment; short-interval scheduling stops before gate; sensor rejects waiting; stopwatch pauses at boundary30.

- [ ] **Step 4: Run RED.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/WorkoutSetupBoundaryTests -only-testing:HangTenTests/WorkoutAudioCuePolicyTests
```

Expected: boundary/failure propagation/stop absent.

- [ ] **Step 5: Implement full-identity boundaries, transition validation, and rest preview.** For each destination work step, choose its first authored `targetKeysByStepID` key only as the stable boundary key, then call `frozenPlan.renderTarget` for the nearest preceding work step and destination. Compare `WorkoutBoardTargetIdentity` values (board, revision, position, presentation, model key, hash), never keys or contact IDs. Thus 18→18 returns nil even if highlights differ, while 18→15 returns a boundary. `nextConfigurationBoundary` returns the first change satisfying `committedElapsed < boundaryElapsed && boundaryElapsed <= sampledElapsed`, including direct no-rest work at 10. `configurationPreview` locates the next work after the exact entered rest, performs the same throwing source/destination validation/comparison, and returns its future boundary only for a change.

`stageBoundary` then calls `board.transitionKind(from:source.configuration.positionID,to:destination.configuration.positionID)` and accepts exactly `.setupRequired`; `.unsupported` throws `.unsupportedTransition`, while an unexpected `.same` or `.seamless` boundary throws `.transitionDoesNotRequireSetup`. Before calling `.waitNow`, capture the running bit and construct the request exactly:

```swift
let wasRunning = sessionState.activeStartUptime != nil
let continuation = WorkoutSetupContinuation(
    action: .naturalBoundary,
    targetElapsed: boundary.boundaryElapsed,
    wasRunning: wasRunning
)
let request = try WorkoutSetupRequest(
    target: boundary.destination.configuration,
    on: board,
    boundaryElapsed: boundary.boundaryElapsed,
    continuation: continuation
)
applySetupEffect(sessionState.stageSetup(request, stage: .waitNow, at: uptime))
```

Call `stageRestPreview` from the existing step-ID change path exactly when the entered step is rest. It stages `.previewDuringRest` without modifying clock/audio/recorder/stopwatches. At expiry, `processConfigurationBoundary` first captures the current `wasRunning`, then constructs the boundary request with `.naturalBoundary`, the exact boundary elapsed, and that captured value. If a preview exists, require the same target/model identity and boundary, preserve only its loading/ready state while replacing its continuation with the just-captured request, and call `.waitNow`; any identity/boundary mismatch fails unavailable. This means pausing during rest produces the paused continuation even if preview began running. If no preview exists (including no-rest), use the same request constructor. Gate every destination work, audio, sensor, and stopwatch path while waiting.

- [ ] **Step 6: Run GREEN.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/WorkoutSetupBoundaryTests -only-testing:HangTenTests/WorkoutAudioCuePolicyTests -only-testing:HangTenTests/WorkoutSessionStateTests -only-testing:HangTenTests/WorkoutTimelineTests
```

Expected: 18→18/18→15 rest and no-rest rows, running/paused natural-boundary continuations, preview/early-confirm/promotion rows, four frozen-planning failures, request rejection, unsupported transition, and audio/time tests pass.

- [ ] **Step 7: Commit and push.**

```bash
rtk git add HangTen/Models/WorkoutTimeline.swift HangTen/Views/RootView.swift HangTenTests/WorkoutSetupBoundaryTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: pause workout time at setup boundaries"
rtk git push
```

**Review checkpoint:** Search boundary path for optional `try`; require zero matches and propagation to unavailable with stopped audio.

### Task 6: Navigation, Frozen Rendering, and Confirmation UI

**Files:**
- Create: `HangTen/Views/WorkoutSetupConfirmationView.swift`
- Create: `HangTenTests/WorkoutConfigurationNavigationTests.swift`
- Modify: `HangTen/Models/BoardConfigurationReviewLaunch.swift` (DEBUG injector)
- Modify: `HangTen/Views/BoardMapView.swift:490-650`
- Modify: `HangTen/Views/RootView.swift:1876-3500`
- Modify: `HangTenUITests/BoardConfigurationUITests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj:1-1015`

**Interfaces:** Consumes Tasks 3–5. Produces `WorkoutSetupCopy.instruction(for:on:) -> String?`; playback has no resolver or picker. Initial entry, restart, natural boundary, seek, jump, rewind, skip, and resume all call this single `WorkoutView` entry point with the Task 4 continuation value:

```swift
private func navigate(
    to destinationStepID: String,
    continuation: WorkoutSetupContinuation,
    at uptime: TimeInterval
)
#if DEBUG
enum BoardConfigurationReviewEventInjector {
    static func events(
        afterSceneApplied exactIdentity: BoardModelConfigurationIdentity,
        alternateIdentity: BoardModelConfigurationIdentity,
        mode: BoardConfigurationReviewLoadMode
    ) -> [BoardModelLoadEvent]
}
enum BoardConfigurationReviewEntry {
    case navigate(stepID: String, continuation: WorkoutSetupContinuation)
    case enterRest(stepID: String, entryUptime: TimeInterval, expirySample: TimeInterval?)
    case naturalBoundary(committedElapsed: TimeInterval, sampledElapsed: TimeInterval)
}
struct BoardConfigurationReviewScenario {
    let board: BoardRevision
    let frozenPlan: WorkoutBoardTargetPlan
    let sessionState: WorkoutSessionState
    let entry: BoardConfigurationReviewEntry
    let injectedEvents: [BoardModelLoadEvent]
    static func make(
        launch: BoardConfigurationReviewLaunch,
        target: BoardConfigurationReviewTarget
    ) throws -> BoardConfigurationReviewScenario
}
#endif
```

- [ ] **Step 1: Write the RED unified navigation matrix.** Give every row an exact `WorkoutSetupContinuation(action:targetElapsed:wasRunning:)` and assert both gate state and continuation effect.

| Entry / frozen destination | Input continuation | Exact result |
| --- | --- | --- |
| initial / 18, no confirmed identity | initial, 0, false | wait; exact-ready confirmation requests initial countdown |
| restart / confirmed 18 | restart, 0, false | no prompt; request initial countdown |
| natural boundary / confirmed 18 | naturalBoundary, 30, true | no prompt; resume running at 30 |
| natural boundary / new 15 | naturalBoundary, 30, false | wait; exact-ready confirmation remains paused at 30 |
| seek / new 15 | seek, 45, true | wait; exact-ready confirmation resumes running at 45 |
| jump / new 10 | jump, 45, true | wait; exact-ready confirmation resumes running at 45 |
| rewind / new 18 | rewind, 10, false | wait; exact-ready confirmation remains paused at 10 |
| skip / new 15 | skip, 45, true | wait; exact-ready confirmation requests skip countdown at 45 |
| resume / new 15 | resume, 45, true | wait; exact-ready confirmation resumes running at 45 |
| resume / new 15 | resume, 45, false | wait; exact-ready confirmation remains paused at 45 |
| any entry / unsupported transition | matching action/time/run state | unavailable, audio stopped, no destination entry |
| interruption while waiting for 15 | unchanged continuation | still waiting at the same target/time; no accrual |

Add UI RED methods `testSetupReadyRequiresExactIdentity` and `testEveryInjectedFailureModeFailsClosed`. The first launches `setup/initial-setup/exact-ready`, asserts `workout.setup.ready` is disabled until `review.model.ready` appears, verifies the ready element's full target-identity value, then asserts Ready enabled. The second independently launches `wrong-identity`, `missing-resource`, `hash-mismatch`, `cancelled`, and `unavailable`; every row keeps Ready disabled, clears stale content, shows `workout.configurationUnavailable` when the exact request fails, and exposes respectively `review.model.failure.wrong-identity`, `review.model.failure.missing-resource`, `review.model.failure.hash-mismatch`, `review.model.failure.cancelled`, or `review.model.failure.unavailable`.

- [ ] **Step 2: Write frozen rendering/Ready tests.** Rest/current use `renderTarget` presentation/position/unioned contacts; board-detail selection cannot alter them. Ready disabled for loading/unavailable/stale and enabled only exact ready; disabled tap has no effect.

- [ ] **Step 3: Run RED.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/WorkoutConfigurationNavigationTests -only-testing:HangTenUITests/BoardConfigurationUITests/testSetupReadyRequiresExactIdentity -only-testing:HangTenUITests/BoardConfigurationUITests/testEveryInjectedFailureModeFailsClosed
```

Expected: navigation routing/setup view absent.

- [ ] **Step 4: Implement one destination function and deterministic setup injection.** The destination function obtains the destination step, calls the throwing frozen `renderTarget`, verifies transition metadata, constructs `WorkoutSetupRequest(target:on:boundaryElapsed:continuation:)`, compares the request identity with the confirmed identity, and either dispatches the continuation immediately or calls `stageSetup(request, stage: .waitNow, at: uptime)`. Initial, restart, natural boundary, seek, jump, rewind, skip, and both running/paused resume call this exact function; remove their separate setup/timer mutations. Catch every planning/request/transition error as `workout.configurationUnavailable`, stop audio, and do not enter the destination. No resolver/highlight resolver.

For DEBUG setup states, resolve the supplied real target and exact identity through Task 1, then construct the production request/view. `production` bypasses injection. Only after the component reports pose, suspension, highlight, and accessibility applied: `exact-ready` emits loading then exact ready; `wrong-identity` emits alternate real depth-10 ready plus `review.model.failure.wrong-identity`; `missing-resource` emits exact unavailable plus its diagnostic; `hash-mismatch` proves a same-board/presentation/position hash of 64 `f` characters is rejected and then emits exact unavailable; `cancelled` emits exact cancelled; `unavailable` emits exact unavailable. Failure identifiers are `review.model.failure.missing-resource`, `.hash-mismatch`, `.cancelled`, and `.unavailable`. Each route derives the real production target once, uses a generation token to reject out-of-order callbacks, and never enables `review.model.ready` for a mismatched/failing event. Add DEBUG `review.rotateLandscape` for `rest-wait`; it changes geometry without recreating session/gate/plan and exposes `review.workflow.rotation-landscape` only from the completed scene-geometry callback.

Build W04–W18 through `BoardConfigurationReviewScenario.make`, using real Plateau Task 13 targets and the production functions below. No two workflow-state cases may alias the same scenario:

| Case/state | Frozen plan and session seed | Exact production entry/request | Injection and required completion/failure signal |
| --- | --- | --- | --- |
| W04 `initial-setup` | one depth-15 work target; paused at 0; no confirmed identity | `navigate(stepID:"work-15", continuation:.init(action:.initial,targetElapsed:0,wasRunning:false), at:100)` | exact ready; tap Ready → `review.workflow.initial-countdown` |
| W05 `rest-preview` | work18 `[0,20)`, rest `[20,30)`, work15; running at 20 | `.enterRest(stepID:"rest",entryUptime:120,expirySample:nil)` calls `stageRestPreview` | exact ready; tap Ready at 25 → `review.workflow.rest-preview-confirmed` while elapsed keeps running |
| W06 `rest-wait` | same frozen plan; running at 29.75 | `.enterRest(stepID:"rest",entryUptime:129.75,expirySample:30.25)` calls preview then `processConfigurationBoundary(after:29.75,through:30.25,at:130.25)` | exact ready; tap Ready → `review.workflow.rest-wait-resumed` at 30 |
| W07 `natural-boundary` | work18 `[0,10)`, work15; running at 9.75 | `.naturalBoundary(committedElapsed:9.75,sampledElapsed:10.25)` | exact ready; tap Ready → `review.workflow.natural-boundary-resumed` at 10 |
| W08 `skip` | depth18 current plus depth15 destination; running at 20 | `navigate("work-15", .init(action:.skip,targetElapsed:45,wasRunning:true), at:120)` | exact ready; tap Ready → `review.workflow.skip-countdown` at 45 |
| W09 `jump` | depth18 current plus depth15 destination; running at 20 | `navigate("work-15", .init(action:.jump,targetElapsed:45,wasRunning:true), at:120)` | exact ready; tap Ready → `review.workflow.jump-resumed` at 45 |
| W10 `rewind` | depth15 current plus depth18 destination; paused at 45 | `navigate("work-18", .init(action:.rewind,targetElapsed:10,wasRunning:false), at:145)` | exact ready; tap Ready → `review.workflow.rewind-paused` at 10 |
| W11 `restart` | depth15 target; first stage/receive exact ready/confirm to seed `confirmedModelIdentity`; paused at 45 | `navigate("work-15", .init(action:.restart,targetElapsed:0,wasRunning:false), at:145)` | no duplicate gate; `review.workflow.restart-countdown` at 0 |
| W12 `resume-paused` | depth18 current plus depth15 destination; paused at 45 | `navigate("work-15", .init(action:.resume,targetElapsed:45,wasRunning:false), at:145)` | exact ready; tap Ready → `review.workflow.resume-paused` at 45 |
| W13 `resume-running` | depth18 current plus depth15 destination; running at 45 | `navigate("work-15", .init(action:.resume,targetElapsed:45,wasRunning:true), at:145)` | exact ready; tap Ready → `review.workflow.resume-running` at 45 |
| W14 `initial-setup` + wrong identity | one depth15 target; paused at 0 | W04 request | alternate real depth10 ready only → `review.model.failure.wrong-identity`; Ready remains disabled |
| W15 `unavailable` + missing resource | one depth15 target; paused at 0 | W04 request | exact `.unavailable` from missing-resource loader → `review.model.failure.missing-resource` |
| W16 `unavailable` + hash mismatch | one depth15 target; paused at 0 | W04 request | wrong-hash ready is ignored, then exact unavailable → `review.model.failure.hash-mismatch` |
| W17 `unavailable` + cancelled | one depth15 target; paused at 0 | W04 request | exact cancelled → `review.model.failure.cancelled` |
| W18 `unavailable` + unavailable | one depth15 target; paused at 0 | W04 request | exact unavailable → `review.model.failure.unavailable` |

The `review.workflow.*` element is DEBUG-only, has value `boardID|presentationID|positionID|modelSHA256|targetElapsed|runState`, and appears only after the corresponding real `WorkoutSetupGateEffect` has been applied. Format `targetElapsed` with `String(format:"%.2f", locale:Locale(identifier:"en_US_POSIX"), targetElapsed)` and set `runState` from the continuation to exactly `running` or `paused`; for example W07 ends in `|10.00|running`. Unit tests call `BoardConfigurationReviewScenario.make` for all fifteen rows and assert distinct entry values, frozen topology, continuation, starting run state, injected events, exact signal value, and final effect; UI tests assert the matching completion/failure signal.

- [ ] **Step 5: Implement confirmation UI.** Lock map to frozen IDs/no picker. Plateau copy is `Set edge to 15 mm`; other copy uses package presentation name; missing evidence unavailable. Bind Ready directly to exact readiness. Add `workout.setup`, `workout.setup.ready`, and equipment-only loading/ready/unavailable previews. Under DEBUG, publish the table's exact `review.workflow.*` signal only from the post-effect callback, never from the button tap or injected event itself; keep every signal and review control out of Release.

- [ ] **Step 6: Run GREEN.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/WorkoutConfigurationNavigationTests -only-testing:HangTenTests/WorkoutSetupGateTests -only-testing:HangTenTests/WorkoutSetupBoundaryTests -only-testing:HangTenTests/WorkoutBoardTargetPlanTests
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenUITests/BoardConfigurationUITests/testSetupReadyRequiresExactIdentity -only-testing:HangTenUITests/BoardConfigurationUITests/testEveryInjectedFailureModeFailsClosed
```

Expected: all twelve navigation rows and frozen rendering/readiness pass.

- [ ] **Step 7: Commit and push.**

```bash
rtk git add HangTen/Models/BoardConfigurationReviewLaunch.swift HangTen/Views/WorkoutSetupConfirmationView.swift HangTen/Views/BoardMapView.swift HangTen/Views/RootView.swift HangTenTests/WorkoutConfigurationNavigationTests.swift HangTenUITests/BoardConfigurationUITests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: gate configuration-aware workout navigation"
rtk git push
```

**Review checkpoint:** Search playback for resolver/highlight resolver/picker; require zero configuration-authority violations.

### Task 7: Frozen Map Activity Handoff

**Files:**
- Create: `HangTenTests/WorkoutFrozenTargetHandoffTests.swift`
- Modify: `HangTen/Models/AppStore.swift:425-520`
- Modify: `HangTen/Views/RootView.swift:3290-3390`
- Modify: `HangTenTests/AppStoreTests.swift:1320-1580`
- Modify: `HangTen.xcodeproj/project.pbxproj:1-1015`

**Interfaces:** Preserve both existing `markSessionComplete` overloads byte-for-byte at the call boundary; they continue invoking runtime metadata with its default `resolvedTargets:nil`. Add a distinct strict entry point used only by configuration-aware `WorkoutView`:

```swift
func markSessionComplete(
    _ plan: TrainingPlan,
    board: BoardRevision,
    stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval],
    startDate: Date,
    endDate: Date,
    selectedHandSide: WorkoutSide? = nil,
    handPreference: WorkoutSessionHandPreference? = nil,
    sessionSteps: [WorkoutStep]? = nil,
    session: WorkoutSessionRecord? = nil
)
func markSessionComplete(
    _ plan: TrainingPlan,
    startDate: Date,
    endDate: Date,
    selectedHandSide: WorkoutSide? = nil,
    handPreference: WorkoutSessionHandPreference? = nil,
    sessionSteps: [WorkoutStep]? = nil,
    session: WorkoutSessionRecord? = nil
)
@discardableResult
func markFrozenSessionComplete(
    _ plan: TrainingPlan,
    board: BoardRevision,
    stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval],
    startDate: Date,
    endDate: Date,
    selectedHandSide: WorkoutSide? = nil,
    handPreference: WorkoutSessionHandPreference? = nil,
    sessionSteps: [WorkoutStep]? = nil,
    resolvedTargets: [WorkoutActivitySegmentKey: ResolvedBoardTarget],
    session: WorkoutSessionRecord? = nil
) -> Bool
private func recordValidatedCompletion(
    plan: TrainingPlan,
    board: BoardRevision,
    metadata: WorkoutActivityMetadata,
    session: WorkoutSessionRecord?,
    startDate: Date,
    endDate: Date
)
```

- [ ] **Step 1: Write the RED compatibility/strict handoff matrix.** Use `CapturingWorkoutHistoryService` and `handoffFixture(positionID:)`.

| Caller | Frozen input | Exact result |
| --- | --- | --- |
| existing board overload | implicit nil | retains legacy resolution/recording behavior and uploads exactly as before |
| existing selected-board convenience overload | implicit nil | delegates to existing board overload; no frozen-map completeness requirement |
| `markFrozenSessionComplete`, Plateau15 | complete one-entry map | returns true; records 15 position/depth/presentation/actual hash |
| strict call after board-detail changes to10 | same frozen15 map | still records frozen15 |
| strict all-self-selected routine | complete empty nonnil map | returns true |
| strict targeted routine | missing required key | returns false; recording error; no session append/history/Health upload |
| strict targeted routine | stale target/hash | returns false; no persistence/upload |
| WorkoutView | frozen plan absent | `workout.configurationUnavailable`; strict method not called |

- [ ] **Step 2: Run RED.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/WorkoutFrozenTargetHandoffTests -only-testing:HangTenTests/AppStoreTests
```

Expected: strict entry point/handoff assertions are absent while legacy call sites still compile.

- [ ] **Step 3: Preserve legacy calls and implement the strict transaction.** Existing overload bodies continue calling `WorkoutActivityRecorder.metadata` without the optional argument, which is exactly `nil`; do not route them through completeness validation. `markFrozenSessionComplete` calls metadata first with the exact nonoptional dictionary. If runtime validation throws, set the recording error and return false before appending `WorkoutSessionRecord`, changing session history, or invoking `recordCompletion`. On success, pass the already-produced metadata into a private common persistence/upload helper, return true, and never normalize/rebuild the dictionary. `WorkoutView` requires `frozenTargetPlan`, calls only the strict method, and maps false to `workout.configurationUnavailable`.

```swift
let activityMetadata: WorkoutActivityMetadata
do {
    activityMetadata = try WorkoutActivityRecorder().metadata(
        for: plan,
        on: board,
        stopwatchDurations: stopwatchDurations,
        selectedHandSide: selectedHandSide,
        handPreference: handPreference,
        sessionSteps: sessionSteps,
        resolvedTargets: resolvedTargets,
        stepMeasurements: session?.steps ?? []
    )
} catch {
    setHealthAuthorizationError(error.localizedDescription, kind: .recording)
    return false
}
recordValidatedCompletion(plan: plan, board: board, metadata: activityMetadata, session: session,
                          startDate: startDate, endDate: endDate)
return true
```

- [ ] **Step 4: Prove setup waits excluded.** Session/Health use authored active interval; prior measurements remain; waiting measurements absent; no setup duration appears in segments.

- [ ] **Step 5: Run GREEN.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -only-testing:HangTenTests/WorkoutFrozenTargetHandoffTests -only-testing:HangTenTests/AppStoreTests -only-testing:HangTenTests/WorkoutActivityRecordingTests
```

Expected: both legacy nil rows and all six strict rows pass with the runtime suite.

- [ ] **Step 6: Commit and push.**

```bash
rtk git add HangTen/Models/AppStore.swift HangTen/Views/RootView.swift HangTenTests/WorkoutFrozenTargetHandoffTests.swift HangTenTests/AppStoreTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: record frozen workout board targets"
rtk git push
```

**Review checkpoint:** Compare object equality at every handoff; no key/target mutation.

### Task 8: Final Package, Legacy, Accessibility, and Simulator Acceptance

**Prerequisites:** Runtime Task 7 and package Task 18 complete; Task 18 includes Port10, Plateau13, ODR16, and native17 handoffs.

**Files:**
- Create (sole owner): `HangTenTests/Batch03WorkoutExperienceIntegrationTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj:1-1015`

**Mandatory resource preflight:** Before Step 1 writes any generated output and before any Task 8 build, re-read the validation skill/docs, derive the owner from `${PASEO_WORKTREE_PATH:-$PWD}`'s final component, and install the documented EXIT/INT/TERM cleanup trap. Register these exact owned paths in the pending/owned manifests before first use: `.context/DerivedData-task8-unit`, `.context/DerivedData-task8-ui`, `.context/DerivedData-task8-debug`, `.context/DerivedData-release`, `.context/DerivedData`, `.context/workout-raw.png`, `.context/workout-landscape.png`, and `.context/batch03-experience-review`. The simulator record is added pending-before-create/owned-after-create in Step 8. If trap/manifest setup fails, stop before running Step 1; never use global DerivedData.

- [ ] **Step 1: Add package-backed Port tests in the solely owned class.** Define these exact helpers:

```swift
private struct PortFixture {
    let board: BoardRevision
    let step: WorkoutStep
    let requirement: ContactRequirement
    let key: WorkoutActivitySegmentKey
    let plan: TrainingPlan
}
private func portCase(contactID: String, positionID: String) throws -> PortFixture
private func recordedSegment(
    fixture: PortFixture,
    target: ResolvedBoardTarget
) throws -> RecordedActivitySegment?
```

| Contact/position | Depth | Exact result |
| --- | --- | --- |
| jug-outer-rim/outer-upper | nil | primary, actual hash, `{}` |
| pinch-body/pinch-side | nil | primary, actual hash, `{}` |
| jug-outer-rim/outer-upper | exact10 | noMatches |
| pinch-body/pinch-side | exact10 | noMatches |

For success, record `[key:target]` and assert configuration position/presentation primary/effectiveDepths `{}`, selected ID, and descriptor hash.

```swift
func testPortUnmeasuredPinchRecordsEmptyDepthMapAndActualHash() throws {
    let f = try portCase(contactID: "pinch-body", positionID: "pinch-side")
    let target = try ContactResolver.resolveTarget([f.requirement], step: f.step, board: f.board, positionID: "pinch-side")
    XCTAssertEqual(target.effectiveDepths, [:])
    let snapshot = try XCTUnwrap(recordedSegment(fixture: f, target: target)?.target?.resolvedContactSnapshot)
    XCTAssertEqual(snapshot.configuration?.effectiveDepths, [:])
    XCTAssertEqual(snapshot.configuration?.presentationID, "primary")
    XCTAssertEqual(snapshot.modelSHA256, target.modelSHA256)
}
```

- [ ] **Step 2: Add immutable legacy snapshot tests in the same class.** Decode/round-trip: Port `pocket-30-two-finger-mono`, Plateau `blocker-edge-15`, Plateau `blocker-edge-10`. `legacySnapshotJSON(boardID:contactID:)` omits configuration. Assert nil configuration and exact unchanged requirement/contactIDs, never rewritten to current IDs.

- [ ] **Step 3: Register and run the package-backed acceptance class.** Add only `Batch03WorkoutExperienceIntegrationTests.swift` to the unit-test target, then run its exact selector. Tasks 1, 2, 3, and 6 already own `BoardConfigurationUITests` and every DEBUG route; Task 8 must not edit those files.

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -derivedDataPath .context/DerivedData-task8-unit -only-testing:HangTenTests/Batch03WorkoutExperienceIntegrationTests
```

Expected: both Port success rows, both invented-depth failures, and all three immutable legacy IDs pass against package Task 18.

- [ ] **Step 4: Run the completed UI ownership slices read-only.** Run the entire `BoardConfigurationUITests` class and require all six methods owned by Tasks 1/2/3/6, including identity-valued `review.model.ready` and production contact-reset assertions, to pass. Do not add or repair DEBUG/UI code in Task 8; route failures return to their owning task.

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -derivedDataPath .context/DerivedData-task8-ui -only-testing:HangTenUITests/BoardConfigurationUITests
```

- [ ] **Step 5: Verify DEBUG isolation before full acceptance.** Build Debug for simulator, then build Release for generic iOS Simulator and reject every string in the DEBUG-only families `HANGTEN_REVIEW_`, `BoardConfigurationReview`, and `review.model.` / `review.workflow.`, plus the existing standalone `review.rotateLandscape` control.

```bash
rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/DerivedData-task8-debug CODE_SIGNING_ALLOWED=YES
rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen -configuration Release -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/DerivedData-release CODE_SIGNING_ALLOWED=YES
rtk bash -c 'set -o pipefail; if LC_ALL=C /usr/bin/strings "$1" | /usr/bin/grep -E -- "HANGTEN_REVIEW_|BoardConfigurationReview|review\\.(model|workflow)\\.|review\\.rotateLandscape"; then exit 1; else status=$?; test "$status" -eq 1; fi' _ .context/DerivedData-release/Build/Products/Release-iphonesimulator/HangTen.app/HangTen
```

Expected: Release build succeeds, `strings` succeeds, `grep` returns exactly 1, no member of any of the three DEBUG-only families appears, and `review.rotateLandscape` is absent.

- [ ] **Step 6: Run focused final integration GREEN.**

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -derivedDataPath .context/DerivedData-task8-ui -only-testing:HangTenTests/Batch03WorkoutExperienceIntegrationTests -only-testing:HangTenTests/BoardConfigurationPresentationTests -only-testing:HangTenTests/CustomRoutineBoardSelectionTests -only-testing:HangTenTests/WorkoutBoardTargetPlanTests -only-testing:HangTenTests/WorkoutSetupGateTests -only-testing:HangTenTests/WorkoutSetupBoundaryTests -only-testing:HangTenTests/WorkoutConfigurationNavigationTests -only-testing:HangTenTests/WorkoutFrozenTargetHandoffTests -only-testing:HangTenTests/Batch03BoardModelTests -only-testing:HangTenUITests/BoardConfigurationUITests
```

Expected: Port four rows, three legacy IDs, reducers, native models, and UI pass.

- [ ] **Step 7: Run complete native regression.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -derivedDataPath .context/DerivedData-task8-unit -only-testing:HangTenTests
rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/DerivedData-task8-debug CODE_SIGNING_ALLOWED=YES
rtk git diff --check
```

Expected: full unit bundle/build pass; diff check empty.

- [ ] **Step 8: Create one isolated simulator.** With the mandatory preflight trap already active, follow `docs/IOS_SIMULATOR_VALIDATION.md:34-181` only for simulator creation: write the exact workspace-owned simulator name to the pending manifest before `simctl create`, move that exact name/UUID to the owned manifest after success, and retain the returned exact UUID in `simulator_uuid`. Do not register build paths here; never use `booted`.

- [ ] **Step 9: Build and install the exact current-source app.**

```bash
rtk xcrun simctl boot "$simulator_uuid"
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination "platform=iOS Simulator,id=$simulator_uuid" -derivedDataPath .context/DerivedData build CODE_SIGNING_ALLOWED=YES
rtk xcrun simctl install "$simulator_uuid" .context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app
rtk xcrun simctl get_app_container "$simulator_uuid" com.hangten.training app
rtk xcrun simctl launch "$simulator_uuid" com.hangten.training
```

Expected: build/install succeeds, the returned container belongs to this UUID, and the final preflight launch leaves this exact bundle running so B01's mandatory terminate succeeds. If validation resumes with no process running, execute that same preflight launch once before the first resumed B/W row; do not suppress or broadly ignore a failed terminate.

- [ ] **Step 10: Execute the exact 22-position model matrix.** Create the owned directory `.context/batch03-experience-review`. For every row, terminate only `com.hangten.training` on `simulator_uuid`, then launch with `SIMCTL_CHILD_` prefixed versions of that row's board, presentation, and position plus `HANGTEN_REVIEW_CONFIGURATION_UI=board-detail`, `HANGTEN_REVIEW_WORKFLOW_STATE=selected`, `HANGTEN_REVIEW_MODEL_LOAD_MODE=production`, and `HANGTEN_REVIEW_PORTRAIT=1`. Require exact `review.model.ready`, tap `review.model.orbit` with AXe, require `review.model.orbit-complete`, tap the row's exact real highlighted contact, require `review.model.reset-complete`, require exact `review.model.ready` again immediately before the screenshot, then capture the row path. A row passes only when orbit visibly changes framing, the production contact tap restores canonical framing/highlights, all three signal values equal the row's full model identity, and suspension/spec verdicts hold. Do not accept a raster, default position, prior-row scene, review-only direct reset, or screenshot after a failed poll.

| Case | Board | Presentation | Position | Reset tap ID | Exact post-reset framing/highlight/suspension verdict | Post-reset capture |
| --- | --- | --- | --- | --- | --- | --- |
| B01 | `aelith.cyclops-011` | `primary` | `front-cup` | `boardModel.contact.mono-20` | canonical front framing; exactly `mono-20`; one cord visible | `.context/batch03-experience-review/B01-aelith-front-cup.png` |
| B02 | `frictitious.nug` | `primary` | `front-25` | `boardModel.contact.edge-25` | canonical front framing; exactly `edge-25`; paired cords visible | `.context/batch03-experience-review/B02-nug-front-25.png` |
| B03 | `frictitious.nug` | `primary` | `front-inverted-20` | `boardModel.contact.edge-20` | canonical front-inverted framing; exactly `edge-20`; paired cords visible | `.context/batch03-experience-review/B03-nug-front-inverted-20.png` |
| B04 | `frictitious.nug` | `primary` | `reverse-13` | `boardModel.contact.edge-13` | canonical reverse framing; exactly `edge-13`; paired cords visible | `.context/batch03-experience-review/B04-nug-reverse-13.png` |
| B05 | `frictitious.nug` | `primary` | `reverse-inverted-8` | `boardModel.contact.edge-8` | canonical reverse-inverted framing; exactly `edge-8`; paired cords visible | `.context/batch03-experience-review/B05-nug-reverse-inverted-8.png` |
| B06 | `frictitious.nug` | `primary` | `outer-upper` | `boardModel.contact.jug-40` | canonical outer-upper framing; exactly `jug-40`; paired cords visible | `.context/batch03-experience-review/B06-nug-outer-upper.png` |
| B07 | `frictitious.nug` | `primary` | `outer-lower` | `boardModel.contact.pinch-60` | canonical outer-lower framing; exactly `pinch-60`; paired cords visible | `.context/batch03-experience-review/B07-nug-outer-lower.png` |
| B08 | `frictitious.port-a-board` | `primary` | `front-upright` | `boardModel.contact.edge-30` | canonical front framing; exactly `edge-30,edge-25`; paired cords visible | `.context/batch03-experience-review/B08-port-front-upright.png` |
| B09 | `frictitious.port-a-board` | `primary` | `front-inverted` | `boardModel.contact.edge-20` | canonical front-inverted framing; exactly `edge-20`; paired cords visible | `.context/batch03-experience-review/B09-port-front-inverted.png` |
| B10 | `frictitious.port-a-board` | `primary` | `reverse-upright` | `boardModel.contact.edge-12` | canonical reverse framing; exactly `edge-12,edge-10`; paired cords visible | `.context/batch03-experience-review/B10-port-reverse-upright.png` |
| B11 | `frictitious.port-a-board` | `primary` | `reverse-inverted` | `boardModel.contact.edge-15` | canonical reverse-inverted framing; exactly `edge-15,edge-8`; paired cords visible | `.context/batch03-experience-review/B11-port-reverse-inverted.png` |
| B12 | `frictitious.port-a-board` | `primary` | `outer-upper` | `boardModel.contact.jug-outer-rim` | canonical outer-upper framing; exactly `jug-outer-rim`; paired cords visible; no authored depth row | `.context/batch03-experience-review/B12-port-outer-upper.png` |
| B13 | `frictitious.port-a-board` | `primary` | `pinch-side` | `boardModel.contact.pinch-body` | canonical pinch framing; exactly corrected `pinch-body`; paired cords visible; no authored depth row | `.context/batch03-experience-review/B13-port-pinch-side.png` |
| B14 | `nature.stone-hanger-mini` | `primary` | `front-upright` | `boardModel.contact.pull-up-jug` | canonical front framing; exactly `pull-up-jug,granite-edge-15`; paired open-groove cords visible | `.context/batch03-experience-review/B14-oak-front-upright.png` |
| B15 | `nature.stone-hanger-mini` | `primary` | `wood-inverted` | `boardModel.contact.wood-edge-15-incut` | canonical wood-inverted framing; exactly `wood-edge-15-incut`; paired open-groove cords visible | `.context/batch03-experience-review/B15-oak-wood-inverted.png` |
| B16 | `nature.stone-hanger-mini` | `primary` | `pinch-side` | `boardModel.contact.pinch-60` | canonical pinch framing; exactly combined `pinch-60`; paired open-groove cords visible | `.context/batch03-experience-review/B16-oak-pinch-side.png` |
| B17 | `nature.stone-hanger-mini-karma8a` | `primary` | `granite-front` | `boardModel.contact.granite-edge-15` | canonical granite-front framing; exactly `granite-edge-15`; paired open-groove cords visible | `.context/batch03-experience-review/B17-karma-granite-front.png` |
| B18 | `nature.stone-hanger-mini-karma8a` | `primary` | `wood-inverted` | `boardModel.contact.wood-edge-15` | canonical wood-inverted framing; exactly `wood-edge-15`; paired open-groove cords visible | `.context/batch03-experience-review/B18-karma-wood-inverted.png` |
| B19 | `nature.stone-hanger-mini-karma8a` | `primary` | `pinch-side` | `boardModel.contact.pinch-60` | canonical pinch framing; exactly combined `pinch-60`; paired open-groove cords visible | `.context/batch03-experience-review/B19-karma-pinch-side.png` |
| B20 | `plateau.lifting-edge` | `depth-18mm` | `depth-18mm` | `boardModel.contact.edge-18` | canonical depth-18 framing; exactly `edge-18`; no blocker highlight; paired cords visible; spec 18 mm | `.context/batch03-experience-review/B20-plateau-depth-18mm.png` |
| B21 | `plateau.lifting-edge` | `depth-15mm` | `depth-15mm` | `boardModel.contact.edge-18` | canonical depth-15 framing; exactly `edge-18`; 15 mm blocker remains body-only; paired cords visible; spec 15 mm | `.context/batch03-experience-review/B21-plateau-depth-15mm.png` |
| B22 | `plateau.lifting-edge` | `depth-10mm` | `depth-10mm` | `boardModel.contact.edge-18` | canonical depth-10 framing; exactly `edge-18`; 10 mm blocker remains body-only; paired cords visible; spec 10 mm | `.context/batch03-experience-review/B22-plateau-depth-10mm.png` |

Use this exact command shape; the table supplies every value and capture path, so no package/position may be omitted:

```bash
rtk xcrun simctl terminate "$simulator_uuid" com.hangten.training
rtk env SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID=aelith.cyclops-011 SIMCTL_CHILD_HANGTEN_REVIEW_PRESENTATION_ID=primary SIMCTL_CHILD_HANGTEN_REVIEW_POSITION_ID=front-cup SIMCTL_CHILD_HANGTEN_REVIEW_CONFIGURATION_UI=board-detail SIMCTL_CHILD_HANGTEN_REVIEW_WORKFLOW_STATE=selected SIMCTL_CHILD_HANGTEN_REVIEW_MODEL_LOAD_MODE=production SIMCTL_CHILD_HANGTEN_REVIEW_PORTRAIT=1 xcrun simctl launch "$simulator_uuid" com.hangten.training
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.ready --timeout-seconds 30 --value-prefix 'aelith.cyclops-011|primary|front-cup|'
rtk axe tap --udid "$simulator_uuid" --id review.model.orbit --wait-timeout 5
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.orbit-complete --timeout-seconds 10 --value-prefix 'aelith.cyclops-011|primary|front-cup|'
rtk axe tap --udid "$simulator_uuid" --id boardModel.contact.mono-20 --wait-timeout 5
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.reset-complete --timeout-seconds 10 --value-prefix 'aelith.cyclops-011|primary|front-cup|'
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.ready --timeout-seconds 10 --value-prefix 'aelith.cyclops-011|primary|front-cup|'
rtk xcrun simctl io "$simulator_uuid" screenshot .context/batch03-experience-review/B01-aelith-front-cup.png
```

For B02–B22 substitute the row's six literal values (board, presentation, position, reset tap ID, verdict, and capture) into the same nine-command sequence; no action is optional. The first command for every row is the exact bundle terminate shown above, and the preceding row leaves the app running. The ready/orbit/reset prefix is exactly that row's `boardID|presentationID|positionID|`. The final value-aware ready wait and screenshot form an inseparable pair: no screenshot command may execute unless that immediately preceding wait returned 0. UI acceptance also asserts the ready/orbit/reset values end in the selected descriptor's 64-character hash.

- [ ] **Step 11: Execute the exact workflow/accessibility matrix.** Every row uses `HANGTEN_REVIEW_BOARD_ID=plateau.lifting-edge`, `HANGTEN_REVIEW_PRESENTATION_ID=depth-15mm`, `HANGTEN_REVIEW_POSITION_ID=depth-15mm`, and `HANGTEN_REVIEW_PORTRAIT=1` unless the row says otherwise. Prefix each name with `SIMCTL_CHILD_` when launching. Capture the exact file and record the exact verdict; never substitute exercise or coaching text for these equipment-only component states.

| Case | Surface/state/mode | First required poll | Ordered AXe action(s) → final poll | Exact capture | Exact verdict |
| --- | --- | --- | --- | --- | --- |
| W01 | `board-detail/selection-switch/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | tap `boardDetail.edgeDepth.depth-10mm` → `review.model.ready --value-prefix 'plateau.lifting-edge|depth-10mm|depth-10mm|'` | `.context/batch03-experience-review/W01-board-detail-switch.png` | 15→10 changes model, highlight, selected control, and spec atomically; no 15 content remains |
| W02 | `editor/selection-switch/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | tap `customRoutine.edgeDepth.depth-10mm` → `review.model.ready --value-prefix 'plateau.lifting-edge|depth-10mm|depth-10mm|'` | `.context/batch03-experience-review/W02-editor-switch.png` | preview and draft show `edge-18/depth-10mm/exact10` together; Save never observes mixed fields |
| W03 | `choice/ambiguous-choice/exact-ready` | `workout.configuration.choice.depth-18mm` | tap `workout.configuration.choice.depth-15mm` → `review.workflow.choice-selected --value-contains 'depth-15mm'` | `.context/batch03-experience-review/W03-choice.png` | 18/15/10 ordered; none initially selected; Continue enables only after explicit 15 |
| W04 | `setup/initial-setup/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | tap `workout.setup.ready` → `review.workflow.initial-countdown --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|0.00|paused'` | `.context/batch03-experience-review/W04-initial-setup.png` | Ready gates exact applied identity, then real initial countdown effect occurs |
| W05 | `setup/rest-preview/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | tap `workout.setup.ready` → `review.workflow.rest-preview-confirmed --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|30.00|running'` | `.context/batch03-experience-review/W05-rest-preview.png` | destination preview is confirmed while authored rest keeps running |
| W06 | `setup/rest-wait/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | tap `workout.setup.ready` → `review.workflow.rest-wait-resumed --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|30.00|running'` | `.context/batch03-experience-review/W06-rest-wait.png` | boundary remains clamped with zero setup accrual, then resumes at 30 |
| W07 | `setup/natural-boundary/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | tap `workout.setup.ready` → `review.workflow.natural-boundary-resumed --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|10.00|running'` | `.context/batch03-experience-review/W07-natural-boundary.png` | running continuation resumes at exact boundary 10 |
| W08 | `setup/skip/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | tap `workout.setup.ready` → `review.workflow.skip-countdown --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|45.00|running'` | `.context/batch03-experience-review/W08-skip.png` | real skip countdown effect targets 45; no prior accrual |
| W09 | `setup/jump/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | tap `workout.setup.ready` → `review.workflow.jump-resumed --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|45.00|running'` | `.context/batch03-experience-review/W09-jump.png` | real running jump resumes at 45 |
| W10 | `setup/rewind/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | tap `workout.setup.ready` → `review.workflow.rewind-paused --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|10.00|paused'` | `.context/batch03-experience-review/W10-rewind.png` | real paused rewind remains paused at 10 |
| W11 | `setup/restart/exact-ready` | `review.workflow.restart-countdown --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|0.00|paused'` | no tap; repeat the same value-aware completion poll immediately before capture | `.context/batch03-experience-review/W11-restart.png` | preconfirmed exact identity avoids duplicate gate and restarts at zero |
| W12 | `setup/resume-paused/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | tap `workout.setup.ready` → `review.workflow.resume-paused --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|45.00|paused'` | `.context/batch03-experience-review/W12-resume-paused.png` | resume remains paused at 45 |
| W13 | `setup/resume-running/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | tap `workout.setup.ready` → `review.workflow.resume-running --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|45.00|running'` | `.context/batch03-experience-review/W13-resume-running.png` | resume returns to running at 45 |
| W14 | `setup/initial-setup/wrong-identity` | `review.model.failure.wrong-identity` | no tap; poll the same failure immediately before capture | `.context/batch03-experience-review/W14-wrong-identity.png` | wrong ready ignored; Ready disabled; no stale model |
| W15 | `setup/unavailable/missing-resource` | `review.model.failure.missing-resource` | no tap; poll `workout.configurationUnavailable`, then the failure again | `.context/batch03-experience-review/W15-missing-resource.png` | unavailable and exact diagnostic visible; no fallback |
| W16 | `setup/unavailable/hash-mismatch` | `review.model.failure.hash-mismatch` | no tap; poll `workout.configurationUnavailable`, then the failure again | `.context/batch03-experience-review/W16-hash-mismatch.png` | wrong hash rejected; Ready disabled |
| W17 | `setup/unavailable/cancelled` | `review.model.failure.cancelled` | no tap; poll `workout.configurationUnavailable`, then the failure again | `.context/batch03-experience-review/W17-cancelled.png` | cancellation unavailable; old scene cleared |
| W18 | `setup/unavailable/unavailable` | `review.model.failure.unavailable` | no tap; poll `workout.configurationUnavailable`, then the failure again | `.context/batch03-experience-review/W18-unavailable.png` | exact unavailable; no default/raster/stale fallback |
| W19 | `setup/initial-setup/exact-ready`; XXXL content size | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | no tap; repeat the same value-aware ready poll immediately before capture | `.context/batch03-experience-review/W19-dynamic-type.png` | instruction, status, and Ready readable without clipping/overlap |
| W20 | `setup/initial-setup/exact-ready`; VoiceOver on | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | perform ordered VoiceOver next gestures setup instruction→model status→Ready; AXe tap `workout.setup.ready` → `review.workflow.initial-countdown --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|0.00|paused'` | `.context/batch03-experience-review/W20-voiceover.png` | values announce 15 millimeters and Ready state once in correct order |
| W21 | `setup/rest-wait/exact-ready` | `review.model.ready --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'` | capture portrait after the same value-aware ready poll; AXe tap `review.rotateLandscape` → `review.workflow.rotation-landscape --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|30.00|running'`; repeat value-aware ready poll before landscape capture | `.context/batch03-experience-review/W21-rotation-portrait.png`, `.context/batch03-experience-review/W21-rotation-landscape.png` | frozen target, wait, and elapsed survive rotation; no clipping or advance |

Execute each row with its literal surface/state/mode, poll ID, tap ID, and capture path from the table. These concrete representatives define all four command shapes: W01–W03 switch/choice, W04–W10/W12–W13/W20 tap-and-effect, W11/W14–W19 no-tap state/failure, and W21 dual capture. Every other row substitutes only table literals into its represented shape.

```bash
rtk xcrun simctl terminate "$simulator_uuid" com.hangten.training
rtk env SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID=plateau.lifting-edge SIMCTL_CHILD_HANGTEN_REVIEW_PRESENTATION_ID=depth-15mm SIMCTL_CHILD_HANGTEN_REVIEW_POSITION_ID=depth-15mm SIMCTL_CHILD_HANGTEN_REVIEW_CONFIGURATION_UI=board-detail SIMCTL_CHILD_HANGTEN_REVIEW_WORKFLOW_STATE=selection-switch SIMCTL_CHILD_HANGTEN_REVIEW_MODEL_LOAD_MODE=exact-ready SIMCTL_CHILD_HANGTEN_REVIEW_PORTRAIT=1 xcrun simctl launch "$simulator_uuid" com.hangten.training
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.ready --timeout-seconds 30 --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'
rtk axe tap --udid "$simulator_uuid" --id boardDetail.edgeDepth.depth-10mm --wait-timeout 5
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.ready --timeout-seconds 30 --value-prefix 'plateau.lifting-edge|depth-10mm|depth-10mm|'
rtk xcrun simctl io "$simulator_uuid" screenshot .context/batch03-experience-review/W01-board-detail-switch.png
rtk xcrun simctl terminate "$simulator_uuid" com.hangten.training
rtk env SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID=plateau.lifting-edge SIMCTL_CHILD_HANGTEN_REVIEW_PRESENTATION_ID=depth-15mm SIMCTL_CHILD_HANGTEN_REVIEW_POSITION_ID=depth-15mm SIMCTL_CHILD_HANGTEN_REVIEW_CONFIGURATION_UI=setup SIMCTL_CHILD_HANGTEN_REVIEW_WORKFLOW_STATE=initial-setup SIMCTL_CHILD_HANGTEN_REVIEW_MODEL_LOAD_MODE=exact-ready SIMCTL_CHILD_HANGTEN_REVIEW_PORTRAIT=1 xcrun simctl launch "$simulator_uuid" com.hangten.training
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.ready --timeout-seconds 30 --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'
rtk axe tap --udid "$simulator_uuid" --id workout.setup.ready --wait-timeout 5
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.workflow.initial-countdown --timeout-seconds 10 --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|0.00|paused'
rtk xcrun simctl io "$simulator_uuid" screenshot .context/batch03-experience-review/W04-initial-setup.png
rtk xcrun simctl terminate "$simulator_uuid" com.hangten.training
rtk env SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID=plateau.lifting-edge SIMCTL_CHILD_HANGTEN_REVIEW_PRESENTATION_ID=depth-15mm SIMCTL_CHILD_HANGTEN_REVIEW_POSITION_ID=depth-15mm SIMCTL_CHILD_HANGTEN_REVIEW_CONFIGURATION_UI=setup SIMCTL_CHILD_HANGTEN_REVIEW_WORKFLOW_STATE=unavailable SIMCTL_CHILD_HANGTEN_REVIEW_MODEL_LOAD_MODE=missing-resource SIMCTL_CHILD_HANGTEN_REVIEW_PORTRAIT=1 xcrun simctl launch "$simulator_uuid" com.hangten.training
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.failure.missing-resource --timeout-seconds 30
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier workout.configurationUnavailable --timeout-seconds 10
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.failure.missing-resource --timeout-seconds 10
rtk xcrun simctl io "$simulator_uuid" screenshot .context/batch03-experience-review/W15-missing-resource.png
rtk xcrun simctl terminate "$simulator_uuid" com.hangten.training
rtk env SIMCTL_CHILD_HANGTEN_REVIEW_BOARD_ID=plateau.lifting-edge SIMCTL_CHILD_HANGTEN_REVIEW_PRESENTATION_ID=depth-15mm SIMCTL_CHILD_HANGTEN_REVIEW_POSITION_ID=depth-15mm SIMCTL_CHILD_HANGTEN_REVIEW_CONFIGURATION_UI=setup SIMCTL_CHILD_HANGTEN_REVIEW_WORKFLOW_STATE=rest-wait SIMCTL_CHILD_HANGTEN_REVIEW_MODEL_LOAD_MODE=exact-ready SIMCTL_CHILD_HANGTEN_REVIEW_PORTRAIT=1 xcrun simctl launch "$simulator_uuid" com.hangten.training
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.ready --timeout-seconds 30 --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.ready --timeout-seconds 10 --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'
rtk xcrun simctl io "$simulator_uuid" screenshot .context/batch03-experience-review/W21-rotation-portrait.png
rtk axe tap --udid "$simulator_uuid" --id review.rotateLandscape --wait-timeout 5
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.workflow.rotation-landscape --timeout-seconds 10 --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|' --value-suffix '|30.00|running'
rtk bash scripts/wait-for-simulator-accessibility.sh --udid "$simulator_uuid" --identifier review.model.ready --timeout-seconds 10 --value-prefix 'plateau.lifting-edge|depth-15mm|depth-15mm|'
rtk xcrun simctl io "$simulator_uuid" screenshot .context/batch03-experience-review/W21-rotation-landscape.png
```

Every W01–W21 row begins with the literal `rtk xcrun simctl terminate "$simulator_uuid" com.hangten.training`, then relaunches with that row's complete environment; the preceding row leaves the process running, and a standalone/resumed matrix performs the Step 9 preflight launch first. For a tap row, the final value-aware completion poll is immediately before its screenshot. For a no-tap row, repeat the table's state/failure poll immediately before its screenshot. W14–W18 therefore always poll their exact `review.model.failure.*` identifier as the final pre-capture command; W15–W18 additionally prove `workout.configurationUnavailable`. A failed terminate, launch, first poll, AXe tap, final poll, identity-value assertion, or screenshot marks that row FAIL and forbids reuse of a prior image; do not mask absent-process or other terminate failures.

Before W19 run:

```bash
rtk xcrun simctl ui "$simulator_uuid" content_size accessibility-extra-extra-extra-large
```

Before W20 enable VoiceOver in the owned simulator's Settings → Accessibility → VoiceOver, navigate the three elements with VoiceOver gestures, then disable it before W21. W21's DEBUG rotation control must invoke the same scene-geometry request as the existing validation route; it may not recreate the session. After the matrix, restore content size, exercise spoken countdown and audio-off behavior, perform the user-triggered Health permission/save flow, and record simulator/physical-device limitations from `docs/IOS_RUNTIME_SERVICES.md`. Inspect every PNG directly and write the 22 board verdicts plus 21 workflow verdicts to `.context/batch03-experience-review/verdicts.md` before cleanup.

- [ ] **Step 12: Clean owned resources.** Trap calls:

```bash
rtk env PASEO_WORKTREE_PATH="$workspace_path" scripts/paseo-resource-cleanup.sh archive
```

Remove only the exact simulator and every preflight-registered path: `.context/DerivedData-task8-unit`, `.context/DerivedData-task8-ui`, `.context/DerivedData-task8-debug`, `.context/DerivedData-release`, `.context/DerivedData`, `.context/workout-raw.png`, `.context/workout-landscape.png`, and `.context/batch03-experience-review`. Retain manifests on failure; verify the exact UUID is absent, its pending/owned records are consumed, and every listed path is absent; never delete shared/global resources.

- [ ] **Step 13: Run plan/source hygiene checks before commit.**

```bash
rtk rg -n '[[:blank:]]+$' docs/superpowers/plans/2026-09-20-batch-03-workout-experience.md || true
rtk rg -n '[T]ODO|[T]BD|[F]IXME|[.][.][.]|<positionI[D]>|<load-mod[e]>|\{\{[^}]+\}\}' docs/superpowers/plans/2026-09-20-batch-03-workout-experience.md || true
rtk rg -n 'strippingExactContactI[D]\(|tr[y]\? .*renderTarget|package Tasks 8[–]9|package Task 1[2]' docs/superpowers/plans/2026-09-20-batch-03-workout-experience.md || true
rtk awk 'BEGIN { inbash=0 } /^```bash$/ { inbash=1; next } /^```$/ { if (inbash) inbash=0; next } inbash && NF && $1 != "rtk" { print NR ":" $0; bad=1 } END { exit bad }' docs/superpowers/plans/2026-09-20-batch-03-workout-experience.md
rtk awk '/^```/ { count += 1 } END { print count; exit count != 112 || count % 2 }' docs/superpowers/plans/2026-09-20-batch-03-workout-experience.md
rtk rg -c '^### Task ' docs/superpowers/plans/2026-09-20-batch-03-workout-experience.md
rtk rg -c '^rtk git commit -m' docs/superpowers/plans/2026-09-20-batch-03-workout-experience.md
rtk rg -c '^rtk git push$' docs/superpowers/plans/2026-09-20-batch-03-workout-experience.md
rtk git diff --check
```

Expected: the three `rg -n` checks emit no findings; the command-prefix check exits zero; fence count prints `112`; each structural count prints `8`; diff check is empty.

- [ ] **Step 14: Commit and push.** Do not add `.context`.

```bash
rtk git add HangTenTests/Batch03WorkoutExperienceIntegrationTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "test: accept batch 03 workout experience"
rtk git push
```

**Review checkpoint:** Whole-branch reviewer checks Port/legacy acceptance, eight task reviews, simulator/accessibility evidence, fail-closed paths, and cleanup before merge.
