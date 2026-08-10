const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { contourPath } = require("../editor-model.js");

test("editor exposes curve-editing affordances", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  const css = fs.readFileSync(path.join(__dirname, "..", "styles.css"), "utf8");
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");

  assert.match(html, /Edit points/);
  assert.match(app, /edge-curve-handle/);
  assert.match(app, /startEdgeCurveDrag/);
  assert.match(css, /\.edge-curve-handle/);
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
