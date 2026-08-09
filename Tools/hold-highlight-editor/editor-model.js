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
  const roundRasterCoordinate = (value) => {
    const lower = Math.floor(value);
    if (value - lower !== 0.5) return Math.round(value);
    return lower % 2 === 0 ? lower : lower + 1;
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

  function pointOnSegment([px, py], [x1, y1], [x2, y2]) {
    const cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1);
    if (Math.abs(cross) > 1e-9) return false;
    return px >= Math.min(x1, x2) - 1e-9
      && px <= Math.max(x1, x2) + 1e-9
      && py >= Math.min(y1, y2) - 1e-9
      && py <= Math.max(y1, y2) + 1e-9;
  }

  function pointInPolygon(point, points, includeBoundary = true) {
    let inside = false;
    for (let index = 0, previous = points.length - 1; index < points.length; previous = index, index += 1) {
      const start = points[previous];
      const end = points[index];
      if (pointOnSegment(point, start, end)) return includeBoundary;
      const crosses = (start[1] > point[1]) !== (end[1] > point[1]);
      if (crosses) {
        const intersectionX = start[0]
          + (point[1] - start[1]) * (end[0] - start[0]) / (end[1] - start[1]);
        if (point[0] < intersectionX) inside = !inside;
      }
    }
    return inside;
  }

  function exportAnchor(region, contour) {
    const existing = Array.isArray(region.anchor)
      && region.anchor.length === 2
      && region.anchor.every(Number.isFinite)
      ? region.anchor.map((value) => round(value))
      : null;
    if (existing && pointInPolygon(existing.map(roundRasterCoordinate), contour)) return existing;

    const center = centroid(contour);
    const [minX, minY, maxX, maxY] = bounds(contour);
    let best = null;
    for (let y = Math.ceil(minY); y <= Math.floor(maxY); y += 1) {
      const intersections = [];
      for (let index = 0; index < contour.length; index += 1) {
        const start = contour[index];
        const end = contour[(index + 1) % contour.length];
        if ((start[1] > y) === (end[1] > y)) continue;
        intersections.push(start[0] + (y - start[1]) * (end[0] - start[0]) / (end[1] - start[1]));
      }
      intersections.sort((left, right) => left - right);
      for (let index = 0; index + 1 < intersections.length; index += 2) {
        const left = intersections[index];
        const right = intersections[index + 1];
        const first = Math.ceil(left + 1e-9);
        const last = Math.floor(right - 1e-9);
        if (first > last) continue;
        const x = Math.round((first + last) / 2);
        if (!pointInPolygon([x, y], contour, false)) continue;
        const candidate = {
          point: [x, y],
          width: right - left,
          centerDistance: Math.hypot(x - center[0], y - center[1]),
        };
        if (
          best === null
          || candidate.width > best.width
          || (candidate.width === best.width && candidate.centerDistance < best.centerDistance)
          || (candidate.width === best.width && candidate.centerDistance === best.centerDistance && y < best.point[1])
          || (candidate.width === best.width && candidate.centerDistance === best.centerDistance && y === best.point[1] && x < best.point[0])
        ) best = candidate;
      }
    }
    if (best) return best.point;
    return contour[0].map(roundRasterCoordinate);
  }

  function regionForExport(region) {
    validateContour(region?.contour);
    const contour = region.contour.map(([x, y]) => [round(x), round(y)]);
    const authoritativeContour = stage2AuthoritativeContour(
      contour,
      region.metadata?.pathStyle || "straight",
      region.metadata?.curveTension ?? 0.8,
      region.metadata?.cornerTreatments,
    );
    return {
      ...clone(region),
      anchor: exportAnchor(region, authoritativeContour),
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
      cornerTreatments: clone(region.metadata?.cornerTreatments || {}),
      notes: region.metadata?.humanNotes || "",
    });
  }

  function contourPath(points, style = "straight", tension = 0.8, cornerTreatments = {}) {
    validateContour(points);
    const treatments = normalizeCornerTreatments(cornerTreatments, points.length);
    if (Object.keys(treatments).length === 0) {
      return style === "smooth" ? smoothClosedPath(points, tension) : straightClosedPath(points);
    }
    return `${treatedPathCommands(points, style, tension, treatments).map(serializePathCommand).join(" ")} Z`;
  }

  function stage2AuthoritativeContour(points, style, tension, cornerTreatments) {
    if (cornerTreatments === undefined || cornerTreatments === null) return clone(points);
    const treatments = normalizeCornerTreatments(cornerTreatments, points.length);
    if (Object.keys(treatments).length === 0) return clone(points);
    return flattenPathCommands(treatedPathCommands(points, style, tension, treatments), 32);
  }

  function treatedPathCommands(points, style, tension, treatments) {
    if (!new Set(["straight", "smooth"]).has(style)) throw new TypeError("Contour path style is invalid");
    const corners = points.map((point, index) => cornerGeometry(points, index, treatments[index]));
    const result = [{ type: "M", point: corners[0].exit }];
    for (let index = 1; index < points.length; index += 1) {
      result.push(connectorCommand(points, corners, index - 1, index, style, tension, treatments));
      if (treatments[index]?.treatment === "rounded") {
        result.push({ type: "Q", control: points[index], point: corners[index].exit });
      }
    }
    result.push(connectorCommand(points, corners, points.length - 1, 0, style, tension, treatments));
    if (treatments[0]?.treatment === "rounded") {
      result.push({ type: "Q", control: points[0], point: corners[0].exit });
    }
    return result;
  }

  function straightClosedPath(points) {
    return `M ${points.map(formatPoint).join(" L ")} Z`;
  }

  function smoothClosedPath(points, tension) {
    const tangentScale = Math.max(0.1, Math.min(1.4, Number(tension) || 0.8)) / 6;
    let result = `M ${formatPoint(points[0])}`;
    for (let index = 0; index < points.length; index += 1) {
      const previous = points[(index - 1 + points.length) % points.length];
      const current = points[index];
      const next = points[(index + 1) % points.length];
      const afterNext = points[(index + 2) % points.length];
      const controlOne = [current[0] + (next[0] - previous[0]) * tangentScale, current[1] + (next[1] - previous[1]) * tangentScale];
      const controlTwo = [next[0] - (afterNext[0] - current[0]) * tangentScale, next[1] - (afterNext[1] - current[1]) * tangentScale];
      result += ` C ${formatPoint(controlOne)} ${formatPoint(controlTwo)} ${formatPoint(next)}`;
    }
    return `${result} Z`;
  }

  function connectorCommand(points, corners, fromIndex, toIndex, style, tension, treatments) {
    const target = corners[toIndex].entry;
    if (style !== "smooth" || treatments[fromIndex] || treatments[toIndex]) return { type: "L", point: target };
    const tangentScale = Math.max(0.1, Math.min(1.4, Number(tension) || 0.8)) / 6;
    const previous = points[(fromIndex - 1 + points.length) % points.length];
    const current = points[fromIndex];
    const next = points[toIndex];
    const afterNext = points[(toIndex + 1) % points.length];
    const controlOne = [current[0] + (next[0] - previous[0]) * tangentScale, current[1] + (next[1] - previous[1]) * tangentScale];
    const controlTwo = [next[0] - (afterNext[0] - current[0]) * tangentScale, next[1] - (afterNext[1] - current[1]) * tangentScale];
    return { type: "C", controlOne, controlTwo, point: target };
  }

  function serializePathCommand(command) {
    if (command.type === "M" || command.type === "L") return `${command.type} ${formatPoint(command.point)}`;
    if (command.type === "Q") return `Q ${formatPoint(command.control)} ${formatPoint(command.point)}`;
    return `C ${formatPoint(command.controlOne)} ${formatPoint(command.controlTwo)} ${formatPoint(command.point)}`;
  }

  function flattenPathCommands(commands, curveSteps) {
    const result = [];
    let current = null;
    for (const command of commands) {
      if (command.type === "M" || command.type === "L") {
        current = command.point.slice();
        result.push(current);
        continue;
      }
      const start = current;
      for (let step = 1; step <= curveSteps; step += 1) {
        const progress = step / curveSteps;
        const remaining = 1 - progress;
        if (command.type === "Q") {
          current = [
            remaining ** 2 * start[0] + 2 * remaining * progress * command.control[0] + progress ** 2 * command.point[0],
            remaining ** 2 * start[1] + 2 * remaining * progress * command.control[1] + progress ** 2 * command.point[1],
          ];
        } else {
          current = [
            remaining ** 3 * start[0] + 3 * remaining ** 2 * progress * command.controlOne[0] + 3 * remaining * progress ** 2 * command.controlTwo[0] + progress ** 3 * command.point[0],
            remaining ** 3 * start[1] + 3 * remaining ** 2 * progress * command.controlOne[1] + 3 * remaining * progress ** 2 * command.controlTwo[1] + progress ** 3 * command.point[1],
          ];
        }
        result.push(current);
      }
    }
    return result;
  }

  function cornerGeometry(points, index, treatment) {
    const vertex = points[index];
    if (treatment?.treatment !== "rounded") return { entry: vertex.slice(), exit: vertex.slice() };
    const previous = points[(index - 1 + points.length) % points.length];
    const next = points[(index + 1) % points.length];
    const previousLength = Math.hypot(vertex[0] - previous[0], vertex[1] - previous[1]);
    const nextLength = Math.hypot(next[0] - vertex[0], next[1] - vertex[1]);
    const cut = Math.min(treatment.amount, previousLength / 2, nextLength / 2);
    const toward = (target, length) => length === 0 ? vertex.slice() : [
      vertex[0] + (target[0] - vertex[0]) * cut / length,
      vertex[1] + (target[1] - vertex[1]) * cut / length,
    ];
    return { entry: toward(previous, previousLength), exit: toward(next, nextLength) };
  }

  function shiftCornerTreatmentsForInsertion(cornerTreatments, insertionIndex, pointCount) {
    if (!Number.isInteger(insertionIndex) || insertionIndex < 0 || insertionIndex > pointCount) {
      throw new RangeError("Corner insertion index is invalid");
    }
    const treatments = normalizeCornerTreatments(cornerTreatments, pointCount);
    return Object.fromEntries(Object.entries(treatments).map(([key, value]) => {
      const index = Number(key);
      return [index >= insertionIndex ? index + 1 : index, clone(value)];
    }));
  }

  function mirrorCornerTreatments(cornerTreatments, pointCount) {
    const treatments = normalizeCornerTreatments(cornerTreatments, pointCount);
    return Object.fromEntries(Object.entries(treatments).map(([key, value]) => [
      pointCount - 1 - Number(key), clone(value),
    ]));
  }

  function normalizeCornerTreatments(cornerTreatments, pointCount) {
    if (!cornerTreatments || typeof cornerTreatments !== "object" || Array.isArray(cornerTreatments)) {
      throw new TypeError("Corner treatments must be an object");
    }
    const result = {};
    for (const [key, treatment] of Object.entries(cornerTreatments)) {
      const index = Number(key);
      if (!Number.isInteger(index) || index < 0 || index >= pointCount || String(index) !== key) {
        throw new RangeError("Corner treatment index is invalid");
      }
      if (!treatment || !new Set(["sharp", "rounded"]).has(treatment.treatment)) {
        throw new TypeError("Corner treatment must be sharp or rounded");
      }
      if (!Number.isFinite(treatment.amount) || treatment.amount <= 0) {
        throw new RangeError("Corner treatment amount must be finite and positive");
      }
      result[index] = { treatment: treatment.treatment, amount: treatment.amount };
    }
    return result;
  }

  function isExportableContour(points) {
    return Array.isArray(points)
      && points.length >= 3
      && points.every((point) => Array.isArray(point)
        && point.length === 2
        && point.every(Number.isFinite));
  }

  function validateContour(points) {
    if (!Array.isArray(points) || points.length < 3) throw new TypeError("Contour must contain at least three points");
    if (!isExportableContour(points)) throw new TypeError("Contour coordinates must be finite points");
  }

  function formatPoint([x, y]) {
    return `${round(x)} ${round(y)}`;
  }

  function normalizePipelineDocument(document, fallbackCanvas, editorMode = "contour") {
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
    return { canvas, regions, editorMode };
  }

  function nextStage2RegionId({ baselineRegions = [], regions = [], nextRegionId = 1 }) {
    const identifiers = [...baselineRegions, ...regions]
      .map((region) => Number(region?.id))
      .filter((identifier) => Number.isInteger(identifier) && identifier > 0);
    const floor = Math.max(0, ...identifiers) + 1;
    const requested = Number(nextRegionId);
    return Number.isInteger(requested) && requested > floor ? requested : floor;
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

  function resizeTransform({ points, rotation = 0, handle, pointer, preserveAspect = false }) {
    if (!Array.isArray(points) || points.length === 0) throw new TypeError("resize points are required");
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
    const localXs = local.map(([x]) => x);
    const localYs = local.map(([, y]) => y);
    const [minX, minY, maxX, maxY] = [
      Math.min(...localXs),
      Math.min(...localYs),
      Math.max(...localXs),
      Math.max(...localYs),
    ];
    const localPointer = toLocal(pointer);
    const scalesX = handle.includes("e") || handle.includes("w");
    const scalesY = handle.includes("n") || handle.includes("s");
    const anchorX = handle.includes("w") ? maxX : minX;
    const anchorY = handle.includes("n") ? maxY : minY;
    const movingX = handle.includes("w") ? minX : maxX;
    const movingY = handle.includes("n") ? minY : maxY;
<<<<<<< HEAD
    let scaleX = scalesX ? (localPointer[0] - anchorX) / Math.max(Math.abs(movingX - anchorX), 1e-6) : 1;
    let scaleY = scalesY ? (localPointer[1] - anchorY) / Math.max(Math.abs(movingY - anchorY), 1e-6) : 1;
    const localWidth = Math.max(maxX - minX, 1e-6);
    const localHeight = Math.max(maxY - minY, 1e-6);
    const minimumSize = 6;
    const minimumScaleX = minimumSize / localWidth;
    const minimumScaleY = minimumSize / localHeight;
    scaleX = scalesX ? Math.max(minimumScaleX, scaleX) : 1;
    scaleY = scalesY ? Math.max(minimumScaleY, scaleY) : 1;
=======
    const signedFloor = (value) => Math.abs(value) < 1e-6 ? (value < 0 ? -1e-6 : 1e-6) : value;
    let scaleX = scalesX ? (localPointer[0] - anchorX) / signedFloor(movingX - anchorX) : 1;
    let scaleY = scalesY ? (localPointer[1] - anchorY) / signedFloor(movingY - anchorY) : 1;
    scaleX = Math.max(0.05, scaleX);
    scaleY = Math.max(0.05, scaleY);
>>>>>>> origin/main
    if (preserveAspect && scalesX && scalesY) {
      const dominant = Math.abs(scaleX - 1) >= Math.abs(scaleY - 1) ? scaleX : scaleY;
      const minimumScale = Math.max(minimumScaleX, minimumScaleY);
      scaleX = Math.max(minimumScale, dominant);
      scaleY = Math.max(minimumScale, dominant);
    }
    const transformPoint = (point) => {
      const [x, y] = toLocal(point);
      return toWorld([
        scalesX ? anchorX + (x - anchorX) * scaleX : x,
        scalesY ? anchorY + (y - anchorY) * scaleY : y,
      ]);
    };
    const origin = transformPoint([0, 0]);
    const unitX = transformPoint([1, 0]);
    const unitY = transformPoint([0, 1]);
    return [
      unitX[0] - origin[0],
      unitX[1] - origin[1],
      unitY[0] - origin[0],
      unitY[1] - origin[1],
      origin[0],
      origin[1],
    ].map((value) => Math.abs(value) < 1e-12 ? 0 : value);
  }

  function resizeContour(options) {
    const matrix = resizeTransform(options);
    return options.points.map(([x, y]) => [
      round(matrix[0] * x + matrix[2] * y + matrix[4]),
      round(matrix[1] * x + matrix[3] * y + matrix[5]),
    ]);
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
    resizeTransform,
    resizeContour,
    simplifyClosedContour,
    mirrorContour,
    findStrongestEdge,
    resolveHistorySelection,
    normalizePipelineDocument,
    nextStage2RegionId,
    contourPath,
    isExportableContour,
    shiftCornerTreatmentsForInsertion,
    mirrorCornerTreatments,
    canSaveEditorState,
    runSessionLoadTransaction,
    formatSessionLoadError,
  };
}));
