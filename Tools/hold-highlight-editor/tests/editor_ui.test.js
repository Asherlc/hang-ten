const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { contourPath } = require("../editor-model.js");
const {
  beginEdgeCurveSession,
  updateEdgeCurveSession,
  edgeCurveHistoryLabel,
  edgeCurveFeedback,
  edgeCurveInspectorState,
  shouldRenderEdgeCurveHandle,
  canStartRegionDrag,
} = require("../curve-gesture-model.js");

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

test("editor exposes curve-editing affordances", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  const css = fs.readFileSync(path.join(__dirname, "..", "styles.css"), "utf8");
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");

  assert.match(html, /Edit points/);
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

test("declares each board picker element once in the element map", () => {
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");
  const initBlock = app.match(
    /const el = Object\.fromEntries\(\[(?<list>[\s\S]*?)\]\.map\(\(id\) => \[id, document\.getElementById\(id\)\]\)\);/,
  );

  assert.ok(initBlock, "expected the element initialization list in app.js");

  const list = initBlock.groups.list;

  for (const id of ["board-picker", "board-picker-separator", "board-select"]) {
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
