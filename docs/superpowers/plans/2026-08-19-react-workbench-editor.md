# React TypeScript Workbench Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the imperative Hangboard Workbench browser application and its standalone JavaScript modules with a locally bundled React application authored in strict TypeScript.

**Architecture:** Typed framework-independent modules implement requests, atomic operations, validation, and SVG path math. A React root composes focused TSX components, `useWorkbench` owns durable async state, and `useHoldEditor` owns transient SVG gestures. esbuild compiles the complete frontend, React, and React DOM into the existing packaged `app.js` asset.

**Tech Stack:** TypeScript 7.0.2, React 19.2.8, React DOM 19.2.8, esbuild 0.28.2, jsdom 30.0.1, tsx 4.23.12, Node.js 22+, Python 3.11+

**Spec:** `docs/superpowers/specs/2026-08-19-react-workbench-editor-design.md`

## Global Constraints

- Preserve current visible copy, class names, CSS, server API payloads, editor behavior, hosted authentication behavior, and macOS packaging behavior.
- React must own all markup beneath `#root`; do not run the legacy imperative app against React-rendered DOM.
- All authored frontend production modules and frontend tests must be `.ts`/`.tsx`, compile with `strict: true`, and contain no explicit `any`, `@ts-ignore`, or unchecked browser-global casts.
- Bundle the complete frontend into checked-in `Tools/HangboardWorkbench/app.js`; packaged runtime must not need Node, `node_modules`, a CDN, or internet access.
- Preserve atomic board selection/save semantics and separate board/Git operation serialization.
- Treat React state as immutable. Path commands may mutate only after parsing/cloning away from current state.
- Preserve CTM-first coordinate conversion, pointer capture, cancellation rollback, second-pointer rejection, multi-piece operations, and keyboard increments.
- Render server and validation messages as text, never injected HTML.
- Use TDD for every behavior: write the assertion, run it to see the expected failure, implement the minimum change, rerun focused and broader tests.
- Read `superpowers:test-driven-development/writing-good-tests.md` before creating or changing tests.
- Prefix every shell command with `rtk`.

---

### Task 1: TypeScript toolchain and framework-independent modules

**Files:**
- Create: `Tools/HangboardWorkbench/package.json`
- Create: `Tools/HangboardWorkbench/package-lock.json`
- Create: `Tools/HangboardWorkbench/tsconfig.json`
- Create: `Tools/HangboardWorkbench/src/types.ts`
- Create: `Tools/HangboardWorkbench/src/workbench-client.ts`
- Create: `Tools/HangboardWorkbench/src/workbench-controller.ts`
- Create: `Tools/HangboardWorkbench/src/path-editor.ts`
- Create: `Tools/HangboardWorkbench/tests/path-editor.test.ts`
- Create: `Tools/HangboardWorkbench/tests/workbench-modules.test.ts`

**Interfaces:**
- Produces `Point`, `PathCommand`, `HoldRegion`, `EditorDocument`, `BoardSummary`, `Board`, `GitStatus`, `AuthStatus`, `WorkbenchClient`, `WorkbenchController`, `PathEditor`, `BrowserRuntime`, `Dialogs`, and `WorkbenchDependencies`.
- Produces `createWorkbenchClient(runtime: BrowserRuntime): WorkbenchClient`.
- Produces typed `validateEditorDocument`, `loadBoardAtomically`, `saveBoardAtomically`, and `createBoardOperationCoordinator`.
- Produces typed `parsePath`, `serializePath`, `moveVertex`, `addVertex`, `deleteVertex`, and `rotatePath`.

- [ ] **Step 1: Add exact dependency and compiler configuration**

Create `package.json` with this initial contract:

```json
{
  "name": "hangboard-workbench-ui",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "engines": { "node": ">=22" },
  "scripts": {
    "build": "esbuild src/main.tsx --bundle --format=iife --platform=browser --target=es2020 --outfile=app.js",
    "typecheck": "tsc --noEmit",
    "test:modules": "tsx --test tests/path-editor.test.ts tests/workbench-modules.test.ts",
    "test": "npm run typecheck && npm run test:modules",
    "check:bundle": "npm run build && git diff --exit-code -- app.js"
  },
  "dependencies": {
    "react": "19.2.8",
    "react-dom": "19.2.8"
  },
  "devDependencies": {
    "@types/jsdom": "30.0.0",
    "@types/node": "26.2.0",
    "@types/react": "19.2.18",
    "@types/react-dom": "19.2.4",
    "esbuild": "0.28.2",
    "jsdom": "30.0.1",
    "tsx": "4.23.12",
    "typescript": "7.0.2"
  }
}
```

Create `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "noUncheckedIndexedAccess": true,
    "useUnknownInCatchVariables": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "types": ["node"]
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "tests/**/*.ts", "tests/**/*.tsx"]
}
```

Run `rtk npm install` inside `Tools/HangboardWorkbench`, retain the generated version-3 lockfile, and do not commit `node_modules`.

- [ ] **Step 2: Port pure module tests before production code**

Port every case from `path-editor.test.js` to `path-editor.test.ts`, importing from `../src/path-editor.ts`. Port the browser-client, controller validation, atomic load/save, and operation-coordinator cases from the first section of `workbench_direct.test.js` to `workbench-modules.test.ts`, importing typed modules directly.

Add compile-time fixtures that use real interfaces rather than casts. `BrowserRuntime` test doubles must supply `fetch`, `location.assign`, optional `postDiagnostic`, `confirm`, `prompt`, and `createImage` through typed functions.

- [ ] **Step 3: Run tests and verify RED**

```sh
rtk npm run test:modules
```

Expected: FAIL because `src/path-editor.ts`, `src/workbench-client.ts`, and `src/workbench-controller.ts` do not exist.

- [ ] **Step 4: Implement typed modules with behavior parity**

Move the existing algorithms without changing messages or request payloads. Key signatures:

```ts
export function parsePath(pathString: string): PathCommand[];
export function serializePath(commands: readonly PathCommand[]): string;
export function validateEditorDocument(document: unknown): EditorDocument;
export function createBoardOperationCoordinator(options?: {
  onBusyChange?: (busy: boolean) => void;
}): BoardOperationCoordinator;
export function createWorkbenchClient(runtime: BrowserRuntime): WorkbenchClient;
```

Use `unknown` for network payloads and caught errors, then narrow with predicates. `request<T>` must accept a payload parser rather than casting JSON. Native diagnostic failure remains non-fatal. A 401 with `login_url` must call `runtime.location.assign(loginUrl)`.

- [ ] **Step 5: Verify GREEN and strict typing**

```sh
rtk npm run typecheck
rtk npm run test:modules
rtk git diff --check
```

Expected: strict typecheck passes, all ported module tests pass, and diff check exits 0. The original JavaScript runtime remains untouched in this task.

- [ ] **Step 6: Commit Task 1**

```sh
rtk git add Tools/HangboardWorkbench/package.json Tools/HangboardWorkbench/package-lock.json Tools/HangboardWorkbench/tsconfig.json Tools/HangboardWorkbench/src Tools/HangboardWorkbench/tests/path-editor.test.ts Tools/HangboardWorkbench/tests/workbench-modules.test.ts
rtk git commit -m "refactor: type workbench browser modules"
```

---

### Task 2: React shell and board/repository workflows

**Files:**
- Create: `Tools/HangboardWorkbench/src/main.tsx`
- Create: `Tools/HangboardWorkbench/src/WorkbenchApp.tsx`
- Create: `Tools/HangboardWorkbench/src/useWorkbench.ts`
- Create: `Tools/HangboardWorkbench/src/components/RepositoryToolbar.tsx`
- Create: `Tools/HangboardWorkbench/src/components/BoardLibrary.tsx`
- Create: `Tools/HangboardWorkbench/src/components/HoldCanvas.tsx`
- Create: `Tools/HangboardWorkbench/src/components/HoldInspector.tsx`
- Create: `Tools/HangboardWorkbench/src/components/ValidationPanel.tsx`
- Create: `Tools/HangboardWorkbench/tests/react-harness.tsx`
- Create: `Tools/HangboardWorkbench/tests/react-app.test.tsx`
- Modify: `Tools/HangboardWorkbench/src/types.ts`
- Modify: `Tools/HangboardWorkbench/package.json`

**Interfaces:**
- Produces `WorkbenchState`, `WorkbenchActions`, `UseWorkbenchResult`, and typed component props.
- Produces `useWorkbench(dependencies: WorkbenchDependencies): UseWorkbenchResult`.
- Produces `WorkbenchApp({ dependencies }: WorkbenchAppProps)` and `mountWorkbench(root: HTMLElement, dependencies: WorkbenchDependencies): Root`.

- [ ] **Step 1: Add typed jsdom harness and failing shell tests**

The harness must create a new jsdom per test, set `IS_REACT_ACT_ENVIRONMENT`, render inside `act`, and restore every replaced global. Expose typed helpers `text`, `disabled`, `click`, `input`, `change`, `keyDown`, `pointer`, `flush`, `documentValue`, and `cleanup`.

Add failing tests for one `main.app-shell.direct-workbench` root, initial copy, all current regions/IDs, logged-out link rendering, and validation text containing `<img ...>` without creating an image node.

- [ ] **Step 2: Add failing workflow tests**

Cover these exact observable contracts:

- Initialization awaits authentication, Git status, then boards.
- Board selection disables all conflicting board/Git actions until image and document commit atomically.
- Failed board selection keeps the prior editor; failed save keeps unsaved edits.
- An old delayed save cannot overwrite a newer document identity.
- Detached HEAD differs from unavailable Git status and still permits New Branch.
- Hosted storage omits commit message, Commit, and Push while Save/Open PR remain.
- Dirty branch switch/create confirms once and honors cancellation; clean state never confirms.
- Successful switch/create plus failed status refresh reports both facts.
- Create clears branch input; empty commit message never calls the client.
- Push names the branch; dismissed PR title makes no call; accepted title/body are trimmed with base `main`.

- [ ] **Step 3: Run React tests and verify RED**

Add `"test:react": "tsx --test tests/react-app.test.tsx"` and update `test` to run `typecheck`, `test:modules`, then `test:react`.

```sh
rtk npm run test:react
```

Expected: FAIL because the React application and hook do not exist.

- [ ] **Step 4: Implement state hook and declarative shell**

Use this exact state shape:

```ts
interface WorkbenchState {
  boards: BoardSummary[];
  board: Board | null;
  document: EditorDocument | null;
  selectedKey: string | null;
  branches: string[];
  currentBranch: string | null;
  selectedBranch: string;
  gitStatusKnown: boolean;
  hasUncommittedChanges: boolean;
  dirty: boolean;
  busyBoard: boolean;
  busyGit: boolean;
  authenticated: boolean;
  username: string | null;
  hostedStorage: boolean;
  newBranchName: string;
  commitMessage: string;
  rotationDegrees: string;
  validation: string;
  status: string;
  boardsError: string;
}
```

Create each coordinator once with `useRef`; busy callbacks use functional state updates. Synchronize a `stateRef` for async identity checks. Clone `EditorDocument` through one typed helper. Components receive values/callbacks and never query the DOM.

Render the same hierarchy, IDs, class names, ARIA labels, and copy as the legacy `index.html`. Keep a placeholder declarative SVG in `HoldCanvas`; Task 3 adds editing.

- [ ] **Step 5: Verify GREEN**

```sh
rtk npm run typecheck
rtk npm test
rtk git diff --check
```

Expected: module and React workflow suites pass without `act` warnings.

- [ ] **Step 6: Commit Task 2**

```sh
rtk git add Tools/HangboardWorkbench/package.json Tools/HangboardWorkbench/src Tools/HangboardWorkbench/tests/react-harness.tsx Tools/HangboardWorkbench/tests/react-app.test.tsx
rtk git commit -m "refactor: move workbench workflows into React"
```

---

### Task 3: Declarative SVG hold editor

**Files:**
- Create: `Tools/HangboardWorkbench/src/editor-model.ts`
- Create: `Tools/HangboardWorkbench/src/useHoldEditor.ts`
- Create: `Tools/HangboardWorkbench/tests/react-editor.test.tsx`
- Modify: `Tools/HangboardWorkbench/src/types.ts`
- Modify: `Tools/HangboardWorkbench/src/useWorkbench.ts`
- Modify: `Tools/HangboardWorkbench/src/WorkbenchApp.tsx`
- Modify: `Tools/HangboardWorkbench/src/components/HoldCanvas.tsx`
- Modify: `Tools/HangboardWorkbench/src/components/HoldInspector.tsx`
- Modify: `Tools/HangboardWorkbench/tests/react-harness.tsx`
- Modify: `Tools/HangboardWorkbench/package.json`

**Interfaces:**
- Produces `holdSiblings`, `holdCentroid`, `rotationHandlePosition`, `svgPoint`, `nextHoldId`, and `nextRegionId` with domain types.
- Produces `useHoldEditor(options: UseHoldEditorOptions): HoldEditorActions`.
- Adds immutable `replaceDocument` and `editDocument` actions to `WorkbenchActions`.

- [ ] **Step 1: Add failing model and keyboard/action tests**

Add `react-editor.test.tsx` and update `test:react` to include both React suites. Test selection renders exactly one overlay; Add Hold creates/selects a centered square; Delete and type changes affect all pieces sharing `holdID`; arrows nudge by 1/10; brackets and buttons rotate by 15/45; arbitrary degrees accept finite non-zero decimals and reject empty, zero, `Infinity`, and `NaN`; extreme degrees reduce modulo 360. Input-targeted arrows retain native behavior.

Test top-edge and narrow-canvas rotation handles remain separated from the shared centroid and at least the handle radius inside every canvas edge.

- [ ] **Step 2: Add failing pointer tests**

Cover vertex, control-point, whole-path, and shared-centroid rotation drags. Assert each move derives from pointer-down paths. Cover double-click insertion, context-menu deletion with protected `M`, `pointercancel`, `lostpointercapture`, second-pointer rejection, CTM inverse before letterbox fallback, and invalid-geometry rollback.

- [ ] **Step 3: Run editor tests and verify RED**

```sh
rtk npx tsx --test Tools/HangboardWorkbench/tests/react-editor.test.tsx
```

Expected: FAIL because `editor-model.ts`, `useHoldEditor.ts`, and handlers do not exist.

- [ ] **Step 4: Implement typed pure helpers and editor hook**

Keep the transient gesture in `useRef<DragState>` with exact fields:

```ts
interface DragState {
  active: boolean;
  type: "vertex" | "control" | "path" | "rotation" | null;
  holdKey: string | null;
  commandIndex: number;
  controlIndex: number;
  startX: number;
  startY: number;
  commands: PathCommand[] | null;
  originalPath: string | null;
  originalPaths: Array<{ key: string; path: string }> | null;
  originalDirty: boolean;
  pivot: Point | null;
  lastAngle: number;
  totalAngle: number;
  pointerId: number | null;
}
```

Expose typed SVG React handlers and actions for rotate/add/delete/type/arbitrary degrees. Durable edits must functional-update cloned documents and validate/rollback. Install keydown in an effect with cleanup and the existing input/content-editable guard.

- [ ] **Step 5: Render editor SVG declaratively**

Render board image, keyed hold paths, vertices, controls, connector, and rotation handle as React SVG elements. Preserve all colors, opacities, stroke widths, dataset attributes, CSS classes, radii, and pointer capture behavior. The SVG owns pointer, double-click, and context-menu callbacks; regions own selection callbacks.

- [ ] **Step 6: Verify GREEN and commit**

```sh
rtk npm run typecheck
rtk npm test
rtk git diff --check
rtk git add Tools/HangboardWorkbench/package.json Tools/HangboardWorkbench/src Tools/HangboardWorkbench/tests/react-harness.tsx Tools/HangboardWorkbench/tests/react-editor.test.tsx
rtk git commit -m "refactor: render hold editor with React"
```

---

### Task 4: Production bundle, legacy removal, and packaged integration

**Files:**
- Modify: `Tools/HangboardWorkbench/src/main.tsx`
- Modify: `Tools/HangboardWorkbench/index.html`
- Generate: `Tools/HangboardWorkbench/app.js`
- Modify: `Tools/HangboardWorkbench/workbench_assets.py`
- Modify: `Tools/HangboardWorkbench/tests/test_server.py`
- Modify: `Tools/HangboardWorkbench/tests/test_workbench_packaging.py`
- Modify: `Tools/HangboardWorkbench/README.md`
- Delete: `Tools/HangboardWorkbench/workbench-client.js`
- Delete: `Tools/HangboardWorkbench/workbench-controller.js`
- Delete: `Tools/HangboardWorkbench/path-editor.js`
- Delete: `Tools/HangboardWorkbench/tests/path-editor.test.js`
- Delete: `Tools/HangboardWorkbench/tests/workbench_direct.test.js`

**Interfaces:**
- Consumes all typed modules and React components.
- Produces one runtime JavaScript asset at `/app.js` plus existing `/styles.css` and HTML routes.

- [ ] **Step 1: Add failing static-asset and bundle integration tests**

Update Python tests first to require `STATIC_ASSET_ROUTES` to contain exactly `/`, `/index.html`, `/styles.css`, and `/app.js`; assert the three legacy script routes are absent. Add a source audit that every authored frontend production/test file is `.ts`/`.tsx` except generated `app.js`.

Add/adjust a server test asserting `/` contains `<div id="root"></div>`, contains only one frontend script tag for `/app.js`, and does not mention the legacy scripts.

- [ ] **Step 2: Run focused tests and verify RED**

```sh
rtk uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests/test_server.py Tools/HangboardWorkbench/tests/test_workbench_packaging.py
```

Expected: FAIL because the asset manifest and HTML still expose legacy scripts.

- [ ] **Step 3: Switch production entry and remove legacy sources**

`main.tsx` must construct `BrowserRuntime` from `globalThis`, create the client, controller, path editor, image loader, and dialogs, then call `mountWorkbench` on `#root`.

Replace the body of `index.html` with only the root and `<script src="app.js"></script>`. Update `workbench_assets.py` to the four exact routes. Delete legacy JS source/tests with `apply_patch`, not a destructive shell command.

Run `rtk npm run build` inside `Tools/HangboardWorkbench`; never hand-edit generated `app.js`.

Update README verification to:

```sh
cd Tools/HangboardWorkbench && npm ci && npm run typecheck && npm test && npm run check:bundle
uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests
swift test --package-path Tools/HangboardWorkbench/macos
```

- [ ] **Step 4: Verify frontend and packaged integrations**

```sh
rtk npm run typecheck
rtk npm test
rtk npm run check:bundle
rtk uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests
rtk swift test --package-path Tools/HangboardWorkbench/macos
rtk git diff --check
```

Expected: all commands exit 0; bundle freshness produces no diff; packaging embeds `app.js`; macOS tests pass.

- [ ] **Step 5: Run an owned local-server smoke test**

Start `server.py` on loopback with port `0`, include `$CONDUCTOR_WORKSPACE_NAME` in the owned process/log name, capture its PID and printed port, and install an exit trap that terminates only that PID. Verify health JSON, non-empty board list, root React node, and bundled `/app.js`. Terminate the captured PID, wait for exit, and verify that exact PID no longer exists. Do not kill shared Python processes.

- [ ] **Step 6: Commit Task 4**

```sh
rtk git add Tools/HangboardWorkbench docs/superpowers/plans/2026-08-19-react-workbench-editor.md docs/superpowers/specs/2026-08-19-react-workbench-editor-design.md
rtk git commit -m "refactor: ship React TypeScript workbench"
```
