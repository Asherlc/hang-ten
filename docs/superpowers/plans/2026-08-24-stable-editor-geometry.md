# Stable Editor Geometry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Workbench’s freeform hold editor stable, session-local anchor, control, and segment identities without changing saved board geometry.

**Architecture:** Add a pure `EditablePath` model that owns typed path commands and opaque local IDs, then make the hook and SVG canvas consume that model rather than command indexes. `displayPath` remains the only persisted editor representation and is produced through the existing canonical serializer.

**Tech Stack:** TypeScript 7, React 19, Node test runner, existing `PathEditor` parser/serializer and Workbench controller.

**Spec:** `docs/superpowers/specs/2026-08-24-stable-editor-geometry-design.md`

## Global Constraints

- Keep `board.json`, its schema version, the Python package validator, and iOS loading unchanged.
- IDs must stay editor-local and must not occur in `displayPath` or any saved document.
- Use existing canonical `PathEditor.parsePath` and `PathEditor.serializePath`; do not add SVG syntax.
- Preserve existing guide snapping, constraint editing, mirroring, history, rollback, and accessibility behavior.
- Follow TDD: every production behavior begins with a focused failing test.

---

### Task 1: Editor-local typed path model

**Files:**
- Create: `Tools/HangboardWorkbench/src/editable-path.ts`
- Modify: `Tools/HangboardWorkbench/src/types.ts`
- Modify: `Tools/HangboardWorkbench/tests/path-editor.test.ts`

**Interfaces:**
- Consumes: `PathEditor.parsePath(pathString): PathCommand[]` and `PathEditor.serializePath(commands): string`.
- Produces: `EditablePath`, `EditableSegment`, `EditableAnchor`, `EditableControl`, `createEditablePath`, `serializeEditablePath`, `editablePathAnchor`, `editablePathControl`, and mutation helpers used by Task 2.

- [ ] **Step 1: Write failing unit tests for a deterministic, non-persisted projection**

```ts
test("editable paths assign deterministic local IDs and serialize only canonical geometry", () => {
  const editable = createEditablePath("hold-a-piece-0", "M 0 0 Q 5 10 10 0 L 10 10 Z", pathEditor);

  assert.deepEqual(editable.segments.map((segment) => segment.id), [
    "hold-a-piece-0:segment:0", "hold-a-piece-0:segment:1", "hold-a-piece-0:segment:2",
  ]);
  assert.equal(editable.segments[1]?.anchor.id, "hold-a-piece-0:anchor:1");
  assert.equal(editable.segments[1]?.controls[0]?.id, "hold-a-piece-0:control:1:0");
  assert.equal(serializeEditablePath(editable, pathEditor), "M 0 0 Q 5 10 10 0 L 10 10 Z");
  assert.equal(JSON.stringify(editable).includes("displayPath"), false);
});
```

- [ ] **Step 2: Run the new test and verify it fails because the projection API is unavailable**

Run: `rtk npm run test:modules --prefix Tools/HangboardWorkbench`

Expected: FAIL with a missing-module or missing-export error for `editable-path.ts`.

- [ ] **Step 3: Implement the minimal typed projection and canonical conversion**

```ts
export interface EditablePath {
  readonly regionKey: string;
  readonly segments: EditableSegment[];
}

export function createEditablePath(regionKey: string, pathString: string, pathEditor: PathEditor): EditablePath {
  return {
    regionKey,
    segments: pathEditor.parsePath(pathString).map((command, index) => toEditableSegment(regionKey, command, index)),
  };
}

export function serializeEditablePath(path: EditablePath, pathEditor: PathEditor): string {
  return pathEditor.serializePath(path.segments.map(toPathCommand));
}
```

Assign IDs as `${regionKey}:segment:${index}`, `${regionKey}:anchor:${index}`, and `${regionKey}:control:${index}:${controlIndex}`. Copy path coordinates; never write local IDs into `PathCommand` values.

- [ ] **Step 4: Add focused failing tests for identity preservation and insertion allocation**

```ts
test("moving a control preserves every local ID while inserting allocates only the new IDs", () => {
  const editable = createEditablePath("hold-a-piece-0", "M 0 0 L 10 0 L 10 10 Z", pathEditor);
  const retained = editable.segments[1]!.anchor.id;

  moveEditableAnchor(editable, retained, 2, 3);
  assert.equal(editable.segments[1]!.anchor.id, retained);

  insertEditableVertex(editable, 0, { x: 5, y: 0 });
  assert.equal(editable.segments.at(-1)!.anchor.id, "hold-a-piece-0:anchor:2");
  assert.equal(editable.segments.find((segment) => segment.anchor.id === retained)?.anchor.id, retained);
});
```

- [ ] **Step 5: Implement local-ID-preserving mutation helpers and rerun module tests**

Wrap existing command operations by converting the editable segments to commands, invoking the matching `PathEditor` method, and reconciling the result: retain identities for semantically unchanged command positions; allocate a fresh monotonic local ID for a newly inserted segment/anchor/control. Run:

```sh
rtk npm run test:modules --prefix Tools/HangboardWorkbench
rtk npm run typecheck --prefix Tools/HangboardWorkbench
```

Expected: PASS.

- [ ] **Step 6: Commit the tested model**

```sh
rtk git add Tools/HangboardWorkbench/src/editable-path.ts Tools/HangboardWorkbench/src/types.ts Tools/HangboardWorkbench/tests/path-editor.test.ts
rtk git commit -m "feat: add stable editable path model"
```

### Task 2: Use stable IDs in the hook and SVG canvas

**Files:**
- Modify: `Tools/HangboardWorkbench/src/useHoldEditor.ts`
- Modify: `Tools/HangboardWorkbench/src/components/HoldCanvas.tsx`
- Modify: `Tools/HangboardWorkbench/tests/react-editor.test.tsx`

**Interfaces:**
- Consumes: Task 1’s `EditablePath` and lookup/mutation helpers, plus the existing `PathEditor` for geometry operations.
- Produces: `HoldEditorActions` selection and drag APIs that address anchors/controls by local ID; stable SVG `key` and `data-*` attributes.

- [ ] **Step 1: Write failing React tests for stable target identity through edits and history**

```tsx
test("a freeform anchor keeps its local target ID while it is dragged", async () => {
  const app = await renderEditor({ path: "M 10 10 L 30 10 L 30 30 Z" });
  const anchor = app.document.querySelector<SVGCircleElement>(".path-editor-vertex")!;
  const id = anchor.dataset.anchorId;

  await drag(app, `.path-editor-vertex[data-anchor-id="${id}"]`, [{ x: 10, y: 10 }, { x: 14, y: 12 }]);

  assert.equal(app.document.querySelector(`.path-editor-vertex[data-anchor-id="${id}"]`)?.getAttribute("cx"), "14");
});
```

Add a second test that inserts a vertex, verifies an unrelated anchor keeps its `data-anchor-id`, then undoes/redoes and verifies the persisted `displayPath` values remain the existing canonical values.

- [ ] **Step 2: Run the tests and verify they fail due to index-only targets**

Run: `rtk npm run test:react --prefix Tools/HangboardWorkbench`

Expected: FAIL because `data-anchor-id` is absent and editor selection is still index-based.

- [ ] **Step 3: Migrate freeform editor state from indexes to local IDs**

Keep an `EditablePath` ref keyed by `(selectedHold.key, selectedHold.displayPath)`. Rebuild it when either part changes outside the active gesture. Update `VertexSelection`, `DragState`, menu state, and `HoldEditorActions` to pass `anchorID`, `controlID`, and `segmentID`; resolve command indexes only inside the editable-path module. Before committing an edit, serialize the ref through `serializeEditablePath` and retain the existing `validateEditorDocument` rollback behavior.

- [ ] **Step 4: Render stable SVG targets and retain accessibility text**

```tsx
<circle
  key={anchor.id}
  className={`path-editor-vertex${editor.selectedAnchorID === anchor.id ? " selected" : ""}`}
  data-anchor-id={anchor.id}
  aria-label={anchor.isStart ? "Start vertex" : `Vertex ${anchor.ordinal + 1}`}
  onFocus={() => editor.selectAnchor(anchor.id)}
/>
```

Give controls `key={control.id}` and `data-control-id={control.id}`. Do not change the visible labels, keyboard behavior, constrained-shape overlay, or existing segment menu semantics.

- [ ] **Step 5: Run integration checks and inspect the changed behavior**

```sh
rtk npm run test:react --prefix Tools/HangboardWorkbench
rtk npm run test:modules --prefix Tools/HangboardWorkbench
rtk npm run typecheck --prefix Tools/HangboardWorkbench
rtk npm run check:bundle --prefix Tools/HangboardWorkbench
```

Expected: all commands pass; React tests prove local identities survive edits and document-history rebuilds without persistence changes.

- [ ] **Step 6: Commit the editor integration**

```sh
rtk git add Tools/HangboardWorkbench/src/useHoldEditor.ts Tools/HangboardWorkbench/src/components/HoldCanvas.tsx Tools/HangboardWorkbench/tests/react-editor.test.tsx
rtk git commit -m "feat: use stable geometry identities in hold editor"
```

### Task 3: Verify package compatibility and document the local-ID boundary

**Files:**
- Modify: `Tools/HangboardWorkbench/README.md`
- Modify: `Tools/HangboardWorkbench/tests/react-editor.test.tsx`

**Interfaces:**
- Consumes: Task 2’s stable SVG attributes and unchanged Workbench save behavior.
- Produces: documentation that distinguishes local editor identities from canonical package geometry, and an integration assertion that serialized data cannot leak IDs.

- [ ] **Step 1: Write a failing save-boundary test**

```tsx
test("saving a stable editable path sends no local geometry IDs", async () => {
  const app = await renderEditor({ path: "M 10 10 L 30 10 L 30 30 Z" });
  await drag(app, ".path-editor-vertex", [{ x: 10, y: 10 }, { x: 12, y: 12 }]);
  await app.click("#save-board-button");

  assert.equal(JSON.stringify(client.saveCalls[0]?.document).includes(":anchor:"), false);
  assert.equal(JSON.stringify(client.saveCalls[0]?.document).includes(":control:"), false);
  assert.equal(JSON.stringify(client.saveCalls[0]?.document).includes(":segment:"), false);
});
```

- [ ] **Step 2: Run the test and verify it fails before the save-boundary assertion is implemented**

Run: `rtk npm run test:react --prefix Tools/HangboardWorkbench`

Expected: FAIL because the test fixture or save-call inspection helper does not yet expose the asserted save document.

- [ ] **Step 3: Complete the test using the existing test client and update documentation**

Add the smallest fixture accessor needed to inspect the actual save request. In `README.md`, add a short “Editor-local geometry identities” note: anchors, controls, and segments use stable IDs only in memory; `displayPath` and `board.json` remain the canonical saved representation.

- [ ] **Step 4: Run full Workbench validation**

```sh
rtk npm test --prefix Tools/HangboardWorkbench
rtk npm run check:bundle --prefix Tools/HangboardWorkbench
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

Expected: all Workbench tests, bundle check, and package validation pass; package contents remain unchanged.

- [ ] **Step 5: Commit compatibility verification and documentation**

```sh
rtk git add Tools/HangboardWorkbench/README.md Tools/HangboardWorkbench/tests/react-editor.test.tsx
rtk git commit -m "docs: clarify editor-local geometry identities"
```
