# Stage 3 Explicit Closing Corner Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Stage 3 per-corner editing treat explicit `L` and `Q` closures like explicit `C` closures, without duplicate closure segments or duplicate endpoint handles.

**Architecture:** Define explicit closure by path position and endpoint equality rather than command type. Reuse that single model predicate in both corner treatment and UI handle rendering, converting the existing closing segment to cubic only when treatment needs cubic handles.

**Tech Stack:** Browser JavaScript, CommonJS-compatible shared model, Node.js test runner.

## Global Constraints

- This branch changes only the local workbench UI/service behavior; do not alter smoothing, material rendering, or any visual-pipeline output.
- All accepted methods remain programmatic, repeatable, scalable, product-neutral, and valid for unseen commercial boards.
- Do not add product-specific production code, coordinates, masks, templates, inventories, or tuning.
- Preserve the existing Beastmaker 1000, Metolius Wood Grips Compact II, and Metolius Simulator 3D PNG hashes exactly.
- Preserve input command arrays without mutation.
- Prefix every shell command with `rtk`.

---

### Task 1: Generalize Explicit Closure Editing and Endpoint Rendering

**Files:**
- Modify: `Tools/hold-highlight-editor/vector-path-model.js`
- Modify: `Tools/hold-highlight-editor/app.js`
- Test: `Tools/hold-highlight-editor/tests/vector_path_model.test.js`

**Interfaces:**
- Consumes: parsed absolute display-path command arrays using `M`, `L`, `Q`, `C`, and `Z`.
- Produces: `isExplicitClosingCommand(commands, commandIndex) -> boolean`, exported from `vector-path-model.js` for the editor UI; updated `treatPathCorner(commands, cornerIndex, treatment, amount)` behavior.

- [ ] **Step 1: Add failing model tests for explicit `L` and `Q` closures**

Add table-driven regression tests with literal expected paths. For each input, treat corner index `0` as rounded, assert the existing closing command is converted in place to `C`, assert no extra drawable command is appended, assert endpoints are unchanged, and assert the input is not mutated:

```js
[
  "M 0 0 L 10 0 L 10 10 L 0 0 Z",
  "M 0 0 L 10 0 L 10 10 Q 3 7 0 0 Z",
]
```

Add direct tests that `isExplicitClosingCommand` returns true for terminal `L`, `Q`, and `C` commands ending at the current subpath's `M`, and false for non-terminal commands or terminal commands ending elsewhere. Include a multi-subpath case so the predicate uses the current subpath start rather than the first `M` in the entire path.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/vector_path_model.test.js
```

Expected: FAIL because explicit `L`/`Q` closure treatment adds a redundant `C`, and because `isExplicitClosingCommand` is not yet exported.

- [ ] **Step 3: Implement the smallest model fix**

Add `isExplicitClosingCommand(commands, commandIndex)` using validated path structure, the command immediately before `Z`, and endpoint equality with that command's own subpath `M`. In `treatPathCorner`, use the predicate instead of requiring `type === "C"`; when the closing segment is explicit, convert that existing `L`/`Q` segment with `asCubic` using its actual preceding endpoint and adjust its handles. Do not append a second closure segment.

- [ ] **Step 4: Reuse the predicate in UI endpoint rendering**

Import `isExplicitClosingCommand` from `HoldVectorPathModel` and use it in `renderVectorHandles` so an explicit closing endpoint is hidden for `L`, `Q`, and `C`, including paths with multiple subpaths. Do not add DOM-only production hooks or product-specific behavior.

- [ ] **Step 5: Verify GREEN and regression safety**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/vector_path_model.test.js
rtk node --test Tools/hold-highlight-editor/tests/*.test.js
rtk node --check Tools/hold-highlight-editor/vector-path-model.js
rtk node --check Tools/hold-highlight-editor/app.js
rtk git diff --check
```

Expected: all tests pass, both files parse, and the diff check is clean.

- [ ] **Step 6: Commit**

```bash
rtk git add Tools/hold-highlight-editor/vector-path-model.js Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/tests/vector_path_model.test.js
rtk git commit -m "Fix explicit closing corner editing"
```
