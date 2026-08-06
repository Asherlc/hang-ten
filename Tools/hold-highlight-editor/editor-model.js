(function exposeEditorModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldEditorModel = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const clone = (value) => JSON.parse(JSON.stringify(value));
  const round = (value, digits = 2) => {
    const factor = 10 ** digits;
    return Math.round(value * factor) / factor;
  };

  function polygonArea(points) {
    let sum = 0;
    for (let index = 0; index < points.length; index += 1) {
      const [x1, y1] = points[index];
      const [x2, y2] = points[(index + 1) % points.length];
      sum += x1 * y2 - x2 * y1;
    }
    return Math.abs(sum / 2);
  }

  function centroid(points) {
    const [x, y] = points.reduce(([sumX, sumY], point) => [sumX + point[0], sumY + point[1]], [0, 0]);
    return [x / points.length, y / points.length];
  }

  function bounds(points) {
    const xs = points.map(([x]) => x);
    const ys = points.map(([, y]) => y);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)].map((value) => round(value));
  }

  function regionForExport(region) {
    const contour = region.contour.map(([x, y]) => [round(x), round(y)]);
    return {
      ...clone(region),
      anchor: centroid(contour).map((value) => round(value)),
      areaPixels: Math.round(polygonArea(contour)),
      bounds: bounds(contour),
      contour,
      metadata: {
        ...clone(region.metadata || {}),
        editedBy: "hold-highlight-editor",
      },
    };
  }

  function comparisonKey(region) {
    return JSON.stringify({
      key: region.key,
      type: region.type,
      contour: region.contour.map(([x, y]) => [round(x), round(y)]),
      mode: region.metadata?.mode,
      shapeKind: region.metadata?.shapeKind || "freeform",
      pathStyle: region.metadata?.pathStyle || "straight",
      curveTension: round(region.metadata?.curveTension ?? 0.8),
      rotation: round(region.metadata?.rotation ?? 0),
      bend: round(region.metadata?.bend ?? 0),
      notes: region.metadata?.humanNotes || "",
    });
  }

  function buildEditedDocument({ canvas, regions, imageName, regionsName }) {
    return {
      schemaVersion: 1,
      canvas: clone(canvas),
      labelEncoding: "uint16-region-id",
      source: { image: imageName, regions: regionsName },
      editor: { name: "hold-highlight-editor", exportedAt: new Date().toISOString() },
      regions: [...regions].sort((left, right) => left.id - right.id).map(regionForExport),
    };
  }

  function buildCorrectionsDocument({ baselineRegions, regions, imageName = "", regionsName = "" }) {
    const baselineById = new Map(baselineRegions.map((region) => [region.id, region]));
    const currentById = new Map(regions.map((region) => [region.id, region]));
    const added = regions.filter((region) => !baselineById.has(region.id)).map(regionForExport);
    const deleted = baselineRegions.filter((region) => !currentById.has(region.id)).map((region) => ({ id: region.id, key: region.key }));
    const modified = regions
      .filter((region) => baselineById.has(region.id) && comparisonKey(region) !== comparisonKey(baselineById.get(region.id)))
      .map((region) => ({ before: regionForExport(baselineById.get(region.id)), after: regionForExport(region) }));
    return {
      schemaVersion: 1,
      kind: "human-region-corrections",
      source: { image: imageName, regions: regionsName },
      exportedAt: new Date().toISOString(),
      summary: { added: added.length, modified: modified.length, deleted: deleted.length },
      added,
      modified,
      deleted,
    };
  }

  return { buildEditedDocument, buildCorrectionsDocument };
}));
