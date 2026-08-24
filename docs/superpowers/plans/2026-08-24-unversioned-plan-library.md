# Unversioned Plan Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Remove plan-library version fields and version-driven compatibility decoding.

**Architecture:** The bundled resource is rewritten once. `PlanLibraryDefinition` and `PlanLibraryMetadata` represent one strict Codable shape; semantic plan validation remains unchanged.

**Tech Stack:** Swift Codable, JSON, XCTest.

**Spec:** `docs/superpowers/specs/2026-08-24-unversioned-content-formats-design.md`

## Global Constraints

- `PlanLibrary.json` has neither root `schemaVersion` nor `metadata.version`.
- No `PlanDefinitionSchema`, unsupported-schema error, or schema migration code remains.
- Former version keys make a document malformed rather than invoking a fallback.

### Task 1: Rewrite and lock the bundled resource

**Files:** Modify `HangTen/Resources/PlanLibrary.json` and `HangTenTests/PlanStorageTests.swift`.

- [ ] Add `testBundledPlanLibraryContainsNoVersionFields`, reading the actual resource and asserting both former keys are absent.
- [ ] Run `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/PlanStorageTests`; expect failure on the current resource.
- [ ] Delete only root `schemaVersion` and `metadata.version` from `PlanLibrary.json`; retain plan, block, mapping, source, and text data unchanged.
- [ ] Rerun the focused test; expect pass.
- [ ] Commit: `git add HangTen/Resources/PlanLibrary.json HangTenTests/PlanStorageTests.swift && git commit -m "Remove versions from bundled plan library"`.

### Task 2: Delete version-aware plan APIs and tests

**Files:** Modify `HangTen/Models/PlanStorage.swift` and `HangTenTests/PlanStorageTests.swift`.

- [ ] Add a failing decoder test for `{"schemaVersion":3,"metadata":{},"boardMappings":[],"blocks":[],"plans":[]}` and assert `PlanLibraryStore(data:)` throws.
- [ ] Replace schema-two migration fixtures with valid unversioned fixtures containing explicit segments; retain segment-resolution expectations.
- [ ] Run the focused PlanStorage target; expect the former-version test to fail because decoding currently accepts the key.
- [ ] Remove `PlanDefinitionSchema`, `PlanLibraryDefinition.schemaVersion`, `PlanLibraryMetadata.version`, `PlanLibraryStoreError.unsupportedSchema`, schema validation issues, and v2 migration branches. The resulting initializer is `PlanLibraryDefinition(metadata:boardMappings:blocks:plans:)`.
- [ ] Verify encoded data omits both former keys, then rerun `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/PlanStorageTests`; expect pass.
- [ ] Commit: `git add HangTen/Models/PlanStorage.swift HangTenTests/PlanStorageTests.swift && git commit -m "Require one unversioned plan library format"`.
