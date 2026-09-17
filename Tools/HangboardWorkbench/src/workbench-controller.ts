import type {
  BoardOperationCoordinator,
  ContactRegion,
  EditorDocument,
  LoadedBoard,
  PhysicalContact,
  SavedBoard,
} from "./types.ts";
import { validateShapeConstraint } from "./shape-constraints.ts";

const IDENTIFIER = /^[a-z0-9]+(?:[a-z0-9._-]*[a-z0-9])?$/;
const CONTACT_KINDS = new Set(["jug", "edge", "pocket", "pinch", "sloper", "gaston"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function exactKeys(value: Record<string, unknown>, required: readonly string[], optional: readonly string[] = []): boolean {
  const keys = Object.keys(value);
  return required.every((key) => keys.includes(key))
    && keys.every((key) => required.includes(key) || optional.includes(key));
}

function isIdentifier(value: unknown): value is string {
  return typeof value === "string" && IDENTIFIER.test(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isMillimeterRange(value: unknown): boolean {
  if (!isRecord(value) || !exactKeys(value, ["minimum", "maximum"])) return false;
  return typeof value.minimum === "number" && Number.isFinite(value.minimum)
    && typeof value.maximum === "number" && Number.isFinite(value.maximum)
    && value.minimum >= 0 && value.maximum >= value.minimum;
}

function isHoldDepth(value: unknown): boolean {
  if (!isRecord(value)) return false;
  if (exactKeys(value, ["category"])) {
    return value.category === "tiny" || value.category === "small"
      || value.category === "medium" || value.category === "large";
  }
  return exactKeys(value, ["range"]) && isMillimeterRange(value.range);
}

function isPhysicalContact(value: unknown): value is PhysicalContact {
  if (!isRecord(value) || !exactKeys(
    value,
    ["id", "equipmentObjectID", "name", "kind", "gripTypes"],
    ["shape", "depth", "fingerCapacity", "handCapacity", "side", "pairedContactID"],
  )) return false;
  if (!isIdentifier(value.id) || !isIdentifier(value.equipmentObjectID)
    || typeof value.name !== "string" || value.name.length === 0
    || typeof value.kind !== "string" || !CONTACT_KINDS.has(value.kind)
    || !isStringArray(value.gripTypes) || new Set(value.gripTypes).size !== value.gripTypes.length) return false;
  if (value.shape !== undefined
    && value.shape !== "flat" && value.shape !== "round"
    && value.shape !== "incut" && value.shape !== "slot") return false;
  if (value.depth !== undefined && !isHoldDepth(value.depth)) return false;
  if (value.fingerCapacity !== undefined
    && (typeof value.fingerCapacity !== "number" || !Number.isInteger(value.fingerCapacity)
      || value.fingerCapacity < 1 || value.fingerCapacity > 4)) return false;
  if (value.handCapacity !== undefined
    && (typeof value.handCapacity !== "number" || !Number.isInteger(value.handCapacity)
      || value.handCapacity < 1 || value.handCapacity > 2)) return false;
  if (value.side !== undefined && value.side !== "left" && value.side !== "right") return false;
  if (value.kind === "gaston") {
    if (value.pairedContactID !== undefined
      && (!isIdentifier(value.pairedContactID) || value.pairedContactID === value.id)) return false;
  } else if (value.pairedContactID !== undefined) return false;
  return true;
}

function isTreatment(value: unknown): boolean {
  if (!isRecord(value) || typeof value.type !== "string") return false;
  if (value.type === "surface") return exactKeys(value, ["type"]);
  if (value.type === "shelf") {
    return exactKeys(value, ["type", "rimInsetFraction"])
      && typeof value.rimInsetFraction === "number"
      && value.rimInsetFraction >= 0 && value.rimInsetFraction <= 0.5;
  }
  if (value.type === "recess") {
    return exactKeys(value, ["type", "rimInsetFraction", "depth"])
      && typeof value.rimInsetFraction === "number"
      && value.rimInsetFraction >= 0 && value.rimInsetFraction <= 0.5
      && (value.depth === "shallow" || value.depth === "deep");
  }
  return false;
}

function isIndexArray(value: unknown): value is number[] {
  return Array.isArray(value)
    && value.every((item) => Number.isInteger(item) && item >= 0)
    && new Set(value).size === value.length;
}

function isContactRegion(value: unknown, presentationID: string, contactIDs: Set<string>): value is ContactRegion {
  if (!isRecord(value) || !exactKeys(
    value,
    ["id", "key", "displayPath", "metadata"],
    ["treatment", "shapeConstraint", "bendableCommandIndexes", "smoothAnchorIndexes"],
  )) return false;
  if (!Number.isInteger(value.id) || typeof value.key !== "string" || !value.key
    || typeof value.displayPath !== "string" || !/^\s*M\s+[^MZ]+\s+Z\s*$/u.test(value.displayPath)
    || !isRecord(value.metadata)
    || !exactKeys(value.metadata, ["contactID", "pieceIndex", "presentationID"])
    || !isIdentifier(value.metadata.contactID)
    || !contactIDs.has(value.metadata.contactID)
    || typeof value.metadata.pieceIndex !== "number"
    || !Number.isInteger(value.metadata.pieceIndex) || value.metadata.pieceIndex < 0
    || value.metadata.presentationID !== presentationID) return false;
  if (value.treatment !== undefined && !isTreatment(value.treatment)) return false;
  if (value.shapeConstraint !== undefined) {
    try { validateShapeConstraint(value.shapeConstraint, `Contact ${value.key} shape constraint`); }
    catch { return false; }
  }
  return (value.bendableCommandIndexes === undefined || isIndexArray(value.bendableCommandIndexes))
    && (value.smoothAnchorIndexes === undefined || isIndexArray(value.smoothAnchorIndexes));
}

export function validateEditorDocument(document: unknown): EditorDocument {
  if (!isRecord(document) || !exactKeys(document, ["presentationID", "contacts", "canvas", "regions"])) {
    throw new TypeError("Contact editor document is required");
  }
  if (!isIdentifier(document.presentationID)) throw new Error("Contact editor needs a valid presentation");
  if (!isRecord(document.canvas) || !exactKeys(document.canvas, ["width", "height"])
    || typeof document.canvas.width !== "number" || document.canvas.width <= 0
    || typeof document.canvas.height !== "number" || document.canvas.height <= 0) {
    throw new Error("Contact editor needs a valid canvas");
  }
  if (!Array.isArray(document.contacts) || document.contacts.length === 0
    || !document.contacts.every(isPhysicalContact)) {
    throw new Error("Contact editor needs valid factual contacts");
  }
  const contactIDs = new Set(document.contacts.map((contact) => contact.id));
  if (contactIDs.size !== document.contacts.length) throw new Error("Contact IDs must be unique");
  for (const contact of document.contacts) {
    if (contact.pairedContactID !== undefined) {
      const pair = document.contacts.find((candidate) => candidate.id === contact.pairedContactID);
      if (!pair || pair.kind !== "gaston" || pair.pairedContactID !== contact.id) {
        throw new Error(`Contact ${contact.id} needs a reciprocal gaston pair`);
      }
    }
  }
  if (!Array.isArray(document.regions) || document.regions.length === 0
    || !document.regions.every((region) => isContactRegion(region, document.presentationID as string, contactIDs))) {
    throw new Error("Contact editor needs valid media regions");
  }
  const keys = new Set<string>();
  const indexes = new Map<string, Set<number>>();
  for (const region of document.regions as ContactRegion[]) {
    if (keys.has(region.key)) throw new Error("Contact region keys must be unique");
    keys.add(region.key);
    const contactIndexes = indexes.get(region.metadata.contactID) ?? new Set<number>();
    if (contactIndexes.has(region.metadata.pieceIndex)) {
      throw new Error(`Contact ${region.metadata.contactID} has a duplicate piece index`);
    }
    contactIndexes.add(region.metadata.pieceIndex);
    indexes.set(region.metadata.contactID, contactIndexes);
  }
  for (const [contactID, contactIndexes] of indexes) {
    if ([...contactIndexes].some((_, index) => !contactIndexes.has(index))) {
      throw new Error(`Contact ${contactID} piece indexes must be contiguous`);
    }
  }
  return document as unknown as EditorDocument;
}

export function validateEditorDocumentForSave(document: unknown): EditorDocument {
  const validated = validateEditorDocument(document);
  for (const contact of validated.contacts) {
    if (contact.kind === "gaston" && !contact.pairedContactID) {
      throw new Error(`Contact ${contact.id} needs a paired gaston contact`);
    }
  }
  return validated;
}

export async function loadBoardAtomically<ImageType>(options: {
  boardId: string;
  getBoard(boardId: string): Promise<import("./types.ts").Board>;
  loadImage(href: string): Promise<ImageType>;
  preloadedImage?: { href: string; promise: Promise<ImageType> };
  commit(value: LoadedBoard<ImageType>): void;
}): Promise<LoadedBoard<ImageType>> {
  const { boardId, getBoard, loadImage, preloadedImage, commit } = options;
  if (!boardId) throw new TypeError("Board ID is required");
  const preparedPreloadedImage = preloadedImage && Promise.resolve(preloadedImage.promise).then(
    (image) => ({ image }), (error: unknown) => ({ error }),
  );
  const board = await getBoard(boardId);
  if (!board || board.boardId !== boardId || !board.imageUrl) {
    throw new Error("Workbench returned an invalid board");
  }
  if (board.selectedPresentationID && board.document.presentationID !== board.selectedPresentationID) {
    throw new Error("Workbench returned a mismatched presentation");
  }
  validateEditorDocument(board.document);
  let image: ImageType;
  if (preloadedImage?.href === board.imageUrl && preparedPreloadedImage !== undefined) {
    const preparedImage = await preparedPreloadedImage;
    if ("error" in preparedImage) throw preparedImage.error;
    image = preparedImage.image;
  } else image = await loadImage(board.imageUrl);
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
  validateEditorDocumentForSave(document);
  const board = await save(boardId, document);
  if (!board || board.boardId !== boardId || !board.document) {
    throw new Error("Workbench returned an invalid saved board");
  }
  validateEditorDocumentForSave(board.document);
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
    get isBusy(): boolean { return activeToken !== null; },
  });
}
