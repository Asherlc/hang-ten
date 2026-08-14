(function exposeWorkbenchController(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldWorkbenchController = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  function validateEditorDocument(document) {
    if (!document || typeof document !== "object" || Array.isArray(document)) {
      throw new TypeError("Hold document is required");
    }
    const canvas = document.canvas;
    if (!canvas || !Number.isFinite(canvas.width) || !Number.isFinite(canvas.height)
      || canvas.width <= 0 || canvas.height <= 0) {
      throw new Error("Hold document needs a valid canvas");
    }
    if (!Array.isArray(document.regions)) throw new Error("Hold document needs holds");
    const keys = new Set();
    for (const region of document.regions) {
      if (!region || typeof region.key !== "string" || !region.key.trim()) {
        throw new Error("Every hold needs a key");
      }
      if (keys.has(region.key)) throw new Error("Every hold needs a unique hold key");
      keys.add(region.key);
      if (typeof region.displayPath !== "string"
        || !/^\s*M\s+[^MZ]+\s+Z\s*$/u.test(region.displayPath)) {
        throw new Error(`Hold ${region.key} needs one closed contour`);
      }
    }
    return document;
  }

  async function loadBoardAtomically({ boardId, getBoard, loadImage, commit }) {
    if (typeof boardId !== "string" || !boardId) throw new TypeError("Board ID is required");
    if (typeof getBoard !== "function" || typeof loadImage !== "function" || typeof commit !== "function") {
      throw new TypeError("Board load callbacks are required");
    }
    const board = await getBoard(boardId);
    if (!board || board.boardId !== boardId || typeof board.imageUrl !== "string" || !board.imageUrl) {
      throw new Error("Workbench returned an invalid board");
    }
    validateEditorDocument(board.document);
    const image = await loadImage(board.imageUrl);
    if (!image) throw new Error("Board image is unavailable");
    const loaded = Object.freeze({ board, image, document: board.document });
    commit(loaded);
    return loaded;
  }

  async function saveBoardAtomically({ boardId, document, save, commit }) {
    if (typeof boardId !== "string" || !boardId) throw new TypeError("Board ID is required");
    if (typeof save !== "function" || typeof commit !== "function") {
      throw new TypeError("Board save callbacks are required");
    }
    validateEditorDocument(document);
    const board = await save(boardId, document);
    if (!board || board.boardId !== boardId || !board.document) {
      throw new Error("Workbench returned an invalid saved board");
    }
    validateEditorDocument(board.document);
    const saved = Object.freeze({ board, document: board.document });
    commit(saved);
    return saved;
  }

  return Object.freeze({ loadBoardAtomically, saveBoardAtomically, validateEditorDocument });
}));
