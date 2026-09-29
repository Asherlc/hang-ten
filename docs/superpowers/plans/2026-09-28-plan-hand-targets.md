# Per-Hand Plan Targets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every bundled plan encodes each hand's target and every cue highlights the complete current grip.

**Architecture:** Replace bundled work-target requirement lists with ordered arrays of one or two hand targets. Decode saved legacy routines at the persistence boundary, then use one simultaneous assignment resolver for board compatibility, preview, live cues, and recording. Preserve old activity records.

**Tech Stack:** Swift, SwiftUI, XCTest, JSON Schema 2020-12, the existing plan exporter, iOS Simulator.

**Spec:** [Per-hand plan targets](../specs/2026-09-28-plan-hand-targets-design.md)

## Global Constraints

- Bundled plans default to two hands unless their source explicitly specifies one hand.
- Preserve source-backed task order, timing, grip descriptions, repetitions, and provenance; record source URLs and per-step audit mappings.
- `tasks` contains ordered arrays of one or two hand targets; no `Task` wrapper, `hands`, `allowSwap`, or selection policy.
- `Depth` is a `$defs` reference: category or `{minMM,maxMM}`, with equal bounds for an exact measurement.
- On a one-hand board, a two-hand task requires two boards and never silently alternates.
- Keep legacy custom-routine decoding and historical activity decoding intact.
- Generated output stays in `.context`; own and clean up isolated simulator resources.

## Review Focus

1. Two different holds in one task resolve simultaneously, with neither dropped (Task 2).
2. Two equal targets may use one documented capacity-two contact or two distinct contacts (Task 2).
3. A one-hand board requires two copies for a two-hand task, including in user-facing copy (Tasks 2 and 5).
4. Multi-task work without source-backed subtask durations advances only by athlete action (Task 5).
5. Old custom routines and activity history remain readable and behaviorally equivalent (Tasks 3 and 5).

---

### Task 1: Authored schema and depth

**Files:** Create `docs/schemas/PlanWorkTarget.schema.json`; modify `HangTen/Models/TrainingModels.swift`, `HangTen/Models/PlanStorage.swift`; test in `HangTenTests/WorkoutSegmentTargetTests.swift`.

**Interfaces:** `PlanContactPredicate(kind: HoldKind?, shape: HoldShape?, depth: PlanDepth?, fingerCapacity: Int?)`; `PlanHandTarget(target: PlanContactPredicate, side: WorkoutSide?)`; `WorkoutSegmentTarget.tasks([[PlanHandTarget]])`. `PlanDepth` uses the new wire shape and converts to `HoldDepth` for matching; board metadata keeps its current wire format. Legacy decoding remains available until Task 3.

- [ ] Write tests for one- and two-entry tasks; categorical, exact, and ranged depths; unknown keys; three-hand tasks; unordered/negative/nonfinite bounds.
- [ ] Run focused tests and confirm the new-format cases fail.
- [ ] Implement the JSON Schema and matching strict Swift decoding/encoding. Keep the existing `HoldDepth.matches` semantics and validate cross-field numeric bounds in Swift; do not alter board JSON encoding.
- [ ] Run focused tests; confirm they pass, then commit.

### Task 2: Simultaneous contact assignment

**Files:** Modify `HangTen/Models/WorkoutActivityRecording.swift`, `HangTen/Models/WorkoutTimeline.swift`, `HangTen/Models/AppStore.swift`, `HangTen/Models/PlanStorage.swift`; test in `HangTenTests/WorkoutTimelineTests.swift`, `HangTenTests/PlanStorageTests.swift`.

**Interfaces:** `ContactResolver.resolve(_ task: [PlanHandTarget], step: WorkoutStep, board: BoardRevision) throws -> [PhysicalContact]`; `resolve(_ tasks: [[PlanHandTarget]], ...)` preserves task boundaries. Callers use assignment results, not flattened `workRequirements`.

- [ ] Write failing tests for asymmetric edge/sloper, paired edges, one shared capacity-two hold, capacity-one board with two copies, explicit side, missing second hold, and compatibility across all tasks.
- [ ] Implement deterministic assignment against default-presentation contacts and board capacity; reject a capacity-one contact used by two hands on one board.
- [ ] Route compatibility and validation through task resolution. Run focused tests; commit.

### Task 3: Persistence and legacy migration

**Files:** Modify `HangTen/Models/PlanStorage.swift`, `HangTen/Models/CustomRoutineDraft.swift`, `HangTen/Models/CustomRoutineStore.swift`, `HangTen/Models/TrainingModels.swift`; test in `HangTenTests/PlanStorageTests.swift`, `HangTenTests/CustomRoutineStoreTests.swift`, `HangTenTests/WorkoutSegmentTargetTests.swift`.

**Interfaces:** Bundled definitions encode `target.tasks`; legacy `target.kind/requirements`, `selection`, step `handUse/side`, and custom routine files decode and translate to task assignments. New custom writes use `tasks`; historical activity data retains its decoder.

- [ ] Write failing fixture tests for old single, bilateral, mixed-target, and self-selected plans; persisted custom routines; exact contact pins; and new-format round trips.
- [ ] Implement translation with explicit handling for ambiguous legacy multi-requirement work; do not guess whether requirements were simultaneous or sequential in bundled content.
- [ ] Run persistence and validation tests; commit.

### Task 4: Source audit and bundled-plan export

**Files:** Modify `HangTen/Models/TrainingModels.swift`, `HangTen/Models/PlanStorage.swift`, `HangTen/Resources/PlanLibrary.json`, `docs/ADDING_A_ROUTINE.md`; create `docs/plan-audits/2026-09-28-per-hand-plan-migration.md`; test in `HangTenTests/BoardTargetSubstitutionTests.swift`, `HangTenTests/PlanStorageTests.swift`.

**Interfaces:** Every work segment in the 26 built-in plans exports `tasks`, including empty `tasks` only for audited self-selected exceptions. No bundled segment exports `selection`, `handUse`, or `side` as hand-count substitutes.

- [ ] Audit each source against its steps: record URL, one/two-hand basis, simultaneous versus sequential target grouping, and any unresolved contact mapping. Cover known one-arm instructions and the Metolius hold ladder explicitly.
- [ ] Write failing catalog tests for all work targets using the new format, sourced one-hand cases, the 7/3 two-hold cue, and resolution on every offered board.
- [ ] Change seed definitions, export with `scripts/export-plan-library.sh`, then run `--check`; add `scripts/validate-plan-work-targets.sh` and `scripts/plan-schema-requirements.txt` using Python `jsonschema`, installed into `.context`, to validate every exported work target against the checked-in schema.
- [ ] Run catalog tests and export check; commit.

### Task 5: Preview, workout, and recording

**Files:** Modify `HangTen/Views/RootView.swift`, `HangTen/Models/WorkoutTimeline.swift`, `HangTen/Models/WorkoutActivityRecording.swift`, and relevant cue views; test in `HangTenTests/WorkoutActivityRecordingTests.swift`, `HangTenTests/WorkoutTimelineTests.swift`, and a focused UI test.

**Interfaces:** Preview and live cues display the current task's entire resolved assignment. A multi-task segment with no authored subtask timing has manual next/previous task controls; changing task does not change the segment timer. Recording snapshots the assignment actually active for performed tasks.

- [ ] Write failing tests for first-task preview, complete two-hand highlight, manual ladder advance, unchanged timing, two-board explanation, and recorded contact IDs.
- [ ] Implement task cursor and UI; preserve existing rest and source-backed timing. Run focused unit/UI tests.
- [ ] Preview paired, asymmetric, sequential, and one-board/two-board cases on an isolated simulator; capture evidence under `.context`, remove exact owned simulator resources, and verify removal. Commit.

### Task 6: Final integration

**Files:** Any files above only for failures found during verification.

- [ ] Run the plan exporter `--check`, schema validation, relevant unit/UI suites, and an iOS build.
- [ ] Verify all 26 plan IDs, source-audit coverage, target compatibility, and clean `git diff --check`.
- [ ] Review the branch against the spec, fix concrete gaps, commit fixes, and push every new commit.
