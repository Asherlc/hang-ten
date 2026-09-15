# Contact-First Hangboard Domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace logical-hold IDs with physical contacts, make plans describe requirements, and migrate board packages and models to the contact-first contract without runtime compatibility code.

**Architecture:** Board schema v3 introduces ordered physical contacts and revision identity. Plans encode `ContactRequirement` values and resolve them only against a selected revision; model descriptors bind mesh nodes to contacts and may contain multiple bodies. Completion persists the resolved contact IDs and revision hash as an audit snapshot.

**Tech Stack:** Swift/Foundation/SceneKit/XCTest, Python 3.11 package validator and pytest, JSON board packages, USDZ descriptors.

**Spec:** `docs/superpowers/specs/2026-09-12-contact-first-hangboard-domain-design.md`

## Global Constraints

- This is a hard cut: final production code accepts schema v3 and activity persistence v2 only; it contains no v1/v2 package reader, semantic mapping, direct target-ID case, fallback substitution, compatibility typealias, or legacy persistence decoder.
- A plan describes factual contact requirements only. New or changed plan fields must be traceable to a retained manufacturer routine source; do not infer requirements from a board mesh or board metadata.
- A model package is model-only; a raster package is allowed only raster media. Model descriptors bind mesh components to physical contact IDs and may contain one or more body components.
- Source model geometry is never modified to hide a parser or matching failure. Physical-contact inventory, source evidence, and human visual review remain prerequisites to a model promotion.
- Run TDD for every task, make a commit after each accepted task, push every commit, and perform a fresh task review before the next task.

---

### Task 1: Contact-first v3 board package contract and catalog conversion

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`, `Tools/HangboardPackages/tests/test_board_catalog.py`, `Tools/HangboardPackages/tests/test_model_first_packages.py`
- Modify: `HangTen/Models/BoardPackageStore.swift`, `HangTen/Models/TrainingModels.swift`, `HangTenTests/BoardPackageStoreTests.swift`, `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`
- Modify: every `Hangboards/*/board.json`
- Delete: v1/v2 package-specific fixtures and parser helpers once their v3 equivalents cover the rule.

**Interfaces:**
- Produces `PhysicalContact(id: String, equipmentObjectID: String, name: String, kind: HoldKind, features: Set<HoldFeature>, fingerCapacity: Int?, handCapacity: Int?, depthRangeMillimeters: MillimeterRange?, gripTypes: Set<GripType>, side: ContactSide?, pairedContactID: String?)`.
- Produces `BoardRevision(id: String, revisionID: String, contacts: [PhysicalContact], presentations: [BoardPresentation], positions: [BoardPosition])`.
- `BoardPosition` exposes `contactIDs`; `BoardModelNodeDescriptor.Role` is `body`, `contact`, or `attachment`, and its optional ID is named `contactID`.

- [ ] **Step 1: Write the failing Python and Swift v3 fixtures**

```python
def test_v3_model_descriptor_binds_contacts_and_allows_two_bodies(tmp_path):
    package = write_v3_model_package(tmp_path, contacts=("left-edge", "right-edge"), body_nodes=("left-body", "right-body"))
    loaded = load_board_package(package)
    assert loaded.board.revision_id == "2026-09-contact-first"
    assert tuple(contact.id for contact in loaded.board.contacts) == ("left-edge", "right-edge")
```

```swift
func testStoreRejectsV2AndLoadsV3ContactsWithMultipleBodies() throws {
    XCTAssertThrowsError(try BoardPackageStore(bundle: fixtureBundle(schemaVersion: 2)).boards)
    let board = try XCTUnwrap(BoardPackageStore(bundle: v3TwoBodyFixtureBundle()).boards.first)
    XCTAssertEqual(board.revisionID, "2026-09-contact-first")
    XCTAssertEqual(board.contacts.map(\.id), ["left-edge", "right-edge"])
}
```

- [ ] **Step 2: Run the focused tests and confirm they fail because v3 is unsupported**

Run: `python3 -B -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q`

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests/testStoreRejectsV2AndLoadsV3ContactsWithMultipleBodies`

Expected: both fail because schema v3 and `contacts` are not accepted.

- [ ] **Step 3: Implement v3-only parsing and representations**

Replace `BoardHold` and `holds` with `PhysicalContact` and `contacts` in both languages. Require root members `schemaVersion: 3`, `revisionID`, and `contacts`; reject `holds`, `semanticHolds`, and all former v1/v2 media members. Rename position `holdIDs` to `contactIDs`. Model descriptors require `contactID` for contact nodes, permit `bodyCount >= 1`, and require their contact inventory to match board contacts exactly. Raster media retains only canonical path ownership keyed by contact ID. Remove all v1/v2 decode functions and compatibility tests rather than branching on version.

- [ ] **Step 4: Convert the full catalog atomically**

For every checked-in `Hangboards/*/board.json`, author a v3 document preserving the ordered physical inventory and source-backed metadata. Set a nonempty immutable `revisionID`, rename hold references to contact references, and move raster paths under raster media. For an existing model package, replace descriptor `holdID` with `contactID` without changing the USDZ. Remove every legacy JSON member; do not commit a converter or an adapter.

- [ ] **Step 5: Run catalog validation and tests**

Run: `python3 -B -m pytest Tools/HangboardPackages/tests/test_board_catalog.py Tools/HangboardPackages/tests/test_model_first_packages.py -q`

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests`

Expected: every shipped package is v3; v1/v2 fixture inputs fail closed; model fixtures prove exact contact coverage and multiple bodies.

- [ ] **Step 6: Commit and push**

Run: `git add Hangboards Tools/HangboardPackages HangTen/Models/BoardPackageStore.swift HangTen/Models/TrainingModels.swift HangTenTests/BoardPackageStoreTests.swift HangTenTests/Fixtures/BoardPackageValidationFixtures.json && git commit -m 'feat: migrate board catalog to contact-first v3' && git push`

### Task 2: ID-free plan requirements and deterministic contact resolution

**Files:**
- Modify: `HangTen/Models/PlanStorage.swift`, `HangTen/Models/WorkoutActivityRecording.swift`, `HangTen/Models/WorkoutTimeline.swift`, `HangTen/Models/AppStore.swift`
- Modify: `HangTen/Resources/PlanLibrary.json`
- Modify: `HangTenTests/PlanStorageTests.swift`, `HangTenTests/WorkoutActivityRecordingTests.swift`, `HangTenTests/WorkoutTimelineTests.swift`

**Interfaces:**
- Produces `struct ContactRequirement: Codable, Hashable { let kind: HoldKind?; let requiredFeatures: Set<HoldFeature>; let depthRangeMillimeters: MillimeterRange?; let fingerCapacity: Int?; let handCapacity: Int?; let compatibleGripTypes: Set<GripType>; let selection: ContactSelectionPolicy }`.
- `ContactSelectionPolicy` has exactly `allMatching`, `single`, and `bilateralPair`.
- `ContactResolver.resolve(_ requirement: ContactRequirement, step: WorkoutStep, board: BoardRevision) throws -> [PhysicalContact]` returns canonical contact order or fails without substitution.

- [ ] **Step 1: Write failing plan-decoding and resolver tests**

```swift
func testPlanDecodesRequirementWithoutContactIDs() throws {
    let target = try decodeTarget(#"{"kind":"edge","depthRangeMillimeters":{"minimum":18,"maximum":22},"selection":"bilateralPair"}"#)
    XCTAssertEqual(target.selection, .bilateralPair)
}

func testResolverRejectsAnAmbiguousSingleRequirement() {
    XCTAssertThrowsError(try ContactResolver.resolve(.edge(selection: .single), step: bilateralStep, board: fixtureBoard))
}
```

- [ ] **Step 2: Run focused tests and confirm current semantic/ID behavior fails them**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/WorkoutActivityRecordingTests`

Expected: failures because a target can still carry `holdIDs`/`semantic` and no selection policy exists.

- [ ] **Step 3: Replace the plan target grammar and resolver**

Replace `WorkoutTargetDefinition`, `HoldTarget`, `SemanticHoldMappingDefinition`, `BoardMappingDefinition`, and all semantic resolver paths with `ContactRequirement`. Remove direct IDs, feature fallbacks, and board mappings from the JSON schema and Swift decoder. Make matching test required factual fields, position membership, side, and grip compatibility; enforce exact cardinality for `single` and documented pair membership for `bilateralPair`. Update highlighting and accessibility to consume resolved contact IDs only after this resolution step.

- [ ] **Step 4: Transcribe bundled plans and reject old content**

Rewrite every bundled plan target in `PlanLibrary.json` to a factual requirement and explicit selection policy, using only the plan's recorded source evidence. Remove `boardMappings`. Add validation that rejects the keys `semantic`, `semantics`, `holdIDs`, and `fallbackFeatures`, and rejects requirements that cannot resolve on every declared board.

- [ ] **Step 5: Run plan/resolution tests and a legacy-key scan**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/WorkoutActivityRecordingTests -only-testing:HangTenTests/WorkoutTimelineTests`

Run: `rg -n 'SemanticHoldMappingDefinition|BoardMappingDefinition|\.semantic\(|\.semantics\(|\.holdIDs\(|boardMappings|fallbackFeatures' HangTen HangTenTests`

Expected: tests pass and the scan returns no production or test compatibility code.

- [ ] **Step 6: Commit and push**

Run: `git add HangTen/Models/PlanStorage.swift HangTen/Models/WorkoutActivityRecording.swift HangTen/Models/WorkoutTimeline.swift HangTen/Models/AppStore.swift HangTen/Resources/PlanLibrary.json HangTenTests/PlanStorageTests.swift HangTenTests/WorkoutActivityRecordingTests.swift HangTenTests/WorkoutTimelineTests.swift && git commit -m 'feat: resolve plans through contact requirements' && git push`

### Task 3: Contact-bound renderer and multi-body model validation

**Files:**
- Modify: `HangTen/Views/BoardModelView.swift`, `HangTen/Models/BoardPackageStore.swift`, `HangTen/Models/TrainingModels.swift`
- Modify: `HangTenTests/BoardModelTests.swift`, `HangTenTests/WorkoutActivityRecordingTests.swift`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`, `Tools/HangboardPackages/tests/test_model_first_packages.py`

**Interfaces:**
- `BoardModelDescriptor.contacts: [String: BoardModelContactDescriptor]` replaces `holds`.
- `BoardModelView` exposes `contactID(for:)` and receives highlighted physical-contact IDs; it never accepts a plan target or semantic alias.

- [ ] **Step 1: Write failing renderer and parser tests**

```swift
func testTwoBodyModelBindsEachContactAndDoesNotMakeBodyTappable() throws {
    let model = try makeModel(twoBodies: true, contacts: ["left-edge", "right-edge"])
    XCTAssertEqual(model.contactNodes.keys.sorted(), ["left-edge", "right-edge"])
    XCTAssertNil(model.contactID(for: try bodyHit(model)))
}
```

- [ ] **Step 2: Run the focused tests and confirm the one-body/hold-ID checks fail**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardModelTests`

Expected: failure because the current descriptor enforces one body and uses hold IDs.

- [ ] **Step 3: Implement contact-only rendering**

Rename renderer collections and descriptor fields from hold to contact. Permit every declared body node to load as nonpickable geometry; require every selectable mesh to resolve to an exactly declared contact. Preserve independent cloned materials, async caching, accessibility, explicit unavailable state, and nearest-triangle selection. Delete the one-body validation and every renderer compatibility name.

- [ ] **Step 4: Run native model checks**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardModelTests`

Run: `python3 -B -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q`

Expected: model descriptors accept multiple body components, reject unbound/selectable bodies, and bind all contacts exactly.

- [ ] **Step 5: Commit and push**

Run: `git add HangTen/Views/BoardModelView.swift HangTen/Models/BoardPackageStore.swift HangTen/Models/TrainingModels.swift HangTenTests/BoardModelTests.swift HangTenTests/WorkoutActivityRecordingTests.swift Tools/HangboardPackages && git commit -m 'feat: bind board models to physical contacts' && git push`

### Task 4: Versioned resolution snapshots and hard-cut local persistence

**Files:**
- Modify: `HangTen/Models/WorkoutActivityRecording.swift`, `HangTen/Models/WorkoutHistory.swift`, `HangTen/Models/WorkoutHistoryService.swift`, `HangTen/Models/WorkoutSessionStore.swift`, `HangTen/Models/LocalWorkoutHistoryStore.swift`, `HangTen/Models/AppStore.swift`
- Modify: `HangTenTests/WorkoutActivityRecordingTests.swift`, `HangTenTests/WorkoutHistoryServiceTests.swift`, `HangTenTests/WorkoutSessionStoreTests.swift`

**Interfaces:**
- `ResolvedContactSnapshot(boardID: String, revisionID: String, modelSHA256: String?, requirement: ContactRequirement, contactIDs: [String])`.
- `RecordedActivitySegment` contains `resolution: ResolvedContactSnapshot?`, not bare `holdIDs`, `holdType`, or `sizeMillimeters`.
- New persisted activity/session keys are suffixed `v2`; the old keys are removed without decoding.

- [ ] **Step 1: Write failing snapshot and storage-isolation tests**

```swift
func testRecordedWorkStoresRevisionRequirementAndResolvedContacts() throws {
    let record = try WorkoutActivityRecorder().segments(for: plan, on: modelBoard).first(where: { $0.kind == .work })
    XCTAssertEqual(record?.resolution?.revisionID, "2026-09-contact-first")
    XCTAssertEqual(record?.resolution?.contactIDs, ["left-edge", "right-edge"])
    XCTAssertEqual(record?.resolution?.modelSHA256, modelBoard.modelSHA256)
}

func testHistoryDoesNotReadTheFormerActivityStorageKey() {
    defaults.set(legacyActivityPayload, forKey: LocalWorkoutHistoryStore.legacyKey)
    XCTAssertEqual(LocalWorkoutHistoryStore(defaults: defaults).records, [])
}
```

- [ ] **Step 2: Run focused tests and confirm they fail under the bare-ID record**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/WorkoutActivityRecordingTests -only-testing:HangTenTests/WorkoutHistoryServiceTests -only-testing:HangTenTests/WorkoutSessionStoreTests`

Expected: failures because records store hold IDs and read existing local storage keys.

- [ ] **Step 3: Implement v2 snapshots and delete legacy decoding**

Build a snapshot only after `ContactResolver` succeeds. Persist board/revision identity, model hash when the selected presentation is model media, exact requirement, and canonical contact IDs. Replace bare ID fields in HealthKit activity JSON and local records. Change local key names to v2, delete prior keys once on initialization, and remove all old `Codable` branches and migration helpers. Preserve the HealthKit workout itself as an external historical record without attempting to decode old activity metadata as v2.

- [ ] **Step 4: Run focused persistence tests**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/WorkoutActivityRecordingTests -only-testing:HangTenTests/WorkoutHistoryServiceTests -only-testing:HangTenTests/WorkoutSessionStoreTests`

Expected: new records are auditable snapshots and former local formats are ignored/removed rather than translated.

- [ ] **Step 5: Commit and push**

Run: `git add HangTen/Models/WorkoutActivityRecording.swift HangTen/Models/WorkoutHistory.swift HangTen/Models/WorkoutHistoryService.swift HangTen/Models/WorkoutSessionStore.swift HangTen/Models/LocalWorkoutHistoryStore.swift HangTen/Models/AppStore.swift HangTenTests/WorkoutActivityRecordingTests.swift HangTenTests/WorkoutHistoryServiceTests.swift HangTenTests/WorkoutSessionStoreTests.swift && git commit -m 'feat: persist resolved contact snapshots' && git push`

### Task 5: Import verified supplied models through v3 contacts

**Files:**
- Modify: only source-audited target packages under `Hangboards/`, their `assets/primary.usdz`, and `assets/primary.model.json`
- Modify: the matching `Tools/HangboardModels` verifier/configuration tests and source-audit records
- Modify: `HangTenTests/BoardModelTests.swift`

**Interfaces:**
- Each promoted descriptor has only `body`, `contact`, and optional `attachment` nodes, and every contact mapping has evidence in that package's retained source audit.

- [ ] **Step 1: Re-run the source-contact audit for one board package**

Run the existing board-specific verifier and review its retained mapping report before making an asset change. The report must identify the exact board revision, every source physical contact, every contact-to-mesh binding, model SHA-256, and two approved materially distinct visual source snapshots.

Expected: a board with any missing, extra, ambiguous, or unsupported source contact stops here and is not imported.

- [ ] **Step 2: Write an exact-inventory regression before promotion**

```swift
func testPromotedModelMatchesItsV3PhysicalContactInventory() throws {
    let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: promotedBoardID))
    let model = try loadBundledModel(for: board)
    XCTAssertEqual(Set(model.contactNodes.keys), Set(board.contacts.map(\.id)))
    XCTAssertTrue(board.modelMedia.descriptor.nodes.filter { $0.role == .body }.count >= 1)
}
```

- [ ] **Step 3: Run the test and confirm the unmigrated package fails the model-only condition**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardModelTests/testPromotedModelMatchesItsV3PhysicalContactInventory`

Expected: failure until the audited USDZ and descriptor replace the raster presentation.

- [ ] **Step 4: Promote only the audited package**

Stage the deterministic USDZ and generated descriptor after the evidence gate. Remove that package's PNG and canonical 2D paths, declare model-only media, and bind each mesh component to the source-audited physical contact ID. Preserve no raster fallback or legacy logical mapping. Do not combine unrelated board imports in this task.

- [ ] **Step 5: Verify the promoted package**

Run the board-specific actual-export verifier, Python package validation, and the focused native model test. Conduct the required human front/oblique/highlight review before promotion.

- [ ] **Step 6: Commit and push**

Run: `git add Hangboards Tools/HangboardModels HangTenTests/BoardModelTests.swift && git commit -m 'feat: migrate audited hangboard model package' && git push`

### Task 6: Whole-branch hard-cut audit and iOS validation

**Files:**
- Modify only files required to resolve concrete failures discovered by this task.
- Modify: `docs/superpowers/specs/2026-09-12-contact-first-hangboard-domain-design.md` only if an approved clarification is necessary.

- [ ] **Step 1: Write negative regression assertions for prohibited APIs**

```python
def test_repository_has_no_legacy_hold_target_contract():
    sources = "\n".join(path.read_text() for path in swift_sources())
    for prohibited in ("SemanticHoldMappingDefinition", "BoardMappingDefinition", "case holdIDs", "case semantic"):
        assert prohibited not in sources
```

- [ ] **Step 2: Run it and confirm it detects any remaining compatibility code**

Run: `python3 -B -m pytest Tools/HangboardPackages/tests/test_hard_cut_audit.py -q`

Expected: fail before cleanup if a prohibited type or schema path remains.

- [ ] **Step 3: Remove every reported residual and add no adapter**

Delete obsolete tests, fixtures, documentation, and source paths named by the audit; update callers to use `PhysicalContact`, `ContactRequirement`, and `ResolvedContactSnapshot`. Do not silence the audit with exclusions.

- [ ] **Step 4: Run the full verification set**

Run: `python3 -B -m pytest Tools/HangboardPackages/tests -q`

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro'`

Run: `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS'`

Expected: all tests/build pass; package validation covers the entire v3 catalog; no production compatibility contract remains.

- [ ] **Step 5: Commit and push**

Run: `git add -A && git commit -m 'test: enforce contact-first hard cut' && git push`
