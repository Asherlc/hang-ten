import assert from "node:assert/strict";
import test from "node:test";
import React from "react";

import { WorkbenchApp } from "../src/WorkbenchApp.tsx";
import {
  holdCentroid,
  holdSiblings,
  nextHoldId,
  nextRegionId,
  normalizedRotationDegrees,
  rotationHandlePosition,
  svgPoint,
} from "../src/editor-model.ts";
import * as pathEditor from "../src/path-editor.ts";
import * as controller from "../src/workbench-controller.ts";
import type {
  AuthStatus,
  Board,
  BoardSummary,
  BrowserRuntime,
  CommitResult,
  Dialogs,
  EditorDocument,
  GitStatus,
  PullRequestResult,
  PushResult,
  WorkbenchClient,
  WorkbenchDependencies,
} from "../src/types.ts";
import { renderReact, type ReactHarness } from "./react-harness.tsx";

const FIRST_PATH = "M 10 10 L 20 10 L 20 20 Z";
const SECOND_PATH = "M 30 10 L 40 10 L 40 20 Z";
const OTHER_PATH = "M 70 10 L 80 10 L 80 20 Z";

function documentFixture(regions: EditorDocument["regions"] = [
  { id: 1, key: "a-piece-0", type: "jug", displayPath: FIRST_PATH, metadata: { holdID: "a", pieceIndex: 0 } },
  { id: 2, key: "a-piece-1", type: "jug", displayPath: SECOND_PATH, metadata: { holdID: "a", pieceIndex: 1 } },
  { id: 3, key: "b-piece-0", type: "edge", displayPath: OTHER_PATH, metadata: { holdID: "b", pieceIndex: 0 } },
]): EditorDocument {
  return { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions };
}

function boardFixture(document = documentFixture()): Board {
  return {
    boardId: "board-a",
    displayName: "Board A",
    holdCount: document.regions.length,
    imageUrl: "/api/boards/board-a/image",
    document,
  };
}

function gitStatus(): GitStatus {
  return { ok: true, currentBranch: "main", branches: ["main"], dirty: false, statusLines: [] };
}

function clientFixture(boards: readonly Board[]): WorkbenchClient {
  const firstBoard = boards[0];
  if (!firstBoard) throw new Error("At least one board fixture is required");
  return {
    async listBoards(): Promise<BoardSummary[]> {
      return boards.map((board) => ({
        boardId: board.boardId,
        displayName: board.displayName,
        holdCount: board.holdCount,
      }));
    },
    async getBoard(boardId): Promise<Board> {
      const board = boards.find((candidate) => candidate.boardId === boardId);
      if (!board) throw new Error(`Unknown board: ${boardId}`);
      return board;
    },
    async saveBoard(boardId, document): Promise<Board> {
      const board = boards.find((candidate) => candidate.boardId === boardId) ?? firstBoard;
      return { ...board, document };
    },
    async getGitStatus(): Promise<GitStatus> { return gitStatus(); },
    async getAuthStatus(): Promise<AuthStatus> { return { ok: true, authenticated: false }; },
    async listBranches(): Promise<GitStatus> { return gitStatus(); },
    async switchBranch(branchName): Promise<string> { return branchName; },
    async createBranch(branchName): Promise<string> { return branchName; },
    async commitBoardChanges(message): Promise<CommitResult> {
      return { ok: true, commit: "abcdef0", branch: "main", message };
    },
    async pushBranch(): Promise<PushResult> { return { ok: true, branch: "main", remote: "origin" }; },
    async openPullRequest(): Promise<PullRequestResult> {
      return { ok: true, branch: "main", url: "https://example.com/pr/1" };
    },
  };
}

function dependenciesFixture(board = boardFixture(), options: {
  validate?(document: unknown): EditorDocument;
  confirm?(message: string): boolean;
  boards?: readonly Board[];
  client?: WorkbenchClient;
} = {}): WorkbenchDependencies {
  const dialogs: Dialogs = {
    confirm: options.confirm ?? (() => true),
    prompt() { return null; },
  };
  const runtime: BrowserRuntime = {
    async fetch() { throw new Error("fetch is not used"); },
    location: { assign() {} },
    ...dialogs,
    createImage() {
      const image = document.createElement("img");
      queueMicrotask(() => image.onload?.(new Event("load")));
      return image;
    },
  };
  return {
    client: options.client ?? clientFixture(options.boards ?? [board]),
    controller: options.validate ? { ...controller, validateEditorDocument: options.validate } : controller,
    pathEditor,
    runtime,
    dialogs,
  };
}

async function withEditor(
  run: (app: ReactHarness) => void | Promise<void>,
  dependencies = dependenciesFixture(),
): Promise<void> {
  const app = await renderReact(<WorkbenchApp dependencies={dependencies} />);
  try {
    await app.flush();
    await app.click("#board-list button");
    await app.flush();
    await run(app);
  } finally {
    await app.cleanup();
  }
}

function paths(app: ReactHarness): string[] {
  return [...app.document.querySelectorAll<SVGPathElement>("#hold-overlay .region-shape")]
    .map((path) => path.getAttribute("d") ?? "");
}

function rotate(path: string, degrees: number, pivot: { x: number; y: number }): string {
  const commands = pathEditor.parsePath(path);
  pathEditor.rotatePath(commands, (degrees * Math.PI) / 180, pivot);
  return pathEditor.serializePath(commands);
}

test("model helpers group physical holds and derive collision-free identifiers", () => {
  const document = documentFixture([
    { id: 2, key: "hold-1-piece-0", displayPath: FIRST_PATH, metadata: { holdID: "hold-1", pieceIndex: 0 } },
    { id: 9, key: "hold-3-piece-0", displayPath: SECOND_PATH, metadata: { holdID: "hold-3", pieceIndex: 0 } },
    { key: "legacy", displayPath: OTHER_PATH },
  ]);
  assert.deepEqual(holdSiblings(document, document.regions[0]!).map((region) => region.key), ["hold-1-piece-0"]);
  assert.deepEqual(holdSiblings(document, document.regions[2]!).map((region) => region.key), ["legacy"]);
  assert.deepEqual(holdCentroid(document.regions, pathEditor), { x: 130 / 3, y: 40 / 3 });
  assert.equal(nextHoldId(document), "hold-4");
  assert.equal(nextRegionId(document), 10);
});

test("rotation handles stay separated and inside both top-edge and narrow canvases", () => {
  const pivot = { x: 50 / 3, y: 10 / 3 };
  for (const canvas of [{ width: 20, height: 100 }, { width: 100, height: 20 }]) {
    const handle = rotationHandlePosition(pivot, canvas);
    assert.ok(Math.hypot(handle.x - pivot.x, handle.y - pivot.y) >= 24);
    assert.ok(handle.x >= 6 && handle.x <= canvas.width - 6);
    assert.ok(handle.y >= 6 && handle.y <= canvas.height - 6);
  }
});

test("rotation degree normalization accepts decimals and rejects empty, zero, and non-finite values", () => {
  assert.equal(normalizedRotationDegrees("23.5"), 23.5);
  assert.equal(normalizedRotationDegrees("1e308"), 1e308 % 360);
  assert.equal(normalizedRotationDegrees(""), null);
  assert.equal(normalizedRotationDegrees("0"), null);
  assert.equal(normalizedRotationDegrees("Infinity"), null);
  assert.equal(normalizedRotationDegrees("NaN"), null);
});

test("svgPoint prefers inverse screen CTM and otherwise accounts for meet letterboxing", () => {
  const svg = {
    getAttribute(name: string) { return name === "viewBox" ? "0 0 100 50" : null; },
    getBoundingClientRect() { return { left: 10, top: 20, width: 200, height: 200 }; },
    getScreenCTM() {
      return { inverse: () => ({ a: 0.5, b: 0, c: 0, d: 0.5, e: -5, f: -35 }) };
    },
  };
  assert.deepEqual(svgPoint(svg, { clientX: 50, clientY: 90 }), { x: 20, y: 10 });
  assert.deepEqual(svgPoint({ ...svg, getScreenCTM: () => null }, { clientX: 110, clientY: 120 }), { x: 50, y: 25 });
});

test("selection renders one declarative handle overlay with legacy visual attributes", async () => {
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    assert.equal(app.document.querySelectorAll(".path-editor-overlay").length, 1);
    assert.equal(app.document.querySelectorAll(".path-editor-vertex").length, 3);
    const handle = app.document.querySelector(".path-editor-rotation-handle");
    assert.equal(handle?.getAttribute("r"), "6");
    assert.equal(handle?.getAttribute("fill"), "#fff7dc");
    assert.equal(handle?.getAttribute("stroke"), "#ff754f");
  });
});

test("Add Hold creates and selects a centered square", async () => {
  await withEditor(async (app) => {
    await app.click("#add-hold-button");
    assert.deepEqual(paths(app), [FIRST_PATH, SECOND_PATH, OTHER_PATH, "M 30 5 L 70 5 L 70 45 L 30 45 Z"]);
    assert.equal(app.text("#hold-heading"), "hold-3-piece-0");
    assert.equal(app.documentValue("#hold-type-select"), "edge");
  });
});

test("delete and type changes apply to every piece sharing holdID", async () => {
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.change("#hold-type-select", "pinch");
    const shapes = app.document.querySelectorAll<SVGPathElement>(".region-shape");
    assert.equal(shapes[0]?.getAttribute("fill"), "#f2c94c");
    assert.equal(shapes[1]?.getAttribute("fill"), "#f2c94c");
    assert.equal(shapes[2]?.getAttribute("fill"), "#9a6cf2");
    await app.click("#delete-hold-button");
    assert.deepEqual(paths(app), [OTHER_PATH]);
    assert.equal(app.text("#hold-heading"), "No selection");
  });
});

test("arrows nudge by 1 and 10 while input-targeted arrows retain native behavior", async () => {
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.keyDown("body", "ArrowRight");
    assert.equal(paths(app)[0], "M 11 10 L 21 10 L 21 20 Z");
    await app.keyDown("body", "ArrowDown", { shiftKey: true });
    assert.equal(paths(app)[0], "M 11 20 L 21 20 L 21 30 Z");
    const nativeInput = app.document.createElement("input");
    nativeInput.id = "native-degree-input";
    app.document.body.append(nativeInput);
    assert.equal(await app.keyDown("#native-degree-input", "ArrowUp"), false);
    assert.equal(paths(app)[0], "M 11 20 L 21 20 L 21 30 Z");
  });
});

test("bracket keys and buttons rotate by 15 and 45 degrees", async () => {
  const pivot = { x: 80 / 3, y: 40 / 3 };
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.keyDown("body", "]");
    assert.equal(paths(app)[0], rotate(FIRST_PATH, 15, pivot));
  });
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.keyDown("body", "[", { shiftKey: true });
    assert.equal(paths(app)[0], rotate(FIRST_PATH, -45, pivot));
  });
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.mouse("#rotate-cw-button", "click");
    assert.equal(paths(app)[0], rotate(FIRST_PATH, 15, pivot));
  });
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.mouse("#rotate-ccw-button", "click", { shiftKey: true });
    assert.equal(paths(app)[0], rotate(FIRST_PATH, -45, pivot));
  });
});

test("arbitrary rotation accepts decimals, normalizes extremes, and rejects invalid values", async () => {
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    const pivot = { x: 80 / 3, y: 40 / 3 };
    await app.input("#rotate-by-input", "23.5");
    await app.click("#rotate-by-apply-button");
    assert.equal(paths(app)[0], rotate(FIRST_PATH, 23.5, pivot));
    assert.equal(paths(app)[1], rotate(SECOND_PATH, 23.5, pivot));

    for (const invalid of ["", "0", "Infinity", "NaN"]) {
      const before = paths(app);
      await app.input("#rotate-by-input", invalid);
      await app.click("#rotate-by-apply-button");
      assert.deepEqual(paths(app), before);
      assert.match(app.text("#editor-status"), /finite, non-zero rotation/i);
    }

    await app.input("#rotate-by-input", "1e308");
    const beforeExtreme = paths(app)[0]!;
    await app.click("#rotate-by-apply-button");
    assert.equal(paths(app)[0], rotate(beforeExtreme, 1e308 % 360, pivot));
    assert.doesNotMatch(paths(app)[0]!, /NaN|Infinity/);
  });
});

async function drag(
  app: ReactHarness,
  selector: string,
  points: Array<{ x: number; y: number }>,
  end = "pointerup",
): Promise<void> {
  const [start, ...moves] = points;
  assert.ok(start);
  await app.pointer(selector, "pointerdown", { pointerId: 7, clientX: start.x, clientY: start.y });
  for (const point of moves) {
    await app.pointer("#editor-svg", "pointermove", { pointerId: 7, clientX: point.x, clientY: point.y });
  }
  const last = moves.at(-1) ?? start;
  await app.pointer("#editor-svg", end, { pointerId: 7, clientX: last.x, clientY: last.y });
}

test("vertex, control, and whole-path drags derive every move from pointer-down geometry", async () => {
  const curved = documentFixture([
    { id: 1, key: "curve", type: "jug", displayPath: "M 10 10 Q 15 5 20 10 L 20 20 Z" },
  ]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="curve"]');

    await drag(app, '.path-editor-vertex[data-index="1"]', [{ x: 20, y: 10 }, { x: 22, y: 12 }, { x: 25, y: 15 }]);
    assert.equal(paths(app)[0], "M 10 10 Q 20 10 25 15 L 20 20 Z");

    await drag(app, '.path-editor-control[data-index="1"]', [{ x: 20, y: 10 }, { x: 22, y: 10 }, { x: 24, y: 10 }]);
    assert.equal(paths(app)[0], "M 10 10 Q 24 10 25 15 L 20 20 Z");

    await drag(app, '[data-hold-key="curve"]', [{ x: 10, y: 10 }, { x: 12, y: 12 }, { x: 15, y: 15 }]);
    assert.equal(paths(app)[0], "M 15 15 Q 29 15 30 20 L 25 25 Z");
  }, dependenciesFixture(boardFixture(curved)));
});

test("rotation drag rotates every sibling from pointer-down paths around the shared centroid", async () => {
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    const connector = app.document.querySelector<SVGLineElement>(".path-editor-rotation-connector")!;
    const handle = app.document.querySelector<SVGCircleElement>(".path-editor-rotation-handle")!;
    const pivot = { x: Number(connector.getAttribute("x1")), y: Number(connector.getAttribute("y1")) };
    const start = { x: Number(handle.getAttribute("cx")), y: Number(handle.getAttribute("cy")) };
    const radius = Math.hypot(start.x - pivot.x, start.y - pivot.y);
    const angle = Math.atan2(start.y - pivot.y, start.x - pivot.x);
    const at = (delta: number) => ({ x: pivot.x + radius * Math.cos(angle + delta), y: pivot.y + radius * Math.sin(angle + delta) });
    await drag(app, ".path-editor-rotation-handle", [start, at(Math.PI / 4), at(Math.PI / 2)]);
    assert.equal(paths(app)[0], rotate(FIRST_PATH, 90, pivot));
    assert.equal(paths(app)[1], rotate(SECOND_PATH, 90, pivot));
    assert.equal(paths(app)[2], OTHER_PATH);
  });
});

test("double-click inserts a vertex and context menu deletes vertices except the protected M", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="square"]');
    await app.mouse("#editor-svg", "dblclick", { clientX: 20, clientY: 10 });
    assert.equal(paths(app)[0], "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z");
    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu");
    assert.equal(paths(app)[0], "M 10 10 L 30 10 L 30 30 L 10 30 Z");
    await app.mouse('.path-editor-vertex[data-index="0"]', "contextmenu");
    assert.equal(paths(app)[0], "M 10 10 L 30 10 L 30 30 L 10 30 Z");
  }, dependenciesFixture(boardFixture(square)));
});

test("double-click insertion preserves prior status while clearing validation and marking dirty", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="square"]');
    await app.input("#rotate-by-input", "0");
    await app.click("#rotate-by-apply-button");
    const priorStatus = app.text("#editor-status");
    assert.match(priorStatus, /finite, non-zero rotation/i);
    assert.equal(app.document.querySelector("#validation-panel")?.classList.contains("hidden"), false);

    await app.mouse("#editor-svg", "dblclick", { clientX: 20, clientY: 10 });

    assert.equal(paths(app)[0], "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z");
    assert.equal(app.text("#editor-status"), priorStatus);
    assert.equal(app.document.querySelector("#validation-panel")?.classList.contains("hidden"), true);
    assert.equal(app.text("#save-state"), "Unsaved changes");
  }, dependenciesFixture(boardFixture(square)));
});

test("context-menu deletion preserves prior status while clearing validation and marking dirty", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    await app.click('[data-hold-key="square"]');
    await app.input("#rotate-by-input", "0");
    await app.click("#rotate-by-apply-button");
    const priorStatus = app.text("#editor-status");
    assert.match(priorStatus, /finite, non-zero rotation/i);
    assert.equal(app.document.querySelector("#validation-panel")?.classList.contains("hidden"), false);

    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu");

    assert.equal(paths(app)[0], "M 10 10 L 30 10 L 30 30 L 10 30 Z");
    assert.equal(app.text("#editor-status"), priorStatus);
    assert.equal(app.document.querySelector("#validation-panel")?.classList.contains("hidden"), true);
    assert.equal(app.text("#save-state"), "Unsaved changes");
  }, dependenciesFixture(boardFixture(square)));
});

test("replacing the document cancels an active gesture without letting later pointer events clobber it", async () => {
  const replacementDocument = documentFixture([
    { id: 40, key: "replacement", type: "edge", displayPath: "M 60 5 L 90 5 L 90 35 Z" },
  ]);
  const replacementBoard: Board = {
    ...boardFixture(replacementDocument),
    boardId: "board-b",
    displayName: "Board B",
    imageUrl: "/api/boards/board-b/image",
  };
  const initialBoard = boardFixture();
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    await app.pointer('.path-editor-vertex[data-index="1"]', "pointerdown", {
      pointerId: 7,
      clientX: 20,
      clientY: 10,
    });
    assert.equal(app.capturedPointerId("#editor-svg"), 7);

    await app.click("#board-list button:nth-child(2)");
    await app.flush();

    assert.equal(app.text("#board-name"), "Board B");
    assert.deepEqual(paths(app), ["M 60 5 L 90 5 L 90 35 Z"]);
    assert.equal(app.text("#save-state"), "Saved");
    assert.equal(app.capturedPointerId("#editor-svg"), null);

    for (const type of ["pointermove", "pointerup", "pointercancel", "lostpointercapture"]) {
      await app.pointer("#editor-svg", type, { pointerId: 7, clientX: 45, clientY: 35 });
      assert.deepEqual(paths(app), ["M 60 5 L 90 5 L 90 35 Z"], type);
      assert.equal(app.text("#save-state"), "Saved", type);
      assert.equal(app.text("#board-name"), "Board B", type);
    }
  }, dependenciesFixture(initialBoard, { boards: [initialBoard, replacementBoard] }));
});

test("pointer cancellation, lost capture, and a second pointer preserve the initiating snapshot", async () => {
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    for (const cancelEvent of ["pointercancel", "lostpointercapture"]) {
      await drag(app, '.path-editor-vertex[data-index="1"]', [{ x: 20, y: 10 }, { x: 25, y: 15 }], cancelEvent);
      assert.equal(paths(app)[0], FIRST_PATH);
    }
    await app.pointer('.path-editor-vertex[data-index="1"]', "pointerdown", { pointerId: 7, clientX: 20, clientY: 10 });
    await app.pointer('.path-editor-vertex[data-index="1"]', "pointerdown", { pointerId: 8, clientX: 20, clientY: 10 });
    assert.equal(app.capturedPointerId("#editor-svg"), 7);
    await app.pointer("#editor-svg", "pointermove", { pointerId: 8, clientX: 40, clientY: 30 });
    assert.equal(paths(app)[0], FIRST_PATH);
    await app.pointer("#editor-svg", "pointermove", { pointerId: 7, clientX: 25, clientY: 15 });
    await app.pointer("#editor-svg", "pointerup", { pointerId: 8, clientX: 25, clientY: 15 });
    assert.equal(app.capturedPointerId("#editor-svg"), 7);
    assert.equal(paths(app)[0], "M 10 10 L 25 15 L 20 20 Z");
    await app.pointer("#editor-svg", "pointerup", { pointerId: 7, clientX: 25, clientY: 15 });
    assert.equal(app.capturedPointerId("#editor-svg"), null);
  });
});

test("invalid pointer geometry rolls back the path and dirty state", async () => {
  let validationCalls = 0;
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    await drag(app, '.path-editor-vertex[data-index="1"]', [{ x: 20, y: 10 }, { x: 25, y: 15 }]);
    assert.equal(paths(app)[0], FIRST_PATH);
    assert.equal(app.text("#save-state"), "Saved");
    assert.match(app.text("#editor-status"), /reverted/i);
  }, dependenciesFixture(boardFixture(), {
    validate(document) {
      validationCalls += 1;
      if (validationCalls >= 1) throw new Error("invalid contour");
      return controller.validateEditorDocument(document);
    },
  }));
});

function constrainedBoardFixture(): Board {
  const document: EditorDocument = {
    schemaVersion: 1,
    canvas: { width: 120, height: 80 },
    regions: [
      {
        id: 1,
        key: "a-piece-0",
        type: "jug",
        displayPath: "M 10 10 L 50 10 L 50 30 L 10 30 Z",
        metadata: { holdID: "a", pieceIndex: 0 },
        shapeConstraint: { shape: "rectangle", rotationDegrees: 0 },
      },
      {
        id: 2,
        key: "a-piece-1",
        type: "jug",
        displayPath: "M 60 10 L 80 10 L 80 30 L 60 30 Z",
        metadata: { holdID: "a", pieceIndex: 1 },
        shapeConstraint: { shape: "oval", rotationDegrees: 0 },
      },
      {
        id: 3,
        key: "b-piece-0",
        type: "edge",
        displayPath: "M 90 10 L 110 10 L 110 30 L 90 30 Z",
        metadata: { holdID: "b", pieceIndex: 0 },
      },
    ],
  };
  return {
    boardId: "board-a",
    displayName: "Board A",
    holdCount: 3,
    imageUrl: "/api/boards/board-a/image",
    document,
  };
}

test("outline picker reflects persisted constraints and changes only the selected piece", async () => {
  const board = boardFixture(documentFixture([
    { id: 1, key: "a-piece-0", type: "jug", displayPath: "M 10 20 L 50 20 L 50 40 L 10 40 Z", metadata: { holdID: "a", pieceIndex: 0 } },
    { id: 2, key: "a-piece-1", type: "jug", displayPath: SECOND_PATH, metadata: { holdID: "a", pieceIndex: 1 }, shapeConstraint: { shape: "roundedRectangle", rotationDegrees: 15 } },
    { id: 3, key: "b-piece-0", type: "edge", displayPath: OTHER_PATH, metadata: { holdID: "b", pieceIndex: 0 } },
  ]));
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    assert.equal(app.documentValue("#outline-shape-select"), "custom");
    assert.deepEqual(
      [...app.document.querySelectorAll<HTMLOptionElement>("#outline-shape-select option")]
        .map((option) => [option.value, option.textContent]),
      [["custom", "Custom"], ["oval", "Oval"], ["circle", "Circle"], ["pill", "Pill"], ["roundedRectangle", "Rounded rectangle"], ["rectangle", "Rectangle"]],
    );
    await app.change("#outline-shape-select", "oval");
    assert.deepEqual(paths(app), [
      "M 30 20 C 41.045695 20 50 24.477153 50 30 C 50 35.522847 41.045695 40 30 40 C 18.954305 40 10 35.522847 10 30 C 10 24.477153 18.954305 20 30 20 Z",
      SECOND_PATH,
      OTHER_PATH,
    ]);
    assert.equal(app.text("#save-state"), "Unsaved changes");
    assert.equal(app.text("#editor-status"), "Outline changed to oval. Save when ready.");
    await app.click('[data-hold-key="a-piece-1"]');
    assert.equal(app.documentValue("#outline-shape-select"), "roundedRectangle");
  }, dependenciesFixture(board));
});

test("primitive selection saves an exact zero-degree constraint and Custom removes only metadata", async () => {
  const board = boardFixture();
  const saved: EditorDocument[] = [];
  const client: WorkbenchClient = {
    ...clientFixture([board]),
    async saveBoard(_boardId, document) {
      saved.push(structuredClone(document));
      return { ...board, document };
    },
  };
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.change("#outline-shape-select", "pill");
    const constrainedPath = paths(app)[0];
    await app.click("#save-button");
    assert.deepEqual(saved[0]?.regions[0]?.shapeConstraint, { shape: "pill", rotationDegrees: 0 });
    await app.change("#outline-shape-select", "custom");
    assert.equal(paths(app)[0], constrainedPath);
    await app.click("#save-button");
    assert.equal(Object.hasOwn(saved[1]?.regions[0] ?? {}, "shapeConstraint"), false);
  }, dependenciesFixture(board, { client }));
});

test("invalid and busy outline actions preserve pointer-down geometry and dirty state", async () => {
  const board = constrainedBoardFixture();
  let resolveSave: ((board: Board) => void) | undefined;
  const client: WorkbenchClient = {
    ...clientFixture([board]),
    saveBoard() { return new Promise((resolve) => { resolveSave = resolve; }); },
  };
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 120, height: 80 } });
    await app.click('[data-hold-key="a-piece-0"]');
    const originalPath = paths(app)[0];
    await app.click("#save-button");
    assert.equal(app.disabled("#outline-shape-select"), true);
    assert.equal(app.disabled("#hold-type-select"), true);
    assert.equal(app.disabled("#rotate-cw-button"), true);
    assert.equal(app.disabled("#delete-hold-button"), true);
    await app.change("#outline-shape-select", "oval");
    await app.pointer('.path-editor-resize-handle[data-handle="e"]', "pointerdown", { pointerId: 19, clientX: 50, clientY: 20 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 19, clientX: 60, clientY: 20 });
    assert.equal(paths(app)[0], originalPath);
    assert.equal(app.capturedPointerId("#editor-svg"), null);
    assert.equal(app.text("#save-state"), "Working…");
    await app.flush(() => { resolveSave?.(board); });
  }, dependenciesFixture(board, { client }));

  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    const originalPath = paths(app)[0];
    await app.change("#outline-shape-select", "oval");
    assert.equal(paths(app)[0], originalPath);
    assert.equal(app.documentValue("#outline-shape-select"), "rectangle");
    assert.equal(app.text("#save-state"), "Saved");
    assert.match(app.text("#editor-status"), /reverted/i);
    assert.match(app.text("#validation-list"), /forced invalid outline/i);
  }, dependenciesFixture(board, {
    validate() { throw new Error("Forced invalid outline"); },
  }));
});

test("constrained selections render an oriented box and eight handles instead of freeform controls", async () => {
  const board = constrainedBoardFixture();
  board.document.regions[0]!.displayPath = "M 20 5 L 35 20 L 20 35 L 5 20 Z";
  board.document.regions[0]!.shapeConstraint = { shape: "rectangle", rotationDegrees: 45 };
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    const handles = [...app.document.querySelectorAll<SVGCircleElement>(".path-editor-resize-handle")];
    assert.deepEqual(handles.map((handle) => handle.dataset.handle), ["nw", "n", "ne", "e", "se", "s", "sw", "w"]);
    assert.equal(app.document.querySelectorAll(".path-editor-constrained-box").length, 1);
    assert.equal(app.document.querySelectorAll(".path-editor-vertex").length, 0);
    assert.equal(app.document.querySelectorAll(".path-editor-control").length, 0);
    assert.deepEqual(
      ["nw", "ne", "se", "sw"].map((id) => {
        const handle = handles.find((candidate) => candidate.dataset.handle === id)!;
        return [Number(Number(handle.getAttribute("cx")).toFixed(6)), Number(Number(handle.getAttribute("cy")).toFixed(6))];
      }),
      [[20, 5], [35, 20], [20, 35], [5, 20]],
    );
  }, dependenciesFixture(board));
});

test("constrained resize keeps circles circular, isolates siblings, and rolls invalid endpoints back", async () => {
  const board = constrainedBoardFixture();
  board.document.regions[0]!.displayPath = "M 30 10 C 35.522847 10 40 14.477153 40 20 C 40 25.522847 35.522847 30 30 30 C 24.477153 30 20 25.522847 20 20 C 20 14.477153 24.477153 10 30 10 Z";
  board.document.regions[0]!.shapeConstraint = { shape: "circle", rotationDegrees: 0 };
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 120, height: 80 } });
    await app.click('[data-hold-key="a-piece-0"]');
    const siblingPath = paths(app)[1];
    await drag(app, '.path-editor-resize-handle[data-handle="e"]', [{ x: 40, y: 20 }, { x: 50, y: 20 }]);
    assert.equal(paths(app)[0], "M 35 5 C 43.284271 5 50 11.715729 50 20 C 50 28.284271 43.284271 35 35 35 C 26.715729 35 20 28.284271 20 20 C 20 11.715729 26.715729 5 35 5 Z");
    assert.equal(paths(app)[1], siblingPath);

    const validPath = paths(app)[0];
    await app.pointer('.path-editor-resize-handle[data-handle="e"]', "pointerdown", { pointerId: 7, clientX: 50, clientY: 20 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 7, clientX: 130, clientY: 20 });
    await app.pointer("#editor-svg", "pointerup", { pointerId: 7, clientX: 130, clientY: 20 });
    assert.equal(paths(app)[0], validPath);
    assert.match(app.text("#editor-status"), /reverted/i);
  }, dependenciesFixture(board));
});

test("constrained resize calculation failures immediately restore pointer-down geometry", async () => {
  const board = constrainedBoardFixture();
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 120, height: 80 } });
    await app.click('[data-hold-key="a-piece-0"]');
    const originalPath = paths(app)[0];
    await app.pointer('.path-editor-resize-handle[data-handle="e"]', "pointerdown", { pointerId: 29, clientX: 50, clientY: 20 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 29, clientX: 60, clientY: 20 });
    assert.notEqual(paths(app)[0], originalPath);
    await app.pointer("#editor-svg", "pointermove", { pointerId: 29, clientX: Number.NaN, clientY: 20 });
    assert.equal(paths(app)[0], originalPath);
    assert.equal(app.documentValue("#outline-shape-select"), "rectangle");
    assert.equal(app.text("#save-state"), "Saved");
    assert.match(app.text("#validation-list"), /finite/i);
  }, dependenciesFixture(board));
});

test("starting save during constrained resize rolls the gesture back before serializing", async () => {
  const board = constrainedBoardFixture();
  let savedDocument: EditorDocument | undefined;
  let resolveSave: (() => void) | undefined;
  const client: WorkbenchClient = {
    ...clientFixture([board]),
    saveBoard(_boardId, document) {
      savedDocument = structuredClone(document);
      return new Promise((resolve) => {
        resolveSave = () => resolve({ ...board, document });
      });
    },
  };
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 120, height: 80 } });
    await app.click('[data-hold-key="a-piece-0"]');
    const originalPath = paths(app)[0]!;
    await app.pointer('.path-editor-resize-handle[data-handle="e"]', "pointerdown", { pointerId: 23, clientX: 50, clientY: 20 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 23, clientX: 60, clientY: 20 });
    assert.notEqual(paths(app)[0], originalPath);
    await app.click("#save-button");
    assert.equal(app.capturedPointerId("#editor-svg"), null);
    assert.equal(paths(app)[0], originalPath);
    assert.equal(savedDocument?.regions[0]?.displayPath, originalPath);
    await app.pointer("#editor-svg", "pointermove", { pointerId: 23, clientX: 80, clientY: 20 });
    assert.equal(paths(app)[0], originalPath);
    await app.flush(() => { resolveSave?.(); });
  }, dependenciesFixture(board, { client }));
});

test("constrained movement preserves metadata while every rotation mode updates sibling angles", async () => {
  const board = constrainedBoardFixture();
  const saved: EditorDocument[] = [];
  const client: WorkbenchClient = {
    ...clientFixture([board]),
    async saveBoard(_boardId, document) {
      saved.push(structuredClone(document));
      return { ...board, document };
    },
  };
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 120, height: 80 } });
    await app.click('[data-hold-key="a-piece-0"]');
    await drag(app, '[data-hold-key="a-piece-0"]', [{ x: 20, y: 20 }, { x: 25, y: 23 }]);
    await app.keyDown("body", "ArrowRight");
    await app.click("#rotate-cw-button");
    await app.keyDown("body", "]");

    const connector = app.document.querySelector<SVGLineElement>(".path-editor-rotation-connector")!;
    const handle = app.document.querySelector<SVGCircleElement>(".path-editor-rotation-handle")!;
    const pivot = { x: Number(connector.getAttribute("x1")), y: Number(connector.getAttribute("y1")) };
    const start = { x: Number(handle.getAttribute("cx")), y: Number(handle.getAttribute("cy")) };
    const radius = Math.hypot(start.x - pivot.x, start.y - pivot.y);
    const angle = Math.atan2(start.y - pivot.y, start.x - pivot.x) + Math.PI / 2;
    await drag(app, ".path-editor-rotation-handle", [start, {
      x: pivot.x + radius * Math.cos(angle),
      y: pivot.y + radius * Math.sin(angle),
    }]);
    await app.click("#save-button");
    assert.deepEqual(saved[0]?.regions.slice(0, 2).map((region) => region.shapeConstraint?.rotationDegrees), [120, 120]);
    assert.equal(Object.hasOwn(saved[0]?.regions[2] ?? {}, "shapeConstraint"), false);
  }, dependenciesFixture(board, { client }));
});

test("constrained pointer cancellation restores paths and angles", async () => {
  const board = constrainedBoardFixture();
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 120, height: 80 } });
    await app.click('[data-hold-key="a-piece-0"]');
    const originalPaths = paths(app).slice(0, 2);
    const handle = app.document.querySelector<SVGCircleElement>(".path-editor-rotation-handle")!;
    const start = { x: Number(handle.getAttribute("cx")), y: Number(handle.getAttribute("cy")) };
    await app.pointer(".path-editor-rotation-handle", "pointerdown", { pointerId: 11, clientX: start.x, clientY: start.y });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 11, clientX: start.x + 20, clientY: start.y + 20 });
    await app.pointer("#editor-svg", "pointercancel", { pointerId: 11, clientX: start.x + 20, clientY: start.y + 20 });
    assert.deepEqual(paths(app).slice(0, 2), originalPaths);
    assert.equal(app.documentValue("#outline-shape-select"), "rectangle");
  }, dependenciesFixture(board));
});
