const test = require("node:test");
const assert = require("node:assert/strict");

const { timelineFor, canApprove } = require("../workbench-model.js");

test("timeline marks current, complete, upcoming, and stale stages", () => {
  const rows = timelineFor({ stage: 3, state: "awaiting_review", staleFromStage: 2 });
  assert.deepEqual(rows.map((row) => row.state), ["complete", "complete", "stale", "current", "upcoming", "upcoming", "upcoming"]);
});

test("timeline completes the final stage after a completed workflow", () => {
  const rows = timelineFor({ stage: 6, state: "complete" });
  assert.deepEqual(rows.map((row) => row.state), ["complete", "complete", "complete", "complete", "complete", "complete", "complete"]);
});

test("canApprove permits an unchanged generated checkpoint and rejects invalid drafts", () => {
  assert.equal(canApprove({ state: "awaiting_review" }), true);
  assert.equal(canApprove({ state: "awaiting_review" }, { valid: false }), false);
  assert.equal(canApprove({ state: "awaiting_review" }, { saving: true }), false);
  assert.equal(canApprove({ state: "awaiting_review" }, { errors: ["missing contour"] }), false);
  assert.equal(canApprove({ state: "processing" }, { valid: true }), false);
});
