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

function clientFixture(board: Board): WorkbenchClient {
  return {
    async listBoards(): Promise<BoardSummary[]> {
      return [{ boardId: board.boardId, displayName: board.displayName, holdCount: board.holdCount }];
    },
    async getBoard(): Promise<Board> { return board; },
    async saveBoard(_boardId, document): Promise<Board> { return { ...board, document }; },
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
    client: clientFixture(board),
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
