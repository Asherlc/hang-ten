# Source-Grounded Plan Cues Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep cue and instruction-card content only when it is supported by the linked training plan, while preserving faithful source adaptations and hiding unsupported fields.

**Architecture:** Keep the existing cue-aware models and views, but make cue resolution provenance-aware: explicit step cue data can render, while board defaults cannot manufacture a prescription. Add a field-level source audit for all built-in plans, clean the seed/export data from unsupported additions, and make the instruction/accessory card omit empty or unsupported fields. Custom routines retain no source-claiming cue controls or persisted cue values.

**Tech Stack:** Swift 5/Xcode 26, SwiftUI, XCTest, schema-versioned JSON, shell exporter.

## Global Constraints

- Faithful paraphrases and necessary timer/UI formatting are allowed when the source fact remains identifiable.
- Do not present an invented exercise, count, duration, interval, hold/finger requirement, safety prescription, warm-up, cooldown, instruction-card text, accessory label, or coaching claim as source fact.
- An app-specific timer or concise instruction adaptation is allowed only when the source task remains identifiable and the UI/metadata labels the addition as an app adaptation.
- A chosen value from a source range must be identified as an app adaptation, not presented as the source’s exact prescription.
- `BoardHold.gripType`, `fingerCapacity`, and `cueStyle` remain physical-board metadata and cannot be used as routine provenance.
- Old persisted JSON must decode safely, but unsupported cue data must not be re-emitted by built-in-plan export or custom-routine save.
- Preserve the user’s unrelated untracked `paseo.json` file.
- Every implementation task uses a fresh subagent, a focused test cycle, a task review, and a commit pushed to the current remote branch.

---

### Task 1: Create the source audit and clean built-in plan data

**Files:**
- Create: `docs/source-audits/2026-08-10-plan-cue-provenance.md`
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Resources/PlanLibrary.json` via `scripts/export-plan-library.sh`
- Test: `HangTenTests/PlanStorageTests.swift`

**Interfaces:**
- Consumes: the ten linked source URLs listed in the design spec and the current `LegacyPlanSeedCatalog`/`PlanLibrary.json` definitions.
- Produces: a field-level audit and source-clean built-in seed data consumed by the existing plan resolver and UI.

- [ ] **Step 1: Write the failing provenance regression test**

  Add a test that loads the exported built-in library and asserts that every
  non-empty visible instruction/accessory and every built-in `gripType` or
  `fingerConfiguration` value has a corresponding keep/adapt entry in the new
  audit document. Assert that any app-specific timer adaptation is labeled as
  such and is never represented as a manufacturer-prescribed duration.

- [ ] **Step 2: Run the focused test to verify it fails**

  Run:

  ```sh
  xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/PlanStorageTests
  ```

  Expected: FAIL because the current exported plan data contains cue/accessory
  fields without a field-level audit and does not distinguish app timing from
  source-prescribed duration.

- [ ] **Step 3: Write the field-level source audit**

For all 20 built-in plans, record plan ID, source URL, source type, and a
  keep/adapt/remove decision for title, subtitle, instruction, accessory,
  target, count, duration, interval, warm-up, cooldown, `gripType`, and
  `fingerConfiguration`. Use these source facts as the baseline:

  - Metolius explicitly specifies the three ten-minute task sequences,
    task-level durations/counts, finger-count phrases, hand switches, stay-on
    transitions, failure/max instructions, and remaining-minute rest.
  - The Frontiers F80/F100 study specifies the force-board hold depth, force
    percentages, 10/6 F80 intervals, 12-repetition maximum, three F80 sets,
    eight-minute recoveries, and the F100 six-second alternating-hand protocol.
  - The Beastmaker study specifies two identical sets, six hang series, seven
    repetitions per series, 7/3 timing, 2:30 between series, and six minutes
    between sets; its changing difficulty includes hold size/finger count but
    does not prescribe Hang Ten’s Compact II mapping.
  - Lattice Max Hangs explicitly supports seven-second half-crimp,
    four-finger, near-maximal hangs on a 20 mm edge with loading/assistance.
  - Lattice Abrahangs explicitly names half-crimp/open positions and the
    four-, three-, and two-finger variants shown on its page.
  - The Hörst page explicitly specifies 7/53, three hangs per set, 3–5 minute
    between-set recovery, and half/open-crimp or pocket options.
  - Bechtel’s 3–6–9 page specifies the 3/6/9 sequence, 3–5 sets, and rest
    ranges; Nelson’s Density Hangs page specifies 20–40 seconds, 10–20 seconds
    at a 2:1 ratio, 2–3 reps, and 3–5 minute set recovery; the Zlagboard page
    specifies ten 60/60 sets.
  - The Eva López PubMed record supports the published maximal/intermittent
    dead-hang study, but fields not present in the linked record must not be
    presented as exact source prescription.

  Mark board-specific Compact II hold substitutions and values selected from a
  source range as app adaptations, not source facts.

- [ ] **Step 4: Remove unsupported seed data without changing source tasks**

  Update `LegacyPlanSeedCatalog` so it no longer emits generic
  warm-up/cooldown text, unsupported coaching prose, or grip overrides that the
  audit marks remove. Preserve source-backed task counts, durations, target
  names, finger-count language, switch/stay-on/max qualifiers, and faithful
  concise paraphrases. If a timer must adapt a source task that has no
  task-local duration, keep the source task identifiable and label the timer as
  an app adaptation; do not encode it as the manufacturer’s duration. Keep
  source-range adaptations only when their source basis is recorded in the
  audit.

- [ ] **Step 5: Regenerate and run the test green**

  Run:

  ```sh
  scripts/export-plan-library.sh
  scripts/export-plan-library.sh --check
  xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/PlanStorageTests
  ```

  Expected: exporter check passes, the focused tests pass, and the generated
  JSON matches the audited seed with source facts and labeled adaptations only.

- [ ] **Step 6: Commit and push**

  ```sh
  git add docs/source-audits/2026-08-10-plan-cue-provenance.md HangTen/Models/TrainingModels.swift HangTen/Resources/PlanLibrary.json HangTenTests/PlanStorageTests.swift
  git commit -m "data: audit built-in plan cue provenance"
  git push origin HEAD
  ```

### Task 2: Make cue resolution source-aware while preserving backed cues

**Files:**
- Modify: `HangTen/Models/WorkoutTimeline.swift`
- Modify: `HangTen/Views/RootView.swift`
- Modify: `HangTen/Views/GripDiagramView.swift` only where needed for optional backed cue values
- Test: `HangTenTests/WorkoutTimelineTests.swift`

**Interfaces:**
- Consumes: audited optional step cue values from Task 1 and the existing
  `WorkoutHoldCuePolicy`/`WorkoutHoldCueVisibilityPolicy` APIs.
- Produces: cue cards that render explicit source-backed cue values and remain
  absent when a step has no source-backed posture/finger prescription.

- [ ] **Step 1: Write failing timeline tests**

  Replace the current test that expects board-grip fallback with a test named
  `testHoldCueDoesNotInferGripFromBoardMetadata`. It must construct a step with
  a matching target but no explicit cue and assert that the policy returns no
  cue. Keep a test proving an explicit `.halfCrimp` plus exact fingers survives,
  and add a test proving a source-backed cue remains visible at countdown zero.

- [ ] **Step 2: Run the focused timeline tests to verify failure**

  ```sh
  xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/WorkoutTimelineTests
  ```

  Expected: FAIL because `WorkoutHoldCuePolicy` currently falls back to
  `BoardHold.gripType`.

- [ ] **Step 3: Remove the unsupported fallback and preserve explicit cues**

  Change `WorkoutHoldCuePolicy.resolve` so it requires explicit step-level
  source-backed cue data before constructing a `WorkoutHoldCue`. It may use the
  matching `BoardHold` for the physical hold name/image, but it must never use
  `hold.gripType` or `hold.fingerCapacity` to create a prescription. Keep the
  existing countdown/completion suppression behavior.

- [ ] **Step 4: Make both layouts conditionally render the backed cue**

  Update `PlanDetailView`, portrait workout layout, landscape side slots, and
  any DEBUG preview path so the cue card appears only when the resolved cue has
  explicit source-backed content. Keep board-map highlights independent. Do not
  remove `GripDiagramView`, `GripHandCueCard`, or their assets when a backed cue
  still uses them.

- [ ] **Step 5: Run focused tests and build**

  ```sh
  xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/WorkoutTimelineTests
  xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData build
  ```

  Expected: timeline tests pass and the Debug app builds with both portrait and
  landscape cue paths compiled.

- [ ] **Step 6: Commit and push**

  ```sh
  git add HangTen/Models/WorkoutTimeline.swift HangTen/Views/RootView.swift HangTen/Views/GripDiagramView.swift HangTenTests/WorkoutTimelineTests.swift
  git commit -m "fix: show only source-backed grip cues"
  git push origin HEAD
  ```

### Task 3: Remove unsupported instruction-card text and custom cue persistence

**Files:**
- Modify: `HangTen/Views/RootView.swift`
- Modify: `HangTen/Models/CustomRoutineDraft.swift`
- Modify: `HangTen/Views/CustomRoutineEditorView.swift`
- Modify: `HangTen/Models/PlanStorage.swift`
- Modify: `HangTen/Models/CustomRoutineStore.swift` to strip legacy cue fields
  during custom-routine save conversion
- Test: `HangTenTests/CustomRoutineDraftTests.swift`
- Test: `HangTenTests/CustomRoutineStoreTests.swift`
- Test: `HangTenTests/PlanStorageTests.swift`

**Interfaces:**
- Consumes: source-clean instruction/accessory values from Task 1 and
  source-aware cue resolution from Task 2.
- Produces: an instruction/accessory card that hides empty unsupported fields,
  and custom routines that no longer create or re-emit unsupported cue data.

- [ ] **Step 1: Write failing card and persistence tests**

  Add tests for the card’s display model (or the smallest existing testable
  helper) proving an empty instruction and empty accessory produce no text row,
  while a source-backed instruction/accessory pair remains. Add a persistence
  fixture containing legacy `gripType` and `fingerConfiguration` keys and assert
  that a custom draft loads without exposing them and that saving the definition
  does not encode them.

- [ ] **Step 2: Run focused tests to verify failure**

  ```sh
  xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/CustomRoutineDraftTests -only-testing:HangTenTests/CustomRoutineStoreTests -only-testing:HangTenTests/PlanStorageTests
  ```

  Expected: FAIL because the current card always renders instruction/accessory
  strings and custom routine editing/persistence still exposes cue fields.

- [ ] **Step 3: Hide unsupported card fields without replacing them**

  Update the instruction/accessory card to render each row only when its
  trimmed value is non-empty. Do not insert replacement coaching copy. Keep
  source-backed task wording and faithful adaptations unchanged.

- [ ] **Step 4: Remove custom-routine cue editing and normalize legacy data**

  Remove the custom editor’s Grip picker, Fingers menu, finger bindings, and
  draft mutation paths. Keep legacy decoding tolerant in `WorkoutStepDefinition`
  but ensure `CustomRoutineDraft` ignores those values and its save conversion
  writes no unsupported cue keys. Preserve custom titles, instructions,
  accessories, timing, phases, and hold targets.

- [ ] **Step 5: Run focused tests and exporter verification**

  ```sh
  scripts/export-plan-library.sh --check
  xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/CustomRoutineDraftTests -only-testing:HangTenTests/CustomRoutineStoreTests -only-testing:HangTenTests/PlanStorageTests
  ```

  Expected: exporter check and all focused tests pass, with legacy cue keys
  accepted on decode but absent after save.

- [ ] **Step 6: Commit and push**

  ```sh
  git add HangTen/Views/RootView.swift HangTen/Models/CustomRoutineDraft.swift HangTen/Views/CustomRoutineEditorView.swift HangTen/Models/PlanStorage.swift HangTen/Models/CustomRoutineStore.swift HangTenTests/CustomRoutineDraftTests.swift HangTenTests/CustomRoutineStoreTests.swift HangTenTests/PlanStorageTests.swift
  git commit -m "fix: remove unsupported instruction and custom cue data"
  git push origin HEAD
  ```

### Task 4: Whole-branch verification and provenance sweep

**Files:**
- Modify: `README.md` to describe source-backed cues and labeled adaptations
- Modify: `docs/ADDING_A_ROUTINE.md` to require field-level provenance for cue
  and instruction-card content
- Test: all `HangTenTests`

**Interfaces:**
- Consumes: all accepted commits from Tasks 1–3.
- Produces: verified source/export/UI behavior with no stale claims or
  unsupported cue fallbacks.

- [ ] **Step 1: Add regression searches**

  Add or update tests/checks so the built-in exported JSON contains no
  unsupported cue or instruction-card values identified as remove in the audit,
  while source-backed cue values remain present where required.

- [ ] **Step 2: Run the full verification suite**

  ```sh
  scripts/export-plan-library.sh --check
  xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test
  xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData build
  rtk rg -n "gripType \?\? hold\.gripType|customRoutine.stepGrip|customRoutine.stepFingers" HangTen HangTenTests HangTen/Resources/PlanLibrary.json
  ```

  Expected: exporter, all tests, and build pass; the final search returns no
  board-grip fallback or custom cue-editor symbols, and the audit-backed
  regression checks cover every retained cue/adaptation.

- [ ] **Step 3: Commit and push documentation-only corrections**

  ```sh
  git add README.md docs/ADDING_A_ROUTINE.md HangTenTests
  git commit -m "docs: verify source-grounded plan cues"
  git push origin HEAD
  ```
