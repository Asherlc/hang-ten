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

test("suite state contains only onboarding, inspection, and validation tools", () => {
  const state = createSuiteState({ board: completeBoard, activeTool: "inspect" });

  assert.deepEqual(TOOL_IDS, ["onboard", "inspect", "validate"]);
  assert.equal(state.activeTool, "inspect");
  assert.equal(state.activeBoard, completeBoard);
  assert.equal(state.activeRevision, "revision-1");
  assert.equal(state.readiness.label, "Ready");
  assert.equal(state.validation, null);
});

test("tool selection preserves the active board and revision", () => {
  const initial = createSuiteState({ board: completeBoard, activeTool: "inspect" });
  const next = selectTool(initial, "validate");

  assert.equal(next.activeTool, "validate");
  assert.equal(next.activeBoard, completeBoard);
  assert.equal(next.activeRevision, "revision-1");
});

test("removed and unknown suite tools are rejected", () => {
  const state = createSuiteState({ board: completeBoard });
  assert.throws(() => selectTool(state, "promote"), /unknown workbench tool/i);
  assert.throws(() => selectTool(state, "batch-promote"), /unknown workbench tool/i);
});

test("a revision or board change clears stale validation state", () => {
  const initial = withSuiteResults(createSuiteState({ board: completeBoard }), {
    validation: {
      boardId: completeBoard.boardId,
      revisionId: "revision-1",
      overallStatus: "passed",
    },
  });

  assert.equal(
    replaceActiveBoard(initial, { ...completeBoard, revisionId: "revision-2" }).validation,
    null,
  );
  assert.equal(
    replaceActiveBoard(initial, { ...completeBoard, boardId: "other.board" }).validation,
    null,
  );
});

test("suite validation results require the active board and revision", () => {
  const state = createSuiteState({ board: completeBoard });

  assert.equal(
    withSuiteResults(state, { validation: { overallStatus: "passed" } }).validation,
    null,
  );
  assert.equal(
    withSuiteResults(state, {
      validation: {
        boardId: "other.board",
        revisionId: "revision-1",
        overallStatus: "passed",
      },
    }).validation,
    null,
  );
});

test("readiness directs incomplete, stale, failed, and validated revisions", () => {
  assert.deepEqual(
    readinessState({ board: { ...completeBoard, state: "awaiting_review" } }),
    { status: "incomplete", label: "Incomplete", nextTool: "onboard" },
  );
  assert.deepEqual(
    readinessState({ board: { ...completeBoard, staleFromStage: 3 } }),
    { status: "stale", label: "Stale", nextTool: "onboard" },
  );
  assert.deepEqual(
    readinessState({ board: completeBoard }),
    { status: "ready", label: "Ready", nextTool: "validate" },
  );
  assert.deepEqual(
    readinessState({ board: completeBoard, validation: { overallStatus: "failed" } }),
    { status: "conflict", label: "Conflict", nextTool: "validate" },
  );
  assert.deepEqual(
    readinessState({ board: completeBoard, validation: { overallStatus: "passed" } }),
    { status: "ready", label: "Ready", nextTool: "inspect" },
  );
});
