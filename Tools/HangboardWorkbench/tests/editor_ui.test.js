const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
  contourPath,
  removeEdgeCurvesForVertex,
  shiftCornerTreatmentsForDeletion,
} = require("../editor-model.js");
const {
  beginEdgeCurveSession,
  updateEdgeCurveSession,
  edgeCurveHistoryLabel,
  edgeCurveFeedback,
  edgeCurveInspectorState,
  shouldRenderEdgeCurveHandle,
  canStartRegionDrag,
} = require("../curve-gesture-model.js");

test("the inspector keeps direct correction controls visible while Advanced tools are closed", () => {
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");

  assert.match(app, /advancedToolsOpen: false/);
  assert.match(app, /function setAdvancedToolsOpen\(open\)/);
  assert.match(app, /advancedToolVisibility\(\{[\s\S]*region,[\s\S]*editorMode: state\.editorMode/);
  assert.match(app, /advanced-tools"\]\.classList\.toggle\("hidden", !state\.advancedToolsOpen \|\| !region\)/);
});

test("E toggles Advanced tools outside text fields", () => {
  const keydown = app.slice(
    app.indexOf('window.addEventListener("keydown"'),
    app.indexOf('window.addEventListener("keyup"'),
  );

  assert.match(
    keydown,
    /event\.key\.toLowerCase\(\) === "e"[\s\S]*setAdvancedToolsOpen\(!state\.advancedToolsOpen\)/,
  );
});

test("starting an edge session records its pointer and edge without mutating curves", () => {
  assert.equal(typeof beginEdgeCurveSession, "function");
  const edgeCurves = { 0: { kind: "quadratic", control: [5, -4] } };

  const session = beginEdgeCurveSession({ pointerId: 17, index: 0, edgeCurves, pointCount: 3 });

  assert.deepEqual(session, {
    pointerId: 17,
    index: 0,
    originalEdgeCurves: { 0: { kind: "quadratic", control: [5, -4] } },
    pointCount: 3,
    changed: false,
  });
  assert.notEqual(session.originalEdgeCurves, edgeCurves);
  assert.notEqual(session.originalEdgeCurves[0], edgeCurves[0]);
  assert.deepEqual(edgeCurves, { 0: { kind: "quadratic", control: [5, -4] } });
});

test("updating an edge session changes only its selected control", () => {
  assert.equal(typeof updateEdgeCurveSession, "function");
  const edgeCurves = {
    0: { kind: "quadratic", control: [5, -4] },
    1: { kind: "quadratic", control: [11, 5] },
  };
  const session = beginEdgeCurveSession({ pointerId: 17, index: 1, edgeCurves, pointCount: 3 });

  const result = updateEdgeCurveSession(session, edgeCurves, [12, 6]);

  assert.deepEqual(result, {
    edgeCurves: {
      0: { kind: "quadratic", control: [5, -4] },
      1: { kind: "quadratic", control: [12, 6] },
    },
    changed: true,
  });
  assert.deepEqual(edgeCurves, {
    0: { kind: "quadratic", control: [5, -4] },
    1: { kind: "quadratic", control: [11, 5] },
  });
  assert.equal(session.changed, false);
});

test("finishing an edge session emits at most one history label", () => {
  assert.equal(typeof edgeCurveHistoryLabel, "function");
  const unchanged = beginEdgeCurveSession({ pointerId: 17, index: 0, edgeCurves: {}, pointCount: 3 });
  const changed = { ...unchanged, changed: true };
  const labels = [];
  let activeSession = changed;
  const finish = () => {
    const label = edgeCurveHistoryLabel(activeSession);
    if (label) labels.push(label);
    activeSession = null;
  };

  assert.equal(edgeCurveHistoryLabel(unchanged), null);
  finish();
  finish();

  assert.deepEqual(labels, ["Moved edge curve"]);
});

test("region dragging requires left-button object input outside drawing and space-pan modes", () => {
  assert.equal(typeof canStartRegionDrag, "function");
  assert.equal(canStartRegionDrag({ drawing: false, spacePressed: false, button: 0 }), true);
  assert.equal(canStartRegionDrag({ drawing: true, spacePressed: false, button: 0 }), false);
  assert.equal(canStartRegionDrag({ drawing: false, spacePressed: true, button: 0 }), false);
  assert.equal(canStartRegionDrag({ drawing: false, spacePressed: false, button: 1 }), false);
  assert.equal(canStartRegionDrag({ drawing: false, spacePressed: false, button: 2 }), false);
});

test("edge sessions reject invalid pointer, edge, and control inputs", () => {
  assert.throws(
    () => beginEdgeCurveSession({ pointerId: NaN, index: 0, edgeCurves: {}, pointCount: 3 }),
    /pointer/i,
  );
  assert.throws(
    () => beginEdgeCurveSession({ pointerId: 17, index: 3, edgeCurves: {}, pointCount: 3 }),
    { message: "Invalid edge curve index: 3." },
  );
  const session = beginEdgeCurveSession({ pointerId: 17, index: 0, edgeCurves: {}, pointCount: 3 });
  assert.throws(() => updateEdgeCurveSession(session, {}, [Infinity, 4]), /finite/i);
});

test("edge-curve handles avoid every nearby vertex while preserving clear controls", () => {
  assert.equal(shouldRenderEdgeCurveHandle({
    start: [0, 0],
    end: [12, 0],
    control: [6, 0],
    vertices: [[0, 0], [12, 0]],
    zoom: 1,
  }), false);
  assert.equal(shouldRenderEdgeCurveHandle({
    start: [0, 0],
    end: [12, 0],
    control: [6, -12],
    vertices: [[0, 0], [12, 0]],
    zoom: 1,
  }), true);
  assert.equal(shouldRenderEdgeCurveHandle({
    start: [0, 0],
    end: [30, 0],
    control: [15, 0],
    vertices: [[0, 0], [30, 0], [15, 4]],
    zoom: 1,
  }), false);
  assert.equal(shouldRenderEdgeCurveHandle({
    start: [0, 0],
    end: [30, 0],
    control: [15, 0],
    vertices: [[0, 0], [30, 0]],
    zoom: 1,
  }), true);
});

test("smooth edge curves explain their rendering override", () => {
  const curvedSmoothRegion = {
    metadata: { pathStyle: "smooth", edgeCurves: { 0: { kind: "quadratic", control: [5, -4] } } },
  };

  assert.equal(
    edgeCurveFeedback(curvedSmoothRegion),
    "Per-edge curves override smooth rendering; uncurved edges are straight and tension is ignored.",
  );
  assert.equal(edgeCurveFeedback({ metadata: { pathStyle: "smooth" } }), null);
  assert.equal(edgeCurveFeedback({ metadata: { pathStyle: "straight", edgeCurves: {} } }), null);
});

test("inspector disables tension only when per-edge curves override smooth mode", () => {
  assert.deepEqual(
    edgeCurveInspectorState({
      metadata: { pathStyle: "smooth", edgeCurves: { 0: { kind: "quadratic", control: [5, -4] } } },
    }),
    {
      visible: true,
      overridden: true,
      feedback: "Per-edge curves override smooth rendering; uncurved edges are straight and tension is ignored.",
    },
  );
  assert.deepEqual(
    edgeCurveInspectorState({ metadata: { pathStyle: "smooth", curveTension: 1 } }),
    { visible: true, overridden: false, feedback: null },
  );
  assert.deepEqual(
    edgeCurveInspectorState({ metadata: { pathStyle: "straight", edgeCurves: { 0: {} } } }),
    { visible: false, overridden: false, feedback: null },
  );
});

test("renderToolState keeps overridden curve tension disabled after a full render", () => {
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");
  const renderToolStateBlock = app.match(/function renderToolState\(\) \{[\s\S]*?\n  \}/);

  assert.ok(renderToolStateBlock, "expected renderToolState() to be present in app.js");
  assert.match(
    renderToolStateBlock[0],
    /edgeCurveInspectorState\(selectedRegion\(\)\)\.overridden/,
    "renderToolState() must account for edge-curve inspector overrides",
  );
  assert.match(
    renderToolStateBlock[0],
    /const curveTensionOverridden = Boolean\(\s*selectedRegion\(\) && edgeCurveInspectorState\(selectedRegion\(\)\)\.overridden,\s*\)/,
    "renderToolState() must derive curveTensionOverridden from the selected region override state",
  );
  assert.match(
    renderToolStateBlock[0],
    /curve-tension-slider\"\]\.disabled = [^;\n]*curveTensionOverridden/,
    "renderToolState() must keep the curve-tension slider disabled when the selected region is overridden",
  );
});

test("editor exposes curve-editing affordances", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  const css = fs.readFileSync(path.join(__dirname, "..", "styles.css"), "utf8");
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");

  assert.doesNotMatch(html, /Edit points/);
  assert.match(app, /edge-curve-handle/);
  assert.match(app, /startEdgeCurveDrag/);
  assert.match(app, /edgeCurveInspectorState/);
  assert.match(app, /curve-tension-slider\"\]\.disabled = tensionState\.overridden/);
  assert.match(app, /shouldRenderEdgeCurveHandle/);
  assert.match(app, /edgeCurveFeedback/);
  assert.match(css, /\.edge-curve-handle/);
  assert.match(html, /id="curve-tension-feedback"/);
  assert.match(html, /src="editor-model\.js"/);
  assert.match(html, /src="curve-gesture-model\.js"/);
  assert.ok(html.indexOf('src="editor-model.js"') < html.indexOf('src="curve-gesture-model.js"'));
  assert.ok(html.indexOf('src="curve-gesture-model.js"') < html.indexOf('src="app.js"'));
  assert.match(app, /return \[clamp\(transformed\.x, 0, state\.canvas\.width\), clamp\(transformed\.y, 0, state\.canvas\.height\)\];/);
});

function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `expected ${name}() to be present`);
  const bodyStart = source.indexOf("{", start);
  let depth = 0;
  for (let index = bodyStart; index < source.length; index += 1) {
    if (source[index] === "{") depth += 1;
    if (source[index] === "}") depth -= 1;
    if (depth === 0) return source.slice(start, index + 1);
  }
  assert.fail(`could not extract ${name}()`);
}

test("freeform holds expose independently draggable vertices instead of object resizing", () => {
  assert.match(app, /function isFreeformRegion\(region\)/);
  assert.match(app, /if \(isFreeformRegion\(region\)\) renderFreeformVertexHandles\(group, region\);/);
  assert.match(app, /if \(!isFreeformRegion\(region\)\) renderObjectControls\(group, region\);/);
  assert.match(app, /function clearSelection\(\) \{[\s\S]*selectRegion\(null\);/);
});

test("deleting a selected freeform vertex preserves the three-point minimum", () => {
  assert.match(app, /function deleteSelectedFreeformVertex\(\)/);
  const state = {
    selectedId: 7,
    selectedCornerIndex: 2,
    regions: [{
      id: 7,
      contour: [[1, 1], [9, 1], [9, 9], [1, 9]],
      metadata: {
        shapeKind: "freeform",
        edgeCurves: Object.fromEntries([0, 1, 2, 3].map((index) => [
          index,
          { kind: "quadratic", control: [index, index + 0.5] },
        ])),
        cornerTreatments: {
          0: { treatment: "sharp", amount: 1 },
          2: { treatment: "rounded", amount: 2 },
          3: { treatment: "sharp", amount: 3 },
        },
      },
    }],
  };
  const history = [];
  let renders = 0;
  let editable = true;
  const context = {
    state,
    selectedRegion: () => state.regions.find((region) => region.id === state.selectedId) || null,
    canEditGeometry: () => editable,
    removeEdgeCurvesForVertex,
    shiftCornerTreatmentsForDeletion,
    commitHistory: (label) => history.push(label),
    render: () => { renders += 1; },
  };
  vm.runInNewContext(`${extractFunction(app, "isFreeformRegion")}\n${extractFunction(app, "deleteSelectedFreeformVertex")}`, context);

  assert.equal(context.deleteSelectedFreeformVertex(), true);
  assert.deepEqual(state.regions[0].contour, [[1, 1], [9, 1], [1, 9]]);
  assert.deepEqual(state.regions[0].metadata.edgeCurves, {
    0: { kind: "quadratic", control: [0, 0.5] },
    2: { kind: "quadratic", control: [3, 3.5] },
  });
  assert.deepEqual(state.regions[0].metadata.cornerTreatments, {
    0: { treatment: "sharp", amount: 1 },
    2: { treatment: "sharp", amount: 3 },
  });
  assert.equal(state.selectedCornerIndex, null);
  assert.deepEqual(history, ["Deleted control point"]);
  assert.equal(renders, 1);

  const before = JSON.stringify(state.regions);
  state.selectedCornerIndex = 0;
  assert.equal(context.deleteSelectedFreeformVertex(), false);
  assert.equal(JSON.stringify(state.regions), before);

  state.regions[0].metadata.shapeKind = "rectangle";
  state.regions[0].contour.push([1, 1]);
  assert.equal(context.deleteSelectedFreeformVertex(), false);
  state.regions[0].metadata.shapeKind = "freeform";
  const frozenContour = JSON.stringify(state.regions[0].contour);
  editable = false;
  assert.equal(context.deleteSelectedFreeformVertex(), false);
  assert.equal(JSON.stringify(state.regions[0].contour), frozenContour);
  state.selectedId = null;
  assert.equal(context.deleteSelectedFreeformVertex(), false);
});

test("restoring a cancelled pointer edit targets its original hold and preserves the exact original shape", () => {
  const state = {
    selectedId: 8,
    regions: [
      {
        id: 7,
        contour: [[3, 3], [8, 3], [8, 8], [3, 8]],
        anchor: [6, 6],
        metadata: {
          edgeCurves: { 0: { kind: "quadratic", control: [4, 1] } },
          rotation: 0.75,
          bend: 14,
          cornerTreatments: { 1: { treatment: "rounded", amount: 8 } },
        },
      },
      { id: 8, contour: [[20, 20], [30, 20], [30, 30]], metadata: { rotation: 9 } },
    ],
  };
  const originalRegion = {
    id: 7,
    key: "grip-007",
    contour: [[1, 1], [9, 1], [9, 9], [1, 9]],
    metadata: { pathStyle: "straight" },
  };
  const session = { regionId: 7, originalRegion };
  const context = { state, clone: (value) => JSON.parse(JSON.stringify(value)) };

  vm.runInNewContext(extractFunction(app, "restorePointerGeometry"), context);

  assert.equal(context.restorePointerGeometry(session), true);
  assert.deepEqual(state.regions[0], originalRegion);
  assert.deepEqual(state.regions[1], { id: 8, contour: [[20, 20], [30, 20], [30, 30]], metadata: { rotation: 9 } });
  assert.equal(Object.hasOwn(state.regions[0], "anchor"), false);
  assert.equal(Object.hasOwn(state.regions[0].metadata, "edgeCurves"), false);
  assert.equal(Object.hasOwn(state.regions[0].metadata, "rotation"), false);
  assert.equal(Object.hasOwn(state.regions[0].metadata, "bend"), false);
  assert.equal(Object.hasOwn(state.regions[0].metadata, "cornerTreatments"), false);
});

test("pointer session snapshots retain the starting hold identity and exact region", () => {
  const context = { clone: (value) => JSON.parse(JSON.stringify(value)) };
  vm.runInNewContext(extractFunction(app, "capturePointerRegionSnapshot"), context);
  const region = { id: 7, contour: [[1, 1], [2, 2], [3, 3]], metadata: {} };

  const session = context.capturePointerRegionSnapshot(region, { pointerId: 17, changed: false });
  region.contour[0][0] = 99;

  assert.deepEqual(JSON.parse(JSON.stringify(session)), {
    pointerId: 17,
    changed: false,
    regionId: 7,
    originalRegion: { id: 7, contour: [[1, 1], [2, 2], [3, 3]], metadata: {} },
  });
});

test("Escape deselects an idle hold but cancels drawing first", () => {
  const handlerStart = app.indexOf('window.addEventListener("keydown", (event) => {');
  const handlerEnd = app.indexOf('window.addEventListener("keyup"', handlerStart);
  assert.notEqual(handlerStart, -1);
  assert.notEqual(handlerEnd, -1);
  const listeners = {};
  const state = {
    drawing: false,
    spacePressed: false,
    mirrorOntoSourceId: null,
    inspectorDrawerOpen: false,
    selectedId: 4,
    panSession: null,
    primitiveSession: null,
    dragSession: null,
    handleSession: null,
    edgeSession: null,
    transformSession: null,
  };
  let cleared = 0;
  let canceled = 0;
  let pointerCancellation = null;
  const context = {
    document: { activeElement: { tagName: "DIV" } },
    state,
    window: { addEventListener: (name, callback) => { listeners[name] = callback; } },
    trapInspectorDrawerFocus: () => {},
    clearSelection: () => { cleared += 1; },
    cancelDraw: () => { canceled += 1; },
    cancelPointerSessions: (options) => { pointerCancellation = options; },
    closeInspectorDrawer: () => {},
    deleteSelectedFreeformVertex: () => false,
    deleteSelected: () => {},
    finishDraw: () => {},
    redo: () => {},
    undo: () => {},
    navigateRegion: () => {},
    mirrorSelectedCopy: () => {},
    toggleEdgeSnapping: () => {},
    renderToolState: () => {},
    render: () => {},
    setStatus: () => {},
  };
  vm.runInNewContext(app.slice(handlerStart, handlerEnd), context);
  const dispatch = (key) => {
    let prevented = false;
    listeners.keydown({
      key,
      code: key,
      preventDefault: () => { prevented = true; },
      ctrlKey: false,
      metaKey: false,
      shiftKey: false,
    });
    return prevented;
  };

  assert.equal(dispatch("Escape"), true);
  assert.equal(cleared, 1);
  assert.equal(canceled, 0);

  state.drawing = true;
  assert.equal(dispatch("Escape"), true);
  assert.equal(canceled, 1);
  assert.equal(cleared, 1);

  state.drawing = false;
  state.transformSession = { pointerId: 1 };
  assert.equal(dispatch("Escape"), true);
  assert.equal(pointerCancellation?.restore, true);
  state.transformSession = null;

  state.mirrorOntoSourceId = 9;
  assert.equal(dispatch("Escape"), true);
  assert.equal(state.mirrorOntoSourceId, null);
  assert.equal(cleared, 1);
});

test("Delete and Backspace remove a selected freeform vertex before deleting its hold", () => {
  const keydown = app.slice(
    app.indexOf('window.addEventListener("keydown"'),
    app.indexOf('window.addEventListener("keyup"'),
  );
  assert.match(
    keydown,
    /event\.key === "Delete" \|\| event\.key === "Backspace"[\s\S]*if \(!deleteSelectedFreeformVertex\(\)\) deleteSelected\(\);/,
  );
});

test("viewport wheel listener pans or cursor-anchored zooms by interaction intent", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");

  assert.match(html, /src="editor-interaction-model\.js"/);
  assert.ok(html.indexOf('src="curve-gesture-model.js"') < html.indexOf('src="editor-interaction-model.js"'));
  assert.ok(html.indexOf('src="editor-interaction-model.js"') < html.indexOf('src="app.js"'));
  assert.match(app, /addEventListener\("wheel", \(event\) => \{[\s\S]*event\.preventDefault\(\)/);
  assert.match(app, /if \(action\.kind === "zoom"\) \{[\s\S]*setZoom\(state\.zoom \* action\.scale, event\.clientX, event\.clientY\)/);
  assert.match(app, /state\.panX -= action\.deltaX;[\s\S]*state\.panY -= action\.deltaY;[\s\S]*renderTransform\(\);/);
});

test("focusing a validation hold closes Advanced tools when it changes selection", () => {
  const state = {
    selectedId: 7,
    selectedCornerIndex: 2,
    advancedToolsOpen: true,
    regions: [{ id: 7 }, { id: 8 }],
  };
  let rendered = 0;
  let focused = 0;
  let scrolled = 0;
  const context = {
    state,
    render: () => { rendered += 1; },
    el: { "canvas-viewport": { focus: () => { focused += 1; } } },
    document: { querySelector: () => ({ scrollIntoView: () => { scrolled += 1; } }) },
    requestAnimationFrame: (callback) => callback(),
  };
  vm.runInNewContext(extractFunction(app, "focusRegion"), context);

  assert.equal(context.focusRegion(8), true);
  assert.equal(state.selectedId, 8);
  assert.equal(state.selectedCornerIndex, null);
  assert.equal(state.advancedToolsOpen, false);
  assert.equal(rendered, 1);
  assert.equal(focused, 1);
  assert.equal(scrolled, 1);
});

test("finishing a new hold closes Advanced tools when it selects the new hold", () => {
  const state = {
    selectedId: 7,
    selectedCornerIndex: 2,
    advancedToolsOpen: true,
    drawing: true,
    draft: [[1, 1], [9, 1], [9, 9]],
    drawShape: "freeform",
    primitiveSession: { pointerId: 1 },
    regions: [],
  };
  const context = {
    state,
    canEditGeometry: () => true,
    allocateRegionId: () => 8,
    normalizeRegion: (region) => region,
    commitHistory: () => {},
    setStatus: () => {},
    render: () => {},
    el: { "draw-instruction": { classList: { remove: () => {} } } },
  };
  vm.runInNewContext(extractFunction(app, "finishDraw"), context);

  context.finishDraw();

  assert.equal(state.selectedId, 8);
  assert.equal(state.selectedCornerIndex, null);
  assert.equal(state.advancedToolsOpen, false);
});

test("declares each focused-editor element once in the element map", () => {
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");
  const initBlock = app.match(
    /const el = Object\.fromEntries\(\[(?<list>[\s\S]*?)\]\.map\(\(id\) => \[id, document\.getElementById\(id\)\]\)\);/,
  );

  assert.ok(initBlock, "expected the element initialization list in app.js");

  const list = initBlock.groups.list;

  for (const id of [
    "board-picker", "board-picker-separator", "board-select",
    "board-details", "board-details-name", "board-details-id", "board-details-revision", "more-actions",
    "advanced-tools-toggle", "advanced-tools", "advanced-outline-tools", "advanced-transform-tools",
    "advanced-assist-tools", "advanced-details-tools",
  ]) {
    const matches = list.match(new RegExp(`"${id.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"`, "g")) ?? [];
    assert.equal(matches.length, 1, `${id} must appear exactly once in the element initialization list`);
  }
});

test("renders exactly one region interaction mode control with its intended label and options", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  const modeControlPattern = /<select\b(?=[^>]*\bid\s*=\s*["']region-mode-select["'])[^>]*>[\s\S]*?<\/select>/gi;
  const modeControls = [...html.matchAll(modeControlPattern)];

  assert.equal(modeControls.length, 1, "region-mode-select must appear exactly once");

  const modeLabelPattern = /<label\b[^>]*>\s*Hold\s+interaction\s+mode\s*<select\b(?=[^>]*\bid\s*=\s*["']region-mode-select["'])[^>]*>[\s\S]*?<\/select>\s*<\/label>/i;
  assert.match(html, modeLabelPattern, "region-mode-select must use the Hold interaction mode label");

  const modeControl = modeControls[0][0];
  assert.match(modeControl, /<option\b[^>]*\bvalue\s*=\s*["']aperture["'][^>]*>\s*Aperture\s*<\/option>/i);
  assert.match(modeControl, /<option\b[^>]*\bvalue\s*=\s*["']surface["'][^>]*>\s*Surface\s*<\/option>/i);
});

test("region edge-curve metadata renders a quadratic contour path", () => {
  const region = {
    contour: [[0, 0], [10, 0], [10, 10]],
    metadata: {
      pathStyle: "straight",
      curveTension: 0.8,
      edgeCurves: { 0: { kind: "quadratic", control: [5, -4] } },
    },
  };

  assert.equal(
    contourPath(
      region.contour,
      region.metadata.pathStyle,
      region.metadata.curveTension,
      region.metadata.edgeCurves,
    ),
    "M 0 0 Q 5 -4 10 0 L 10 10 L 0 0 Z",
  );
});

test("live region rendering forwards edge curves into regionPath", () => {
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");
  const liveRegionPathCall = app.match(
    /const path = makeSvg\("path", \{\s*d:\s*regionPath\(\s*region\s*,\s*region\.metadata\.edgeCurves\s*\),[\s\S]*?fill:\s*colorFor\(region\)[\s\S]*?\}\);/,
  );

  assert.ok(liveRegionPathCall, "expected the live region path render call to forward region.metadata.edgeCurves");
});

const root = path.join(__dirname, "..");
const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "app.js"), "utf8");
const readme = fs.readFileSync(path.join(root, "README.md"), "utf8");
const server = fs.readFileSync(path.join(root, "server.py"), "utf8");

void app;
void readme;

test("brands the workspace as a Hold Editor", () => {
  assert.match(index, /<title>Hold Editor<\/title>/);
  assert.match(index, /<h1>Hold Editor<\/h1>/);
  assert.doesNotMatch(index, /Hold Region Editor/);
  assert.match(index, /Edit and save hold highlights/);
});

test("keeps full hold editing controls", () => {
  assert.match(index, /id="new-shape-select"/);
  assert.match(index, /id="region-type-select"/);
  assert.match(index, /value="jug"/);
  assert.match(index, /value="sloper"/);
  assert.match(index, /value="edge"/);
  assert.match(index, /value="pocket"/);
  assert.match(index, /id="add-region-button"/);
  assert.match(index, />\s*<span>＋<\/span>\s*Add highlight\s*</);
  assert.match(index, /id="delete-button"/);
});

test("keeps internal region controls while presenting hold highlights", () => {
  assert.match(index, /id="region-list"[^>]*aria-label="Hold highlights"/);
  assert.match(index, /id="new-shape-select"[^>]*aria-label="New highlight shape"/);
  assert.match(index, /id="add-region-button"[\s\S]*?Add highlight/);
  assert.match(index, /id="delete-button">Delete highlight<\/button>/);
  assert.match(index, /id="region-mode-select"/);
  assert.match(index, /id="region-key-input"/);
  assert.match(index, /Select a hold highlight to edit its exact geometry and details\./);
});

test("handles drawing Enter and Escape before the focused-control guard", () => {
  const handlerStart = app.indexOf('window.addEventListener("keydown", (event) => {');
  assert.notEqual(handlerStart, -1);
  const bodyStart = app.indexOf("{", handlerStart);
  let depth = 0;
  let bodyEnd = -1;
  for (let index = bodyStart; index < app.length; index += 1) {
    if (app[index] === "{") depth += 1;
    if (app[index] === "}") depth -= 1;
    if (depth === 0) {
      bodyEnd = index + 1;
      break;
    }
  }
  assert.notEqual(bodyEnd, -1);

  const listeners = {};
  const state = { drawing: true, spacePressed: false, mirrorOntoSourceId: null };
  let finished = 0;
  let canceled = 0;
  const context = {
    document: { activeElement: { tagName: "INPUT" } },
    finishDraw: () => { finished += 1; },
    cancelDraw: () => { canceled += 1; },
    trapInspectorDrawerFocus: () => {},
    renderToolState: () => {},
    setStatus: () => {},
    state,
    window: {
      addEventListener: (name, callback) => { listeners[name] = callback; },
    },
  };
  vm.runInNewContext(app.slice(handlerStart, bodyEnd) + ");", context);

  const dispatch = (key) => {
    let prevented = false;
    listeners.keydown({
      key,
      code: key,
      preventDefault: () => { prevented = true; },
      ctrlKey: false,
      metaKey: false,
      shiftKey: false,
    });
    return prevented;
  };

  assert.equal(dispatch("Enter"), true);
  assert.equal(finished, 1);
  assert.equal(canceled, 0);

  state.drawing = true;
  assert.equal(dispatch("Escape"), true);
  assert.equal(finished, 1);
  assert.equal(canceled, 1);
});

test("keeps the inspector available as a responsive accessible drawer", () => {
  const css = fs.readFileSync(path.join(__dirname, "..", "styles.css"), "utf8");

  assert.match(css, /@media \(max-width: 1250px\)[\s\S]*\.workspace-grid \{ grid-template-columns: 250px minmax\(0, 1fr\); \}/);
  assert.match(css, /\.inspector-panel\.drawer-open/);
  assert.doesNotMatch(css, /@media \(max-width: 980px\)[\s\S]*\.inspector-panel \{ display: none; \}/);
  assert.match(app, /function openInspectorDrawer\(\)/);
  assert.match(app, /function closeInspectorDrawer\(\{ restoreFocus = true \} = \{\}\)/);
  assert.match(app, /function trapInspectorDrawerFocus\(event\)/);
  assert.match(app, /inspector-drawer-toggle"\]\.setAttribute\("aria-expanded", "true"\)/);
  assert.match(app, /inspector-drawer-toggle"\]\.setAttribute\("aria-expanded", "false"\)/);
  assert.match(app, /function syncInspectorDrawerAccessibility\(\)/);
  assert.match(app, /const drawerIsModal = inspectorDrawerMedia\.matches && state\.inspectorDrawerOpen;/);
  assert.match(app, /panel\.setAttribute\("role", "dialog"\)/);
  assert.match(app, /panel\.setAttribute\("aria-modal", "true"\)/);
  assert.match(app, /panel\.inert = true;/);
  assert.match(app, /panel\.setAttribute\("aria-hidden", "true"\)/);
  assert.match(app, /panel\.inert = false;/);
  assert.match(app, /panel\.removeAttribute\("aria-modal"\)/);

  const keydownStart = app.indexOf('window.addEventListener("keydown", (event) => {');
  const closeDrawerStart = app.indexOf("closeInspectorDrawer", keydownStart);
  const editingTextGuard = app.indexOf("if (editingText) return;", keydownStart);
  assert.ok(closeDrawerStart > keydownStart && closeDrawerStart < editingTextGuard, "Escape must close the inspector drawer before ordinary keyboard handling");
});

test("preserves the selected primitive shape when adding a highlight", () => {
  assert.match(app, /const primitiveShapeKind = state\.drawShape === "curved-freeform" \? "freeform" : state\.drawShape/);
  assert.match(app, /shapeKind:\s*primitiveShapeKind/);
});

test("documents the direct hold-highlight workflow", () => {
  assert.match(readme, /^# Hold Editor/m);
  assert.match(readme, /choose a board.*edit.*add.*delete.*save/is);
  assert.match(readme, /hold type/i);
  assert.doesNotMatch(readme, /# Hold Region Editor/);
});

test("uses hold editor wording in server labels", () => {
  assert.match(server, /Hold Editor: http:\/\//);
  assert.doesNotMatch(server, /Hold Region Editor: http:\/\//);
});

test("marks manual file loading as a static fallback", () => {
  assert.match(index, /id="static-load-controls"/);
  assert.match(index, /id="load-image-button"/);
  assert.match(index, /id="load-regions-button"/);
});

test("switches between server-first and static fallback entry states", () => {
  assert.match(app, /function showStaticLoadControls\(visible\)/);
  assert.match(app, /static-load-controls/);
  assert.match(app, /showStaticLoadControls\(false\)/);
  assert.match(app, /showStaticLoadControls\(true\)/);
});

test("uses hold language for selection and editing status", () => {
  assert.match(app, /Hold \$\{region\.id\}/);
  assert.match(app, /Added \$\{region\.key\}/);
  assert.match(app, /Deleted \$\{region\.key\}/);
  assert.doesNotMatch(app, /Select a region to edit its shape and metadata/);
});

test("describes static save mode with hold-editor wording", () => {
  assert.match(app, /save hold highlights in this Hold Editor/i);
  assert.doesNotMatch(app, /onboarding run/);
});

test("uses hold-highlight terminology in visible editor controls", () => {
  assert.match(index, />Load highlights</);
  assert.match(index, />Export edited highlights</);
  assert.match(index, />All highlights</);
  assert.match(index, /Drop a board image and hold-highlight JSON here/);
  assert.match(index, /Why was this hold highlight changed\?/);
  assert.doesNotMatch(index, />Load regions</);
  assert.doesNotMatch(index, />All regions</);
});

test("uses hold-highlight terminology in runtime messages", () => {
  assert.match(app, /Rotated hold highlight/);
  assert.match(app, /Exported .* edited hold highlights/);
  assert.doesNotMatch(app, /"(?:Rotated|Bent|Resized|Moved|Renamed) region"/);
  assert.doesNotMatch(app, /edited regions\.`/);
});

test("prevents default draw Enter and Escape shortcuts before the focused-control guard", () => {
  const keydown = app.slice(
    app.indexOf('window.addEventListener("keydown"'),
    app.indexOf('window.addEventListener("keyup"'),
  );
  const guardIndex = keydown.indexOf("if (editingText) return;");
  const enterIndex = keydown.indexOf('event.key === "Enter" && state.drawing');
  const escapeIndex = keydown.indexOf('event.key === "Escape" && state.drawing');
  const enterBranch = keydown.slice(
    enterIndex,
    keydown.indexOf("}", enterIndex) + 1,
  );
  const escapeBranch = keydown.slice(
    escapeIndex,
    keydown.indexOf("}", escapeIndex) + 1,
  );

  assert.ok(enterIndex !== -1, "expected Enter draw handler");
  assert.ok(escapeIndex !== -1, "expected Escape draw handler");
  assert.ok(guardIndex !== -1, "expected focused-control guard");
  assert.ok(enterIndex < guardIndex, "Enter draw handler should run before the focused-control guard");
  assert.ok(escapeIndex < guardIndex, "Escape draw handler should run before the focused-control guard");
  assert.match(
    enterBranch,
    /event\.preventDefault\(\);[\s\S]*finishDraw\(\);/,
    "Enter draw handler should prevent default before finishing the draw",
  );
  assert.match(
    escapeBranch,
    /event\.preventDefault\(\);[\s\S]*cancelDraw\(\);/,
    "Escape draw handler should prevent default before canceling the draw",
  );
});

test("uses shared normalizeRegion and preserves primitive shape kinds while drawing", () => {
  assert.match(app, /normalizeRegion,/);
  assert.doesNotMatch(app, /function normalizeRegion\(/);
  assert.match(app, /const primitiveShapeKind = state\.drawShape === "curved-freeform" \? "freeform" : state\.drawShape/);
  assert.match(app, /shapeKind:\s*primitiveShapeKind/);
});

test("documents hold-highlight operations without generic region prose", () => {
  assert.match(readme, /Hold highlights can be drawn/);
  assert.match(readme, /previous or next hold highlight/);
  assert.doesNotMatch(readme, /Regions can be drawn/);
  assert.doesNotMatch(readme, /symmetric region/);
});
