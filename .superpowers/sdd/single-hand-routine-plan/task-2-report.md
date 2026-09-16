# Task 2 implementation report — single-hand routine tracking

Base reviewed: `6c9b485f92481b038a8179caf96435d263ce0721`.

## Outcome

- Opted in exactly 11 shipped work steps with `WorkoutHandUse.either`: the
  five `research.max-hangs` work steps and six `research.abrahangs` work
  steps. The generated catalog now exposes those steps so the L/R picker is
  reachable.
- Materialized the selected hand before live header, timeline, routine-row,
  hand-cue, and board-highlight presentation. An unresolved either step still
  presents as authored; bilateral steps remain unchanged.
- Made custom-routine editor preview resolve a valid left/right alternative
  before resolving contacts, and made its toggle operate on that previewed
  alternative so removing the selected mirrored hold clears the selection
  rather than silently losing it.
- Replaced the `boardID: nil` compatibility fixture with board-backed
  symmetric positive coverage and asymmetric one-side rejection coverage.
- Regenerated `HangTen/Resources/PlanLibrary.json` through the repository
  exporter and verified generated parity.

## Eligibility audit and source mappings

`WorkoutHandUse.either` is documented as a Hang Ten adaptation, not a claim
that either source itself prescribes one-arm work. It changes neither source
task content nor source timing/order/rest structure; it lets an athlete choose
one hand where the source has no bilateral or alternating-side requirement.

| Newly enabled plan/steps | Source URL | Audit mapping and rationale |
| --- | --- | --- |
| `research.max-hangs`: `max-hangs-1` through `max-hangs-5` | https://latticetraining.com/workout/1c4cc25a-ebe8-4930-8541-5b604a831c5f/half-4-hang-max/ | The source identifies a 20 mm four-finger half-crimp max-hang task and its loading adjustment, without prescribing a bilateral pair or left/right alternation. The catalog retains its five 7-second tasks and recovery timing; it adds athlete-selected hand capability only. |
| `research.abrahangs`: `abrahangs-grip-1` through `abrahangs-grip-6` | https://latticetraining.com/workout/1832c13b-14c1-444c-82a2-e72b22a6fb13/abrahangs-protocol | The source identifies six individual finger-position variants with feet-supported low loading, without a bilateral-pair or alternating-side prescription. The catalog retains those grips and the existing 10/50 timing adaptation; it adds athlete-selected hand capability only. |

The amendment in `docs/source-audits/2026-08-10-plan-cue-provenance.md`
explicitly excludes indiscriminate hang conversion and preserves F80's
both-hand prescription, RPTC two-handed work, F100 and other explicit
alternating sequences, Megos unilateral left/right work, offset/pull/
isometric-pull work, and all rest steps. A generated-catalog audit found 11
`either` steps, exactly the IDs listed above.

## Changed paths

- `HangTen/Models/TrainingModels.swift`
- `HangTen/Models/WorkoutTimeline.swift`
- `HangTen/Models/CustomRoutineDraft.swift`
- `HangTen/Resources/PlanLibrary.json` (exporter-generated)
- `HangTen/Views/CustomRoutineEditorView.swift`
- `HangTen/Views/RootView.swift`
- `HangTen/Views/WorkoutStepPickerView.swift`
- `HangTenTests/CustomRoutineDraftTests.swift`
- `HangTenTests/PlanStorageTests.swift`
- `HangTenTests/WorkoutTimelineTests.swift`
- `docs/source-audits/2026-08-10-plan-cue-provenance.md`

## Verification

| Command/check | Outcome |
| --- | --- |
| `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/derived-single-hand-task-2-build CODE_SIGNING_ALLOWED=NO` | Passed (compile-only simulator build). |
| `DERIVED_FILE_DIR=.context/export-plan-library-task-2 scripts/export-plan-library.sh --check` | Passed: exported 25 plans and `PlanLibrary.json matches the source-audited definitions`. It emitted two pre-existing unused-binding warnings in `BoardPackageStore.swift` for `suspension` and `orientation`. |
| Generated-catalog audit | Passed: `jq` found 11 `handUse: either` entries, only `max-hangs-1...5` and `abrahangs-grip-1...6`. |
| `git diff --check` | Passed. |
| Focused XCTest command covering live presentation, custom-preview toggle, board-backed positive/negative either validation, and bundled eligibility | Blocked before test execution because CoreSimulator was unavailable. Exact error: `CoreSimulatorService connection became invalid. Simulator services will no longer be available.` The service also reported: `Cannot talk to the service used to manage runtime disk images (simdiskimaged) because its launchd job is not registered or was unloaded`. |
| Visual simulator validation | Blocked for the same CoreSimulator service failure; no simulator was created or retried. |

## Residual concerns

Focused XCTest and visual simulator validation require a healthy CoreSimulator
service. The changed SwiftUI/editor code compiled successfully, and source/
generated parity passed, but the focused tests and live visual L/R-picker
exercise should be rerun after CoreSimulator and `simdiskimaged` are restored.

## Amendment — custom either-hand target semantics

Board-specific custom targets persist an exact `contactID` only for explicit
single-hand picks. Either-hand picks retain generic factual requirements, so
their preview resolves and displays both valid left/right alternatives before a
session-side choice materializes one of them. Double-hand targets retain their
documented bilateral-pair resolution. `CustomRoutineDraftTests` cover generic
either persistence, both-alternative preview, removal, and exact single-pick
behavior separately.

## Amendment — generic custom-target scope

Exact custom contact IDs are now scoped to board-specific routines. Retargeting
a new board-specific draft to generic mode removes the exact ID while retaining
the selected contact's factual kind/features/capacities and selection policy;
switching an unsaved board-specific draft to a different board also removes the
old board identity. Store normalization applies the same migration to older
generic persisted definitions, while validation rejects any unnormalized
generic exact ID. This keeps right-side mirror picks exact on their selected
board and leaves bilateral-pair behavior unchanged.

The final follow-up `xcodebuild build-for-testing` compilation of `HangTenTests`
passed after the resolver, preview, persistence, and fixture corrections.
Focused runtime execution remains unavailable because CoreSimulator does not
provide the requested `iPhone 16 Pro` destination; no shared simulator was
repurposed. No bundled catalog or source-plan semantics changed.

## Fix-round amendment — explicit-null decoder handling

Updated `BoardPackageStore` and `BoardPackageWriter` decoders to distinguish
omitted unilateral-hand-resolution metadata from an explicit JSON `null`:
omitted metadata remains backward-compatible as `nil`, while explicit JSON
`null` and unsupported strings are rejected by both decoders.

Focused tests:

- `BoardPackageStoreTests.testStoreRejectsNullAndUnsupportedUnilateralHandResolution`
- `BoardPackageStoreTests.testStoreLeavesOmittedUnilateralHandResolutionNil`
- `BoardPackageWriterTests.testEditorDecoderRejectsNullAndUnsupportedUnilateralHandResolution`
- `BoardPackageWriterTests.testEditorDecoderLeavesOmittedUnilateralHandResolutionNil`

Exact focused test command:

```sh
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=CC149757-8C65-413B-9960-EDF9D6E96994' -derivedDataPath .context/derived-single-hand-task-2 -disableAutomaticPackageResolution -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardPackageWriterTests CODE_SIGNING_ALLOWED=NO
```

The xcresult summary reported `Test - HangTen` on iPhone 17 / iOS 26.3.1:
153 passed, 0 failed, 0 skipped. `build-for-testing` exited 0, and
`git diff --check` passed. These focused checks cover the two named decoder
test suites only; they do not establish coverage of other areas.

## Fix-round amendment — BoardRevision positional compatibility

Addressed the CodeRabbit finding that required positional
`unilateral_hand_resolution` shifted the existing positional
`model_contact_frames` argument. Changed `board_catalog.py` to make
`unilateral_hand_resolution` keyword-only with a `None` default, and updated
`_load_board` to pass it by keyword. Added a regression in
`test_board_catalog.py`; no other source files were changed.

TDD evidence: the regression first failed as expected because
`model_contact_frames` remained empty and the positional mapping landed in
`unilateral_hand_resolution`; after the implementation change it passed.

Exact focused command:

```sh
rtk .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_board_catalog.py::test_board_revision_preserves_positional_model_contact_frames_argument -q
```

Result: 1 passed. Exact full package test command:

```sh
rtk .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests -q
```

Result: 609 passed in 120.84s.

## Fix-round amendment — custom editor hand-use transitions

The custom step editor now routes explicit hand-use changes, the forced
either-to-double transition when changing a step to pull, and the forced
either-to-double transition for isometric pull through
`CustomRoutineStepDraft.transitionHandUse(to:)`. The transition sets the
compatible side, removes exact contact identity for either/double, selects
`.bilateralPair` for double-hand requirements, and preserves factual kind,
features, depth, capacity, and grip constraints. Rest-phase target clearing is
unchanged.

Regression tests cover single-to-either resolution of both mirrored sides,
single-to-double and stale-either-to-double bilateral pairing, and saving a
board-specific routine after an actual left-hold tap followed by either-hand
selection. The save case checks the identity-neutral factual requirement,
left/right preview resolution, validator acceptance, and persisted store value.

TDD red evidence before the transition helper:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=CC149757-8C65-413B-9960-EDF9D6E96994' -derivedDataPath .context/derived-pr422-editor-handuse -disableAutomaticPackageResolution -only-testing:HangTenTests/CustomRoutineDraftTests/testChangingSingleHandToEitherClearsExactContactAndResolvesBothHands -only-testing:HangTenTests/CustomRoutineDraftTests/testChangingSingleHandToDoubleUsesBilateralPairAndPreservesRequirementFacts -only-testing:HangTenTests/CustomRoutineDraftTests/testChangingEitherHandWithStaleExactTargetToDoubleUsesBilateralPair CODE_SIGNING_ALLOWED=NO
```

Result: 3 tests, 6 expected assertion failures. The exact `left` ID remained,
either-hand preview returned only `left`, and double-hand requirements remained
`.single` instead of `.bilateralPair`.

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=CC149757-8C65-413B-9960-EDF9D6E96994' -derivedDataPath .context/derived-pr422-editor-handuse -disableAutomaticPackageResolution -only-testing:HangTenTests/CustomRoutineStoreTests/testBoardSpecificEitherHandSidedTapRemainsSaveableForBothSides CODE_SIGNING_ALLOWED=NO
```

Result: 1 test, 5 expected assertion failures; the sided exact-ID target did
not resolve for both sides, validation reported `unresolvableTargets`, and
`CustomRoutineStore.save` threw `validationFailed`.

Four-case green command after wiring both implicit editor paths through the
helper:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=CC149757-8C65-413B-9960-EDF9D6E96994' -derivedDataPath .context/derived-pr422-editor-handuse -disableAutomaticPackageResolution -only-testing:HangTenTests/CustomRoutineDraftTests/testChangingSingleHandToEitherClearsExactContactAndResolvesBothHands -only-testing:HangTenTests/CustomRoutineDraftTests/testChangingSingleHandToDoubleUsesBilateralPairAndPreservesRequirementFacts -only-testing:HangTenTests/CustomRoutineDraftTests/testChangingEitherHandWithStaleExactTargetToDoubleUsesBilateralPair -only-testing:HangTenTests/CustomRoutineStoreTests/testBoardSpecificEitherHandSidedTapRemainsSaveableForBothSides CODE_SIGNING_ALLOWED=NO
```

Result: all 4 tests passed, 0 failures.

Final focused suite command:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=CC149757-8C65-413B-9960-EDF9D6E96994' -derivedDataPath .context/derived-pr422-editor-handuse -disableAutomaticPackageResolution -only-testing:HangTenTests/CustomRoutineDraftTests -only-testing:HangTenTests/CustomRoutineStoreTests CODE_SIGNING_ALLOWED=NO
```

Result: 71 tests passed, 0 failures, after wiring the phase and action
transitions through the same model helper.

Compile-only test build:

```sh
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/derived-pr422-editor-handuse -disableAutomaticPackageResolution CODE_SIGNING_ALLOWED=NO
```

Result: exit 0. `rtk git diff --check` passed. No catalog or source-plan files
were changed.
