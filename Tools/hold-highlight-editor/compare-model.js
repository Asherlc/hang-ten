(function exposeComparisonModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldComparisonModel = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const ordered = (values) => [...values].sort((left, right) => left - right);

  function normalize(region) {
    return JSON.stringify({
      key: region.key,
      type: region.type,
      mode: region.mode,
      contour: (region.contour || []).map(([x, y]) => [Number(x), Number(y)]),
    });
  }

  function toMap(regions) {
    return new Map((regions || []).map((region) => [Number(region.id), region]));
  }

  function correctionIds(corrections, key) {
    return ordered(new Set((corrections?.[key] || []).map((entry) => Number(entry.id)).filter(Number.isFinite)));
  }

  function buildSummary(baseline, edited, corrections = null) {
    const baselineById = toMap(baseline);
    const editedById = toMap(edited);

    const added = corrections ? correctionIds(corrections, "added") : ordered(
      [...editedById.keys()].filter((id) => !baselineById.has(id)),
    );
    const deleted = corrections ? correctionIds(corrections, "deleted") : ordered(
      [...baselineById.keys()].filter((id) => !editedById.has(id)),
    );
    const modified = corrections ? correctionIds(corrections, "modified") : ordered(
      [...editedById.keys()].filter((id) => baselineById.has(id) && normalize(editedById.get(id)) !== normalize(baselineById.get(id))),
    );
    const changed = new Set([...added, ...deleted, ...modified]);
    const unchanged = ordered(
      [...baselineById.keys()].filter((id) => editedById.has(id) && !changed.has(id) && normalize(editedById.get(id)) === normalize(baselineById.get(id))),
    );
    return { added, modified, deleted, unchanged };
  }

  function visibleLayers(mode) {
    const layers = {
      image: ["image"],
      automatic: ["image", "automatic"],
      edited: ["image", "edited"],
      difference: ["image", "automatic", "edited", "difference"],
    }[mode];
    if (!layers) throw new Error(`unsupported comparison mode: ${mode}`);
    return layers.slice();
  }

  function computeFitZoom({
    imageWidth,
    imageHeight,
    viewportWidth,
    viewportHeight,
    maxZoom = 1,
  }) {
    const sourceWidth = Number(imageWidth);
    const sourceHeight = Number(imageHeight);
    const targetWidth = Number(viewportWidth);
    const targetHeight = Number(viewportHeight);
    const maximum = Number(maxZoom);
    if (![sourceWidth, sourceHeight, targetWidth, targetHeight, maximum].every(Number.isFinite)) return 1;
    if (sourceWidth <= 0 || sourceHeight <= 0 || targetWidth <= 0 || targetHeight <= 0 || maximum <= 0) return 1;
    const ratio = Math.min(targetWidth / sourceWidth, targetHeight / sourceHeight);
    return Math.min(maximum, Number(ratio.toFixed(4)));
  }

  return {
    buildSummary,
    computeFitZoom,
    visibleLayers,
  };
}));
