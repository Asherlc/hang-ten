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
    "validation-panel", "validation-list", "hold-heading", "hold-empty", "hold-form", "hold-key", "hold-path", "apply-hold-button",
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

  function renderInspector() {
    const hold = selectedHold();
    el["apply-hold-button"].disabled = state.busy || !hold;
    el["hold-path"].disabled = state.busy || !hold;
    el["hold-empty"].classList.toggle("hidden", Boolean(hold));
    el["hold-form"].classList.toggle("hidden", !hold);
    el["hold-heading"].textContent = hold ? hold.key : "No selection";
    if (!hold) return;
    el["hold-key"].value = hold.key;
    el["hold-path"].value = hold.displayPath;
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

  function applyHold(event) {
    event.preventDefault();
    if (state.busy) return;
    const hold = selectedHold();
    if (!hold) return;
    const candidate = clone(state.document);
    candidate.regions.find((region) => region.key === hold.key).displayPath = el["hold-path"].value.trim();
    try {
      validateEditorDocument(candidate);
      state.document = candidate;
      state.dirty = true;
      setValidation();
      setStatus("Contour updated. Save when ready.");
      render();
    } catch (error) {
      setValidation(error.message || "Contour is invalid.");
    }
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
  el["hold-form"].addEventListener("submit", applyHold);
  el["save-button"].addEventListener("click", () => { void saveBoard(); });
  void refreshBoards();
})();
