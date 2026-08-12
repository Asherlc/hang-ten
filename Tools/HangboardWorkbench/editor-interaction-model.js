(() => {
  "use strict";

  function viewportWheelAction({ ctrlKey, deltaX, deltaY }) {
    return ctrlKey
      ? { kind: "zoom", scale: Math.exp(-deltaY * 0.0012) }
      : { kind: "pan", deltaX, deltaY };
  }

  const api = Object.freeze({ viewportWheelAction });
  globalThis.HoldEditorInteractionModel = api;
  if (typeof module !== "undefined") module.exports = api;
})();
