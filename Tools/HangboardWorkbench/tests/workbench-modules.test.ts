import assert from "node:assert/strict";
import test from "node:test";

import {
  createBoardOperationCoordinator,
  loadBoardAtomically,
  saveBoardAtomically,
  validateEditorDocument,
  validateEditorDocumentForSave,
} from "../src/workbench-controller.ts";
import { resolveCordRigPresentationGeometry } from "../src/cord-rig.ts";
import { createWorkbenchClient } from "../src/workbench-client.ts";
import { cloneEditorDocument } from "../src/editor-model.ts";
import { postNativeDiagnostic } from "../src/native-bridge.ts";
import * as pathEditor from "../src/path-editor.ts";
import type {
  Board,
  BoardPresentation,
  BrowserRuntime,
  Dialogs,
  DirectTwoAnchorCordRig,
  EditorDocument,
  LoadedBoard,
  PathEditor,
  Point,
  RoutedCordRig,
  WorkbenchClient,
  WorkbenchController,
  WorkbenchDependencies,
} from "../src/types.ts";

function response(payload: unknown, options: { ok?: boolean; status?: number } = {}): Response {
  const ok = options.ok ?? true;
  const status = options.status ?? (ok ? 200 : 400);
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

interface RuntimeFixture {
  runtime: BrowserRuntime;
  assignedUrls: string[];
}

function runtimeFixture(fetchImplementation: BrowserRuntime["fetch"]): RuntimeFixture {
  const assignedUrls: string[] = [];
  const runtime: BrowserRuntime = {
    fetch: fetchImplementation,
    location: {
      assign(url: string): void {
        assignedUrls.push(url);
      },
    },
    confirm(_message: string): boolean {
      return true;
    },
    prompt(_message: string, _defaultValue?: string): string | null {
      return null;
    },
    createImage(): HTMLImageElement {
      throw new Error("createImage is not used by module tests");
    },
  };
  return { runtime, assignedUrls };
}

function editorDocument(regions: EditorDocument["regions"] = []): EditorDocument {
  return { canvas: { width: 100, height: 50 }, regions };
}

function boardFixture(overrides: Partial<Board> = {}): Board {
  return {
    boardId: "compact",
    displayName: "Compact",
    holdCount: 0,
    imageUrl: "/api/boards/compact/image",
    document: editorDocument(),
    ...overrides,
  };
}

function routedRenderRig(overrides: Partial<RoutedCordRig> = {}): RoutedCordRig {
  return {
    type: "routed",
    sceneSize: { width: 200, height: 200 },
    sourceFrame: { x: 40, y: 40, width: 120, height: 120 },
    innerFaceFrame: { x: 0, y: 0, width: 120, height: 120 },
    style: {
      diameter: 10,
      outlineColor: "#101010",
      baseColor: "#2255AA",
      braidColors: ["#FFD000", "#0055CC"],
    },
    ports: [
      { id: "body-left", space: "body", point: { x: 30, y: 90 } },
      { id: "body-right", space: "body", point: { x: 90, y: 90 } },
      { id: "world-left", space: "world", point: { x: 10, y: 10 } },
      { id: "world-right", space: "world", point: { x: 110, y: 10 } },
    ],
    tensionGroups: [{
      id: "main",
      bodyPortIDs: ["body-left", "body-right"],
      worldPortIDs: ["world-left", "world-right"],
      pairing: "declared",
      layer: "behindFace",
    }],
    paths: [
      {
        id: "world-tail",
        space: "world",
        layer: "behindFace",
        commands: [
          { command: "move", to: [15, 15] },
          { command: "line", to: [25, 15] },
        ],
      },
      {
        id: "body-return",
        space: "body",
        layer: "aboveFace",
        commands: [
          { command: "move", to: [30, 90] },
          { command: "quad", control: [60, 110], to: [90, 90] },
        ],
      },
      {
        id: "world-knot",
        space: "world",
        layer: "overpass",
        commands: [
          { command: "move", to: [45, 15] },
          { command: "curve", control1: [50, 5], control2: [70, 5], to: [75, 15] },
        ],
      },
    ],
    occlusions: [
      { type: "radialLip", bodyPortID: "body-left", radius: 6, chordOffset: 2 },
      {
        type: "facePatch",
        commands: [
          { command: "move", to: [80, 70] },
          { command: "line", to: [100, 70] },
          { command: "line", to: [100, 85] },
          { command: "close" },
        ],
      },
    ],
    ...overrides,
  };
}

function circularArcClipContains(
  path: string,
  center: { x: number; y: number },
  point: { x: number; y: number },
): boolean {
  const tokens = path.split(" ");
  assert.equal(tokens.length, 12, `unexpected circular-arc path: ${path}`);
  assert.equal(tokens[0], "M");
  assert.equal(tokens[3], "A");
  assert.equal(tokens[6], "0");
  assert.equal(tokens[11], "Z");
  const start = { x: Number(tokens[1]), y: Number(tokens[2]) };
  const radius = Number(tokens[4]);
  assert.equal(Number(tokens[5]), radius);
  const largeArc = tokens[7] === "1";
  const positiveSweep = tokens[8] === "1";
  const end = { x: Number(tokens[9]), y: Number(tokens[10]) };
  const startAngle = Math.atan2(start.y - center.y, start.x - center.x);
  const endAngle = Math.atan2(end.y - center.y, end.x - center.x);
  const fullTurn = 2 * Math.PI;
  let sweep = ((endAngle - startAngle) % fullTurn + fullTurn) % fullTurn;
  if (!positiveSweep) sweep -= fullTurn;
  if (largeArc && Math.abs(sweep) < Math.PI) sweep += positiveSweep ? fullTurn : -fullTurn;
  if (!largeArc && Math.abs(sweep) > Math.PI) sweep += positiveSweep ? -fullTurn : fullTurn;
  const arcMidpointAngle = startAngle + sweep / 2;
  const arcMidpoint = {
    x: center.x + radius * Math.cos(arcMidpointAngle),
    y: center.y + radius * Math.sin(arcMidpointAngle),
  };
  const sideOfChord = (candidate: { x: number; y: number }): number => (
    (end.x - start.x) * (candidate.y - start.y)
      - (end.y - start.y) * (candidate.x - start.x)
  );
  return Math.hypot(point.x - center.x, point.y - center.y) <= radius
    && sideOfChord(point) * sideOfChord(arcMidpoint) >= 0;
}

test("the browser client lists and opens direct boards", async () => {
  const calls: string[] = [];
  const { runtime } = runtimeFixture(async (input) => {
    const request = String(input);
    calls.push(request);
    if (request === "/api/boards") {
      return response({
        ok: true,
        boards: [{
          boardId: "compact",
          displayName: "Compact",
          holdCount: 10,
          needsAttention: false,
          imageUrl: "/api/boards/compact/image",
        }],
      });
    }
    return response({ ok: true, board: boardFixture({ holdCount: 10 }) });
  });
  const client: WorkbenchClient = createWorkbenchClient(runtime);

  assert.deepEqual(await client.listBoards(), [
    {
      boardId: "compact",
      displayName: "Compact",
      holdCount: 10,
      needsAttention: false,
      imageUrl: "/api/boards/compact/image",
    },
  ]);
  assert.equal((await client.getBoard("compact")).boardId, "compact");
  assert.deepEqual(calls, ["/api/boards", "/api/boards/compact"]);
});

test("the browser client requests and validates a selected presentation", async () => {
  const calls: string[] = [];
  const document: EditorDocument = {
    presentationID: "back",
    canvas: { width: 80, height: 120 },
    regions: [{
      key: "back-hold-piece-0",
      displayPath: "M 1 1 L 20 1 L 20 20 Z",
      metadata: { holdID: "back-hold", pieceIndex: 0, presentationID: "back" },
    }],
  };
  const { runtime } = runtimeFixture(async (input) => {
    calls.push(String(input));
    return response({
      ok: true,
      board: boardFixture({
        imageUrl: "/api/boards/compact/image?presentationID=back",
        selectedPresentationID: "back",
        presentations: [
          {
            presentationID: "front",
            displayName: "Front",
            imageUrl: "/api/boards/compact/image?presentationID=front",
            default: true,
          },
          {
            presentationID: "back",
            displayName: "Back",
            imageUrl: "/api/boards/compact/image?presentationID=back",
            default: false,
          },
        ],
        document,
      }),
    });
  });

  const board = await createWorkbenchClient(runtime).getBoard("compact", "back");

  assert.equal(board.selectedPresentationID, "back");
  assert.equal(board.document.presentationID, "back");
  assert.equal(board.document.regions[0]?.metadata?.presentationID, "back");
  assert.deepEqual(calls, ["/api/boards/compact?presentationID=back"]);
});

test("the browser client preserves valid inverted alias anchor metadata", async () => {
  const alias: BoardPresentation = {
    presentationID: "front-inverted",
    displayName: "Front inverted",
    imageUrl: "/api/boards/compact/image?presentationID=front-inverted",
    default: false,
    sourcePresentationID: "front",
    availableHoldIDs: ["hold-1"],
    isInverted: true,
    geometryRotationAnchor: { x: 0.5, y: 0.68 },
  };
  const { runtime } = runtimeFixture(async () => response({
    ok: true,
    board: boardFixture({
      presentations: [
        {
          presentationID: "front",
          displayName: "Front",
          imageUrl: "/api/boards/compact/image?presentationID=front",
          default: true,
        },
        alias,
      ],
    }),
  }));

  const board = await createWorkbenchClient(runtime).getBoard("compact");

  assert.deepEqual(board.presentations?.[1], alias);
});

test("the browser client rejects malformed available hold IDs", async (context) => {
  const invalidValues: unknown[] = [null, [], ["hold-1", "hold-1"], [1]];

  for (const availableHoldIDs of invalidValues) {
    await context.test(JSON.stringify(availableHoldIDs), async () => {
      const { runtime } = runtimeFixture(async () => response({
        ok: true,
        board: boardFixture({
          presentations: [{
            presentationID: "front",
            displayName: "Front",
            imageUrl: "/api/boards/compact/image?presentationID=front",
            default: true,
            availableHoldIDs,
          } as unknown as BoardPresentation],
        }),
      }));

      await assert.rejects(
        createWorkbenchClient(runtime).getBoard("compact"),
        /invalid board/,
      );
    });
  }
});

test("the browser client preserves an explicit arbitrary alias rotation", async () => {
  const alias: BoardPresentation = {
    presentationID: "front-angled",
    displayName: "Front angled",
    imageUrl: "/api/boards/compact/image?presentationID=front-angled",
    default: false,
    sourcePresentationID: "front",
    rotationDegrees: 135,
    geometryRotationAnchor: { x: 0.5, y: 0.68 },
  };
  const { runtime } = runtimeFixture(async () => response({
    ok: true,
    board: boardFixture({ presentations: [alias] }),
  }));

  const board = await createWorkbenchClient(runtime).getBoard("compact");

  assert.deepEqual(board.presentations?.[0], alias);
});

test("the browser client preserves a canonical direct-two-anchor cord rig", async () => {
  const rig: DirectTwoAnchorCordRig = {
    type: "directTwoAnchor",
    sceneSize: { width: 100, height: 400 },
    sourceFrame: { x: 0, y: 200, width: 100, height: 100 },
    innerFaceFrame: { x: 0, y: 0, width: 100, height: 100 },
    attachmentPoints: [{ x: 20, y: 50 }, { x: 80, y: 50 }],
    pullPoint: { x: 50, y: 0 },
    eyeletRadius: 2,
  };
  const { runtime } = runtimeFixture(async () => response({
    ok: true,
    board: boardFixture({
      presentations: [{
        presentationID: "front",
        displayName: "Front",
        imageUrl: "/api/boards/compact/image?presentationID=front",
        default: true,
        cordRig: rig,
      }],
    }),
  }));

  const board = await createWorkbenchClient(runtime).getBoard("compact");

  assert.deepEqual(
    (board.presentations?.[0] as unknown as { cordRig?: unknown })?.cordRig,
    rig,
  );
});

test("the browser client preserves a structurally valid canonical routed cord rig", async () => {
  const rig: RoutedCordRig = {
    type: "routed",
    sceneSize: { width: 100, height: 200 },
    sourceFrame: { x: 0, y: 100, width: 100, height: 100 },
    innerFaceFrame: { x: 0, y: 0, width: 100, height: 100 },
    style: {
      diameter: 4,
      outlineColor: "#101010",
      baseColor: "#2255AA",
      braidColors: ["#FFD000", "#0055CC"],
    },
    ports: [
      { id: "body-left", space: "body", point: { x: 20, y: 50 } },
      { id: "world-left", space: "world", point: { x: 20, y: 0 } },
    ],
    tensionGroups: [{
      id: "main",
      bodyPortIDs: ["body-left"],
      worldPortIDs: ["world-left"],
      pairing: "declared",
      layer: "behindFace",
    }],
    paths: [{
      id: "return",
      space: "body",
      layer: "aboveFace",
      commands: [
        { command: "move", to: [20, 50] },
        { command: "quad", control: [50, 90], to: [80, 50] },
      ],
    }],
    occlusions: [{
      type: "radialLip",
      bodyPortID: "body-left",
      radius: 6,
      chordOffset: 2,
    }],
  };
  const { runtime } = runtimeFixture(async () => response({
    ok: true,
    board: boardFixture({
      presentations: [{
        presentationID: "front",
        displayName: "Front",
        imageUrl: "/api/boards/compact/image?presentationID=front",
        default: true,
        cordRig: rig,
      }],
    }),
  }));

  const board = await createWorkbenchClient(runtime).getBoard("compact");

  assert.deepEqual(board.presentations?.[0]?.cordRig, rig);
});

test("the browser client rejects malformed routed cord structure", async (context) => {
  const baseRig = {
    type: "routed",
    sceneSize: { width: 100, height: 200 },
    sourceFrame: { x: 0, y: 100, width: 100, height: 100 },
    innerFaceFrame: { x: 0, y: 0, width: 100, height: 100 },
    style: {
      diameter: 4,
      outlineColor: "#101010",
      baseColor: "#2255AA",
      braidColors: ["#FFD000", "#0055CC"],
    },
    ports: [
      { id: "body-left", space: "body", point: { x: 20, y: 50 } },
      { id: "world-left", space: "world", point: { x: 20, y: 0 } },
    ],
    tensionGroups: [{
      id: "main",
      bodyPortIDs: ["body-left"],
      worldPortIDs: ["world-left"],
      pairing: "declared",
      layer: "behindFace",
    }],
    paths: [],
    occlusions: [],
  };
  const cases: Array<[string, (rig: Record<string, any>) => void]> = [
    ["unknown key", (rig) => { rig.extra = true; }],
    ["bad color", (rig) => { rig.style.baseColor = "blue"; }],
    ["duplicate ports", (rig) => { rig.ports.push({ ...rig.ports[0] }); }],
    ["wrong port space", (rig) => { rig.ports[0].space = "world"; }],
    ["unequal cardinality", (rig) => { rig.tensionGroups[0].worldPortIDs = ["world-left", "world-left-2"]; }],
    ["multiple closes", (rig) => {
      rig.paths = [{
        id: "bad-path",
        space: "body",
        layer: "aboveFace",
        commands: [
          { command: "move", to: [0, 0] },
          { command: "close" },
          { command: "close" },
        ],
      }];
    }],
    ["move and close path without a drawing segment", (rig) => {
      rig.paths = [{
        id: "bad-path",
        space: "body",
        layer: "aboveFace",
        commands: [
          { command: "move", to: [20, 50] },
          { command: "close" },
        ],
      }];
    }],
    ["move and close face patch without a drawing segment", (rig) => {
      rig.occlusions = [{
        type: "facePatch",
        commands: [
          { command: "move", to: [20, 50] },
          { command: "close" },
        ],
      }];
    }],
  ];

  for (const [name, mutate] of cases) {
    await context.test(name, async () => {
      const rig = structuredClone(baseRig);
      mutate(rig);
      const { runtime } = runtimeFixture(async () => response({
        ok: true,
        board: boardFixture({
          presentations: [{
            presentationID: "front",
            displayName: "Front",
            imageUrl: "/api/boards/compact/image?presentationID=front",
            default: true,
            cordRig: rig,
          } as unknown as BoardPresentation],
        }),
      }));

      await assert.rejects(
        createWorkbenchClient(runtime).getBoard("compact"),
        /invalid board/,
      );
    });
  }
});

test("routed rig geometry rotates body points clockwise while world points stay fixed", () => {
  const document: EditorDocument = {
    presentationID: "front-quarter-turn",
    canvas: { width: 120, height: 120 },
    regions: [],
  };
  const board = boardFixture({
    document,
    selectedPresentationID: "front-quarter-turn",
    presentations: [
      {
        presentationID: "front",
        displayName: "Front",
        imageUrl: "/api/boards/compact/image?presentationID=front",
        default: true,
        cordRig: routedRenderRig(),
      },
      {
        presentationID: "front-quarter-turn",
        displayName: "Front quarter turn",
        imageUrl: "/api/boards/compact/image?presentationID=front-quarter-turn",
        default: false,
        sourcePresentationID: "front",
        rotationDegrees: 90,
        geometryRotationAnchor: { x: 0.5, y: 0.5 },
      },
    ],
  });

  const geometry = resolveCordRigPresentationGeometry(board, document) as unknown as {
    type: "routed";
    viewBox: { x: number; y: number; width: number; height: number };
    rotationAnchor: Point;
    layers: Record<"behindFace" | "aboveFace" | "overpass", Array<{
      kind: "span" | "path";
      id: string;
      d: string;
      bodyPortID?: string;
      worldPortID?: string;
    }>>;
    occlusions: Array<{ type: "radialLip" | "facePatch"; d: string }>;
  } | null;

  assert.ok(geometry);
  assert.equal(geometry.type, "routed");
  assert.deepEqual(geometry.viewBox, { x: -40, y: -40, width: 200, height: 200 });
  assert.deepEqual(geometry.rotationAnchor, { x: 60, y: 60 });
  assert.deepEqual(geometry.layers.behindFace, [
    {
      kind: "span",
      id: "main:0",
      bodyPortID: "body-left",
      worldPortID: "world-left",
      d: "M 10 10 L 30 30",
    },
    {
      kind: "span",
      id: "main:1",
      bodyPortID: "body-right",
      worldPortID: "world-right",
      d: "M 110 10 L 30 90",
    },
    { kind: "path", id: "world-tail", d: "M 15 15 L 25 15" },
  ]);
  assert.deepEqual(geometry.layers.aboveFace, [
    { kind: "path", id: "body-return", d: "M 30 30 Q 10 60 30 90" },
  ]);
  assert.deepEqual(geometry.layers.overpass, [
    { kind: "path", id: "world-knot", d: "M 45 15 C 50 5 70 5 75 15" },
  ]);
  assert.equal(geometry.occlusions[0]?.type, "radialLip");
  assert.match(geometry.occlusions[0]?.d ?? "", /^M 32\.585786437627 24\.585786437627 A 6 6/);
  assert.deepEqual(geometry.occlusions[1], {
    type: "facePatch",
    d: "M 50 80 L 50 100 L 35 100 Z",
  });
});

test("routed screenOrder pairing stable-sorts transformed ports by x, y, then declaration index", () => {
  const rig = routedRenderRig({
    ports: [
      { id: "body-second", space: "body", point: { x: 30, y: 100 } },
      { id: "body-first", space: "body", point: { x: 30, y: 90 } },
      { id: "world-second", space: "world", point: { x: 10, y: 10 } },
      { id: "world-first", space: "world", point: { x: 10, y: 10 } },
    ],
    tensionGroups: [{
      id: "ordered",
      bodyPortIDs: ["body-second", "body-first"],
      worldPortIDs: ["world-second", "world-first"],
      pairing: "screenOrder",
      layer: "behindFace",
    }],
    paths: [],
    occlusions: [],
  });
  const document: EditorDocument = { canvas: { width: 120, height: 120 }, regions: [] };
  const board = boardFixture({
    document,
    selectedPresentationID: "front",
    presentations: [{
      presentationID: "front",
      displayName: "Front",
      imageUrl: "/api/boards/compact/image?presentationID=front",
      default: true,
      cordRig: rig,
    }],
  });

  const geometry = resolveCordRigPresentationGeometry(board, document) as unknown as {
    type: "routed";
    layers: { behindFace: Array<{ bodyPortID?: string; worldPortID?: string }> };
  } | null;

  assert.ok(geometry);
  assert.equal(geometry.type, "routed");
  assert.deepEqual(
    geometry.layers.behindFace.map(({ bodyPortID, worldPortID }) => ({ bodyPortID, worldPortID })),
    [
      { bodyPortID: "body-first", worldPortID: "world-second" },
      { bodyPortID: "body-second", worldPortID: "world-first" },
    ],
  );
});

test("the eyelet foreground keeps the board-side face above the incoming cord", () => {
  const rig: DirectTwoAnchorCordRig = {
    type: "directTwoAnchor",
    sceneSize: { width: 100, height: 200 },
    sourceFrame: { x: 0, y: 100, width: 100, height: 100 },
    innerFaceFrame: { x: 0, y: 0, width: 100, height: 100 },
    attachmentPoints: [{ x: 20, y: 50 }, { x: 64, y: 50 }],
    pullPoint: { x: 42, y: 0 },
    eyeletRadius: 10,
  };
  const document: EditorDocument = {
    canvas: { width: 100, height: 100 },
    regions: [],
  };
  const board = boardFixture({
    document,
    selectedPresentationID: "front",
    presentations: [{
      presentationID: "front",
      displayName: "Front",
      imageUrl: "/api/boards/compact/image?presentationID=front",
      default: true,
      cordRig: rig,
    }],
  });

  const geometry = resolveCordRigPresentationGeometry(board, document);
  assert.ok(geometry);
  if (geometry.type !== "directTwoAnchor") assert.fail("expected a direct-two-anchor rig");
  const strand = geometry.strands[0];
  const path = geometry.eyeletForegroundCrescents[0];
  assert.deepEqual(strand, { start: { x: 20, y: 0 }, end: { x: 20, y: 50 } });
  assert.equal(circularArcClipContains(path, strand.end, { x: 20, y: 58 }), true);
  assert.equal(circularArcClipContains(path, strand.end, { x: 20, y: 42 }), false);
});

test("the browser client rejects malformed or illegally placed alias anchors", async (context) => {
  const invalidPresentations: Array<{ name: string; presentation: unknown }> = [
    {
      name: "null anchor",
      presentation: {
        presentationID: "front-inverted",
        displayName: "Front inverted",
        imageUrl: "/api/boards/compact/image?presentationID=front-inverted",
        default: false,
        sourcePresentationID: "front",
        isInverted: true,
        geometryRotationAnchor: null,
      },
    },
    {
      name: "missing anchor coordinate",
      presentation: {
        presentationID: "front-inverted",
        displayName: "Front inverted",
        imageUrl: "/api/boards/compact/image?presentationID=front-inverted",
        default: false,
        sourcePresentationID: "front",
        isInverted: true,
        geometryRotationAnchor: { x: 0.5 },
      },
    },
    {
      name: "unknown anchor key",
      presentation: {
        presentationID: "front-inverted",
        displayName: "Front inverted",
        imageUrl: "/api/boards/compact/image?presentationID=front-inverted",
        default: false,
        sourcePresentationID: "front",
        isInverted: true,
        geometryRotationAnchor: { x: 0.5, y: 0.68, z: 0 },
      },
    },
    {
      name: "coordinate outside the normalized canvas",
      presentation: {
        presentationID: "front-inverted",
        displayName: "Front inverted",
        imageUrl: "/api/boards/compact/image?presentationID=front-inverted",
        default: false,
        sourcePresentationID: "front",
        isInverted: true,
        geometryRotationAnchor: { x: 0.5, y: 1.01 },
      },
    },
    {
      name: "anchor on a source presentation",
      presentation: {
        presentationID: "front",
        displayName: "Front",
        imageUrl: "/api/boards/compact/image?presentationID=front",
        default: true,
        isInverted: true,
        geometryRotationAnchor: { x: 0.5, y: 0.68 },
      },
    },
    {
      name: "anchor on a non-inverted alias",
      presentation: {
        presentationID: "front-alias",
        displayName: "Front alias",
        imageUrl: "/api/boards/compact/image?presentationID=front-alias",
        default: false,
        sourcePresentationID: "front",
        geometryRotationAnchor: { x: 0.5, y: 0.68 },
      },
    },
    {
      name: "explicit false inversion flag",
      presentation: {
        presentationID: "front-alias",
        displayName: "Front alias",
        imageUrl: "/api/boards/compact/image?presentationID=front-alias",
        default: false,
        sourcePresentationID: "front",
        isInverted: false,
      },
    },
    {
      name: "rotation on a source presentation",
      presentation: {
        presentationID: "front",
        displayName: "Front",
        imageUrl: "/api/boards/compact/image?presentationID=front",
        default: true,
        rotationDegrees: 90,
      },
    },
    {
      name: "rotation outside normalized range",
      presentation: {
        presentationID: "front-alias",
        displayName: "Front alias",
        imageUrl: "/api/boards/compact/image?presentationID=front-alias",
        default: false,
        sourcePresentationID: "front",
        rotationDegrees: 360,
      },
    },
    {
      name: "legacy and explicit rotation together",
      presentation: {
        presentationID: "front-alias",
        displayName: "Front alias",
        imageUrl: "/api/boards/compact/image?presentationID=front-alias",
        default: false,
        sourcePresentationID: "front",
        isInverted: true,
        rotationDegrees: 180,
      },
    },
    {
      name: "unknown presentation key",
      presentation: {
        presentationID: "front-alias",
        displayName: "Front alias",
        imageUrl: "/api/boards/compact/image?presentationID=front-alias",
        default: false,
        sourcePresentationID: "front",
        unexpected: true,
      },
    },
  ];

  for (const fixture of invalidPresentations) {
    await context.test(fixture.name, async () => {
      const { runtime } = runtimeFixture(async () => response({
        ok: true,
        board: boardFixture({ presentations: [fixture.presentation] as never[] }),
      }));

      await assert.rejects(
        createWorkbenchClient(runtime).getBoard("compact"),
        /invalid board/,
      );
    });
  }
});

test("the browser client rejects a non-finite alias anchor coordinate", async () => {
  const payload = JSON.stringify({
    ok: true,
    board: boardFixture({
      presentations: [{
        presentationID: "front-inverted",
        displayName: "Front inverted",
        imageUrl: "/api/boards/compact/image?presentationID=front-inverted",
        default: false,
        sourcePresentationID: "front",
        isInverted: true,
        geometryRotationAnchor: { x: "__nonfinite__", y: 0.68 },
      }] as never[],
    }),
  }).replace('"__nonfinite__"', "1e999");
  const { runtime } = runtimeFixture(async () => new Response(payload, {
    status: 200,
    headers: { "Content-Type": "application/json" },
  }));

  await assert.rejects(
    createWorkbenchClient(runtime).getBoard("compact"),
    /invalid board/,
  );
});

test("the browser client deletes a selected presentation and returns the next focused board", async () => {
  const calls: Array<{ request: string; options: RequestInit | undefined }> = [];
  const { runtime } = runtimeFixture(async (input, options) => {
    calls.push({ request: String(input), options });
    return response({
      ok: true,
      board: boardFixture({
        selectedPresentationID: "back",
        presentations: [{
          presentationID: "back",
          displayName: "Back",
          imageUrl: "/api/boards/compact/image?presentationID=back",
          default: true,
        }],
        document: {
          presentationID: "back",
          canvas: { width: 100, height: 50 },
          regions: [],
        },
      }),
    });
  });
  const client = createWorkbenchClient(runtime) as unknown as {
    deletePresentation(boardID: string, presentationID: string): Promise<Board>;
  };

  const board = await client.deletePresentation("compact", "front");

  assert.equal(board.selectedPresentationID, "back");
  assert.equal(calls[0]?.request, "/api/boards/compact/presentations/front");
  assert.equal(calls[0]?.options?.method, "DELETE");
});

test("backend requests carry a fifteen-second timeout signal", async (context) => {
  const timeoutSignal = new AbortController().signal;
  const timeout = context.mock.method(AbortSignal, "timeout", () => timeoutSignal);
  let requestOptions: RequestInit | undefined;
  const { runtime } = runtimeFixture(async (_input, options) => {
    requestOptions = options;
    return response({ ok: true, boards: [] });
  });

  await createWorkbenchClient(runtime).listBoards();

  assert.equal(timeout.mock.callCount(), 1);
  assert.deepEqual(timeout.mock.calls[0]?.arguments, [15_000]);
  assert.equal(requestOptions?.signal, timeoutSignal);
});

test("the browser entry module can be imported without a document", async () => {
  assert.equal(typeof globalThis.document, "undefined");
  await assert.doesNotReject(import("../src/main.tsx"));
});

test("the browser client rejects invalid optional board URLs", async () => {
  const { runtime } = runtimeFixture(async (input) => {
    if (String(input) === "/api/boards") {
      return response({
        ok: true,
        boards: [{
          boardId: "compact",
          displayName: "Compact",
          holdCount: 10,
          href: 42,
        }],
      });
    }
    return response({
      ok: true,
      board: {
        boardId: "compact",
        displayName: "Compact",
        holdCount: 10,
        imageUrl: "/api/boards/compact/image",
        saveUrl: 42,
        document: editorDocument(),
      },
    });
  });
  const client = createWorkbenchClient(runtime);

  await assert.rejects(client.listBoards(), /invalid board list/);
  await assert.rejects(client.getBoard("compact"), /invalid board/);
});

test("the browser client rejects invalid optional hold-region fields", async (context) => {
  const invalidRegions: Array<{ name: string; region: unknown }> = [
    {
      name: "id",
      region: { id: "1", key: "hold-1", displayPath: "M 1 1 L 2 1 L 2 2 Z" },
    },
    {
      name: "type",
      region: { type: 42, key: "hold-1", displayPath: "M 1 1 L 2 1 L 2 2 Z" },
    },
    {
      name: "metadata",
      region: { metadata: "invalid", key: "hold-1", displayPath: "M 1 1 L 2 1 L 2 2 Z" },
    },
    {
      name: "metadata holdID",
      region: {
        metadata: { holdID: 42, pieceIndex: 0 },
        key: "hold-1",
        displayPath: "M 1 1 L 2 1 L 2 2 Z",
      },
    },
    {
      name: "metadata pieceIndex",
      region: {
        metadata: { holdID: "hold-1", pieceIndex: "0" },
        key: "hold-1",
        displayPath: "M 1 1 L 2 1 L 2 2 Z",
      },
    },
    {
      name: "bendable command indexes",
      region: {
        bendableCommandIndexes: [1, 1],
        key: "hold-1",
        displayPath: "M 1 1 L 2 1 L 2 2 Z",
      },
    },
  ];

  for (const fixture of invalidRegions) {
    await context.test(fixture.name, async () => {
      const { runtime } = runtimeFixture(async () => response({
        ok: true,
        board: {
          boardId: "compact",
          displayName: "Compact",
          holdCount: 1,
          imageUrl: "/api/boards/compact/image",
          document: {
            canvas: { width: 100, height: 50 },
            regions: [fixture.region],
          },
        },
      }));
      const client = createWorkbenchClient(runtime);

      await assert.rejects(client.getBoard("compact"), /invalid board/);
    });
  }
});

test("the browser client preserves a fractional fixed depth", async () => {
  const document = editorDocument([{
    key: "hold-1-piece-0",
    displayPath: "M 1 1 L 20 1 L 20 20 Z",
    metadata: { holdID: "hold-1", pieceIndex: 0 },
    sizeMillimeters: 7.25,
  }]);
  const { runtime } = runtimeFixture(async () => response({
    ok: true,
    board: boardFixture({ holdCount: 1, document }),
  }));

  const board = await createWorkbenchClient(runtime).getBoard("compact");

  assert.equal(board.document.regions[0]?.sizeMillimeters, 7.25);
});

test("the browser client preserves valid sloper metadata", async () => {
  const document = editorDocument([{
    key: "hold-1-piece-0",
    type: "sloper",
    displayPath: "M 1 1 L 20 1 L 20 20 Z",
    metadata: { holdID: "hold-1", pieceIndex: 0 },
    sloper: { type: "flat", angleDegrees: 20 },
  }]);
  const { runtime } = runtimeFixture(async () => response({
    ok: true,
    board: boardFixture({ holdCount: 1, document }),
  }));

  const board = await createWorkbenchClient(runtime).getBoard("compact");

  assert.deepEqual(board.document.regions[0]?.sloper, {
    type: "flat",
    angleDegrees: 20,
  });
});

test("the browser client rejects invalid sloper metadata", async (context) => {
  for (const fixture of [
    { name: "metadata on a jug", type: "jug", sloper: { type: "flat" } },
    { name: "round angle", type: "sloper", sloper: { type: "round", angleDegrees: 20 } },
    { name: "out-of-range angle", type: "sloper", sloper: { type: "flat", angleDegrees: 90.01 } },
    { name: "unknown metadata key", type: "sloper", sloper: { type: "flat", unexpected: true } },
  ]) {
    await context.test(fixture.name, async () => {
      const { name: _name, ...regionFields } = fixture;
      const { runtime } = runtimeFixture(async () => response({
        ok: true,
        board: boardFixture({
          holdCount: 1,
          document: {
            canvas: { width: 100, height: 50 },
            regions: [{
              key: "hold-1-piece-0",
              displayPath: "M 1 1 L 20 1 L 20 20 Z",
              metadata: { holdID: "hold-1", pieceIndex: 0 },
              ...regionFields,
            }],
          } as EditorDocument,
        }),
      }));

      await assert.rejects(
        createWorkbenchClient(runtime).getBoard("compact"),
        /invalid board/,
      );
    });
  }
});

test("the browser client rejects invalid or ambiguous fixed-depth payloads", async (context) => {
  const invalidRegionSets: Array<{ name: string; regions: unknown[] }> = [
    {
      name: "zero fixed depth",
      regions: [{
        key: "hold-1-piece-0",
        displayPath: "M 1 1 L 20 1 L 20 20 Z",
        metadata: { holdID: "hold-1", pieceIndex: 0 },
        sizeMillimeters: 0,
      }],
    },
    {
      name: "non-finite fixed depth",
      regions: [{
        key: "hold-1-piece-0",
        displayPath: "M 1 1 L 20 1 L 20 20 Z",
        metadata: { holdID: "hold-1", pieceIndex: 0 },
        sizeMillimeters: Number.POSITIVE_INFINITY,
      }],
    },
    {
      name: "fixed and variable depth",
      regions: [{
        key: "hold-1-piece-0",
        displayPath: "M 1 1 L 20 1 L 20 20 Z",
        metadata: { holdID: "hold-1", pieceIndex: 0 },
        sizeMillimeters: 8.5,
        depthRangeMillimeters: { lowerBound: 7.5, upperBound: 12.5 },
      }],
    },
    {
      name: "different sibling fixed depths",
      regions: [
        {
          key: "hold-1-piece-0",
          displayPath: "M 1 1 L 20 1 L 20 20 Z",
          metadata: { holdID: "hold-1", pieceIndex: 0 },
          sizeMillimeters: 8.5,
        },
        {
          key: "hold-1-piece-1",
          displayPath: "M 30 1 L 40 1 L 40 20 Z",
          metadata: { holdID: "hold-1", pieceIndex: 1 },
          sizeMillimeters: 9.5,
        },
      ],
    },
    {
      name: "mixed sibling depth representations",
      regions: [
        {
          key: "hold-1-piece-0",
          displayPath: "M 1 1 L 20 1 L 20 20 Z",
          metadata: { holdID: "hold-1", pieceIndex: 0 },
          sizeMillimeters: 8.5,
        },
        {
          key: "hold-1-piece-1",
          displayPath: "M 30 1 L 40 1 L 40 20 Z",
          metadata: { holdID: "hold-1", pieceIndex: 1 },
          depthRangeMillimeters: { lowerBound: 7.5, upperBound: 12.5 },
        },
      ],
    },
  ];

  for (const fixture of invalidRegionSets) {
    await context.test(fixture.name, async () => {
      const { runtime } = runtimeFixture(async () => response({
        ok: true,
        board: boardFixture({
          holdCount: fixture.regions.length,
          document: {
            canvas: { width: 100, height: 50 },
            regions: fixture.regions,
          } as EditorDocument,
        }),
      }));

      await assert.rejects(
        createWorkbenchClient(runtime).getBoard("compact"),
        /invalid board/,
      );
    });
  }
});

test("the browser client navigates to login when an API request is unauthenticated", async () => {
  const { runtime, assignedUrls } = runtimeFixture(async () => response(
    { ok: false, error: "authentication required", login_url: "/auth/login" },
    { ok: false, status: 401 },
  ));
  const client = createWorkbenchClient(runtime);

  await assert.rejects(client.getGitStatus(), /authentication required/);

  assert.deepEqual(assignedUrls, ["/auth/login"]);
});

test("the browser client preserves an auth-status API failure", async () => {
  const { runtime } = runtimeFixture(async () => response(
    { ok: false, error: "Authentication service is unavailable" },
    { ok: false, status: 503 },
  ));

  await assert.rejects(
    createWorkbenchClient(runtime).getAuthStatus(),
    /Authentication service is unavailable/,
  );
});

test("the browser client keeps the current tab on an unauthenticated save and exposes the login URL", async () => {
  let requestOptions: RequestInit | undefined;
  const { runtime, assignedUrls } = runtimeFixture(async (_input, options) => {
    requestOptions = options;
    return response(
      {
        ok: false,
        error: "GitHub authentication expired or insufficient permissions",
        login_url: "/auth/login",
      },
      { ok: false, status: 401 },
    );
  });
  const client = createWorkbenchClient(runtime);

  await assert.rejects(
    client.saveBoard("compact", editorDocument()),
    (error: unknown) => error instanceof Error
      && error.message === "GitHub authentication expired or insufficient permissions"
      && (error as Error & { loginUrl?: unknown }).loginUrl === "/auth/login",
  );

  assert.deepEqual(assignedUrls, []);
  assert.equal(Object.hasOwn(requestOptions ?? {}, "redirectOnUnauthorized"), false);
});

test("the browser client saves one direct editor document with PUT", async () => {
  const calls: Array<{ request: string; options: RequestInit | undefined }> = [];
  const document = editorDocument();
  const { runtime } = runtimeFixture(async (input, options) => {
    calls.push({ request: String(input), options });
    return response({ ok: true, board: boardFixture({ document }) });
  });
  const client = createWorkbenchClient(runtime);

  await client.saveBoard("compact", document);

  assert.equal(calls[0]?.request, "/api/boards/compact");
  assert.equal(calls[0]?.options?.method, "PUT");
  assert.deepEqual(JSON.parse(String(calls[0]?.options?.body)), document);
});

test("the browser client can read git status and run git operations", async () => {
  const calls: Array<{ request: string; options: RequestInit | undefined }> = [];
  const { runtime } = runtimeFixture(async (input, options) => {
    const request = String(input);
    calls.push({ request, options });
    if (request === "/api/git/status") {
      return response({
        ok: true,
        currentBranch: "main",
        branches: ["main", "feature"],
        dirty: false,
      });
    }
    if (request === "/api/git/checkout") {
      return response({ ok: true, branch: "feature" });
    }
    if (request === "/api/git/commit") {
      return response({
        ok: true,
        commit: "a".repeat(40),
        branch: "main",
        message: "Update board",
      });
    }
    if (request === "/api/git/push") {
      return response({ ok: true, branch: "main", remote: "origin" });
    }
    if (request === "/api/git/open-pr") {
      return response({ ok: true, branch: "main", url: "https://example.com/pull/1" });
    }
    throw new Error(`unexpected endpoint ${request}`);
  });
  const client = createWorkbenchClient(runtime);

  assert.deepEqual(await client.getGitStatus(), {
    ok: true,
    currentBranch: "main",
    branches: ["main", "feature"],
    dirty: false,
    statusLines: [],
  });
  assert.equal((await client.listBranches()).branches.join(","), "main,feature");
  assert.equal(await client.switchBranch("feature"), "feature");
  assert.equal(await client.createBranch("feature"), "feature");
  assert.deepEqual(JSON.parse(String(calls.at(-1)?.options?.body)), {
    branch: "feature",
    create: true,
  });
  assert.equal((await client.commitBoardChanges("Update board")).commit, "a".repeat(40));
  assert.equal((await client.pushBranch()).remote, "origin");
  assert.equal((await client.openPullRequest({
    title: "Update board",
    body: "",
    base: "main",
  })).url, "https://example.com/pull/1");
  assert.equal(calls.length, 7);
});

test("getGitStatus falls back to an empty statusLines array for null or non-array values", async () => {
  let statusLines: unknown = null;
  const { runtime } = runtimeFixture(async (input) => {
    if (String(input) === "/api/git/status") {
      return response({
        ok: true,
        currentBranch: "main",
        branches: ["main"],
        dirty: true,
        statusLines,
      });
    }
    throw new Error(`unexpected endpoint ${String(input)}`);
  });
  const client = createWorkbenchClient(runtime);

  assert.deepEqual(await client.getGitStatus(), {
    ok: true,
    currentBranch: "main",
    branches: ["main"],
    dirty: true,
    statusLines: [],
  });

  statusLines = "not an array";
  assert.deepEqual(await client.getGitStatus(), {
    ok: true,
    currentBranch: "main",
    branches: ["main"],
    dirty: true,
    statusLines: [],
  });
});

test("native diagnostic failures do not replace the useful request error", async () => {
  const { runtime } = runtimeFixture(async () => {
    throw new Error("connection refused");
  });
  runtime.postDiagnostic = (): void => {
    throw new Error("native bridge failed");
  };
  const client = createWorkbenchClient(runtime);

  await assert.rejects(
    client.listBoards(),
    /Could not reach the Hangboard Workbench backend for \/api\/boards: connection refused/,
  );
});

test("native diagnostics ignore malformed browser bridge shapes", () => {
  const diagnostic = { path: "/api/boards", category: "network", message: "unavailable" };
  const messages: unknown[] = [];

  postNativeDiagnostic({ webkit: { messageHandlers: { workbenchDiagnostics: {} } } }, diagnostic);
  postNativeDiagnostic({ webkit: { messageHandlers: { workbenchDiagnostics: { postMessage: "nope" } } } }, diagnostic);
  postNativeDiagnostic({
    webkit: { messageHandlers: { workbenchDiagnostics: { postMessage: (message: unknown) => messages.push(message) } } },
  }, diagnostic);

  assert.deepEqual(messages, [diagnostic]);
});

test("direct board loading commits image and holds together and preserves the prior editor on failure", async () => {
  interface LoadedImage {
    href: string;
    naturalWidth: number;
    naturalHeight: number;
  }

  const candidate = boardFixture({
    holdCount: 1,
    document: editorDocument([
      { key: "hold-1", displayPath: "M 1 1 L 2 1 L 2 2 Z" },
    ]),
  });
  const committed: Array<LoadedBoard<LoadedImage>> = [];
  const success = await loadBoardAtomically({
    boardId: "compact",
    getBoard: async () => candidate,
    loadImage: async (href) => ({ href, naturalWidth: 100, naturalHeight: 50 }),
    commit: (value) => committed.push(value),
  });
  assert.equal(success.board.boardId, "compact");
  assert.equal(committed.length, 1);

  await assert.rejects(
    loadBoardAtomically({
      boardId: "broken",
      getBoard: async () => boardFixture({
        ...candidate,
        boardId: "broken",
        imageUrl: "/api/boards/broken/image",
      }),
      loadImage: async () => { throw new Error("Image unavailable"); },
      commit: (value) => committed.push(value),
    }),
    /Image unavailable/,
  );
  assert.deepEqual(committed, [success]);
});

test("direct board loading uses a matching preloaded image promise", async () => {
  const candidate = boardFixture({
    document: editorDocument([
      { key: "hold-1", displayPath: "M 1 1 L 2 1 L 2 2 Z" },
    ]),
  });
  const image = { href: candidate.imageUrl, naturalWidth: 100, naturalHeight: 50 };

  const loaded = await loadBoardAtomically({
    boardId: candidate.boardId,
    getBoard: async () => candidate,
    loadImage: async () => { throw new Error("Image loader should not run"); },
    preloadedImage: { href: candidate.imageUrl, promise: Promise.resolve(image) },
    commit() {},
  });

  assert.equal(loaded.image, image);
});

test("direct board loading ignores a preloaded image from a different URL", async () => {
  const candidate = boardFixture({
    document: editorDocument([
      { key: "hold-1", displayPath: "M 1 1 L 2 1 L 2 2 Z" },
    ]),
  });
  const expectedImage = { href: candidate.imageUrl, naturalWidth: 100, naturalHeight: 50 };

  const loaded = await loadBoardAtomically({
    boardId: candidate.boardId,
    getBoard: async () => candidate,
    loadImage: async () => expectedImage,
    preloadedImage: {
      href: "/api/boards/previous/image",
      promise: Promise.resolve({ href: "/api/boards/previous/image" }),
    },
    commit() {},
  });

  assert.equal(loaded.image, expectedImage);
});

test("direct board loading rejects malformed shape constraints before image loading or commit", async () => {
  const malformedConstraints: unknown[] = [
    { shape: "rectangle", rotationDegrees: 180 },
    { shape: "rectangle", rotationDegrees: -181 },
    { shape: "rounded-rectangle", rotationDegrees: 0 },
    { shape: "rectangle", rotationDegrees: true },
    { shape: "rectangle", rotationDegrees: "0" },
    { shape: "rectangle", rotationDegrees: Number.NaN },
    { shape: "rectangle", rotationDegrees: Number.POSITIVE_INFINITY },
    { shape: "rectangle" },
    { shape: "rectangle", rotationDegrees: 0, legacyShape: "oval" },
    null,
  ];

  for (const shapeConstraint of malformedConstraints) {
    let imageLoads = 0;
    let commits = 0;
    await assert.rejects(
      loadBoardAtomically({
        boardId: "broken",
        getBoard: async () => ({
          boardId: "broken",
          displayName: "Broken",
          holdCount: 1,
          imageUrl: "/api/boards/broken/image",
          document: {
            canvas: { width: 100, height: 50 },
            regions: [{
              key: "hold-1",
              displayPath: "M 1 1 L 20 1 L 20 20 Z",
              shapeConstraint,
            }],
          } as EditorDocument,
        }),
        loadImage: async () => { imageLoads += 1; return {}; },
        commit: () => { commits += 1; },
      }),
      /shape constraint/i,
      JSON.stringify(shapeConstraint),
    );
    assert.equal(imageLoads, 0, JSON.stringify(shapeConstraint));
    assert.equal(commits, 0, JSON.stringify(shapeConstraint));
  }
});

test("the direct editor model rejects duplicate and open hold paths before saving", () => {
  const base = { canvas: { width: 100, height: 50 } };
  assert.throws(() => validateEditorDocument({ ...base, regions: [
    { key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20 Z" },
    { key: "hold-1", displayPath: "M 30 1 L 40 1 L 40 20 Z" },
  ] }), /unique hold key/);
  assert.throws(() => validateEditorDocument({ ...base, regions: [
    { key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20" },
  ] }), /one closed contour/);
});

test("the direct editor model rejects the removed schema version field", () => {
  assert.throws(
    () => validateEditorDocument({
      schemaVersion: 1,
      canvas: { width: 100, height: 50 },
      regions: [{ key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20 Z" }],
    }),
    /unknown.*schemaVersion/i,
  );
});

test("the direct editor model rejects invalid optional hold-region fields", () => {
  const invalidRegions: unknown[] = [
    { id: "1", key: "hold-1", displayPath: "M 1 1 L 2 1 L 2 2 Z" },
    { type: 42, key: "hold-1", displayPath: "M 1 1 L 2 1 L 2 2 Z" },
    { metadata: "invalid", key: "hold-1", displayPath: "M 1 1 L 2 1 L 2 2 Z" },
    {
      metadata: { holdID: 42, pieceIndex: 0 },
      key: "hold-1",
      displayPath: "M 1 1 L 2 1 L 2 2 Z",
    },
    {
      metadata: { holdID: "hold-1", pieceIndex: "0" },
      key: "hold-1",
      displayPath: "M 1 1 L 2 1 L 2 2 Z",
    },
    {
      bendableCommandIndexes: [-1],
      key: "hold-1",
      displayPath: "M 1 1 L 2 1 L 2 2 Z",
    },
  ];

  for (const region of invalidRegions) {
    assert.throws(
      () => validateEditorDocument({
        canvas: { width: 100, height: 50 },
        regions: [region],
      }),
      /valid hold fields/,
    );
  }
});

test("the direct editor model rejects malformed gaston pair identifiers before saving", () => {
  assert.throws(
    () => validateEditorDocumentForSave(editorDocument([
      {
        key: "left-piece-0",
        type: "gaston",
        pairedHoldID: "not an identifier",
        displayPath: "M 1 1 L 20 1 L 20 20 Z",
        metadata: { holdID: "left", pieceIndex: 0 },
      },
      {
        key: "right-piece-0",
        type: "gaston",
        pairedHoldID: "left",
        displayPath: "M 30 1 L 40 1 L 40 20 Z",
        metadata: { holdID: "right", pieceIndex: 0 },
      },
    ])),
    /paired gaston hold ID must be identifier-shaped/i,
  );
});

test("the editor document clones and validates bendable curve command indexes", () => {
  const document = editorDocument([{
    key: "hold-1",
    displayPath: "M 1 1 C 5 1 15 1 20 1 L 20 20 Z",
    bendableCommandIndexes: [1],
  }]);

  assert.doesNotThrow(() => validateEditorDocument(document));
  const cloned = cloneEditorDocument(document);
  cloned.regions[0]?.bendableCommandIndexes?.push(2);

  assert.deepEqual(document.regions[0]?.bendableCommandIndexes, [1]);
  assert.deepEqual(cloned.regions[0]?.bendableCommandIndexes, [1, 2]);
  for (const indexes of [[1, 1], [-1], [1.5]]) {
    assert.throws(
      () => validateEditorDocument(editorDocument([{
        key: "hold-1",
        displayPath: "M 1 1 L 2 1 L 2 2 Z",
        bendableCommandIndexes: indexes,
      }])),
      /valid hold fields/,
    );
  }
});

test("the direct editor model validates and deeply clones sloper metadata", () => {
  const document = editorDocument([{
    key: "hold-1-piece-0",
    type: "sloper",
    displayPath: "M 1 1 L 20 1 L 20 20 Z",
    metadata: { holdID: "hold-1", pieceIndex: 0 },
    sloper: { type: "flat", angleDegrees: 20 },
  }]);

  assert.doesNotThrow(() => validateEditorDocument(document));
  const cloned = cloneEditorDocument(document);
  if (cloned.regions[0]?.sloper?.type === "flat") {
    cloned.regions[0].sloper.angleDegrees = 30;
  }

  assert.deepEqual(document.regions[0]?.sloper, {
    type: "flat",
    angleDegrees: 20,
  });
});

test("the direct editor model rejects invalid and inconsistent sloper metadata", () => {
  const fixtures: Array<{ type?: string; sloper: unknown }> = [
    { type: "jug", sloper: { type: "flat" } },
    { type: "sloper", sloper: { type: "round", angleDegrees: 20 } },
    { type: "sloper", sloper: { type: "flat", angleDegrees: -0.01 } },
    { type: "sloper", sloper: { type: "flat", angleDegrees: Number.POSITIVE_INFINITY } },
    { type: "sloper", sloper: { type: "domed" } },
    { type: "sloper", sloper: { type: "flat", unexpected: true } },
  ];
  for (const fixture of fixtures) {
    assert.throws(
      () => validateEditorDocument(editorDocument([{
        key: "hold-1-piece-0",
        displayPath: "M 1 1 L 20 1 L 20 20 Z",
        metadata: { holdID: "hold-1", pieceIndex: 0 },
        ...fixture,
      }] as EditorDocument["regions"])),
      /sloper|valid hold fields/i,
    );
  }

  assert.throws(
    () => validateEditorDocument(editorDocument([
      {
        key: "hold-1-piece-0",
        type: "sloper",
        displayPath: "M 1 1 L 20 1 L 20 20 Z",
        metadata: { holdID: "hold-1", pieceIndex: 0 },
        sloper: { type: "flat", angleDegrees: 20 },
      },
      {
        key: "hold-1-piece-1",
        type: "sloper",
        displayPath: "M 30 1 L 40 1 L 40 20 Z",
        metadata: { holdID: "hold-1", pieceIndex: 1 },
        sloper: { type: "round" },
      },
    ])),
    /sloper/i,
  );
});

test("the direct editor model rejects inconsistent finger capacities for one physical hold", () => {
  assert.throws(
    () => validateEditorDocument({
      canvas: { width: 100, height: 50 },
      regions: [
        {
          key: "hold-1-piece-0",
          displayPath: "M 1 1 L 20 1 L 20 20 Z",
          metadata: { holdID: "hold-1", pieceIndex: 0 },
          fingerCapacity: 2,
        },
        {
          key: "hold-1-piece-1",
          displayPath: "M 30 1 L 40 1 L 40 20 Z",
          metadata: { holdID: "hold-1", pieceIndex: 1 },
          fingerCapacity: 3,
        },
      ],
    }),
    /finger capacity/i,
  );
});

test("the direct editor model accepts positive finite fractional depth ranges", () => {
  assert.doesNotThrow(() => validateEditorDocument({
    canvas: { width: 100, height: 50 },
    regions: [{
      key: "hold-1-piece-0",
      displayPath: "M 1 1 L 20 1 L 20 20 Z",
      metadata: { holdID: "hold-1", pieceIndex: 0 },
      depthRangeMillimeters: { lowerBound: 7.5, upperBound: 12.5 },
    }],
  }));
});

test("the direct editor model accepts positive finite fractional fixed depth", () => {
  assert.doesNotThrow(() => validateEditorDocument({
    canvas: { width: 100, height: 50 },
    regions: [{
      key: "hold-1-piece-0",
      displayPath: "M 1 1 L 20 1 L 20 20 Z",
      metadata: { holdID: "hold-1", pieceIndex: 0 },
      sizeMillimeters: 7.25,
    }],
  }));
});

test("the direct editor model rejects invalid or ambiguous fixed depth", () => {
  for (const region of [
    { sizeMillimeters: 0 },
    { sizeMillimeters: -1 },
    { sizeMillimeters: Number.NaN },
    { sizeMillimeters: Number.POSITIVE_INFINITY },
    { sizeMillimeters: "7.5" },
    {
      sizeMillimeters: 8.5,
      depthRangeMillimeters: { lowerBound: 7.5, upperBound: 12.5 },
    },
  ]) {
    assert.throws(
      () => validateEditorDocument(editorDocument([{
        key: "hold-1-piece-0",
        displayPath: "M 1 1 L 20 1 L 20 20 Z",
        metadata: { holdID: "hold-1", pieceIndex: 0 },
        ...region,
      }] as EditorDocument["regions"])),
      /fixed depth|depth representation/i,
    );
  }
});

test("the direct editor model rejects inconsistent sibling fixed-depth representation", () => {
  for (const secondPiece of [
    { sizeMillimeters: 9.5 },
    { depthRangeMillimeters: { lowerBound: 7.5, upperBound: 12.5 } },
    {},
  ]) {
    assert.throws(
      () => validateEditorDocument(editorDocument([
        {
          key: "hold-1-piece-0",
          displayPath: "M 1 1 L 20 1 L 20 20 Z",
          metadata: { holdID: "hold-1", pieceIndex: 0 },
          sizeMillimeters: 8.5,
        },
        {
          key: "hold-1-piece-1",
          displayPath: "M 30 1 L 40 1 L 40 20 Z",
          metadata: { holdID: "hold-1", pieceIndex: 1 },
          ...secondPiece,
        },
      ])),
      /fixed depth|depth representation/i,
    );
  }
});

test("the direct editor model rejects malformed, non-finite, and unordered depth ranges", () => {
  for (const depthRangeMillimeters of [
    {},
    { lowerBound: 7.5 },
    { lowerBound: Number.NaN, upperBound: 12.5 },
    { lowerBound: 12.5, upperBound: Number.POSITIVE_INFINITY },
    { lowerBound: 12.5, upperBound: 7.5 },
  ]) {
    assert.throws(
      () => validateEditorDocument({
        canvas: { width: 100, height: 50 },
        regions: [{
          key: "hold-1-piece-0",
          displayPath: "M 1 1 L 20 1 L 20 20 Z",
          metadata: { holdID: "hold-1", pieceIndex: 0 },
          depthRangeMillimeters,
        }],
      }),
      /depth range/i,
    );
  }
});

test("the direct editor model rejects invalid and inconsistent hand capacities", () => {
  assert.throws(
    () => validateEditorDocument({
      canvas: { width: 100, height: 50 },
      regions: [{
        key: "hold-1-piece-0",
        displayPath: "M 1 1 L 20 1 L 20 20 Z",
        metadata: { holdID: "hold-1", pieceIndex: 0 },
        handCapacity: 3,
      }],
    }),
    /hand capacity/i,
  );

  assert.throws(
    () => validateEditorDocument({
      canvas: { width: 100, height: 50 },
      regions: [
        {
          key: "hold-1-piece-0",
          displayPath: "M 1 1 L 20 1 L 20 20 Z",
          metadata: { holdID: "hold-1", pieceIndex: 0 },
          handCapacity: 1,
        },
        {
          key: "hold-1-piece-1",
          displayPath: "M 30 1 L 40 1 L 40 20 Z",
          metadata: { holdID: "hold-1", pieceIndex: 1 },
          handCapacity: 2,
        },
      ],
    }),
    /hand capacity/i,
  );
});

test("a rejected save keeps the editor document untouched", async () => {
  const document = editorDocument([
    { key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20 Z" },
  ]);
  let commits = 0;
  await assert.rejects(
    saveBoardAtomically({
      boardId: "compact",
      document,
      save: async () => { throw new Error("Hold path crosses itself"); },
      commit: () => { commits += 1; },
    }),
    /Hold path crosses itself/,
  );
  assert.equal(commits, 0);
  assert.equal(document.regions[0]?.displayPath, "M 1 1 L 20 1 L 20 20 Z");
});

test("board operations serialize out-of-order selections", async () => {
  const busyStates: boolean[] = [];
  const coordinator = createBoardOperationCoordinator({
    onBusyChange: (busy) => busyStates.push(busy),
  });
  let resolveFirst: (() => void) | undefined;
  const commits: string[] = [];

  const first = coordinator.perform(async ({ isCurrent }) => {
    await new Promise<void>((resolve) => { resolveFirst = resolve; });
    if (isCurrent()) commits.push("first");
  });
  const second = await coordinator.perform(async ({ isCurrent }) => {
    if (isCurrent()) commits.push("second");
  });

  assert.deepEqual(second, { started: false, value: undefined });
  assert.deepEqual(busyStates, [true]);
  assert.ok(resolveFirst);
  resolveFirst();
  assert.deepEqual(await first, { started: true, value: undefined });
  assert.deepEqual(commits, ["first"]);
  assert.deepEqual(busyStates, [true, false]);
});

test("a pending save cannot overwrite a board selected after the operation changes", async () => {
  const coordinator = createBoardOperationCoordinator();
  const editor = { boardId: "board-a", document: { regions: [{ key: "a" }] } };
  let resolveSave: (() => void) | undefined;
  const pendingSave = coordinator.perform(async ({ isCurrent }) => {
    await new Promise<void>((resolve) => { resolveSave = resolve; });
    if (isCurrent() && editor.boardId === "board-a") {
      editor.document = { regions: [{ key: "saved-a" }] };
    }
  });

  editor.boardId = "board-b";
  editor.document = { regions: [{ key: "edited-b" }] };
  assert.ok(resolveSave);
  resolveSave();
  await pendingSave;

  assert.equal(editor.boardId, "board-b");
  assert.deepEqual(editor.document, { regions: [{ key: "edited-b" }] });
});

const dialogsFixture: Dialogs = {
  confirm: (_message) => true,
  prompt: (_message, _defaultValue) => null,
};
const pathEditorFixture: PathEditor = pathEditor;
const controllerFixture: WorkbenchController = {
  validateEditorDocument,
  validateEditorDocumentForSave,
  loadBoardAtomically,
  saveBoardAtomically,
  createBoardOperationCoordinator,
};
const composedRuntime = runtimeFixture(async () => response({ ok: true, boards: [] })).runtime;
const dependencyFixture: WorkbenchDependencies = {
  client: createWorkbenchClient(composedRuntime),
  controller: controllerFixture,
  pathEditor: pathEditorFixture,
  runtime: composedRuntime,
  dialogs: dialogsFixture,
};
void dependencyFixture;
