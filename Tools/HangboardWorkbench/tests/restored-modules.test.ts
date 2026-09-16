import assert from "node:assert/strict";
import test from "node:test";

import {
  createBoardOperationCoordinator,
  loadBoardAtomically,
  saveBoardAtomically,
  validateEditorDocument,
  validateEditorDocumentForSave,
} from "../src/workbench-controller.ts";
import { createWorkbenchClient } from "../src/workbench-client.ts";
import { cloneEditorDocument } from "../src/editor-model.ts";
import { postNativeDiagnostic } from "../src/native-bridge.ts";
import * as pathEditor from "../src/path-editor.ts";
import type {
  Board,
  BrowserRuntime,
  ContactRegion,
  Dialogs,
  EditorDocument,
  LoadedBoard,
  PathEditor,
  PhysicalContact,
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

function contactFixture(id: string, overrides: Partial<Omit<PhysicalContact, "id">> = {}): PhysicalContact {
  return {
    id,
    equipmentObjectID: "primary",
    name: id,
    kind: "jug",
    features: [],
    gripTypes: [],
    ...overrides,
  };
}

function regionFixture(
  id: number,
  key: string,
  displayPath: string,
  contactID: string,
  pieceIndex = 0,
  presentationID = "primary",
  overrides: Partial<Omit<ContactRegion, "id" | "key" | "displayPath" | "metadata">> = {},
): ContactRegion {
  return {
    id,
    key,
    displayPath,
    metadata: { contactID, pieceIndex, presentationID },
    ...overrides,
  };
}

const DEFAULT_CONTACTS = [contactFixture("contact-1")];
const DEFAULT_REGIONS = [regionFixture(1, "contact-1-piece-0", "M 1 1 L 20 1 L 20 20 Z", "contact-1")];

function editorDocument(options: {
  contacts?: readonly PhysicalContact[];
  regions?: readonly ContactRegion[];
  presentationID?: string;
} = {}): EditorDocument {
  const presentationID = options.presentationID ?? "primary";
  const contacts = [...structuredClone(options.contacts ?? DEFAULT_CONTACTS)];
  const regions = [...structuredClone(options.regions ?? DEFAULT_REGIONS)];
  for (const region of regions) {
    if (region.metadata.presentationID !== presentationID) {
      throw new Error(`Region ${region.key} must belong to focused presentation ${presentationID}`);
    }
  }
  return {
    presentationID,
    contacts,
    canvas: { width: 100, height: 50 },
    regions,
  };
}

function boardFixture(overrides: Partial<Board> = {}): Board {
  const document = overrides.document ?? editorDocument();
  return {
    boardId: "compact",
    displayName: "Compact",
    contactCount: document.contacts.length,
    imageUrl: "/api/boards/compact/image",
    document,
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
          contactCount: 10,
          needsAttention: false,
          imageUrl: "/api/boards/compact/image",
        }],
      });
    }
    return response({ ok: true, board: boardFixture({ contactCount: 10 }) });
  });
  const client: WorkbenchClient = createWorkbenchClient(runtime);

  assert.deepEqual(await client.listBoards(), [
    {
      boardId: "compact",
      displayName: "Compact",
      contactCount: 10,
      needsAttention: false,
      imageUrl: "/api/boards/compact/image",
    },
  ]);
  assert.equal((await client.getBoard("compact")).boardId, "compact");
  assert.deepEqual(calls, ["/api/boards", "/api/boards/compact"]);
});

test("the browser client requests and validates a selected presentation", async () => {
  const calls: string[] = [];
  const document = editorDocument({
    presentationID: "back",
    contacts: [contactFixture("back-contact")],
    regions: [regionFixture(1, "back-contact-piece-0", "M 1 1 L 20 1 L 20 20 Z", "back-contact", 0, "back")],
  });
  document.canvas = { width: 80, height: 120 };
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
        document: editorDocument({
          presentationID: "back",
          contacts: [contactFixture("back-contact")],
          regions: [regionFixture(1, "back-contact-piece-0", "M 1 1 L 20 1 L 20 20 Z", "back-contact", 0, "back")],
        }),
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
          contactCount: 10,
          href: 42,
        }],
      });
    }
    return response({
      ok: true,
      board: {
        boardId: "compact",
        displayName: "Compact",
        contactCount: 10,
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

test("the browser client rejects invalid optional contact-region fields", async (context) => {
  const invalidRegionPatches: Array<{ name: string; patch: Record<string, unknown> }> = [
    { name: "id", patch: { id: "1" } },
    { name: "fact field on media", patch: { kind: "jug" } },
    { name: "metadata", patch: { metadata: "invalid" } },
    { name: "metadata contactID", patch: { metadata: { contactID: 42, pieceIndex: 0, presentationID: "primary" } } },
    { name: "metadata pieceIndex", patch: { metadata: { contactID: "contact-1", pieceIndex: "0", presentationID: "primary" } } },
    { name: "bendable command indexes", patch: { bendableCommandIndexes: [1, 1] } },
  ];

  for (const fixture of invalidRegionPatches) {
    await context.test(fixture.name, async () => {
      const document = editorDocument();
      Object.assign(document.regions[0] as object, fixture.patch);
      const { runtime } = runtimeFixture(async () => response({
        ok: true,
        board: boardFixture({ contactCount: 1, document }),
      }));
      const client = createWorkbenchClient(runtime);

      await assert.rejects(client.getBoard("compact"), /invalid board/);
    });
  }
});

test("the browser client preserves an equal-bound factual depth range", async () => {
  const document = editorDocument({
    contacts: [contactFixture("hold-1", { depth: { range: { minimum: 7.25, maximum: 7.25 } } })],
    regions: [regionFixture(1, "hold-1-piece-0", "M 1 1 L 20 1 L 20 20 Z", "hold-1")],
  });
  const { runtime } = runtimeFixture(async () => response({
    ok: true,
    board: boardFixture({ contactCount: 1, document }),
  }));

  const board = await createWorkbenchClient(runtime).getBoard("compact");

  assert.deepEqual(board.document.contacts[0]?.depth, {
    range: { minimum: 7.25, maximum: 7.25 },
  });
});

test("the browser client preserves valid contact kind and raster treatment metadata", async () => {
  const document = editorDocument({
    contacts: [contactFixture("hold-1", { kind: "sloper" })],
    regions: [regionFixture(1, "hold-1-piece-0", "M 1 1 L 20 1 L 20 20 Z", "hold-1", 0, "primary", {
      treatment: { type: "surface" },
    })],
  });
  const { runtime } = runtimeFixture(async () => response({
    ok: true,
    board: boardFixture({ contactCount: 1, document }),
  }));

  const board = await createWorkbenchClient(runtime).getBoard("compact");

  assert.equal(board.document.contacts[0]?.kind, "sloper");
  assert.deepEqual(board.document.regions[0]?.treatment, { type: "surface" });
});

test("the browser client rejects invalid raster treatment metadata", async (context) => {
  for (const fixture of [
    { name: "unknown treatment", treatment: { type: "painted" } },
    { name: "out-of-range rim", treatment: { type: "shelf", rimInsetFraction: 0.75 } },
    { name: "missing recess depth", treatment: { type: "recess", rimInsetFraction: 0.15 } },
    { name: "unknown metadata key", treatment: { type: "surface", unexpected: true } },
  ]) {
    await context.test(fixture.name, async () => {
      const document = editorDocument();
      (document.regions[0] as unknown as { treatment: unknown }).treatment = fixture.treatment;
      const { runtime } = runtimeFixture(async () => response({
        ok: true,
        board: boardFixture({ contactCount: 1, document }),
      }));

      await assert.rejects(
        createWorkbenchClient(runtime).getBoard("compact"),
        /invalid board/,
      );
    });
  }
});

test("the browser client rejects invalid tagged contact depth payloads", async (context) => {
  const invalidRanges: Array<{ name: string; value: unknown }> = [
    { name: "non-finite maximum", value: { range: { minimum: 8, maximum: Number.POSITIVE_INFINITY } } },
    { name: "unordered range", value: { range: { minimum: 12, maximum: 8 } } },
    { name: "unknown range member", value: { range: { minimum: 8, maximum: 12, fixed: true } } },
    { name: "string bounds", value: { range: { minimum: "8", maximum: 12 } } },
    { name: "mixed representations", value: { category: "large", range: { minimum: 25, maximum: 30 } } },
  ];

  for (const fixture of invalidRanges) {
    await context.test(fixture.name, async () => {
      const document = editorDocument();
      (document.contacts[0] as unknown as { depth: unknown }).depth = fixture.value;
      const { runtime } = runtimeFixture(async () => response({
        ok: true,
        board: boardFixture({ contactCount: 1, document }),
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
  assert.ok(requestOptions);
  assert.equal(Object.hasOwn(requestOptions, "redirectOnUnauthorized"), false);
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

test("direct board loading commits image and contacts together and preserves the prior editor on failure", async () => {
  interface LoadedImage {
    href: string;
    naturalWidth: number;
    naturalHeight: number;
  }

  const candidate = boardFixture({
    contactCount: 1,
    document: editorDocument({
      contacts: [contactFixture("hold-1")],
      regions: [regionFixture(1, "hold-1", "M 1 1 L 2 1 L 2 2 Z", "hold-1")],
    }),
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
    document: editorDocument({
      contacts: [contactFixture("hold-1")],
      regions: [regionFixture(1, "hold-1", "M 1 1 L 2 1 L 2 2 Z", "hold-1")],
    }),
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
    document: editorDocument({
      contacts: [contactFixture("hold-1")],
      regions: [regionFixture(1, "hold-1", "M 1 1 L 2 1 L 2 2 Z", "hold-1")],
    }),
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
  for (const shapeConstraint of [
    { shape: "rectangle", rotationDegrees: 180 },
    { shape: "rounded-rectangle", rotationDegrees: 0 },
    { shape: "rectangle", rotationDegrees: Number.POSITIVE_INFINITY },
    { shape: "rectangle" },
    null,
  ]) {
    const document = editorDocument();
    (document.regions[0] as unknown as { shapeConstraint: unknown }).shapeConstraint = shapeConstraint;
    let imageLoads = 0;
    let commits = 0;
    await assert.rejects(loadBoardAtomically({
      boardId: "broken",
      getBoard: async () => boardFixture({ boardId: "broken", document }),
      loadImage: async () => { imageLoads += 1; return {}; },
      commit: () => { commits += 1; },
    }), /valid media regions/i, JSON.stringify(shapeConstraint));
    assert.equal(imageLoads, 0, JSON.stringify(shapeConstraint));
    assert.equal(commits, 0, JSON.stringify(shapeConstraint));
  }
});

test("the direct editor model rejects duplicate and open contact paths before saving", () => {
  const duplicate = editorDocument({
    contacts: DEFAULT_CONTACTS,
    regions: [
      regionFixture(1, "contact-1-piece-0", "M 1 1 L 20 1 L 20 20 Z", "contact-1", 0),
      regionFixture(2, "contact-1-piece-0", "M 30 1 L 40 1 L 40 20 Z", "contact-1", 1),
    ],
  });
  assert.throws(() => validateEditorDocument(duplicate), /region keys must be unique/i);
  const open = editorDocument();
  open.regions[0]!.displayPath = "M 1 1 L 20 1 L 20 20";
  assert.throws(() => validateEditorDocument(open), /valid media regions/i);
});

test("the direct editor model rejects the removed schema version field", () => {
  assert.throws(() => validateEditorDocument({ ...editorDocument(), schemaVersion: 2 }), /document is required/i);
});

test("the direct editor model rejects invalid optional contact-region fields", () => {
  for (const patch of [
    { id: "1" },
    { treatment: { type: "painted" } },
    { metadata: "invalid" },
    { bendableCommandIndexes: [-1] },
    { smoothAnchorIndexes: [1, 1] },
    { unknown: true },
  ]) {
    const document = editorDocument();
    Object.assign(document.regions[0] as object, patch);
    assert.throws(() => validateEditorDocument(document), /valid media regions/i);
  }
});

test("the direct editor model rejects malformed gaston pair identifiers before saving", () => {
  const document = editorDocument();
  Object.assign(document.contacts[0]!, { kind: "gaston", pairedContactID: "not an identifier" });
  assert.throws(() => validateEditorDocumentForSave(document), /valid factual contacts/i);
});

test("the editor document clones and validates bendable curve command indexes", () => {
  const document = editorDocument({
    contacts: DEFAULT_CONTACTS,
    regions: [regionFixture(1, "contact-1-piece-0", "M 1 1 C 5 1 15 1 20 1 L 20 20 Z", "contact-1", 0, "primary", {
      bendableCommandIndexes: [1],
    })],
  });
  assert.doesNotThrow(() => validateEditorDocument(document));
  const cloned = cloneEditorDocument(document);
  cloned.regions[0]?.bendableCommandIndexes?.push(2);
  assert.deepEqual(document.regions[0]?.bendableCommandIndexes, [1]);
  assert.deepEqual(cloned.regions[0]?.bendableCommandIndexes, [1, 2]);
  for (const indexes of [[1, 1], [-1], [1.5]]) {
    const invalid = editorDocument();
    invalid.regions[0]!.bendableCommandIndexes = indexes;
    assert.throws(() => validateEditorDocument(invalid), /valid media regions/i);
  }
});

test("the direct editor model validates and deeply clones raster treatment metadata", () => {
  const document = editorDocument({
    contacts: DEFAULT_CONTACTS,
    regions: [regionFixture(1, "contact-1-piece-0", "M 1 1 L 20 1 L 20 20 Z", "contact-1", 0, "primary", {
      treatment: { type: "shelf", rimInsetFraction: 0.2 },
    })],
  });
  assert.doesNotThrow(() => validateEditorDocument(document));
  const cloned = cloneEditorDocument(document);
  if (cloned.regions[0]?.treatment?.type === "shelf") cloned.regions[0].treatment.rimInsetFraction = 0.3;
  assert.deepEqual(document.regions[0]?.treatment, { type: "shelf", rimInsetFraction: 0.2 });
});

test("the direct editor model rejects invalid raster treatment metadata", () => {
  for (const treatment of [
    { type: "painted" },
    { type: "surface", extra: true },
    { type: "shelf", rimInsetFraction: -0.1 },
    { type: "recess", rimInsetFraction: 0.1 },
  ]) {
    const document = editorDocument();
    (document.regions[0] as unknown as { treatment: unknown }).treatment = treatment;
    assert.throws(() => validateEditorDocument(document), /valid media regions/i);
  }
});

test("the direct editor model rejects invalid factual finger capacities", () => {
  for (const fingerCapacity of [0, 5, 1.5, Number.POSITIVE_INFINITY]) {
    const document = editorDocument();
    document.contacts[0]!.fingerCapacity = fingerCapacity;
    assert.throws(() => validateEditorDocument(document), /valid factual contacts/i);
  }
});

test("the direct editor model accepts finite fractional measured depths", () => {
  const document = editorDocument();
  document.contacts[0]!.depth = { range: { minimum: 7.5, maximum: 12.5 } };
  assert.doesNotThrow(() => validateEditorDocument(document));
});

test("the direct editor model accepts equal bounds for source-backed fixed depth", () => {
  const document = editorDocument();
  document.contacts[0]!.depth = { range: { minimum: 7.25, maximum: 7.25 } };
  assert.doesNotThrow(() => validateEditorDocument(document));
});

test("the direct editor model accepts zero but rejects negative measured contact depth", () => {
  const zero = editorDocument();
  zero.contacts[0]!.depth = { range: { minimum: 0, maximum: 8 } };
  assert.doesNotThrow(() => validateEditorDocument(zero));
  for (const depth of [
    { range: { minimum: -1, maximum: 8 } },
  ] as unknown[]) {
    const document = editorDocument();
    (document.contacts[0] as unknown as { depth: unknown }).depth = depth;
    assert.throws(() => validateEditorDocument(document), /valid factual contacts/i);
  }
});

test("the direct editor model rejects malformed, non-finite, missing, and reversed tagged depths", () => {
  for (const depth of [
    {},
    { range: { minimum: 8 } },
    { range: { maximum: 8 } },
    { range: { minimum: Number.NaN, maximum: 8 } },
    { range: { minimum: 8, maximum: Number.POSITIVE_INFINITY } },
    { range: { minimum: 12, maximum: 8 } },
    { category: "unexpected" },
  ] as unknown[]) {
    const document = editorDocument();
    (document.contacts[0] as unknown as { depth: unknown }).depth = depth;
    assert.throws(() => validateEditorDocument(document), /valid factual contacts/i);
  }
});

test("contact facts have one owner regardless of how many media pieces reference them", () => {
  const document = editorDocument({
    contacts: [contactFixture("contact-1", { fingerCapacity: 2 })],
    regions: [
      regionFixture(1, "contact-1-piece-0", "M 1 1 L 20 1 L 20 20 Z", "contact-1", 0),
      regionFixture(2, "contact-1-piece-1", "M 30 1 L 40 1 L 40 20 Z", "contact-1", 1),
    ],
  });
  assert.equal(document.contacts.length, 1);
  assert.equal(document.contacts[0]?.fingerCapacity, 2);
  assert.doesNotThrow(() => validateEditorDocument(document));
});

test("the direct editor model rejects dangling contact references and noncontiguous pieces", () => {
  const dangling = editorDocument();
  dangling.regions[0]!.metadata.contactID = "missing-contact";
  assert.throws(() => validateEditorDocument(dangling), /valid media regions/i);
  const noncontiguous = editorDocument();
  noncontiguous.regions[0]!.metadata.pieceIndex = 1;
  assert.throws(() => validateEditorDocument(noncontiguous), /piece indexes must be contiguous/i);
});

test("the direct editor model rejects invalid factual hand capacities", () => {
  for (const handCapacity of [0, 3, 1.5, Number.POSITIVE_INFINITY]) {
    const document = editorDocument();
    document.contacts[0]!.handCapacity = handCapacity;
    assert.throws(() => validateEditorDocument(document), /valid factual contacts/i);
  }
});

test("a rejected save keeps the editor document untouched", async () => {
  const document = editorDocument({
    contacts: [contactFixture("hold-1")],
    regions: [regionFixture(1, "hold-1", "M 1 1 L 20 1 L 20 20 Z", "hold-1")],
  });
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
