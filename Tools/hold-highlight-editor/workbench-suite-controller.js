(function exposeWorkbenchSuiteController(root, factory) {
  const api = factory(root.HoldWorkbenchSuiteModel);
  if (typeof module === "object" && module.exports) module.exports = factory(require("./workbench-suite-model.js"));
  else root.HoldWorkbenchSuiteController = api;
}(typeof globalThis === "object" ? globalThis : this, (model) => {
  "use strict";

  function createToolSuiteController({
    selectTool,
    loadBoard,
    render,
    initialState = model?.createSuiteState(),
  } = {}) {
    if (typeof selectTool !== "function") throw new TypeError("selectTool must be a function");
    if (typeof loadBoard !== "function") throw new TypeError("loadBoard must be a function");
    if (typeof render !== "function") throw new TypeError("render must be a function");
    if (!model?.replaceActiveBoard) throw new TypeError("workbench suite model is required");

    let state = initialState;
    let loadToken = 0;

    function renderCurrent() {
      render(state);
      return state;
    }

    function chooseTool(toolId) {
      state = selectTool(state, toolId);
      return renderCurrent();
    }

    async function loadActiveBoard(boardId, revisionId = null) {
      const token = ++loadToken;
      const board = await loadBoard(boardId, revisionId);
      if (token !== loadToken) return state;
      state = model.replaceActiveBoard(state, board);
      return renderCurrent();
    }

    function setBoard(board) {
      loadToken += 1;
      state = model.replaceActiveBoard(state, board);
      return renderCurrent();
    }

    return Object.freeze({
      getState: () => state,
      selectTool: chooseTool,
      loadBoard: loadActiveBoard,
      setBoard,
    });
  }

  return Object.freeze({ createToolSuiteController });
}));
