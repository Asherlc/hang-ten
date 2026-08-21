import assert from "node:assert/strict";
import test from "node:test";
import React from "react";

import { WorkbenchApp } from "../src/WorkbenchApp.tsx";
import { HoldCanvas } from "../src/components/HoldCanvas.tsx";
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
import type { HoldEditorActions } from "../src/useHoldEditor.ts";
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

async function touchCanvas(
  app: ReactHarness,
  type: "touchstart" | "touchmove" | "touchend",
  touches: readonly { clientX: number; clientY: number }[],
): Promise<boolean> {
  let defaultPrevented = false;
  await app.flush(() => {
    const viewport = app.document.querySelector<HTMLElement>("#canvas-viewport");
    const windowValue = app.document.defaultView;
    if (!viewport || !windowValue) throw new Error("Missing canvas viewport test environment");
    const event = new windowValue.Event(type, { bubbles: true, cancelable: true });
    Object.defineProperty(event, "touches", { configurable: true, value: touches });
    viewport.dispatchEvent(event);
    defaultPrevented = event.defaultPrevented;
  });
  return defaultPrevented;
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

test("svgPoint preserves finite pointer offsets when fallback geometry has zero dimensions", () => {
  const svg = {
    getAttribute(name: string) { return name === "viewBox" ? "0 0 0 0" : null; },
    getBoundingClientRect() { return { left: 10, top: 20, width: 0, height: 0 }; },
    getScreenCTM() { return null; },
  };

  assert.deepEqual(svgPoint(svg, { clientX: 14, clientY: 27 }), { x: 4, y: 7 });
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

test("canvas zoom controls and Alt-wheel adjust a bounded zoom while preserving normal scrolling", async () => {
  await withEditor(async (app) => {
    assert.equal(app.text("#canvas-zoom-level"), "100%");
    assert.equal(app.document.querySelector("#zoom-out-button")?.getAttribute("aria-label"), "Zoom out");
    assert.equal(app.document.querySelector("#zoom-in-button")?.getAttribute("aria-label"), "Zoom in");

    await app.click("#zoom-in-button");
    assert.equal(app.text("#canvas-zoom-level"), "125%");
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -1, altKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "150%");
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -1 }), false);
    assert.equal(app.text("#canvas-zoom-level"), "150%");

    for (let index = 0; index < 12; index += 1) await app.click("#zoom-in-button");
    assert.equal(app.text("#canvas-zoom-level"), "300%");
    assert.equal(app.disabled("#zoom-in-button"), true);
    for (let index = 0; index < 12; index += 1) await app.click("#zoom-out-button");
    assert.equal(app.text("#canvas-zoom-level"), "50%");
    assert.equal(app.disabled("#zoom-out-button"), true);
  });
});

test("Command plus and minus shortcuts zoom only an open board outside editable targets", async () => {
  await withEditor(async (app) => {
    assert.equal(await app.keyDown("body", "+", { metaKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "125%");
    assert.equal(await app.keyDown("body", "-", { metaKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "100%");

    assert.equal(await app.keyDown("body", "+", { ctrlKey: true }), false);
    assert.equal(app.text("#canvas-zoom-level"), "100%");

    const input = app.document.createElement("input");
    input.id = "native-zoom-input";
    app.document.body.append(input);
    assert.equal(await app.keyDown("#native-zoom-input", "+", { metaKey: true }), false);
    assert.equal(app.text("#canvas-zoom-level"), "100%");

    for (let index = 0; index < 8; index += 1) {
      assert.equal(await app.keyDown("body", "+", { metaKey: true }), true);
    }
    assert.equal(app.text("#canvas-zoom-level"), "300%");
    assert.equal(await app.keyDown("body", "+", { metaKey: true }), false);

    for (let index = 0; index < 10; index += 1) {
      assert.equal(await app.keyDown("body", "-", { metaKey: true }), true);
    }
    assert.equal(app.text("#canvas-zoom-level"), "50%");
    assert.equal(await app.keyDown("body", "-", { metaKey: true }), false);
  });

  const app = await renderReact(<WorkbenchApp dependencies={dependenciesFixture()} />);
  try {
    await app.flush();
    assert.equal(await app.keyDown("body", "+", { metaKey: true }), false);
    assert.equal(app.text("#canvas-zoom-level"), "100%");
  } finally {
    await app.cleanup();
  }
});

test("Alt-wheel zoom accepts a horizontal-only wheel delta", async () => {
  await withEditor(async (app) => {
    assert.equal(await app.wheel("#canvas-viewport", { deltaX: -1, deltaY: 0, altKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "125%");
  });
});

test("Ctrl-wheel pinch zoom accumulates small deltas without changing Alt-wheel sensitivity", async () => {
  await withEditor(async (app) => {
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -20, ctrlKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "100%");
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -30, ctrlKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "100%");
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -60, ctrlKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "125%");
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -1, altKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "150%");
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -40, ctrlKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "150%");
  });
});

test("Alt-wheel resets pending Ctrl-pinch deltas before its immediate zoom", async () => {
  await withEditor(async (app) => {
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -40, ctrlKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "100%");
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -1, altKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "125%");
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -60, ctrlKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "125%");
  });
});

test("ordinary wheel resets pending Ctrl-pinch deltas before the next pinch", async () => {
  await withEditor(async (app) => {
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -40, ctrlKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "100%");
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -1 }), false);
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -60, ctrlKey: true }), true);
    assert.equal(app.text("#canvas-zoom-level"), "100%");
  });
});

test("rapid Ctrl-pinch events consume browser zoom while advancing canvas zoom only within bounds", async () => {
  await withEditor(async (app) => {
    const events: WheelEvent[] = [];
    await app.flush(() => {
      const viewport = app.document.querySelector<HTMLElement>("#canvas-viewport");
      if (!viewport) throw new Error("Missing canvas viewport");
      const windowValue = app.document.defaultView;
      if (!windowValue) throw new Error("Missing test document window");
      for (let index = 0; index < 20; index += 1) {
        const event = new windowValue.WheelEvent("wheel", {
          bubbles: true,
          cancelable: true,
          deltaY: -100,
          ctrlKey: true,
        });
        viewport.dispatchEvent(event);
        events.push(event);
      }
    });
    assert.equal(app.text("#canvas-zoom-level"), "300%");
    assert.ok(events.slice(0, 8).every((event) => event.defaultPrevented));
    assert.ok(events.slice(8).every((event) => !event.defaultPrevented));

    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -100, altKey: true }), false);
    assert.equal(app.text("#canvas-zoom-level"), "300%");
  });
});

test("Ctrl-pinch does not consume a sub-threshold event when canvas zoom is at its bound", async () => {
  await withEditor(async (app) => {
    for (let index = 0; index < 8; index += 1) await app.click("#zoom-in-button");
    assert.equal(app.text("#canvas-zoom-level"), "300%");

    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -20, ctrlKey: true }), false);
    assert.equal(app.text("#canvas-zoom-level"), "300%");
  });
});

test("wheel zoom uses callbacks from the latest render", async () => {
  const inertEditor = { cancelActiveEdit: () => false } as HoldEditorActions;
  function WheelZoomHarness() {
    const [useCurrentCallbacks, setUseCurrentCallbacks] = React.useState(false);
    const [zoom, setZoom] = React.useState(100);
    const canvasDocument = React.useMemo(() => documentFixture(), []);
    const onZoomChange = useCurrentCallbacks
      ? (direction: number) => {
        setZoom((current) => current + direction * 25);
        return true;
      }
      : () => false;
    const canZoomChange = useCurrentCallbacks ? () => true : () => false;
    return <>
      <button id="use-current-wheel-callbacks" type="button" onClick={() => setUseCurrentCallbacks(true)}>Use current callbacks</button>
      <output id="wheel-harness-zoom">{zoom}%</output>
      <HoldCanvas
        board={null}
        document={canvasDocument}
        selectedKey={null}
        selectedKeys={[]}
        busy={false}
        onSelectHold={() => {}}
        pathEditor={pathEditor}
        editor={inertEditor}
        zoomPercent={100}
        onZoomChange={onZoomChange}
        canZoomChange={canZoomChange}
        guides={[]}
        onMoveGuide={() => {}}
      />
    </>;
  }

  const app = await renderReact(<WheelZoomHarness />);
  try {
    await app.click("#use-current-wheel-callbacks");
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -1, altKey: true }), true);
    assert.equal(app.text("#wheel-harness-zoom"), "125%");
    assert.equal(await app.wheel("#canvas-viewport", { deltaY: -100, ctrlKey: true }), true);
    assert.equal(app.text("#wheel-harness-zoom"), "150%");
  } finally {
    await app.cleanup();
  }
});

test("two-finger touch pinch continues zooming across rerenders without intercepting one-finger touches", async () => {
  await withEditor(async (app) => {
    assert.equal(await touchCanvas(app, "touchstart", [{ clientX: 20, clientY: 20 }]), false);
    assert.equal(await touchCanvas(app, "touchmove", [{ clientX: 35, clientY: 20 }]), false);
    assert.equal(app.text("#canvas-zoom-level"), "100%");

    assert.equal(await touchCanvas(app, "touchstart", [
      { clientX: 20, clientY: 20 },
      { clientX: 80, clientY: 20 },
    ]), true);
    assert.equal(await touchCanvas(app, "touchmove", [
      { clientX: 10, clientY: 20 },
      { clientX: 90, clientY: 20 },
    ]), true);
    assert.equal(app.text("#canvas-zoom-level"), "125%");
    assert.equal(await touchCanvas(app, "touchmove", [
      { clientX: 0, clientY: 20 },
      { clientX: 100, clientY: 20 },
    ]), true);
    assert.equal(app.text("#canvas-zoom-level"), "150%");
    assert.equal(await touchCanvas(app, "touchend", []), false);
  });
});

test("pointer edits retain SVG coordinates at a zoomed canvas size", async () => {
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 200, height: 100 } });
    for (let index = 0; index < 4; index += 1) await app.click("#zoom-in-button");
    assert.equal(app.text("#canvas-zoom-level"), "200%");
    await app.click('[data-hold-key="a-piece-0"]');
    await drag(app, '.path-editor-vertex[data-index="1"]', [{ x: 40, y: 20 }, { x: 50, y: 30 }]);
    assert.equal(paths(app)[0], "M 10 10 L 25 15 L 20 20 Z");
  });
});

test("hold paths expose button semantics and support Enter and Space selection", async () => {
  await withEditor(async (app) => {
    const target = app.document.querySelector<SVGPathElement>('[data-hold-key="b-piece-0"]');
    assert.equal(target?.getAttribute("role"), "button");
    assert.equal(target?.getAttribute("tabindex"), "0");
    assert.equal(target?.getAttribute("aria-label"), "Select hold b-piece-0");

    assert.equal(await app.keyDown('[data-hold-key="b-piece-0"]', "Enter"), false);
    assert.equal(app.text("#hold-heading"), "b-piece-0");
    assert.equal(await app.keyDown('[data-hold-key="a-piece-0"]', " "), true);
    assert.equal(app.text("#hold-heading"), "a-piece-0");
  });
});

test("modifier selection toggles highlighted holds while plain selection replaces the batch and keeps one primary overlay", async () => {
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.mouse('[data-hold-key="b-piece-0"]', "click", { ctrlKey: true });

    assert.equal(app.document.querySelector('[data-hold-key="a-piece-0"]')?.getAttribute("aria-pressed"), "true");
    assert.equal(app.document.querySelector('[data-hold-key="b-piece-0"]')?.getAttribute("aria-pressed"), "true");
    assert.equal(app.text("#hold-heading"), "b-piece-0");
    assert.equal(app.document.querySelectorAll(".path-editor-overlay").length, 1);

    assert.equal(await app.keyDown('[data-hold-key="a-piece-1"]', "Enter", { metaKey: true }), false);
    assert.equal(app.document.querySelector('[data-hold-key="a-piece-1"]')?.getAttribute("aria-pressed"), "true");
    assert.equal(app.text("#hold-heading"), "a-piece-1");

    await app.click('[data-hold-key="a-piece-0"]');
    assert.equal(app.document.querySelector('[data-hold-key="a-piece-0"]')?.getAttribute("aria-pressed"), "true");
    assert.equal(app.document.querySelector('[data-hold-key="a-piece-1"]')?.getAttribute("aria-pressed"), "false");
    assert.equal(app.document.querySelector('[data-hold-key="b-piece-0"]')?.getAttribute("aria-pressed"), "false");
    assert.equal(app.text("#hold-heading"), "a-piece-0");
  });
});

test("Command-click selection survives its trailing plain click", async () => {
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.pointer('[data-hold-key="b-piece-0"]', "pointerdown", { pointerId: 42, metaKey: true });
    await app.pointer('[data-hold-key="b-piece-0"]', "pointerup", { pointerId: 42, metaKey: true });
    await app.mouse('[data-hold-key="b-piece-0"]', "click");

    assert.equal(app.document.querySelector('[data-hold-key="a-piece-0"]')?.getAttribute("aria-pressed"), "true");
    assert.equal(app.document.querySelector('[data-hold-key="b-piece-0"]')?.getAttribute("aria-pressed"), "true");
    assert.equal(app.text("#hold-heading"), "b-piece-0");
  });
});

test("a cancelled Command-click does not suppress the next normal click", async () => {
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.pointer('[data-hold-key="b-piece-0"]', "pointerdown", { pointerId: 42, metaKey: true });
    await app.pointer('[data-hold-key="b-piece-0"]', "pointercancel", { pointerId: 42, metaKey: true });
    await app.click('[data-hold-key="b-piece-0"]');

    assert.equal(app.document.querySelector('[data-hold-key="a-piece-0"]')?.getAttribute("aria-pressed"), "false");
    assert.equal(app.document.querySelector('[data-hold-key="b-piece-0"]')?.getAttribute("aria-pressed"), "true");
  });
});

test("batch inspector actions change every selected physical hold and undo restores them", async () => {
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.mouse('[data-hold-key="b-piece-0"]', "click", { ctrlKey: true });

    await app.change("#hold-type-select", "pinch");
    assert.deepEqual([...app.document.querySelectorAll<SVGPathElement>(".region-shape")].map((path) => path.getAttribute("fill")), ["#f2c94c", "#f2c94c", "#f2c94c"]);

    await app.change("#outline-shape-select", "rectangle");
    assert.deepEqual([...app.document.querySelectorAll<SVGPathElement>(".region-shape")].map((path) => path.getAttribute("d")), [
      "M 10 10 L 20 10 L 20 20 L 10 20 Z",
      "M 30 10 L 40 10 L 40 20 L 30 20 Z",
      "M 70 10 L 80 10 L 80 20 L 70 20 Z",
    ]);

    await app.click("#rotate-cw-button");
    assert.notDeepEqual(paths(app), [
      "M 10 10 L 20 10 L 20 20 L 10 20 Z",
      "M 30 10 L 40 10 L 40 20 L 30 20 Z",
      "M 70 10 L 80 10 L 80 20 L 70 20 Z",
    ]);
    assert.equal(await app.keyDown("body", "z", { ctrlKey: true }), true);
    assert.deepEqual(paths(app), [
      "M 10 10 L 20 10 L 20 20 L 10 20 Z",
      "M 30 10 L 40 10 L 40 20 L 30 20 Z",
      "M 70 10 L 80 10 L 80 20 L 70 20 Z",
    ]);

    await app.input("#rotate-by-input", "23.5");
    await app.click("#rotate-by-apply-button");
    assert.notDeepEqual(paths(app), [
      "M 10 10 L 20 10 L 20 20 L 10 20 Z",
      "M 30 10 L 40 10 L 40 20 L 30 20 Z",
      "M 70 10 L 80 10 L 80 20 L 70 20 Z",
    ]);
    assert.equal(await app.keyDown("body", "z", { ctrlKey: true }), true);
    assert.deepEqual(paths(app), [
      "M 10 10 L 20 10 L 20 20 L 10 20 Z",
      "M 30 10 L 40 10 L 40 20 L 30 20 Z",
      "M 70 10 L 80 10 L 80 20 L 70 20 Z",
    ]);

    await app.click("#delete-hold-button");
    assert.deepEqual(paths(app), []);
    assert.equal(app.text("#hold-heading"), "No selection");
    assert.equal(await app.keyDown("body", "z", { ctrlKey: true }), true);
    assert.equal(paths(app).length, 3);
  });
});

test("batch deletion names every selected physical hold and leaves the document intact when cancelled", async () => {
  const prompts: string[] = [];
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.mouse('[data-hold-key="b-piece-0"]', "click", { ctrlKey: true });
    await app.click("#delete-hold-button");

    assert.deepEqual(prompts, ["Delete 2 selected holds and all of their pieces?"]);
    assert.deepEqual(paths(app), [FIRST_PATH, SECOND_PATH, OTHER_PATH]);
    assert.equal(app.text("#hold-heading"), "b-piece-0");
  }, dependenciesFixture(boardFixture(), {
    confirm(message) {
      prompts.push(message);
      return false;
    },
  }));
});

test("the hold type control preserves an out-of-list document value", async () => {
  const board = boardFixture(documentFixture([
    { id: 1, key: "legacy-piece-0", type: "legacy-grip", displayPath: FIRST_PATH },
  ]));
  await withEditor(async (app) => {
    await app.click('[data-hold-key="legacy-piece-0"]');

    assert.equal(app.documentValue("#hold-type-select"), "legacy-grip");
    assert.equal(app.text('#hold-type-select option[value="legacy-grip"]'), "legacy-grip");
  }, dependenciesFixture(board));
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

test("finger capacity loads in the inspector, applies to every physical piece, and new holds are unset", async () => {
  const board = boardFixture(documentFixture([
    { id: 1, key: "a-piece-0", type: "jug", displayPath: FIRST_PATH, metadata: { holdID: "a", pieceIndex: 0 }, fingerCapacity: 2 },
    { id: 2, key: "a-piece-1", type: "jug", displayPath: SECOND_PATH, metadata: { holdID: "a", pieceIndex: 1 }, fingerCapacity: 2 },
    { id: 3, key: "b-piece-0", type: "edge", displayPath: OTHER_PATH, metadata: { holdID: "b", pieceIndex: 0 } },
  ]));
  const saved: EditorDocument[] = [];
  const client = {
    ...clientFixture([board]),
    async saveBoard(_boardId: string, document: EditorDocument): Promise<Board> {
      saved.push(structuredClone(document));
      return { ...board, document };
    },
  } satisfies WorkbenchClient;

  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    assert.equal(app.documentValue("#finger-capacity-select"), "2");
    await app.change("#finger-capacity-select", "4");
    await app.click("#save-button");
    assert.deepEqual(saved[0]?.regions.slice(0, 2).map((region) => region.fingerCapacity), [4, 4]);
    assert.equal(Object.hasOwn(saved[0]?.regions[2] ?? {}, "fingerCapacity"), false);

    await app.click("#add-hold-button");
    assert.equal(app.documentValue("#finger-capacity-select"), "");
  }, dependenciesFixture(board, { client }));
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

test("command/control undo and redo reverse document edits and preserve native input behavior", async () => {
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.keyDown("body", "ArrowRight");
    assert.equal(paths(app)[0], "M 11 10 L 21 10 L 21 20 Z");
    assert.equal(await app.keyDown("body", "z", { metaKey: true }), true);
    assert.equal(paths(app)[0], FIRST_PATH);
    assert.equal(await app.keyDown("body", "y", { ctrlKey: true }), true);
    assert.equal(paths(app)[0], "M 11 10 L 21 10 L 21 20 Z");
    assert.equal(await app.keyDown("body", "z", { ctrlKey: true }), true);
    assert.equal(paths(app)[0], FIRST_PATH);
    assert.equal(await app.keyDown("body", "z", { metaKey: true, shiftKey: true }), true);
    assert.equal(paths(app)[0], "M 11 10 L 21 10 L 21 20 Z");
    assert.equal(await app.keyDown("body", "y", { ctrlKey: true }), false);

    const input = app.document.createElement("input");
    input.id = "native-history-input";
    app.document.body.append(input);
    assert.equal(await app.keyDown("#native-history-input", "z", { metaKey: true }), false);
    assert.equal(await app.keyDown("#native-history-input", "z", { ctrlKey: true }), false);
    assert.equal(await app.keyDown("#native-history-input", "y", { ctrlKey: true }), false);
    assert.equal(paths(app)[0], "M 11 10 L 21 10 L 21 20 Z");
  });
});

test("a new edit clears redo and a completed drag is a single undo step", async () => {
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    await drag(app, '[data-hold-key="a-piece-0"]', [{ x: 15, y: 15 }, { x: 20, y: 15 }, { x: 25, y: 15 }]);
    assert.equal(await app.keyDown("body", "z", { ctrlKey: true }), true);
    assert.equal(paths(app)[0], FIRST_PATH);
    await app.keyDown("body", "ArrowRight");
    assert.equal(await app.keyDown("body", "y", { ctrlKey: true }), false);
  });
});

test("undo during a drag restores the committed document before building redo history", async () => {
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    await app.keyDown("body", "ArrowRight");
    const committedPath = paths(app)[0];
    await app.pointer('[data-hold-key="a-piece-0"]', "pointerdown", { pointerId: 7, clientX: 16, clientY: 15 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 7, clientX: 26, clientY: 15 });
    const previewPath = paths(app)[0];
    assert.notEqual(previewPath, committedPath);

    assert.equal(await app.keyDown("body", "z", { ctrlKey: true }), true);
    assert.equal(paths(app)[0], FIRST_PATH);
    assert.equal(await app.keyDown("body", "z", { ctrlKey: true, shiftKey: true }), true);
    assert.equal(paths(app)[0], committedPath);
    assert.notEqual(paths(app)[0], previewPath);
  });
});

test("command/control undo and Ctrl redo consume browser shortcuts when cancelling an active drag without history", async () => {
  for (const shortcut of [
    { key: "z", options: { ctrlKey: true } },
    { key: "z", options: { metaKey: true } },
    { key: "y", options: { ctrlKey: true } },
  ]) {
    await withEditor(async (app) => {
      app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
      await app.click('[data-hold-key="a-piece-0"]');
      await app.pointer('[data-hold-key="a-piece-0"]', "pointerdown", { pointerId: 7, clientX: 15, clientY: 15 });
      await app.pointer("#editor-svg", "pointermove", { pointerId: 7, clientX: 25, clientY: 15 });
      assert.notEqual(paths(app)[0], FIRST_PATH);

      assert.equal(await app.keyDown("body", shortcut.key, shortcut.options), true);
      assert.equal(paths(app)[0], FIRST_PATH);
    });
  }
});

test("no-op drags do not create an undo revision", async () => {
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    await drag(app, '[data-hold-key="a-piece-0"]', [{ x: 15, y: 15 }]);
    assert.equal(app.text("#save-state"), "Saved");
    assert.equal(await app.keyDown("body", "z", { ctrlKey: true }), false);
    assert.equal(paths(app)[0], FIRST_PATH);

    await drag(app, '[data-hold-key="a-piece-0"]', [{ x: 15, y: 15 }, { x: 25, y: 15 }, { x: 15, y: 15 }]);
    assert.equal(paths(app)[0], FIRST_PATH);
    assert.equal(app.text("#save-state"), "Saved");
    assert.equal(await app.keyDown("body", "z", { ctrlKey: true }), false);
  });
});

test("escape cancels a drag and command/control save saves only outside editable targets", async () => {
  const board = boardFixture();
  let saves = 0;
  const client = {
    ...clientFixture([board]),
    async saveBoard(boardId: string, document: EditorDocument): Promise<Board> {
      saves += 1;
      return { ...board, boardId, document };
    },
  } satisfies WorkbenchClient;
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    await app.pointer('[data-hold-key="a-piece-0"]', "pointerdown", { pointerId: 7, clientX: 15, clientY: 15 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 7, clientX: 25, clientY: 15 });
    assert.notEqual(paths(app)[0], FIRST_PATH);
    assert.equal(await app.keyDown("body", "Escape"), true);
    assert.equal(paths(app)[0], FIRST_PATH);
    assert.equal(await app.keyDown("body", "s", { metaKey: true }), true);
    await app.flush();
    assert.equal(saves, 1);

    const input = app.document.createElement("input");
    input.id = "native-save-input";
    app.document.body.append(input);
    assert.equal(await app.keyDown("#native-save-input", "s", { ctrlKey: true }), false);
    assert.equal(saves, 1);
  }, dependenciesFixture(board, { client }));
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

test("guide controls create horizontal and vertical guides at the selected hold center", async () => {
  const square = documentFixture([{
    id: 1,
    key: "square",
    type: "jug",
    displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z",
  }]);
  await withEditor(async (app) => {
    assert.equal(app.disabled("#add-horizontal-guide-button"), true);
    assert.equal(app.disabled("#add-vertical-guide-button"), true);
    await app.click('[data-hold-key="square"]');
    await app.click("#add-horizontal-guide-button");
    await app.click("#add-vertical-guide-button");

    const horizontal = app.document.querySelector<SVGLineElement>('[data-guide-axis="horizontal"]');
    const vertical = app.document.querySelector<SVGLineElement>('[data-guide-axis="vertical"]');
    assert.equal(horizontal?.getAttribute("y1"), "20");
    assert.equal(horizontal?.getAttribute("y2"), "20");
    assert.equal(vertical?.getAttribute("x1"), "20");
    assert.equal(vertical?.getAttribute("x2"), "20");
  }, dependenciesFixture(boardFixture(square)));
});

test("whole-path dragging snaps its horizontal and vertical bounds edges to nearby guides", async () => {
  const document = documentFixture([
    { id: 1, key: "guide-source", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" },
    { id: 2, key: "snap-target", type: "edge", displayPath: "M 30 30 L 50 30 L 50 50 L 30 50 Z" },
  ]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 100 } });
    await app.click('[data-hold-key="guide-source"]');
    await app.click("#add-horizontal-guide-button");
    await app.click("#add-vertical-guide-button");
    await app.click('[data-hold-key="snap-target"]');
    await drag(app, '[data-hold-key="snap-target"]', [{ x: 30, y: 30 }, { x: 14, y: 14 }]);

    assert.equal(paths(app)[1], "M 20 20 L 40 20 L 40 40 L 20 40 Z");
    assert.equal(await app.keyDown("body", "z", { ctrlKey: true }), true);
    assert.equal(paths(app)[1], "M 30 30 L 50 30 L 50 50 L 30 50 Z");
  }, dependenciesFixture(boardFixture(document)));
});

test("whole-path dragging does not snap when only its center is near a guide", async () => {
  const document = documentFixture([
    { id: 1, key: "guide-source", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" },
    { id: 2, key: "snap-target", type: "edge", displayPath: "M 30 30 L 50 30 L 50 50 L 30 50 Z" },
  ]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 100 } });
    await app.click('[data-hold-key="guide-source"]');
    await app.click("#add-horizontal-guide-button");
    await app.click("#add-vertical-guide-button");
    await app.click('[data-hold-key="snap-target"]');
    await drag(app, '[data-hold-key="snap-target"]', [{ x: 30, y: 30 }, { x: 13, y: 13 }]);

    assert.equal(paths(app)[1], "M 13 13 L 33 13 L 33 33 L 13 33 Z");
  }, dependenciesFixture(boardFixture(document)));
});

test("Alt bypasses guide snapping during a whole-path drag", async () => {
  const document = documentFixture([
    { id: 1, key: "guide-source", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" },
    { id: 2, key: "snap-target", type: "edge", displayPath: "M 30 30 L 50 30 L 50 50 L 30 50 Z" },
  ]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 100 } });
    await app.click('[data-hold-key="guide-source"]');
    await app.click("#add-horizontal-guide-button");
    await app.click("#add-vertical-guide-button");
    await app.click('[data-hold-key="snap-target"]');
    await app.pointer('[data-hold-key="snap-target"]', "pointerdown", { pointerId: 7, clientX: 30, clientY: 30 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 7, clientX: 14, clientY: 14, altKey: true });
    await app.pointer("#editor-svg", "pointerup", { pointerId: 7, clientX: 14, clientY: 14, altKey: true });

    assert.equal(paths(app)[1], "M 14 14 L 34 14 L 34 34 L 14 34 Z");
  }, dependenciesFixture(boardFixture(document)));
});

test("guides drag on their own axis and clear without changing the document", async () => {
  const square = documentFixture([{
    id: 1,
    key: "square",
    type: "jug",
    displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z",
  }]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 100 } });
    await app.click('[data-hold-key="square"]');
    await app.click("#add-horizontal-guide-button");
    await app.click("#add-vertical-guide-button");

    await app.pointer('[data-guide-axis="horizontal"]', "pointerdown", { pointerId: 17, clientX: 50, clientY: 20 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 17, clientX: 5, clientY: 56 });
    await app.pointer("#editor-svg", "pointerup", { pointerId: 17, clientX: 5, clientY: 56 });
    await app.pointer('[data-guide-axis="vertical"]', "pointerdown", { pointerId: 18, clientX: 20, clientY: 50 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 18, clientX: 27, clientY: 5 });
    await app.pointer("#editor-svg", "pointerup", { pointerId: 18, clientX: 27, clientY: 5 });

    const horizontal = app.document.querySelector<SVGLineElement>('[data-guide-axis="horizontal"]');
    const vertical = app.document.querySelector<SVGLineElement>('[data-guide-axis="vertical"]');
    assert.equal(horizontal?.getAttribute("y1"), "31");
    assert.equal(vertical?.getAttribute("x1"), "27");
    await app.click("#clear-guides-button");
    assert.equal(app.document.querySelectorAll("[data-guide-axis]").length, 0);
    assert.equal(paths(app)[0], "M 10 10 L 30 10 L 30 30 L 10 30 Z");
    assert.equal(app.text("#save-state"), "Saved");
  }, dependenciesFixture(boardFixture(square)));
});

test("starting a touch pinch stops an active guide drag", async () => {
  const square = documentFixture([{
    id: 1,
    key: "square",
    type: "jug",
    displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z",
  }]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 100 } });
    await app.click('[data-hold-key="square"]');
    await app.click("#add-horizontal-guide-button");
    await app.pointer('[data-guide-axis="horizontal"]', "pointerdown", { pointerId: 17, clientX: 50, clientY: 20 });
    assert.equal(app.capturedPointerId("#editor-svg"), 17);
    assert.equal(await touchCanvas(app, "touchstart", [
      { clientX: 20, clientY: 20 },
      { clientX: 80, clientY: 20 },
    ]), true);
    assert.equal(app.capturedPointerId("#editor-svg"), null);
    await app.pointer("#editor-svg", "pointermove", { pointerId: 17, clientX: 50, clientY: 56 });

    assert.equal(app.document.querySelector('[data-guide-axis="horizontal"]')?.getAttribute("y1"), "20");
  }, dependenciesFixture(boardFixture(square)));
});

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

test("rotation drag rotates every Command-selected physical hold around its own centroid", async () => {
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    await app.mouse('[data-hold-key="b-piece-0"]', "click", { ctrlKey: true });
    assert.equal(app.document.querySelector('[data-hold-key="a-piece-0"]')?.getAttribute("aria-pressed"), "true");
    assert.equal(app.document.querySelector('[data-hold-key="b-piece-0"]')?.getAttribute("aria-pressed"), "true");

    const connector = app.document.querySelector<SVGLineElement>(".path-editor-rotation-connector")!;
    const handle = app.document.querySelector<SVGCircleElement>(".path-editor-rotation-handle")!;
    const primaryPivot = { x: Number(connector.getAttribute("x1")), y: Number(connector.getAttribute("y1")) };
    const start = { x: Number(handle.getAttribute("cx")), y: Number(handle.getAttribute("cy")) };
    const radius = Math.hypot(start.x - primaryPivot.x, start.y - primaryPivot.y);
    const startAngle = Math.atan2(start.y - primaryPivot.y, start.x - primaryPivot.x);
    const end = {
      x: primaryPivot.x + radius * Math.cos(startAngle + Math.PI / 2),
      y: primaryPivot.y + radius * Math.sin(startAngle + Math.PI / 2),
    };

    await drag(app, ".path-editor-rotation-handle", [start, end]);

    const physicalAPivot = holdCentroid(documentFixture().regions.slice(0, 2), pathEditor);
    const physicalBPivot = holdCentroid([documentFixture().regions[2]!], pathEditor);
    assert.equal(paths(app)[0], rotate(FIRST_PATH, 90, physicalAPivot));
    assert.equal(paths(app)[1], rotate(SECOND_PATH, 90, physicalAPivot));
    assert.equal(paths(app)[2], rotate(OTHER_PATH, 90, physicalBPivot));
  });
});

test("double-click inserts a vertex while right-click selects it and waits for an explicit Delete action", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="square"]');
    await app.mouse("#editor-svg", "dblclick", { clientX: 20, clientY: 10 });
    assert.equal(paths(app)[0], "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z");
    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2, clientX: 73, clientY: 41 });
    assert.equal(paths(app)[0], "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z");
    const selected = app.document.querySelector('.path-editor-vertex[data-index="1"]');
    assert.equal(selected?.classList.contains("selected"), true);
    assert.equal(selected?.getAttribute("aria-pressed"), "true");
    const menu = app.document.querySelector<HTMLElement>('[role="menu"]');
    assert.equal(menu?.style.left, "73px");
    assert.equal(menu?.style.top, "41px");
    assert.equal(app.text('[role="menuitem"]'), "Delete");
    assert.equal(app.disabled('[role="menuitem"]'), false);
    assert.equal(app.document.activeElement?.getAttribute("role"), "menuitem");
    await app.click('[role="menuitem"]');
    assert.equal(paths(app)[0], "M 10 10 L 30 10 L 30 30 L 10 30 Z");
    assert.equal(app.document.querySelector('[role="menu"]'), null);
    assert.equal(app.document.querySelector(".path-editor-vertex.selected"), null);
  }, dependenciesFixture(boardFixture(square)));
});

test("vertex menu rounds a corner as a persisted quadratic", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    await app.click('[data-hold-key="square"]');

    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2, clientX: 30, clientY: 10 });
    assert.equal(app.text("#round-corner-action"), "Round corner");
    await app.click("#round-corner-action");
    assert.equal(paths(app)[0], "M 10 10 L 26 10 Q 30 10 30 14 L 30 30 L 10 30 Z");
    assert.equal(app.document.querySelector('[role="menu"]'), null);
    assert.equal(app.document.querySelector(".path-editor-vertex.selected"), null);
  }, dependenciesFixture(boardFixture(square)));
});

test("straight-segment menu converts a segment to a bendable quadratic", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="square"]');
    await app.mouse('[data-hold-key="square"]', "contextmenu", { button: 2, clientX: 20, clientY: 10 });
    assert.equal(app.document.querySelector('[role="menu"]')?.getAttribute("aria-label"), "Line actions");
    assert.equal(app.text("#make-bendable-action"), "Make bendable");
    const invokingLine = app.document.querySelector<SVGPathElement>('[data-hold-key="square"]');
    assert.ok(invokingLine);
    assert.equal(await app.keyDown("#make-bendable-action", "Escape"), true);
    assert.equal(app.document.querySelector('[role="menu"]'), null);
    assert.equal(app.document.activeElement, invokingLine);

    await app.mouse('[data-hold-key="square"]', "contextmenu", { button: 2, clientX: 20, clientY: 10 });
    await app.click("#make-bendable-action");
    assert.equal(paths(app)[0], "M 10 10 Q 20 10 30 10 L 30 30 L 10 30 Z");
    assert.ok(app.document.querySelector('.path-editor-control[data-index="1"][data-control="0"]'));
    assert.equal(app.document.querySelector('[role="menu"]'), null);
  }, dependenciesFixture(boardFixture(square)));
});

test("line menu snaps a diagonal custom-outline segment to the chosen axis", async () => {
  for (const [action, expectedPath, expectedStatus] of [
    ["#make-horizontal-action", "M 10 10 L 30 10 L 30 40 L 10 40 Z", "Line made horizontal. Save when ready."],
    ["#make-vertical-action", "M 10 10 L 10 20 L 30 40 L 10 40 Z", "Line made vertical. Save when ready."],
  ] as const) {
    const diagonal = documentFixture([
      { id: 1, key: "diagonal", type: "jug", displayPath: "M 10 10 L 30 20 L 30 40 L 10 40 Z" },
    ]);
    await withEditor(async (app) => {
      app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
      await app.click('[data-hold-key="diagonal"]');
      await app.mouse('[data-hold-key="diagonal"]', "contextmenu", { button: 2, clientX: 20, clientY: 15 });

      assert.equal(app.document.querySelector('[role="menu"]')?.getAttribute("aria-label"), "Line actions");
      assert.equal(app.document.querySelector(action)?.textContent, action === "#make-horizontal-action" ? "Make horizontal" : "Make vertical");
      await app.click(action);
      assert.equal(paths(app)[0], expectedPath);
      assert.equal(app.text("#editor-status"), expectedStatus);
      assert.equal(app.document.querySelector('[role="menu"]'), null);
      assert.equal(app.document.querySelector(".path-editor-vertex.selected"), null);
    }, dependenciesFixture(boardFixture(diagonal)));
  }
});

test("curved-segment menu makes a quadratic segment straight and removes its control", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 Q 20 0 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="square"]');
    await app.mouse('[data-hold-key="square"]', "contextmenu", { button: 2, clientX: 20, clientY: 5 });

    assert.equal(app.document.querySelector('[role="menu"]')?.getAttribute("aria-label"), "Line actions");
    assert.equal(app.text("#make-straight-action"), "Make straight");
    await app.click("#make-straight-action");
    assert.equal(paths(app)[0], "M 10 10 L 30 10 L 30 30 L 10 30 Z");
    assert.equal(app.document.querySelector('.path-editor-control[data-index="1"][data-control="0"]'), null);
    assert.equal(app.document.querySelector('[role="menu"]'), null);
  }, dependenciesFixture(boardFixture(square)));
});

test("curved-segment menu adds an inflection point at the right-click location and labels its reversible removal", async () => {
  const square = documentFixture([
    { id: 1, key: "square", type: "jug", displayPath: "M 10 10 Q 10 50 50 50 L 50 10 Z" },
  ]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="square"]');
    await app.mouse('[data-hold-key="square"]', "contextmenu", { button: 2, clientX: 12.5, clientY: 27.5 });

    assert.equal(app.text("#add-inflection-point-action"), "Add inflection point");
    await app.click("#add-inflection-point-action");
    assert.match(paths(app)[0]!, /^M 10 10 Q 10 20(?:\.\d+)? 12\.5 27\.5/);

    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2, clientX: 12.5, clientY: 27.5 });
    assert.equal(app.text('[role="menuitem"]'), "Remove inflection point");
    await app.click('[role="menuitem"]');
    assert.equal(paths(app)[0], "M 10 10 Q 10 50 50 50 L 50 10 Z");
  }, dependenciesFixture(boardFixture(square)));
});

test("a serialized and dragged quadratic inflection point remains removable", async () => {
  const square = documentFixture([
    { id: 1, key: "square", type: "jug", displayPath: "M 0 0 Q 37.1234567 98.7654321 123.4567891 4.5678912 L 0 100 Z" },
  ]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 200, height: 150 } });
    await app.click('[data-hold-key="square"]');
    await app.mouse('[data-hold-key="square"]', "contextmenu", { button: 2, clientX: 6.456789, clientY: 17.654321 });
    await app.click("#add-inflection-point-action");

    const vertex = app.document.querySelector<SVGCircleElement>('.path-editor-vertex[data-index="1"]');
    const x = Number(vertex?.getAttribute("cx"));
    const y = Number(vertex?.getAttribute("cy"));
    assert.ok(Number.isFinite(x) && Number.isFinite(y));
    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2, clientX: x, clientY: y });
    assert.equal(app.text('[role="menuitem"]'), "Remove inflection point");
    await app.keyDown('[role="menuitem"]', "Escape");

    await drag(app, '.path-editor-vertex[data-index="1"]', [{ x, y }, { x: x + 8, y: y - 5 }]);
    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2, clientX: x + 8, clientY: y - 5 });
    assert.equal(app.text('[role="menuitem"]'), "Remove inflection point");
    await app.click('[role="menuitem"]');
    assert.equal(pathEditor.parsePath(paths(app)[0]!)[1]?.type, "Q");
  }, dependenciesFixture(boardFixture(square)));
});

test("straight-segment context menu chooses the closest eligible edge", async () => {
  const path = "M 10 10 L 30 10 L 30 30 L 10 30 Z";
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: path }]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="square"]');

    await app.mouse('[data-hold-key="square"]', "contextmenu", { button: 2, clientX: 28, clientY: 15 });
    await app.click("#make-bendable-action");

    assert.equal(paths(app)[0], "M 10 10 L 30 10 Q 30 20 30 30 L 10 30 Z");
  }, dependenciesFixture(boardFixture(square)));
});

test("changing holds closes a stale line menu before it can edit the new selection", async () => {
  const firstPath = "M 10 10 L 30 10 L 30 30 L 10 30 Z";
  const secondPath = "M 60 10 L 80 10 L 80 30 L 60 30 Z";
  const document = documentFixture([
    { id: 1, key: "first", type: "jug", displayPath: firstPath },
    { id: 2, key: "second", type: "edge", displayPath: secondPath },
  ]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="first"]');
    await app.mouse('[data-hold-key="first"]', "contextmenu", { button: 2, clientX: 20, clientY: 10 });
    assert.ok(app.document.querySelector('[role="menu"]'));

    await app.click('[data-hold-key="second"]');

    assert.equal(app.document.querySelector('[role="menu"]'), null);
    assert.deepEqual(paths(app), [firstPath, secondPath]);
  }, dependenciesFixture(boardFixture(document)));
});

test("vertex menu arrow navigation moves between actions without editing the selected hold", async () => {
  const squarePath = "M 10 10 L 30 10 L 30 30 L 10 30 Z";
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: squarePath }]);
  await withEditor(async (app) => {
    await app.click('[data-hold-key="square"]');
    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2 });

    const deleteItem = app.document.querySelector<HTMLElement>('[role="menuitem"]');
    const roundItem = app.document.querySelector<HTMLElement>("#round-corner-action");
    assert.ok(deleteItem);
    assert.ok(roundItem);
    assert.equal(app.document.activeElement, deleteItem);
    assert.equal(await app.keyDown('[role="menuitem"]', "ArrowDown"), true);
    assert.equal(app.document.activeElement, roundItem);
    assert.equal(await app.keyDown("#round-corner-action", "ArrowUp"), true);
    assert.equal(app.document.activeElement, deleteItem);
    for (const shortcut of ["[", "]"]) {
      assert.equal(await app.keyDown('[role="menuitem"]', shortcut), true);
      assert.equal(paths(app)[0], squarePath);
      assert.ok(app.document.querySelector('[role="menu"]'));
    }
    assert.equal(app.text("#save-state"), "Saved");
    assert.ok(app.document.querySelector('[role="menu"]'));
  }, dependenciesFixture(boardFixture(square)));
});

test("left pointer-down selects a vertex and secondary-button movement never starts a drag", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="square"]');

    await app.pointer('.path-editor-vertex[data-index="2"]', "pointerdown", {
      button: 0,
      pointerId: 7,
      clientX: 30,
      clientY: 30,
    });
    assert.equal(app.document.querySelector('.path-editor-vertex[data-index="2"]')?.classList.contains("selected"), true);
    assert.equal(app.document.querySelector('.path-editor-vertex[data-index="2"]')?.getAttribute("aria-pressed"), "true");
    await app.pointer("#editor-svg", "pointercancel", { pointerId: 7, clientX: 30, clientY: 30 });

    const beforeSecondaryDrag = paths(app)[0];
    await app.pointer('.path-editor-vertex[data-index="1"]', "pointerdown", {
      button: 2,
      pointerId: 8,
      clientX: 30,
      clientY: 10,
    });
    await app.pointer("#editor-svg", "pointermove", { button: 2, pointerId: 8, clientX: 45, clientY: 20 });
    await app.pointer("#editor-svg", "pointerup", { button: 2, pointerId: 8, clientX: 45, clientY: 20 });
    assert.equal(paths(app)[0], beforeSecondaryDrag);
  }, dependenciesFixture(boardFixture(square)));
});

test("left pointer-up preserves a valid vertex selection for keyboard deletion", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="square"]');
    await app.pointer('.path-editor-vertex[data-index="2"]', "pointerdown", {
      button: 0,
      pointerId: 11,
      clientX: 30,
      clientY: 30,
    });
    await app.pointer("#editor-svg", "pointerup", { button: 0, pointerId: 11, clientX: 30, clientY: 30 });

    assert.equal(app.document.querySelector('.path-editor-vertex[data-index="2"]')?.classList.contains("selected"), true);
    assert.equal(app.text("#save-state"), "Saved");
    assert.equal(await app.keyDown("body", "Delete"), true);
    assert.equal(paths(app)[0], "M 10 10 L 30 10 L 10 30 Z");
  }, dependenciesFixture(boardFixture(square)));
});

test("focusing another vertex selects it before keyboard deletion", async () => {
  const polygon = documentFixture([{
    id: 1,
    key: "polygon",
    type: "jug",
    displayPath: "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z",
  }]);
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="polygon"]');
    await app.pointer('.path-editor-vertex[data-index="1"]', "pointerdown", {
      button: 0,
      pointerId: 12,
      clientX: 20,
      clientY: 10,
    });
    await app.pointer("#editor-svg", "pointerup", { button: 0, pointerId: 12, clientX: 20, clientY: 10 });

    const focused = app.document.querySelector<SVGCircleElement>('.path-editor-vertex[data-index="3"]');
    assert.ok(focused);
    await app.flush(() => focused.focus());
    assert.equal(app.document.activeElement, focused);
    assert.equal(focused.getAttribute("aria-pressed"), "true");

    assert.equal(await app.keyDown("body", "Delete"), true);
    assert.equal(paths(app)[0], "M 10 10 L 20 10 L 30 10 L 10 30 Z");
  }, dependenciesFixture(boardFixture(polygon)));
});

test("vertex button Enter and Space activation select the targeted point", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    await app.click('[data-hold-key="square"]');

    assert.equal(await app.keyDown('.path-editor-vertex[data-index="1"]', "Enter"), false);
    assert.equal(app.document.querySelector('.path-editor-vertex[data-index="1"]')?.getAttribute("aria-pressed"), "true");
    assert.equal(await app.keyDown('.path-editor-vertex[data-index="2"]', " "), true);
    assert.equal(app.document.querySelector('.path-editor-vertex[data-index="2"]')?.getAttribute("aria-pressed"), "true");
    assert.equal(app.document.querySelector('.path-editor-vertex[data-index="1"]')?.getAttribute("aria-pressed"), "false");
  }, dependenciesFixture(boardFixture(square)));
});

test("four-vertex start vertices expose an enabled Delete action and are removed", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    await app.click('[data-hold-key="square"]');
    await app.mouse('.path-editor-vertex[data-index="0"]', "contextmenu", { button: 2 });
    assert.equal(app.disabled('[role="menuitem"]'), false);
    await app.click('[role="menuitem"]');
    assert.equal(paths(app)[0], "M 30 10 L 30 30 L 10 30 Z");
  }, dependenciesFixture(boardFixture(square)));
});

test("minimum-contour vertices expose a disabled Delete action without dirtying", async () => {
  await withEditor(async (app) => {
    await app.click('[data-hold-key="a-piece-0"]');
    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2 });
    assert.equal(app.disabled('[role="menuitem"]'), true);
    assert.equal(await app.keyDown("body", "Backspace"), false);
    assert.equal(paths(app)[0], FIRST_PATH);
    assert.equal(app.text("#save-state"), "Saved");
  });
});

test("Delete and Backspace remove only the selected eligible vertex and ignore form targets", async () => {
  const polygon = documentFixture([{
    id: 1,
    key: "polygon",
    type: "jug",
    displayPath: "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z",
  }]);
  await withEditor(async (app) => {
    await app.click('[data-hold-key="polygon"]');
    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2 });

    for (const selector of ["#rotate-by-input", "#hold-type-select"]) {
      const target = app.document.querySelector<HTMLElement>(selector);
      assert.ok(target);
      await app.flush(() => target.focus());
      assert.equal(await app.keyDown(selector, "Delete"), false);
      assert.equal(paths(app)[0], "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z");
    }
    const editable = app.document.querySelector<HTMLElement>("#hold-heading");
    assert.ok(editable);
    editable.setAttribute("contenteditable", "true");
    await app.flush(() => editable.focus());
    assert.equal(await app.keyDown("#hold-heading", "Delete"), false);
    assert.equal(paths(app)[0], "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z");
    editable.removeAttribute("contenteditable");

    assert.equal(await app.keyDown("body", "Delete"), true);
    assert.equal(paths(app)[0], "M 10 10 L 30 10 L 30 30 L 10 30 Z");
    assert.equal(app.document.querySelector(".path-editor-vertex.selected"), null);

    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2 });
    assert.equal(await app.keyDown("body", "Backspace"), true);
    assert.equal(paths(app)[0], "M 10 10 L 30 30 L 10 30 Z");
  }, dependenciesFixture(boardFixture(polygon)));
});

test("Escape returns focus to the selected vertex and outside pointer-down preserves target focus", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    await app.click('[data-hold-key="square"]');
    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2 });
    const selectedVertex = app.document.querySelector<SVGCircleElement>('.path-editor-vertex[data-index="1"]');
    assert.ok(selectedVertex);
    assert.ok(app.document.querySelector('[role="menu"]'));
    assert.equal(await app.keyDown('[role="menuitem"]', "Escape"), true);
    assert.equal(app.document.querySelector('[role="menu"]'), null);
    assert.ok(app.document.querySelector(".path-editor-vertex.selected"));
    assert.equal(app.document.activeElement, selectedVertex);

    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2 });
    const outsideTarget = app.document.querySelector<HTMLButtonElement>("#zoom-in-button");
    assert.ok(outsideTarget);
    outsideTarget.addEventListener("pointerdown", () => outsideTarget.focus(), { once: true });
    await app.pointer("#zoom-in-button", "pointerdown", { pointerId: 22 });
    assert.equal(app.document.querySelector('[role="menu"]'), null);
    assert.ok(app.document.querySelector(".path-editor-vertex.selected"));
    assert.equal(app.document.activeElement, outsideTarget);
  }, dependenciesFixture(boardFixture(square)));
});

test("the vertex menu measures and flips within the viewport edges", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    const windowValue = app.document.defaultView!;
    Object.defineProperty(windowValue, "innerWidth", { configurable: true, value: 200 });
    Object.defineProperty(windowValue, "innerHeight", { configurable: true, value: 100 });
    const originalGetBoundingClientRect = windowValue.HTMLElement.prototype.getBoundingClientRect;
    Object.defineProperty(windowValue.HTMLElement.prototype, "getBoundingClientRect", {
      configurable: true,
      value(this: HTMLElement): DOMRect {
        if (!this.classList.contains("path-editor-vertex-menu")) {
          return originalGetBoundingClientRect.call(this);
        }
        return {
          x: 190,
          y: 95,
          left: 190,
          top: 95,
          right: 270,
          bottom: 125,
          width: 80,
          height: 30,
          toJSON: () => ({}),
        } as DOMRect;
      },
    });

    await app.click('[data-hold-key="square"]');
    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", {
      button: 2,
      clientX: 190,
      clientY: 95,
    });

    const menu = app.document.querySelector<HTMLElement>('[role="menu"]');
    assert.equal(menu?.style.left, "110px");
    assert.equal(menu?.style.top, "65px");
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

test("menu deletion preserves prior status while clearing validation and marking dirty", async () => {
  const square = documentFixture([{ id: 1, key: "square", type: "jug", displayPath: "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z" }]);
  await withEditor(async (app) => {
    await app.click('[data-hold-key="square"]');
    await app.input("#rotate-by-input", "0");
    await app.click("#rotate-by-apply-button");
    const priorStatus = app.text("#editor-status");
    assert.match(priorStatus, /finite, non-zero rotation/i);
    assert.equal(app.document.querySelector("#validation-panel")?.classList.contains("hidden"), false);

    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2 });
    assert.equal(paths(app)[0], "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z");
    await app.click('[role="menuitem"]');

    assert.equal(paths(app)[0], "M 10 10 L 30 10 L 30 30 L 10 30 Z");
    assert.equal(app.text("#editor-status"), priorStatus);
    assert.equal(app.document.querySelector("#validation-panel")?.classList.contains("hidden"), true);
    assert.equal(app.text("#save-state"), "Unsaved changes");
  }, dependenciesFixture(boardFixture(square)));
});

test("failed menu deletion preserves the selected vertex and menu while exposing validation", async () => {
  const polygon = documentFixture([{
    id: 1,
    key: "polygon",
    type: "jug",
    displayPath: "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z",
  }]);
  await withEditor(async (app) => {
    await app.click('[data-hold-key="polygon"]');
    await app.mouse('.path-editor-vertex[data-index="1"]', "contextmenu", { button: 2 });
    await app.click('[role="menuitem"]');

    assert.equal(paths(app)[0], "M 10 10 L 20 10 L 30 10 L 30 30 L 10 30 Z");
    assert.ok(app.document.querySelector(".path-editor-vertex.selected"));
    assert.ok(app.document.querySelector('[role="menu"]'));
    assert.match(app.text("#validation-list"), /forced deletion rejection/i);
    assert.equal(app.text("#save-state"), "Saved");
  }, dependenciesFixture(boardFixture(polygon), {
    validate(document) {
      const validated = controller.validateEditorDocument(document);
      const vertexCount = pathEditor.parsePath(validated.regions[0]!.displayPath)
        .filter((command) => command.type !== "Z").length;
      if (vertexCount < 5) throw new Error("Forced deletion rejection");
      return validated;
    },
  }));
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
  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="a-piece-0"]');
    await drag(app, '.path-editor-vertex[data-index="1"]', [{ x: 20, y: 10 }, { x: 25, y: 15 }]);
    assert.equal(paths(app)[0], FIRST_PATH);
    assert.equal(app.text("#save-state"), "Saved");
    assert.match(app.text("#editor-status"), /reverted/i);
  }, dependenciesFixture(boardFixture(), {
    validate() {
      throw new Error("invalid contour");
    },
  }));
});

test("malformed selected paths report interaction failures instead of throwing", async () => {
  const malformedBoard = boardFixture(documentFixture([
    { id: 1, key: "malformed-piece-0", type: "jug", displayPath: "M 1 2 L 3 Z" },
  ]));

  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="malformed-piece-0"]');
    await app.pointer('[data-hold-key="malformed-piece-0"]', "pointerdown", {
      pointerId: 7,
      clientX: 10,
      clientY: 10,
    });
    assert.match(app.text("#editor-status"), /could not edit.*invalid path/i);
  }, dependenciesFixture(malformedBoard));

  await withEditor(async (app) => {
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click('[data-hold-key="malformed-piece-0"]');
    await app.mouse("#editor-svg", "dblclick", { clientX: 10, clientY: 10 });
    assert.match(app.text("#editor-status"), /could not edit.*invalid path/i);
  }, dependenciesFixture(malformedBoard));
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

test("outline picker reflects persisted constraints and changes every piece of the selected physical hold", async () => {
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
      "M 35 10 C 37.761424 10 40 12.238576 40 15 C 40 17.761424 37.761424 20 35 20 C 32.238576 20 30 17.761424 30 15 C 30 12.238576 32.238576 10 35 10 Z",
      OTHER_PATH,
    ]);
    assert.equal(app.text("#save-state"), "Unsaved changes");
    assert.equal(app.text("#editor-status"), "Outline changed to oval. Save when ready.");
    await app.click('[data-hold-key="a-piece-1"]');
    assert.equal(app.documentValue("#outline-shape-select"), "oval");
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

test("invalid outline actions preserve geometry while save-in-progress edits remain unsaved", async () => {
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
    assert.equal(app.disabled("#outline-shape-select"), false);
    assert.equal(app.disabled("#hold-type-select"), false);
    assert.equal(app.disabled("#rotate-cw-button"), false);
    assert.equal(app.disabled("#delete-hold-button"), false);
    await app.change("#outline-shape-select", "oval");
    const convertedPath = paths(app)[0]!;
    assert.notEqual(convertedPath, originalPath);
    await app.pointer('.path-editor-resize-handle[data-handle="e"]', "pointerdown", { pointerId: 19, clientX: 50, clientY: 20 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 19, clientX: 60, clientY: 20 });
    const resizedPath = paths(app)[0]!;
    assert.notEqual(resizedPath, convertedPath);
    assert.equal(app.capturedPointerId("#editor-svg"), 19);
    await app.pointer("#editor-svg", "pointerup", { pointerId: 19, clientX: 60, clientY: 20 });
    assert.equal(app.capturedPointerId("#editor-svg"), null);
    assert.equal(paths(app)[0], resizedPath);
    assert.equal(app.text("#save-state"), "Working…");
    await app.flush(() => { resolveSave?.(board); });
    assert.equal(paths(app)[0], resizedPath);
    assert.equal(app.text("#save-state"), "Unsaved changes");
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

test("constrained resize keeps circles circular, isolates siblings, and allows finite off-canvas endpoints", async () => {
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

    await app.pointer('.path-editor-resize-handle[data-handle="e"]', "pointerdown", { pointerId: 7, clientX: 50, clientY: 20 });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 7, clientX: 130, clientY: 20 });
    await app.pointer("#editor-svg", "pointerup", { pointerId: 7, clientX: 130, clientY: 20 });
    assert.equal(paths(app)[0], "M 75 -35 C 105.375661 -35 130 -10.375661 130 20 C 130 50.375661 105.375661 75 75 75 C 44.624339 75 20 50.375661 20 20 C 20 -10.375661 44.624339 -35 75 -35 Z");
    assert.doesNotMatch(app.text("#editor-status"), /reverted/i);
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
