import type {
  BoardOperationCoordinator,
  EditorDocument,
  HoldRegion,
  LoadedBoard,
  SavedBoard,
} from "./types.ts";
import { isShapeConstraint, validateShapeConstraint } from "./shape-constraints.ts";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isHoldRegion(value: unknown): value is HoldRegion {
  if (!isRecord(value)) return false;
  const metadata = value.metadata;
  return typeof value.key === "string"
    && typeof value.displayPath === "string"
    && (value.id === undefined || typeof value.id === "number")
    && (value.type === undefined || typeof value.type === "string")
    && (value.shapeConstraint === undefined || isShapeConstraint(value.shapeConstraint))
    && (metadata === undefined
      || (isRecord(metadata)
        && typeof metadata.holdID === "string"
        && typeof metadata.pieceIndex === "number"
        && (metadata.presentationID === undefined || typeof metadata.presentationID === "string")));
}

function isEditorDocument(value: unknown): value is EditorDocument {
  return isRecord(value)
    && typeof value.schemaVersion === "number"
    && isRecord(value.canvas)
    && typeof value.canvas.width === "number"
    && typeof value.canvas.height === "number"
    && Array.isArray(value.regions)
    && value.regions.every(isHoldRegion);
}

export function validateEditorDocument(document: unknown): EditorDocument {
  if (!isRecord(document)) {
    throw new TypeError("Hold document is required");
  }
  const canvas = document.canvas;
  if (!isRecord(canvas)
    || !Number.isFinite(canvas.width)
    || !Number.isFinite(canvas.height)
    || Number(canvas.width) <= 0
    || Number(canvas.height) <= 0) {
    throw new Error("Hold document needs a valid canvas");
  }
  if (!Array.isArray(document.regions)) throw new Error("Hold document needs holds");
  const presentationID = typeof document.presentationID === "string"
    ? document.presentationID
    : null;
  if (document.presentationID !== undefined && !presentationID) {
    throw new Error("Hold document needs a valid presentation");
  }
  const keys = new Set<string>();
  for (const region of document.regions) {
    if (!isRecord(region) || typeof region.key !== "string" || !region.key.trim()) {
      throw new Error("Every hold needs a key");
    }
    if (keys.has(region.key)) throw new Error("Every hold needs a unique hold key");
    keys.add(region.key);
    if (typeof region.displayPath !== "string"
      || !/^\s*M\s+[^MZ]+\s+Z\s*$/u.test(region.displayPath)) {
      throw new Error(`Hold ${region.key} needs one closed contour`);
    }
    if (Object.hasOwn(region, "shapeConstraint")) {
      validateShapeConstraint(region.shapeConstraint, `Hold ${region.key} shape constraint`);
    }
    if (!isHoldRegion(region)) {
      throw new Error(`Hold ${region.key} needs valid hold fields`);
    }
    if (presentationID && region.metadata?.presentationID !== presentationID) {
      throw new Error(`Hold ${region.key} must belong to the selected presentation`);
    }
  }
  if (!isEditorDocument(document)) {
    throw new TypeError("Hold document is required");
  }
  return document;
}

export async function loadBoardAtomically<ImageType>(options: {
  boardId: string;
  getBoard(boardId: string): Promise<import("./types.ts").Board>;
  loadImage(href: string): Promise<ImageType>;
  commit(value: LoadedBoard<ImageType>): void;
}): Promise<LoadedBoard<ImageType>> {
  const { boardId, getBoard, loadImage, commit } = options;
  if (!boardId) throw new TypeError("Board ID is required");
  const board = await getBoard(boardId);
  if (!board || board.boardId !== boardId || !board.imageUrl) {
    throw new Error("Workbench returned an invalid board");
  }
  if (board.selectedPresentationID
    && board.document.presentationID !== board.selectedPresentationID) {
    throw new Error("Workbench returned a mismatched presentation");
  }
  validateEditorDocument(board.document);
  const image = await loadImage(board.imageUrl);
  if (!image) throw new Error("Board image is unavailable");
  const loaded = Object.freeze({ board, image, document: board.document });
  commit(loaded);
  return loaded;
}

export async function saveBoardAtomically(options: {
  boardId: string;
  document: EditorDocument;
  save(boardId: string, document: EditorDocument): Promise<import("./types.ts").Board>;
  commit(value: SavedBoard): void;
}): Promise<SavedBoard> {
  const { boardId, document, save, commit } = options;
  if (!boardId) throw new TypeError("Board ID is required");
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

export function createBoardOperationCoordinator(options: {
  onBusyChange?: (busy: boolean) => void;
} = {}): BoardOperationCoordinator {
  const onBusyChange = options.onBusyChange ?? (() => {});
  let activeToken: number | null = null;
  let nextToken = 0;

  return Object.freeze({
    async perform<T>(operation: (context: { isCurrent(): boolean }) => Promise<T>) {
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
    },
    get isBusy(): boolean {
      return activeToken !== null;
    },
  });
}
