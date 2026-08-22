import assert from "node:assert/strict";
import test from "node:test";

import {
  createBoardOperationCoordinator,
  loadBoardAtomically,
  saveBoardAtomically,
  validateEditorDocument,
} from "../src/workbench-controller.ts";
import { createWorkbenchClient } from "../src/workbench-client.ts";
import { postNativeDiagnostic } from "../src/native-bridge.ts";
import * as pathEditor from "../src/path-editor.ts";
import type {
  Board,
  BrowserRuntime,
  Dialogs,
  EditorDocument,
  LoadedBoard,
  PathEditor,
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
  return { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions };
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
      imageUrl: "/api/boards/compact/image",
    },
  ]);
  assert.equal((await client.getBoard("compact")).boardId, "compact");
  assert.deepEqual(calls, ["/api/boards", "/api/boards/compact"]);
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
            schemaVersion: 1,
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
            schemaVersion: 1,
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
  const base = { schemaVersion: 1, canvas: { width: 100, height: 50 } };
  assert.throws(() => validateEditorDocument({ ...base, regions: [
    { key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20 Z" },
    { key: "hold-1", displayPath: "M 30 1 L 40 1 L 40 20 Z" },
  ] }), /unique hold key/);
  assert.throws(() => validateEditorDocument({ ...base, regions: [
    { key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20" },
  ] }), /one closed contour/);
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
  ];

  for (const region of invalidRegions) {
    assert.throws(
      () => validateEditorDocument({
        schemaVersion: 1,
        canvas: { width: 100, height: 50 },
        regions: [region],
      }),
      /valid hold fields/,
    );
  }
});

test("the direct editor model rejects inconsistent finger capacities for one physical hold", () => {
  assert.throws(
    () => validateEditorDocument({
      schemaVersion: 1,
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

test("the direct editor model rejects invalid and inconsistent hand capacities", () => {
  assert.throws(
    () => validateEditorDocument({
      schemaVersion: 1,
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
      schemaVersion: 1,
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
