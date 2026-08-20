# Resolve Constrained Shape Merge Conflicts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge current `origin/main` into `change-hold-outline-shape` while preserving both the new main-branch board/package behavior and the constrained hold-shape feature.

**Architecture:** Resolve the merge at the shared schema boundaries instead of choosing either side wholesale. Keep main's newer board geometry, source-boundary, and Trango Rock Prodigy Pivot behavior, then layer the optional `shapeConstraint` parsing, validation, persistence, and Swift compatibility into those updated implementations.

**Tech Stack:** Git, Python 3.11/pytest, vanilla JavaScript/Node test runner, Swift 5.10/XCTest

**Spec:** `docs/superpowers/specs/2026-08-19-constrained-hold-shapes-design.md`

## Global Constraints

- Preserve every behavior and test introduced by `origin/main` at `668d70c205c464bef5b5968875487a833aa58114`.
- Preserve the complete constrained-shape contract already reviewed at `8f658e98be848cd13aca83448f1f98de2f4e357b`.
- `shapeConstraint.shape` remains exactly `oval`, `circle`, `pill`, `roundedRectangle`, or `rectangle`.
- `shapeConstraint.rotationDegrees` remains finite and normalized to `[-180, 180)`.
- Existing `frame` and `shape` remain the only runtime rendering geometry; absence of `shapeConstraint` remains Custom/freeform.
- Do not introduce board-specific conflict workarounds, force-push, rebase published history, or discard either side wholesale.

---

### Task 1: Merge main and reconcile shared schema consumers

**Files:**
- Modify only files reported as conflicted by `git merge --no-ff origin/main`.
- Test the existing Workbench, pipeline, macOS Swift, and focused iOS decoder suites.

**Interfaces:**
- Consumes the updated board/package model from `origin/main` and the optional piece-level constrained-shape schema from the feature branch.
- Produces one ordinary merge commit on `change-hold-outline-shape` with no unresolved markers and no loss from either parent.

- [ ] **Step 1: Reproduce and inventory the conflicts**

Run:

```bash
rtk git merge --no-ff origin/main
rtk git status --short
rtk git diff --name-only --diff-filter=U
```

Expected: Git reports conflicts only in the overlapping package/schema implementation and test files. Record their exact paths before editing.

- [ ] **Step 2: Resolve each conflicted hunk semantically**

For every conflicted implementation hunk, begin with main's updated structure and retain the feature branch's strict optional `shapeConstraint` behavior at the equivalent boundary. For every test hunk, retain both main's new coverage and the constrained-shape coverage. Remove all conflict markers and do not change cleanly merged files unless verification identifies a direct integration defect.

- [ ] **Step 3: Verify the merge result**

Run:

```bash
rtk git diff --check
rtk rg '^(<<<<<<<|=======|>>>>>>>)' --glob '!docs/superpowers/plans/*.md'
rtk node --test Tools/HangboardWorkbench/tests/*.test.js
rtk uv run --project Tools/HangboardPipeline --with pytest python -m pytest -q Tools/HangboardWorkbench/tests
rtk uv run --project Tools/HangboardPipeline --with pytest python -m pytest -q Tools/HangboardPipeline/tests
rtk swift test --package-path Tools/HangboardWorkbench/macos
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/BoardPackageStoreTests
```

Expected: no conflict markers or diff errors and every suite passes.

- [ ] **Step 4: Commit the resolved merge**

Stage only the exact conflicted paths plus this plan, then create the merge commit:

```bash
rtk git commit -m "Merge main into constrained hold shapes"
```
