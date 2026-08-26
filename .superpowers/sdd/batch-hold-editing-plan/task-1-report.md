# Task 1 — Batch hold editing report

## Status

Implemented and committed batch hold selection and batch inspector actions for Hangboard Workbench.

## Behavior delivered

- Workbench state now stores ordered `selectedKeys` alongside the primary `selectedKey`.
- Command/Control click and Command/Control + Enter/Space toggle a hold in the selection; a plain activation replaces it.
- Every selected path is highlighted and exposes `aria-pressed`; the primary (most recently selected remaining) hold alone renders contour handles.
- The inspector displays the primary hold and a batch count when multiple paths are selected.
- Type, outline, button rotation, arbitrary rotation, and deletion expand selected paths to their physical-hold siblings. Rotation keeps a separate centroid per physical hold.
- Board loads, document replacement, saves, undo, and redo normalize selection against the new document so stale keys cannot remain.

## TDD evidence

Initial focused command (after installing the local package dependencies):

```sh
rtk npm run test:react -- --test-name-pattern='modifier selection|batch inspector actions'
```

RED outcome: 2 expected failures — selected paths had no `aria-pressed` batch state, and a batch type edit changed only the primary physical hold. (The first attempted test invocation was blocked before execution because `tsx` was not installed; `rtk npm ci` installed the declared local dependencies.)

GREEN focused command:

```sh
rtk npm run test:react -- --test-name-pattern='modifier selection|batch inspector actions|outline picker reflects'
```

GREEN outcome: 83 passing React tests, 0 failures.

Final required verification:

```sh
rtk npm test
rtk npm run check:bundle
```

Outcome: TypeScript check passed; module tests 81/81 passed; React tests 83/83 passed; esbuild bundle completed (`app.js`, 1.2 MB).

## Files changed

- `Tools/HangboardWorkbench/src/types.ts`
- `Tools/HangboardWorkbench/src/useWorkbench.ts`
- `Tools/HangboardWorkbench/src/useHoldEditor.ts`
- `Tools/HangboardWorkbench/src/WorkbenchApp.tsx`
- `Tools/HangboardWorkbench/src/components/HoldCanvas.tsx`
- `Tools/HangboardWorkbench/src/components/HoldInspector.tsx`
- `Tools/HangboardWorkbench/tests/react-editor.test.tsx`

## Self-review

- Confirmed batch operations deduplicate physical holds, so selecting two pieces of one hold does not rotate it twice.
- Confirmed rotation is per physical-hold centroid, preserving the relationship of each hold's pieces.
- Confirmed all document ingress points sanitize selected keys; `rtk git diff --check` reported no whitespace errors.
- No schema or persisted API contract changed. No known concerns.

## Review fix 1/5 — accurate batch deletion confirmation

The delete action previously confirmed only the primary key even though it deleted every selected physical hold and each hold's sibling pieces. It now retains `Delete hold "<primary-key>"?` for one physical hold and, for a batch, asks `Delete <count> selected holds and all of their pieces?` before any edit occurs.

Added a focused React editor test that selects two physical holds, captures the exact batch prompt, returns `false`, and verifies all paths plus the primary selection remain intact.

RED command:

```sh
rtk npm run test:react -- --test-name-pattern='batch deletion names'
```

RED output: the new test failed as expected because it received `Delete hold "b-piece-0"?` rather than the explicit batch prompt.

GREEN focused command:

```sh
rtk npm run test:react -- --test-name-pattern='batch deletion names|batch inspector actions|delete and type changes'
```

GREEN output: 84 React tests passed, 0 failed.

Final verification:

```sh
rtk npm test
rtk npm run check:bundle
```

Output: TypeScript check passed; module tests 81/81 passed; React tests 84/84 passed; esbuild bundle completed (`app.js`, 1.2 MB). `rtk git diff --check` passed.
