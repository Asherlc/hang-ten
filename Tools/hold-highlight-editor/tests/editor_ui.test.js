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

test("edge-curve handles avoid short projected edges while remaining available on longer edges", () => {
  assert.equal(shouldRenderEdgeCurveHandle([0, 0], [8, 0], 1), false);
  assert.equal(shouldRenderEdgeCurveHandle([0, 0], [12, 0], 1), true);
  assert.equal(shouldRenderEdgeCurveHandle([0, 0], [8, 0], 2), true);
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

test("editor exposes curve-editing affordances", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  const css = fs.readFileSync(path.join(__dirname, "..", "styles.css"), "utf8");
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");

  assert.match(html, /Edit points/);
  assert.match(app, /edge-curve-handle/);
  assert.match(app, /startEdgeCurveDrag/);
  assert.match(app, /shouldRenderEdgeCurveHandle/);
  assert.match(app, /edgeCurveFeedback/);
  assert.match(css, /\.edge-curve-handle/);
  assert.match(html, /src="curve-gesture-model\.js"/);
  assert.ok(html.indexOf('src="editor-model.js"') < html.indexOf('src="curve-gesture-model.js"'));
  assert.ok(html.indexOf('src="curve-gesture-model.js"') < html.indexOf('src="app.js"'));
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
