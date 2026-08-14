(() => {
  "use strict";

  const client = globalThis.HoldWorkbenchClient;
  const { loadBoardAtomically, saveBoardAtomically, validateEditorDocument } = globalThis.HoldWorkbenchController;
  const svgNS = "http://www.w3.org/2000/svg";
  const TYPE_COLORS = { jug: "#ff754f", sloper: "#32bbc1", edge: "#9a6cf2", pocket: "#ee4d97", pinch: "#f2c94c" };
  const state = { boards: [], board: null, document: null, image: null, selectedKey: null, busy: false, dirty: false };
  const el = Object.fromEntries([
    "board-list", "boards-error", "refresh-boards-button", "save-button", "save-state", "board-status",
    "board-name", "editor-svg", "board-image", "hold-overlay", "empty-state", "editor-status",
    "validation-panel", "validation-list", "hold-heading", "hold-empty", "hold-form", "hold-key", "hold-path",
  ].map((id) => [id, document.getElementById(id)]));

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
      title.className = "region-key";
      title.textContent = board.displayName;
      detail.className = "region-type";
      detail.textContent = `${board.holdCount} holds`;
      button.append(title, detail);
      button.addEventListener("click", () => { void selectBoard(board.boardId); });
      el["board-list"].append(button);
    }
  }

  function renderEditor() {
    const documentValue = state.document;
    const selected = selectedHold();
    el["empty-state"].classList.toggle("hidden", Boolean(documentValue));
    el["hold-overlay"].replaceChildren();
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
  }

  function renderInspector() {
    const hold = selectedHold();
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
    state.busy = true;
    renderSaveState();
    el["boards-error"].classList.add("hidden");
    try {
      state.boards = await client.listBoards();
      renderBoards();
      setStatus("Boards loaded.");
    } catch (error) {
      el["boards-error"].textContent = error.message || "Could not load boards.";
      el["boards-error"].classList.remove("hidden");
      setStatus("Could not load boards.");
    } finally {
      state.busy = false;
      renderSaveState();
    }
  }

  async function selectBoard(boardId) {
    state.busy = true;
    setValidation();
    renderSaveState();
    try {
      await loadBoardAtomically({
        boardId,
        getBoard: client.getBoard,
        loadImage,
        commit: ({ board, document: documentValue, image }) => {
          state.board = board;
          state.document = clone(documentValue);
          state.image = image;
          state.selectedKey = null;
          state.dirty = false;
        },
      });
      setStatus("Board loaded.");
      render();
    } catch (error) {
      setValidation(error.message || "Could not load board.");
      setStatus("Could not load board. The current editor was kept.");
    } finally {
      state.busy = false;
      renderSaveState();
    }
  }

  function applyHold(event) {
    event.preventDefault();
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
    if (!state.board || !state.document) return;
    try {
      validateEditorDocument(state.document);
    } catch (error) {
      setValidation(error.message || "Hold document is invalid.");
      return;
    }
    state.busy = true;
    renderSaveState();
    try {
      await saveBoardAtomically({
        boardId: state.board.boardId,
        document: state.document,
        save: client.saveBoard,
        commit: ({ board, document: documentValue }) => {
          state.board = board;
          state.document = clone(documentValue);
          state.dirty = false;
        },
      });
      setValidation();
      setStatus("Board saved.");
      render();
    } catch (error) {
      setValidation(error.message || "Could not save board.");
      setStatus("Could not save board. Your editor changes were kept.");
    } finally {
      state.busy = false;
      renderSaveState();
    }
  }

  el["refresh-boards-button"].addEventListener("click", () => { void refreshBoards(); });
  el["hold-form"].addEventListener("submit", applyHold);
  el["save-button"].addEventListener("click", () => { void saveBoard(); });
  void refreshBoards();
})();
