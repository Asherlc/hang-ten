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
    if (!Number.isInteger(index) || index < 0 || index >= pointCount) {
      throw new Error(`Invalid edge curve index: ${index}.`);
    }
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

  function edgeCurveFeedback(region) {
    if (region?.metadata?.pathStyle !== "smooth" || !Object.keys(region.metadata.edgeCurves || {}).length) {
      return null;
    }
    return "Per-edge curves override smooth rendering; uncurved edges are straight and tension is ignored.";
  }

  function shouldRenderEdgeCurveHandle(start, end, zoom) {
    const scale = Math.max(Number(zoom) || 0, 0.3);
    const curveHandleRadius = 3.75 / scale;
    return Math.hypot(end[0] - start[0], end[1] - start[1]) >= curveHandleRadius * 3;
  }

  function canStartRegionDrag({ drawing, spacePressed, button }) {
    return !drawing && !spacePressed && button === 0;
  }

  return {
    beginEdgeCurveSession,
    updateEdgeCurveSession,
    edgeCurveHistoryLabel,
    edgeCurveFeedback,
    shouldRenderEdgeCurveHandle,
    canStartRegionDrag,
  };
}));
