# Workbench Editor History and Shortcuts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reversible editor document history and standard desktop keyboard shortcuts for undo, redo, save, and drag cancellation.

**Architecture:** `useWorkbench` owns two bounded stacks of immutable `EditorDocument` snapshots and exposes `undoDocument`/`redoDocument` through `WorkbenchActions`. `useHoldEditor` consumes those actions for revision and Escape keyboard commands; `WorkbenchApp` handles save after cancelling any active drag. Completed edits add precisely one history entry, including a completed drag; preview replacements never enter history.

**Tech Stack:** React 19, TypeScript strict mode, Node test runner with jsdom, tsx, esbuild.

**Spec:** `docs/superpowers/specs/2026-08-20-workbench-editor-history-shortcuts-design.md`

## Global Constraints

- Support `Command/Ctrl+Z` for undo, `Command/Ctrl+Shift+Z` and `Ctrl+Y` for redo, `Command/Ctrl+S` for save, and `Escape` for active-drag cancellation.
- Do not intercept any shortcut while the target is an input, select, textarea, or content-editable element.
- History is local, bounded, document-specific, and never serialized to `board.json` or sent to the server.
- Pointer-move previews must not create history entries; each finished drag is one reversible edit.
- Loading or saving a board resets history; a failed save preserves unsaved edits and local history.
- Preserve existing document validation, dirty-state, selection, and busy-operation behavior.

---

## File Structure

- `Tools/HangboardWorkbench/src/types.ts`: exposes document-history actions on `WorkbenchActions`.
- `Tools/HangboardWorkbench/src/useWorkbench.ts`: records/replays bounded document snapshots and resets history at board lifecycle boundaries.
- `Tools/HangboardWorkbench/src/useHoldEditor.ts`: routes undo/redo and Escape keys, and commits drag history only after successful completion.
- `Tools/HangboardWorkbench/src/WorkbenchApp.tsx`: routes the save shortcut through drag cancellation and `saveBoard`.
- `Tools/HangboardWorkbench/tests/react-editor.test.tsx`: asserts user-visible history and shortcut behavior through the rendered app.

### Task 1: Document history and editor keyboard shortcuts

**Files:**
- Modify: `Tools/HangboardWorkbench/src/types.ts:257-274`
- Modify: `Tools/HangboardWorkbench/src/useWorkbench.ts:25-40, 214-272, 505-640`
- Modify: `Tools/HangboardWorkbench/src/useHoldEditor.ts:356-365, 659-692`
- Modify: `Tools/HangboardWorkbench/src/WorkbenchApp.tsx:17-46`
- Test: `Tools/HangboardWorkbench/tests/react-editor.test.tsx:297-390, 760-845`

**Interfaces:**
- Consumes: `cloneEditorDocument(document: EditorDocument): EditorDocument`, `WorkbenchActions.editDocument`, `WorkbenchActions.replaceDocument`, and `HoldEditorActions.cancelActiveEdit(): boolean`.
- Produces: `WorkbenchActions.undoDocument(): boolean` and `WorkbenchActions.redoDocument(): boolean`; each returns `true` only when a document revision was applied.

- [ ] **Step 1: Write the failing rendered-editor tests**

Add these tests adjacent to the existing keyboard and pointer tests. The assertions deliberately exercise `WorkbenchApp` and the global document listeners, not implementation details:

```ts
test("command/control undo and redo reverse document edits and preserve native input behavior", async () => {
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.keyDown("body", "ArrowRight");
    assert.equal(paths(app)[0], "M 11 10 L 21 10 L 21 20 Z");
    assert.equal(await app.keyDown("body", "z", { metaKey: true }), true);
    assert.equal(paths(app)[0], FIRST_PATH);
    assert.equal(await app.keyDown("body", "z", { ctrlKey: true, shiftKey: true }), true);
    assert.equal(paths(app)[0], "M 11 10 L 21 10 L 21 20 Z");
    assert.equal(await app.keyDown("body", "y", { ctrlKey: true }), false);

    const input = app.document.createElement("input");
    input.id = "native-history-input";
    app.document.body.append(input);
    assert.equal(await app.keyDown("#native-history-input", "z", { metaKey: true }), false);
    assert.equal(paths(app)[0], "M 11 10 L 21 10 L 21 20 Z");
  });
});

test("a new edit clears redo and a completed drag is a single undo step", async () => {
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    await drag(app, '[data-hold-key="a-piece-0"]', [{ x: 15, y: 15 }, { x: 20, y: 15 }, { x: 25, y: 15 }]);
    assert.equal(await app.keyDown("body", "z", { ctrlKey: true }), true);
    assert.equal(paths(app)[0], FIRST_PATH);
    await app.keyDown("body", "ArrowRight");
    assert.equal(await app.keyDown("body", "y", { ctrlKey: true }), false);
  });
});

test("escape cancels a drag and command/control save saves only outside editable targets", async () => {
  const board = boardFixture();
  let saves = 0;
  const client = {
    ...clientFixture([board]),
    async saveBoard(boardId: string, document: EditorDocument): Promise<Board> {
      saves += 1;
      return { ...board, boardId, document };
    },
  } satisfies WorkbenchClient;
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    await app.pointer('[data-hold-key="a-piece-0"]', "pointerdown", { pointerId: 7, clientX: 15, clientY: 15 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 7, clientX: 25, clientY: 15 });
    assert.notEqual(paths(app)[0], FIRST_PATH);
    assert.equal(await app.keyDown("body", "Escape"), true);
    assert.equal(paths(app)[0], FIRST_PATH);
    assert.equal(await app.keyDown("body", "s", { metaKey: true }), true);
    await app.flush();
    assert.equal(saves, 1);

    const input = app.document.createElement("input");
    input.id = "native-save-input";
    app.document.body.append(input);
    assert.equal(await app.keyDown("#native-save-input", "s", { ctrlKey: true }), false);
    assert.equal(saves, 1);
  }, dependenciesFixture(board, { client }));
});
```

Use a client fixture with a `saveBoard` spy/count for the save assertion, and assert no save call when the target is an appended input.

- [ ] **Step 2: Run the focused React test file to verify the new behavior fails**

Run: `cd Tools/HangboardWorkbench && npm run test:react -- --test-name-pattern="undo|redo|escape|save"`

Expected: FAIL because `WorkbenchActions` has no undo/redo implementation and no global handlers respond to the new key combinations.

- [ ] **Step 3: Add bounded immutable history to `useWorkbench`**

Define a small private history model near `INITIAL_STATE`, using `useRef` so preview rendering does not create a revision:

```ts
const MAX_DOCUMENT_HISTORY = 100;
interface DocumentHistory {
  undo: EditorDocument[];
  redo: EditorDocument[];
}

function resetHistory(history: DocumentHistory): void {
  history.undo = [];
  history.redo = [];
}

function recordHistory(history: DocumentHistory, document: EditorDocument): void {
  history.undo.push(cloneEditorDocument(document));
  if (history.undo.length > MAX_DOCUMENT_HISTORY) history.undo.shift();
  history.redo = [];
}
```

Create `historyRef` once in `useWorkbench`. Extend `DocumentUpdateOptions` with `historySnapshot?: EditorDocument`. When it is present, `replaceDocument` records that immutable snapshot before making the existing state transition; when omitted, the update is a preview or restoration and does not affect history. Make successful `editDocument` call `replaceDocument(nextDocument, { ...options, historySnapshot: current.document })` only after validation succeeds.

Implement `undoDocument` and `redoDocument` by cloning the current document to the opposite stack, popping a snapshot, and updating state with that clone. Preserve the selection only if `next.regions.some(region => region.key === current.selectedKey)`; otherwise set it to `null`. Both actions set `dirty: true`, `validation: ""`, and status text of `"Undo. Save when ready."` or `"Redo. Save when ready."`. Return `false` without changing state when no board/document or no snapshot exists.

Call `resetHistory(historyRef.current)` in the successful `selectBoard` commit and successful `saveBoard` commit, and in `clearEditor`.

- [ ] **Step 4: Expose the new actions and keep drag previews out of history**

Add the public methods to `WorkbenchActions`:

```ts
undoDocument(): boolean;
redoDocument(): boolean;
```

Add both callbacks to the `actions` memo in `useWorkbench`. In `useHoldEditor`, add `originalDocument: EditorDocument | null` to `DragState`, clone the current document on pointer down, and retain it through the drag. On successful `completeDrag`, call `actions.replaceDocument(candidate, { ..., historySnapshot: drag.originalDocument })` exactly once; do not create history from `onPointerMove`. On pointer cancellation, lost capture, busy cancellation, and Escape, continue using non-history restoration.

Update the keyboard effect so editable targets return before shortcut handling. Above bracket/arrow handling, use:

```ts
const modifier = event.metaKey || event.ctrlKey;
if (modifier && event.key.toLowerCase() === "z") {
  const changed = event.shiftKey ? actions.redoDocument() : actions.undoDocument();
  if (changed) event.preventDefault();
  return;
}
if (event.ctrlKey && !event.metaKey && event.key.toLowerCase() === "y") {
  if (actions.redoDocument()) event.preventDefault();
  return;
}
if (event.key === "Escape" && cancelActiveEdit()) event.preventDefault();
```

Ensure the effect dependency array contains the new actions and `cancelActiveEdit`.

- [ ] **Step 5: Add the save shortcut in `WorkbenchApp`**

Create a memoized `saveFromShortcut` callback which returns early if `busy` or `state.board` is absent, otherwise calls `editor.cancelActiveEdit()` before `void actions.saveBoard()`. Add a `useEffect` document listener that ignores editable targets and only prevents `metaKey || ctrlKey` plus case-insensitive `s` when `saveFromShortcut` will act:

```tsx
React.useEffect(() => {
  const onKeyDown = (event: KeyboardEvent): void => {
    const target = event.target instanceof Element ? event.target : null;
    const tag = target?.tagName.toLowerCase();
    const editable = (target instanceof HTMLElement && target.isContentEditable)
      || target?.getAttribute("contenteditable") === "true"
      || tag === "input" || tag === "select" || tag === "textarea";
    if (editable || !(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "s") return;
    if (busy || !state.board) return;
    event.preventDefault();
    saveFromShortcut();
  };
  window.document.addEventListener("keydown", onKeyDown);
  return () => window.document.removeEventListener("keydown", onKeyDown);
}, [busy, saveFromShortcut, state.board]);
```

Use the same `saveFromShortcut` callback from the existing Save button so both paths share drag cancellation behavior.

- [ ] **Step 6: Run focused tests, then the full frontend verification suite**

Run: `cd Tools/HangboardWorkbench && npm run test:react -- --test-name-pattern="undo|redo|escape|save"`

Expected: PASS with every newly added keyboard/history test passing.

Run: `cd Tools/HangboardWorkbench && npm test && npm run check:bundle`

Expected: all strict typecheck, module tests, React tests, build, and generated-bundle freshness checks pass.

- [ ] **Step 7: Commit the implementation**

```bash
git add Tools/HangboardWorkbench/src/types.ts Tools/HangboardWorkbench/src/useWorkbench.ts Tools/HangboardWorkbench/src/useHoldEditor.ts Tools/HangboardWorkbench/src/WorkbenchApp.tsx Tools/HangboardWorkbench/tests/react-editor.test.tsx Tools/HangboardWorkbench/app.js
git commit -m "Add editor undo redo shortcuts"
```

After independently checking the commit diff and test output, push the new commit to `origin/add-editor-undo-redo-shortcuts`.
