# Unversioned Custom Routines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Persist custom routines in one unversioned envelope and remove routine schema compatibility code.

**Architecture:** `CustomRoutineLibrary` contains only routines; `CustomRoutineStore` retains routine-content validation but no schema guard. There are no existing user routines to migrate, so stale versioned data is rejected.

**Tech Stack:** Swift Codable, UserDefaults, XCTest.

**Spec:** `docs/superpowers/specs/2026-08-24-unversioned-content-formats-design.md`

## Global Constraints

- Routine JSON is exactly an envelope containing `routines`.
- `currentSchemaVersion` and unsupported-schema handling are removed.
- Content normalization such as unsupported cue stripping remains; it is not schema-version fallback.

### Task 1: Define the strict persisted envelope

**Files:** Modify `HangTen/Models/CustomRoutineStore.swift` and `HangTenTests/CustomRoutineStoreTests.swift`.

- [ ] Add failing tests that `JSONEncoder().encode(CustomRoutineLibrary(routines: []))` has no `schemaVersion`, and that decoding `{"schemaVersion":1,"routines":[]}` throws.
- [ ] Run `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/CustomRoutineStoreTests`; expect failure because the old envelope emits and requires the field.
- [ ] Replace the model with `struct CustomRoutineLibrary: Codable, Hashable { let routines: [CustomRoutineDefinition] }`; remove its custom CodingKeys/encode/decode, `currentSchemaVersion`, the store version guard, and `CustomRoutineStoreError.unsupportedSchema`.
- [ ] Rerun the focused target and assert a save-load round trip persists only `routines`; expect pass.
- [ ] Commit: `git add HangTen/Models/CustomRoutineStore.swift HangTenTests/CustomRoutineStoreTests.swift && git commit -m "Remove custom routine schema versions"`.

### Task 2: Audit all in-scope content boundaries

**Files:** Modify `HangTenTests/BoardSourceBoundaryAudit.swift`, `HangTenTests/BoardSourceBoundaryTests.swift`, and only fixtures made obsolete by compile/test failures.

- [ ] Add `testBundledContentDoesNotContainSchemaVersion`, enumerating every `Hangboards/*/board.json` plus `PlanLibrary.json` and asserting the root key is absent; also assert plan metadata has no `version`.
- [ ] Run `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardSourceBoundaryAudit`; expect failure until the board/plan work is complete.
- [ ] Delete stale version fixtures and assertions in the board, plan, and routine tests. Do not change workout-session migration fixtures or release-version checks.
- [ ] Run the full affected verification:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro'
(cd Tools/HangboardWorkbench && npm test)
uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests Tools/HangboardPackages/tests
```

- [ ] Commit: `git add HangTenTests && git commit -m "Audit unversioned bundled content"`.
