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

  function normalizeEdgeCurves(edgeCurves, pointCount) {
    if (!Number.isInteger(pointCount) || pointCount < 0) throw new Error("Edge curve point count must be a non-negative integer.");
    if (edgeCurves === undefined) return {};
    if (!edgeCurves || typeof edgeCurves !== "object" || Array.isArray(edgeCurves)) {
      throw new Error("Edge curves must be an object keyed by edge index.");
    }
    const normalized = {};
    Object.entries(edgeCurves).forEach(([key, entry]) => {
      if (!/^(0|[1-9]\d*)$/.test(key) || Number(key) >= pointCount) {
        throw new Error(`Invalid edge curve index: ${key}.`);
      }
      if (!entry || typeof entry !== "object" || Array.isArray(entry) || entry.kind !== "quadratic") {
        throw new Error(`Invalid edge curve kind at edge ${key}.`);
      }
      if (!Array.isArray(entry.control) || entry.control.length !== 2 || !entry.control.every(Number.isFinite)) {
        throw new Error(`Edge curve control at edge ${key} must contain two finite coordinates.`);
      }
      normalized[Number(key)] = { kind: "quadratic", control: [entry.control[0], entry.control[1]] };
    });
    return normalized;
  }

  function smoothControls(points, index, tension) {
    const count = points.length;
    const tangentScale = Math.max(0.1, Math.min(1.4, Number(tension) || 0.8)) / 6;
    const previous = points[(index - 1 + count) % count];
    const current = points[index];
    const next = points[(index + 1) % count];
    const afterNext = points[(index + 2) % count];
    return [
      [current[0] + (next[0] - previous[0]) * tangentScale, current[1] + (next[1] - previous[1]) * tangentScale],
      [next[0] - (afterNext[0] - current[0]) * tangentScale, next[1] - (afterNext[1] - current[1]) * tangentScale],
    ];
  }

  function contourPath(points, style = "straight", tension = 0.8, edgeCurves) {
    if (!points?.length) return "";
    const curves = normalizeEdgeCurves(edgeCurves, points.length);
    const curveIndexes = Object.keys(curves);
    const pointText = ([x, y]) => `${round(x)} ${round(y)}`;
    if (!curveIndexes.length) {
      if (style !== "smooth" || points.length < 3) {
        return `M ${points.map(pointText).join(" L ")} Z`;
      }
      let result = `M ${pointText(points[0])}`;
      for (let index = 0; index < points.length; index += 1) {
        const [controlOne, controlTwo] = smoothControls(points, index, tension);
        const endpoint = points[(index + 1) % points.length];
        result += ` C ${pointText(controlOne)}, ${pointText(controlTwo)}, ${pointText(endpoint)}`;
      }
      return `${result} Z`;
    }
    let result = `M ${pointText(points[0])}`;
    for (let index = 0; index < points.length; index += 1) {
      const endpoint = points[(index + 1) % points.length];
      const curve = curves[index];
      result += curve
        ? ` Q ${pointText(curve.control)} ${pointText(endpoint)}`
        : ` L ${pointText(endpoint)}`;
    }
    return `${result} Z`;
  }

  function flattenContour(points, style = "straight", tension = 0.8, edgeCurves, curveSteps = 32) {
    if (!points?.length) return [];
    if (!Number.isInteger(curveSteps) || curveSteps < 1) throw new Error("curveSteps must be a positive integer.");
    const curves = normalizeEdgeCurves(edgeCurves, points.length);
    const hasEdgeCurves = Object.keys(curves).length > 0;
    const usesSmoothPath = !hasEdgeCurves && style === "smooth" && points.length >= 3;
    if (!hasEdgeCurves && !usesSmoothPath) return points.map(([x, y]) => [x, y]);

    const flattened = [[points[0][0], points[0][1]]];
    for (let index = 0; index < points.length; index += 1) {
      const start = points[index];
      const endpoint = points[(index + 1) % points.length];
      const curve = curves[index];
      if (!curve && !usesSmoothPath) {
        if (index < points.length - 1) flattened.push([endpoint[0], endpoint[1]]);
        continue;
      }
      const controls = usesSmoothPath ? smoothControls(points, index, tension) : null;
      for (let step = 1; step <= curveSteps; step += 1) {
        if (index === points.length - 1 && step === curveSteps) continue;
        const progress = step / curveSteps;
        const remaining = 1 - progress;
        if (curve) {
          flattened.push([
            remaining ** 2 * start[0] + 2 * remaining * progress * curve.control[0] + progress ** 2 * endpoint[0],
            remaining ** 2 * start[1] + 2 * remaining * progress * curve.control[1] + progress ** 2 * endpoint[1],
          ]);
        } else {
          const [controlOne, controlTwo] = controls;
          flattened.push([
            remaining ** 3 * start[0] + 3 * remaining ** 2 * progress * controlOne[0]
              + 3 * remaining * progress ** 2 * controlTwo[0] + progress ** 3 * endpoint[0],
            remaining ** 3 * start[1] + 3 * remaining ** 2 * progress * controlOne[1]
              + 3 * remaining * progress ** 2 * controlTwo[1] + progress ** 3 * endpoint[1],
          ]);
        }
      }
    }
    return flattened;
  }

  function mapEdgeCurves(edgeCurves, pointCount, mapper) {
    if (typeof mapper !== "function") throw new Error("Edge curve mapper must be a function.");
    const curves = normalizeEdgeCurves(edgeCurves, pointCount);
    const mapped = {};
    Object.entries(curves).forEach(([key, entry]) => {
      const index = Number(key);
      const control = mapper([entry.control[0], entry.control[1]], index);
      if (!Array.isArray(control) || control.length !== 2 || !control.every(Number.isFinite)) {
        throw new Error(`Mapped edge curve control at edge ${key} must contain two finite coordinates.`);
      }
      mapped[index] = { kind: "quadratic", control: [control[0], control[1]] };
    });
    return mapped;
  }

  function setEdgeCurveControl(edgeCurves, edgeIndex, control, pointCount) {
    const curves = normalizeEdgeCurves(edgeCurves, pointCount);
    return normalizeEdgeCurves({
      ...curves,
      [edgeIndex]: { kind: "quadratic", control },
    }, pointCount);
  }

  function translateEdgeCurves(edgeCurves, dx, dy, pointCount) {
    if (!Number.isFinite(dx) || !Number.isFinite(dy)) throw new Error("Edge curve translation must use finite coordinates.");
    return mapEdgeCurves(edgeCurves, pointCount, ([x, y]) => [x + dx, y + dy]);
  }

  function mirrorEdgeCurves(edgeCurves, pointCount, canvasWidth) {
    if (!Number.isFinite(canvasWidth)) throw new Error("Edge curve mirror width must be finite.");
    const curves = normalizeEdgeCurves(edgeCurves, pointCount);
    const mirrored = {};
    Object.entries(curves).forEach(([key, entry]) => {
      const oldIndex = Number(key);
      const newIndex = (pointCount - 2 - oldIndex + pointCount) % pointCount;
      mirrored[newIndex] = {
        kind: "quadratic",
        control: [canvasWidth - entry.control[0], entry.control[1]],
      };
    });
    return mirrored;
  }

  function insertEdgeCurves(edgeCurves, insertionIndex, pointCount) {
    const curves = normalizeEdgeCurves(edgeCurves, pointCount);
    if (!Number.isInteger(insertionIndex) || insertionIndex < 0 || insertionIndex > pointCount) {
      throw new Error("Edge curve insertion index is outside the contour.");
    }
    if (pointCount === 0) return curves;
    const splitEdge = (insertionIndex - 1 + pointCount) % pointCount;
    const inserted = {};
    Object.entries(curves).forEach(([key, entry]) => {
      const oldIndex = Number(key);
      if (oldIndex === splitEdge) return;
      const newIndex = oldIndex >= insertionIndex ? oldIndex + 1 : oldIndex;
      inserted[newIndex] = { kind: "quadratic", control: [entry.control[0], entry.control[1]] };
    });
    return normalizeEdgeCurves(inserted, pointCount + 1);
  }

  function normalizeEditableContour(editableContour) {
    if (!Array.isArray(editableContour) || editableContour.length < 3) {
      throw new Error("Editable contour must contain at least three finite points.");
    }
    return editableContour.map((point) => {
      if (!Array.isArray(point) || point.length !== 2) {
        throw new Error("Editable contour must contain at least three finite points.");
      }
      const normalized = point.map(Number);
      if (!normalized.every(Number.isFinite)) {
        throw new Error("Editable contour must contain at least three finite points.");
      }
      return normalized;
    });
  }

  function regionForExport(region) {
    const metadata = clone(region.metadata || {});
    const hasEdgeCurves = Object.hasOwn(region.metadata || {}, "edgeCurves");
    const edgeCurves = hasEdgeCurves
      ? normalizeEdgeCurves(region.metadata.edgeCurves, region.contour.length)
      : undefined;
    delete metadata.editableContour;
    if (hasEdgeCurves) metadata.edgeCurves = edgeCurves;
    const contour = flattenContour(
      region.contour,
      metadata.pathStyle || "straight",
      Number(metadata.curveTension ?? 0.8),
      edgeCurves,
    ).map(([x, y]) => [round(x), round(y)]);
    if (hasEdgeCurves || contour.length !== region.contour.length) {
      metadata.editableContour = region.contour.map(([x, y]) => [round(x), round(y)]);
    }
    return {
      ...clone(region),
      anchor: centroid(contour).map((value) => round(value)),
      areaPixels: Math.round(polygonArea(contour)),
      bounds: bounds(contour),
      contour,
      metadata: {
        ...metadata,
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
      edgeCurves: normalizeEdgeCurves(region.metadata?.edgeCurves, region.contour.length),
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
      const contour = Object.hasOwn(region.metadata || {}, "editableContour")
        ? normalizeEditableContour(region.metadata.editableContour)
        : (region.contour || region.points || []).map(([x, y]) => [Number(x), Number(y)]);
      const metadata = {
        mode: region.metadata?.mode || region.mode || region.visualMode || (region.type === "pocket" ? "aperture" : "surface"),
        shapeKind: region.metadata?.shapeKind || "freeform",
        pathStyle: region.metadata?.pathStyle || "straight",
        curveTension: Number(region.metadata?.curveTension ?? 0.8),
        humanNotes: region.metadata?.humanNotes || "",
        ...clone(region.metadata || {}),
        ...(typeof sourceId === "string" && !/^\d+$/.test(sourceId) ? { sourceRegionId: sourceId } : {}),
      };
      delete metadata.editableContour;
      if (Object.hasOwn(region.metadata || {}, "edgeCurves")) {
        metadata.edgeCurves = normalizeEdgeCurves(region.metadata.edgeCurves, contour.length);
      }
      return {
        ...clone(region),
        id,
        key: region.key || (typeof sourceId === "string" ? sourceId : `grip-${String(id).padStart(3, "0")}`),
        type: region.type || "edge",
        contour,
        metadata,
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
    const localWidth = Math.max(maxX - minX, 1e-6);
    const localHeight = Math.max(maxY - minY, 1e-6);
    const minimumSize = 6;
    const minimumScaleX = minimumSize / localWidth;
    const minimumScaleY = minimumSize / localHeight;
    scaleX = scalesX ? Math.max(minimumScaleX, scaleX) : 1;
    scaleY = scalesY ? Math.max(minimumScaleY, scaleY) : 1;
    if (preserveAspect && scalesX && scalesY) {
      const dominant = Math.abs(scaleX - 1) >= Math.abs(scaleY - 1) ? scaleX : scaleY;
      const minimumScale = Math.max(minimumScaleX, minimumScaleY);
      scaleX = Math.max(minimumScale, dominant);
      scaleY = Math.max(minimumScale, dominant);
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
    normalizeEdgeCurves,
    contourPath,
    flattenContour,
    setEdgeCurveControl,
    translateEdgeCurves,
    mapEdgeCurves,
    mirrorEdgeCurves,
    insertEdgeCurves,
  };
}));
