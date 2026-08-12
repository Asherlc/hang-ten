const test = require("node:test");
const assert = require("node:assert/strict");

const { advancedToolVisibility } = require("../editor-ui-model.js");

test("freeform contour holds expose outline, assists, and details", () => {
  assert.deepEqual(advancedToolVisibility({
    region: { metadata: { shapeKind: "freeform" } },
    editorMode: "contour", editable: true, hasImagePixels: true,
  }), {
    outline: true, transform: true, assists: true, details: true, edgeSnap: true,
  });
});

test("primitive contour holds expose all editable contour tools", () => {
  assert.deepEqual(advancedToolVisibility({
    region: { metadata: { shapeKind: "rectangle" } },
    editorMode: "contour", editable: true, hasImagePixels: true,
  }), {
    outline: true, transform: true, assists: true, details: true, edgeSnap: true,
  });
});

test("vector and no-selection states expose no contour expert controls", () => {
  assert.deepEqual(advancedToolVisibility({
    region: null, editorMode: "contour", editable: true, hasImagePixels: true,
  }), { outline: false, transform: false, assists: false, details: false, edgeSnap: false });
  assert.deepEqual(advancedToolVisibility({
    region: { metadata: { shapeKind: "freeform" } },
    editorMode: "vector", editable: true, hasImagePixels: true,
  }), { outline: false, transform: false, assists: false, details: true, edgeSnap: false });
});
