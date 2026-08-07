(function exposeWorkbenchModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldWorkbenchModel = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const STAGE_COUNT = 7;

  function timelineFor(view = {}) {
    const completed = view.state === "complete";
    const currentStage = normalizeStage(view.stage, completed ? STAGE_COUNT : 0);
    const staleFromStage = Number.isInteger(view.staleFromStage) ? view.staleFromStage : null;

    return Array.from({ length: STAGE_COUNT }, (_, stage) => {
      let state = "upcoming";
      if (stage < currentStage || (completed && stage === currentStage)) state = "complete";
      else if (stage === currentStage) state = "current";
      if (state === "complete" && staleFromStage !== null && stage >= staleFromStage) state = "stale";
      return { stage, state };
    });
  }

  // An unchanged generated checkpoint is approvable. Drafts only block approval
  // when they explicitly report invalidity, an active save, or validation errors.
  function canApprove(view, draft) {
    if (view?.state !== "awaiting_review") return false;
    if (draft == null) return true;
    return draft.valid !== false && draft.saving !== true && !(Array.isArray(draft.errors) && draft.errors.length > 0);
  }

  function normalizeStage(value, fallback) {
    if (!Number.isInteger(value)) return fallback;
    return Math.max(0, Math.min(STAGE_COUNT, value));
  }

  function openingSections(libraryBoards = [], runtimeBoards = []) {
    const byLabelThenId = (labelKey, idKey) => (left, right) => {
      const labelOrder = String(left?.[labelKey] || "").localeCompare(
        String(right?.[labelKey] || ""),
        undefined,
        { sensitivity: "base" },
      );
      if (labelOrder) return labelOrder;
      return String(left?.[idKey] || "").localeCompare(String(right?.[idKey] || ""));
    };
    const library = Array.isArray(libraryBoards) ? [...libraryBoards] : [];
    const runtime = Array.isArray(runtimeBoards) ? [...runtimeBoards] : [];
    const currentVersions = new Map(library.map((board) => [board?.boardId, board?.currentVersionId]));
    const inProgress = runtime.filter((board) => !(
      board?.saved === true
      && board.repositoryBoardId
      && board.repositoryVersionId
      && currentVersions.get(board.repositoryBoardId) === board.repositoryVersionId
    ));
    return {
      library: library.sort(byLabelThenId("displayName", "boardId")),
      inProgress: inProgress.sort(byLabelThenId("productName", "boardId")),
    };
  }

  return { timelineFor, canApprove, openingSections };
}));
