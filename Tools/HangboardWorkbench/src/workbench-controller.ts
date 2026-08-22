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

function isFingerCapacity(value: unknown): value is number {
  return Number.isInteger(value) && typeof value === "number" && value >= 1 && value <= 4;
}

function isMillimeterRange(value: unknown): value is { lowerBound: number; upperBound: number } {
  if (!isRecord(value)) return false;
  const { lowerBound, upperBound } = value;
  return Number.isInteger(lowerBound)
    && Number.isInteger(upperBound)
    && typeof lowerBound === "number"
    && typeof upperBound === "number"
    && lowerBound > 0
    && upperBound >= lowerBound;
}

function isHandCapacity(value: unknown): value is number {
  return Number.isInteger(value) && typeof value === "number" && value >= 1 && value <= 2;
}

function isHoldRegion(value: unknown): value is HoldRegion {
  if (!isRecord(value)) return false;
  const metadata = value.metadata;
  return typeof value.key === "string"
    && typeof value.displayPath === "string"
    && (value.id === undefined || typeof value.id === "number")
    && (value.type === undefined || typeof value.type === "string")
    && (value.fingerCapacity === undefined || isFingerCapacity(value.fingerCapacity))
    && (value.depthRangeMillimeters === undefined || isMillimeterRange(value.depthRangeMillimeters))
    && (value.handCapacity === undefined || isHandCapacity(value.handCapacity))
    && (value.shapeConstraint === undefined || isShapeConstraint(value.shapeConstraint))
    && (metadata === undefined
      || (isRecord(metadata)
        && typeof metadata.holdID === "string"
        && typeof metadata.pieceIndex === "number"));
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
  const keys = new Set<string>();
  const fingerCapacityByHoldId = new Map<string, number | undefined>();
  const depthRangeByHoldId = new Map<string, { lowerBound: number; upperBound: number } | undefined>();
  const handCapacityByHoldId = new Map<string, number | undefined>();
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
    if (Object.hasOwn(region, "fingerCapacity")
      && !isFingerCapacity(region.fingerCapacity)) {
      throw new Error(`Hold ${region.key} finger capacity must be between 1 and 4`);
    }
    if (Object.hasOwn(region, "depthRangeMillimeters")
      && !isMillimeterRange(region.depthRangeMillimeters)) {
      throw new Error(`Hold ${region.key} depth range must be positive and ordered`);
    }
    if (Object.hasOwn(region, "handCapacity")
      && !isHandCapacity(region.handCapacity)) {
      throw new Error(`Hold ${region.key} hand capacity must be between 1 and 2`);
    }
    if (!isHoldRegion(region)) {
      throw new Error(`Hold ${region.key} needs valid hold fields`);
    }
    if (region.metadata) {
      const { holdID } = region.metadata;
      if (fingerCapacityByHoldId.has(holdID)
        && fingerCapacityByHoldId.get(holdID) !== region.fingerCapacity) {
        throw new Error(`Hold ${holdID} pieces must share one finger capacity`);
      }
      fingerCapacityByHoldId.set(holdID, region.fingerCapacity);
      const depthRange = region.depthRangeMillimeters;
      const existingDepthRange = depthRangeByHoldId.get(holdID);
      if (depthRangeByHoldId.has(holdID)
        && (existingDepthRange?.lowerBound !== depthRange?.lowerBound
          || existingDepthRange?.upperBound !== depthRange?.upperBound)) {
        throw new Error(`Hold ${holdID} pieces must share one depth range`);
      }
      depthRangeByHoldId.set(holdID, depthRange);
      if (handCapacityByHoldId.has(holdID)
        && handCapacityByHoldId.get(holdID) !== region.handCapacity) {
        throw new Error(`Hold ${holdID} pieces must share one hand capacity`);
      }
      handCapacityByHoldId.set(holdID, region.handCapacity);
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
