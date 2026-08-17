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
  const { parsePath, serializePath, moveVertex, addVertex, deleteVertex } = (() => {
    try { return require("./path-editor.js"); } catch { return globalThis.HoldPathEditor || {}; }
  })();
  const TYPE_COLORS = { jug: "#ff754f", sloper: "#32bbc1", edge: "#9a6cf2", pocket: "#ee4d97", pinch: "#f2c94c" };
  const state = { boards: [], board: null, document: null, image: null, selectedKey: null, busy: false, dirty: false };
  const el = Object.fromEntries([
    "board-list", "boards-error", "refresh-boards-button", "save-button", "save-state", "board-status",
    "board-name", "editor-svg", "board-image", "hold-overlay", "empty-state", "editor-status",
    "validation-panel", "validation-list", "hold-heading", "hold-empty", "hold-form", "hold-key",
  ].map((id) => [id, document.getElementById(id)]));
  const boardOperations = createBoardOperationCoordinator({
    onBusyChange: (busy) => {
      state.busy = busy;
      render();
    },
  });

  function clone(value) { return JSON.parse(JSON.stringify(value)); }

  function selectedHold() {
    return state.document?.regions.find((region) => region.key === state.selectedKey) || null;
  }

  function setStatus(message) { el["editor-status"].textContent = message; }

  function setValidation(error = "") {
    el["validation-list"].replaceChildren();
    el["validation-panel"].classList.toggle("hidden", !error);
    if (!error) return;
    const item = document.createElement("li");
    item.textContent = error;
    el["validation-list"].append(item);
  }

  function renderSaveState() {
    el["save-button"].disabled = !state.board || state.busy;
    el["refresh-boards-button"].disabled = state.busy;
    el["save-state"].textContent = !state.board ? "No board selected" : state.busy ? "Working…" : state.dirty ? "Unsaved changes" : "Saved";
  }

  function renderBoards() {
    el["board-list"].replaceChildren();
    for (const board of state.boards) {
      const button = document.createElement("button");
      const title = document.createElement("span");
      const detail = document.createElement("small");
      button.type = "button";
      button.className = `region-item${state.board?.boardId === board.boardId ? " selected" : ""}`;
      button.disabled = state.busy;
      title.className = "region-key";
      title.textContent = board.displayName;
      detail.className = "region-type";
      detail.textContent = `${board.holdCount} holds`;
      button.append(title, detail);
      button.addEventListener("click", () => {
        if (!state.busy) void selectBoard(board.boardId);
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

  const drag = { active: false, type: null, holdKey: null, commandIndex: -1, controlIndex: -1, startX: 0, startY: 0, commands: null, originalPath: null, originalDirty: false };

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
    if (target.classList.contains("path-editor-vertex")) {
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
  }

  function handlePointerMove(event) {
    if (!drag.active) return;
    event.preventDefault();
    const pt = svgPoint(event);
    const dx = pt.x - drag.startX;
    const dy = pt.y - drag.startY;
    const hold = state.document?.regions.find((r) => r.key === drag.holdKey);
    if (!hold) { drag.active = false; return; }
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

  function handlePointerUp() {
    if (!drag.active) return;
    drag.active = false;
    const hold = state.document?.regions.find((r) => r.key === drag.holdKey);
    if (!hold) return;
    try {
      validateEditorDocument(state.document);
      setValidation();
      setStatus("Contour updated. Save when ready.");
    } catch (error) {
      hold.displayPath = drag.originalPath;
      state.dirty = drag.originalDirty;
      setValidation(error.message || "Contour is invalid.");
      setStatus("Edit reverted — contour is invalid.");
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
        const originalPath = hold.displayPath;
        const originalDirty = state.dirty;
        addVertex(commands, i, pt.x, pt.y);
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

  function closestPointOnSegment(a, b, p) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return Math.hypot(p.x - a.x, p.y - a.y);
    let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
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
    if (state.busy) return;
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

  async function selectBoard(boardId) {
    if (state.busy) return;
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
    if (state.busy || !state.board || !state.document) return;
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

  el["refresh-boards-button"].addEventListener("click", () => { void refreshBoards(); });
  el["save-button"].addEventListener("click", () => { void saveBoard(); });
  el["editor-svg"].addEventListener("pointerdown", handlePointerDown);
  el["editor-svg"].addEventListener("pointermove", handlePointerMove);
  el["editor-svg"].addEventListener("pointerup", handlePointerUp);
  el["editor-svg"].addEventListener("dblclick", handleDoubleClick);
  el["editor-svg"].addEventListener("contextmenu", handleContextMenu);

  void refreshBoards();
})();
