import assert from "node:assert/strict";
import test from "node:test";
import React from "react";

import { ContactCanvas } from "../src/components/ContactCanvas.tsx";
import { ContactInspector } from "../src/components/ContactInspector.tsx";
import { cloneEditorDocument } from "../src/editor-model.ts";
import * as pathEditor from "../src/path-editor.ts";
import { useContactEditor, type ContactEditorActions } from "../src/useContactEditor.ts";
import type { Board, EditorDocument, WorkbenchActions } from "../src/types.ts";
import { validateEditorDocument } from "../src/workbench-controller.ts";
import { renderReact } from "./react-harness.tsx";

const PATH = "M 10 10 L 40 10 L 40 40 L 10 40 Z";

function documentFixture(constrained = false): EditorDocument {
  return {
    presentationID: "primary",
    contacts: [{
      id: "edge-left",
      equipmentObjectID: "primary",
      name: "Left edge",
      kind: "edge",
      features: ["largeEdge"],
      gripTypes: ["openHand"],
      depthRangeMillimeters: { lowerBound: 18, upperBound: 20 },
      fingerCapacity: 4,
      handCapacity: 1,
      side: "left",
    }],
    canvas: { width: 100, height: 60 },
    regions: [{
      id: 1,
      key: "edge-left-piece-0",
      displayPath: PATH,
      metadata: { contactID: "edge-left", pieceIndex: 0, presentationID: "primary" },
      treatment: { type: "surface" },
      ...(constrained ? { shapeConstraint: { shape: "rectangle" as const, rotationDegrees: 0 } } : {}),
    }],
  };
}

function boardFixture(document: EditorDocument): Board {
  return {
    boardId: "fixture.board",
    displayName: "Fixture Board",
    contactCount: document.contacts.length,
    imageUrl: "/fixture.png",
    document,
  };
}

function editorStub(overrides: Partial<ContactEditorActions> = {}): ContactEditorActions {
  const noop = (): void => {};
  return {
    editablePath: null,
    selectedAnchorID: null,
    vertexMenu: null,
    canDeleteSelectedVertex: false,
    selectedVertexIsInflection: false,
    canRoundSelectedVertex: false,
    canAddInflectionPoint: false,
    canMakeSelectedSegmentBendable: false,
    canMakeSelectedSegmentStraight: false,
    canMakeSelectedSegmentHorizontal: false,
    canMakeSelectedSegmentVertical: false,
    addContact: noop,
    addContactPiece: noop,
    duplicateAndMirrorContact: noop,
    deleteContact: noop,
    selectAnchor: noop,
    deleteSelectedVertex: noop,
    roundSelectedVertex: noop,
    addInflectionPoint: noop,
    makeSelectedSegmentBendable: noop,
    makeSelectedSegmentStraight: noop,
    makeSelectedSegmentHorizontal: noop,
    makeSelectedSegmentVertical: noop,
    dismissVertexMenu: noop,
    changeDisplayPath: noop,
    changeTreatment: noop,
    changeOutlineShape: noop,
    rotateContact: noop,
    applyRotation: noop,
    cancelActiveEdit: () => false,
    onPointerDown: noop,
    onPointerMove: noop,
    onPointerUp: noop,
    onPointerCancel: noop,
    onLostPointerCapture: noop,
    onDoubleClick: noop,
    onContextMenu: noop,
    ...overrides,
  };
}

function EditorInteractionHarness({
  initial = documentFixture(),
  prompts = [],
  onDocument,
}: {
  initial?: EditorDocument;
  prompts?: string[];
  onDocument(document: EditorDocument): void;
}) {
  const [document, setDocument] = React.useState(initial);
  const selectedRegion = document.regions[0] ?? null;
  const promptQueue = React.useRef([...prompts]);
  React.useEffect(() => onDocument(document), [document, onDocument]);
  const actions = React.useMemo(() => ({
    editDocument(edit: (value: EditorDocument) => void): boolean {
      const candidate = cloneEditorDocument(document);
      edit(candidate);
      validateEditorDocument(candidate);
      setDocument(candidate);
      return true;
    },
    replaceDocument(candidate: EditorDocument): EditorDocument {
      validateEditorDocument(candidate);
      setDocument(candidate);
      return candidate;
    },
    undoDocument: () => false,
    redoDocument: () => false,
  } as unknown as WorkbenchActions), [document]);
  const editor = useContactEditor({
    document,
    selectedRegion,
    selectedKeys: selectedRegion ? [selectedRegion.key] : [],
    dirty: false,
    status: "Ready",
    busy: false,
    rotationDegrees: "90",
    actions,
    pathEditor,
    validateEditorDocument,
    dialogs: {
      confirm: () => true,
      prompt: () => promptQueue.current.shift() ?? null,
    },
    horizontalGuideYs: [],
    verticalGuideXs: [],
  });
  return <>
    <button id="add-piece" onClick={editor.addContactPiece}>Add piece</button>
    <button id="duplicate-mirror" onClick={editor.duplicateAndMirrorContact}>Duplicate and mirror</button>
    <button id="make-oval" onClick={() => editor.changeOutlineShape("oval")}>Oval</button>
    <button id="rotate" onClick={() => editor.rotateContact(90)}>Rotate</button>
    <ContactCanvas
      board={boardFixture(document)}
      document={document}
      selectedKey={selectedRegion?.key ?? null}
      selectedKeys={selectedRegion ? [selectedRegion.key] : []}
      busy={false}
      onSelectContact={() => {}}
      pathEditor={pathEditor}
      editor={editor}
      zoomPercent={100}
      onZoomChange={() => true}
      canZoomChange={() => true}
      onPinchZoomChange={() => true}
      canPinchZoomChange={() => true}
      guides={[]}
      onMoveGuide={() => {}}
    />
  </>;
}

test("canvas colors media geometry from its contact fact owner", async () => {
  const document = documentFixture();
  const harness = await renderReact(<ContactCanvas
    board={boardFixture(document)}
    document={document}
    selectedKey="edge-left-piece-0"
    selectedKeys={["edge-left-piece-0"]}
    busy={false}
    onSelectContact={() => {}}
    pathEditor={pathEditor}
    editor={editorStub()}
    zoomPercent={100}
    onZoomChange={() => true}
    canZoomChange={() => true}
    onPinchZoomChange={() => true}
    canPinchZoomChange={() => true}
    guides={[]}
    onMoveGuide={() => {}}
  />);
  try {
    const path = harness.document.querySelector<SVGPathElement>("[data-contact-key='edge-left-piece-0']");
    assert.equal(path?.getAttribute("d"), PATH);
    assert.equal(path?.getAttribute("fill"), "#9a6cf2");
    assert.equal(harness.document.querySelectorAll(".path-editor-vertex").length, 0);
  } finally {
    await harness.cleanup();
  }
});

test("canvas preserves constrained resize and rotation controls", async () => {
  const document = documentFixture(true);
  const harness = await renderReact(<ContactCanvas
    board={boardFixture(document)}
    document={document}
    selectedKey="edge-left-piece-0"
    selectedKeys={["edge-left-piece-0"]}
    busy={false}
    onSelectContact={() => {}}
    pathEditor={pathEditor}
    editor={editorStub()}
    zoomPercent={100}
    onZoomChange={() => true}
    canZoomChange={() => true}
    onPinchZoomChange={() => true}
    canPinchZoomChange={() => true}
    guides={[]}
    onMoveGuide={() => {}}
  />);
  try {
    assert.equal(harness.document.querySelectorAll(".path-editor-resize-handle").length, 8);
    assert.equal(harness.document.querySelectorAll(".path-editor-rotation-handle").length, 1);
  } finally {
    await harness.cleanup();
  }
});

test("inspector sends factual edits and media treatment edits to distinct owners", async () => {
  const source = documentFixture();
  let document = cloneEditorDocument(source);
  const harness = await renderReact(<ContactInspector
    region={document.regions[0]!}
    contact={document.contacts[0]!}
    selectedCount={1}
    busy={false}
    rotationDegrees=""
    onRotationDegreesChange={() => {}}
    onContactChange={(contact) => { document.contacts[0] = contact; }}
    onDisplayPathChange={(displayPath) => { document.regions[0]!.displayPath = displayPath; }}
    onTreatmentChange={(treatment) => {
      if (treatment) document.regions[0]!.treatment = treatment;
      else delete document.regions[0]!.treatment;
    }}
    gastonPairCandidates={[]}
    onOutlineShapeChange={() => {}}
    onRotate={() => {}}
    onApplyRotation={() => {}}
    onAddSegment={() => {}}
    onDuplicateAndMirror={() => {}}
    onDelete={() => {}}
    onMobileCollapse={() => {}}
  />);
  try {
    const name = [...harness.document.querySelectorAll("label")].find((label) => label.textContent?.startsWith("Name"))?.querySelector("input");
    const treatment = [...harness.document.querySelectorAll("label")].find((label) => label.textContent?.startsWith("Geometry treatment"))?.querySelector("select");
    assert.ok(name);
    assert.ok(treatment);
    await harness.input("#contact-name", "Reviewed edge");
    await harness.change("#contact-treatment", "recess");
    assert.equal(document.contacts[0]!.name, "Reviewed edge");
    assert.deepEqual(document.regions[0]!.treatment, { type: "recess", rimInsetFraction: 0.15, depth: "shallow" });
    assert.equal((document.regions[0] as unknown as Record<string, unknown>).name, undefined);
    assert.equal((document.contacts[0] as unknown as Record<string, unknown>).treatment, undefined);
  } finally {
    await harness.cleanup();
  }
});

test("full editor adds a second media piece without duplicating contact facts", async () => {
  let current = documentFixture();
  const harness = await renderReact(<EditorInteractionHarness onDocument={(document) => { current = document; }} />);
  try {
    await harness.click("#add-piece");
    assert.equal(current.contacts.length, 1);
    assert.equal(current.regions.length, 2);
    assert.deepEqual(current.regions.map((region) => region.metadata.pieceIndex), [0, 1]);
    assert.equal(current.regions[1]!.metadata.contactID, "edge-left");
  } finally {
    await harness.cleanup();
  }
});

test("full editor mirrors geometry only after explicit factual identity input", async () => {
  let current = documentFixture();
  const harness = await renderReact(<EditorInteractionHarness
    prompts={["edge-right", "Right edge"]}
    onDocument={(document) => { current = document; }}
  />);
  try {
    await harness.click("#duplicate-mirror");
    assert.deepEqual(current.contacts.map((contact) => contact.id), ["edge-left", "edge-right"]);
    assert.equal(current.contacts[1]!.name, "Right edge");
    assert.equal(current.contacts[1]!.side, undefined);
    assert.equal(current.regions[1]!.metadata.contactID, "edge-right");
    assert.equal(current.regions[1]!.displayPath, "M 90 10 L 60 10 L 60 40 L 90 40 Z");
  } finally {
    await harness.cleanup();
  }
});

test("full editor preserves constrained outline and rotation authoring", async () => {
  let current = documentFixture();
  const originalFacts = cloneEditorDocument(current).contacts;
  const harness = await renderReact(<EditorInteractionHarness onDocument={(document) => { current = document; }} />);
  try {
    await harness.click("#make-oval");
    assert.equal(current.regions[0]!.shapeConstraint?.shape, "oval");
    const ovalPath = current.regions[0]!.displayPath;
    await harness.click("#rotate");
    assert.notEqual(current.regions[0]!.displayPath, ovalPath);
    assert.equal(current.regions[0]!.shapeConstraint?.rotationDegrees, 90);
    assert.deepEqual(current.contacts, originalFacts);
  } finally {
    await harness.cleanup();
  }
});

test("keyboard nudge edits canonical media geometry without changing facts", async () => {
  let current = documentFixture();
  const originalFacts = cloneEditorDocument(current).contacts;
  const harness = await renderReact(<EditorInteractionHarness onDocument={(document) => { current = document; }} />);
  try {
    const prevented = await harness.keyDown("#editor-svg", "ArrowRight");
    assert.equal(prevented, true);
    assert.equal(current.regions[0]!.displayPath, "M 11 10 L 41 10 L 41 40 L 11 40 Z");
    assert.deepEqual(current.contacts, originalFacts);
  } finally {
    await harness.cleanup();
  }
});
