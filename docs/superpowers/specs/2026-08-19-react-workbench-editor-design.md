# React Workbench Editor Design

## Goal

Replace the Hangboard Workbench browser editor's imperative DOM application with a React application while preserving its current UI, editing behavior, server API, packaged macOS runtime, and hosted deployment behavior.

## Scope

React will own all UI rendering beneath a single root element, including the repository toolbar, board library, SVG hold editor, validation panel, status bar, and hold inspector. The migration covers the existing board load/save flow, Git operations, authentication display, hold selection and editing, keyboard shortcuts, pointer gestures, validation rollback, and multi-piece physical-hold behavior.

The Python server, request/response formats, CSS visual design, and native macOS shell remain behaviorally unchanged unless integration wiring must change to serve the React bundle. The browser client, atomic-operation controller, and path editor move from standalone JavaScript globals into typed framework-independent modules imported by the React bundle. This work does not redesign the editor or add new editing features.

## Considered Approaches

### Recommended: locally bundled React application

Add a small npm/TypeScript/esbuild toolchain under `Tools/HangboardWorkbench`, author focused strict TypeScript and TSX modules, bundle React and React DOM into the existing `/app.js` asset, and test the rendered application in jsdom. The runtime remains a set of static files served and embedded by the Python packaging flow, with no network dependency.

This provides a real React ownership boundary, keeps release packaging simple, and lets the framework-independent modules remain directly testable while removing runtime global-script coupling.

### Rejected: React shell around the imperative application

Rendering the existing HTML from React and then running the current `app.js` against that DOM would minimize the first diff, but React and the imperative renderer would compete for ownership. State would still live in mutable module globals and direct DOM writes, so the refactor would not achieve its purpose.

### Rejected: browser-loaded React from a CDN

Loading React from a CDN avoids a build step but breaks offline packaged use, makes startup depend on a third party, and complicates the native shell's reliability and security posture.

## Architecture

`src/main.tsx` imports the typed browser client, controller, and path editor, constructs production dependencies, and mounts one `WorkbenchApp` using `createRoot`. `WorkbenchApp` composes focused toolbar, board-library, canvas, validation, and inspector components. A typed `useWorkbench` hook owns application state and asynchronous actions. A typed `useHoldEditor` hook owns transient pointer-drag state and exposes SVG event handlers plus editing actions. Pure geometry and model helpers live outside React so tests can cover them without rendering. Shared domain and dependency interfaces live in `types.ts`; browser capabilities such as fetch, navigation, dialogs, images, and native diagnostics are narrowed through an explicit `BrowserRuntime` interface rather than leaking `any` through components.

The following typed modules remain framework-independent integration boundaries:

- `workbench-client.ts` performs backend requests through a supplied `BrowserRuntime`.
- `workbench-controller.ts` validates documents and coordinates atomic operations.
- `path-editor.ts` parses, serializes, edits, and rotates SVG contours.
- A `WorkbenchDependencies` value supplies the client, controller functions, path editor functions, image loader, and dialogs to React.

React, React DOM, and all typed Workbench modules compile into `app.js`; none are globals or separate scripts loaded by `index.html`.

## State and Data Flow

The React state model retains the current fields: boards, active board, editable document, selected region key, Git branches and status, authentication state, dirty state, board/Git busy state, validation text, and status text. Form values for branch name, commit message, selected branch, and arbitrary rotation degrees become controlled React state.

Board and Git operations continue to use separate operation coordinators. Busy callbacks update React state and disable all conflicting actions. Board selection first loads and decodes the image and validates the document; only then does one state transition replace the active board and document. Saving captures both the board ID and editable document identity, so a delayed response cannot overwrite a newer board or newer edits.

Document changes use immutable updates at the React boundary. Geometry helpers may mutate a freshly cloned command array, but no action mutates the document object currently held by React state. This gives React reliable change detection and makes rollback explicit.

## SVG Editing

The canvas renders board image, hold paths, vertices, control points, and rotation affordances declaratively. Pointer capture remains on the SVG element. Transient drag details—pointer ID, original paths, original dirty state, pivot, accumulated angle, and parsed commands—live in a ref because they change during a gesture without independently driving layout.

Every pointer move computes a candidate document from the pointer-down snapshot. Pointer completion validates and commits the candidate. Pointer cancellation and lost capture restore the snapshot. A second pointer is ignored while a gesture is active. The existing CTM-first coordinate conversion and letterbox fallback are retained.

Keyboard actions remain document-level listeners installed and removed by a React effect. Inputs, selects, textareas, and content-editable targets preserve their native keyboard behavior. Arrow keys nudge by 1 pixel or 10 with Shift; brackets rotate by 15 degrees or 45 with Shift.

## Error Handling

Existing user-visible messages remain unchanged where tests currently assert them. Failed board loads retain the prior editor. Failed saves retain unsaved edits. Invalid edit candidates restore their original geometry and dirty state. A successful branch operation followed by a failed status refresh reports both facts. Authentication request failure remains non-fatal and shows the logged-out state.

The app must not render raw server content as HTML. The login link is React markup, while server and validation messages render as text.

## Build and Packaging

`package.json` and its lockfile define React, React DOM, TypeScript, esbuild, tsx, jsdom, and their exact type packages. A strict `tsconfig.json` provides a separate no-emit typecheck gate. The build script bundles `src/main.tsx` to `app.js` as a browser IIFE with an external source map omitted from packaged assets. `index.html` contains the root node and loads only the frontend `app.js` bundle.

The checked-in `app.js` remains the production asset embedded by PyInstaller and served by Python. Tests verify that it is freshly generated from source. The asset manifest exposes only the HTML, CSS, and bundled `/app.js` frontend assets; no frontend dependency is required at runtime.

## Testing

The migration follows red-green-refactor cycles:

1. Add a typed jsdom React harness and failing rendering tests for the initial layout, async initialization, busy controls, and security-sensitive text rendering.
2. Add failing workflow tests for board selection/save, hosted/local Git controls, branch operations, and pull-request prompts before implementing the state hook and toolbar/library components.
3. Add failing SVG interaction tests for selection, add/delete/type changes, nudge/rotate commands, pointer rotation, cancellation, and multi-piece holds before implementing the editor hook and canvas components.
4. Switch `index.html` to the React root and verify strict typechecking, the generated bundle, Python asset/packaging tests, the complete frontend suite, and a server smoke test.

Existing pure tests for the client, controller, and path editor are ported to TypeScript imports and remain behaviorally equivalent. The old fake-DOM tests for imperative rendering are replaced by user-observable jsdom tests rather than source-shape assertions.

## Acceptance Criteria

- React owns all workbench UI and SVG rendering from one root.
- All new application source and React tests are TypeScript/TSX and pass strict no-emit typechecking without `any` escape hatches.
- No imperative application renderer or manual DOM event-registration block remains.
- No standalone frontend JavaScript source or Workbench browser globals remain; the authored frontend is strict TypeScript/TSX.
- All current editor and repository workflows retain their observable behavior.
- The packaged app works without internet access or installed Node modules.
- The Python static asset manifest and PyInstaller build include the generated React bundle.
- JavaScript, Python Workbench, and macOS package tests pass.
- The served root page and API health/board endpoints pass a local smoke test.
