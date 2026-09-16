import assert from "node:assert/strict";
import test from "node:test";

import { cloneEditorDocument } from "../src/editor-model.ts";
import {
  saveBoardAtomically,
  validateEditorDocument,
  validateEditorDocumentForSave,
} from "../src/workbench-controller.ts";
import type { Board, EditorDocument } from "../src/types.ts";

const PATH = "M 10 10 L 30 10 L 30 30 L 10 30 Z";

function document(): EditorDocument {
  return {
    presentationID: "primary",
    contacts: [{
      id: "edge-left",
      equipmentObjectID: "primary",
      name: "Left edge",
      kind: "edge",
      features: ["largeEdge"],
      gripTypes: ["openHand"],
      depth: { range: { minimum: 18, maximum: 20 } },
      fingerCapacity: 4,
      handCapacity: 1,
      side: "left",
    }],
    canvas: { width: 100, height: 50 },
    regions: [{
      id: 1,
      key: "edge-left-piece-0",
      displayPath: PATH,
      metadata: { contactID: "edge-left", pieceIndex: 0, presentationID: "primary" },
      treatment: { type: "surface" },
    }],
  };
}

test("contact facts and media geometry validate in distinct owners", () => {
  const value = document();
  assert.equal(validateEditorDocument(value), value);

  const factual = cloneEditorDocument(value);
  factual.contacts[0]!.name = "Reviewed edge";
  assert.equal(validateEditorDocumentForSave(factual), factual);

  const geometric = cloneEditorDocument(value);
  geometric.regions[0]!.displayPath = "M 12 12 L 32 12 L 32 32 L 12 32 Z";
  geometric.regions[0]!.treatment = { type: "shelf", rimInsetFraction: 0.2 };
  assert.equal(validateEditorDocumentForSave(geometric), geometric);
});

test("contacts accept exactly one tagged depth representation", () => {
  const category = document() as unknown as {
    contacts: Array<Record<string, unknown>>;
  };
  category.contacts[0]!.depth = { category: "large" };
  assert.equal(validateEditorDocument(category), category);

  const range = document() as unknown as {
    contacts: Array<Record<string, unknown>>;
  };
  range.contacts[0]!.depth = { range: { minimum: 25, maximum: 30 } };
  assert.equal(validateEditorDocument(range), range);

  const invalid = document() as unknown as {
    contacts: Array<Record<string, unknown>>;
  };
  invalid.contacts[0]!.depth = { category: "large", range: { minimum: 25, maximum: 30 } };
  assert.throws(() => validateEditorDocument(invalid), /valid factual contacts/);

  const legacy = document() as unknown as {
    contacts: Array<Record<string, unknown>>;
  };
  delete legacy.contacts[0]!.depth;
  legacy.contacts[0]!.depthRangeMillimeters = { lowerBound: 25, upperBound: 30 };
  assert.throws(() => validateEditorDocument(legacy), /valid factual contacts/);
});

test("legacy IDs and factual fields inside regions are rejected", () => {
  const legacyID = cloneEditorDocument(document()) as unknown as {
    regions: Array<Record<string, unknown>>;
  };
  legacyID.regions[0]!.metadata = { holdID: "edge-left", pieceIndex: 0, presentationID: "primary" };
  assert.throws(() => validateEditorDocument(legacyID), /valid media regions/);

  const duplicatedFact = cloneEditorDocument(document()) as unknown as {
    regions: Array<Record<string, unknown>>;
  };
  duplicatedFact.regions[0]!.kind = "edge";
  assert.throws(() => validateEditorDocument(duplicatedFact), /valid media regions/);
});

test("contact facts are closed and gaston pairs are strict at save", () => {
  const unknownFact = cloneEditorDocument(document()) as unknown as {
    contacts: Array<Record<string, unknown>>;
  };
  unknownFact.contacts[0]!.holdName = "legacy";
  assert.throws(() => validateEditorDocument(unknownFact), /valid factual contacts/);

  const unpaired = cloneEditorDocument(document());
  unpaired.contacts[0]!.kind = "gaston";
  assert.equal(validateEditorDocument(unpaired), unpaired);
  assert.throws(() => validateEditorDocumentForSave(unpaired), /paired gaston contact/);
});

test("cloning does not alias factual arrays or geometry metadata", () => {
  const source = document();
  const copy = cloneEditorDocument(source);
  copy.contacts[0]!.features.push("smallEdge");
  copy.regions[0]!.treatment!.type = "recess";
  assert.deepEqual(source.contacts[0]!.features, ["largeEdge"]);
  assert.deepEqual(source.regions[0]!.treatment, { type: "surface" });
});

test("atomic save transmits the native contact document", async () => {
  const value = document();
  const board: Board = {
    boardId: "fixture.board",
    displayName: "Fixture Board",
    contactCount: 1,
    imageUrl: "/image.png",
    document: value,
  };
  let transmitted: EditorDocument | null = null;
  let committed = false;
  await saveBoardAtomically({
    boardId: board.boardId,
    document: value,
    save: async (_boardID, payload) => {
      transmitted = payload;
      return board;
    },
    commit: () => { committed = true; },
  });
  assert.equal(transmitted, value);
  assert.equal(committed, true);
});
