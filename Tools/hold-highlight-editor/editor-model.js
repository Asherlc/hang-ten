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

  function normalizePipelineDocument(document, fallbackCanvas) {
    const canvas = {
      width: Number(document.canvas?.width || document.width || fallbackCanvas.width),
      height: Number(document.canvas?.height || document.height || fallbackCanvas.height),
    };
    const regions = (document.regions || []).map((region, index) => {
      const fallbackId = index + 1;
      const sourceId = region.id ?? fallbackId;
      const numericId = Number(sourceId);
      const id = Number.isInteger(numericId) && numericId > 0 ? numericId : fallbackId;
      return {
        ...clone(region),
        id,
        key: region.key || (typeof sourceId === "string" ? sourceId : `grip-${String(id).padStart(3, "0")}`),
        type: region.type || "edge",
        contour: (region.contour || region.points || []).map(([x, y]) => [Number(x), Number(y)]),
        metadata: {
          mode: region.metadata?.mode || region.mode || region.visualMode || (region.type === "pocket" ? "aperture" : "surface"),
          shapeKind: region.metadata?.shapeKind || "freeform",
          pathStyle: region.metadata?.pathStyle || "straight",
          curveTension: Number(region.metadata?.curveTension ?? 0.8),
          humanNotes: region.metadata?.humanNotes || "",
          ...clone(region.metadata || {}),
          ...(typeof sourceId === "string" && !/^\d+$/.test(sourceId) ? { sourceRegionId: sourceId } : {}),
        },
      };
    });
    return { canvas, regions };
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

  function canSaveEditorState({ serverSession, dirty, saving, loadingSession }) {
    return Boolean(serverSession && dirty && !saving && !loadingSession);
  }

  function formatSessionLoadError(error) {
    const trustedMessages = new Set([
      "Could not load the selected board session",
      "Could not load hold highlights from the run",
    ]);
    return error instanceof Error && trustedMessages.has(error.message)
      ? `Could not load the selected board: ${error.message}`
      : "Could not load the selected board. Please try again.";
  }

  async function runSessionLoadTransaction(current, { loadSession, loadRegions, normalizeRegions, loadImage }) {
    try {
      const session = await loadSession();
      const regions = await loadRegions(session);
      const imageAsset = await loadImage(session);
      const normalized = normalizeRegions(regions, {
        width: imageAsset.image.naturalWidth,
        height: imageAsset.image.naturalHeight,
      });
      return { ok: true, value: { session, normalized, imageAsset }, error: null };
    } catch (error) {
      return { ok: false, value: current, error };
    }
  }

  function resizeContour({ points, rotation = 0, handle, pointer, preserveAspect = false }) {
    const center = centroid(points);
    const cosine = Math.cos(rotation);
    const sine = Math.sin(rotation);
    const toLocal = ([x, y]) => {
      const dx = x - center[0];
      const dy = y - center[1];
      return [dx * cosine + dy * sine, -dx * sine + dy * cosine];
    };
    const toWorld = ([x, y]) => [
      center[0] + x * cosine - y * sine,
      center[1] + x * sine + y * cosine,
    ];
    const local = points.map(toLocal);
    const [minX, minY, maxX, maxY] = bounds(local);
    const localPointer = toLocal(pointer);
    const scalesX = handle.includes("e") || handle.includes("w");
    const scalesY = handle.includes("n") || handle.includes("s");
    const anchorX = handle.includes("w") ? maxX : minX;
    const anchorY = handle.includes("n") ? maxY : minY;
    const movingX = handle.includes("w") ? minX : maxX;
    const movingY = handle.includes("n") ? minY : maxY;
    let scaleX = scalesX ? (localPointer[0] - anchorX) / Math.max(Math.abs(movingX - anchorX), 1e-6) : 1;
    let scaleY = scalesY ? (localPointer[1] - anchorY) / Math.max(Math.abs(movingY - anchorY), 1e-6) : 1;
    scaleX = Math.max(0.05, scaleX);
    scaleY = Math.max(0.05, scaleY);
    if (preserveAspect && scalesX && scalesY) {
      const dominant = Math.abs(scaleX - 1) >= Math.abs(scaleY - 1) ? scaleX : scaleY;
      scaleX = dominant;
      scaleY = dominant;
    }
    return local.map(([x, y]) => toWorld([
      scalesX ? anchorX + (x - anchorX) * scaleX : x,
      scalesY ? anchorY + (y - anchorY) * scaleY : y,
    ])).map(([x, y]) => [round(x), round(y)]);
  }

  function mirrorContour(points, canvasWidth) {
    return points.map(([x, y]) => [round(canvasWidth - x), round(y)]).reverse();
  }

  function simplifyClosedContour(points, tolerance) {
    const ring = points.length > 1 && points[0][0] === points.at(-1)[0] && points[0][1] === points.at(-1)[1]
      ? points.slice(0, -1)
      : points.slice();
    if (ring.length <= 4) return clone(ring);
    let first = 0;
    let second = 1;
    let greatestDistance = -1;
    for (let left = 0; left < ring.length; left += 1) {
      for (let right = left + 1; right < ring.length; right += 1) {
        const distance = (ring[left][0] - ring[right][0]) ** 2 + (ring[left][1] - ring[right][1]) ** 2;
        if (distance > greatestDistance) {
          greatestDistance = distance;
          first = left;
          second = right;
        }
      }
    }
    const chain = (start, end) => {
      const result = [];
      for (let index = start; ; index = (index + 1) % ring.length) {
        result.push(ring[index]);
        if (index === end) break;
      }
      return result;
    };
    const forward = simplifyOpenContour(chain(first, second), tolerance);
    const backward = simplifyOpenContour(chain(second, first), tolerance);
    const simplified = [...forward, ...backward.slice(1, -1)];
    return simplified.length >= 4 ? clone(simplified) : clone(ring);
  }

  function simplifyOpenContour(points, tolerance) {
    if (points.length <= 2) return points.slice();
    let greatestDistance = -1;
    let splitIndex = -1;
    for (let index = 1; index < points.length - 1; index += 1) {
      const distance = distanceToSegment(points[index], points[0], points.at(-1));
      if (distance > greatestDistance) {
        greatestDistance = distance;
        splitIndex = index;
      }
    }
    if (greatestDistance <= tolerance) return [points[0], points.at(-1)];
    return [
      ...simplifyOpenContour(points.slice(0, splitIndex + 1), tolerance).slice(0, -1),
      ...simplifyOpenContour(points.slice(splitIndex), tolerance),
    ];
  }

  function distanceToSegment([px, py], [x1, y1], [x2, y2]) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    if (dx === 0 && dy === 0) return Math.hypot(px - x1, py - y1);
    const progress = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)));
    return Math.hypot(px - (x1 + progress * dx), py - (y1 + progress * dy));
  }

  function findStrongestEdge({ rgba, width, height, point, radius, threshold }) {
    if (!rgba || width < 3 || height < 3) return null;
    const [centerX, centerY] = point;
    const luminance = (x, y) => {
      const offset = (y * width + x) * 4;
      return rgba[offset] * 0.2126 + rgba[offset + 1] * 0.7152 + rgba[offset + 2] * 0.0722;
    };
    let bestPoint = null;
    let bestScore = threshold;
    let bestDistance = Infinity;
    const minX = Math.max(1, Math.floor(centerX - radius));
    const maxX = Math.min(width - 2, Math.ceil(centerX + radius));
    const minY = Math.max(1, Math.floor(centerY - radius));
    const maxY = Math.min(height - 2, Math.ceil(centerY + radius));
    for (let y = minY; y <= maxY; y += 1) {
      for (let x = minX; x <= maxX; x += 1) {
        const distance = Math.hypot(x - centerX, y - centerY);
        if (distance > radius) continue;
        const gradientX = luminance(x + 1, y) - luminance(x - 1, y);
        const gradientY = luminance(x, y + 1) - luminance(x, y - 1);
        const score = Math.hypot(gradientX, gradientY);
        if (score > bestScore || (score === bestScore && distance < bestDistance)) {
          bestScore = score;
          bestDistance = distance;
          bestPoint = [x, y];
        }
      }
    }
    return bestPoint;
  }

  function resolveHistorySelection(entry, regions, fallbackSelectedId) {
    const candidate = Number.isInteger(entry?.selectedId) ? entry.selectedId : fallbackSelectedId;
    return regions.some((region) => region.id === candidate) ? candidate : null;
  }

  return {
    buildEditedDocument,
    buildCorrectionsDocument,
    resizeContour,
    simplifyClosedContour,
    mirrorContour,
    findStrongestEdge,
    resolveHistorySelection,
    normalizePipelineDocument,
    canSaveEditorState,
    runSessionLoadTransaction,
    formatSessionLoadError,
  };
}));
