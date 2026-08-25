# Persisted Bendable Curve Segments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist explicit bendable-curve intent in `board.json` and make direct curve pulling honor only that intent.

**Architecture:** A canonical path `curve` command optionally carries `bendable: true`; all readers validate it but rendering ignores it. The Workbench projects those command flags into an editor-document `bendableCommandIndexes` array, updates the projection with every path mutation, and maps it back to the canonical curve commands during save.

**Tech Stack:** Python package validation and Workbench persistence, TypeScript/React, Swift Codable, Node test runner, pytest, XCTest.

**Spec:** `docs/superpowers/specs/2026-08-24-bendable-curve-segment-schema-design.md`

## Global Constraints

- `bendable` is optional, may only be literal `true`, and is valid only on canonical `curve` commands.
- The flag is authoring metadata; it must not alter geometry, rendering, hit testing, or iOS runtime behavior.
- Persist `bendable` on the canonical command, never as a `board.json` command-index list.
- Unmarked cubics and constrained outlines retain whole-path drag behavior.
- A direct pull changes only a marked, unconstrained cubic and preserves its anchors.
- Existing board packages without the field remain valid and behaviorally unchanged.
- Every code change follows TDD: add a focused test, run it red, make the minimal change, then rerun green.

---

### Task 1: Validate the canonical command property across package readers

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_geometry_schema.py:82-130`
- Modify: `Tools/HangboardPackages/tests/test_board_geometry_schema.py`
- Modify: `HangTen/Models/BoardPackageStore.swift:1218-1428`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`

**Interfaces:**
- Produces: `PathCommand.bendable: bool` in Python and accepted optional `bendable` curve metadata in Swift.
- Consumes: canonical command objects with `command`, controls, destination, and optional `bendable`.

- [ ] **Step 1: Write failing Python schema tests**

```python
def test_curve_command_accepts_true_bendable_metadata() -> None:
    command = PathCommand.from_json(
        {"command": "curve", "control1": [0.2, 0.2], "control2": [0.8, 0.2], "to": [1, 0], "bendable": True},
        "commands[1]",
    )
    assert command.bendable is True

@pytest.mark.parametrize("command", [_move(0, 0), _line(1, 0), _quad((0.5, 1), 1, 0), _close()])
def test_non_curve_commands_reject_bendable_metadata(command: dict) -> None:
    command["bendable"] = True
    with pytest.raises(ValueError, match="unexpected keys"):
        PathCommand.from_json(command, "commands[0]")
```

- [ ] **Step 2: Run the focused schema tests and confirm they fail because `bendable` is unsupported**

Run: `pytest Tools/HangboardPackages/tests/test_board_geometry_schema.py -q`

- [ ] **Step 3: Extend the Python schema minimally**

```python
@dataclass(frozen=True)
class PathCommand:
    # existing fields
    bendable: bool = False

if command == "curve":
    _closed(payload, label, required={"command", "control1", "control2", "to"}, optional={"bendable"})
    if payload.get("bendable", False) is not True:
        raise ValueError(f"{label}.bendable must be true")
    return cls(..., bendable=payload.get("bendable", False))
```

Keep all other command key sets closed, so false, non-booleans, and `bendable` on other command types are rejected.

- [ ] **Step 4: Add a failing Swift decode test**

Mutate a valid fixture's curve command with `"bendable": true`, load it through `BoardPackageStore`, and assert that normal hold geometry loads. Add a companion fixture mutation with `bendable` on a line and assert strict decoding rejects it.

- [ ] **Step 5: Permit only the curve property in the strict Swift decoder**

```swift
case "curve":
    allowedKeys = ["command", "to", "control1", "control2", "bendable"]
```

Decode the property only for validation (`true` when present); do not carry it into `BoardPathCommand` or runtime rendering types.

- [ ] **Step 6: Run the focused tests and commit**

Run: `pytest Tools/HangboardPackages/tests/test_board_geometry_schema.py -q` and the focused `BoardPackageStoreTests` command used by this repository.

Commit: `git add Tools/HangboardPackages/src/hangboard_packages/board_geometry_schema.py Tools/HangboardPackages/tests/test_board_geometry_schema.py HangTen/Models/BoardPackageStore.swift HangTenTests/BoardPackageStoreTests.swift && git commit -m "Validate bendable curve metadata"`

### Task 2: Round-trip canonical bendability through the Workbench API and save path

**Files:**
- Modify: `Tools/HangboardWorkbench/board_package.py:350-535, 1000-1315`
- Modify: `Tools/HangboardWorkbench/tests/test_board_package.py`
- Modify: `Tools/HangboardWorkbench/src/types.ts:48-62`
- Modify: `Tools/HangboardWorkbench/src/workbench-client.ts:49-75`
- Modify: `Tools/HangboardWorkbench/src/workbench-controller.ts:33-57`
- Modify: `Tools/HangboardWorkbench/src/editor-model.ts:20-33`
- Modify: `Tools/HangboardWorkbench/tests/workbench-modules.test.ts`

**Interfaces:**
- Consumes: canonical path commands whose cubic entries may contain `bendable: true`.
- Produces: optional `HoldRegion.bendableCommandIndexes: number[]`, a transient projection aligned with the SVG command sequence in `displayPath`.
- Persistence rule: save maps those indices back to `shape.commands[index].bendable`; indices never appear in `board.json`.

- [ ] **Step 1: Write failing backend round-trip tests**

```python
def test_editor_document_projects_a_bendable_curve_command_index(package_root: Path) -> None:
    # mark a curve in board.json with bendable: true
    document = editor_document(load_board_package(package_root))
    assert document["regions"][0]["bendableCommandIndexes"] == [1]

def test_save_editor_document_persists_only_selected_curve_indexes(package_root: Path) -> None:
    document = editor_document(load_board_package(package_root))
    document["regions"][0]["bendableCommandIndexes"] = [1]
    save_editor_document(package_root.parent, package_root.name, document)
    assert saved_curve_command["bendable"] is True
```

Cover invalid duplicate, out-of-range, and non-curve indexes, plus rejection when a constrained piece requests bendability.

- [ ] **Step 2: Run focused Workbench package tests and confirm the new projection is absent**

Run: `pytest Tools/HangboardWorkbench/tests/test_board_package.py -q`

- [ ] **Step 3: Add the projection to the Python editor boundary**

Expose each canonical curve command that contains `bendable: true` as its matching display-path command index. In `_validate_editor_document`, accept a unique integer list only when every selected parsed command is `C` and the region has no `shapeConstraint`. Carry the validated list in `_EditorPiece`/parsed-region data, and in `_apply_editor_document` remove `bendable` from every regenerated curve before setting it on exactly the selected curves.

When applying unchanged geometry, still update the command metadata so an author can mark or unmark an existing curve without moving it. Include the metadata in dirty comparison so marker-only edits save.

- [ ] **Step 4: Extend TypeScript document validation and cloning**

```ts
export interface HoldRegion {
  // existing fields
  bendableCommandIndexes?: number[];
}
```

Require a unique non-negative integer array in both browser-client and controller boundary guards. Deep-copy it in `cloneEditorDocument` so undo/redo snapshots do not alias the array.

- [ ] **Step 5: Run focused backend and module tests and commit**

Run: `pytest Tools/HangboardWorkbench/tests/test_board_package.py -q` and `npm run test:modules` from `Tools/HangboardWorkbench`.

Commit: `git add Tools/HangboardWorkbench/board_package.py Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/src/types.ts Tools/HangboardWorkbench/src/workbench-client.ts Tools/HangboardWorkbench/src/workbench-controller.ts Tools/HangboardWorkbench/src/editor-model.ts Tools/HangboardWorkbench/tests/workbench-modules.test.ts && git commit -m "Round-trip bendable curve metadata in Workbench"`

### Task 3: Make the editor carry and honor the persisted marker

**Files:**
- Modify: `Tools/HangboardWorkbench/src/path-editor.ts:1-70, 480-650`
- Modify: `Tools/HangboardWorkbench/src/useHoldEditor.ts:1-150, 520-620, 1000-1190`
- Modify: `Tools/HangboardWorkbench/tests/path-editor.test.ts`
- Modify: `Tools/HangboardWorkbench/tests/react-editor.test.tsx`

**Interfaces:**
- Consumes: `HoldRegion.bendableCommandIndexes` from Task 2.
- Produces: path commands carrying `bendable?: boolean`; `serializePath` remains geometry-only and does not serialize metadata into SVG text.
- Uses: `bendSegmentToPoint(commands, afterIndex, point)` only after verifying `commands[afterIndex + 1]?.bendable === true` and no shape constraint.

- [ ] **Step 1: Write failing pure path-editor tests**

```ts
test("makeSegmentBendable marks its replacement cubic", () => {
  const commands = parsePath("M 0 0 L 10 0 L 10 10 Z");
  makeSegmentBendable(commands, 0);
  assert.equal(commands[1]?.bendable, true);
});

test("splitting a bendable cubic preserves bendability on both descendants", () => {
  const commands = parsePath("M 0 0 C 3 0 7 0 10 0 L 10 10 Z");
  commands[1]!.bendable = true;
  addVertex(commands, 0, 5, 0);
  assert.equal(commands[1]?.bendable, true);
  assert.equal(commands[2]?.bendable, true);
});
```

Also assert straightening or deleting/replacing a marked curve removes its flag.

- [ ] **Step 2: Run the focused path-editor tests and confirm the marker does not yet survive operations**

Run: `npm run test:modules -- --test-name-pattern="bendable"`

- [ ] **Step 3: Carry metadata through path mutations**

Add optional `bendable` to `PathCommand`. Add a small helper in `useHoldEditor` that hydrates parsed SVG commands from `bendableCommandIndexes`, and a paired helper that writes the resulting marked command indexes back to the edited region whenever a path is serialized. Remove the current session-only `Set` and `documentIdentity` plumbing.

Set the flag in `makeSegmentBendable`; duplicate it when `addVertex` subdivides a flagged cubic; omit it from line/quadratic replacements. Direct path dragging, rotation, and control/anchor moves retain the same command objects and therefore retain the marker.

- [ ] **Step 4: Write failing React interaction tests**

Add tests that:

1. mark a line with **Make bendable**, save/reload through the editor fixture, then pull it and verify unchanged endpoints;
2. show an unmarked imported cubic still translates as a whole path;
3. show a constrained cubic still translates as a whole path;
4. split a marked curve, then pull either descendant; and
5. undo/redo a marker edit without leaking or losing its marker.

- [ ] **Step 5: Implement the minimum direct-drag condition**

```ts
const bendsSegment = bendableSegmentAfterIndex !== null
  && !selectedHold.shapeConstraint
  && commands[bendableSegmentAfterIndex + 1]?.type === "C"
  && commands[bendableSegmentAfterIndex + 1]?.bendable === true;
```

Keep the existing midpoint-through-pointer calculation in `bendSegmentToPoint`; it changes controls only, never endpoints.

- [ ] **Step 6: Run Workbench verification and commit**

Run from `Tools/HangboardWorkbench`: `npm test && npm run check:bundle`.

Commit: `git add Tools/HangboardWorkbench/src/path-editor.ts Tools/HangboardWorkbench/src/useHoldEditor.ts Tools/HangboardWorkbench/tests/path-editor.test.ts Tools/HangboardWorkbench/tests/react-editor.test.tsx && git commit -m "Persist bendable curve editor segments"`

## Plan self-review

- Spec coverage: Task 1 proves Python and iOS schema compatibility; Task 2 proves Workbench package load/save/reload; Task 3 implements the exact editor behavior and structural semantics and runs the complete Workbench verification.
- Placeholder scan: No deferred requirements or unspecified validation cases remain; every task lists files, interfaces, focused tests, and verification commands.
- Type consistency: `bendable` is canonical curve metadata; `bendableCommandIndexes` is only the Workbench editor-document projection; `PathCommand.bendable` is the in-memory editing representation.
