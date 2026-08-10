(() => {
  "use strict";

  const {
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
  } = globalThis.HoldEditorModel;
  const workbenchClient = globalThis.HoldWorkbenchClient;
  const { timelineFor, canApprove, openingSections } = globalThis.HoldWorkbenchModel;
  const {
    TOOL_IDS,
    createSuiteState,
    selectTool: selectSuiteTool,
  } = globalThis.HoldWorkbenchSuiteModel;
  const { createToolSuiteController } = globalThis.HoldWorkbenchSuiteController;
  const { createPromotionController, renderPromotionView } = globalThis.HoldPromotionView;
  const {
    parseDisplayPath,
    serializeDisplayPath,
    transformPath,
    bendPath,
    mirrorPath,
    treatPathCorner,
    isExplicitClosingCommand,
    explicitClosingCommandChecker,
    movePathEndpoint,
  } = globalThis.HoldVectorPathModel;
  const {
    createLatestLoadCoordinator,
    createOpeningBoardController,
    openingScreenState,
    renderOpeningFormVisibility,
    renderRepositoryDiagnostics,
    renderOpeningBoardList,
    openingActionsDisabled,
    handleOpeningSelectionFailure,
    createAutosaveCoordinator,
    createDraftStore,
    checkpointImageUrl,
    checkpointComparisonUrl,
    validateEditableImageAlignment,
    createActiveJobStore,
    reconcileActiveJobs,
    restoreOpeningAfterJobRecovery,
    clearMatchingAcceptedJob,
    clearConfirmedTerminalJob,
    isRecoverableJobError,
    geometryValidationError,
    runFrozenApproval,
  } = globalThis.HoldWorkbenchController;

  const STAGE_LABELS = [
    "Input",
    "Source review",
    "Cleanup review",
    "Hold-contour refinement",
    "Smoothing",
    "Vector refinement",
    "Save",
  ];
  const PIPELINE_TO_TIMELINE_STAGE = [1, 2, 3, 5, 6];
  const EDITOR_STAGES = new Set([2, 3]);
  const AUTOSAVE_DELAY_MS = 500;
  const loadCoordinator = createLatestLoadCoordinator();
  const draftStore = createDraftStore(localStorage);
  const activeJobStore = createActiveJobStore(localStorage);
  const openingBoardController = createOpeningBoardController({
    listLibraryBoards: () => workbenchClient.listLibraryBoards(),
    listBoards: () => workbenchClient.listBoards(),
    openLibraryBoard: (boardId) => runTrackedJob((options) => workbenchClient.openLibraryBoard(boardId, options)),
    getBoard: (boardId) => workbenchClient.getBoard(boardId),
  });
  const autosaveCoordinator = createAutosaveCoordinator({
    save: (entry) => runTrackedJob((options) => workbenchClient.saveDraft(
      entry.view, entry.document, options,
    )),
    onStart: handleAutosaveStart,
    onSuccess: handleAutosaveSuccess,
    onError: handleAutosaveError,
  });
  let suiteController = null;
  let promotionController = null;

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
    selectedCornerIndex: null,
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
    guided: false,
    boards: [],
    libraryBoards: [],
    libraryDiagnostics: [],
    openingErrors: { library: "", runtime: "" },
    board: null,
    editorMode: "contour",
    checkpointDocument: null,
    compareEnabled: false,
    validationErrors: [],
    busy: false,
    editingFrozen: false,
    autosaveTimer: null,
    draftStatus: "clean",
    nextRegionId: 1,
    suiteState: createSuiteState(),
  };

  const el = Object.fromEntries([
    "region-list", "region-count", "region-search", "add-region-button",
    "canvas-viewport", "canvas-stage", "editor-svg", "board-image",
    "annotated-review", "annotated-review-image",
    "compare-overlay", "region-overlay", "draft-overlay", "empty-state", "draw-instruction",
    "status-text", "zoom-label", "opacity-slider", "inspector-title",
    "inspector-empty", "inspector-form", "region-key-input",
    "region-type-select", "region-shape-select", "region-path-style-select", "region-mode-select", "region-notes-input",
    "point-count", "area-value", "image-file-input", "regions-file-input",
    "load-image-button", "load-regions-button", "snap-button", "undo-button", "redo-button", "save-button", "save-state",
    "export-button", "corrections-button", "delete-button", "duplicate-button", "edit-points-button", "simplify-curve-button",
    "mirror-copy-button", "mirror-onto-button", "previous-region-button", "next-region-button",
    "zoom-out-button", "zoom-in-button", "fit-button", "new-shape-select",
    "tension-field", "curve-tension-slider", "curve-tension-value",
    "corner-treatment-field", "corner-number", "corner-treatment-select", "corner-amount-input",
    "board-picker", "board-picker-separator", "board-select", "compare-button", "retry-button", "revise-button",
    "setup-screen", "workbench-screen", "create-board-form", "setup-product-field", "setup-product-input", "setup-url-input", "setup-upload-input",
    "setup-url-field", "setup-upload-field", "setup-error", "setup-submit-button", "repository-board-list", "repository-diagnostics", "in-progress-board-list",
    "workflow-block", "recent-block", "inventory-block", "stage-timeline", "recent-runs", "new-board-button",
    "board-title", "board-state", "checkpoint-title", "validation-panel", "validation-list", "legacy-controls",
    "onboard-view", "inspect-view", "promote-view", "validate-view", "tool-suite-sidebar",
    "tool-onboard", "tool-inspect", "tool-promote", "tool-validate",
    "active-board-card", "active-board-name", "active-board-revision", "active-board-readiness",
    "inspect-board-preview", "inspect-artifact-links", "inspect-hold-inventory", "inspect-approval-status", "inspect-readiness", "inspect-next-action",
  ].map((id) => [id, document.getElementById(id)]));

  const svgNS = "http://www.w3.org/2000/svg";

  function clone(value) { return JSON.parse(JSON.stringify(value)); }

  function setStatus(message) { el["status-text"].textContent = message; }

  function colorFor(region) { return TYPE_COLORS[region.type] || TYPE_COLORS.edge; }

  function isVectorMode() { return state.editorMode === "vector"; }

  function vectorPoints(region, includeHandles = true) {
    try {
      return parseDisplayPath(region.displayPath).flatMap((command) => {
        if (command.type === "Z") return [];
        const points = [[command.x, command.y]];
        if (includeHandles && command.type === "Q") points.push([command.x1, command.y1]);
        if (includeHandles && command.type === "C") points.push([command.x1, command.y1], [command.x2, command.y2]);
        return points;
      });
    } catch (_error) {
      return [];
    }
  }

  function geometryPoints(region, includeHandles = true) {
    return isVectorMode() ? vectorPoints(region, includeHandles) : region.contour;
  }

  function regionPath(region) {
    if (isVectorMode()) return region.displayPath || "";
    try {
      return contourPath(region.contour, region.metadata.pathStyle, region.metadata.curveTension, region.metadata.cornerTreatments || {});
    } catch (_error) {
      try {
        return pathFor(region.contour);
      } catch (_fallbackError) {
        return "";
      }
    }
  }

  function pathFor(points, style = "straight", tension = 0.8) {
    if (!points?.length) return "";
    if (points.length < 3) return `M ${points.map(([x, y]) => `${round(x)} ${round(y)}`).join(" L ")}`;
    return contourPath(points, style, tension, {});
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
    renderSuite();
    renderComparisonView();
    renderOverlay();
    renderRegionList();
    renderInspector();
    renderTransform();
    renderHistoryControls();
    renderSaveState();
    renderToolState();
    renderValidation();
  }

  function appendInspectText(container, text, className = "") {
    const item = document.createElement("p");
    if (className) item.className = className;
    item.textContent = text;
    container.appendChild(item);
    return item;
  }

  function renderInspectView(suite) {
    const board = suite.activeBoard;
    el["inspect-board-preview"].replaceChildren();
    el["inspect-artifact-links"].replaceChildren();
    el["inspect-hold-inventory"].replaceChildren();
    el["inspect-approval-status"].replaceChildren();
    el["inspect-readiness"].replaceChildren();
    if (!board) {
      appendInspectText(el["inspect-board-preview"], "Choose a board to inspect its package.");
      appendInspectText(el["inspect-artifact-links"], "Stage 4 artifacts will appear for the selected revision.");
      appendInspectText(el["inspect-hold-inventory"], "No board is active.");
      appendInspectText(el["inspect-approval-status"], "No active revision.");
    } else {
      const previewUrl = board.normalArtifactUrl || board.editorImageUrl || board.reviewUrl;
      if (previewUrl) {
        const image = document.createElement("img");
        image.src = previewUrl;
        image.alt = `Board preview for ${board.productName || board.boardId}`;
        el["inspect-board-preview"].appendChild(image);
      } else {
        appendInspectText(el["inspect-board-preview"], "A board preview is not available for this revision.");
      }
      [
        [board.normalArtifactUrl, "Stage 4 normal artifact"],
        [board.reviewUrl, "Stage 4 highlighted artifact"],
      ].forEach(([url, label]) => {
        if (!url) return;
        const link = document.createElement("a");
        link.href = url;
        link.target = "_blank";
        link.rel = "noreferrer";
        link.textContent = label;
        el["inspect-artifact-links"].appendChild(link);
      });
      if (!el["inspect-artifact-links"].childElementCount) {
        appendInspectText(el["inspect-artifact-links"], "Stage 4 artifacts are not available for this revision.");
      }
      const count = Number.isInteger(board.holdCount) ? board.holdCount : null;
      appendInspectText(
        el["inspect-hold-inventory"],
        count != null ? `${String(count)} hold${count === 1 ? "" : "s"} in the loaded inventory.` : "Hold inventory is available in the Stage 4 artifacts.",
      );
      appendInspectText(el["inspect-approval-status"], `Revision ${board.revisionId} · ${String(board.state || "unknown").replaceAll("_", " ")}`);
    }
    appendInspectText(el["inspect-readiness"], `${suite.readiness.label}: continue with ${suite.readiness.nextTool}.`);
    el["inspect-next-action"].textContent = `Open ${suite.readiness.nextTool[0].toUpperCase()}${suite.readiness.nextTool.slice(1)}`;
    el["inspect-next-action"].disabled = !board;
  }

  function renderSuite() {
    const suite = state.suiteState;
    if (!suite) return;
    TOOL_IDS.forEach((toolId) => {
      const button = el[`tool-${toolId}`];
      const active = suite.activeTool === toolId;
      button.classList.toggle("active", active);
      button.setAttribute("aria-current", active ? "page" : "false");
      el[`${toolId}-view`].classList.toggle("hidden", !active);
    });
    const board = suite.activeBoard;
    el["active-board-name"].textContent = board?.productName || board?.boardId || "No board selected";
    el["active-board-revision"].textContent = board ? `Revision ${suite.activeRevision}` : "Choose a board to begin.";
    el["active-board-readiness"].textContent = suite.readiness.label;
    el["active-board-readiness"].className = `readiness-badge ${suite.readiness.status}`;
    renderInspectView(suite);
    if (promotionController) {
      renderPromotionView(el["promote-view"], {
        suite,
        promotion: promotionController.getState(),
      });
    }
  }

  function renderToolState() {
    const editable = canEditGeometry();
    const hasExportableContours = state.regions.length > 0
      && state.regions.every((region) => isExportableContour(region.contour));
    el["snap-button"].disabled = !state.imagePixels || isVectorMode() || !editable;
    el["snap-button"].classList.toggle("active", state.snapEnabled);
    el["snap-button"].textContent = state.snapEnabled ? "Snap edges: on" : "Snap edges";
    el["mirror-onto-button"].classList.toggle("active", state.mirrorOntoSourceId != null);
    el["add-region-button"].disabled = !editable || isVectorMode();
    el["delete-button"].disabled = !editable || isVectorMode();
    el["duplicate-button"].disabled = !editable || isVectorMode();
    el["mirror-copy-button"].disabled = !editable || isVectorMode();
    el["simplify-curve-button"].disabled = !editable || isVectorMode() || (selectedRegion()?.contour?.length || 0) < 6;
    el["region-shape-select"].disabled = !editable || isVectorMode();
    el["region-path-style-select"].disabled = !editable || isVectorMode();
    el["curve-tension-slider"].disabled = !editable || isVectorMode();
    el["region-type-select"].disabled = !editable || isVectorMode();
    el["region-key-input"].disabled = !editable || state.guided;
    el["region-mode-select"].disabled = !editable;
    el["region-notes-input"].disabled = !editable;
    el["edit-points-button"].disabled = !editable;
    el["mirror-onto-button"].disabled = !editable;
    el["compare-button"].classList.toggle("active", state.compareEnabled);
    el["compare-button"].setAttribute("aria-pressed", state.compareEnabled ? "true" : "false");
    el["export-button"].disabled = !hasExportableContours;
    el["corrections-button"].disabled = !hasExportableContours;
    el["canvas-viewport"].classList.toggle("static-checkpoint", !editable);
  }

  function renderSaveState() {
    if (state.guided) {
      const view = state.board;
      const complete = view?.state === "complete";
      const approving = Boolean(view && canApprove(view, {
        valid: state.validationErrors.length === 0,
        saving: state.draftStatus === "saving",
        errors: state.validationErrors,
      }));
      el["save-state"].className = "save-state";
      el["save-state"].textContent = state.saveError
        ? "Action failed"
        : state.busy
          ? "Working…"
          : state.draftStatus === "saving"
            ? "Saving draft…"
            : state.draftStatus === "dirty"
              ? "Draft pending"
              : state.draftStatus === "saved"
                ? "Draft saved"
                : complete && view?.saved
                  ? "Saved locally"
                  : "Up to date";
      if (state.saveError) el["save-state"].classList.add("error");
      else if (state.draftStatus === "dirty") el["save-state"].classList.add("dirty");
      else if (state.draftStatus === "saved" || view?.saved) el["save-state"].classList.add("saved");
      el["save-button"].textContent = complete ? (view.saved ? "Saved locally" : "Save locally") : "Approve & continue";
      el["save-button"].disabled = state.busy || !view || (complete ? view.saved : !approving);
      el["retry-button"].disabled = state.busy || !view || !["failed", "awaiting_review", "ready"].includes(view.state);
      el["revise-button"].disabled = state.busy || !view || view.stage < 1;
      return;
    }
    const canSave = canSaveEditorState(state);
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
    el["compare-overlay"].replaceChildren();
    el["region-overlay"].replaceChildren();
    el["draft-overlay"].replaceChildren();

    if (
      state.compareEnabled
      && !checkpointComparisonUrl(state.board)
      && state.overlayMode !== "none"
    ) {
      state.baselineRegions.forEach((region) => {
        const path = makeSvg("path", { d: regionPath(region), class: "compare-shape" });
        el["compare-overlay"].appendChild(path);
      });
    }

    if (state.overlayMode !== "none") {
      state.regions.forEach((region) => {
        if (state.overlayMode === "selected" && region.id !== state.selectedId) return;
        const group = makeSvg("g", { "data-region-id": region.id });
        const path = makeSvg("path", {
          d: regionPath(region),
          fill: colorFor(region),
          "fill-opacity": region.id === state.selectedId ? Math.min(state.opacity + 0.14, 0.8) : state.opacity,
          stroke: colorFor(region),
          "stroke-width": region.id === state.selectedId ? 2.2 : 1.2,
          class: `region-shape${region.id === state.selectedId ? " selected" : ""}`,
        });
        path.addEventListener("pointerdown", (event) => startRegionDrag(event, region.id));
        if (!isVectorMode()) path.addEventListener("dblclick", (event) => insertPointOnNearestEdge(event, region.id));
        group.appendChild(path);

        const [cx, cy] = Array.isArray(region.anchor) ? region.anchor : centroid(geometryPoints(region, false));
        const label = makeSvg("text", { x: cx, y: cy, class: "region-label" });
        label.textContent = region.id;
        group.appendChild(label);

        if (region.id === state.selectedId) {
          renderObjectControls(group, region);
          if (state.editPoints) {
            if (isVectorMode()) renderVectorHandles(group, region);
            else region.contour.forEach(([x, y], index) => {
                const selected = state.selectedCornerIndex === index;
                const handle = makeSvg("circle", { cx: x, cy: y, r: 4.5 / Math.max(state.zoom, 0.3), class: `vertex-handle${selected ? " selected-corner" : ""}` });
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

  function renderVectorHandles(group, region) {
    let commands;
    try {
      commands = parseDisplayPath(region.displayPath);
    } catch (_error) {
      return;
    }
    const isExplicitClosureAt = explicitClosingCommandChecker(commands);
    let previous = null;
    commands.forEach((command, commandIndex) => {
      if (command.type === "Z") {
        previous = null;
        return;
      }
      const endpoint = [command.x, command.y];
      const controls = [];
      if (command.type === "Q" || command.type === "C") controls.push([command.x1, command.y1, "control1"]);
      if (command.type === "C") controls.push([command.x2, command.y2, "control2"]);
      if (previous && controls.length) {
        group.appendChild(makeSvg("line", { x1: previous[0], y1: previous[1], x2: controls[0][0], y2: controls[0][1], class: "vector-control-line" }));
      }
      if (controls.length) {
        const last = controls.at(-1);
        group.appendChild(makeSvg("line", { x1: last[0], y1: last[1], x2: endpoint[0], y2: endpoint[1], class: "vector-control-line" }));
      }
      controls.forEach(([x, y, kind]) => {
        const handle = makeSvg("circle", { cx: x, cy: y, r: 4 / Math.max(state.zoom, 0.3), class: "vector-control-handle" });
        handle.addEventListener("pointerdown", (event) => startVectorHandleDrag(event, region.id, commandIndex, kind));
        group.appendChild(handle);
      });
      const isExplicitClosure = isExplicitClosureAt(commandIndex);
      if (!isExplicitClosure) {
        const selected = state.selectedCornerIndex === commandIndex;
        const handle = makeSvg("circle", { cx: endpoint[0], cy: endpoint[1], r: 4.5 / Math.max(state.zoom, 0.3), class: `vector-endpoint-handle${selected ? " selected-corner" : ""}` });
        handle.addEventListener("pointerdown", (event) => startVectorHandleDrag(event, region.id, commandIndex, "endpoint"));
        group.appendChild(handle);
      }
      previous = endpoint;
    });
  }

  function renderValidation() {
    el["validation-list"].replaceChildren();
    state.validationErrors.forEach((error) => {
      const item = document.createElement("li");
      if (error.regionId == null) {
        item.textContent = error.message;
      } else {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = error.message;
        button.addEventListener("click", () => focusRegion(error.regionId));
        item.appendChild(button);
      }
      el["validation-list"].appendChild(item);
    });
    el["validation-panel"].classList.toggle("hidden", state.validationErrors.length === 0);
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
    el["inspector-title"].textContent = region ? `Region ${region.id}` : "No selection";
    el["inspector-empty"].classList.toggle("hidden", Boolean(region));
    el["inspector-form"].classList.toggle("hidden", !region);
    if (!region) {
      el["corner-treatment-field"].classList.add("hidden");
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
    const cornerIndex = state.selectedCornerIndex;
    const cornerSelected = Number.isInteger(cornerIndex);
    const corner = cornerSelected ? region.metadata.cornerTreatments?.[cornerIndex] : null;
    el["corner-treatment-field"].classList.toggle("hidden", !cornerSelected);
    el["corner-treatment-select"].disabled = !cornerSelected;
    el["corner-amount-input"].disabled = !cornerSelected;
    if (cornerSelected) {
      el["corner-number"].textContent = String(cornerIndex + 1);
      if (document.activeElement !== el["corner-treatment-select"]) el["corner-treatment-select"].value = corner?.treatment || "sharp";
      if (document.activeElement !== el["corner-amount-input"]) el["corner-amount-input"].value = String(corner?.amount || 12);
    }
    if (document.activeElement !== el["region-mode-select"]) el["region-mode-select"].value = region.metadata.mode || "surface";
    if (document.activeElement !== el["region-notes-input"]) el["region-notes-input"].value = region.metadata.humanNotes || "";
    const points = geometryPoints(region);
    el["point-count"].textContent = points.length;
    const pointBounds = points.length ? bounds(points) : [0, 0, 0, 0];
    el["area-value"].textContent = isVectorMode()
      ? `${Math.round(Math.max(0, (pointBounds[2] - pointBounds[0]) * (pointBounds[3] - pointBounds[1]))).toLocaleString()} px² bounds`
      : `${Math.round(polygonArea(region.contour)).toLocaleString()} px²`;
    el["edit-points-button"].classList.toggle("edit-points-active", state.editPoints);
    el["edit-points-button"].textContent = state.editPoints ? "Finish points" : "Edit points";
    el["simplify-curve-button"].disabled = isVectorMode() || region.contour.length < 6;
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
    const points = geometryPoints(region);
    if (!points.length) return { center: [0, 0], rotation: 0, minX: 0, minY: 0, maxX: 0, maxY: 0, centerLocalX: 0, centerLocalY: 0, corners: [[0, 0], [0, 0], [0, 0], [0, 0]] };
    const center = centroid(points);
    const rotation = Number(region.metadata.rotation || 0);
    const local = points.map((point) => worldToLocal(point, center, rotation));
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
    el["undo-button"].disabled = !canEditGeometry() || state.historyIndex <= 0;
    el["redo-button"].disabled = !canEditGeometry() || state.historyIndex >= state.history.length - 1;
  }

  function selectRegion(id) {
    if (id != null && state.mirrorOntoSourceId != null && id !== state.mirrorOntoSourceId) {
      completeMirrorOnto(id);
      return;
    }
    if (id !== state.selectedId) {
      state.editPoints = false;
      state.selectedCornerIndex = null;
    }
    state.selectedId = id;
    render();
    const region = selectedRegion();
    if (region) setStatus(`Selected ${region.key}. Drag the shape or its control points.`);
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

  function canEditGeometry() {
    return !state.busy && !state.editingFrozen && (!state.guided || EDITOR_STAGES.has(state.board?.stage));
  }

  function allocateRegionId() {
    const identifier = nextStage2RegionId({
      baselineRegions: state.baselineRegions,
      regions: state.regions,
      nextRegionId: state.nextRegionId,
    });
    state.nextRegionId = identifier + 1;
    return identifier;
  }

  function startRegionDrag(event, id) {
    if (!canEditGeometry() || state.drawing || state.spacePressed || event.button !== 0) return;
    event.stopPropagation();
    selectRegion(id);
    const region = selectedRegion();
    const start = clientToSvg(event.clientX, event.clientY);
    state.dragSession = {
      pointerId: event.pointerId,
      start,
      original: isVectorMode() ? parseDisplayPath(region.displayPath) : clone(region.contour),
      originalAnchor: clone(region.anchor || centroid(geometryPoints(region, false))),
      changed: false,
    };
    el["editor-svg"].setPointerCapture(event.pointerId);
  }

  function startHandleDrag(event, id, index) {
    if (!canEditGeometry() || isVectorMode() || event.button !== 0) return;
    event.stopPropagation();
    selectRegion(id);
    state.selectedCornerIndex = index;
    state.handleSession = { pointerId: event.pointerId, index, changed: false };
    render();
    el["editor-svg"].setPointerCapture(event.pointerId);
  }

  function startVectorHandleDrag(event, id, commandIndex, handleKind) {
    if (!canEditGeometry() || !isVectorMode() || event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    selectRegion(id);
    if (handleKind === "endpoint") state.selectedCornerIndex = commandIndex;
    state.handleSession = { pointerId: event.pointerId, commandIndex, handleKind, changed: false };
    render();
    el["editor-svg"].setPointerCapture(event.pointerId);
  }

  function startTransformDrag(event, id, kind) {
    if (!canEditGeometry() || event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    selectRegion(id);
    const region = selectedRegion();
    const center = centroid(geometryPoints(region));
    const start = clientToSvg(event.clientX, event.clientY);
    state.transformSession = {
      pointerId: event.pointerId,
      kind,
      start,
      center,
      original: isVectorMode() ? parseDisplayPath(region.displayPath) : clone(region.contour),
      originalAnchor: clone(region.anchor || center),
      rotation: Number(region.metadata.rotation || 0),
      bend: Number(region.metadata.bend || 0),
      changed: false,
    };
    el["editor-svg"].setPointerCapture(event.pointerId);
  }

  function startResizeDrag(event, id, handle) {
    if (!canEditGeometry() || event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    selectRegion(id);
    const region = selectedRegion();
    state.transformSession = {
      pointerId: event.pointerId,
      kind: "resize",
      resizeHandle: handle,
      original: isVectorMode() ? parseDisplayPath(region.displayPath) : clone(region.contour),
      originalPoints: clone(geometryPoints(region)),
      originalAnchor: clone(region.anchor || centroid(geometryPoints(region, false))),
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
        if (isVectorMode()) resizeVectorRegion(region, session, pointer, event.shiftKey);
        else region.contour = resizeContour({
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
        if (isVectorMode()) {
          const cosine = Math.cos(delta);
          const sine = Math.sin(delta);
          applyVectorMatrix(region, session, [
            cosine,
            sine,
            -sine,
            cosine,
            session.center[0] - cosine * session.center[0] + sine * session.center[1],
            session.center[1] - sine * session.center[0] - cosine * session.center[1],
          ]);
        } else region.contour = session.original.map((point) => rotatePoint(point, session.center, delta));
        region.metadata.rotation = session.rotation + delta;
      } else {
        const dx = current[0] - session.start[0];
        const dy = current[1] - session.start[1];
        const localDeltaY = -Math.sin(session.rotation) * dx + Math.cos(session.rotation) * dy;
        if (isVectorMode()) {
          const originalPoints = session.original.flatMap((command) => command.type === "Z" ? [] : [[command.x, command.y]]);
          const originalBounds = bounds(originalPoints);
          region.displayPath = serializeDisplayPath(bendPath(session.original, localDeltaY, originalBounds));
          const [minX, , maxX] = originalBounds;
          const progress = clamp((session.originalAnchor[0] - minX) / Math.max(maxX - minX, 1), 0, 1);
          region.anchor = [session.originalAnchor[0], session.originalAnchor[1] + localDeltaY * 4 * progress * (1 - progress)];
        } else {
          const localPoints = session.original.map((point) => worldToLocal(point, session.center, session.rotation));
          const [minX, , maxX] = bounds(localPoints);
          const width = Math.max(maxX - minX, 1);
          region.contour = localPoints.map(([x, y]) => {
            const progress = clamp((x - minX) / width, 0, 1);
            const influence = 4 * progress * (1 - progress);
            return localToWorld([x, y + localDeltaY * influence], session.center, session.rotation);
          });
        }
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
      if (isVectorMode()) applyVectorMatrix(region, state.dragSession, [1, 0, 0, 1, dx, dy]);
      else region.contour = state.dragSession.original.map(([x, y]) => [clamp(x + dx, 0, state.canvas.width), clamp(y + dy, 0, state.canvas.height)]);
      state.dragSession.changed = true;
      renderOverlay();
      renderInspector();
      return;
    }
    if (state.handleSession?.pointerId === event.pointerId) {
      const region = selectedRegion();
      const pointer = clientToSvg(event.clientX, event.clientY);
      if (isVectorMode()) {
        const commands = parseDisplayPath(region.displayPath);
        const command = commands[state.handleSession.commandIndex];
        const [x, y] = pointer;
        if (state.handleSession.handleKind === "endpoint") {
          const moved = movePathEndpoint(
            commands, state.handleSession.commandIndex, [x, y],
          );
          const corner = region.metadata.cornerTreatments?.[state.handleSession.commandIndex];
          if (corner) {
            region.displayPath = serializeDisplayPath(treatPathCorner(
              moved,
              state.handleSession.commandIndex,
              corner.treatment,
              corner.amount,
            ));
          } else region.displayPath = serializeDisplayPath(moved);
        }
        else if (state.handleSession.handleKind === "control1") [command.x1, command.y1] = [x, y];
        else [command.x2, command.y2] = [x, y];
        if (state.handleSession.handleKind !== "endpoint") region.displayPath = serializeDisplayPath(commands);
      } else region.contour[state.handleSession.index] = snapPoint(pointer, event.altKey);
      state.handleSession.changed = true;
      renderOverlay();
      renderInspector();
    }
  }

  function applyVectorMatrix(region, session, matrix) {
    region.displayPath = serializeDisplayPath(transformPath(session.original, matrix));
    const [a, b, c, d, e, f] = matrix;
    const [x, y] = session.originalAnchor;
    region.anchor = [a * x + c * y + e, b * x + d * y + f];
  }

  function resizeVectorRegion(region, session, pointer, preserveAspect) {
    applyVectorMatrix(region, session, resizeTransform({
      points: session.originalPoints,
      rotation: session.rotation,
      handle: session.resizeHandle,
      pointer,
      preserveAspect,
    }));
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
    if (!canEditGeometry()) return;
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
    region.metadata.cornerTreatments = shiftCornerTreatmentsForInsertion(
      region.metadata.cornerTreatments || {}, bestIndex, region.contour.length - 1,
    );
    state.selectedCornerIndex = bestIndex;
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
    if (!canEditGeometry() || isVectorMode()) return;
    state.drawing = true;
    state.drawShape = el["new-shape-select"].value;
    state.draft = [];
    state.primitiveSession = null;
    state.selectedId = null;
    state.selectedCornerIndex = null;
    el["draw-instruction"].classList.add("visible");
    el["draw-instruction"].textContent = ["freeform", "curved-freeform"].includes(state.drawShape)
      ? "Click around the hold. Press Enter to finish or Escape to cancel."
      : `Drag to create a ${shapeLabel(state.drawShape).toLowerCase()}. Press Escape to cancel.`;
    setStatus(`Creating a ${shapeLabel(state.drawShape).toLowerCase()} region.`);
    render();
  }

  function finishDraw() {
    if (!canEditGeometry() || !state.drawing || state.draft.length < 3) return;
    const nextId = allocateRegionId();
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
    state.selectedCornerIndex = null;
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
    if (!canEditGeometry() || state.selectedId == null || isVectorMode()) return;
    const region = selectedRegion();
    state.regions = state.regions.filter((item) => item.id !== state.selectedId);
    state.selectedId = null;
    state.selectedCornerIndex = null;
    commitHistory("Deleted region");
    setStatus(`Deleted ${region.key}. Undo is available.`);
    render();
  }

  function duplicateSelected() {
    if (!canEditGeometry()) return;
    const source = selectedRegion();
    if (!source || isVectorMode()) return;
    const nextId = allocateRegionId();
    const copy = clone(source);
    copy.id = nextId;
    copy.key = `grip-${String(nextId).padStart(3, "0")}`;
    copy.contour = copy.contour.map(([x, y]) => [clamp(x + 10, 0, state.canvas.width), clamp(y + 10, 0, state.canvas.height)]);
    copy.metadata.humanNotes = "Duplicated manually";
    state.regions.push(copy);
    state.selectedId = nextId;
    state.selectedCornerIndex = null;
    commitHistory("Duplicated region");
    render();
  }

  function simplifySelectedCurve() {
    if (!canEditGeometry()) return;
    const region = selectedRegion();
    if (!region || isVectorMode() || region.contour.length < 6) return;
    const before = region.contour.length;
    const tolerance = Math.max(1.5, Math.hypot(state.canvas.width, state.canvas.height) * 0.0025);
    const simplified = simplifyClosedContour(region.contour, tolerance);
    if (simplified.length >= before) {
      setStatus(`${region.key} already has a sparse contour.`);
      return;
    }
    region.contour = simplified;
    delete region.metadata.cornerTreatments;
    state.selectedCornerIndex = null;
    region.metadata.shapeKind = "freeform";
    region.metadata.pathStyle = "smooth";
    commitHistory("Simplified curve");
    setStatus(`Simplified ${region.key} from ${before} to ${simplified.length} controls.`);
    render();
  }

  function mirrorSelectedCopy() {
    if (!canEditGeometry()) return;
    const source = selectedRegion();
    if (!source || isVectorMode()) return;
    const nextId = allocateRegionId();
    const copy = clone(source);
    copy.id = nextId;
    copy.key = `grip-${String(nextId).padStart(3, "0")}`;
    copy.contour = mirrorContour(source.contour, state.canvas.width);
    copy.metadata.cornerTreatments = mirrorCornerTreatments(source.metadata.cornerTreatments || {}, source.contour.length);
    copy.metadata.rotation = -Number(source.metadata.rotation || 0);
    copy.metadata.humanNotes = `Mirrored from ${source.key}`;
    state.regions.push(copy);
    state.selectedId = nextId;
    state.selectedCornerIndex = null;
    commitHistory("Mirrored region copy");
    setStatus(`Created mirrored copy ${copy.key}.`);
    render();
  }

  function beginMirrorOnto() {
    if (!canEditGeometry()) return;
    const source = selectedRegion();
    if (!source) return;
    if (state.mirrorOntoSourceId === source.id) {
      state.mirrorOntoSourceId = null;
      setStatus("Mirror replacement cancelled.");
    } else {
      state.mirrorOntoSourceId = source.id;
      setStatus(`Mirror ${source.key} onto which target? Select another region.`);
    }
    renderToolState();
  }

  function completeMirrorOnto(targetId) {
    if (!canEditGeometry()) return;
    const source = state.regions.find((region) => region.id === state.mirrorOntoSourceId);
    const target = state.regions.find((region) => region.id === targetId);
    if (!source || !target) {
      state.mirrorOntoSourceId = null;
      return;
    }
    const geometryKeys = ["shapeKind", "pathStyle", "curveTension", "bend", "cornerTreatments"];
    geometryKeys.forEach((key) => {
      if (source.metadata[key] === undefined) delete target.metadata[key];
      else target.metadata[key] = clone(source.metadata[key]);
    });
    target.metadata.rotation = -Number(source.metadata.rotation || 0);
    if (isVectorMode()) {
      target.displayPath = serializeDisplayPath(mirrorPath(parseDisplayPath(source.displayPath), state.canvas.width / 2));
      if (Array.isArray(source.anchor)) target.anchor = [state.canvas.width - source.anchor[0], source.anchor[1]];
    } else {
      target.contour = mirrorContour(source.contour, state.canvas.width);
      target.metadata.cornerTreatments = mirrorCornerTreatments(source.metadata.cornerTreatments || {}, source.contour.length);
    }
    state.mirrorOntoSourceId = null;
    state.selectedId = targetId;
    state.selectedCornerIndex = null;
    commitHistory("Mirrored geometry onto region");
    setStatus(`Replaced ${target.key} with mirrored geometry from ${source.key}.`);
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
    if (!canEditGeometry()) return;
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
    onDraftChanged();
    renderHistoryControls();
    renderSaveState();
  }

  function resetHistory() {
    state.history = [{ snapshot: JSON.stringify(state.regions), label: "Loaded regions", selectedId: state.selectedId }];
    state.historyIndex = 0;
    state.savedSnapshot = state.history[0].snapshot;
    state.dirty = false;
    state.saveError = "";
    state.hasSaved = false;
  }

  function undo() {
    if (!canEditGeometry() || state.historyIndex <= 0) return;
    state.historyIndex -= 1;
    const entry = state.history[state.historyIndex];
    state.regions = JSON.parse(entry.snapshot);
    const restoredId = resolveHistorySelection(entry, state.regions, state.selectedId);
    if (restoredId !== state.selectedId) state.selectedCornerIndex = null;
    state.selectedId = restoredId;
    state.dirty = JSON.stringify(state.regions) !== state.savedSnapshot;
    state.saveError = "";
    onDraftChanged();
    setStatus(`Undo: ${state.history[state.historyIndex + 1].label}`);
    render();
  }

  function redo() {
    if (!canEditGeometry() || state.historyIndex >= state.history.length - 1) return;
    state.historyIndex += 1;
    const entry = state.history[state.historyIndex];
    state.regions = JSON.parse(entry.snapshot);
    const restoredId = resolveHistorySelection(entry, state.regions, state.selectedId);
    if (restoredId !== state.selectedId) state.selectedCornerIndex = null;
    state.selectedId = restoredId;
    state.dirty = JSON.stringify(state.regions) !== state.savedSnapshot;
    state.saveError = "";
    onDraftChanged();
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

  function draftStorageKey(view = state.board) {
    return draftStore.keyFor(view);
  }

  function discardStaleDrafts(view) {
    try {
      draftStore.discardMismatched(view);
    } catch (error) {
      console.warn("Could not prune stale local drafts", error);
    }
  }

  function readStoredDraft(view) {
    discardStaleDrafts(view);
    try {
      return draftStore.read(view);
    } catch (error) {
      console.warn("Could not restore the local draft", error);
    }
    return null;
  }

  function serializeDraft() {
    if (!state.board || !EDITOR_STAGES.has(state.board.stage) || !state.checkpointDocument) return null;
    if (state.board.stage === 2) {
      const edited = buildEditedDocument({
        canvas: state.canvas,
        regions: state.regions,
        imageName: state.imageName,
        regionsName: state.regionsName,
      });
      return {
        ...clone(state.checkpointDocument),
        stage: 2,
        canvas: clone(state.canvas),
        labelEncoding: state.checkpointDocument.labelEncoding || "uint16-region-id",
        inventory: { nextRegionId: state.nextRegionId },
        regions: edited.regions,
      };
    }
    return {
      ...clone(state.checkpointDocument),
      stage: 3,
      canvas: clone(state.canvas),
      regions: clone(state.regions),
    };
  }

  function markDraftSaved(draftDocument = serializeDraft(), savedSnapshot = JSON.stringify(state.regions)) {
    if (!state.board || !draftDocument) return;
    state.savedSnapshot = savedSnapshot;
    state.dirty = JSON.stringify(state.regions) !== savedSnapshot;
    state.draftStatus = state.dirty ? "dirty" : "saved";
    try {
      const entry = {
        boardId: state.board.boardId,
        revisionId: state.board.revisionId,
        stage: state.board.stage,
        checkpointToken: state.board.checkpointToken,
        key: draftStorageKey(),
        generation: 0,
        document: draftDocument,
      };
      draftStore.writeDirty(entry);
      draftStore.markSaved(entry);
    } catch (error) {
      console.warn("Could not persist the local draft cache", error);
    }
    renderSaveState();
  }

  function persistCurrentDraft() {
    const draftDocument = serializeDraft();
    if (!state.board || !draftDocument) return null;
    const view = { ...state.board };
    const entry = autosaveCoordinator.update({
      boardId: view.boardId,
      revisionId: view.revisionId,
      stage: view.stage,
      checkpointToken: view.checkpointToken,
      key: draftStorageKey(view),
      view,
      document: draftDocument,
      snapshot: JSON.stringify(state.regions),
    });
    try {
      draftStore.writeDirty(entry);
    } catch (error) {
      console.warn("Could not persist the local draft cache", error);
    }
    return entry;
  }

  function handleAutosaveStart(entry) {
    if (draftStorageKey(state.board) !== entry.key) return;
    state.draftStatus = "saving";
    state.saveError = "";
    renderSaveState();
  }

  function handleAutosaveSuccess(entry, updated) {
    try {
      draftStore.markSaved(entry);
    } catch (error) {
      console.warn("Could not update the local draft cache", error);
    }
    if (draftStorageKey(state.board) !== entry.key) return;
    if (updated) state.board = updated;
    state.savedSnapshot = entry.snapshot;
    state.dirty = JSON.stringify(state.regions) !== entry.snapshot;
    state.draftStatus = state.dirty ? "dirty" : "saved";
    if (!state.dirty) setStatus("Draft saved to the active revision.");
    renderSaveState();
  }

  function handleAutosaveError(entry, error) {
    if (draftStorageKey(state.board) !== entry.key) return;
    state.dirty = true;
    state.draftStatus = "dirty";
    if (holdForActiveJobRecovery(error)) return;
    state.saveError = error.message || "Draft save failed";
    focusGeometryError(state.saveError);
    setStatus(state.saveError);
    render();
  }

  function validateGeometry() {
    if (!state.board || !EDITOR_STAGES.has(state.board.stage)) return [];
    const errors = [];
    const baseline = state.baselineRegions;
    const baselineById = new Map(baseline.map((region) => [region.id, region]));
    const baselineIdByKey = new Map(baseline.map((region) => [region.key, region.id]));
    const maximumBaselineId = Math.max(0, ...baseline.map((region) => region.id));
    const seenIds = new Set();
    let previousId = 0;
    state.regions.forEach((region, index) => {
      if (!Number.isInteger(region.id) || region.id <= 0 || region.id > 65535 || seenIds.has(region.id) || region.id <= previousId) {
        errors.push({ regionId: region.id, message: `Region ${String(region.id)} has an invalid stable ID or order.` });
      }
      seenIds.add(region.id);
      previousId = region.id;
      if (!region.key || state.regions.some((candidate, candidateIndex) => candidateIndex !== index && candidate.key === region.key)) {
        errors.push({ regionId: region.id, message: `Region ${String(region.id)} has a missing or duplicate key.` });
      }
      if (state.board.stage === 2) {
        const expected = baselineById.get(region.id);
        if (expected && expected.key !== region.key) {
          errors.push({ regionId: region.id, message: `Region ${String(region.id)} changed its retained stable key.` });
        } else if (!expected && (region.id <= maximumBaselineId || baselineIdByKey.has(region.key))) {
          errors.push({ regionId: region.id, message: `Region ${String(region.id)} does not follow the monotonic new-ID policy.` });
        }
        if (!Array.isArray(region.contour) || region.contour.length < 3) {
          errors.push({ regionId: region.id, message: `Region ${String(region.id)} needs at least three contour vertices.` });
        } else if (region.contour.some(([x, y]) => !Number.isFinite(x) || !Number.isFinite(y) || x < 0 || y < 0 || x >= state.canvas.width || y >= state.canvas.height)) {
          errors.push({ regionId: region.id, message: `Region ${String(region.id)} has an out-of-bounds contour point.` });
        } else if (polygonArea(region.contour) < 1) {
          errors.push({ regionId: region.id, message: `Region ${String(region.id)} has degenerate geometry.` });
        }
      } else {
        const expected = baseline[index];
        if (!expected || expected.id !== region.id || expected.key !== region.key || expected.type !== region.type) {
          errors.push({ regionId: region.id, message: `Region ${String(region.id)} changed required Stage 3 identity.` });
        }
        try {
          const commands = parseDisplayPath(region.displayPath);
          const points = commands.flatMap((command) => command.type === "Z" ? [] : vectorCommandPoints(command));
          if (points.some(([x, y]) => x < 0 || y < 0 || x > state.canvas.width || y > state.canvas.height)) {
            errors.push({ regionId: region.id, message: `Region ${String(region.id)} has an out-of-bounds vector endpoint or handle.` });
          }
        } catch (_error) {
          errors.push({ regionId: region.id, message: `Region ${String(region.id)} has a malformed display path.` });
        }
      }
    });
    if (state.board.stage === 3 && state.regions.length !== baseline.length) {
      errors.unshift({ regionId: state.regions[0]?.id ?? null, message: `Stage ${String(state.board.stage)} region inventory no longer matches the generated checkpoint.` });
    }
    return errors;
  }

  function vectorCommandPoints(command) {
    if (command.type === "M" || command.type === "L") return [[command.x, command.y]];
    if (command.type === "Q") return [[command.x1, command.y1], [command.x, command.y]];
    if (command.type === "C") return [[command.x1, command.y1], [command.x2, command.y2], [command.x, command.y]];
    return [];
  }

  function onDraftChanged() {
    if (!state.guided || !EDITOR_STAGES.has(state.board?.stage)) return;
    state.validationErrors = validateGeometry();
    state.dirty = true;
    state.draftStatus = "dirty";
    persistCurrentDraft();
    scheduleDraftSave();
    renderValidation();
  }

  function scheduleDraftSave() {
    if (!state.guided || !EDITOR_STAGES.has(state.board?.stage)) return;
    if (state.autosaveTimer != null) clearTimeout(state.autosaveTimer);
    state.autosaveTimer = setTimeout(() => {
      state.autosaveTimer = null;
      void saveDraftNow(true);
    }, AUTOSAVE_DELAY_MS);
    renderSaveState();
  }

  async function saveDraftNow(background = false) {
    if (!state.board || !EDITOR_STAGES.has(state.board.stage)) return null;
    state.validationErrors = validateGeometry();
    if (state.validationErrors.length) {
      focusRegion(state.validationErrors[0].regionId);
      render();
      return null;
    }
    if (!autosaveCoordinator.hasPending()) persistCurrentDraft();
    return background ? autosaveCoordinator.savePending() : autosaveCoordinator.flush();
  }

  async function flushDraft() {
    if (state.autosaveTimer != null) {
      clearTimeout(state.autosaveTimer);
      state.autosaveTimer = null;
    }
    if (state.dirty || state.draftStatus === "saving") await saveDraftNow();
  }

  function focusGeometryError(message) {
    const error = geometryValidationError(message);
    if (!error) return false;
    state.validationErrors = [error];
    if (error.regionId != null) focusRegion(error.regionId);
    return true;
  }

  async function runTrackedJob(operation) {
    let acceptedJob = null;
    const options = {
      onAccepted(job) {
        acceptedJob = job;
        activeJobStore.write(job);
      },
    };
    try {
      const result = await operation(options);
      if (acceptedJob) clearMatchingAcceptedJob(activeJobStore, acceptedJob);
      return result;
    } catch (error) {
      clearConfirmedTerminalJob(activeJobStore, acceptedJob, error);
      holdForActiveJobRecovery(error);
      throw error;
    }
  }

  function holdForStoredActiveJob(jobId = null) {
    if (jobId == null ? !activeJobStore.read() : !activeJobStore.read(jobId)) return false;
    state.busy = true;
    state.editingFrozen = true;
    state.saveError = "";
    setStatus("Reconnecting to the active workbench job…");
    renderGuidedShell();
    render();
    return true;
  }

  function holdForActiveJobRecovery(error) {
    if (!isRecoverableJobError(error) || !activeJobStore.read(error.jobId)) return false;
    return holdForStoredActiveJob(error.jobId);
  }

  function focusRegion(regionId) {
    const numericId = Number(regionId);
    if (!state.regions.some((region) => region.id === numericId)) return false;
    if (state.selectedId !== numericId) state.selectedCornerIndex = null;
    state.selectedId = numericId;
    state.editPoints = true;
    render();
    el["canvas-viewport"].focus({ preventScroll: true });
    requestAnimationFrame(() => document.querySelector(`.region-item[data-region-id="${String(numericId)}"]`)?.scrollIntoView({ block: "nearest" }));
    return true;
  }

  function setCompareEnabled(enabled) {
    state.compareEnabled = Boolean(enabled);
    renderComparisonView();
    renderOverlay();
    renderToolState();
    return state.compareEnabled;
  }

  function renderComparisonView() {
    const separateReview = Boolean(
      state.guided && checkpointComparisonUrl(state.board)
    );
    const showReview = separateReview && state.compareEnabled;
    el["canvas-viewport"].classList.toggle("hidden", showReview);
    el["annotated-review"].classList.toggle("hidden", !showReview);
  }

  function checkpointDocumentUrl(view) {
    const names = { 2: "stage-2-regions.json", 3: "stage-3-vector-regions.json" };
    const name = names[view.stage];
    if (!name || !view.reviewUrl) return null;
    const url = new URL(view.reviewUrl, window.location.origin);
    const path = url.searchParams.get("path");
    if (!path) return null;
    url.searchParams.set("path", path.replace(/[^/]+$/, name));
    return `${url.pathname}?${url.searchParams.toString()}`;
  }

  async function loadCheckpoint(view, providedDocument = null, pendingLoad = null) {
    if (!view) return false;
    const ownsLoad = pendingLoad == null;
    const load = pendingLoad || loadCoordinator.begin();
    if (ownsLoad) {
      state.busy = true;
      renderSaveState();
    }
    try {
      if (!load.isCurrent()) return false;
      const imageUrl = checkpointImageUrl(view);
      const imageAsset = imageUrl
        ? await loadImageAsset(imageUrl, `Stage ${String(view.stage)} editor image`)
        : null;
      if (!load.isCurrent()) return false;
      let baselineDocument = providedDocument;
      if (EDITOR_STAGES.has(view.stage)) {
        if (!baselineDocument) {
          const documentUrl = checkpointDocumentUrl(view);
          if (!documentUrl) throw new Error(`Stage ${String(view.stage)} checkpoint document is unavailable`);
          const response = await fetch(documentUrl, { cache: "no-store" });
          if (!response.ok) throw new Error(`Could not load Stage ${String(view.stage)} checkpoint geometry`);
          baselineDocument = await response.json();
        }
        validateEditableImageAlignment(view, imageAsset, baselineDocument);
      }
      if (!load.isCurrent()) return false;
      const comparisonUrl = checkpointComparisonUrl(view);
      const reviewAsset = comparisonUrl
        ? await loadImageAsset(
          comparisonUrl,
          `Stage ${String(view.stage)} annotated review`,
        )
        : null;
      if (!load.isCurrent()) return false;

      return load.commit(() => {
      if (state.autosaveTimer != null) clearTimeout(state.autosaveTimer);
      state.autosaveTimer = null;
      state.board = view;
      suiteController?.setBoard(view);
      state.editorMode = view.editorMode || "contour";
      state.checkpointDocument = null;
      state.validationErrors = [];
      state.saveError = "";
      state.editingFrozen = false;
      state.draftStatus = "clean";
      state.drawing = false;
      state.editPoints = false;
      state.mirrorOntoSourceId = null;
      state.regions = [];
      state.baselineRegions = [];
      state.selectedId = null;
      state.selectedCornerIndex = null;
      state.imageHref = "";
      state.imageName = "";
      state.imagePixels = null;
      el["board-image"].removeAttribute("href");
      el["annotated-review-image"].removeAttribute("src");
      el["annotated-review-image"].alt = "";
      if (imageAsset) applyImageAsset(imageAsset);
      if (reviewAsset) applyAnnotatedReviewAsset(reviewAsset);

      if (EDITOR_STAGES.has(view.stage)) {
        const restored = readStoredDraft(view);
        state.checkpointDocument = clone(baselineDocument);
        setRegions(restored?.document || baselineDocument, `stage-${String(view.stage)}-checkpoint.json`, view.editorMode, baselineDocument);
        if (restored?.dirty) {
          state.savedSnapshot = JSON.stringify(state.baselineRegions);
          state.dirty = true;
          state.draftStatus = "dirty";
          persistCurrentDraft();
          scheduleDraftSave();
          setStatus("Restored an unsaved same-browser draft for this revision.");
        } else if (restored) {
          state.draftStatus = "saved";
          state.savedSnapshot = JSON.stringify(state.regions);
          setStatus("Restored the latest same-browser draft for this revision.");
        }
      } else {
        resetHistory();
        configureSvg();
        render();
        requestAnimationFrame(fitCanvas);
      }
        renderGuidedShell();
      });
    } finally {
      if (ownsLoad && load.isCurrent()) {
        state.busy = false;
        renderGuidedShell();
        render();
      }
    }
  }

  function timelineView(view) {
    const mappedStage = PIPELINE_TO_TIMELINE_STAGE[view.stage] ?? Math.min(view.stage, 6);
    const mappedStale = view.staleFromStage == null ? null : (PIPELINE_TO_TIMELINE_STAGE[view.staleFromStage] ?? view.staleFromStage);
    return { ...view, stage: mappedStage, staleFromStage: mappedStale };
  }

  function renderGuidedShell() {
    if (!state.guided) return;
    const view = state.board;
    el["stage-timeline"].replaceChildren();
    const timeline = timelineFor(view ? timelineView(view) : {});
    timeline.forEach((row, index) => {
      const item = document.createElement("li");
      item.className = `stage-row ${row.state}`;
      item.innerHTML = `<span class="stage-dot">${row.state === "complete" ? "✓" : String(index + 1)}</span><span>${escapeHTML(STAGE_LABELS[index])}</span>`;
      el["stage-timeline"].appendChild(item);
    });
    renderRecentRuns();
    el["board-title"].textContent = view?.productName || "Hangboard Workbench";
    el["board-state"].textContent = view
      ? `Revision ${view.revisionId} · ${view.state.replaceAll("_", " ")}`
      : "Create or choose a board to begin.";
    el["checkpoint-title"].textContent = view
      ? `${view.editorMode === "vector" ? "Exact vector" : view.editorMode === "contour" ? "Contour" : "Visual"} · Stage ${String(view.stage)}`
      : "Waiting for a board";
    el["inventory-block"].classList.toggle("hidden", !view || !EDITOR_STAGES.has(view.stage));
    renderSaveState();
  }

  function renderRecentRuns() {
    el["recent-runs"].replaceChildren();
    state.boards.forEach((board) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `recent-run${board.boardId === state.board?.boardId ? " active" : ""}`;
      button.disabled = openingActionsDisabled(state);
      button.innerHTML = `<span>${escapeHTML(board.productName)}</span><small>Stage ${String(board.stage)}</small>`;
      button.addEventListener("click", () => void selectGuidedBoard(board.boardId));
      el["recent-runs"].appendChild(button);
    });
  }

  function renderOpeningSections() {
    const sections = openingSections(state.libraryBoards, state.boards);
    const screen = openingScreenState({
      library: sections.library,
      diagnostics: state.libraryDiagnostics,
      runtime: sections.inProgress,
      errors: state.openingErrors,
    });
    renderOpeningFormVisibility(el["create-board-form"], screen);
    renderRepositoryDiagnostics(el["repository-diagnostics"], screen.repositoryDiagnostics);
    el["setup-submit-button"].disabled = openingActionsDisabled(state);
    renderOpeningBoardList(el["repository-board-list"], screen.repository, {
      label: (board) => board.displayName || board.boardId,
      detail: () => "Ready to open",
      onSelect: selectLibraryBoard,
      disabled: openingActionsDisabled(state),
    });
    renderOpeningBoardList(el["in-progress-board-list"], screen.inProgress, {
      label: (board) => board.productName || board.boardId,
      detail: (board) => board.saved ? "Saved locally" : `Stage ${String(board.stage ?? 0)} · Unsaved`,
      onSelect: selectGuidedBoard,
      disabled: openingActionsDisabled(state),
    });
  }

  function showSetup() {
    el["setup-screen"].classList.remove("hidden");
    el["workbench-screen"].classList.add("hidden");
    renderOpeningSections();
  }

  function showWorkbench() {
    el["setup-screen"].classList.add("hidden");
    el["workbench-screen"].classList.remove("hidden");
  }

  async function refreshBoards() {
    const opening = await openingBoardController.refresh();
    state.libraryBoards = opening.library;
    state.libraryDiagnostics = opening.diagnostics;
    state.boards = opening.runtime;
    state.openingErrors = { ...opening.errors };
    renderRecentRuns();
    renderOpeningSections();
    return state.boards;
  }

  async function selectLibraryBoard(boardId) {
    if (openingActionsDisabled(state)) return false;
    const load = loadCoordinator.begin();
    state.busy = true;
    showWorkbench();
    renderSaveState();
    try {
      const view = await openingBoardController.openRepositoryBoard(boardId);
      await refreshBoards();
      if (!load.isCurrent()) return false;
      const loaded = await loadCheckpoint(view, null, load);
      if (loaded) setStatus(`Reviewing ${view.productName}.`);
      return loaded;
    } catch (error) {
      if (!load.isCurrent()) return false;
      handleOpeningSelectionFailure({
        error,
        editingFrozen: state.editingFrozen,
        setLibraryError(message) { state.openingErrors.library = message; },
        showSetup,
      });
      return false;
    } finally {
      if (load.isCurrent()) {
        if (!state.editingFrozen) state.busy = false;
        renderGuidedShell();
        render();
      }
    }
  }

  async function selectGuidedBoard(boardId) {
    if (openingActionsDisabled(state)) return false;
    const load = loadCoordinator.begin();
    state.busy = true;
    showWorkbench();
    renderSaveState();
    try {
      const view = await openingBoardController.openRuntimeBoard(boardId);
      if (!load.isCurrent()) return false;
      const loaded = await loadCheckpoint(view, null, load);
      if (loaded) setStatus(`Reviewing ${view.productName}.`);
      return loaded;
    } catch (error) {
      if (!load.isCurrent()) return false;
      state.saveError = error.message || "Could not load board";
      setStatus(state.saveError);
      return false;
    } finally {
      if (load.isCurrent()) {
        state.busy = false;
        renderGuidedShell();
        render();
      }
    }
  }

  async function createGuidedBoard(event) {
    event.preventDefault();
    const productName = el["setup-product-input"].value.trim();
    const sourceKind = new FormData(el["create-board-form"]).get("sourceKind");
    const source = el["setup-url-input"].value.trim();
    const upload = el["setup-upload-input"].files[0];
    el["setup-error"].classList.add("hidden");
    const invalid = !productName || (sourceKind === "url" ? !source : !upload);
    if (invalid) {
      el["setup-error"].textContent = "Enter a product name and choose one image source.";
      el["setup-error"].classList.remove("hidden");
      return;
    }
    const load = loadCoordinator.begin();
    el["setup-submit-button"].disabled = true;
    el["setup-submit-button"].textContent = "Creating…";
    try {
      const view = await runTrackedJob((options) => {
        if (sourceKind === "url") return workbenchClient.createFromUrl(productName, source, options);
        return workbenchClient.createFromUpload(productName, upload, options);
      });
      await refreshBoards();
      if (!load.isCurrent()) return;
      showWorkbench();
      await loadCheckpoint(view, null, load);
    } catch (error) {
      if (!load.isCurrent()) return;
      if (!holdForActiveJobRecovery(error)) {
        el["setup-error"].textContent = error.message || "Could not create the board.";
        el["setup-error"].classList.remove("hidden");
      }
    } finally {
      el["setup-submit-button"].disabled = state.editingFrozen;
      renderSetupSourceKind(new FormData(el["create-board-form"]).get("sourceKind"));
    }
  }

  function renderSetupSourceKind(sourceKind) {
    el["setup-product-field"].classList.remove("hidden");
    el["setup-product-input"].required = true;
    el["setup-url-field"].classList.toggle("hidden", sourceKind !== "url");
    el["setup-upload-field"].classList.toggle("hidden", sourceKind !== "upload");
    el["setup-submit-button"].textContent = "Create board";
  }

  async function approveCurrent() {
    if (!state.board || state.busy) return;
    state.validationErrors = validateGeometry();
    if (state.validationErrors.length) {
      focusRegion(state.validationErrors[0].regionId);
      render();
      return;
    }
    const view = state.board;
    const load = loadCoordinator.begin();
    state.busy = true;
    state.saveError = "";
    renderSaveState();
    try {
      const updated = await runFrozenApproval({
        setFrozen(value) {
          state.editingFrozen = value;
          renderToolState();
        },
        cancelPointerSessions,
        flushDraft,
        approve: () => runTrackedJob((options) => workbenchClient.approve(view, options)),
      });
      await refreshBoards();
      if (!load.isCurrent()) return;
      const loaded = await loadCheckpoint(updated, null, load);
      if (loaded) setStatus(`Stage ${String(updated.stage)} is ready for review.`);
    } catch (error) {
      if (!load.isCurrent()) return;
      if (!holdForActiveJobRecovery(error)) {
        state.saveError = error.message || "Approval failed";
        focusGeometryError(state.saveError);
        setStatus(state.saveError);
      }
    } finally {
      if (load.isCurrent()) {
        if (!state.editingFrozen) state.busy = false;
        renderGuidedShell();
        render();
      }
    }
  }

  function cancelPointerSessions() {
    const captures = [
      [state.transformSession, el["editor-svg"]],
      [state.dragSession, el["editor-svg"]],
      [state.handleSession, el["editor-svg"]],
      [state.primitiveSession, el["canvas-viewport"]],
      [state.panSession, el["canvas-viewport"]],
    ];
    captures.forEach(([session, target]) => {
      if (session?.pointerId == null || typeof target?.hasPointerCapture !== "function") return;
      if (target.hasPointerCapture(session.pointerId)) target.releasePointerCapture(session.pointerId);
    });
    if ([state.transformSession, state.dragSession, state.handleSession].some((session) => session?.changed)) {
      commitHistory("Completed active edit before approval");
    }
    state.transformSession = null;
    state.dragSession = null;
    state.handleSession = null;
    state.primitiveSession = null;
    state.panSession = null;
    state.drawing = false;
    state.draft = [];
    state.mirrorOntoSourceId = null;
    el["draw-instruction"].classList.remove("visible");
    el["canvas-viewport"].classList.remove("panning");
  }

  async function retryCurrent() {
    if (!state.board || state.busy) return;
    await runGuidedMutation((options) => workbenchClient.retry(state.board, options), "Checkpoint regenerated.");
  }

  async function reviseCurrent() {
    if (!state.board || state.busy || state.board.stage < 1) return;
    await runGuidedMutation((options) => workbenchClient.revise(state.board, state.board.stage - 1, options), "Created a new upstream revision.");
  }

  async function finalSaveCurrent() {
    if (!state.board || state.busy) return;
    await runGuidedMutation((options) => workbenchClient.finalSave(state.board, options), "Saved to this repository.");
  }

  async function runGuidedMutation(operation, successMessage) {
    const load = loadCoordinator.begin();
    state.busy = true;
    state.saveError = "";
    renderSaveState();
    try {
      const updated = await runTrackedJob(operation);
      await refreshBoards();
      if (!load.isCurrent()) return;
      const loaded = await loadCheckpoint(updated, null, load);
      if (loaded) setStatus(successMessage);
    } catch (error) {
      if (!load.isCurrent()) return;
      if (!holdForActiveJobRecovery(error)) {
        state.saveError = error.message || "Workbench action failed";
        focusGeometryError(state.saveError);
        setStatus(state.saveError);
      }
    } finally {
      if (load.isCurrent()) {
        if (!state.editingFrozen) state.busy = false;
        renderGuidedShell();
        render();
      }
    }
  }

  async function loadGuidedWorkbench() {
    state.guided = true;
    el["legacy-controls"].classList.add("hidden");
    showBoardPicker(false);
    const acceptedJobs = activeJobStore.readAll();
    let recoveredFailure = null;
    if (acceptedJobs.length) {
      state.busy = true;
      state.editingFrozen = true;
      showWorkbench();
      setStatus("Reconnecting to active workbench jobs…");
      render();
      try {
        const reconciliation = await reconcileActiveJobs(
          activeJobStore,
          (jobId) => workbenchClient.pollJob(jobId),
        );
        if (reconciliation.unknown.length || activeJobStore.readAll().length) {
          holdForStoredActiveJob();
          return true;
        }
        state.editingFrozen = false;
        const recovered = reconciliation.succeeded.at(-1)?.result;
        if (recovered) {
          await refreshBoards();
          await loadCheckpoint(recovered);
          setStatus(`Reconnected to ${recovered.productName}.`);
          return true;
        }
        const failure = reconciliation.failed.at(-1)?.error;
        if (failure) {
          state.saveError = failure.message || "Could not reconnect to an active job";
          recoveredFailure = failure;
        }
      } catch (error) {
        holdForStoredActiveJob();
        if (activeJobStore.readAll().length) return true;
        state.editingFrozen = false;
        state.saveError = error.message || "Could not reconcile active jobs";
        recoveredFailure = error;
      } finally {
        if (!activeJobStore.readAll().length) state.busy = false;
        render();
      }
    }
    await restoreOpeningAfterJobRecovery({
      failure: recoveredFailure,
      refreshBoards,
      showSetup,
      setupError: el["setup-error"],
      setStatus,
    });
    if (state.openingErrors.library && state.openingErrors.runtime) {
      state.guided = false;
      el["legacy-controls"].classList.remove("hidden");
      showWorkbench();
      return false;
    }
    return true;
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

  function showBoardPicker(visible) {
    el["board-picker"].classList.toggle("hidden", !visible);
    el["board-picker-separator"].classList.toggle("hidden", !visible);
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
      if (!regionsResponse.ok) throw new Error("Could not load hold highlights from the run");
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
      el["board-select"].value = session.id;
      setStatus(`Editing ${session.label}. Changes can be saved into this generated run.`);
      return true;
    } catch (error) {
      console.warn(error);
      if (previousRunId) el["board-select"].value = previousRunId;
      setStatus(formatSessionLoadError(error));
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
    if (await loadGuidedWorkbench()) return;
    if (await loadServerCatalog()) return;
    showBoardPicker(false);
    await loadDemo();
  }

  async function loadImageAsset(href, name) {
    const image = await new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error(`Could not load image asset: ${href}`));
      image.src = href;
    });
    return { href, name, image };
  }

  function applyImageAsset({ href, name, image }) {
    state.imageHref = href;
    state.imageName = name;
    el["board-image"].setAttribute("href", href);
    captureImagePixels(image);
    if (!state.regions.length) state.canvas = { width: image.naturalWidth, height: image.naturalHeight };
    configureSvg();
    el["empty-state"].classList.add("hidden");
  }

  function applyAnnotatedReviewAsset({ href, name }) {
    el["annotated-review-image"].src = href;
    el["annotated-review-image"].alt = name;
  }

  async function setImageHref(href, name) {
    applyImageAsset(await loadImageAsset(href, name));
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

  function setRegions(data, name = "regions.json", editorMode = "contour", baselineData = data) {
    const normalized = normalizePipelineDocument(data, state.canvas, editorMode);
    const baseline = normalizePipelineDocument(baselineData, normalized.canvas, editorMode);
    state.canvas = normalized.canvas;
    state.regions = normalized.regions;
    state.baselineRegions = clone(baseline.regions);
    state.nextRegionId = nextStage2RegionId({
      baselineRegions: state.baselineRegions,
      regions: state.regions,
      nextRegionId: data.inventory?.nextRegionId,
    });
    state.editorMode = normalized.editorMode;
    state.regionsName = name;
    state.selectedId = state.regions[0]?.id ?? null;
    state.selectedCornerIndex = null;
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
    renderSaveState();
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
      setStatus(`Saved ${result.regionsPath} and ${result.correctionsPath}.`);
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
    if (!canEditGeometry()) return;
    const region = selectedRegion();
    if (!region) return;
    mutator(region);
    commitHistory(label);
    render();
  }

  function updateSelectedCorner(patch, label) {
    if (!canEditGeometry() || !Number.isInteger(state.selectedCornerIndex)) return;
    const region = selectedRegion();
    if (!region) return;
    const index = state.selectedCornerIndex;
    const current = region.metadata.cornerTreatments?.[index] || { treatment: "sharp", amount: 12 };
    const next = { ...current, ...patch };
    region.metadata.cornerTreatments = { ...(region.metadata.cornerTreatments || {}), [index]: next };
    if (isVectorMode()) {
      region.displayPath = serializeDisplayPath(treatPathCorner(
        parseDisplayPath(region.displayPath), index, next.treatment, next.amount,
      ));
    }
    commitHistory(label);
    render();
  }

  function shapeLabel(kind) {
    return ({ freeform: "Freeform", "curved-freeform": "Curved freeform", rectangle: "Rectangle", "rounded-rectangle": "Rounded rectangle", "arced-rectangle": "Arced rectangle", ellipse: "Ellipse", capsule: "Capsule" })[kind] || "Freeform";
  }

  function normalizeRegion(region, fallbackId) {
    return normalizePipelineDocument({ canvas: state.canvas, regions: [region] }, state.canvas, "contour").regions.map((item) => ({ ...item, id: fallbackId }))[0];
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
    if (!canEditGeometry()) return;
    const region = selectedRegion();
    if (!region || isVectorMode()) return;
    if (kind !== "freeform") {
      const [x1, y1, x2, y2] = bounds(region.contour);
      region.contour = shapeContour(kind, [x1, y1], [x2, y2]);
      delete region.metadata.cornerTreatments;
      state.selectedCornerIndex = null;
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
  el["save-button"].addEventListener("click", () => {
    if (!state.guided) void saveToRun();
    else if (state.board?.state === "complete") void finalSaveCurrent();
    else void approveCurrent();
  });
  el["compare-button"].addEventListener("click", () => setCompareEnabled(!state.compareEnabled));
  el["retry-button"].addEventListener("click", () => void retryCurrent());
  el["revise-button"].addEventListener("click", () => void reviseCurrent());
  el["new-board-button"].addEventListener("click", () => {
    showSetup();
    void refreshBoards();
  });
  el["create-board-form"].addEventListener("submit", createGuidedBoard);
  document.querySelectorAll('input[name="sourceKind"]').forEach((input) => {
    input.addEventListener("change", () => {
      if (!input.checked) return;
      renderSetupSourceKind(input.value);
    });
  });
  el["fit-button"].addEventListener("click", fitCanvas);
  el["zoom-in-button"].addEventListener("click", () => setZoom(state.zoom * 1.2));
  el["zoom-out-button"].addEventListener("click", () => setZoom(state.zoom / 1.2));
  el["opacity-slider"].addEventListener("input", (event) => { state.opacity = Number(event.target.value) / 100; renderOverlay(); });
  el["region-key-input"].addEventListener("change", (event) => updateSelected((region) => { region.key = event.target.value.trim() || region.key; }, "Renamed region"));
  el["region-type-select"].addEventListener("change", (event) => updateSelected((region) => { region.type = event.target.value; }, "Changed grip type"));
  el["region-shape-select"].addEventListener("change", (event) => convertSelectedShape(event.target.value));
  el["region-path-style-select"].addEventListener("change", (event) => updateSelected((region) => { region.metadata.pathStyle = event.target.value; }, "Changed path style"));
  el["curve-tension-slider"].addEventListener("input", (event) => {
    if (!canEditGeometry()) return;
    const region = selectedRegion();
    if (!region) return;
    region.metadata.curveTension = Number(event.target.value) / 100;
    el["curve-tension-value"].value = `${event.target.value}%`;
    renderOverlay();
  });
  el["curve-tension-slider"].addEventListener("change", () => {
    if (!canEditGeometry() || !selectedRegion()) return;
    commitHistory("Changed curve tension");
    render();
  });
  el["corner-treatment-select"].addEventListener("change", (event) => {
    updateSelectedCorner({ treatment: event.target.value }, "Changed corner treatment");
  });
  el["corner-amount-input"].addEventListener("change", (event) => {
    const amount = clamp(Number(event.target.value), 0.5, 100);
    if (!Number.isFinite(amount)) return renderInspector();
    updateSelectedCorner({ amount }, "Changed corner amount");
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

  window.HoldEditor = Object.freeze({
    loadCheckpoint,
    serializeDraft,
    markDraftSaved,
    focusRegion,
    setCompareEnabled,
  });

  suiteController = createToolSuiteController({
    selectTool: selectSuiteTool,
    loadBoard: (boardId, revisionId) => workbenchClient.getBoard(boardId, revisionId),
    render(nextState) {
      state.suiteState = nextState;
      renderSuite();
    },
    initialState: state.suiteState,
  });
  promotionController = createPromotionController({
    client: workbenchClient,
    getSuiteState: () => suiteController.getState(),
    onPromotion(promotion) {
      suiteController.setResults({ promotion });
    },
    render(promotion) {
      renderPromotionView(el["promote-view"], {
        suite: state.suiteState,
        promotion,
      });
    },
  });
  document.querySelectorAll("[data-tool]").forEach((button) => {
    button.addEventListener("click", () => suiteController.selectTool(button.dataset.tool));
  });
  el["inspect-next-action"].addEventListener("click", () => {
    suiteController.selectTool(state.suiteState.readiness.nextTool);
  });
  document.querySelectorAll("[data-promotion-field]").forEach((input) => {
    input.addEventListener("input", () => promotionController.setProfileField(
      input.dataset.promotionField,
      input.value,
    ));
  });
  document.getElementById("promotion-preview-button").addEventListener("click", () => {
    void promotionController.generatePreview();
  });
  document.getElementById("promotion-refresh-button").addEventListener("click", () => {
    void promotionController.refreshPreview();
  });
  document.getElementById("promotion-save-button").addEventListener("click", () => {
    void promotionController.saveLocally();
  });

  configureSvg();
  resetHistory();
  render();
  loadInitialSession();
})();
