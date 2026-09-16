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

## Amendment — mirrored custom-contact preservation

Board-specific custom targets now persist an optional exact `contactID` in
their `ContactRequirement`. This prevents a right-side tap on a symmetric
board from being re-resolved to its otherwise identical left-side alternative.
The constraint is written only for single/either custom picks; double-hand
targets retain their documented bilateral-pair resolution. The added
`CustomRoutineDraftTests` regression covers left removal, right selection,
JSON persistence, right preview, and right removal.
