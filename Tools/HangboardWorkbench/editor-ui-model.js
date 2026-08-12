(() => {
  "use strict";

  function advancedToolVisibility({
    region = null,
    editorMode = "contour",
    editable = false,
    hasImagePixels = false,
  } = {}) {
    const selected = Boolean(region);
    const editableSelection = selected && editable;
    const contourSelection = editableSelection && editorMode !== "vector";
    return Object.freeze({
      outline: contourSelection,
      transform: contourSelection,
      assists: contourSelection,
      details: editableSelection,
      edgeSnap: contourSelection && hasImagePixels,
    });
  }

  function formatFocusedEditorError(message, fallback = "Could not complete this editor action") {
    const source = typeof message === "string" ? message.trim() : "";
    if (!source) return fallback;
    return source
      .replace(/\bStage[\s_-]*[23]\s+regions?\s+(\d+)\b/gi, (_match, regionId) => `Hold ${regionId}`)
      .replace(/\bStage[\s_-]*2\b/gi, "Detected hold outlines")
      .replace(/\bStage[\s_-]*3\b/gi, "Editable hold outlines")
      .replace(/\bStage[\s_-]*\d+\b/gi, "Board data")
      .replace(/\bstages\b/gi, "editing steps")
      .replace(/\bstage\b/gi, "editing step")
      .replace(/\bcheckpointToken\b/gi, "boardVersionToken")
      .replace(/\bcheckpoints\b/gi, "saved board versions")
      .replace(/\bcheckpoint\b/gi, "saved board version")
      .replace(/\bpromotions\b/gi, "repository updates")
      .replace(/\bpromotion\b/gi, "repository update")
      .replace(/\bpromoting\b/gi, "updating the repository")
      .replace(/\bpromoted\b/gi, "updated in the repository")
      .replace(/\bpromotes\b/gi, "updates the repository")
      .replace(/\bpromote\b/gi, "update the repository")
      .replace(/\bapprovals\b/gi, "outline saves")
      .replace(/\bapproval\b/gi, "outline save")
      .replace(/\bapproving\b/gi, "saving outlines")
      .replace(/\bapproved\b/gi, "saved")
      .replace(/\bapproves\b/gi, "saves")
      .replace(/\bapprove\b/gi, "save")
      .replace(/\bvalidations\b/gi, "outline checks")
      .replace(/\bvalidation\b/gi, "outline check")
      .replace(/\bvalidating\b/gi, "checking outlines")
      .replace(/\bvalidated\b/gi, "checked")
      .replace(/\bvalidates\b/gi, "checks")
      .replace(/\bvalidate\b/gi, "check")
      .replace(/\bregions\b/gi, "holds")
      .replace(/\bregion\b/gi, "hold")
      .replace(/\bcontours\b/gi, "outlines")
      .replace(/\bcontour\b/gi, "outline");
  }

  const api = Object.freeze({ advancedToolVisibility, formatFocusedEditorError });
  globalThis.HoldEditorUIModel = api;
  if (typeof module !== "undefined") module.exports = api;
})();
