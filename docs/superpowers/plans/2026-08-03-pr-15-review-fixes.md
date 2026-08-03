# PR 15 Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct automatic stopwatch finalization at workout step boundaries and preserve schema-v2 timed-rest intervals in recorded activity metadata.

**Architecture:** Keep stopwatch lifecycle state in `WorkoutView`, but finalize the prior step by its stable step ID whenever the timeline changes steps. Keep schema migration compatibility in `PlanDefinitionResolver.resolveSegments`, deriving a fixed rest segment only for the legacy `activeDuration` remainder so the existing recorder can serialize it without special cases.

**Tech Stack:** SwiftUI, Swift value types, XCTest, Xcode iOS targets.

## Global Constraints

- All production behavior changes require a regression test that fails before the fix and passes after it.
- Preserve the existing `(stepID, segmentIndex)` stopwatch key contract.
- Preserve legacy schema-v2 semantics: a timed work interval is followed by the positive remainder of the enclosing step as fixed rest.
- Do not change GitHub review-thread state or post review replies from the implementation workspace.

---

### Task 1: Finalize stopwatches at automatic step boundaries

**Files:**
- Modify: `HangTen/Views/RootView.swift:672-746,1330-1375`
- Test: the existing workout stopwatch/timeline XCTest files, or a focused test file registered in `HangTen.xcodeproj/project.pbxproj` if a pure boundary helper is introduced.

**Interfaces:**
- Consumes: `WorkoutStep.id`, `WorkoutActivitySegmentKey`, `WorkoutStopwatch`, and the existing `stopwatches` state dictionary.
- Produces: automatic finalization of all running stopwatch segments belonging to the step that just ended, while preserving explicit skip/jump/end/completion behavior.

- [ ] **Step 1: Write the failing regression test**

  Model a stopwatch started during one step and a timeline transition to a later step. Assert that the first step's stopwatch is finalized at the transition timestamp and does not include elapsed time from the later step. Keep the test independent of SwiftUI rendering by exercising a pure helper/state transition if needed.

- [ ] **Step 2: Run the focused test and verify the expected failure**

  Run the focused XCTest target/test. It must fail because the current implementation only finalizes on `isResting`, which is false for stopwatch-only steps.

- [ ] **Step 3: Implement the minimal boundary fix**

  Add an `onChange(of: step.id)` transition handler to finalize the previous step's stopwatch(s) at the current timeline date. Refactor the existing current-step finalization only as needed to share a step-ID-based helper; do not alter stopwatch duration semantics or unrelated UI behavior.

- [ ] **Step 4: Run focused and related tests**

  Run the stopwatch and timeline tests, then the full iOS simulator XCTest suite. Confirm the new boundary regression and existing lifecycle tests pass.

- [ ] **Step 5: Commit**

  Commit the RootView boundary fix and its regression coverage with a focused message.

---

### Task 2: Preserve schema-v2 derived rest segments

**Files:**
- Modify: `HangTen/Models/PlanStorage.swift:939-977`
- Test: `HangTenTests/PlanStorageTests.swift` (schema-v2 compatibility migration assertions)

**Interfaces:**
- Consumes: `WorkoutStepDefinition.activeDuration`, `WorkoutStepDefinition.duration`, and resolved `targets`.
- Produces: schema-v2 compatibility `WorkoutStep.segments` containing fixed work followed by fixed rest when the positive remainder exists; schema-v3 explicit segments and untimed/untargeted paths remain unchanged.

- [ ] **Step 1: Update the compatibility test expectation**

  In `testSchemaTwoDefinitionsWithoutSegmentsMigrateWithCompatibilitySegments`, assert that the timed legacy step resolves to a fixed work segment of 10 seconds followed by a fixed rest segment of 20 seconds.

- [ ] **Step 2: Run the focused test and verify the expected failure**

  Run the PlanStorage compatibility test. It must fail against the current single-work-segment result.

- [ ] **Step 3: Implement the minimal resolver change**

  Build the existing fixed work segment, append a fixed rest segment only when `step.duration - activeDuration` is positive and finite, then return the ordered array. Keep rest targets nil and avoid deriving zero-length rest records.

- [ ] **Step 4: Run focused and related tests**

  Run all PlanStorage and WorkoutActivityRecording tests, then the full iOS simulator XCTest suite. Confirm explicit v3 segment behavior and recorder ordering remain unchanged.

- [ ] **Step 5: Commit**

  Commit the schema-v2 compatibility fix and test update with a focused message.

---

### Final verification

- [ ] Run the full iOS simulator XCTest suite from the repository's CI-equivalent command.
- [ ] Inspect `git diff origin/main...HEAD` and confirm both review findings map to tested changes.
- [ ] Re-fetch PR #15 review threads to confirm the latest diff no longer leaves these findings technically unaddressed; do not resolve or reply to threads unless explicitly requested.
