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

  const api = Object.freeze({ advancedToolVisibility });
  globalThis.HoldEditorUIModel = api;
  if (typeof module !== "undefined") module.exports = api;
})();
