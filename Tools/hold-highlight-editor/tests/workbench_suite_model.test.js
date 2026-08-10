const test = require("node:test");
const assert = require("node:assert/strict");

const {
  TOOL_IDS,
  createSuiteState,
  selectTool,
  replaceActiveBoard,
  readinessState,
  withSuiteResults,
} = require("../workbench-suite-model.js");

const completeBoard = Object.freeze({
  boardId: "metolius.compact-ii",
  revisionId: "revision-1",
  productName: "Compact II",
  state: "complete",
  stage: 4,
});

test("suite state begins on the requested tool with one active board revision", () => {
  const state = createSuiteState({ board: completeBoard, activeTool: "inspect" });

  assert.deepEqual(TOOL_IDS, ["onboard", "inspect", "promote", "validate"]);
  assert.equal(state.activeTool, "inspect");
  assert.equal(state.activeBoard, completeBoard);
  assert.equal(state.activeRevision, "revision-1");
  assert.equal(state.readiness.label, "Ready");
  assert.equal(state.promotion, null);
  assert.equal(state.validation, null);
});

test("tool selection preserves the active board and revision", () => {
  const initial = createSuiteState({ board: completeBoard, activeTool: "inspect" });
  const next = selectTool(initial, "promote");

  assert.equal(next.activeTool, "promote");
  assert.equal(next.activeBoard, completeBoard);
  assert.equal(next.activeRevision, "revision-1");
});

test("unknown suite tools are rejected", () => {
  const state = createSuiteState({ board: completeBoard });
  assert.throws(() => selectTool(state, "batch-promote"), /unknown workbench tool/i);
});

test("a revision change clears stale promotion and validation state", () => {
  const initial = {
    ...createSuiteState({ board: completeBoard }),
    promotion: { previewToken: "preview-1", revisionId: "revision-1" },
    validation: { overallStatus: "passed", revisionId: "revision-1" },
  };
  const updated = replaceActiveBoard(initial, { ...completeBoard, revisionId: "revision-2" });

  assert.equal(updated.activeRevision, "revision-2");
  assert.equal(updated.promotion, null);
  assert.equal(updated.validation, null);
});

test("suite results require an explicit matching revision", () => {
  const state = createSuiteState({ board: completeBoard });

  const updated = withSuiteResults(state, {
    promotion: { boardId: "metolius.compact-ii", previewToken: "preview-1", revisionId: "revision-1" },
    validation: { overallStatus: "passed" },
  });

  assert.deepEqual(updated.promotion, {
    boardId: "metolius.compact-ii",
    previewToken: "preview-1",
    revisionId: "revision-1",
  });
  assert.equal(updated.validation, null);
  assert.equal(
    createSuiteState({ promotion: { previewToken: "unbound", revisionId: null } }).promotion,
    null,
  );
});

test("suite results require the active board as well as the active revision", () => {
  const state = createSuiteState({ board: completeBoard });
  const updated = withSuiteResults(state, {
    promotion: { boardId: "other.board", previewToken: "preview-1", revisionId: "revision-1" },
    validation: { boardId: "other.board", overallStatus: "passed", revisionId: "revision-1" },
  });

  assert.equal(updated.promotion, null);
  assert.equal(updated.validation, null);
});

test("readiness exposes stable labels for incomplete, stale, conflict, saved, and ready boards", () => {
  assert.deepEqual(
    readinessState({ board: { ...completeBoard, state: "awaiting_review" } }),
    { status: "incomplete", label: "Incomplete", nextTool: "onboard" },
  );
  assert.deepEqual(
    readinessState({ board: { ...completeBoard, staleFromStage: 3 } }),
    { status: "stale", label: "Stale", nextTool: "onboard" },
  );
  assert.deepEqual(
    readinessState({ board: completeBoard, promotion: { issues: [{ code: "target_changed" }] } }),
    { status: "conflict", label: "Conflict", nextTool: "promote" },
  );
  assert.deepEqual(
    readinessState({ board: completeBoard, promotion: { saved: true } }),
    { status: "saved", label: "Saved", nextTool: "validate" },
  );
  assert.deepEqual(
    readinessState({ board: completeBoard, validation: { overallStatus: "passed" } }),
    { status: "ready", label: "Ready", nextTool: "promote" },
  );
});
