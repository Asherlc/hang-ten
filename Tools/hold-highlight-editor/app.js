(() => {
  "use strict";

  const TYPE_COLORS = {
    jug: "#ff754f",
    sloper: "#32bbc1",
    edge: "#9a6cf2",
    pocket: "#ee4d97",
  };

  const state = {
    canvas: { width: 1000, height: 358 },
    imageHref: "",
    imageName: "",
    regionsName: "",
    regions: [],
    baselineRegions: [],
    selectedId: null,
    overlayMode: "all",
    opacity: 0.34,
    zoom: 1,
    panX: 0,
    panY: 0,
    drawing: false,
    drawShape: "freeform",
    draft: [],
    primitiveSession: null,
    spacePressed: false,
    panSession: null,
    dragSession: null,
    handleSession: null,
    transformSession: null,
    editPoints: false,
    history: [],
    historyIndex: -1,
  };

  const el = Object.fromEntries([
    "region-list", "region-count", "region-search", "add-region-button",
    "canvas-viewport", "canvas-stage", "editor-svg", "board-image",
    "region-overlay", "draft-overlay", "empty-state", "draw-instruction",
    "status-text", "zoom-label", "opacity-slider", "inspector-title",
    "inspector-empty", "inspector-form", "region-key-input",
    "region-type-select", "region-shape-select", "region-path-style-select", "region-mode-select", "region-notes-input",
    "point-count", "area-value", "image-file-input", "regions-file-input",
    "load-image-button", "load-regions-button", "undo-button", "redo-button",
    "export-button", "corrections-button", "delete-button", "duplicate-button", "edit-points-button",
    "zoom-out-button", "zoom-in-button", "fit-button", "new-shape-select",
    "tension-field", "curve-tension-slider", "curve-tension-value",
  ].map((id) => [id, document.getElementById(id)]));

  const svgNS = "http://www.w3.org/2000/svg";

  function clone(value) { return JSON.parse(JSON.stringify(value)); }

  function setStatus(message) { el["status-text"].textContent = message; }

  function colorFor(region) { return TYPE_COLORS[region.type] || TYPE_COLORS.edge; }

  function pathFor(points, style = "straight", tension = 0.8) {
    if (!points?.length) return "";
    if (style === "smooth" && points.length >= 3) return smoothClosedPath(points, tension);
    return `M ${points.map(([x, y]) => `${round(x)} ${round(y)}`).join(" L ")} Z`;
  }

  function smoothClosedPath(points, tension = 0.8) {
    const count = points.length;
    const tangentScale = clamp(Number(tension) || 0.8, 0.1, 1.4) / 6;
    let result = `M ${round(points[0][0])} ${round(points[0][1])}`;
    for (let index = 0; index < count; index += 1) {
      const previous = points[(index - 1 + count) % count];
      const current = points[index];
      const next = points[(index + 1) % count];
      const afterNext = points[(index + 2) % count];
      const controlOne = [current[0] + (next[0] - previous[0]) * tangentScale, current[1] + (next[1] - previous[1]) * tangentScale];
      const controlTwo = [next[0] - (afterNext[0] - current[0]) * tangentScale, next[1] - (afterNext[1] - current[1]) * tangentScale];
      result += ` C ${round(controlOne[0])} ${round(controlOne[1])}, ${round(controlTwo[0])} ${round(controlTwo[1])}, ${round(next[0])} ${round(next[1])}`;
    }
    return `${result} Z`;
  }

  function round(value, digits = 2) {
    const factor = 10 ** digits;
    return Math.round(value * factor) / factor;
  }

  function polygonArea(points) {
    if (!points || points.length < 3) return 0;
    let sum = 0;
    for (let i = 0; i < points.length; i += 1) {
      const [x1, y1] = points[i];
      const [x2, y2] = points[(i + 1) % points.length];
      sum += x1 * y2 - x2 * y1;
    }
    return Math.abs(sum / 2);
  }

  function centroid(points) {
    if (!points?.length) return [0, 0];
    const sum = points.reduce(([sx, sy], [x, y]) => [sx + x, sy + y], [0, 0]);
    return [sum[0] / points.length, sum[1] / points.length];
  }

  function bounds(points) {
    const xs = points.map((point) => point[0]);
    const ys = points.map((point) => point[1]);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)].map((v) => round(v));
  }

  function selectedRegion() {
    return state.regions.find((region) => region.id === state.selectedId) || null;
  }

  function normalizeRegion(region, fallbackId) {
    const id = Number(region.id ?? fallbackId);
    const contour = (region.contour || region.points || []).map(([x, y]) => [Number(x), Number(y)]);
    return {
      ...clone(region),
      id,
      key: region.key || `grip-${String(id).padStart(3, "0")}`,
      type: region.type || "edge",
      contour,
      metadata: {
        mode: region.metadata?.mode || region.mode || (region.type === "pocket" ? "aperture" : "surface"),
        shapeKind: region.metadata?.shapeKind || "freeform",
        pathStyle: region.metadata?.pathStyle || "straight",
        curveTension: Number(region.metadata?.curveTension ?? 0.8),
        humanNotes: region.metadata?.humanNotes || "",
        ...clone(region.metadata || {}),
      },
    };
  }

  function makeSvg(tag, attributes = {}) {
    const node = document.createElementNS(svgNS, tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
    return node;
  }

  function render() {
    renderOverlay();
    renderRegionList();
    renderInspector();
    renderTransform();
    renderHistoryControls();
  }

  function renderOverlay() {
    el["region-overlay"].replaceChildren();
    el["draft-overlay"].replaceChildren();

    if (state.overlayMode !== "none") {
      state.regions.forEach((region) => {
        if (state.overlayMode === "selected" && region.id !== state.selectedId) return;
        const group = makeSvg("g", { "data-region-id": region.id });
        const path = makeSvg("path", {
          d: pathFor(region.contour, region.metadata.pathStyle, region.metadata.curveTension),
          fill: colorFor(region),
          "fill-opacity": region.id === state.selectedId ? Math.min(state.opacity + 0.14, 0.8) : state.opacity,
          stroke: colorFor(region),
          "stroke-width": region.id === state.selectedId ? 2.2 : 1.2,
          class: `region-shape${region.id === state.selectedId ? " selected" : ""}`,
        });
        path.addEventListener("pointerdown", (event) => startRegionDrag(event, region.id));
        path.addEventListener("dblclick", (event) => insertPointOnNearestEdge(event, region.id));
        group.appendChild(path);

        const [cx, cy] = centroid(region.contour);
        const label = makeSvg("text", { x: cx, y: cy, class: "region-label" });
        label.textContent = region.id;
        group.appendChild(label);

        if (region.id === state.selectedId) {
          renderObjectControls(group, region);
          if (state.editPoints) {
            region.contour.forEach(([x, y], index) => {
              const handle = makeSvg("circle", { cx: x, cy: y, r: 4.5 / Math.max(state.zoom, 0.3), class: "vertex-handle" });
              handle.addEventListener("pointerdown", (event) => startHandleDrag(event, region.id, index));
              group.appendChild(handle);
            });
          }
        }
        el["region-overlay"].appendChild(group);
      });
    }

    if (state.drawing && state.draft.length) {
      const draftStyle = state.drawShape === "curved-freeform" ? "smooth" : "straight";
      const draft = makeSvg("path", { d: pathFor(state.draft, draftStyle, 0.8), class: "draft-line" });
      el["draft-overlay"].appendChild(draft);
      state.draft.forEach(([x, y]) => {
        el["draft-overlay"].appendChild(makeSvg("circle", { cx: x, cy: y, r: 4.5 / Math.max(state.zoom, 0.3), class: "vertex-handle" }));
      });
    }
  }

  function renderRegionList() {
    const query = el["region-search"].value.trim().toLowerCase();
    el["region-list"].replaceChildren();
    state.regions
      .filter((region) => !query || `${region.id} ${region.key} ${region.type}`.toLowerCase().includes(query))
      .sort((a, b) => a.id - b.id)
      .forEach((region) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = `region-item${region.id === state.selectedId ? " selected" : ""}`;
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", region.id === state.selectedId ? "true" : "false");
        item.innerHTML = `<i class="dot ${escapeHTML(region.type)}"></i><span class="region-id">${region.id}</span><span class="region-key">${escapeHTML(region.key)}</span><span class="region-type">${escapeHTML(region.type)}</span>`;
        item.addEventListener("click", () => selectRegion(region.id));
        el["region-list"].appendChild(item);
      });
    el["region-count"].textContent = state.regions.length;
  }

  function renderInspector() {
    const region = selectedRegion();
    el["inspector-title"].textContent = region ? `Region ${region.id}` : "No selection";
    el["inspector-empty"].classList.toggle("hidden", Boolean(region));
    el["inspector-form"].classList.toggle("hidden", !region);
    if (!region) return;
    if (document.activeElement !== el["region-key-input"]) el["region-key-input"].value = region.key;
    if (document.activeElement !== el["region-type-select"]) el["region-type-select"].value = region.type;
    if (document.activeElement !== el["region-shape-select"]) el["region-shape-select"].value = region.metadata.shapeKind || "freeform";
    if (document.activeElement !== el["region-path-style-select"]) el["region-path-style-select"].value = region.metadata.pathStyle || "straight";
    const tensionPercent = Math.round((region.metadata.curveTension ?? 0.8) * 100);
    if (document.activeElement !== el["curve-tension-slider"]) el["curve-tension-slider"].value = tensionPercent;
    el["curve-tension-value"].value = `${tensionPercent}%`;
    el["tension-field"].classList.toggle("hidden", region.metadata.pathStyle !== "smooth");
    if (document.activeElement !== el["region-mode-select"]) el["region-mode-select"].value = region.metadata.mode || "surface";
    if (document.activeElement !== el["region-notes-input"]) el["region-notes-input"].value = region.metadata.humanNotes || "";
    el["point-count"].textContent = region.contour.length;
    el["area-value"].textContent = `${Math.round(polygonArea(region.contour)).toLocaleString()} px²`;
    el["edit-points-button"].classList.toggle("edit-points-active", state.editPoints);
    el["edit-points-button"].textContent = state.editPoints ? "Finish points" : "Edit points";
  }

  function renderObjectControls(group, region) {
    const frame = orientedFrame(region);
    const pointText = frame.corners.map(([x, y]) => `${round(x)},${round(y)}`).join(" ");
    group.appendChild(makeSvg("polygon", { points: pointText, class: "transform-frame" }));
    const handleOffset = 28 / Math.max(state.zoom, 0.3);
    const top = localToWorld([frame.centerLocalX, frame.minY], frame.center, frame.rotation);
    const rotatePoint = localToWorld([frame.centerLocalX, frame.minY - handleOffset], frame.center, frame.rotation);
    group.appendChild(makeSvg("line", { x1: top[0], y1: top[1], x2: rotatePoint[0], y2: rotatePoint[1], class: "transform-stem" }));
    const rotateHandle = makeSvg("circle", { cx: rotatePoint[0], cy: rotatePoint[1], r: 6 / Math.max(state.zoom, 0.3), class: "transform-handle", "aria-label": "Rotate region" });
    rotateHandle.addEventListener("pointerdown", (event) => startTransformDrag(event, region.id, "rotate"));
    group.appendChild(rotateHandle);

    const bendPoint = localToWorld([frame.centerLocalX, frame.minY + Math.min((frame.maxY - frame.minY) * 0.3, 14 / Math.max(state.zoom, 0.3))], frame.center, frame.rotation);
    const bendSize = 6 / Math.max(state.zoom, 0.3);
    const bendHandle = makeSvg("rect", { x: bendPoint[0] - bendSize, y: bendPoint[1] - bendSize, width: bendSize * 2, height: bendSize * 2, rx: 1.5, class: "transform-handle bend-handle", transform: `rotate(45 ${bendPoint[0]} ${bendPoint[1]})`, "aria-label": "Bend region" });
    bendHandle.addEventListener("pointerdown", (event) => startTransformDrag(event, region.id, "bend"));
    group.appendChild(bendHandle);
  }

  function orientedFrame(region) {
    const center = centroid(region.contour);
    const rotation = Number(region.metadata.rotation || 0);
    const local = region.contour.map((point) => worldToLocal(point, center, rotation));
    const [minX, minY, maxX, maxY] = bounds(local);
    return {
      center,
      rotation,
      minX,
      minY,
      maxX,
      maxY,
      centerLocalX: (minX + maxX) / 2,
      corners: [[minX, minY], [maxX, minY], [maxX, maxY], [minX, maxY]].map((point) => localToWorld(point, center, rotation)),
    };
  }

  function localToWorld([x, y], [cx, cy], rotation) {
    const cosine = Math.cos(rotation);
    const sine = Math.sin(rotation);
    return [cx + x * cosine - y * sine, cy + x * sine + y * cosine];
  }

  function worldToLocal([x, y], [cx, cy], rotation) {
    const dx = x - cx;
    const dy = y - cy;
    const cosine = Math.cos(rotation);
    const sine = Math.sin(rotation);
    return [dx * cosine + dy * sine, -dx * sine + dy * cosine];
  }

  function renderTransform() {
    el["canvas-stage"].style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom})`;
    el["zoom-label"].textContent = `${Math.round(state.zoom * 100)}%`;
  }

  function renderHistoryControls() {
    el["undo-button"].disabled = state.historyIndex <= 0;
    el["redo-button"].disabled = state.historyIndex >= state.history.length - 1;
  }

  function selectRegion(id) {
    if (id !== state.selectedId) state.editPoints = false;
    state.selectedId = id;
    render();
    const region = selectedRegion();
    if (region) setStatus(`Selected ${region.key}. Drag the shape or its control points.`);
  }

  function clientToSvg(clientX, clientY) {
    const point = el["editor-svg"].createSVGPoint();
    point.x = clientX;
    point.y = clientY;
    const transformed = point.matrixTransform(el["editor-svg"].getScreenCTM().inverse());
    return [clamp(transformed.x, 0, state.canvas.width), clamp(transformed.y, 0, state.canvas.height)];
  }

  function clamp(value, min, max) { return Math.min(max, Math.max(min, value)); }

  function startRegionDrag(event, id) {
    if (state.drawing || state.spacePressed || event.button !== 0) return;
    event.stopPropagation();
    selectRegion(id);
    const region = selectedRegion();
    const start = clientToSvg(event.clientX, event.clientY);
    state.dragSession = { pointerId: event.pointerId, start, original: clone(region.contour), changed: false };
    el["editor-svg"].setPointerCapture(event.pointerId);
  }

  function startHandleDrag(event, id, index) {
    if (event.button !== 0) return;
    event.stopPropagation();
    selectRegion(id);
    state.handleSession = { pointerId: event.pointerId, index, changed: false };
    el["editor-svg"].setPointerCapture(event.pointerId);
  }

  function startTransformDrag(event, id, kind) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    selectRegion(id);
    const region = selectedRegion();
    const center = centroid(region.contour);
    const start = clientToSvg(event.clientX, event.clientY);
    state.transformSession = {
      pointerId: event.pointerId,
      kind,
      start,
      center,
      original: clone(region.contour),
      rotation: Number(region.metadata.rotation || 0),
      bend: Number(region.metadata.bend || 0),
      changed: false,
    };
    el["editor-svg"].setPointerCapture(event.pointerId);
  }

  function onSvgPointerMove(event) {
    if (state.transformSession?.pointerId === event.pointerId) {
      const session = state.transformSession;
      const current = clientToSvg(event.clientX, event.clientY);
      const region = selectedRegion();
      if (session.kind === "rotate") {
        const startAngle = Math.atan2(session.start[1] - session.center[1], session.start[0] - session.center[0]);
        const currentAngle = Math.atan2(current[1] - session.center[1], current[0] - session.center[0]);
        const delta = currentAngle - startAngle;
        region.contour = session.original.map((point) => rotatePoint(point, session.center, delta));
        region.metadata.rotation = session.rotation + delta;
      } else {
        const dx = current[0] - session.start[0];
        const dy = current[1] - session.start[1];
        const localDeltaY = -Math.sin(session.rotation) * dx + Math.cos(session.rotation) * dy;
        const localPoints = session.original.map((point) => worldToLocal(point, session.center, session.rotation));
        const [minX, , maxX] = bounds(localPoints);
        const width = Math.max(maxX - minX, 1);
        region.contour = localPoints.map(([x, y]) => {
          const progress = clamp((x - minX) / width, 0, 1);
          const influence = 4 * progress * (1 - progress);
          return localToWorld([x, y + localDeltaY * influence], session.center, session.rotation);
        });
        region.metadata.bend = session.bend + localDeltaY;
      }
      session.changed = true;
      renderOverlay();
      renderInspector();
      return;
    }
    if (state.dragSession?.pointerId === event.pointerId) {
      const current = clientToSvg(event.clientX, event.clientY);
      const [sx, sy] = state.dragSession.start;
      const dx = current[0] - sx;
      const dy = current[1] - sy;
      const region = selectedRegion();
      region.contour = state.dragSession.original.map(([x, y]) => [clamp(x + dx, 0, state.canvas.width), clamp(y + dy, 0, state.canvas.height)]);
      state.dragSession.changed = true;
      renderOverlay();
      renderInspector();
      return;
    }
    if (state.handleSession?.pointerId === event.pointerId) {
      const region = selectedRegion();
      region.contour[state.handleSession.index] = clientToSvg(event.clientX, event.clientY);
      state.handleSession.changed = true;
      renderOverlay();
      renderInspector();
    }
  }

  function onSvgPointerUp(event) {
    if (state.transformSession?.pointerId === event.pointerId) {
      if (state.transformSession.changed) commitHistory(state.transformSession.kind === "rotate" ? "Rotated region" : "Bent region");
      state.transformSession = null;
      render();
    }
    if (state.dragSession?.pointerId === event.pointerId) {
      if (state.dragSession.changed) commitHistory("Moved region");
      state.dragSession = null;
      render();
    }
    if (state.handleSession?.pointerId === event.pointerId) {
      if (state.handleSession.changed) commitHistory("Moved control point");
      state.handleSession = null;
      render();
    }
  }

  function rotatePoint([x, y], [cx, cy], angle) {
    const dx = x - cx;
    const dy = y - cy;
    const cosine = Math.cos(angle);
    const sine = Math.sin(angle);
    return [cx + dx * cosine - dy * sine, cy + dx * sine + dy * cosine];
  }

  function insertPointOnNearestEdge(event, id) {
    event.preventDefault();
    event.stopPropagation();
    selectRegion(id);
    const point = clientToSvg(event.clientX, event.clientY);
    const region = selectedRegion();
    let bestIndex = 0;
    let bestDistance = Infinity;
    for (let i = 0; i < region.contour.length; i += 1) {
      const distance = distanceToSegment(point, region.contour[i], region.contour[(i + 1) % region.contour.length]);
      if (distance < bestDistance) {
        bestDistance = distance;
        bestIndex = i + 1;
      }
    }
    region.contour.splice(bestIndex, 0, point);
    commitHistory("Added control point");
    render();
  }

  function distanceToSegment([px, py], [x1, y1], [x2, y2]) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    if (dx === 0 && dy === 0) return Math.hypot(px - x1, py - y1);
    const t = clamp(((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy), 0, 1);
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
  }

  function beginDraw() {
    state.drawing = true;
    state.drawShape = el["new-shape-select"].value;
    state.draft = [];
    state.primitiveSession = null;
    state.selectedId = null;
    el["draw-instruction"].classList.add("visible");
    el["draw-instruction"].textContent = ["freeform", "curved-freeform"].includes(state.drawShape)
      ? "Click around the hold. Press Enter to finish or Escape to cancel."
      : `Drag to create a ${shapeLabel(state.drawShape).toLowerCase()}. Press Escape to cancel.`;
    setStatus(`Creating a ${shapeLabel(state.drawShape).toLowerCase()} region.`);
    render();
  }

  function finishDraw() {
    if (!state.drawing || state.draft.length < 3) return;
    const nextId = state.regions.reduce((max, region) => Math.max(max, region.id), 0) + 1;
    const isCurved = state.drawShape === "curved-freeform";
    const region = normalizeRegion({
      id: nextId,
      key: `grip-${String(nextId).padStart(3, "0")}`,
      type: "edge",
      contour: state.draft,
      metadata: {
        mode: "surface",
        shapeKind: "freeform",
        pathStyle: isCurved ? "smooth" : "straight",
        curveTension: 0.8,
        humanNotes: "Added manually",
      },
    }, nextId);
    state.regions.push(region);
    state.drawing = false;
    state.draft = [];
    state.primitiveSession = null;
    state.selectedId = nextId;
    el["draw-instruction"].classList.remove("visible");
    commitHistory("Added region");
    setStatus(`Added ${region.key}.`);
    render();
  }

  function cancelDraw() {
    state.drawing = false;
    state.draft = [];
    state.primitiveSession = null;
    el["draw-instruction"].classList.remove("visible");
    setStatus("Drawing cancelled.");
    render();
  }

  function deleteSelected() {
    if (state.selectedId == null) return;
    const region = selectedRegion();
    state.regions = state.regions.filter((item) => item.id !== state.selectedId);
    state.selectedId = null;
    commitHistory("Deleted region");
    setStatus(`Deleted ${region.key}. Undo is available.`);
    render();
  }

  function duplicateSelected() {
    const source = selectedRegion();
    if (!source) return;
    const nextId = state.regions.reduce((max, region) => Math.max(max, region.id), 0) + 1;
    const copy = clone(source);
    copy.id = nextId;
    copy.key = `grip-${String(nextId).padStart(3, "0")}`;
    copy.contour = copy.contour.map(([x, y]) => [clamp(x + 10, 0, state.canvas.width), clamp(y + 10, 0, state.canvas.height)]);
    copy.metadata.humanNotes = "Duplicated manually";
    state.regions.push(copy);
    state.selectedId = nextId;
    commitHistory("Duplicated region");
    render();
  }

  function commitHistory(label) {
    const snapshot = JSON.stringify(state.regions);
    if (state.history[state.historyIndex]?.snapshot === snapshot) return;
    state.history = state.history.slice(0, state.historyIndex + 1);
    state.history.push({ snapshot, label });
    state.historyIndex = state.history.length - 1;
    renderHistoryControls();
  }

  function resetHistory() {
    state.history = [{ snapshot: JSON.stringify(state.regions), label: "Loaded regions" }];
    state.historyIndex = 0;
  }

  function undo() {
    if (state.historyIndex <= 0) return;
    state.historyIndex -= 1;
    state.regions = JSON.parse(state.history[state.historyIndex].snapshot);
    state.selectedId = state.regions.some((region) => region.id === state.selectedId) ? state.selectedId : null;
    setStatus(`Undo: ${state.history[state.historyIndex + 1].label}`);
    render();
  }

  function redo() {
    if (state.historyIndex >= state.history.length - 1) return;
    state.historyIndex += 1;
    state.regions = JSON.parse(state.history[state.historyIndex].snapshot);
    setStatus(`Redo: ${state.history[state.historyIndex].label}`);
    render();
  }

  function fitCanvas() {
    const rect = el["canvas-viewport"].getBoundingClientRect();
    const padding = 50;
    state.zoom = Math.min((rect.width - padding * 2) / state.canvas.width, (rect.height - padding * 2) / state.canvas.height);
    state.zoom = clamp(state.zoom, 0.1, 5);
    state.panX = (rect.width - state.canvas.width * state.zoom) / 2;
    state.panY = (rect.height - state.canvas.height * state.zoom) / 2;
    renderTransform();
  }

  function setZoom(nextZoom, centerX = null, centerY = null) {
    const rect = el["canvas-viewport"].getBoundingClientRect();
    const x = centerX ?? rect.left + rect.width / 2;
    const y = centerY ?? rect.top + rect.height / 2;
    const localX = x - rect.left;
    const localY = y - rect.top;
    const sourceX = (localX - state.panX) / state.zoom;
    const sourceY = (localY - state.panY) / state.zoom;
    state.zoom = clamp(nextZoom, 0.1, 8);
    state.panX = localX - sourceX * state.zoom;
    state.panY = localY - sourceY * state.zoom;
    renderTransform();
  }

  function startPan(event) {
    if (!(event.button === 1 || state.spacePressed)) return false;
    event.preventDefault();
    state.panSession = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, panX: state.panX, panY: state.panY };
    el["canvas-viewport"].setPointerCapture(event.pointerId);
    el["canvas-viewport"].classList.add("panning");
    return true;
  }

  function onViewportPointerDown(event) {
    if (startPan(event)) return;
    if (state.drawing && event.button === 0) {
      if (["freeform", "curved-freeform"].includes(state.drawShape)) {
        state.draft.push(clientToSvg(event.clientX, event.clientY));
      } else {
        const start = clientToSvg(event.clientX, event.clientY);
        state.primitiveSession = { pointerId: event.pointerId, start };
        state.draft = shapeContour(state.drawShape, start, start);
        el["canvas-viewport"].setPointerCapture(event.pointerId);
      }
      renderOverlay();
      return;
    }
    if (event.target === el["editor-svg"] || event.target === el["board-image"]) selectRegion(null);
  }

  function onViewportPointerMove(event) {
    if (state.primitiveSession?.pointerId === event.pointerId) {
      const current = clientToSvg(event.clientX, event.clientY);
      state.draft = shapeContour(state.drawShape, state.primitiveSession.start, current);
      renderOverlay();
      return;
    }
    if (!state.panSession || state.panSession.pointerId !== event.pointerId) return;
    state.panX = state.panSession.panX + event.clientX - state.panSession.x;
    state.panY = state.panSession.panY + event.clientY - state.panSession.y;
    renderTransform();
  }

  function onViewportPointerUp(event) {
    if (state.primitiveSession?.pointerId === event.pointerId) {
      const current = clientToSvg(event.clientX, event.clientY);
      state.draft = shapeContour(state.drawShape, state.primitiveSession.start, current);
      const [x1, y1, x2, y2] = bounds(state.draft);
      state.primitiveSession = null;
      if (Math.abs(x2 - x1) >= 6 && Math.abs(y2 - y1) >= 6) finishDraw();
      else {
        state.draft = [];
        setStatus("Drag a larger area to create the shape.");
        renderOverlay();
      }
      return;
    }
    if (!state.panSession || state.panSession.pointerId !== event.pointerId) return;
    state.panSession = null;
    el["canvas-viewport"].classList.remove("panning");
  }

  async function loadDemo() {
    try {
      const [regionsResponse] = await Promise.all([fetch("demo/stage-2-regions.json", { cache: "no-store" })]);
      if (!regionsResponse.ok) throw new Error("Demo regions unavailable");
      const data = await regionsResponse.json();
      await setImageHref("demo/stage-1-auto-rgba.png", "Simulator Stage 1 demo");
      setRegions(data, "stage-2-regions.json");
      setStatus("Simulator demo loaded. Select a region to begin editing.");
    } catch (error) {
      setStatus("Load an image and region JSON to begin.");
      console.warn(error);
    }
  }

  async function setImageHref(href, name) {
    await new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => {
        state.imageHref = href;
        state.imageName = name;
        el["board-image"].setAttribute("href", href);
        if (!state.regions.length) state.canvas = { width: image.naturalWidth, height: image.naturalHeight };
        resolve();
      };
      image.onerror = reject;
      image.src = href;
    });
    configureSvg();
    el["empty-state"].classList.add("hidden");
  }

  function setRegions(data, name = "regions.json") {
    state.canvas = { width: Number(data.canvas?.width || state.canvas.width), height: Number(data.canvas?.height || state.canvas.height) };
    state.regions = (data.regions || []).map((region, index) => normalizeRegion(region, index + 1));
    state.baselineRegions = clone(state.regions);
    state.regionsName = name;
    state.selectedId = state.regions[0]?.id ?? null;
    resetHistory();
    configureSvg();
    render();
    requestAnimationFrame(fitCanvas);
  }

  function configureSvg() {
    el["editor-svg"].setAttribute("viewBox", `0 0 ${state.canvas.width} ${state.canvas.height}`);
    el["editor-svg"].setAttribute("width", state.canvas.width);
    el["editor-svg"].setAttribute("height", state.canvas.height);
    el["board-image"].setAttribute("width", state.canvas.width);
    el["board-image"].setAttribute("height", state.canvas.height);
  }

  function loadImageFile(file) {
    const reader = new FileReader();
    reader.onload = async () => {
      await setImageHref(reader.result, file.name);
      requestAnimationFrame(fitCanvas);
      setStatus(`Loaded ${file.name}.`);
      render();
    };
    reader.readAsDataURL(file);
  }

  function loadRegionsFile(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        setRegions(JSON.parse(reader.result), file.name);
        setStatus(`Loaded ${file.name} with ${state.regions.length} regions.`);
      } catch (error) {
        setStatus(`Could not read ${file.name}.`);
        console.error(error);
      }
    };
    reader.readAsText(file);
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

  function exportEditedRegions() {
    const payload = {
      schemaVersion: 1,
      canvas: clone(state.canvas),
      labelEncoding: "uint16-region-id",
      source: { image: state.imageName, regions: state.regionsName },
      editor: { name: "hold-highlight-editor", exportedAt: new Date().toISOString() },
      regions: state.regions.sort((a, b) => a.id - b.id).map(regionForExport),
    };
    downloadJson(payload, "stage-2-regions.edited.json");
    setStatus(`Exported ${payload.regions.length} edited regions.`);
  }

  function exportCorrections() {
    const baselineById = new Map(state.baselineRegions.map((region) => [region.id, region]));
    const currentById = new Map(state.regions.map((region) => [region.id, region]));
    const added = state.regions.filter((region) => !baselineById.has(region.id)).map(regionForExport);
    const deleted = state.baselineRegions.filter((region) => !currentById.has(region.id)).map((region) => ({ id: region.id, key: region.key }));
    const modified = state.regions
      .filter((region) => baselineById.has(region.id) && comparisonKey(region) !== comparisonKey(baselineById.get(region.id)))
      .map((region) => ({ before: regionForExport(baselineById.get(region.id)), after: regionForExport(region) }));
    const payload = {
      schemaVersion: 1,
      kind: "human-region-corrections",
      source: { image: state.imageName, regions: state.regionsName },
      exportedAt: new Date().toISOString(),
      summary: { added: added.length, modified: modified.length, deleted: deleted.length },
      added,
      modified,
      deleted,
    };
    downloadJson(payload, "stage-2-human-corrections.json");
    setStatus(`Exported corrections: ${added.length} added, ${modified.length} modified, ${deleted.length} deleted.`);
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

  function downloadJson(payload, filename) {
    const url = URL.createObjectURL(new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  function escapeHTML(value) {
    return String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
  }

  function updateSelected(mutator, label) {
    const region = selectedRegion();
    if (!region) return;
    mutator(region);
    commitHistory(label);
    render();
  }

  function shapeLabel(kind) {
    return ({ freeform: "Freeform", "curved-freeform": "Curved freeform", rectangle: "Rectangle", "rounded-rectangle": "Rounded rectangle", "arced-rectangle": "Arced rectangle", ellipse: "Ellipse", capsule: "Capsule" })[kind] || "Freeform";
  }

  function shapeContour(kind, start, end) {
    let [x1, y1] = start;
    let [x2, y2] = end;
    if (x1 > x2) [x1, x2] = [x2, x1];
    if (y1 > y2) [y1, y2] = [y2, y1];
    if (x2 - x1 < 0.5) x2 = x1 + 0.5;
    if (y2 - y1 < 0.5) y2 = y1 + 0.5;
    if (kind === "rectangle") return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]];
    if (kind === "ellipse") return ellipseContour(x1, y1, x2, y2, 32);
    if (kind === "capsule") return roundedRectContour(x1, y1, x2, y2, Math.min(x2 - x1, y2 - y1) / 2, 7);
    if (kind === "rounded-rectangle") return roundedRectContour(x1, y1, x2, y2, Math.min(x2 - x1, y2 - y1) * 0.26, 6);
    if (kind === "arced-rectangle") return arcedRectangleContour(x1, y1, x2, y2);
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]];
  }

  function arcedRectangleContour(x1, y1, x2, y2, curveSteps = 24, capSteps = 8) {
    const width = x2 - x1;
    const height = y2 - y1;
    const halfThickness = Math.min(height * 0.27, width * 0.12);
    const bend = Math.min(height * 0.22, width * 0.08);
    const centerY = (y1 + y2) / 2;
    const start = [x1 + halfThickness, centerY + bend];
    const control = [(x1 + x2) / 2, centerY - bend];
    const end = [x2 - halfThickness, centerY + bend];

    const sample = (progress) => {
      const inverse = 1 - progress;
      const point = [
        inverse * inverse * start[0] + 2 * inverse * progress * control[0] + progress * progress * end[0],
        inverse * inverse * start[1] + 2 * inverse * progress * control[1] + progress * progress * end[1],
      ];
      const derivative = [
        2 * inverse * (control[0] - start[0]) + 2 * progress * (end[0] - control[0]),
        2 * inverse * (control[1] - start[1]) + 2 * progress * (end[1] - control[1]),
      ];
      const length = Math.hypot(...derivative) || 1;
      return { point, tangent: [derivative[0] / length, derivative[1] / length], normal: [-derivative[1] / length, derivative[0] / length] };
    };

    const samples = Array.from({ length: curveSteps + 1 }, (_, index) => sample(index / curveSteps));
    const top = samples.map(({ point, normal }) => [point[0] - normal[0] * halfThickness, point[1] - normal[1] * halfThickness]);
    const bottom = samples.map(({ point, normal }) => [point[0] + normal[0] * halfThickness, point[1] + normal[1] * halfThickness]);
    const right = samples.at(-1);
    const left = samples[0];
    const rightCap = Array.from({ length: capSteps - 1 }, (_, index) => {
      const angle = ((index + 1) / capSteps) * Math.PI;
      return [
        right.point[0] + halfThickness * (-right.normal[0] * Math.cos(angle) + right.tangent[0] * Math.sin(angle)),
        right.point[1] + halfThickness * (-right.normal[1] * Math.cos(angle) + right.tangent[1] * Math.sin(angle)),
      ];
    });
    const leftCap = Array.from({ length: capSteps - 1 }, (_, index) => {
      const angle = ((index + 1) / capSteps) * Math.PI;
      return [
        left.point[0] + halfThickness * (left.normal[0] * Math.cos(angle) - left.tangent[0] * Math.sin(angle)),
        left.point[1] + halfThickness * (left.normal[1] * Math.cos(angle) - left.tangent[1] * Math.sin(angle)),
      ];
    });
    return [...top, ...rightCap, ...bottom.reverse(), ...leftCap].map(([x, y]) => [round(x), round(y)]);
  }

  function ellipseContour(x1, y1, x2, y2, count) {
    const cx = (x1 + x2) / 2;
    const cy = (y1 + y2) / 2;
    const rx = (x2 - x1) / 2;
    const ry = (y2 - y1) / 2;
    return Array.from({ length: count }, (_, index) => {
      const angle = -Math.PI / 2 + (index / count) * Math.PI * 2;
      return [cx + Math.cos(angle) * rx, cy + Math.sin(angle) * ry];
    });
  }

  function roundedRectContour(x1, y1, x2, y2, radius, steps) {
    const r = Math.max(0, Math.min(radius, (x2 - x1) / 2, (y2 - y1) / 2));
    const corners = [
      [x2 - r, y1 + r, -Math.PI / 2, 0],
      [x2 - r, y2 - r, 0, Math.PI / 2],
      [x1 + r, y2 - r, Math.PI / 2, Math.PI],
      [x1 + r, y1 + r, Math.PI, Math.PI * 1.5],
    ];
    return corners.flatMap(([cx, cy, startAngle, endAngle]) => Array.from({ length: steps }, (_, index) => {
      const angle = startAngle + ((endAngle - startAngle) * index) / (steps - 1);
      return [cx + Math.cos(angle) * r, cy + Math.sin(angle) * r];
    }));
  }

  function convertSelectedShape(kind) {
    const region = selectedRegion();
    if (!region) return;
    if (kind !== "freeform") {
      const [x1, y1, x2, y2] = bounds(region.contour);
      region.contour = shapeContour(kind, [x1, y1], [x2, y2]);
    }
    region.metadata.shapeKind = kind;
    region.metadata.rotation = 0;
    region.metadata.bend = 0;
    commitHistory(`Converted to ${shapeLabel(kind)}`);
    setStatus(`${region.key} converted to ${shapeLabel(kind).toLowerCase()}.`);
    render();
  }

  el["load-image-button"].addEventListener("click", () => el["image-file-input"].click());
  el["load-regions-button"].addEventListener("click", () => el["regions-file-input"].click());
  el["image-file-input"].addEventListener("change", (event) => event.target.files[0] && loadImageFile(event.target.files[0]));
  el["regions-file-input"].addEventListener("change", (event) => event.target.files[0] && loadRegionsFile(event.target.files[0]));
  el["region-search"].addEventListener("input", renderRegionList);
  el["add-region-button"].addEventListener("click", beginDraw);
  el["undo-button"].addEventListener("click", undo);
  el["redo-button"].addEventListener("click", redo);
  el["delete-button"].addEventListener("click", deleteSelected);
  el["duplicate-button"].addEventListener("click", duplicateSelected);
  el["edit-points-button"].addEventListener("click", () => {
    state.editPoints = !state.editPoints;
    setStatus(state.editPoints ? "Point editing enabled." : "Object controls enabled.");
    render();
  });
  el["export-button"].addEventListener("click", exportEditedRegions);
  el["corrections-button"].addEventListener("click", exportCorrections);
  el["fit-button"].addEventListener("click", fitCanvas);
  el["zoom-in-button"].addEventListener("click", () => setZoom(state.zoom * 1.2));
  el["zoom-out-button"].addEventListener("click", () => setZoom(state.zoom / 1.2));
  el["opacity-slider"].addEventListener("input", (event) => { state.opacity = Number(event.target.value) / 100; renderOverlay(); });
  el["region-key-input"].addEventListener("change", (event) => updateSelected((region) => { region.key = event.target.value.trim() || region.key; }, "Renamed region"));
  el["region-type-select"].addEventListener("change", (event) => updateSelected((region) => { region.type = event.target.value; }, "Changed grip type"));
  el["region-shape-select"].addEventListener("change", (event) => convertSelectedShape(event.target.value));
  el["region-path-style-select"].addEventListener("change", (event) => updateSelected((region) => { region.metadata.pathStyle = event.target.value; }, "Changed path style"));
  el["curve-tension-slider"].addEventListener("input", (event) => {
    const region = selectedRegion();
    if (!region) return;
    region.metadata.curveTension = Number(event.target.value) / 100;
    el["curve-tension-value"].value = `${event.target.value}%`;
    renderOverlay();
  });
  el["curve-tension-slider"].addEventListener("change", () => {
    if (!selectedRegion()) return;
    commitHistory("Changed curve tension");
    render();
  });
  el["region-mode-select"].addEventListener("change", (event) => updateSelected((region) => { region.metadata.mode = event.target.value; }, "Changed interaction mode"));
  el["region-notes-input"].addEventListener("change", (event) => updateSelected((region) => { region.metadata.humanNotes = event.target.value; }, "Updated review notes"));

  document.querySelectorAll("[data-overlay]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-overlay]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.overlayMode = button.dataset.overlay;
      renderOverlay();
    });
  });

  el["editor-svg"].addEventListener("pointermove", onSvgPointerMove);
  el["editor-svg"].addEventListener("pointerup", onSvgPointerUp);
  el["editor-svg"].addEventListener("pointercancel", onSvgPointerUp);
  el["canvas-viewport"].addEventListener("pointerdown", onViewportPointerDown);
  el["canvas-viewport"].addEventListener("pointermove", onViewportPointerMove);
  el["canvas-viewport"].addEventListener("pointerup", onViewportPointerUp);
  el["canvas-viewport"].addEventListener("pointercancel", onViewportPointerUp);
  el["canvas-viewport"].addEventListener("wheel", (event) => {
    event.preventDefault();
    setZoom(state.zoom * Math.exp(-event.deltaY * 0.0012), event.clientX, event.clientY);
  }, { passive: false });

  el["canvas-viewport"].addEventListener("dragover", (event) => event.preventDefault());
  el["canvas-viewport"].addEventListener("drop", (event) => {
    event.preventDefault();
    [...event.dataTransfer.files].forEach((file) => {
      if (file.type.startsWith("image/")) loadImageFile(file);
      else if (file.name.endsWith(".json")) loadRegionsFile(file);
    });
  });

  window.addEventListener("resize", () => state.imageHref && fitCanvas());
  window.addEventListener("keydown", (event) => {
    const editingText = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
    if (event.code === "Space" && !editingText) { state.spacePressed = true; event.preventDefault(); }
    if (editingText) return;
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "z") {
      event.preventDefault();
      event.shiftKey ? redo() : undo();
    } else if (event.key === "Delete" || event.key === "Backspace") {
      event.preventDefault();
      deleteSelected();
    } else if (event.key === "Enter" && state.drawing) {
      finishDraw();
    } else if (event.key === "Escape" && state.drawing) {
      cancelDraw();
    }
  });
  window.addEventListener("keyup", (event) => { if (event.code === "Space") state.spacePressed = false; });

  configureSvg();
  resetHistory();
  render();
  loadDemo();
})();
