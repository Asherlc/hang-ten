const test = require("node:test");
const assert = require("node:assert/strict");

const { createSuiteState, selectTool } = require("../workbench-suite-model.js");
const { createToolSuiteController } = require("../workbench-suite-controller.js");

const board = Object.freeze({
  boardId: "board-7",
  revisionId: "revision-1",
  productName: "Workbench Board",
  state: "complete",
  stage: 4,
});

test("suite controller routes tools and re-renders without reloading the board", () => {
  const rendered = [];
  const controller = createToolSuiteController({
    selectTool,
    async loadBoard() { throw new Error("tool selection must not load a board"); },
    render(state) { rendered.push(state); },
    initialState: createSuiteState({ board, activeTool: "onboard" }),
  });

  const state = controller.selectTool("inspect");

  assert.equal(state.activeTool, "inspect");
  assert.equal(state.activeBoard, board);
  assert.equal(state.activeRevision, "revision-1");
  assert.deepEqual(rendered, [state]);
});

test("suite controller retains the selected tool while a newer board revision replaces stale shared data", async () => {
  const rendered = [];
  const controller = createToolSuiteController({
    selectTool,
    async loadBoard(boardId, revisionId) {
      assert.equal(boardId, "board-7");
      assert.equal(revisionId, "revision-2");
      return { ...board, revisionId, state: "complete" };
    },
    render(state) { rendered.push(state); },
    initialState: {
      ...createSuiteState({ board, activeTool: "inspect" }),
      promotion: { previewToken: "old-preview", revisionId: "revision-1" },
      validation: { overallStatus: "passed", revisionId: "revision-1" },
    },
  });

  const state = await controller.loadBoard("board-7", "revision-2");

  assert.equal(state.activeTool, "inspect");
  assert.equal(state.activeRevision, "revision-2");
  assert.equal(state.promotion, null);
  assert.equal(state.validation, null);
  assert.deepEqual(rendered, [state]);
});

test("a stale board request cannot overwrite a newer selected board", async () => {
  const pending = new Map();
  const rendered = [];
  const controller = createToolSuiteController({
    selectTool,
    loadBoard(boardId) {
      return new Promise((resolve) => pending.set(boardId, resolve));
    },
    render(state) { rendered.push(state); },
    initialState: createSuiteState({ board, activeTool: "inspect" }),
  });

  const first = controller.loadBoard("board-older", "revision-1");
  const second = controller.loadBoard("board-newer", "revision-2");
  pending.get("board-newer")({ ...board, boardId: "board-newer", revisionId: "revision-2" });
  const current = await second;
  pending.get("board-older")({ ...board, boardId: "board-older", revisionId: "revision-1" });

  assert.equal((await first).activeBoard.boardId, "board-newer");
  assert.equal(current.activeBoard.boardId, "board-newer");
  assert.equal(rendered.length, 1);
});
