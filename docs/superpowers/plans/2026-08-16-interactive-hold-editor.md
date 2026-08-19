# Interactive Hold Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive SVG path editing to the Hangboard Workbench so users can visually refine manually authored hold contours by dragging vertices, adjusting bezier curves, and repositioning holds.

**Architecture:** A standalone `path-editor.js` module (exported both as CommonJS and `globalThis.HoldPathEditor`) parses `displayPath` strings into a structured command array and exposes pure mutation helpers (`moveVertex`, `addVertex`, `deleteVertex`). `app.js` renders vertex/control point handles on the SVG, wires pointer events for dragging, and calls into `path-editor.js` on each edit before serializing back to `displayPath`. No changes to the backend data model or save flow.

**Tech Stack:** Dependency-free vanilla JavaScript, SVG DOM, Node test runner.

**Spec:** `docs/superpowers/specs/2026-08-16-interactive-hold-editor-design.md`

---

### Task 1: Path command parser and serializer

**Files:**
- Create: `Tools/HangboardWorkbench/path-editor.js`
- Create: `Tools/HangboardWorkbench/tests/path-editor.test.js`

- [ ] **Step 1: Write failing tests for path parsing**

```javascript
// tests/path-editor.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { parsePath, serializePath } = require("../path-editor.js");

test("parsePath splits an SVG path string into commands", () => {
  const commands = parsePath("M 10 20 L 30 40 Q 50 60 70 80 C 10 20 30 40 50 60 Z");
  assert.equal(commands.length, 5);
  assert.equal(commands[0].type, "M");
  assert.deepEqual(commands[0].points, [{ x: 10, y: 20 }]);
  assert.equal(commands[1].type, "L");
  assert.deepEqual(commands[1].points, [{ x: 30, y: 40 }]);
  assert.equal(commands[2].type, "Q");
  assert.deepEqual(commands[2].points, [{ x: 70, y: 80 }]);
  assert.deepEqual(commands[2].controls, [{ x: 50, y: 60 }]);
  assert.equal(commands[3].type, "C");
  assert.deepEqual(commands[3].points, [{ x: 50, y: 60 }]);
  assert.deepEqual(commands[3].controls, [{ x: 10, y: 20 }, { x: 30, y: 40 }]);
  assert.equal(commands[4].type, "Z");
});

test("parsePath handles a simple triangle", () => {
  const commands = parsePath("M 0 0 L 100 0 L 50 80 Z");
  assert.equal(commands.length, 4);
  assert.equal(commands[0].type, "M");
  assert.equal(commands[3].type, "Z");
});

test("serializePath reconstructs an SVG path string", () => {
  const input = "M 10 20 L 30 40 Q 50 60 70 80 C 10 20 30 40 50 60 Z";
  const commands = parsePath(input);
  const output = serializePath(commands);
  assert.equal(output, input);
});

test("serializePath handles integer coordinates cleanly", () => {
  const commands = [{ type: "M", points: [{ x: 0, y: 0 }] }, { type: "L", points: [{ x: 100, y: 0 }] }, { type: "L", points: [{ x: 50, y: 80 }] }, { type: "Z", points: [] }];
  assert.equal(serializePath(commands), "M 0 0 L 100 0 L 50 80 Z");
});

test("parsePath throws on malformed input", () => {
  assert.throws(() => parsePath(""), /non-empty/);
  assert.throws(() => parsePath("not a path"), /command/);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test Tools/HangboardWorkbench/tests/path-editor.test.js`
Expected: FAIL — module not found

- [ ] **Step 3: Implement parsePath and serializePath**

```javascript
// path-editor.js
"use strict";

function parsePath(pathString) {
  if (typeof pathString !== "string" || !pathString.trim()) {
    throw new Error("path must be a non-empty string");
  }
  const tokens = pathString.trim().split(/[\s,]+/);
  const commands = [];
  let i = 0;
  const ARITY = { M: 1, L: 1, Q: 2, C: 3, Z: 0 };

  while (i < tokens.length) {
    const cmd = tokens[i];
    if (!ARITY.hasOwnProperty(cmd)) throw new Error(`expected a command, got "${cmd}"`);
    i++;
    const arity = ARITY[cmd];
    const points = [];
    for (let j = 0; j < arity; j++) {
      const x = parseFloat(tokens[i++]);
      const y = parseFloat(tokens[i++]);
      points.push({ x, y });
    }
    const controls = cmd === "Q" ? [points[0]] : cmd === "C" ? [points[0], points[1]] : [];
    const endpoint = cmd === "Z" ? [] : cmd === "Q" ? [points[1]] : cmd === "C" ? [points[2]] : points;
    commands.push({ type: cmd, points: endpoint, controls });
  }
  return commands;
}

function serializePath(commands) {
  const parts = [];
  for (const cmd of commands) {
    if (cmd.type === "Z") { parts.push("Z"); continue; }
    if (cmd.type === "M" || cmd.type === "L") {
      parts.push(cmd.type, fmt(cmd.points[0].x), fmt(cmd.points[0].y));
    } else if (cmd.type === "Q") {
      parts.push("Q", fmt(cmd.controls[0].x), fmt(cmd.controls[0].y), fmt(cmd.points[0].x), fmt(cmd.points[0].y));
    } else if (cmd.type === "C") {
      parts.push("C", fmt(cmd.controls[0].x), fmt(cmd.controls[0].y), fmt(cmd.controls[1].x), fmt(cmd.controls[1].y), fmt(cmd.points[0].x), fmt(cmd.points[0].y));
    }
  }
  return parts.join(" ");
}

function fmt(n) { return Number.isInteger(n) ? String(n) : String(Math.round(n * 1e6) / 1e6); }

module.exports = { parsePath, serializePath };
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test Tools/HangboardWorkbench/tests/path-editor.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add Tools/HangboardWorkbench/path-editor.js Tools/HangboardWorkbench/tests/path-editor.test.js
git commit -m "feat: add path command parser and serializer for hold editor"
```

---

### Task 2: Vertex manipulation utilities

**Files:**
- Modify: `Tools/HangboardWorkbench/path-editor.js`
- Modify: `Tools/HangboardWorkbench/tests/path-editor.test.js`

- [ ] **Step 1: Write failing tests for moveVertex**

Append to `tests/path-editor.test.js`:

```javascript
const { moveVertex, addVertex, deleteVertex } = require("../path-editor.js");

test("moveVertex translates an anchor point and its dependent controls", () => {
  const commands = parsePath("M 0 0 L 50 50 Q 60 60 100 100 Z");
  moveVertex(commands, 1, 10, 10);
  assert.deepEqual(commands[1].points, [{ x: 60, y: 60 }]);
});

test("moveVertex on a Q endpoint shifts the curve", () => {
  const commands = parsePath("M 0 0 L 10 10 Q 20 20 50 50 Z");
  moveVertex(commands, 2, 5, -5);
  assert.deepEqual(commands[2].points, [{ x: 55, y: 45 }]);
  assert.deepEqual(commands[2].controls, [{ x: 25, y: 15 }]);
});

test("moveVertex on a C endpoint shifts both control points equally", () => {
  const commands = parsePath("M 0 0 L 10 10 C 20 20 30 30 50 50 Z");
  moveVertex(commands, 2, 5, 5);
  assert.deepEqual(commands[2].points, [{ x: 55, y: 55 }]);
  assert.deepEqual(commands[2].controls, [{ x: 25, y: 25 }, { x: 35, y: 35 }]);
});

test("moveVertex on M shifts the start point", () => {
  const commands = parsePath("M 10 10 L 50 50 Z");
  moveVertex(commands, 0, 5, 5);
  assert.deepEqual(commands[0].points, [{ x: 15, y: 15 }]);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test Tools/HangboardWorkbench/tests/path-editor.test.js`
Expected: FAIL — moveVertex not defined

- [ ] **Step 3: Implement moveVertex**

Append to `path-editor.js`:

```javascript
function moveVertex(commands, index, dx, dy) {
  const cmd = commands[index];
  if (!cmd || cmd.type === "Z") return;
  for (const p of cmd.points) { p.x += dx; p.y += dy; }
  if (cmd.type === "Q" || cmd.type === "C") {
    for (const c of cmd.controls) { c.x += dx; c.y += dy; }
  }
}

module.exports = { parsePath, serializePath, moveVertex };
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test Tools/HangboardWorkbench/tests/path-editor.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add Tools/HangboardWorkbench/path-editor.js Tools/HangboardWorkbench/tests/path-editor.test.js
git commit -m "feat: add moveVertex utility for hold editor"
```

---

### Task 3: Add vertex (De Casteljau subdivision)

**Files:**
- Modify: `Tools/HangboardWorkbench/path-editor.js`
- Modify: `Tools/HangboardWorkbench/tests/path-editor.test.js`

- [ ] **Step 1: Write failing tests for addVertex**

Append to `tests/path-editor.test.js`:

```javascript
test("addVertex on an L segment inserts a new L at the midpoint", () => {
  const commands = parsePath("M 0 0 L 100 0 L 100 100 Z");
  addVertex(commands, 1, 50, 0);
  assert.equal(commands.length, 5);
  assert.equal(commands[1].type, "L");
  assert.deepEqual(commands[1].points, [{ x: 50, y: 0 }]);
  assert.equal(commands[2].type, "L");
  assert.deepEqual(commands[2].points, [{ x: 100, y: 0 }]);
});

test("addVertex on a Q segment subdivides the bezier", () => {
  const commands = parsePath("M 0 0 Q 50 100 100 0 Z");
  addVertex(commands, 0, 50, 50);
  assert.equal(commands.length, 4);
  assert.equal(commands[0].type, "M");
  assert.equal(commands[1].type, "Q");
  assert.equal(commands[2].type, "Q");
  assert.equal(commands[3].type, "Z");
  assert.deepEqual(commands[1].points, [{ x: 50, y: 50 }]);
  assert.deepEqual(commands[2].points, [{ x: 100, y: 0 }]);
});

test("addVertex on a C segment subdivides the cubic bezier", () => {
  const commands = parsePath("M 0 0 C 25 100 75 100 100 0 Z");
  addVertex(commands, 0, 50, 50);
  assert.equal(commands.length, 4);
  assert.equal(commands[1].type, "C");
  assert.equal(commands[2].type, "C");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test Tools/HangboardWorkbench/tests/path-editor.test.js`
Expected: FAIL — addVertex not defined

- [ ] **Step 3: Implement addVertex**

Append to `path-editor.js`:

```javascript
function addVertex(commands, afterIndex, x, y) {
  const cmd = commands[afterIndex];
  if (!cmd || cmd.type === "Z") return;
  const nextIndex = (afterIndex + 1) % commands.length;
  const next = commands[nextIndex];

  if (cmd.type === "M") {
    commands.splice(nextIndex, 0, { type: "L", points: [{ x, y }], controls: [] });
    return;
  }

  if (cmd.type === "L") {
    commands.splice(nextIndex, 0, { type: "L", points: [{ x, y }], controls: [] });
    return;
  }

  if (cmd.type === "Q") {
    const p0 = cmd.points[0];
    const c = cmd.controls[0];
    const p1 = next.type === "Z" ? cmd.points[0] : next.points[0];
    const mid = bezierQuad(p0, c, p1, 0.5);
    const newCmd1 = { type: "Q", points: [mid], controls: [lerp2(p0, c, 0.5)] };
    const newCmd2 = { type: "Q", points: [p1], controls: [lerp2(c, p1, 0.5)] };
    commands.splice(afterIndex, 1, newCmd1, newCmd2);
    return;
  }

  if (cmd.type === "C") {
    const p0 = cmd.points[0];
    const c1 = cmd.controls[0];
    const c2 = cmd.controls[1];
    const p1 = next.type === "Z" ? cmd.points[0] : next.points[0];
    const { left, right } = subdivideCubic(p0, c1, c2, p1);
    commands.splice(afterIndex, 1, left, right);
    return;
  }
}

function lerp2(a, b, t) { return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }; }

function bezierQuad(p0, c, p1, t) {
  const u = 1 - t;
  return {
    x: u * u * p0.x + 2 * u * t * c.x + t * t * p1.x,
    y: u * u * p0.y + 2 * u * t * c.y + t * t * p1.y,
  };
}

function subdivideCubic(p0, c1, c2, p3) {
  const m01 = lerp2(p0, c1, 0.5);
  const m12 = lerp2(c1, c2, 0.5);
  const m23 = lerp2(c2, p3, 0.5);
  const m012 = lerp2(m01, m12, 0.5);
  const m123 = lerp2(m12, m23, 0.5);
  const mid = lerp2(m012, m123, 0.5);
  return {
    left: { type: "C", points: [mid], controls: [m01, m012] },
    right: { type: "C", points: [p3], controls: [m123, m23] },
  };
}

module.exports = { parsePath, serializePath, moveVertex, addVertex };
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test Tools/HangboardWorkbench/tests/path-editor.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add Tools/HangboardWorkbench/path-editor.js Tools/HangboardWorkbench/tests/path-editor.test.js
git commit -m "feat: add addVertex with De Casteljau subdivision"
```

---

### Task 4: Delete vertex

**Files:**
- Modify: `Tools/HangboardWorkbench/path-editor.js`
- Modify: `Tools/HangboardWorkbench/tests/path-editor.test.js`

- [ ] **Step 1: Write failing tests for deleteVertex**

Append to `tests/path-editor.test.js`:

```javascript
test("deleteVertex removes a vertex and converts adjacent curves to lines", () => {
  const commands = parsePath("M 0 0 L 25 50 L 50 0 L 75 50 Z");
  deleteVertex(commands, 2);
  assert.equal(commands.length, 4);
  assert.equal(commands[2].type, "L");
  assert.deepEqual(commands[2].points, [{ x: 75, y: 50 }]);
});

test("deleteVertex on an L between Q segments converts to a single L", () => {
  const commands = parsePath("M 0 0 Q 25 50 50 0 L 75 50 Q 100 100 125 0 Z");
  deleteVertex(commands, 2);
  assert.equal(commands.length, 4);
  assert.equal(commands[1].type, "L");
  assert.equal(commands[2].type, "L");
});

test("deleteVertex refuses to delete the M vertex", () => {
  const commands = parsePath("M 0 0 L 50 0 Z");
  deleteVertex(commands, 0);
  assert.equal(commands.length, 3);
  assert.equal(commands[0].type, "M");
});

test("deleteVertex on the vertex before Z wraps correctly", () => {
  const commands = parsePath("M 0 0 L 50 0 L 100 50 Z");
  deleteVertex(commands, 2);
  assert.equal(commands.length, 3);
  assert.equal(commands[0].type, "M");
  assert.equal(commands[1].type, "L");
  assert.equal(commands[2].type, "Z");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test Tools/HangboardWorkbench/tests/path-editor.test.js`
Expected: FAIL — deleteVertex not defined

- [ ] **Step 3: Implement deleteVertex**

Append to `path-editor.js`:

```javascript
function deleteVertex(commands, index) {
  if (index === 0 || commands[index].type === "Z" || commands.length <= 3) return;
  const prev = commands[(index - 1 + commands.length) % commands.length];
  const next = commands[(index + 1) % commands.length];
  if (next.type === "Z") {
    commands.splice(index, 1);
    return;
  }
  const isCurve = prev.type === "Q" || prev.type === "C" || next.type === "Q" || next.type === "C";
  if (isCurve) {
    const prevStart = prev.type === "M" ? prev.points[0] : prev.type === "Z" ? null : prev.points[0];
    const nextEnd = next.points[0];
    const l = { type: "L", points: [{ x: nextEnd.x, y: nextEnd.y }], controls: [] };
    commands.splice(index, 1, l);
    if (prev.type === "Q" || prev.type === "C") {
      const idx = (index - 1 + commands.length) % commands.length;
      commands[idx] = { type: "L", points: [commands[idx].points[commands[idx].points.length - 1]], controls: [] };
    }
  } else {
    commands.splice(index, 1);
  }
}

module.exports = { parsePath, serializePath, moveVertex, addVertex, deleteVertex };
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test Tools/HangboardWorkbench/tests/path-editor.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add Tools/HangboardWorkbench/path-editor.js Tools/HangboardWorkbench/tests/path-editor.test.js
git commit -m "feat: add deleteVertex utility for hold editor"
```

---

### Task 5: Handle rendering and SVG integration

**Files:**
- Modify: `Tools/HangboardWorkbench/app.js`
- Modify: `Tools/HangboardWorkbench/styles.css`

- [ ] **Step 1: Add CSS for path editor handles**

Append to `styles.css`:

```css
.path-editor-vertex { cursor: grab; }
.path-editor-vertex:active { cursor: grabbing; }
.path-editor-control { cursor: move; }
.path-editor-line { pointer-events: none; }
```

- [ ] **Step 2: Add path editor rendering to app.js**

In `app.js`, add after the `svgNS` constant (line 11):

```javascript
const { parsePath, serializePath, moveVertex, addVertex, deleteVertex } = (() => {
  try { return require("./path-editor.js"); } catch { return globalThis.HoldPathEditor || {}; }
})();
```

In `renderEditor()`, after the hold rendering loop (after line 98), add path editor overlay rendering. Replace the `renderEditor` function with:

```javascript
function renderEditor() {
  const documentValue = state.document;
  const selected = selectedHold();
  el["empty-state"].classList.toggle("hidden", Boolean(documentValue));
  el["hold-overlay"].replaceChildren();
  el["editor-svg"].querySelector(".path-editor-overlay")?.remove();
  if (!documentValue) {
    el["board-name"].textContent = "No board selected";
    el["board-image"].removeAttribute("href");
    return;
  }
  const { width, height } = documentValue.canvas;
  el["board-name"].textContent = state.board.displayName;
  el["editor-svg"].setAttribute("viewBox", `0 0 ${width} ${height}`);
  el["editor-svg"].setAttribute("width", String(width));
  el["editor-svg"].setAttribute("height", String(height));
  el["board-image"].setAttribute("href", state.board.imageUrl);
  el["board-image"].setAttribute("width", String(width));
  el["board-image"].setAttribute("height", String(height));
  for (const hold of documentValue.regions) {
    const shape = document.createElementNS(svgNS, "path");
    shape.setAttribute("d", hold.displayPath);
    shape.setAttribute("fill", TYPE_COLORS[hold.type] || "#ff754f");
    shape.setAttribute("fill-opacity", hold.key === selected?.key ? "0.58" : "0.3");
    shape.setAttribute("stroke", hold.key === selected?.key ? "#fff7dc" : TYPE_COLORS[hold.type] || "#ff754f");
    shape.setAttribute("stroke-width", hold.key === selected?.key ? "2.2" : "1.4");
    shape.classList.add("region-shape");
    shape.addEventListener("click", () => { state.selectedKey = hold.key; render(); });
    el["hold-overlay"].append(shape);
  }
  if (selected) {
    renderPathHandles(selected, width, height);
  }
}

function renderPathHandles(hold, canvasWidth, canvasHeight) {
  if (!parsePath) return;
  const overlay = document.createElementNS(svgNS, "g");
  overlay.classList.add("path-editor-overlay");
  let commands;
  try { commands = parsePath(hold.displayPath); } catch { return; }
  for (let i = 0; i < commands.length; i++) {
    const cmd = commands[i];
    if (cmd.type === "Z") continue;
    const endpoint = cmd.points[cmd.points.length - 1];
    const circle = document.createElementNS(svgNS, "circle");
    circle.setAttribute("cx", String(endpoint.x));
    circle.setAttribute("cy", String(endpoint.y));
    circle.setAttribute("r", "6");
    circle.setAttribute("fill", TYPE_COLORS[hold.type] || "#ff754f");
    circle.setAttribute("stroke", "#fff7dc");
    circle.setAttribute("stroke-width", "1.5");
    circle.classList.add("path-editor-vertex");
    circle.dataset.index = String(i);
    overlay.append(circle);
    for (let j = 0; j < cmd.controls.length; j++) {
      const cp = cmd.controls[j];
      const anchor = j === 0 ? (i === 0 ? cmd.points[0] : commands[i - 1]?.type === "Z" ? commands[0].points[0] : commands[i - 1].points[0]) : cmd.points[0];
      if (anchor) {
        const line = document.createElementNS(svgNS, "line");
        line.setAttribute("x1", String(anchor.x));
        line.setAttribute("y1", String(anchor.y));
        line.setAttribute("x2", String(cp.x));
        line.setAttribute("y2", String(cp.y));
        line.setAttribute("stroke", "#888");
        line.setAttribute("stroke-width", "1");
        line.setAttribute("stroke-dasharray", "4 2");
        line.classList.add("path-editor-line");
        overlay.append(line);
      }
      const cc = document.createElementNS(svgNS, "circle");
      cc.setAttribute("cx", String(cp.x));
      cc.setAttribute("cy", String(cp.y));
      cc.setAttribute("r", "3");
      cc.setAttribute("fill", "#888");
      cc.setAttribute("stroke", "#fff");
      cc.setAttribute("stroke-width", "1");
      cc.classList.add("path-editor-control");
      cc.dataset.index = String(i);
      cc.dataset.control = String(j);
      overlay.append(cc);
    }
  }
  el["editor-svg"].append(overlay);
}
```

- [ ] **Step 3: Verify no regressions**

Load a board in the workbench. Confirm holds render with colored overlays. Select a hold — vertex handles and control point handles should appear on its contour. Deselect — handles disappear.

- [ ] **Step 4: Commit**

```bash
git add Tools/HangboardWorkbench/app.js Tools/HangboardWorkbench/styles.css
git commit -m "feat: render vertex and control point handles on selected hold"
```

---

### Task 6: Drag interaction (vertex, control, body)

**Files:**
- Modify: `Tools/HangboardWorkbench/app.js`

- [ ] **Step 1: Add drag state and handlers to app.js**

After the `renderPathHandles` function, add the path editor drag system:

```javascript
const drag = { active: false, type: null, holdKey: null, commandIndex: -1, controlIndex: -1, startX: 0, startY: 0, commands: null, originalPath: null };

function svgPoint(event) {
  const svg = el["editor-svg"];
  const rect = svg.getBoundingClientRect();
  const vb = svg.getAttribute("viewBox").split(" ").map(Number);
  const scaleX = vb[2] / rect.width;
  const scaleY = vb[3] / rect.height;
  return { x: (event.clientX - rect.left) * scaleX, y: (event.clientY - rect.top) * scaleY };
}

function handlePointerDown(event) {
  const target = event.target;
  if (target.classList.contains("path-editor-vertex")) {
    event.preventDefault();
    const hold = selectedHold();
    if (!hold) return;
    const idx = parseInt(target.dataset.index, 10);
    const pt = svgPoint(event);
    drag.active = true;
    drag.type = "vertex";
    drag.holdKey = hold.key;
    drag.commandIndex = idx;
    drag.startX = pt.x;
    drag.startY = pt.y;
    drag.commands = parsePath(hold.displayPath);
    drag.originalPath = hold.displayPath;
  } else if (target.classList.contains("path-editor-control")) {
    event.preventDefault();
    const hold = selectedHold();
    if (!hold) return;
    const pt = svgPoint(event);
    drag.active = true;
    drag.type = "control";
    drag.holdKey = hold.key;
    drag.commandIndex = parseInt(target.dataset.index, 10);
    drag.controlIndex = parseInt(target.dataset.control, 10);
    drag.startX = pt.x;
    drag.startY = pt.y;
    drag.commands = parsePath(hold.displayPath);
    drag.originalPath = hold.displayPath;
  } else if (target.classList.contains("region-shape") && !target.classList.contains("path-editor-vertex")) {
    event.preventDefault();
    const hold = selectedHold();
    if (!hold || hold.key !== state.selectedKey) return;
    const pt = svgPoint(event);
    drag.active = true;
    drag.type = "body";
    drag.holdKey = hold.key;
    drag.startX = pt.x;
    drag.startY = pt.y;
    drag.commands = parsePath(hold.displayPath);
    drag.originalPath = hold.displayPath;
  }
}

function handlePointerMove(event) {
  if (!drag.active) return;
  event.preventDefault();
  const pt = svgPoint(event);
  const dx = pt.x - drag.startX;
  const dy = pt.y - drag.startY;
  const hold = state.document?.regions.find((r) => r.key === drag.holdKey);
  if (!hold) { drag.active = false; return; }
  const cmds = drag.commands.map((c) => ({
    ...c,
    points: c.points.map((p) => ({ ...p })),
    controls: c.controls.map((p) => ({ ...p })),
  }));
  if (drag.type === "vertex") {
    moveVertex(cmds, drag.commandIndex, dx, dy);
  } else if (drag.type === "control") {
    const cmd = cmds[drag.commandIndex];
    if (cmd && cmd.controls[drag.controlIndex]) {
      cmd.controls[drag.controlIndex].x += dx;
      cmd.controls[drag.controlIndex].y += dy;
    }
  } else if (drag.type === "body") {
    for (const cmd of cmds) {
      if (cmd.type === "Z") continue;
      for (const p of cmd.points) { p.x += dx; p.y += dy; }
      for (const c of cmd.controls) { c.x += dx; c.y += dy; }
    }
  }
  const newPath = serializePath(cmds);
  hold.displayPath = newPath;
  drag.startX = pt.x;
  drag.startY = pt.y;
  drag.commands = cmds;
  state.dirty = true;
  render();
}

function handlePointerUp() {
  if (!drag.active) return;
  drag.active = false;
  const hold = state.document?.regions.find((r) => r.key === drag.holdKey);
  if (!hold) return;
  try {
    validateEditorDocument(state.document);
    setValidation();
    setStatus("Contour updated. Save when ready.");
  } catch (error) {
    hold.displayPath = drag.originalPath;
    setValidation(error.message || "Contour is invalid.");
    setStatus("Edit reverted — contour is invalid.");
  }
  render();
}

function handleDoubleClick(event) {
  if (event.target.classList.contains("path-editor-vertex") || event.target.classList.contains("path-editor-control")) return;
  const hold = selectedHold();
  if (!hold) return;
  const pt = svgPoint(event);
  let commands;
  try { commands = parsePath(hold.displayPath); } catch { return; }
  for (let i = 0; i < commands.length; i++) {
    const cmd = commands[i];
    if (cmd.type === "Z") continue;
    const nextIdx = (i + 1) % commands.length;
    const next = commands[nextIdx];
    if (next.type === "Z" && cmd.type === "M") continue;
    const start = cmd.points[cmd.points.length - 1];
    const end = next.type === "Z" ? commands[0].points[0] : next.points[0];
    if (closestPointOnSegment(start, end, pt) < 15) {
      addVertex(commands, i, pt.x, pt.y);
      hold.displayPath = serializePath(commands);
      state.dirty = true;
      try { validateEditorDocument(state.document); setValidation(); } catch (e) { setValidation(e.message); }
      render();
      return;
    }
  }
}

function handleContextMenu(event) {
  if (!event.target.classList.contains("path-editor-vertex")) return;
  event.preventDefault();
  const hold = selectedHold();
  if (!hold) return;
  const idx = parseInt(event.target.dataset.index, 10);
  let commands;
  try { commands = parsePath(hold.displayPath); } catch { return; }
  if (idx === 0) return;
  deleteVertex(commands, idx);
  hold.displayPath = serializePath(commands);
  state.dirty = true;
  try { validateEditorDocument(state.document); setValidation(); } catch (e) { setValidation(e.message); }
  render();
}

function closestPointOnSegment(a, b, p) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return Math.hypot(p.x - a.x, p.y - a.y);
  let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}
```

- [ ] **Step 2: Wire event listeners**

In the event listener section at the bottom of `app.js` (after line 234), add:

```javascript
el["editor-svg"].addEventListener("pointerdown", handlePointerDown);
el["editor-svg"].addEventListener("pointermove", handlePointerMove);
el["editor-svg"].addEventListener("pointerup", handlePointerUp);
el["editor-svg"].addEventListener("dblclick", handleDoubleClick);
el["editor-svg"].addEventListener("contextmenu", handleContextMenu);
```

- [ ] **Step 3: Verify end-to-end interaction**

Load a board, select a hold. Verify:
1. Drag a vertex handle — contour reshapes live
2. Drag a control point — bezier curve adjusts
3. Drag the hold body — entire hold moves
4. Double-click a segment — new vertex appears
5. Right-click a vertex — vertex is removed
6. Make an invalid edit — validation panel shows error, edit reverts
7. Make a valid edit — dirty state shows "Unsaved changes"

- [ ] **Step 4: Commit**

```bash
git add Tools/HangboardWorkbench/app.js
git commit -m "feat: add interactive drag, add, and delete for hold vertices"
```

---

### Task 7: Integration and cleanup

**Files:**
- Modify: `Tools/HangboardWorkbench/app.js`
- Modify: `Tools/HangboardWorkbench/index.html`

- [ ] **Step 1: Remove the textarea-based hold path editor from the inspector panel**

In `index.html`, remove the textarea and apply button from the inspector form (lines 81-83):

```html
<!-- Remove these lines: -->
<label>Closed contour <textarea id="hold-path" rows="8" spellcheck="false"></textarea></label>
<button class="tool-button" id="apply-hold-button" type="submit">Apply contour</button>
```

- [ ] **Step 2: Remove unused textarea references from app.js**

Remove from the `el` array (line 17): `"hold-path"`, `"apply-hold-button"`, `"hold-form"`.

Remove the `applyHold` function and its event listener (lines 176-193, 233).

Remove from `renderInspector`: the textarea-related lines (lines 103-104, 109-110).

- [ ] **Step 3: Add path-editor.js to the script load order in index.html**

Add before `app.js`:

```html
<script src="path-editor.js"></script>
```

- [ ] **Step 4: Run existing tests to verify no regressions**

Run: `node --test Tools/HangboardWorkbench/tests/workbench_direct.test.js`
Expected: PASS (update FakeElement if needed to support new element IDs)

- [ ] **Step 5: Commit**

```bash
git add Tools/HangboardWorkbench/app.js Tools/HangboardWorkbench/index.html
git commit -m "feat: remove textarea editor, wire interactive path editor as primary hold editing interface"
```
