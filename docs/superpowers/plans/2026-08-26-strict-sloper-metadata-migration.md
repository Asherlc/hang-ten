# Strict Sloper Metadata Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store source-backed flat-versus-round sloper metadata where available, preserve manufacturer-published flat-surface angles when available, and expose both in the iOS Hold inspector.

**Architecture:** Add one canonical `sloper` metadata object to the per-hold JSON schema, with matching Python and Swift value types. Extend the existing source-audit ledger with a `sloper` field so the strict package migration can be mechanically cross-checked against all 96 current slopers. The editor reads and writes the same model, offering a subtype control and a conditional angle control.

**Tech Stack:** Swift/SwiftUI/XCTest; Python 3/pytest; canonical `Hangboards/*/board.json` packages; shell package validator.

**Spec:** `docs/superpowers/specs/2026-08-26-sloper-metadata-strict-migration-design.md`

## Global Constraints

- `sloper` is optional when `kind` is `sloper`, and prohibited otherwise.
- When present, `sloper.type` is required and exactly `flat` or `round`.
- A flat sloper may include finite `angleDegrees` in the inclusive range 0 through 90, measured from the board face; a round sloper must not contain it.
- Each migrated hold must have a primary manufacturer URL. A subtype is stored only when the manufacturer publishes it; an angle is stored only when the manufacturer publishes it. Do not infer either fact from names, images, geometry, or `shapeConstraint`.
- A missing primary-source subtype is recorded as unavailable and leaves `sloper` absent; omit unsupported flat angles rather than fabricating or approximating them.
- Add and execute red-green tests before production changes, using real decoder, writer, validator, and editor-session behavior.
- Keep plan wording and training content unchanged. Do not alter hold geometry.

---

## File structure

- `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` adds the Python schema representation and conditional per-hold validation.
- `Tools/HangboardPackages/src/hangboard_packages/metadata_audit.py` adds source-ledger parsing and package-value comparison for `sloper`.
- `Tools/HangboardPackages/tests/test_board_catalog.py` and `Tools/HangboardPackages/tests/test_metadata_audit.py` cover parser and ledger contracts.
- `HangTen/Models/TrainingModels.swift` defines the shared Swift sloper metadata model carried by `BoardHold`.
- `HangTen/Models/BoardPackageStore.swift` decodes and enforces the canonical JSON contract.
- `HangTen/Models/BoardPackageWriter.swift` preserves the model in editable JSON and rejects invalid editor documents.
- `HangTen/Views/BoardEditor/BoardEditorSession.swift` provides validated subtype-changing state transitions.
- `HangTen/Views/BoardEditor/HoldInspectorView.swift` renders the subtype control and the flat-only angle editor.
- `HangTenTests/BoardPackageStoreTests.swift`, `HangTenTests/BoardPackageWriterTests.swift`, and `HangTenTests/BoardEditorSessionTests.swift` exercise the Swift contract.
- `docs/source-audits/2026-08-26-sloper-metadata-audit.md` records the hold-ID-to-primary-source reasoning.
- `docs/source-audits/2026-08-25-hangboard-metadata-ledger.json` gains verified `sloper` records for each migrated sloper.
- The 28 affected `Hangboards/*/board.json` files gain only source-backed `sloper` metadata on their 96 sloper holds.

### Task 1: Python schema and audit-ledger contract

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/metadata_audit.py`
- Modify: `Tools/HangboardPackages/tests/test_board_catalog.py`
- Modify: `Tools/HangboardPackages/tests/test_metadata_audit.py`

**Interfaces:**
- Produces a Python `SloperMetadata` value carried by `BoardHold`.
- Produces `_load_hold` validation: slopers may omit `sloper`; when present it requires a `sloper.type`; flat slopers may include `angleDegrees`; non-slopers reject `sloper`.
- Produces metadata-audit field `sloper`, whose verified value is exactly the canonical object and whose comparison reads `BoardHold.sloper`.

- [ ] **Step 1: Write failing schema tests**

Add focused tests that load otherwise-valid board payloads containing these literal cases: a flat sloper with `{"type": "flat", "angleDegrees": 20}`, a flat sloper with `{"type": "flat"}`, a round sloper with `{"type": "round"}`, a sloper omitting `sloper`, a non-sloper containing `sloper`, a round sloper containing `angleDegrees`, and out-of-range/non-finite supplied angles. Assert accepted values are exposed as optional structured metadata and rejected values raise `ValueError` containing the relevant field path.

- [ ] **Step 2: Verify the schema tests fail for the missing contract**

Run: `pytest Tools/HangboardPackages/tests/test_board_catalog.py -k sloper -v`

Expected: the new positive test fails because parsed `BoardHold` has no sloper metadata, and at least one invalid payload is currently accepted.

- [ ] **Step 3: Write failing source-ledger tests**

Add tests for a verified `sloper` ledger record that matches a flat hold, a record whose angle differs from the hold, and a record that uses a non-manufacturer or non-HTTPS source. Use literal JSON objects rather than building expected values with production helpers.

- [ ] **Step 4: Verify the ledger tests fail for the missing field**

Run: `pytest Tools/HangboardPackages/tests/test_metadata_audit.py -k sloper -v`

Expected: the new valid record is rejected as an unsupported field or does not compare to package data.

- [ ] **Step 5: Implement the minimum Python model and validation**

Add a frozen `SloperMetadata(type: str, angle_degrees: float | None)` with a parser that accepts only `flat` and `round`, permits an absent flat angle, rejects every round angle, and bounds any supplied flat angle to 0...90. Add optional `sloper` metadata to the Python `BoardHold`, make `_load_hold` reject metadata only on non-slopers, and extend the audit ledger field set, verified-value parsing, actual-value extraction, and value comparison for canonical `{"type": ..., "angleDegrees": ...}` values.

- [ ] **Step 6: Verify the focused Python tests pass**

Run: `pytest Tools/HangboardPackages/tests/test_board_catalog.py -k sloper -v && pytest Tools/HangboardPackages/tests/test_metadata_audit.py -k sloper -v`

Expected: every selected test passes.

- [ ] **Step 7: Commit and push the task**

Run: `git add Tools/HangboardPackages/src/hangboard_packages/board_catalog.py Tools/HangboardPackages/src/hangboard_packages/metadata_audit.py Tools/HangboardPackages/tests/test_board_catalog.py Tools/HangboardPackages/tests/test_metadata_audit.py && git commit -m "Validate strict sloper metadata" && git push`

### Task 2: Primary-source evidence audit and canonical package migration

**Files:**
- Create: `docs/source-audits/2026-08-26-sloper-metadata-audit.md`
- Modify: `docs/source-audits/2026-08-25-hangboard-metadata-ledger.json`
- Modify: the 28 `Hangboards/*/board.json` files containing the 96 `kind: "sloper"` holds.
- Test: `Tools/HangboardPackages/tests/test_complete_catalog_source_audit.py`

**Interfaces:**
- Consumes Task 1’s `sloper` parser and ledger field.
- Produces canonical board data populated only with manufacturer-verified metadata and a machine-checked manufacturer evidence record for every sloper.

- [ ] **Step 1: Produce the exact migration inventory**

Run `rg -n -C 2 '"kind": "sloper"' Hangboards/*/board.json` and record each package ID and hold ID in the audit document. Confirm the inventory has 96 hold occurrences in 28 package files before assigning facts.

- [ ] **Step 2: Gather primary manufacturer evidence without inference**

For each inventory row, use the official manufacturer product page, specification, or official labelled hold diagram. Record the direct source URL and visible source fact. Store `flat` or `round` only when the source establishes that subtype; otherwise record `sloper` as unavailable with a precise reason. For a flat entry, record an angle only when the manufacturer states it using the documented board-face convention.

- [ ] **Step 3: Add the source-audit document and ledger entries**

Write one audit table row for every sloper, grouping only hold IDs supported by the same direct source fact. Include package ID, hold IDs, canonical `sloper` value or unavailable outcome, source label, source URL, and a concise source-fact quotation or precise paraphrase. Add matching `field: "sloper"` records to the existing JSON ledger: use `outcome: "verified"` with a literal canonical object for sourced subtypes, or `outcome: "unavailable"` with a precise reason for generic-only evidence. Use the real review date and `kind: "manufacturer"` source objects.

- [ ] **Step 4: Update only the canonical sloper data**

Insert the literal `sloper` object after `kind` only for a hold with a manufacturer-verified subtype. A flat hold receives `{"type":"flat"}` plus `angleDegrees` only when the manufacturer publishes the value; a round hold receives `{"type":"round"}`. For generic-only evidence, leave `sloper` absent. Do not change the hold name, kind, geometry, presentations, depth, capacity, features, or training-plan files.

- [ ] **Step 5: Validate all package data and source records**

Run: `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory && scripts/hangboard-packages.sh audit-metadata --root Hangboards --ledger docs/source-audits/2026-08-25-hangboard-metadata-ledger.json --final-inventory`

Expected: both commands complete with exit code 0 and the audit report has no unaccounted field records.

- [ ] **Step 6: Commit and push the migration**

Run: `git add Hangboards docs/source-audits/2026-08-26-sloper-metadata-audit.md docs/source-audits/2026-08-25-hangboard-metadata-ledger.json && git commit -m "Add audited sloper metadata" && git push`

### Task 3: Swift decoding, writer round trips, and editor controls

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Models/BoardPackageStore.swift`
- Modify: `HangTen/Models/BoardPackageWriter.swift`
- Modify: `HangTen/Views/BoardEditor/BoardEditorSession.swift`
- Modify: `HangTen/Views/BoardEditor/HoldInspectorView.swift`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `HangTenTests/BoardPackageWriterTests.swift`
- Modify: `HangTenTests/BoardEditorSessionTests.swift`

**Interfaces:**
- Consumes Task 2’s optional canonical `sloper` object in sourced bundled packages.
- Produces `SloperMetadata` and `SloperType` in Swift, optional `BoardHold.sloper`, and an optional `BoardEditableHold.sloper` that survives JSON decoding and canonical writer output.
- Produces editor-session methods that select an optional subtype and update only flat-surface angles.

- [ ] **Step 1: Write failing Store and writer tests**

Add XCTest fixtures that decode a flat sloper with `angleDegrees == 20`, a flat sloper with a nil angle, a round sloper with a nil angle, and a sloper with no metadata; reject non-sloper metadata, round-with-angle, and supplied values outside 0...90. Extend the existing editable-document semantic equality assertion and round-trip test to compare optional sloper metadata.

- [ ] **Step 2: Verify Store and writer tests fail**

Run the exact Xcode test selector(s) containing the new Store and writer tests using the project’s existing simulator scheme. Expected: compilation or assertions fail because `BoardHold` and `BoardEditableHold` do not yet expose sloper metadata.

- [ ] **Step 3: Implement the shared model and strict persistence**

Define `SloperType: String, Codable, Hashable` with `flat` and `round`, plus `SloperMetadata: Codable, Hashable` with conditional validation. Add optional metadata to `BoardHold`, the package document, the editable document, `BoardPackageStore`, and `BoardPackageWriter`. Keep decoding fail-closed by adding `sloper` to exact coding-key allowlists, accepting its absence only on slopers, and rejecting every invalid kind/type/angle combination named in Step 1 while preserving an absent flat angle.

- [ ] **Step 4: Write failing editor-session tests**

Create a selected sloper fixture in `BoardEditorSessionTests`. Assert an unspecified sloper has nil metadata, changing it to flat leaves an absent angle absent, updating a supplied angle changes only flat metadata, changing to round clears the angle, and changing it back to unspecified clears metadata. An angle update while round or unspecified is rejected or ignored without changing the saved document.

- [ ] **Step 5: Verify editor tests fail**

Run the exact Xcode test selector(s) containing the new editor-session tests. Expected: the session has no subtype/angle transition API and the document cannot retain the state.

- [ ] **Step 6: Implement the editor API and Hold inspector**

Add session methods that push one undo checkpoint before changing the selected hold’s optional `sloper` value and that only accept an in-range finite angle while the type is flat. In `HoldInspectorView`, render a `Sloper` card only when the selected hold kind is `.sloper`, use a `Picker`/segmented control for `Unspecified`, `Flat`, and `Round`, and display an optional degrees-labelled numeric control only when the model type is `.flat`. Wire each control through the session methods, preserving existing error presentation and undo behavior.

- [ ] **Step 7: Verify all focused Swift tests pass**

Run the focused Store, writer, and editor-session XCTest selectors from Steps 2 and 5. Expected: all selected tests pass with no new warnings.

- [ ] **Step 8: Commit and push the task**

Run: `git add HangTen/Models/TrainingModels.swift HangTen/Models/BoardPackageStore.swift HangTen/Models/BoardPackageWriter.swift HangTen/Views/BoardEditor/BoardEditorSession.swift HangTen/Views/BoardEditor/HoldInspectorView.swift HangTenTests/BoardPackageStoreTests.swift HangTenTests/BoardPackageWriterTests.swift HangTenTests/BoardEditorSessionTests.swift && git commit -m "Edit strict sloper metadata" && git push`

### Task 4: Whole-migration verification

**Files:**
- Modify only if verification finds a defect in a file owned by Tasks 1–3.

**Interfaces:**
- Consumes strict validators, all migrated packages, source audit, and editor persistence.
- Produces verification evidence for the completed branch without widening schema scope.

- [ ] **Step 1: Run the complete Python validator suite**

Run: `pytest Tools/HangboardPackages/tests -v`

Expected: all package-validator tests pass.

- [ ] **Step 2: Run final inventory and source-ledger checks**

Run: `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory && scripts/hangboard-packages.sh audit-metadata --root Hangboards --ledger docs/source-audits/2026-08-25-hangboard-metadata-ledger.json --final-inventory`

Expected: both commands exit 0 and account for every source-audited `sloper` field.

- [ ] **Step 3: Run the complete relevant iOS test target**

Run the project’s existing `HangTenTests` Xcode test target on its configured iOS Simulator destination.

Expected: the target exits 0 with no failing tests.

- [ ] **Step 4: Inspect the complete change for accidental geometry or plan-content edits**

Run: `git diff --check origin/main...HEAD && scripts/verify-sloper-metadata-migration.py origin/main HEAD && git diff --name-only origin/main...HEAD`

Expected: no whitespace errors; the verifier confirms changed board files contain only new `sloper` metadata values; no training-plan source is listed.

- [ ] **Step 5: Return any verification failure to its owning task**

Do not create an empty verification commit. If a command in Steps 1–4 fails,
record the exact failing command and output in the task report, identify the
owning task (Task 1, 2, or 3), and return it to the controller for a scoped
fix and re-review.

## Plan self-review

- Spec coverage: Tasks 1 and 3 enforce identical conditional schema rules; Task 2 supplies primary-source evidence and all 96 data values; Task 3 covers editor behavior; Task 4 runs every required end-to-end check.
- Placeholder scan: every task names exact files, literal schema values, validation cases, and commands. The source-audit task intentionally stops on missing evidence, as the approved spec requires.
- Type consistency: Python uses `SloperMetadata(type, angle_degrees)` and Swift uses `SloperMetadata(type, angleDegrees)` only at their language boundaries; JSON is consistently `sloper.type` and `sloper.angleDegrees`.
