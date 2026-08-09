(() => {
  "use strict";

  const {
    buildEditedDocument,
    buildCorrectionsDocument,
    resizeContour,
    simplifyClosedContour,
    mirrorContour,
    findStrongestEdge,
    resolveHistorySelection,
    normalizePipelineDocument,
  } = globalThis.HoldEditorModel;

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
    serverSession: null,
    serverSessions: [],
    selectedRunId: null,
    loadingSession: false,
    dirty: false,
    saving: false,
    savedSnapshot: "[]",
    saveError: "",
    hasSaved: false,
    mirrorOntoSourceId: null,
    snapEnabled: false,
    imagePixels: null,
  };

  const el = Object.fromEntries([
    "region-list", "region-count", "region-search", "add-region-button",
    "canvas-viewport", "canvas-stage", "editor-svg", "board-image",
    "region-overlay", "draft-overlay", "empty-state", "draw-instruction",
    "status-text", "zoom-label", "opacity-slider", "inspector-title",
    "inspector-empty", "inspector-form", "region-key-input",
    "region-type-select", "region-shape-select", "region-path-style-select", "region-mode-select", "region-notes-input",
    "point-count", "area-value", "image-file-input", "regions-file-input",
    "load-image-button", "load-regions-button", "snap-button", "undo-button", "redo-button", "save-button", "save-state",
    "export-button", "corrections-button", "delete-button", "duplicate-button", "edit-points-button", "simplify-curve-button",
    "mirror-copy-button", "mirror-onto-button", "previous-region-button", "next-region-button",
    "zoom-out-button", "zoom-in-button", "fit-button", "new-shape-select",
    "tension-field", "curve-tension-slider", "curve-tension-value", "static-load-controls",
    "board-picker", "board-picker-separator", "board-select",
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
    renderSaveState();
    renderToolState();
  }

  function renderToolState() {
    el["snap-button"].disabled = !state.imagePixels;
    el["snap-button"].classList.toggle("active", state.snapEnabled);
    el["snap-button"].textContent = state.snapEnabled ? "Snap edges: on" : "Snap edges";
    el["mirror-onto-button"].classList.toggle("active", state.mirrorOntoSourceId != null);
  }

  function renderSaveState() {
    const canSave = Boolean(state.serverSession && state.regions.length && state.dirty && !state.saving && !state.loadingSession);
    el["save-button"].disabled = !canSave;
    el["board-select"].disabled = state.loadingSession || state.saving;
    el["save-state"].className = "save-state";
    if (!state.serverSession) {
      el["save-state"].textContent = "Static mode";
      el["save-button"].title = "Start server.py with --run-dir to save into an onboarding run";
    } else if (state.saveError) {
      el["save-state"].textContent = "Save failed";
      el["save-state"].classList.add("error");
      el["save-button"].title = state.saveError;
    } else if (state.saving) {
      el["save-state"].textContent = "Saving…";
    } else if (state.dirty) {
      el["save-state"].textContent = "Unsaved changes";
      el["save-state"].classList.add("dirty");
      el["save-button"].title = `Save into ${state.serverSession.runName}`;
    } else if (state.hasSaved) {
      el["save-state"].textContent = "Saved";
      el["save-state"].classList.add("saved");
      el["save-button"].title = `Saved in ${state.serverSession.runName}`;
    } else {
      el["save-state"].textContent = "Ready";
      el["save-button"].title = `Editing ${state.serverSession.runName}`;
    }
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
        item.dataset.regionId = region.id;
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
    el["inspector-title"].textContent = region ? `Hold ${region.id}` : "No selection";
    el["inspector-empty"].classList.toggle("hidden", Boolean(region));
    el["inspector-form"].classList.toggle("hidden", !region);
    if (!region) {
      el["inspector-empty"].textContent = "Select a hold highlight to edit its shape and details.";
      return;
    }
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
    el["simplify-curve-button"].disabled = region.contour.length < 6;
    el["previous-region-button"].disabled = state.regions.length < 2;
    el["next-region-button"].disabled = state.regions.length < 2;
  }

  function renderObjectControls(group, region) {
    const frame = orientedFrame(region);
    const pointText = frame.corners.map(([x, y]) => `${round(x)},${round(y)}`).join(" ");
    group.appendChild(makeSvg("polygon", { points: pointText, class: "transform-frame" }));
    const resizePositions = {
      nw: [frame.minX, frame.minY],
      n: [frame.centerLocalX, frame.minY],
      ne: [frame.maxX, frame.minY],
      e: [frame.maxX, frame.centerLocalY],
      se: [frame.maxX, frame.maxY],
      s: [frame.centerLocalX, frame.maxY],
      sw: [frame.minX, frame.maxY],
      w: [frame.minX, frame.centerLocalY],
    };
    Object.entries(resizePositions).forEach(([handleName, localPoint]) => {
      const [x, y] = localToWorld(localPoint, frame.center, frame.rotation);
      const corner = handleName.length === 2;
      const horizontalSide = handleName === "n" || handleName === "s";
      const width = (corner ? 9 : horizontalSide ? 14 : 6) / Math.max(state.zoom, 0.3);
      const height = (corner ? 9 : horizontalSide ? 6 : 14) / Math.max(state.zoom, 0.3);
      const handle = makeSvg("rect", {
        x: x - width / 2,
        y: y - height / 2,
        width,
        height,
        rx: 1.5,
        class: "resize-handle",
        "data-resize-handle": handleName,
        transform: `rotate(${round(frame.rotation * 180 / Math.PI)} ${x} ${y})`,
        "aria-label": `Resize ${handleName}`,
      });
      handle.addEventListener("pointerdown", (event) => startResizeDrag(event, region.id, handleName));
      group.appendChild(handle);
    });
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
      centerLocalY: (minY + maxY) / 2,
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
    if (id != null && state.mirrorOntoSourceId != null && id !== state.mirrorOntoSourceId) {
      completeMirrorOnto(id);
      return;
    }
    if (id !== state.selectedId) state.editPoints = false;
    state.selectedId = id;
    render();
    const region = selectedRegion();
    if (region) setStatus(`Selected hold ${region.key}. Drag the highlight or its control points.`);
    requestAnimationFrame(() => document.querySelector(`.region-item[data-region-id="${id}"]`)?.scrollIntoView({ block: "nearest" }));
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

  function startResizeDrag(event, id, handle) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    selectRegion(id);
    const region = selectedRegion();
    state.transformSession = {
      pointerId: event.pointerId,
      kind: "resize",
      resizeHandle: handle,
      original: clone(region.contour),
      rotation: Number(region.metadata.rotation || 0),
      changed: false,
    };
    el["editor-svg"].setPointerCapture(event.pointerId);
  }

  function onSvgPointerMove(event) {
    if (state.transformSession?.pointerId === event.pointerId) {
      const session = state.transformSession;
      const current = clientToSvg(event.clientX, event.clientY);
      const region = selectedRegion();
      if (session.kind === "resize") {
        const pointer = snapPoint(current, event.altKey);
        region.contour = resizeContour({
          points: session.original,
          rotation: session.rotation,
          handle: session.resizeHandle,
          pointer,
          preserveAspect: event.shiftKey,
        });
      } else if (session.kind === "rotate") {
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
      const pointer = clientToSvg(event.clientX, event.clientY);
      region.contour[state.handleSession.index] = snapPoint(pointer, event.altKey);
      state.handleSession.changed = true;
      renderOverlay();
      renderInspector();
    }
  }

  function onSvgPointerUp(event) {
    if (state.transformSession?.pointerId === event.pointerId) {
      if (state.transformSession.changed) {
        const labels = { rotate: "Rotated region", bend: "Bent region", resize: "Resized region" };
        commitHistory(labels[state.transformSession.kind]);
      }
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
    setStatus(`Creating a ${shapeLabel(state.drawShape).toLowerCase()} hold highlight.`);
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
    commitHistory("Added hold highlight");
    setStatus(`Added ${region.key} hold highlight.`);
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
    commitHistory("Deleted hold highlight");
    setStatus(`Deleted ${region.key} hold highlight. Undo is available.`);
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
    commitHistory("Duplicated hold highlight");
    setStatus(`Duplicated hold highlight ${copy.key}.`);
    render();
  }

  function simplifySelectedCurve() {
    const region = selectedRegion();
    if (!region || region.contour.length < 6) return;
    const before = region.contour.length;
    const tolerance = Math.max(1.5, Math.hypot(state.canvas.width, state.canvas.height) * 0.0025);
    const simplified = simplifyClosedContour(region.contour, tolerance);
    if (simplified.length >= before) {
      setStatus(`${region.key} already has a sparse hold highlight contour.`);
      return;
    }
    region.contour = simplified;
    region.metadata.shapeKind = "freeform";
    region.metadata.pathStyle = "smooth";
    commitHistory("Simplified curve");
    setStatus(`Simplified ${region.key} hold highlight from ${before} to ${simplified.length} controls.`);
    render();
  }

  function mirrorSelectedCopy() {
    const source = selectedRegion();
    if (!source) return;
    const nextId = state.regions.reduce((maximum, region) => Math.max(maximum, region.id), 0) + 1;
    const copy = clone(source);
    copy.id = nextId;
    copy.key = `grip-${String(nextId).padStart(3, "0")}`;
    copy.contour = mirrorContour(source.contour, state.canvas.width);
    copy.metadata.rotation = -Number(source.metadata.rotation || 0);
    copy.metadata.humanNotes = `Mirrored from ${source.key}`;
    state.regions.push(copy);
    state.selectedId = nextId;
    commitHistory("Mirrored hold highlight copy");
    setStatus(`Created mirrored hold highlight copy ${copy.key}.`);
    render();
  }

  function beginMirrorOnto() {
    const source = selectedRegion();
    if (!source) return;
    if (state.mirrorOntoSourceId === source.id) {
      state.mirrorOntoSourceId = null;
      setStatus("Mirror replacement cancelled.");
    } else {
      state.mirrorOntoSourceId = source.id;
      setStatus(`Mirror ${source.key} onto which target? Select another hold highlight.`);
    }
    renderToolState();
  }

  function completeMirrorOnto(targetId) {
    const source = state.regions.find((region) => region.id === state.mirrorOntoSourceId);
    const target = state.regions.find((region) => region.id === targetId);
    if (!source || !target) {
      state.mirrorOntoSourceId = null;
      return;
    }
    const geometryKeys = ["shapeKind", "pathStyle", "curveTension", "bend"];
    geometryKeys.forEach((key) => { target.metadata[key] = source.metadata[key]; });
    target.metadata.rotation = -Number(source.metadata.rotation || 0);
    target.contour = mirrorContour(source.contour, state.canvas.width);
    state.mirrorOntoSourceId = null;
    state.selectedId = targetId;
    commitHistory("Mirrored geometry onto hold highlight");
    setStatus(`Replaced ${target.key} hold highlight with mirrored geometry from ${source.key}.`);
    render();
  }

  function navigateRegion(direction) {
    if (!state.regions.length) return;
    const ordered = [...state.regions].sort((left, right) => left.id - right.id);
    const currentIndex = ordered.findIndex((region) => region.id === state.selectedId);
    const nextIndex = currentIndex < 0 ? 0 : (currentIndex + direction + ordered.length) % ordered.length;
    selectRegion(ordered[nextIndex].id);
  }

  function togglePointEditing() {
    state.editPoints = !state.editPoints;
    setStatus(state.editPoints ? "Point editing enabled." : "Object controls enabled.");
    render();
  }

  function commitHistory(label) {
    const snapshot = JSON.stringify(state.regions);
    if (state.history[state.historyIndex]?.snapshot === snapshot) return;
    state.history = state.history.slice(0, state.historyIndex + 1);
    state.history.push({ snapshot, label, selectedId: state.selectedId });
    state.historyIndex = state.history.length - 1;
    state.dirty = snapshot !== state.savedSnapshot;
    state.saveError = "";
    renderHistoryControls();
    renderSaveState();
  }

  function resetHistory() {
    state.history = [{ snapshot: JSON.stringify(state.regions), label: "Loaded hold highlights", selectedId: state.selectedId }];
    state.historyIndex = 0;
    state.savedSnapshot = state.history[0].snapshot;
    state.dirty = false;
    state.saveError = "";
    state.hasSaved = false;
  }

  function undo() {
    if (state.historyIndex <= 0) return;
    state.historyIndex -= 1;
    const entry = state.history[state.historyIndex];
    state.regions = JSON.parse(entry.snapshot);
    state.selectedId = resolveHistorySelection(entry, state.regions, state.selectedId);
    state.dirty = JSON.stringify(state.regions) !== state.savedSnapshot;
    state.saveError = "";
    setStatus(`Undo: ${state.history[state.historyIndex + 1].label}`);
    render();
  }

  function redo() {
    if (state.historyIndex >= state.history.length - 1) return;
    state.historyIndex += 1;
    const entry = state.history[state.historyIndex];
    state.regions = JSON.parse(entry.snapshot);
    state.selectedId = resolveHistorySelection(entry, state.regions, state.selectedId);
    state.dirty = JSON.stringify(state.regions) !== state.savedSnapshot;
    state.saveError = "";
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
        setStatus("Drag a larger area to create the hold highlight.");
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
      setStatus("Simulator demo loaded. Select a hold highlight to begin editing.");
    } catch (error) {
      setStatus("Load an image and hold highlight JSON to begin.");
      console.warn(error);
    }
  }

  function showBoardPicker(visible) {
    el["board-picker"].classList.toggle("hidden", !visible);
    el["board-picker-separator"].classList.toggle("hidden", !visible);
  }

  function showStaticLoadControls(visible) {
    el["static-load-controls"].classList.toggle("hidden", !visible);
  }

  function populateBoardPicker(sessions) {
    el["board-select"].replaceChildren();
    sessions.forEach((session) => {
      const option = document.createElement("option");
      option.value = session.id;
      option.textContent = session.label;
      el["board-select"].appendChild(option);
    });
    showBoardPicker(sessions.length > 0);
  }

  async function loadServerSession(runId) {
    const previousRunId = state.selectedRunId;
    state.loadingSession = true;
    renderSaveState();
    try {
      const sessionUrl = `/api/session?run=${encodeURIComponent(runId)}`;
      const sessionResponse = await fetch(sessionUrl, { cache: "no-store" });
      if (!sessionResponse.ok || !sessionResponse.headers.get("content-type")?.includes("application/json")) return false;
      const session = await sessionResponse.json();
      if (!session.ok) return false;
      const regionsResponse = await fetch(session.regionsUrl, { cache: "no-store" });
      if (!regionsResponse.ok) throw new Error("Could not load Stage 2 regions from the run");
      const regions = await regionsResponse.json();
      await setImageHref(session.imageUrl, session.imagePath || "stage-1-auto-rgba.png");
      state.serverSession = session;
      state.selectedRunId = session.id;
      state.drawing = false;
      state.draft = [];
      state.primitiveSession = null;
      state.editPoints = false;
      state.mirrorOntoSourceId = null;
      setRegions(regions, session.regionsPath || "stage-2-regions.json");
      showStaticLoadControls(false);
      el["board-select"].value = session.id;
      setStatus(`Loaded ${session.label}. Edit the hold highlights and save changes into this generated run.`);
      return true;
    } catch (error) {
      console.warn(error);
      if (previousRunId) el["board-select"].value = previousRunId;
      setStatus(`Could not switch boards: ${error.message || error}`);
      return false;
    } finally {
      state.loadingSession = false;
      renderSaveState();
    }
  }

  async function switchServerSession(runId) {
    if (!runId || runId === state.selectedRunId || state.loadingSession) return;
    if (state.dirty && !window.confirm("Discard unsaved changes and switch boards?")) {
      el["board-select"].value = state.selectedRunId;
      return;
    }
    await loadServerSession(runId);
  }

  async function loadServerCatalog() {
    try {
      const response = await fetch("/api/sessions", { cache: "no-store" });
      if (!response.ok || !response.headers.get("content-type")?.includes("application/json")) return false;
      const catalog = await response.json();
      if (!catalog.ok || !catalog.sessions?.length) return false;
      state.serverSessions = catalog.sessions;
      populateBoardPicker(catalog.sessions);
      return await loadServerSession(catalog.sessions[0].id);
    } catch (error) {
      console.warn(error);
      return false;
    }
  }

  async function loadInitialSession() {
    if (await loadServerCatalog()) return;
    showStaticLoadControls(true);
    showBoardPicker(false);
    await loadDemo();
  }

  async function setImageHref(href, name) {
    await new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => {
        state.imageHref = href;
        state.imageName = name;
        el["board-image"].setAttribute("href", href);
        captureImagePixels(image);
        if (!state.regions.length) state.canvas = { width: image.naturalWidth, height: image.naturalHeight };
        resolve();
      };
      image.onerror = reject;
      image.src = href;
    });
    configureSvg();
    el["empty-state"].classList.add("hidden");
  }

  function captureImagePixels(image) {
    try {
      const canvas = document.createElement("canvas");
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      context.drawImage(image, 0, 0);
      state.imagePixels = {
        rgba: context.getImageData(0, 0, canvas.width, canvas.height).data,
        width: canvas.width,
        height: canvas.height,
      };
    } catch (error) {
      state.imagePixels = null;
      state.snapEnabled = false;
      console.warn("Edge snapping unavailable for this image", error);
    }
    renderToolState();
  }

  function snapPoint(point, bypass = false) {
    if (!state.snapEnabled || bypass || !state.imagePixels) return point;
    const scaleX = state.imagePixels.width / state.canvas.width;
    const scaleY = state.imagePixels.height / state.canvas.height;
    const imagePoint = [point[0] * scaleX, point[1] * scaleY];
    const canvasRadius = Math.max(4, Math.round(Math.hypot(state.canvas.width, state.canvas.height) * 0.008));
    const imageRadius = canvasRadius * Math.max(scaleX, scaleY);
    const snapped = findStrongestEdge({
      ...state.imagePixels,
      point: imagePoint,
      radius: imageRadius,
      threshold: 24,
    });
    return snapped ? [snapped[0] / scaleX, snapped[1] / scaleY] : point;
  }

  function toggleEdgeSnapping() {
    if (!state.imagePixels) {
      setStatus("Edge snapping is unavailable for this image.");
      return;
    }
    state.snapEnabled = !state.snapEnabled;
    setStatus(state.snapEnabled ? "Edge snapping enabled. Hold Alt to bypass it." : "Edge snapping disabled.");
    renderToolState();
  }

  function setRegions(data, name = "regions.json") {
    const normalized = normalizePipelineDocument(data, state.canvas);
    state.canvas = normalized.canvas;
    state.regions = normalized.regions;
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
    state.serverSession = null;
    state.selectedRunId = null;
    showBoardPicker(false);
    showStaticLoadControls(true);
    renderSaveState();
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
    state.serverSession = null;
    state.selectedRunId = null;
    showBoardPicker(false);
    showStaticLoadControls(true);
    renderSaveState();
    const reader = new FileReader();
    reader.onload = () => {
      try {
        setRegions(JSON.parse(reader.result), file.name);
        setStatus(`Loaded ${file.name} with ${state.regions.length} hold highlights.`);
      } catch (error) {
        setStatus(`Could not read ${file.name}.`);
        console.error(error);
      }
    };
    reader.readAsText(file);
  }

  function editedDocument() {
    return buildEditedDocument({
      canvas: state.canvas,
      regions: state.regions,
      imageName: state.imageName,
      regionsName: state.regionsName,
    });
  }

  function correctionsDocument() {
    return buildCorrectionsDocument({
      baselineRegions: state.baselineRegions,
      regions: state.regions,
      imageName: state.imageName,
      regionsName: state.regionsName,
    });
  }

  function exportEditedRegions() {
    const payload = editedDocument();
    downloadJson(payload, "stage-2-regions.edited.json");
    setStatus(`Exported ${payload.regions.length} edited regions.`);
  }

  function exportCorrections() {
    const payload = correctionsDocument();
    downloadJson(payload, "stage-2-human-corrections.json");
    setStatus(`Exported corrections: ${payload.summary.added} added, ${payload.summary.modified} modified, ${payload.summary.deleted} deleted.`);
  }

  async function saveToRun() {
    if (!state.serverSession || !state.dirty || state.saving) return;
    state.saving = true;
    state.saveError = "";
    renderSaveState();
    try {
      const response = await fetch(state.serverSession.saveUrl || "/api/save", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ regions: editedDocument(), corrections: correctionsDocument() }),
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || `Save failed (${response.status})`);
      state.savedSnapshot = JSON.stringify(state.regions);
      state.dirty = false;
      state.hasSaved = true;
      setStatus(`Saved edited hold highlights to ${result.regionsPath} and ${result.correctionsPath}.`);
    } catch (error) {
      state.saveError = error.message || "Save failed";
      setStatus(state.saveError);
    } finally {
      state.saving = false;
      renderSaveState();
    }
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
  el["board-select"].addEventListener("change", (event) => switchServerSession(event.target.value));
  el["load-regions-button"].addEventListener("click", () => el["regions-file-input"].click());
  el["image-file-input"].addEventListener("change", (event) => event.target.files[0] && loadImageFile(event.target.files[0]));
  el["regions-file-input"].addEventListener("change", (event) => event.target.files[0] && loadRegionsFile(event.target.files[0]));
  el["region-search"].addEventListener("input", renderRegionList);
  el["add-region-button"].addEventListener("click", beginDraw);
  el["undo-button"].addEventListener("click", undo);
  el["redo-button"].addEventListener("click", redo);
  el["delete-button"].addEventListener("click", deleteSelected);
  el["duplicate-button"].addEventListener("click", duplicateSelected);
  el["edit-points-button"].addEventListener("click", togglePointEditing);
  el["simplify-curve-button"].addEventListener("click", simplifySelectedCurve);
  el["mirror-copy-button"].addEventListener("click", mirrorSelectedCopy);
  el["mirror-onto-button"].addEventListener("click", beginMirrorOnto);
  el["previous-region-button"].addEventListener("click", () => navigateRegion(-1));
  el["next-region-button"].addEventListener("click", () => navigateRegion(1));
  el["snap-button"].addEventListener("click", toggleEdgeSnapping);
  el["export-button"].addEventListener("click", exportEditedRegions);
  el["corrections-button"].addEventListener("click", exportCorrections);
  el["save-button"].addEventListener("click", saveToRun);
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
    } else if (event.key === "Escape" && state.mirrorOntoSourceId != null) {
      state.mirrorOntoSourceId = null;
      setStatus("Mirror replacement cancelled.");
      renderToolState();
    } else if (event.key === "[") {
      navigateRegion(-1);
    } else if (event.key === "]") {
      navigateRegion(1);
    } else if (event.key.toLowerCase() === "m") {
      mirrorSelectedCopy();
    } else if (event.key.toLowerCase() === "e") {
      togglePointEditing();
    } else if (event.key.toLowerCase() === "s") {
      toggleEdgeSnapping();
    }
  });
  window.addEventListener("keyup", (event) => { if (event.code === "Space") state.spacePressed = false; });
  window.addEventListener("beforeunload", (event) => {
    if (!state.dirty) return;
    event.preventDefault();
    event.returnValue = "";
  });

  configureSvg();
  resetHistory();
  render();
  loadInitialSession();
})();
