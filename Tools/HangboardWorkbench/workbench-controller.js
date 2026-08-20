(function exposeWorkbenchController(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldWorkbenchController = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const CONSTRAINED_SHAPES = new Set(["oval", "circle", "pill", "roundedRectangle", "rectangle"]);

  function validateShapeConstraint(constraint, holdKey) {
    if (!constraint || typeof constraint !== "object" || Array.isArray(constraint)) {
      throw new Error(`Hold ${holdKey} has an invalid shape constraint`);
    }
    const keys = Object.keys(constraint);
    if (keys.length !== 2 || !Object.hasOwn(constraint, "shape") || !Object.hasOwn(constraint, "rotationDegrees")) {
      throw new Error(`Hold ${holdKey} shape constraint needs exactly shape and rotationDegrees`);
    }
    if (!CONSTRAINED_SHAPES.has(constraint.shape)) {
      throw new Error(`Hold ${holdKey} has an invalid shape constraint shape`);
    }
    if (typeof constraint.rotationDegrees !== "number" || !Number.isFinite(constraint.rotationDegrees)) {
      throw new Error(`Hold ${holdKey} shape constraint rotation must be finite`);
    }
    if (constraint.rotationDegrees < -180 || constraint.rotationDegrees >= 180) {
      throw new Error(`Hold ${holdKey} shape constraint rotation must be normalized to [-180, 180)`);
    }
  }

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
      if (Object.hasOwn(region, "shapeConstraint")) {
        validateShapeConstraint(region.shapeConstraint, region.key);
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

  function createBoardOperationCoordinator({ onBusyChange = () => {} } = {}) {
    if (typeof onBusyChange !== "function") throw new TypeError("Board busy callback must be a function");
    let activeToken = null;
    let nextToken = 0;

    async function perform(operation) {
      if (typeof operation !== "function") throw new TypeError("Board operation must be a function");
      if (activeToken !== null) return { started: false, value: undefined };
      const token = ++nextToken;
      activeToken = token;
      onBusyChange(true);
      try {
        const value = await operation({ isCurrent: () => activeToken === token });
        return { started: true, value };
      } finally {
        if (activeToken === token) {
          activeToken = null;
          onBusyChange(false);
        }
      }
    }

    return Object.freeze({
      perform,
      get isBusy() { return activeToken !== null; },
    });
  }

  return Object.freeze({
    createBoardOperationCoordinator,
    loadBoardAtomically,
    saveBoardAtomically,
    validateEditorDocument,
  });
}));
