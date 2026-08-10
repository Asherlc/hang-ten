(function exposeWorkbenchSuiteModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldWorkbenchSuiteModel = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const TOOL_IDS = Object.freeze(["onboard", "inspect", "promote", "validate"]);
  const DEFAULT_TOOL = "onboard";

  function assertTool(toolId) {
    if (!TOOL_IDS.includes(toolId)) throw new RangeError(`Unknown workbench tool: ${String(toolId)}`);
    return toolId;
  }

  function activeRevisionFor(board) {
    return typeof board?.revisionId === "string" && board.revisionId ? board.revisionId : null;
  }

  function resultForActiveRevision(result, activeRevision) {
    return typeof activeRevision === "string" && activeRevision && result?.revisionId === activeRevision
      ? result
      : null;
  }

  function hasPromotionConflict(promotion) {
    return Array.isArray(promotion?.issues) && promotion.issues.length > 0;
  }

  function readinessState({ board = null, promotion = null, validation = null } = {}) {
    if (!board || board.state !== "complete") {
      return { status: "incomplete", label: "Incomplete", nextTool: "onboard" };
    }
    if (board.staleFromStage != null || validation?.overallStatus === "stale") {
      return { status: "stale", label: "Stale", nextTool: "onboard" };
    }
    if (hasPromotionConflict(promotion) || validation?.overallStatus === "failed") {
      return { status: "conflict", label: "Conflict", nextTool: "promote" };
    }
    if (promotion?.saved === true) {
      return { status: "saved", label: "Saved", nextTool: "validate" };
    }
    return { status: "ready", label: "Ready", nextTool: "promote" };
  }

  function createSuiteState({ board = null, activeTool = DEFAULT_TOOL, promotion = null, validation = null } = {}) {
    const activeRevision = activeRevisionFor(board);
    const currentPromotion = resultForActiveRevision(promotion, activeRevision);
    const currentValidation = resultForActiveRevision(validation, activeRevision);
    return Object.freeze({
      activeTool: assertTool(activeTool),
      activeBoard: board,
      activeRevision,
      readiness: readinessState({ board, promotion: currentPromotion, validation: currentValidation }),
      promotion: currentPromotion,
      validation: currentValidation,
    });
  }

  function selectTool(state, toolId) {
    const nextTool = assertTool(toolId);
    return Object.freeze({ ...state, activeTool: nextTool });
  }

  function replaceActiveBoard(state, board) {
    const activeRevision = activeRevisionFor(board);
    const revisionChanged = state.activeRevision !== activeRevision;
    const promotion = revisionChanged ? null : state.promotion;
    const validation = revisionChanged ? null : state.validation;
    return Object.freeze({
      ...state,
      activeBoard: board,
      activeRevision,
      promotion,
      validation,
      readiness: readinessState({ board, promotion, validation }),
    });
  }

  function withSuiteResults(state, { promotion = state.promotion, validation = state.validation } = {}) {
    const activeRevision = state.activeRevision;
    const currentPromotion = resultForActiveRevision(promotion, activeRevision);
    const currentValidation = resultForActiveRevision(validation, activeRevision);
    return Object.freeze({
      ...state,
      promotion: currentPromotion,
      validation: currentValidation,
      readiness: readinessState({
        board: state.activeBoard,
        promotion: currentPromotion,
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
