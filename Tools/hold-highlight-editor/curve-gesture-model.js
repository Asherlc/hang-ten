(function exposeCurveGestureModel(root, factory) {
  const editorModel = typeof module === "object" && module.exports
    ? require("./editor-model.js")
    : root.HoldEditorModel;
  const api = factory(editorModel);
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldCurveGestureModel = api;
}(typeof globalThis === "object" ? globalThis : this, (editorModel) => {
  "use strict";

  const { normalizeEdgeCurves, setEdgeCurveControl } = editorModel;

  function beginEdgeCurveSession({ pointerId, index, edgeCurves, pointCount }) {
    if (!Number.isInteger(pointerId)) throw new Error("Edge curve pointer ID must be an integer.");
    const originalEdgeCurves = normalizeEdgeCurves(edgeCurves, pointCount);
    setEdgeCurveControl({}, index, [0, 0], pointCount);
    return { pointerId, index, originalEdgeCurves, pointCount, changed: false };
  }

  function updateEdgeCurveSession(session, edgeCurves, control) {
    return {
      edgeCurves: setEdgeCurveControl(edgeCurves, session.index, control, session.pointCount),
      changed: true,
    };
  }

  function edgeCurveHistoryLabel(session) {
    return session?.changed ? "Moved edge curve" : null;
  }

  function canStartRegionDrag({ drawing, spacePressed, button }) {
    return !drawing && !spacePressed && button === 0;
  }

  return {
    beginEdgeCurveSession,
    updateEdgeCurveSession,
    edgeCurveHistoryLabel,
    canStartRegionDrag,
  };
}));
