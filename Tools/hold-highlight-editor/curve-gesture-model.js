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

  function edgeCurveInspectorState(region) {
    const visible = region?.metadata?.pathStyle === "smooth";
    const overridden = visible && Object.keys(region?.metadata?.edgeCurves || {}).length > 0;
    return {
      visible,
      overridden,
      feedback: overridden ? edgeCurveFeedback(region) : null,
    };
  }

  function shouldRenderEdgeCurveHandle({ start, end, control, vertices, zoom }) {
    const scale = Math.max(Number(zoom) || 0, 0.3);
    const candidate = control || [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2];
    // Include both circle radii and the combined 1.5px stroke width so SVG hit areas do not touch.
    const minimumDistance = (4.5 + 3.75 + 1.5) / scale;
    const neighboringVertices = vertices || [start, end];
    if (!Array.isArray(candidate) || candidate.length !== 2 || !candidate.every(Number.isFinite)) return false;
    return neighboringVertices.every((vertex) => (
      Array.isArray(vertex)
      && vertex.length === 2
      && vertex.every(Number.isFinite)
      && Math.hypot(candidate[0] - vertex[0], candidate[1] - vertex[1]) >= minimumDistance
    ));
  }

  function canStartRegionDrag({ drawing, spacePressed, button }) {
    return !drawing && !spacePressed && button === 0;
  }

  return {
    beginEdgeCurveSession,
    updateEdgeCurveSession,
    edgeCurveHistoryLabel,
    edgeCurveFeedback,
    edgeCurveInspectorState,
    shouldRenderEdgeCurveHandle,
    canStartRegionDrag,
  };
}));
