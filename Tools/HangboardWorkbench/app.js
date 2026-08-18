(() => {
  "use strict";

  const client = globalThis.HoldWorkbenchClient;
  const {
    createBoardOperationCoordinator,
    loadBoardAtomically,
    saveBoardAtomically,
    validateEditorDocument,
  } = globalThis.HoldWorkbenchController;
  const svgNS = "http://www.w3.org/2000/svg";
  const { parsePath, serializePath, moveVertex, addVertex, deleteVertex, rotatePath } = (() => {
    try { return require("./path-editor.js"); } catch { return globalThis.HoldPathEditor || {}; }
  })();
  const dialogs = globalThis.HoldWorkbenchDialogs || {
    confirm: (message) => window.confirm(message),
    prompt: (message, defaultValue) => window.prompt(message, defaultValue),
  };
  const TYPE_COLORS = { jug: "#ff754f", sloper: "#32bbc1", edge: "#9a6cf2", pocket: "#ee4d97", pinch: "#f2c94c" };
  const HOLD_KINDS = Object.keys(TYPE_COLORS);

  const state = {
    boards: [],
    board: null,
    document: null,
    image: null,
    selectedKey: null,
    branches: [],
    currentBranch: null,
    gitStatusKnown: false,
    hasUncommittedChanges: false,
    dirty: false,
    busyBoard: false,
    busyGit: false,
    authenticated: false,
    username: null,
  };

  const el = Object.fromEntries([
    "board-list", "boards-error", "refresh-boards-button", "save-button", "save-state", "board-status",
    "board-name", "editor-svg", "board-image", "hold-overlay", "empty-state", "editor-status",
    "validation-panel", "validation-list", "hold-heading", "hold-empty", "hold-form", "hold-key",
    "hold-type-select", "add-hold-button",
    "git-auth-status", "git-status", "git-branch-select", "git-refresh-button", "git-switch-button",
    "git-new-branch-name", "git-new-branch-button",
    "git-commit-message", "git-commit-button", "git-push-button", "git-open-pr-button",
    "delete-hold-button", "rotate-ccw-button", "rotate-cw-button", "rotate-by-input", "rotate-by-apply-button",
  ].map((id) => [id, document.getElementById(id)]));

  for (const kind of HOLD_KINDS) {
    const option = document.createElement("option");
    option.value = kind;
    option.textContent = kind;
    el["hold-type-select"].append(option);
  }

  const boardOperations = createBoardOperationCoordinator({
    onBusyChange: (busy) => {
      state.busyBoard = busy;
      render();
    },
  });

  const gitOperations = createBoardOperationCoordinator({
    onBusyChange: (busy) => {
      state.busyGit = busy;
      render();
    },
  });

  function isBusy() {
    return state.busyBoard || state.busyGit;
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function selectedHold() {
    return state.document?.regions.find((region) => region.key === state.selectedKey) || null;
  }

  function setStatus(message) {
    el["editor-status"].textContent = message;
  }

  function setValidation(error = "") {
    el["validation-list"].replaceChildren();
    el["validation-panel"].classList.toggle("hidden", !error);
    if (!error) return;
    const item = document.createElement("li");
    item.textContent = error;
    el["validation-list"].append(item);
  }

  function renderSaveState() {
    el["save-button"].disabled = !state.board || isBusy();
    el["add-hold-button"].disabled = !state.document || isBusy();
    el["refresh-boards-button"].disabled = isBusy();
    el["save-state"].textContent = !state.board
      ? "No board selected"
      : isBusy()
        ? "Working…"
        : state.dirty
          ? "Unsaved changes"
          : "Saved";

    el["git-status"].textContent = state.currentBranch
      ? `${state.currentBranch}${state.hasUncommittedChanges ? " (uncommitted changes)" : ""}`
      : state.gitStatusKnown
        ? `Detached HEAD${state.hasUncommittedChanges ? " (uncommitted changes)" : ""}`
        : "Repository status unavailable";

    el["git-refresh-button"].disabled = isBusy();
    el["git-branch-select"].disabled = isBusy() || state.branches.length === 0;
    el["git-switch-button"].disabled = isBusy() || !state.currentBranch || !el["git-branch-select"].value || el["git-branch-select"].value === state.currentBranch;
    el["git-new-branch-name"].disabled = isBusy();
    el["git-new-branch-button"].disabled = isBusy() || !el["git-new-branch-name"].value.trim();
    el["git-commit-message"].disabled = isBusy();
    el["git-commit-button"].disabled = isBusy() || !state.currentBranch;
    el["git-push-button"].disabled = isBusy() || !state.currentBranch;
    el["git-open-pr-button"].disabled = isBusy() || !state.currentBranch;

    el["board-status"].textContent = state.currentBranch
      ? `Current branch: ${state.currentBranch}`
      : state.gitStatusKnown
        ? "Detached HEAD"
        : "No branch detected";
  }

  function syncBranches(activeBranch) {
    el["git-branch-select"].replaceChildren();
    const ordered = [...state.branches].sort();
    if (ordered.length === 0) {
      const fallback = document.createElement("option");
      fallback.value = "";
      fallback.textContent = "No branches detected";
      el["git-branch-select"].append(fallback);
      return;
    }
    for (const branch of ordered) {
      const option = document.createElement("option");
      option.value = branch;
      option.textContent = branch;
      option.selected = branch === activeBranch;
      el["git-branch-select"].append(option);
    }
    if (activeBranch && ordered.includes(activeBranch)) {
      el["git-branch-select"].value = activeBranch;
    }
  }

  function renderBoards() {
    el["board-list"].replaceChildren();
    for (const board of state.boards) {
      const button = document.createElement("button");
      const title = document.createElement("span");
      const detail = document.createElement("small");
      button.type = "button";
      button.className = `region-item${state.board?.boardId === board.boardId ? " selected" : ""}`;
      button.disabled = isBusy();
      title.className = "region-key";
      title.textContent = board.displayName;
      detail.className = "region-type";
      detail.textContent = `${board.holdCount} holds`;
      button.append(title, detail);
      button.addEventListener("click", () => {
        if (!isBusy()) void selectBoard(board.boardId);
      });
      el["board-list"].append(button);
    }
  }

  function renderEditor() {
    const documentValue = state.document;
    const selected = selectedHold();
    el["empty-state"].classList.toggle("hidden", Boolean(documentValue));
    el["hold-overlay"].replaceChildren();
    el["editor-svg"].querySelector(".path-editor-overlay")?.remove();
    if (!documentValue) {
      el["board-name"].textContent = "No board selected";
      el["board-image"].removeAttribute("href");
      return;
    }
    const { width, height } = documentValue.canvas;
    el["board-name"].textContent = state.board.displayName;
    el["editor-svg"].setAttribute("viewBox", `0 0 ${width} ${height}`);
    el["editor-svg"].setAttribute("width", String(width));
    el["editor-svg"].setAttribute("height", String(height));
    el["board-image"].setAttribute("href", state.board.imageUrl);
    el["board-image"].setAttribute("width", String(width));
    el["board-image"].setAttribute("height", String(height));
    for (const hold of documentValue.regions) {
      const shape = document.createElementNS(svgNS, "path");
      shape.setAttribute("d", hold.displayPath);
      shape.setAttribute("fill", TYPE_COLORS[hold.type] || "#ff754f");
      shape.setAttribute("fill-opacity", hold.key === selected?.key ? "0.58" : "0.3");
      shape.setAttribute("stroke", hold.key === selected?.key ? "#fff7dc" : TYPE_COLORS[hold.type] || "#ff754f");
      shape.setAttribute("stroke-width", hold.key === selected?.key ? "2.2" : "1.4");
      shape.classList.add("region-shape");
      shape.dataset.holdKey = hold.key;
      shape.addEventListener("click", () => { state.selectedKey = hold.key; render(); });
      el["hold-overlay"].append(shape);
    }
    if (selected) {
      renderPathHandles(selected);
    }
  }

  function renderPathHandles(hold) {
    if (!parsePath) return;
    const overlay = document.createElementNS(svgNS, "g");
    overlay.classList.add("path-editor-overlay");
    const pivot = holdCentroid(holdSiblings(hold));
    const handleY = pivot.y - 24;
    const rotationConnector = document.createElementNS(svgNS, "line");
    rotationConnector.setAttribute("x1", String(pivot.x));
    rotationConnector.setAttribute("y1", String(pivot.y));
    rotationConnector.setAttribute("x2", String(pivot.x));
    rotationConnector.setAttribute("y2", String(handleY));
    rotationConnector.setAttribute("stroke", "#fff7dc");
    rotationConnector.setAttribute("stroke-width", "1.5");
    rotationConnector.setAttribute("stroke-dasharray", "4 3");
    rotationConnector.classList.add("path-editor-rotation-connector");
    overlay.append(rotationConnector);
    const rotationHandle = document.createElementNS(svgNS, "circle");
    rotationHandle.setAttribute("cx", String(pivot.x));
    rotationHandle.setAttribute("cy", String(handleY));
    rotationHandle.setAttribute("r", "6");
    rotationHandle.setAttribute("fill", "#fff7dc");
    rotationHandle.setAttribute("stroke", TYPE_COLORS[hold.type] || "#ff754f");
    rotationHandle.setAttribute("stroke-width", "2");
    rotationHandle.classList.add("path-editor-rotation-handle");
    overlay.append(rotationHandle);
    let commands;
    try { commands = parsePath(hold.displayPath); } catch { return; }
    for (let i = 0; i < commands.length; i++) {
      const cmd = commands[i];
      if (cmd.type === "Z") continue;
      const endpoint = cmd.points[cmd.points.length - 1];
      const circle = document.createElementNS(svgNS, "circle");
      circle.setAttribute("cx", String(endpoint.x));
      circle.setAttribute("cy", String(endpoint.y));
      circle.setAttribute("r", "6");
      circle.setAttribute("fill", TYPE_COLORS[hold.type] || "#ff754f");
      circle.setAttribute("stroke", "#fff7dc");
      circle.setAttribute("stroke-width", "1.5");
      circle.classList.add("path-editor-vertex");
      circle.dataset.index = String(i);
      overlay.append(circle);
      for (let j = 0; j < cmd.controls.length; j++) {
        const cp = cmd.controls[j];
        const prevCmd = i > 0 ? commands[i - 1] : null;
        const anchor = j === 0
          ? (prevCmd && prevCmd.type !== "Z" ? prevCmd.points[prevCmd.points.length - 1] : cmd.points[0])
          : cmd.points[0];
        if (anchor) {
          const line = document.createElementNS(svgNS, "line");
          line.setAttribute("x1", String(anchor.x));
          line.setAttribute("y1", String(anchor.y));
          line.setAttribute("x2", String(cp.x));
          line.setAttribute("y2", String(cp.y));
          line.setAttribute("stroke", "#888");
          line.setAttribute("stroke-width", "1");
          line.setAttribute("stroke-dasharray", "4 2");
          line.classList.add("path-editor-line");
          overlay.append(line);
        }
        const cc = document.createElementNS(svgNS, "circle");
        cc.setAttribute("cx", String(cp.x));
        cc.setAttribute("cy", String(cp.y));
        cc.setAttribute("r", "3");
        cc.setAttribute("fill", "#888");
        cc.setAttribute("stroke", "#fff");
        cc.setAttribute("stroke-width", "1");
        cc.classList.add("path-editor-control");
        cc.dataset.index = String(i);
        cc.dataset.control = String(j);
        overlay.append(cc);
      }
    }
    el["editor-svg"].append(overlay);
  }

  const drag = {
    active: false,
    type: null,
    holdKey: null,
    commandIndex: -1,
    controlIndex: -1,
    startX: 0,
    startY: 0,
    commands: null,
    originalPath: null,
    originalPaths: null,
    originalDirty: false,
    pivot: null,
    lastAngle: 0,
    totalAngle: 0,
    pointerId: null,
  };

  function svgPoint(event) {
    const svg = el["editor-svg"];
    const rect = svg.getBoundingClientRect();
    const vb = svg.getAttribute("viewBox").split(" ").map(Number);
    const scaleX = vb[2] / rect.width;
    const scaleY = vb[3] / rect.height;
    return { x: (event.clientX - rect.left) * scaleX, y: (event.clientY - rect.top) * scaleY };
  }

  function handlePointerDown(event) {
    const target = event.target;
    if (target.classList.contains("path-editor-rotation-handle")) {
      event.preventDefault();
      const hold = selectedHold();
      if (!hold) return;
      const siblings = holdSiblings(hold);
      const pivot = holdCentroid(siblings);
      const pt = svgPoint(event);
      drag.active = true;
      drag.type = "rotation";
      drag.holdKey = hold.key;
      drag.originalPaths = siblings.map((region) => ({ key: region.key, path: region.displayPath }));
      drag.originalDirty = state.dirty;
      drag.pivot = pivot;
      drag.lastAngle = Math.atan2(pt.y - pivot.y, pt.x - pivot.x);
      drag.totalAngle = 0;
    } else if (target.classList.contains("path-editor-vertex")) {
      event.preventDefault();
      const hold = selectedHold();
      if (!hold) return;
      const idx = parseInt(target.dataset.index, 10);
      const pt = svgPoint(event);
      drag.active = true;
      drag.type = "vertex";
      drag.holdKey = hold.key;
      drag.commandIndex = idx;
      drag.startX = pt.x;
      drag.startY = pt.y;
      drag.commands = parsePath(hold.displayPath);
      drag.originalPath = hold.displayPath;
      drag.originalDirty = state.dirty;
    } else if (target.classList.contains("path-editor-control")) {
      event.preventDefault();
      const hold = selectedHold();
      if (!hold) return;
      const pt = svgPoint(event);
      drag.active = true;
      drag.type = "control";
      drag.holdKey = hold.key;
      drag.commandIndex = parseInt(target.dataset.index, 10);
      drag.controlIndex = parseInt(target.dataset.control, 10);
      drag.startX = pt.x;
      drag.startY = pt.y;
      drag.commands = parsePath(hold.displayPath);
      drag.originalPath = hold.displayPath;
      drag.originalDirty = state.dirty;
    } else if (target.classList.contains("region-shape") && target.dataset.holdKey === state.selectedKey) {
      event.preventDefault();
      const hold = selectedHold();
      if (!hold) return;
      const pt = svgPoint(event);
      drag.active = true;
      drag.type = "body";
      drag.holdKey = hold.key;
      drag.startX = pt.x;
      drag.startY = pt.y;
      drag.commands = parsePath(hold.displayPath);
      drag.originalPath = hold.displayPath;
      drag.originalDirty = state.dirty;
    }
    if (drag.active && event.pointerId != null) {
      drag.pointerId = event.pointerId;
      el["editor-svg"].setPointerCapture?.(event.pointerId);
    }
  }

  function handlePointerMove(event) {
    if (!drag.active) return;
    event.preventDefault();
    const pt = svgPoint(event);
    const hold = state.document?.regions.find((r) => r.key === drag.holdKey);
    if (!hold) { drag.active = false; return; }
    if (drag.type === "rotation") {
      const angle = Math.atan2(pt.y - drag.pivot.y, pt.x - drag.pivot.x);
      let angleDelta = angle - drag.lastAngle;
      if (angleDelta > Math.PI) angleDelta -= 2 * Math.PI;
      if (angleDelta < -Math.PI) angleDelta += 2 * Math.PI;
      drag.lastAngle = angle;
      drag.totalAngle += angleDelta;
      for (const original of drag.originalPaths) {
        const region = state.document.regions.find((candidate) => candidate.key === original.key);
        if (!region) continue;
        let commands;
        try { commands = parsePath(original.path); } catch { continue; }
        rotatePath(commands, drag.totalAngle, drag.pivot);
        region.displayPath = serializePath(commands);
      }
      state.dirty = true;
      render();
      return;
    }
    const dx = pt.x - drag.startX;
    const dy = pt.y - drag.startY;
    const cmds = drag.commands.map((c) => ({
      ...c,
      points: c.points.map((p) => ({ ...p })),
      controls: c.controls.map((p) => ({ ...p })),
    }));
    if (drag.type === "vertex") {
      moveVertex(cmds, drag.commandIndex, dx, dy);
    } else if (drag.type === "control") {
      const cmd = cmds[drag.commandIndex];
      if (cmd && cmd.controls[drag.controlIndex]) {
        cmd.controls[drag.controlIndex].x += dx;
        cmd.controls[drag.controlIndex].y += dy;
      }
    } else if (drag.type === "body") {
      for (const cmd of cmds) {
        if (cmd.type === "Z") continue;
        for (const p of cmd.points) { p.x += dx; p.y += dy; }
        for (const c of cmd.controls) { c.x += dx; c.y += dy; }
      }
    }
    const newPath = serializePath(cmds);
    hold.displayPath = newPath;
    drag.startX = pt.x;
    drag.startY = pt.y;
    drag.commands = cmds;
    state.dirty = true;
    render();
  }

  function handlePointerUp(event) {
    if (!drag.active) return;
    drag.active = false;
    if (drag.pointerId != null) {
      el["editor-svg"].releasePointerCapture?.(drag.pointerId);
      drag.pointerId = null;
    }
    const hold = state.document?.regions.find((r) => r.key === drag.holdKey);
    if (!hold) return;
    try {
      validateEditorDocument(state.document);
      setValidation();
      setStatus(drag.type === "rotation" ? "Hold rotated. Save when ready." : "Contour updated. Save when ready.");
    } catch (error) {
      if (drag.type === "rotation") {
        for (const original of drag.originalPaths) {
          const region = state.document.regions.find((candidate) => candidate.key === original.key);
          if (region) region.displayPath = original.path;
        }
      } else {
        hold.displayPath = drag.originalPath;
      }
      state.dirty = drag.originalDirty;
      setValidation(error.message || "Contour is invalid.");
      setStatus(drag.type === "rotation" ? "Rotation reverted — contour is invalid." : "Edit reverted — contour is invalid.");
    }
    render();
  }

  function handleDoubleClick(event) {
    if (event.target.classList.contains("path-editor-vertex") || event.target.classList.contains("path-editor-control")) return;
    const hold = selectedHold();
    if (!hold) return;
    const pt = svgPoint(event);
    let commands;
    try { commands = parsePath(hold.displayPath); } catch { return; }
    for (let i = 0; i < commands.length; i++) {
      const cmd = commands[i];
      if (cmd.type === "Z") continue;
      const nextIdx = (i + 1) % commands.length;
      const next = commands[nextIdx];
      if (next.type === "Z" && cmd.type === "M") continue;
      const start = cmd.points[cmd.points.length - 1];
      const segment = next.type === "Z" ? { type: "L", points: [commands[0].points[0]], controls: [] } : next;
      if (closestDistanceOnSegment(start, segment, pt) < 15) {
        const insertPoint = segment.type === "L" ? closestPointOnLine(start, segment.points[0], pt) : pt;
        const originalPath = hold.displayPath;
        const originalDirty = state.dirty;
        addVertex(commands, i, insertPoint.x, insertPoint.y);
        hold.displayPath = serializePath(commands);
        state.dirty = true;
        try {
          validateEditorDocument(state.document);
          setValidation();
        } catch (error) {
          hold.displayPath = originalPath;
          state.dirty = originalDirty;
          setValidation(error.message || "Contour is invalid.");
        }
        render();
        return;
      }
    }
  }

  function handleContextMenu(event) {
    if (!event.target.classList.contains("path-editor-vertex")) return;
    event.preventDefault();
    const hold = selectedHold();
    if (!hold) return;
    const idx = parseInt(event.target.dataset.index, 10);
    let commands;
    try { commands = parsePath(hold.displayPath); } catch { return; }
    if (idx === 0) return;
    const originalPath = hold.displayPath;
    const originalDirty = state.dirty;
    deleteVertex(commands, idx);
    hold.displayPath = serializePath(commands);
    state.dirty = true;
    try {
      validateEditorDocument(state.document);
      setValidation();
    } catch (error) {
      hold.displayPath = originalPath;
      state.dirty = originalDirty;
      setValidation(error.message || "Contour is invalid.");
    }
    render();
  }

  function closestPointOnLine(a, b, p) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return { x: a.x, y: a.y };
    let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));
    return { x: a.x + t * dx, y: a.y + t * dy };
  }

  function closestPointOnSegment(a, b, p) {
    const proj = closestPointOnLine(a, b, p);
    return Math.hypot(p.x - proj.x, p.y - proj.y);
  }

  function bezierPointAt(p0, cmd, t) {
    const u = 1 - t;
    if (cmd.type === "Q") {
      const c = cmd.controls[0], p1 = cmd.points[0];
      return { x: u * u * p0.x + 2 * u * t * c.x + t * t * p1.x, y: u * u * p0.y + 2 * u * t * c.y + t * t * p1.y };
    }
    if (cmd.type === "C") {
      const c1 = cmd.controls[0], c2 = cmd.controls[1], p1 = cmd.points[0];
      return {
        x: u * u * u * p0.x + 3 * u * u * t * c1.x + 3 * u * t * t * c2.x + t * t * t * p1.x,
        y: u * u * u * p0.y + 3 * u * u * t * c1.y + 3 * u * t * t * c2.y + t * t * t * p1.y,
      };
    }
    return { x: p0.x + (cmd.points[0].x - p0.x) * t, y: p0.y + (cmd.points[0].y - p0.y) * t };
  }

  function closestDistanceOnSegment(p0, cmd, point, samples = 20) {
    let min = Infinity;
    let prev = p0;
    for (let s = 1; s <= samples; s++) {
      const cur = bezierPointAt(p0, cmd, s / samples);
      min = Math.min(min, closestPointOnSegment(prev, cur, point));
      prev = cur;
    }
    return min;
  }

  function renderInspector() {
    const hold = selectedHold();
    el["hold-empty"].classList.toggle("hidden", Boolean(hold));
    el["hold-form"].classList.toggle("hidden", !hold);
    el["hold-heading"].textContent = hold ? hold.key : "No selection";
    if (!hold) return;
    el["hold-key"].value = hold.key;
    el["hold-type-select"].value = hold.type;
  }

  function render() {
    renderBoards();
    renderEditor();
    renderInspector();
    renderSaveState();
  }

  function loadImage(href) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error("Board image is unavailable"));
      image.src = href;
    });
  }

  async function refreshBoards() {
    if (state.busyBoard || state.busyGit) return;
    el["boards-error"].classList.add("hidden");
    await boardOperations.perform(async () => {
      try {
        state.boards = await client.listBoards();
        renderBoards();
        setStatus("Boards loaded.");
      } catch (error) {
        el["boards-error"].textContent = error.message || "Could not load boards.";
        el["boards-error"].classList.remove("hidden");
        setStatus("Could not load boards.");
      }
    });
  }

  async function refreshGitState() {
    try {
      const status = await client.getGitStatus();
      const branches = Array.isArray(status.branches) ? status.branches : [];
      state.currentBranch = status.currentBranch || null;
      state.branches = branches;
      state.hasUncommittedChanges = Boolean(status.dirty);
      state.gitStatusKnown = true;
      syncBranches(state.currentBranch);
      return true;
    } catch (error) {
      state.branches = [];
      state.currentBranch = null;
      state.hasUncommittedChanges = false;
      state.gitStatusKnown = false;
      syncBranches(null);
      setValidation(error.message || "Could not read repository status.");
      setStatus("Could not read repository status.");
      return false;
    }
  }

  async function refreshAuthState() {
    try {
      const status = await client.getAuthStatus();
      state.authenticated = Boolean(status.authenticated);
      state.username = status.username || null;
    } catch {
      state.authenticated = false;
      state.username = null;
    }
    renderAuthState();
  }

  function renderAuthState() {
    if (state.authenticated && state.username) {
      el["git-auth-status"].textContent = `Logged in as ${state.username}`;
    } else {
      el["git-auth-status"].innerHTML = '<a href="/auth/login">Log in with GitHub</a>';
    }
  }

  async function selectBoard(boardId) {
    if (isBusy()) return;
    setValidation();
    await boardOperations.perform(async ({ isCurrent }) => {
      let committed = false;
      try {
        await loadBoardAtomically({
          boardId,
          getBoard: client.getBoard,
          loadImage,
          commit: ({ board, document: documentValue, image }) => {
            if (!isCurrent()) return;
            state.board = board;
            state.document = clone(documentValue);
            state.image = image;
            state.selectedKey = null;
            state.dirty = false;
            committed = true;
          },
        });
        if (!committed) return;
        setStatus("Board loaded.");
        render();
      } catch (error) {
        if (!isCurrent()) return;
        setValidation(error.message || "Could not load board.");
        setStatus("Could not load board. The current editor was kept.");
      }
    });
  }

  async function saveBoard() {
    if (isBusy() || !state.board || !state.document) return;
    try {
      validateEditorDocument(state.document);
    } catch (error) {
      setValidation(error.message || "Hold document is invalid.");
      return;
    }
    const boardId = state.board.boardId;
    const documentValue = state.document;
    await boardOperations.perform(async ({ isCurrent }) => {
      let committed = false;
      try {
        await saveBoardAtomically({
          boardId,
          document: clone(documentValue),
          save: client.saveBoard,
          commit: ({ board, document: savedDocument }) => {
            if (!isCurrent() || state.board?.boardId !== boardId || state.document !== documentValue) return;
            state.board = board;
            state.document = clone(savedDocument);
            state.dirty = false;
            committed = true;
          },
        });
        if (!committed) return;
        setValidation();
        setStatus("Board saved.");
        render();
      } catch (error) {
        if (!isCurrent()) return;
        setValidation(error.message || "Could not save board.");
        setStatus("Could not save board. Your editor changes were kept.");
      }
    });
  }

  async function switchBranch() {
    const branch = el["git-branch-select"].value;
    if (!branch || isBusy()) return;
    await gitOperations.perform(async () => {
      if (state.dirty) {
        const proceed = dialogs.confirm("You have unsaved hold edits. Switching branches will keep those edits in memory only. Continue?");
        if (!proceed) return;
      }
      try {
        await client.switchBranch(branch);
      } catch (error) {
        setValidation(error.message || "Could not switch branch.");
        setStatus("Could not switch branch.");
        return;
      }
      state.board = null;
      state.document = null;
      state.image = null;
      state.selectedKey = null;
      state.dirty = false;
      const gitStateRefreshed = await refreshGitState();
      if (gitStateRefreshed) {
        setValidation("");
        setStatus(`Switched to ${branch}.`);
      } else {
        setStatus(`Switched to ${branch}. Repository status unavailable.`);
      }
      try {
        await boardOperations.perform(async () => {
          state.boards = await client.listBoards();
        });
      } catch (error) {
        state.boards = [];
        setValidation(error.message || "Could not reload boards for the new branch.");
        setStatus(`Switched to ${branch}. Could not reload boards.`);
      }
      render();
    });
  }

  async function createBranch() {
    const branchName = el["git-new-branch-name"].value.trim();
    if (!branchName || isBusy()) return;
    await gitOperations.perform(async () => {
      if (state.dirty) {
        const proceed = dialogs.confirm("You have unsaved hold edits. Creating a branch will keep those edits in memory only. Continue?");
        if (!proceed) return;
      }
      try {
        await client.createBranch(branchName);
      } catch (error) {
        setValidation(error.message || "Could not create branch.");
        setStatus("Could not create branch.");
        return;
      }
      el["git-new-branch-name"].value = "";
      state.board = null;
      state.document = null;
      state.image = null;
      state.selectedKey = null;
      state.dirty = false;
      const gitStateRefreshed = await refreshGitState();
      if (gitStateRefreshed) {
        setValidation("");
        setStatus(`Created and switched to ${branchName}.`);
      } else {
        setStatus(`Created ${branchName}. Repository status unavailable.`);
      }
      try {
        await boardOperations.perform(async () => {
          state.boards = await client.listBoards();
        });
      } catch (error) {
        state.boards = [];
        setValidation(error.message || "Could not reload boards for the new branch.");
        setStatus(`Created ${branchName}. Could not reload boards.`);
      }
      render();
    });
  }

  async function commitChanges() {
    const message = el["git-commit-message"].value.trim();
    if (!message) {
      setValidation("Commit message is required.");
      return;
    }
    if (isBusy()) return;
    await gitOperations.perform(async () => {
      try {
        const result = await client.commitBoardChanges(message);
        el["git-commit-message"].value = "";
        const commitLabel = `Committed ${result.commit?.slice(0, 7) || "changes"}.`;
        const gitStateRefreshed = await refreshGitState();
        if (gitStateRefreshed) {
          setValidation("");
          setStatus(commitLabel);
        } else {
          setStatus(`${commitLabel} Repository status unavailable.`);
        }
      } catch (error) {
        setValidation(error.message || "Could not commit changes.");
        setStatus("Could not commit changes.");
      }
    });
  }

  async function pushBranch() {
    if (isBusy()) return;
    await gitOperations.perform(async () => {
      try {
        const pushedBranch = state.currentBranch || "current branch";
        await client.pushBranch();
        const pushLabel = `Pushed ${pushedBranch}.`;
        const gitStateRefreshed = await refreshGitState();
        if (gitStateRefreshed) {
          setValidation("");
          setStatus(pushLabel);
        } else {
          setStatus(`${pushLabel} Repository status unavailable.`);
        }
      } catch (error) {
        setValidation(error.message || "Could not push branch.");
        setStatus("Could not push branch.");
      }
    });
  }

  async function openPullRequest() {
    if (isBusy()) return;
    const defaultTitle = `Update ${state.currentBranch || "branch"}`;
    const title = dialogs.prompt("Pull request title:", defaultTitle);
    if (!title) return;
    const bodyText = dialogs.prompt("Pull request description (optional):", "") || "";
    await gitOperations.perform(async () => {
      try {
        const result = await client.openPullRequest({
          title: title.trim(),
          body: bodyText.trim(),
          base: "main",
        });
        setValidation("");
        setStatus(`Opened PR: ${result.url || "created"}`);
      } catch (error) {
        setValidation(error.message || "Could not open pull request.");
        setStatus("Could not open pull request.");
      }
    });
  }

  el["refresh-boards-button"].addEventListener("click", () => { void refreshBoards(); });
  el["save-button"].addEventListener("click", () => { void saveBoard(); });
  el["editor-svg"].addEventListener("pointerdown", handlePointerDown);
  el["editor-svg"].addEventListener("pointermove", handlePointerMove);
  el["editor-svg"].addEventListener("pointerup", handlePointerUp);
  el["editor-svg"].addEventListener("dblclick", handleDoubleClick);
  el["editor-svg"].addEventListener("contextmenu", handleContextMenu);
  el["git-refresh-button"].addEventListener("click", () => {
    void gitOperations.perform(async () => {
      await refreshGitState();
    });
  });
  el["git-branch-select"].addEventListener("change", () => { render(); });
  el["git-switch-button"].addEventListener("click", () => { void switchBranch(); });
  el["git-new-branch-name"].addEventListener("input", () => { render(); });
  el["git-new-branch-button"].addEventListener("click", () => { void createBranch(); });
  el["git-commit-button"].addEventListener("click", () => { void commitChanges(); });
  el["git-push-button"].addEventListener("click", () => { void pushBranch(); });
  el["git-open-pr-button"].addEventListener("click", () => { void openPullRequest(); });

  function holdSiblings(hold) {
    const holdId = hold.metadata?.holdID;
    if (holdId == null) return [hold];
    return state.document.regions.filter((region) => region.metadata?.holdID === holdId);
  }

  function holdCentroid(regions) {
    let sumX = 0, sumY = 0, count = 0;
    for (const region of regions) {
      let commands;
      try { commands = parsePath(region.displayPath); } catch { continue; }
      for (const cmd of commands) {
        if (cmd.type === "Z") continue;
        const p = cmd.points[cmd.points.length - 1];
        sumX += p.x;
        sumY += p.y;
        count++;
      }
    }
    return count ? { x: sumX / count, y: sumY / count } : { x: 0, y: 0 };
  }

  function rotateHold(angleDegrees) {
    const hold = selectedHold();
    if (!hold) return;
    const siblings = holdSiblings(hold);
    const pivot = holdCentroid(siblings);
    const angleRadians = (angleDegrees * Math.PI) / 180;
    const originalPaths = siblings.map((region) => region.displayPath);
    const originalDirty = state.dirty;
    for (const region of siblings) {
      let commands;
      try { commands = parsePath(region.displayPath); } catch { continue; }
      rotatePath(commands, angleRadians, pivot);
      region.displayPath = serializePath(commands);
    }
    state.dirty = true;
    try {
      validateEditorDocument(state.document);
      setValidation();
      setStatus("Hold rotated. Save when ready.");
    } catch (error) {
      siblings.forEach((region, index) => { region.displayPath = originalPaths[index]; });
      state.dirty = originalDirty;
      setValidation(error.message || "Contour is invalid.");
      setStatus("Rotation reverted — contour is invalid.");
    }
    render();
  }

  el["rotate-ccw-button"].addEventListener("click", (event) => { rotateHold(event.shiftKey ? -45 : -15); });
  el["rotate-cw-button"].addEventListener("click", (event) => { rotateHold(event.shiftKey ? 45 : 15); });
  el["rotate-by-apply-button"].addEventListener("click", () => {
    const input = el["rotate-by-input"].value.trim();
    const angleDegrees = Number(input);
    if (!input || !Number.isFinite(angleDegrees) || angleDegrees === 0) {
      setValidation("Enter a finite, non-zero rotation in degrees.");
      setStatus("Enter a finite, non-zero rotation in degrees.");
      return;
    }
    rotateHold(angleDegrees);
  });

  function handleKeyDown(event) {
    const key = event.key;
    if (key === "[" || key === "]") {
      if (!selectedHold()) return;
      event.preventDefault();
      rotateHold(key === "]" ? (event.shiftKey ? 45 : 15) : (event.shiftKey ? -45 : -15));
      return;
    }
    if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(key)) return;
    const hold = selectedHold();
    if (!hold) return;
    event.preventDefault();
    const step = event.shiftKey ? 10 : 1;
    const dx = key === "ArrowRight" ? step : key === "ArrowLeft" ? -step : 0;
    const dy = key === "ArrowDown" ? step : key === "ArrowUp" ? -step : 0;
    let commands;
    try { commands = parsePath(hold.displayPath); } catch { return; }
    const originalPath = hold.displayPath;
    const originalDirty = state.dirty;
    for (const cmd of commands) {
      if (cmd.type === "Z") continue;
      for (const p of cmd.points) { p.x += dx; p.y += dy; }
      for (const c of cmd.controls) { c.x += dx; c.y += dy; }
    }
    hold.displayPath = serializePath(commands);
    state.dirty = true;
    try {
      validateEditorDocument(state.document);
      setValidation();
      setStatus("Hold nudged. Save when ready.");
    } catch (error) {
      hold.displayPath = originalPath;
      state.dirty = originalDirty;
      setValidation(error.message || "Contour is invalid.");
      setStatus("Nudge reverted — contour is invalid.");
    }
    render();
  }

  document.addEventListener("keydown", handleKeyDown);

  el["delete-hold-button"].addEventListener("click", () => {
    const hold = selectedHold();
    if (!hold) return;
    const proceed = dialogs.confirm(`Delete hold "${hold.key}"?`);
    if (!proceed) return;
    const holdId = hold.metadata.holdID;
    state.document.regions = state.document.regions.filter((r) => r.metadata.holdID !== holdId);
    state.selectedKey = null;
    state.dirty = true;
    try {
      validateEditorDocument(state.document);
      setValidation();
    } catch (error) {
      setValidation(error.message || "Document is invalid after deletion.");
    }
    setStatus("Hold deleted. Save when ready.");
    render();
  });

  el["hold-type-select"].addEventListener("change", () => {
    const hold = selectedHold();
    if (!hold) return;
    const type = el["hold-type-select"].value;
    const holdId = hold.metadata.holdID;
    const siblings = state.document.regions.filter((r) => r.metadata.holdID === holdId);
    const originalTypes = siblings.map((r) => r.type);
    const originalDirty = state.dirty;
    for (const region of siblings) region.type = type;
    state.dirty = true;
    try {
      validateEditorDocument(state.document);
      setValidation();
      setStatus("Hold recategorized. Save when ready.");
    } catch (error) {
      siblings.forEach((region, index) => { region.type = originalTypes[index]; });
      state.dirty = originalDirty;
      setValidation(error.message || "Hold type is invalid.");
    }
    render();
  });

  function nextHoldId() {
    const ids = new Set((state.document?.regions || []).map((region) => region.metadata.holdID));
    let n = ids.size + 1;
    while (ids.has(`hold-${n}`)) n++;
    return `hold-${n}`;
  }

  function nextRegionId() {
    const ids = (state.document?.regions || []).map((region) => region.id);
    return ids.length ? Math.max(...ids) + 1 : 1;
  }

  el["add-hold-button"].addEventListener("click", () => {
    if (!state.document) return;
    const { width, height } = state.document.canvas;
    const size = Math.max(20, Math.min(60, width * 0.06, height * 0.06));
    const cx = width / 2;
    const cy = height / 2;
    const holdId = nextHoldId();
    const region = {
      id: nextRegionId(),
      key: `${holdId}-piece-0`,
      type: "edge",
      displayPath: `M ${cx - size} ${cy - size} L ${cx + size} ${cy - size} L ${cx + size} ${cy + size} L ${cx - size} ${cy + size} Z`,
      metadata: { holdID: holdId, pieceIndex: 0 },
    };
    state.document.regions.push(region);
    state.selectedKey = region.key;
    state.dirty = true;
    try {
      validateEditorDocument(state.document);
      setValidation();
      setStatus("Hold added. Drag it into place and save when ready.");
    } catch (error) {
      state.document.regions.pop();
      state.selectedKey = null;
      setValidation(error.message || "Could not add hold.");
    }
    render();
  });

  void (async () => {
    await refreshAuthState();
    await gitOperations.perform(async () => {
      await refreshGitState();
    });
    await refreshBoards();
  })();
})();
