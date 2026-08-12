const test = require("node:test");
const assert = require("node:assert/strict");
const { viewportWheelAction } = require("../editor-interaction-model.js");

test("normal trackpad wheel input pans by both deltas", () => {
  assert.deepEqual(
    viewportWheelAction({ ctrlKey: false, deltaX: 18, deltaY: -24 }),
    { kind: "pan", deltaX: 18, deltaY: -24 },
  );
});

test("ctrl wheel input preserves exponential pinch zoom semantics", () => {
  const action = viewportWheelAction({ ctrlKey: true, deltaX: 18, deltaY: 120 });

  assert.equal(action.kind, "zoom");
  assert.equal(action.scale, Math.exp(-120 * 0.0012));
});
