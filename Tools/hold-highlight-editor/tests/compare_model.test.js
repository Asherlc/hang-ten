const test = require("node:test");
const assert = require("node:assert/strict");

const {
  buildSummary,
  visibleLayers,
} = require("../compare-model.js");

test("buildSummary separates added modified deleted and unchanged regions by numeric id", () => {
  const baseline = [
    { id: 3, key: "deleted", contour: [[0, 0], [1, 0], [1, 1]], type: "edge", mode: "surface" },
    { id: 2, key: "same", contour: [[2, 0], [3, 0], [3, 1]], type: "edge", mode: "surface" },
    { id: 1, key: "changed", contour: [[4, 0], [5, 0], [5, 1]], type: "edge", mode: "surface" },
  ];
  const edited = [
    { id: 4, key: "added", contour: [[8, 0], [9, 0], [9, 1]], type: "jug", mode: "surface" },
    { id: 2, key: "same", contour: [[2, 0], [3, 0], [3, 1]], type: "edge", mode: "surface" },
    { id: 1, key: "changed", contour: [[4, 0], [6, 0], [5, 1]], type: "edge", mode: "surface" },
  ];
  const corrections = {
    modified: [{ id: 1, key: "changed" }],
    added: [{ id: 4, key: "added" }],
    deleted: [{ id: 3, key: "deleted" }],
  };

  assert.deepEqual(buildSummary(baseline, edited, corrections), {
    added: [4],
    modified: [1],
    deleted: [3],
    unchanged: [2],
  });
});

test("visibleLayers returns the exact layer sets for each comparison mode", () => {
  assert.deepEqual(visibleLayers("image"), ["image"]);
  assert.deepEqual(visibleLayers("automatic"), ["image", "automatic"]);
  assert.deepEqual(visibleLayers("edited"), ["image", "edited"]);
  assert.deepEqual(visibleLayers("difference"), ["image", "automatic", "edited", "difference"]);
});
