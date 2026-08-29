# Compact Single-Hand Hangboards Implementation Plan

> **For agentic workers:** REQUIRED: Use a fresh subagent for every implementation or configuration task. The controller must use `superpowers:subagent-driven-development` with a per-task implementation and review checkpoint; do not substitute `executing-plans`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add every currently sold, primary-source-verifiable compact single-hand hangboard or lifting edge found by a comprehensive manufacturer search, plus only source-complete routines.

**Architecture:** A dated source audit is the inclusion gate. Each admitted physical revision becomes an independent flat board package with a manually drawn presentation and geometry. The routine catalog remains unchanged unless the search finds a fully specified source prescription; any routine is seeded in `TrainingModels.swift` and exported to `PlanLibrary.json`.

**Tech Stack:** JSON board packages, PNG presentation assets, Swift plan seeds, Python package validator, Xcode/iOS Simulator.

**Spec:** `docs/superpowers/specs/2026-08-29-compact-single-hand-hangboards-design.md`

## Global Constraints

- Admit only compact one-hand lifting edges, single-hand portable boards, and rope-suspended compact boards; exclude conventional full-width boards.
- Use direct manufacturer evidence and record URL, review date, revision, visible hold inventory, and exclusions.
- Directly author canonical paths; never derive geometry from image processing or vectorization.
- Omit every unsupported physical fact and every incomplete training prescription.
- Push each commit to the workspace-owned remote branch selected for this work.

---

### Task 1: Create the comprehensive candidate and prescription audit

**Files:**
- Create: `docs/source-audits/2026-08-29-compact-single-hand-hangboards.md`
- Modify: `docs/superpowers/plans/2026-08-29-compact-single-hand-hangboards.md`

**Interfaces:**
- Consumes: the scope definition in the design spec.
- Produces: an inclusion table naming every qualified product/revision and exact source URLs; an exclusion table with reason; a routine table that identifies complete prescriptions or explicitly says none.

- [ ] **Step 1: Write the audit acceptance test**

Add a "Verification" section to the audit requiring a row for the checked manufacturers: Nature Climbing, Lattice, Plateau, Frictitious, Max Climbing, Tension, Metolius, Captain Fingerfood, Problemsolver, AEVORN, Aelith, Two Stones, and Zodiac. Each row must state `included`, `excluded`, or `no current product`, and a primary URL.

- [ ] **Step 2: Verify the test fails**

Run: `test -f docs/source-audits/2026-08-29-compact-single-hand-hangboards.md`

Expected: exit status 1 because the audit does not yet exist.

- [ ] **Step 3: Research and write the source audit**

Search each manufacturer's current catalog and official manuals/product pages. Use the audit to classify: `Nature Stone Hanger Mini`; `Lattice Mini Bar`; `Lattice MXEdge Lift Small`; `Lattice MXEdge Lift Large`; `Plateau Lifting Edge`; `Frictitious Nug`; and `Max One Finger Trainer`, plus every additional product that meets the global category. Treat wood finishes with unchanged hold layouts as variants, not independent packages. Record every product that is excluded for full-width form, discontinued status, no primary evidence, or insufficient geometry.

- [ ] **Step 4: Verify the audit is complete**

Run: `rg -n 'Nature Climbing|Lattice|Plateau|Frictitious|Max Climbing|Tension|Metolius|Captain Fingerfood|Problemsolver|AEVORN|Aelith|Two Stones|Zodiac' docs/source-audits/2026-08-29-compact-single-hand-hangboards.md`

Expected: at least one result for every named manufacturer, with a direct URL and a disposition.

- [ ] **Step 5: Commit and push**

```sh
git add docs/source-audits/2026-08-29-compact-single-hand-hangboards.md docs/superpowers/plans/2026-08-29-compact-single-hand-hangboards.md
git commit -m "docs: audit compact single-hand hangboards"
git push
```

### Task 2: Import every audit-admitted board package

**Files:**
- Create: `Hangboards/<audited-slug>/board.json`
- Create: `Hangboards/<audited-slug>/assets/primary.png`
- Modify: `Tools/HangboardWorkbench/tests/test_approved_board_packages.py`

**Interfaces:**
- Consumes: only `included` product revisions and frozen inventories in the Task 1 audit.
- Produces: complete directly discoverable board packages; every test asserts the exact audited hold IDs rather than counts alone.

- [ ] **Step 1: Write failing package tests**

Add one test per imported package. Each test must load the package through `board_package.load_board_package`, assert its `id` and the exact set of audit-defined hold IDs, assert every hold has `handCapacity == 1`, and assert each declared presentation asset exists. Do not add a test for an excluded candidate.

- [ ] **Step 2: Verify the tests fail**

Run: `rtk python -m pytest Tools/HangboardWorkbench/tests/test_approved_board_packages.py -q`

Expected: failures because the newly audited package directories do not exist.

- [ ] **Step 3: Create presentation assets and direct geometry**

For each included physical revision, use the official straight-on source as evidence to create a clean, simplified, head-on PNG under its declared `assets/` path. Create `board.json` with only source-supported identity and hold metadata. Draw every closed path manually in Workbench, use manually selected constraints only for genuinely regular holds, and review every side independently unless the source proves symmetry.

- [ ] **Step 4: Verify package behavior**

Run:

```sh
rtk python -m pytest Tools/HangboardWorkbench/tests/test_approved_board_packages.py -q
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
```

Expected: all new exact-inventory tests pass and package validation reports no incomplete package.

- [ ] **Step 5: Commit and push**

```sh
git add Hangboards Tools/HangboardWorkbench/tests/test_approved_board_packages.py
git commit -m "feat: add compact single-hand hangboard catalog"
git push
```

### Task 3: Import source-complete compact-board training plans, if any

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Resources/PlanLibrary.json`
- Modify: `HangTenTests/PlanStorageTests.swift`
- Modify: `docs/source-audits/2026-08-29-compact-single-hand-hangboards.md`

**Interfaces:**
- Consumes: Task 1's routine audit and Task 2 factual board IDs/hold IDs.
- Produces: only complete routine definitions whose targets resolve without semantic fabrication.

- [ ] **Step 1: Write a failing plan-resolution test for each admitted routine**

For every routine marked `included` by the audit, add a `PlanStorageTests` assertion that unwraps its exact plan ID, asserts source URL/provenance, and resolves every target on its declared board or on at least one factual compatible board. If the routine audit has no included prescription, add no plan test and document that result in the audit.

- [ ] **Step 2: Verify the test fails**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/PlanStorageTests`

Expected: each new included plan fails to resolve because its seed is not present.

- [ ] **Step 3: Implement only the audited prescriptions**

Add `TrainingPlan` seeds with exact source task order, repetitions, work/rest intervals, laterality, and targets. Use `.official` only when unchanged. For an app-guided expansion, retain every source datum, mark `.adapted`, and update the audit mapping. Do not create a routine from product usage prose or a source that omits runner-visible interval data.

- [ ] **Step 4: Export and verify the library**

Run:

```sh
scripts/export-plan-library.sh
scripts/export-plan-library.sh --check
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/PlanStorageTests
```

Expected: export check passes and every newly included plan-resolution test passes.

- [ ] **Step 5: Commit and push**

```sh
git add HangTen/Models/TrainingModels.swift HangTen/Resources/PlanLibrary.json HangTenTests/PlanStorageTests.swift docs/source-audits/2026-08-29-compact-single-hand-hangboards.md
git commit -m "feat: add audited compact-board training plans"
git push
```

### Task 4: Run final package, app, and source-audit verification

**Files:**
- Modify: `docs/source-audits/2026-08-29-compact-single-hand-hangboards.md`

**Interfaces:**
- Consumes: all imported packages and optional plans.
- Produces: evidence that discovery, staging, plan export, and representative active-hold behavior work.

- [ ] **Step 1: Add failing evidence checklist**

Add unchecked audit checklist entries for package validation, PlanLibrary export check, Xcode build-for-testing, each package's normal/highlight inspection, and simulator cleanup.

- [ ] **Step 2: Verify the checklist is incomplete**

Run: `rg -n '\[ \]' docs/source-audits/2026-08-29-compact-single-hand-hangboards.md`

Expected: unchecked evidence entries exist.

- [ ] **Step 3: Run validations and capture exact outcomes**

Before creating the dedicated simulator, derive its owner from the final component of `${PASEO_WORKTREE_PATH:-$PWD}`, include that owner in the simulator name, and immediately record the exact name and UDID in `.context`. Follow `docs/IOS_SIMULATOR_VALIDATION.md`, inspect representative normal, active, and hit-tested paths for every imported package, record the exact commands/results in the audit, clean up the owned simulator, verify deletion, and mark the evidence checklist complete.

- [ ] **Step 4: Verify all final checks**

Run:

```sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
scripts/export-plan-library.sh --check
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
rg -n '\[ \]' docs/source-audits/2026-08-29-compact-single-hand-hangboards.md
```

Expected: the first three commands exit 0 and the final command returns no unchecked evidence.

- [ ] **Step 5: Commit and push**

```sh
git add docs/source-audits/2026-08-29-compact-single-hand-hangboards.md
git commit -m "test: verify compact single-hand hangboard catalog"
git push
```
