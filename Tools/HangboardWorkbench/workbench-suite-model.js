(function exposeWorkbenchSuiteModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldWorkbenchSuiteModel = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const TOOL_IDS = Object.freeze(["onboard", "inspect", "validate"]);
  const DEFAULT_TOOL = "onboard";

  function assertTool(toolId) {
    if (!TOOL_IDS.includes(toolId)) throw new RangeError(`Unknown workbench tool: ${String(toolId)}`);
    return toolId;
  }

  function activeRevisionFor(board) {
    return typeof board?.revisionId === "string" && board.revisionId ? board.revisionId : null;
  }

  function resultForActiveRevision(result, activeBoard, activeRevision) {
    return activeBoard?.boardId
      && typeof activeRevision === "string"
      && activeRevision
      && result?.boardId === activeBoard.boardId
      && result?.revisionId === activeRevision
      ? result
      : null;
  }

  function readinessState({ board = null, validation = null } = {}) {
    if (!board || board.state !== "complete") {
      return { status: "incomplete", label: "Incomplete", nextTool: "onboard" };
    }
    if (board.staleFromStage != null || validation?.overallStatus === "stale") {
      return { status: "stale", label: "Stale", nextTool: "onboard" };
    }
    if (validation?.overallStatus === "failed") {
      return { status: "conflict", label: "Conflict", nextTool: "validate" };
    }
    if (validation?.overallStatus === "passed") {
      return { status: "ready", label: "Ready", nextTool: "inspect" };
    }
    return { status: "ready", label: "Ready", nextTool: "validate" };
  }

  function createSuiteState({ board = null, activeTool = DEFAULT_TOOL, validation = null } = {}) {
    const activeRevision = activeRevisionFor(board);
    const currentValidation = resultForActiveRevision(validation, board, activeRevision);
    return Object.freeze({
      activeTool: assertTool(activeTool),
      activeBoard: board,
      activeRevision,
      readiness: readinessState({ board, validation: currentValidation }),
      validation: currentValidation,
    });
  }

  function selectTool(state, toolId) {
    const nextTool = assertTool(toolId);
    return Object.freeze({ ...state, activeTool: nextTool });
  }

  function replaceActiveBoard(state, board) {
    const activeRevision = activeRevisionFor(board);
    const validation = resultForActiveRevision(state.validation, board, activeRevision);
    return Object.freeze({
      ...state,
      activeBoard: board,
      activeRevision,
      validation,
      readiness: readinessState({ board, validation }),
    });
  }

  function withSuiteResults(state, { validation = state.validation } = {}) {
    const activeRevision = state.activeRevision;
    const currentValidation = resultForActiveRevision(validation, state.activeBoard, activeRevision);
    return Object.freeze({
      ...state,
      validation: currentValidation,
      readiness: readinessState({
        board: state.activeBoard,
        validation: currentValidation,
      }),
    });
  }

  return Object.freeze({
    TOOL_IDS,
    createSuiteState,
    selectTool,
    replaceActiveBoard,
    readinessState,
    withSuiteResults,
  });
}));
