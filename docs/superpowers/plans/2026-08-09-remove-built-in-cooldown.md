# Remove Built-in Cooldown Steps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove explicit final cooldown timer steps from all built-in Hang Ten routines while preserving warm-ups, recovery intervals, and backward-compatible cooldown decoding.

**Architecture:** Keep `WorkoutPhase.coolDown` in the runtime/persistence model, but stop creating cooldown steps in `LegacyPlanSeedCatalog`. Simplify `BuiltInPlanLibraryDefinition` so generated built-in libraries contain no shared cooldown block, then regenerate the checked-in JSON resource from the source definition.

**Tech Stack:** Swift, XCTest, Xcode project, generated JSON resource, repository export script.

## Global Constraints

- Remove only the explicit final cooldown timer from built-in routines.
- Do not remove warm-up steps.
- Do not remove or shorten between-set, between-grip, or intra-set recovery.
- Keep the `.coolDown` phase in the model and decoding paths for compatibility.
- Do not redesign workout summary or recovery messaging beyond the absence of a final cooldown step.

---

### Task 1: Remove cooldown generation and refresh the built-in library

**Files:**
- Modify: `HangTenTests/PlanStorageTests.swift` near the existing built-in seed and recovery tests
- Modify: `HangTen/Models/TrainingModels.swift` in `LegacyPlanSeedCatalog`
- Modify: `HangTen/Models/PlanStorage.swift` in `BuiltInPlanLibraryDefinition`
- Modify: `HangTen/Resources/PlanLibrary.json` via `scripts/export-plan-library.sh`
- Test: `HangTenTests/PlanStorageTests.swift`

**Interfaces:**
- Consumes: the existing `LegacyPlanSeedCatalog.all`, `WorkoutPhase.coolDown`, `PlanLibraryStore.builtIn`, and `BuiltInPlanLibraryDefinition.document` APIs.
- Produces: built-in seed plans and the bundled plan library with no final `.coolDown` step and no `shared.cool-down` block; all existing warm-up and recovery step APIs remain unchanged.

- [ ] **Step 1: Write the failing regression test**

Add a focused XCTest beside the existing catalog tests. It should inspect every
plan in `LegacyPlanSeedCatalog.all` and assert that its last step is not
`.coolDown`, assert that `BuiltInPlanLibraryDefinition.document.blocks` has no
block with ID `shared.cool-down`, and assert that the bundled
`PlanLibraryStore.builtIn.plans` also has no final `.coolDown` step. Keep the
existing recovery-duration test unchanged so the regression suite continues to
prove that recovery intervals survive the change.

Use the project’s existing XCTest style, for example:

```swift
func testBuiltInPlansDoNotEndWithCooldownSteps() {
    XCTAssertTrue(
        LegacyPlanSeedCatalog.all.allSatisfy { $0.steps.last?.phase != .coolDown }
    )
    XCTAssertFalse(
        BuiltInPlanLibraryDefinition.document.blocks.contains { $0.id == "shared.cool-down" }
    )
    XCTAssertTrue(
        PlanLibraryStore.builtIn.plans.allSatisfy { $0.steps.last?.phase != .coolDown }
    )
}
```

- [ ] **Step 2: Run the focused test and verify it fails for the intended reason**

Run:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/PlanStorageTests/testBuiltInPlansDoNotEndWithCooldownSteps
```

Expected result before implementation: the test fails because the seed plans
still end in `.coolDown`, the generated document still contains
`shared.cool-down`, or both. If the test cannot run because the named simulator
is unavailable, select an installed iOS Simulator destination and rerun the
same focused test; do not treat a build/setup error as the intended red state.

- [ ] **Step 3: Remove cooldown steps from the source seed catalog**

In `HangTen/Models/TrainingModels.swift`, remove the private
`coolDownStep(id:)` factory and remove every `coolDownStep(...)` append/call in
the built-in plan definitions. Leave all `warmUpStep(...)`, `recoveryStep(...)`,
and hang-step timing untouched. Do not change the `WorkoutPhase.coolDown`
enum, its labels/colors, or Codable behavior.

- [ ] **Step 4: Remove generated shared cooldown handling**

In `HangTen/Models/PlanStorage.swift`, remove the `sharedCoolDown` discovery,
registration, and reference branches from `BuiltInPlanLibraryDefinition`. Keep
the shared warm-up extraction and the existing middle-block construction. The
resulting builder should still create valid definitions when a plan has only a
warm-up or no middle steps, and it must not emit a block or reference named
`shared.cool-down`.

- [ ] **Step 5: Run the focused test and verify it passes**

Run the focused `xcodebuild test` command from Step 2. Expected result: the
new regression test passes, including the source seed, generated definition,
and bundled resource assertions.

- [ ] **Step 6: Regenerate the checked-in plan resource**

Run:

```bash
scripts/export-plan-library.sh
```

This must update `HangTen/Resources/PlanLibrary.json` from the source
definition. Confirm the generated resource no longer contains
`shared.cool-down`, `coolDown`, or final cooldown step IDs, while retaining
warm-up and recovery entries.

- [ ] **Step 7: Run repository verification**

Run:

```bash
scripts/export-plan-library.sh --check
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16'
git diff --check
```

Expected result: the export check succeeds, the full Hang Ten test suite
passes, and `git diff --check` reports no whitespace errors. If the simulator
name is unavailable, use the installed equivalent destination and record the
actual destination in the implementation report.

- [ ] **Step 8: Review the diff and commit the implementation**

Review that the diff is limited to the seed catalog, plan-library builder,
generated resource, and focused regression test; the pre-existing unrelated
worktree changes must remain untouched. Then commit:

```bash
git add HangTen/Models/TrainingModels.swift HangTen/Models/PlanStorage.swift HangTen/Resources/PlanLibrary.json HangTenTests/PlanStorageTests.swift
git commit -m "feat: remove built-in cooldown steps"
```
