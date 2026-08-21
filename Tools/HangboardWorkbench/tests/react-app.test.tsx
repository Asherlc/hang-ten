import assert from "node:assert/strict";
import test from "node:test";
import { useState, type ReactElement } from "react";

import { WorkbenchApp } from "../src/WorkbenchApp.tsx";
import { useWorkbench } from "../src/useWorkbench.ts";
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
  UseWorkbenchResult,
  WorkbenchClient,
  WorkbenchDependencies,
} from "../src/types.ts";
import { renderReact, type ReactHarness } from "./react-harness.tsx";

function deferred<T>(): {
  promise: Promise<T>;
  resolve(value: T): void;
  reject(reason: unknown): void;
} {
  let resolvePromise!: (value: T) => void;
  let rejectPromise!: (reason: unknown) => void;
  return {
    promise: new Promise<T>((resolve, reject) => {
      resolvePromise = resolve;
      rejectPromise = reject;
    }),
    resolve: resolvePromise,
    reject: rejectPromise,
  };
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => { setTimeout(resolve, milliseconds); });
}

function storageFixture(initial: Record<string, string> = {}): Pick<Storage, "getItem" | "setItem"> {
  const values = new Map(Object.entries(initial));
  return {
    getItem(key) {
      return values.get(key) ?? null;
    },
    setItem(key, value) {
      values.set(key, value);
    },
  };
}

function editorDocument(path = "M 1 1 L 20 1 L 20 20 Z"): EditorDocument {
  return {
    schemaVersion: 1,
    canvas: { width: 100, height: 50 },
    regions: [{ key: "hold-1", type: "jug", displayPath: path }],
  };
}

function boardFixture(boardId = "board-a", document = editorDocument()): Board {
  return {
    boardId,
    displayName: boardId === "board-a" ? "Board A" : "Board B",
    holdCount: document.regions.length,
    imageUrl: `/api/boards/${boardId}/image`,
    document,
  };
}

function gitStatus(overrides: Partial<GitStatus> = {}): GitStatus {
  return {
    ok: true,
    currentBranch: "main",
    branches: ["main", "feature"],
    dirty: false,
    statusLines: [],
    ...overrides,
  };
}

interface ImageFixture {
  pending: HTMLImageElement[];
  succeed(): void;
  fail(): void;
}

function imageFixture(): { runtime: BrowserRuntime; images: ImageFixture } {
  const pending: HTMLImageElement[] = [];
  const createImage = (): HTMLImageElement => {
    const image = document.createElement("img");
    let source = "";
    Object.defineProperty(image, "src", {
      configurable: true,
      get: () => source,
      set: (value: string) => {
        source = value;
        pending.push(image);
      },
    });
    return image;
  };
  const runtime: BrowserRuntime = {
    async fetch() {
      throw new Error("fetch is not used by React workflow tests");
    },
    location: { assign() {} },
    confirm() { return true; },
    prompt() { return null; },
    createImage,
  };
  return {
    runtime,
    images: {
      pending,
      succeed() {
        const image = pending.shift();
        if (!image) throw new Error("No pending image load");
        image.onload?.(new Event("load"));
      },
      fail() {
        const image = pending.shift();
        if (!image) throw new Error("No pending image load");
        image.onerror?.(new Event("error"));
      },
    },
  };
}

function clientFixture(overrides: Partial<WorkbenchClient> = {}): WorkbenchClient {
  const board = boardFixture();
  return {
    async listBoards(): Promise<BoardSummary[]> {
      return [{ boardId: board.boardId, displayName: board.displayName, holdCount: board.holdCount }];
    },
    async getBoard(): Promise<Board> { return board; },
    async saveBoard(_boardId, document): Promise<Board> { return { ...board, document }; },
    async getGitStatus(): Promise<GitStatus> { return gitStatus(); },
    async getAuthStatus(): Promise<AuthStatus> {
      return { ok: true, authenticated: false };
    },
    async listBranches(): Promise<GitStatus> { return gitStatus(); },
    async switchBranch(branchName): Promise<string> { return branchName; },
    async createBranch(branchName): Promise<string> { return branchName; },
    async commitBoardChanges(message): Promise<CommitResult> {
      return { ok: true, commit: "abcdef0123456789", branch: "main", message };
    },
    async pushBranch(): Promise<PushResult> {
      return { ok: true, branch: "main", remote: "origin" };
    },
    async openPullRequest(): Promise<PullRequestResult> {
      return { ok: true, branch: "feature", url: "https://example.com/pr/1" };
    },
    ...overrides,
  };
}

function dependenciesFixture(options: {
  client?: Partial<WorkbenchClient>;
  dialogs?: Partial<Dialogs>;
  runtime?: BrowserRuntime;
} = {}): WorkbenchDependencies {
  const image = imageFixture();
  const dialogs: Dialogs = {
    confirm() { return true; },
    prompt() { return null; },
    ...options.dialogs,
  };
  return {
    client: clientFixture(options.client),
    controller,
    pathEditor,
    runtime: options.runtime ?? image.runtime,
    dialogs,
  };
}

async function withApp(
  dependencies: WorkbenchDependencies,
  run: (harness: ReactHarness) => void | Promise<void>,
): Promise<void> {
  const harness = await renderReact(<WorkbenchApp dependencies={dependencies} />);
  try {
    await run(harness);
  } finally {
    await harness.cleanup();
  }
}

function HookProbe({
  dependencies,
  onResult,
}: {
  dependencies: WorkbenchDependencies;
  onResult(result: UseWorkbenchResult): void;
}): ReactElement | null {
  onResult(useWorkbench(dependencies));
  return null;
}

async function withHook(
  dependencies: WorkbenchDependencies,
  run: (result: () => UseWorkbenchResult, harness: ReactHarness) => void | Promise<void>,
): Promise<void> {
  let current: UseWorkbenchResult | undefined;
  const harness = await renderReact(
    <HookProbe dependencies={dependencies} onResult={(result) => { current = result; }} />,
  );
  try {
    await run(() => {
      if (!current) throw new Error("Hook result unavailable");
      return current;
    }, harness);
  } finally {
    await harness.cleanup();
  }
}

test("renderReact restores browser globals when the initial render throws", async () => {
  const originalDocument = globalThis.document;
  function BrokenApp(): ReactElement {
    throw new Error("render failure");
  }

  await assert.rejects(renderReact(<BrokenApp />), /render failure/u);

  assert.equal(globalThis.document, originalDocument);
});

test("the React shell preserves the direct-workbench DOM and renders logged-out auth safely", async () => {
  await withApp(dependenciesFixture({
    client: {
      getAuthStatus() { return new Promise<AuthStatus>(() => {}); },
      async listBoards() { return []; },
    },
  }), async (app) => {
    assert.equal(app.document.querySelectorAll("main.app-shell.direct-workbench").length, 1);
    assert.equal(app.text("h1"), "Hangboard Workbench");
    assert.equal(app.text("#board-status"), "Choose a board to edit its holds.");
    assert.equal(app.text("#git-status"), "Repository status");
    assert.equal(app.text("#save-state"), "No board selected");
    const autosave = app.document.querySelector<HTMLInputElement>("#autosave-toggle");
    assert.equal(autosave?.checked, true);
    assert.equal(app.text("#board-name"), "No board selected");
    assert.equal(app.text("#empty-state"), "Select a boardIts image and holds load together.");
    assert.equal(app.text("#hold-heading"), "No selection");
    assert.equal(app.text("#hold-empty"), "Select a hold to edit its closed contour.");
    const requiredIds = [
      "board-status", "refresh-boards-button", "save-state", "save-button", "git-auth-status",
      "git-status", "git-branch-select", "git-refresh-button", "git-switch-button",
      "git-new-branch-name", "git-new-branch-button", "git-commit-message", "git-commit-button",
      "git-push-button", "git-open-pr-button", "boards-heading", "boards-error", "board-list",
      "board-name", "add-hold-button", "canvas-viewport", "editor-svg", "board-image", "hold-overlay",
      "empty-state", "validation-panel", "validation-list", "editor-status", "hold-heading", "hold-empty",
      "hold-form", "hold-key", "hold-type-select", "rotate-ccw-button", "rotate-cw-button",
      "rotate-by-input", "rotate-by-apply-button", "delete-hold-button",
    ];
    for (const id of requiredIds) assert.ok(app.document.getElementById(id), `missing #${id}`);
    const login = app.document.querySelector<HTMLAnchorElement>("#git-auth-status a");
    assert.equal(login?.textContent, "Log in with GitHub");
    assert.equal(login?.getAttribute("href"), "/auth/login");
  });
});

test("mobile canvas controls open the board drawer, repository sheet, and selected-hold sheet", async () => {
  const image = imageFixture();
  await withApp(dependenciesFixture({ runtime: image.runtime }), async (app) => {
    await app.flush();

    for (const id of [
      "mobile-boards-button", "mobile-menu-button", "mobile-save-button",
      "mobile-zoom-out-button", "mobile-zoom-in-button", "mobile-add-hold-button",
    ]) assert.ok(app.document.getElementById(id), `missing #${id}`);

    await app.click("#mobile-boards-button");
    assert.equal(app.document.querySelector(".workspace-grid")?.classList.contains("mobile-boards-open"), true);
    await app.click("#mobile-menu-button");
    assert.equal(app.document.querySelector(".topbar")?.classList.contains("mobile-menu-open"), true);

    await app.click("#board-list button");
    await app.flush(() => image.images.succeed());
    await app.click("#hold-overlay path");
    assert.equal(app.document.querySelector(".inspector-panel")?.classList.contains("mobile-sheet-open"), true);

    await app.click("#mobile-zoom-in-button");
    assert.equal(app.text("#canvas-zoom-level"), "125%");
    await app.click("#mobile-add-hold-button");
    assert.equal(app.document.querySelectorAll("#hold-overlay path").length, 2);
  });
});

test("collapsing the mobile hold sheet retains the selected hold", async () => {
  const image = imageFixture();
  await withApp(dependenciesFixture({ runtime: image.runtime }), async (app) => {
    await app.flush();
    await app.click("#board-list button");
    await app.flush(() => image.images.succeed());
    await app.click("#hold-overlay path");

    assert.equal(app.document.querySelector(".inspector-panel")?.classList.contains("mobile-sheet-open"), true);
    assert.equal(app.text("#hold-heading"), "hold-1");

    await app.click("#mobile-collapse-hold-sheet-button");

    assert.equal(app.document.querySelector(".inspector-panel")?.classList.contains("mobile-sheet-open"), false);
    assert.equal(app.text("#hold-heading"), "hold-1");
  });
});

test("autosave restores the saved browser preference", async () => {
  const image = imageFixture();
  const storage = storageFixture({ "hangboard-workbench:autosave-enabled": "false" });
  const runtime = { ...image.runtime, storage } as BrowserRuntime;
  await withApp(dependenciesFixture({ runtime }), async (app) => {
    const autosave = app.document.querySelector<HTMLInputElement>("#autosave-toggle");
    assert.equal(autosave?.checked, false);
  });
});

test("changing autosave persists the preference for a future app mount", async () => {
  const image = imageFixture();
  const storage = storageFixture();
  const runtime = { ...image.runtime, storage } as BrowserRuntime;
  const dependencies = dependenciesFixture({ runtime });

  await withApp(dependencies, async (app) => {
    await app.click("#autosave-toggle");
    assert.equal(storage.getItem("hangboard-workbench:autosave-enabled"), "false");
  });

  await withApp(dependencies, async (app) => {
    const autosave = app.document.querySelector<HTMLInputElement>("#autosave-toggle");
    assert.equal(autosave?.checked, false);
  });
});

test("manual board refresh does not masquerade as completed repository initialization", async () => {
  await withApp(dependenciesFixture({
    client: {
      getAuthStatus() { return new Promise<AuthStatus>(() => {}); },
      async listBoards() { return []; },
    },
  }), async (app) => {
    await app.click("#refresh-boards-button");

    assert.equal(app.text("#board-status"), "Choose a board to edit its holds.");
    assert.equal(app.text("#git-status"), "Repository status");
  });
});

test("state-dependent actions observe updates dispatched earlier in the same task", async () => {
  const createdBranches: string[] = [];
  await withHook(dependenciesFixture({
    client: {
      async createBranch(branchName) {
        createdBranches.push(branchName);
        return branchName;
      },
    },
  }), async (result, app) => {
    await app.flush();
    await app.flush(async () => {
      result().actions.setNewBranchName("same-task-branch");
      await result().actions.createBranch();
    });

    assert.deepEqual(createdBranches, ["same-task-branch"]);
  });
});

test("validation renders angle-bracket error text without interpreting an image node", async () => {
  const malicious = '<img src=x onerror="globalThis.pwned=true">';
  await withApp(dependenciesFixture({
    client: {
      async listBoards() { return []; },
      async getGitStatus() { throw new Error(malicious); },
    },
  }), async (app) => {
    await app.flush();
    assert.equal(app.text("#validation-list"), malicious);
    assert.equal(app.document.querySelector("#validation-list img"), null);
  });
});

test("initialization awaits authentication, repository status, then boards", async () => {
  const calls: string[] = [];
  const auth = deferred<AuthStatus>();
  const status = deferred<GitStatus>();
  await withApp(dependenciesFixture({
    client: {
      getAuthStatus() { calls.push("auth"); return auth.promise; },
      getGitStatus() { calls.push("git"); return status.promise; },
      async listBoards() { calls.push("boards"); return []; },
    },
  }), async (app) => {
    assert.deepEqual(calls, ["auth"]);
    await app.flush(() => auth.resolve({ ok: true, authenticated: true, username: "octocat" }));
    assert.deepEqual(calls, ["auth", "git"]);
    assert.equal(app.disabled("#git-refresh-button"), true);
    assert.equal(app.disabled("#git-new-branch-name"), true);
    await app.click("#git-refresh-button");
    assert.deepEqual(calls, ["auth", "git"]);
    await app.flush(() => status.resolve(gitStatus()));
    assert.deepEqual(calls, ["auth", "git", "boards"]);
    assert.equal(app.disabled("#git-refresh-button"), false);
  });
});

test("board selection locks board and Git actions and commits image plus document together", async () => {
  const board = boardFixture();
  const image = imageFixture();
  await withApp(dependenciesFixture({
    runtime: image.runtime,
    client: {
      async listBoards() {
        return [
          { boardId: "board-a", displayName: "Board A", holdCount: 1 },
          { boardId: "board-b", displayName: "Board B", holdCount: 1 },
        ];
      },
      async getBoard() { return board; },
    },
  }), async (app) => {
    await app.flush();
    await app.click("#board-list button");
    assert.equal(app.text("#board-name"), "No board selected");
    for (const selector of [
      "#refresh-boards-button", "#save-button", "#board-list button", "#git-refresh-button",
      "#git-branch-select", "#git-switch-button", "#git-new-branch-name", "#git-new-branch-button",
      "#git-commit-message", "#git-commit-button", "#git-push-button", "#git-open-pr-button",
    ]) assert.equal(app.disabled(selector), true, `${selector} must be locked`);
    assert.equal(image.images.pending.length, 1);
    await app.flush(() => image.images.succeed());
    assert.equal(app.text("#board-name"), "Board A");
    assert.equal(app.document.querySelectorAll("#hold-overlay path").length, 1);
  });
});

test("failed board selection keeps the prior editor and failed save keeps unsaved edits", async () => {
  let getBoardCalls = 0;
  const saved = deferred<Board>();
  const image = imageFixture();
  await withHook(dependenciesFixture({
    runtime: image.runtime,
    client: {
      async getBoard() {
        getBoardCalls += 1;
        if (getBoardCalls === 1) return boardFixture();
        throw new Error("Board B image missing");
      },
      saveBoard() { return saved.promise; },
    },
  }), async (result, harness) => {
    await harness.flush();
    let firstLoad!: Promise<void>;
    await harness.flush(() => { firstLoad = result().actions.selectBoard("board-a"); });
    await harness.flush(async () => {
      image.images.succeed();
      await firstLoad;
    });
    const priorDocument = result().state.document;
    await harness.flush(() => result().actions.selectBoard("board-b"));
    assert.equal(result().state.board?.boardId, "board-a");
    assert.equal(result().state.document, priorDocument);
    assert.match(result().state.status, /current editor was kept/);

    const changed = editorDocument("M 5 5 L 25 5 L 25 25 Z");
    await harness.flush(() => result().actions.updateDocument(changed, "Contour updated."));
    let pendingSave!: Promise<void>;
    await harness.flush(() => { pendingSave = result().actions.saveBoard(); });
    await harness.flush(async () => {
      saved.reject(new Error("save rejected"));
      await pendingSave;
    });
    assert.equal(result().state.document?.regions[0]?.displayPath, "M 5 5 L 25 5 L 25 25 Z");
    assert.equal(result().state.dirty, true);
    assert.match(result().state.status, /editor changes were kept/);
  });
});

test("recoverable save authentication failure keeps edits and offers safe separate-tab login", async () => {
  const image = imageFixture();
  const saveAttempts: EditorDocument[] = [];
  await withApp(dependenciesFixture({
    runtime: image.runtime,
    client: {
      async saveBoard(_boardId, document) {
        saveAttempts.push(document);
        if (saveAttempts.length === 1) {
          throw Object.assign(
            new Error("GitHub authentication expired or insufficient permissions"),
            { loginUrl: "/auth/login" },
          );
        }
        return boardFixture("board-a", document);
      },
    },
  }), async (app) => {
    await app.flush();
    await app.click("#board-list button");
    await app.flush(() => image.images.succeed());
    await app.click("#hold-overlay path");
    await app.change("#hold-type-select", "pinch");
    assert.equal(app.text("#save-state"), "Unsaved changes");

    await app.click("#save-button");

    assert.equal(saveAttempts.length, 1);
    assert.equal(saveAttempts[0]?.regions[0]?.type, "pinch");
    assert.equal(app.documentValue("#hold-type-select"), "pinch");
    assert.equal(app.text("#save-state"), "Unsaved changes");
    assert.equal(app.document.querySelector("#validation-panel")?.classList.contains("hidden"), true);
    const status = app.document.querySelector<HTMLElement>("#editor-status");
    assert.match(status?.textContent ?? "", /return here and save again/i);
    assert.equal(status?.firstChild?.nodeType, Node.TEXT_NODE);
    const login = status?.querySelector<HTMLAnchorElement>("a");
    assert.equal(login?.previousSibling?.textContent, " ");
    assert.equal(login?.getAttribute("href"), "/auth/login");
    assert.equal(login?.getAttribute("target"), "_blank");
    assert.equal(login?.getAttribute("rel"), "noopener noreferrer");

    await app.click("#save-button");

    assert.equal(saveAttempts.length, 2);
    assert.equal(app.text("#save-state"), "Saved");
    assert.equal(app.text("#editor-status"), "Board saved.");
    assert.equal(app.document.querySelector("#editor-status a"), null);
  });
});

test("selecting another board clears save authentication recovery state", async () => {
  const image = imageFixture();
  await withHook(dependenciesFixture({
    runtime: image.runtime,
    client: {
      async getBoard(boardId) { return boardFixture(boardId); },
      async saveBoard() {
        throw Object.assign(
          new Error("GitHub authentication expired or insufficient permissions"),
          { loginUrl: "/auth/login" },
        );
      },
    },
  }), async (result, harness) => {
    await harness.flush();
    let firstLoad!: Promise<void>;
    await harness.flush(() => { firstLoad = result().actions.selectBoard("board-a"); });
    await harness.flush(async () => {
      image.images.succeed();
      await firstLoad;
    });
    await harness.flush(() => result().actions.updateDocument(
      editorDocument("M 4 4 L 24 4 L 24 24 Z"),
      "Edited.",
    ));
    await harness.flush(() => result().actions.saveBoard());
    assert.equal(result().state.saveLoginUrl, "/auth/login");

    let secondLoad!: Promise<void>;
    await harness.flush(() => { secondLoad = result().actions.selectBoard("board-b"); });
    await harness.flush(async () => {
      image.images.succeed();
      await secondLoad;
    });

    assert.equal(result().state.board?.boardId, "board-b");
    assert.equal(result().state.status, "Board loaded.");
    assert.equal(result().state.saveLoginUrl, null);
  });
});

test("branch changes clear save authentication recovery with the editor", async (context) => {
  for (const branchAction of ["switch", "create"] as const) {
    await context.test(branchAction, async () => {
      const image = imageFixture();
      await withHook(dependenciesFixture({
        runtime: image.runtime,
        client: {
          async saveBoard() {
            throw Object.assign(
              new Error("GitHub authentication expired or insufficient permissions"),
              { loginUrl: "/auth/login" },
            );
          },
        },
      }), async (result, harness) => {
        await harness.flush();
        let load!: Promise<void>;
        await harness.flush(() => { load = result().actions.selectBoard("board-a"); });
        await harness.flush(async () => {
          image.images.succeed();
          await load;
        });
        await harness.flush(() => result().actions.updateDocument(
          editorDocument("M 4 4 L 24 4 L 24 24 Z"),
          "Edited.",
        ));
        await harness.flush(() => result().actions.saveBoard());
        assert.equal(result().state.saveLoginUrl, "/auth/login");

        if (branchAction === "switch") {
          await harness.flush(() => result().actions.switchBranch("feature"));
        } else {
          await harness.flush(() => result().actions.createBranch("feature"));
        }

        assert.equal(result().state.board, null);
        assert.equal(result().state.document, null);
        assert.match(result().state.status, /feature/);
        assert.equal(result().state.saveLoginUrl, null);
      });
    });
  }
});

test("an old delayed save cannot overwrite a newer document identity", async () => {
  const image = imageFixture();
  const save = deferred<Board>();
  await withHook(dependenciesFixture({
    runtime: image.runtime,
    client: { saveBoard() { return save.promise; } },
  }), async (result, harness) => {
    await harness.flush();
    let load!: Promise<void>;
    await harness.flush(() => { load = result().actions.selectBoard("board-a"); });
    await harness.flush(async () => {
      image.images.succeed();
      await load;
    });
    const oldDocument = editorDocument("M 2 2 L 22 2 L 22 22 Z");
    await harness.flush(() => result().actions.updateDocument(oldDocument, "First edit"));
    let pendingSave!: Promise<void>;
    await harness.flush(() => { pendingSave = result().actions.saveBoard(); });
    const newDocument = editorDocument("M 9 9 L 29 9 L 29 29 Z");
    await harness.flush(() => result().actions.updateDocument(newDocument, "Newer edit"));
    await harness.flush(async () => {
      save.resolve(boardFixture("board-a", editorDocument("M 3 3 L 23 3 L 23 23 Z")));
      await pendingSave;
    });
    assert.equal(result().state.document?.regions[0]?.displayPath, "M 9 9 L 29 9 L 29 29 Z");
    assert.equal(result().state.dirty, true);
  });
});

test("autosave waits for a quiet 750ms window and saves the latest valid document once", async () => {
  const image = imageFixture();
  const savedDocuments: EditorDocument[] = [];
  await withHook(dependenciesFixture({
    runtime: image.runtime,
    client: {
      async saveBoard(_boardId, document) {
        savedDocuments.push(document);
        return boardFixture("board-a", document);
      },
    },
  }), async (result, harness) => {
    await harness.flush();
    let load!: Promise<void>;
    await harness.flush(() => { load = result().actions.selectBoard("board-a"); });
    await harness.flush(async () => {
      image.images.succeed();
      await load;
    });

    await harness.flush(() => result().actions.updateDocument(
      editorDocument("M 2 2 L 22 2 L 22 22 Z"),
      "First edit.",
    ));
    await harness.flush(() => wait(500));
    await harness.flush(() => result().actions.updateDocument(
      editorDocument("M 8 8 L 28 8 L 28 28 Z"),
      "Latest edit.",
    ));
    await harness.flush(() => wait(500));
    assert.equal(savedDocuments.length, 0);

    await harness.flush(() => wait(300));
    assert.equal(savedDocuments.length, 1);
    assert.equal(savedDocuments[0]?.regions[0]?.displayPath, "M 8 8 L 28 8 L 28 28 Z");
    assert.equal(result().state.dirty, false);
  });
});

test("a failed autosave waits for another document change before trying again", async () => {
  const image = imageFixture();
  const failedSave = deferred<Board>();
  let saves = 0;
  await withHook(dependenciesFixture({
    runtime: image.runtime,
    client: {
      async saveBoard() {
        saves += 1;
        return failedSave.promise;
      },
    },
  }), async (result, harness) => {
    await harness.flush();
    let load!: Promise<void>;
    await harness.flush(() => { load = result().actions.selectBoard("board-a"); });
    await harness.flush(async () => {
      image.images.succeed();
      await load;
    });
    await harness.flush(() => result().actions.updateDocument(
      editorDocument("M 7 7 L 27 7 L 27 27 Z"),
      "Edited.",
    ));

    await harness.flush(() => wait(800));
    assert.equal(saves, 1);
    await harness.flush(() => failedSave.reject(new Error("storage unavailable")));
    await harness.flush(() => wait(800));
    assert.equal(saves, 1);
  });
});

test("a failed manual save waits for another document change before autosaving", async () => {
  const image = imageFixture();
  let saves = 0;
  await withHook(dependenciesFixture({
    runtime: image.runtime,
    client: {
      async saveBoard() {
        saves += 1;
        throw new Error("storage unavailable");
      },
    },
  }), async (result, harness) => {
    await harness.flush();
    let load!: Promise<void>;
    await harness.flush(() => { load = result().actions.selectBoard("board-a"); });
    await harness.flush(async () => {
      image.images.succeed();
      await load;
    });
    await harness.flush(() => result().actions.updateDocument(
      editorDocument("M 7 7 L 27 7 L 27 27 Z"),
      "Edited.",
    ));

    await harness.flush(() => result().actions.saveBoard());
    assert.equal(saves, 1);
    await harness.flush(() => wait(800));
    assert.equal(saves, 1);
    assert.equal(result().state.dirty, true);
  });
});

test("turning autosave off cancels pending work and leaves later edits for manual save", async () => {
  const image = imageFixture();
  let saves = 0;
  await withApp(dependenciesFixture({
    runtime: image.runtime,
    client: {
      async saveBoard(_boardId, document) {
        saves += 1;
        return boardFixture("board-a", document);
      },
    },
  }), async (app) => {
    await app.flush();
    await app.click("#board-list button");
    await app.flush(() => image.images.succeed());
    await app.click("#hold-overlay path");
    await app.change("#hold-type-select", "pinch");
    await app.click("#autosave-toggle");
    await app.flush(() => wait(800));
    assert.equal(saves, 0);

    await app.change("#hold-type-select", "sloper");
    await app.flush(() => wait(800));
    assert.equal(saves, 0);
    assert.equal(app.text("#save-state"), "Unsaved changes");
  });
});

test("hold editing remains available during a save and survives its stale response", async () => {
  const image = imageFixture();
  const firstSave = deferred<Board>();
  const secondSave = deferred<Board>();
  const saves = [firstSave, secondSave];
  const savedDocuments: EditorDocument[] = [];
  await withApp(dependenciesFixture({
    runtime: image.runtime,
    client: {
      saveBoard(boardId, document) {
        savedDocuments.push(document);
        return saves[savedDocuments.length - 1]!.promise;
      },
    },
  }), async (app) => {
    await app.flush();
    await app.click("#board-list button");
    await app.flush(() => image.images.succeed());
    app.setSvgGeometry("#editor-svg", { rect: { left: 0, top: 0, width: 100, height: 50 } });
    await app.click("#hold-overlay path");
    await app.change("#hold-type-select", "sloper");

    await app.click("#save-button");

    assert.equal(savedDocuments.length, 1);
    assert.equal(savedDocuments[0]?.regions[0]?.type, "sloper");
    const inFlightSnapshot = structuredClone(savedDocuments[0]!);
    assert.equal(app.disabled("#save-button"), true);
    assert.equal(app.disabled("#board-list button"), true);
    assert.equal(app.disabled("#refresh-boards-button"), true);
    assert.equal(app.disabled("#git-refresh-button"), true);
    assert.equal(app.disabled("#git-branch-select"), true);
    assert.equal(app.disabled("#hold-type-select"), false);
    assert.equal(app.disabled("#add-hold-button"), false);

    await app.click("#add-hold-button");
    assert.equal(app.document.querySelectorAll("#hold-overlay path").length, 2);
    await app.click("#delete-hold-button");
    assert.equal(app.document.querySelectorAll("#hold-overlay path").length, 1);
    await app.click("#hold-overlay path");
    await app.click("#add-horizontal-guide-button");
    assert.equal(app.document.querySelectorAll("#guide-overlay .editor-guide-horizontal").length, 1);
    await app.pointer("#guide-overlay .editor-guide-horizontal", "pointerdown", {
      pointerId: 12,
      clientX: 10,
      clientY: 10,
    });
    await app.pointer("#editor-svg", "pointermove", { pointerId: 12, clientX: 10, clientY: 25 });
    await app.pointer("#editor-svg", "pointerup", { pointerId: 12, clientX: 10, clientY: 25 });
    assert.equal(app.document.querySelector("#guide-overlay .editor-guide-horizontal")?.getAttribute("y1"), "25");
    await app.click("#clear-guides-button");
    assert.equal(app.document.querySelectorAll("#guide-overlay .editor-guide-horizontal").length, 0);
    await app.change("#hold-type-select", "pinch");
    assert.deepEqual(savedDocuments[0], inFlightSnapshot);
    await app.click("#save-button");
    assert.equal(savedDocuments.length, 1);
    await app.flush(() => firstSave.resolve(boardFixture("board-a", savedDocuments[0]!)));

    assert.equal(app.documentValue("#hold-type-select"), "pinch");
    assert.equal(app.text("#save-state"), "Unsaved changes");
    await app.click("#save-button");
    assert.equal(savedDocuments.length, 2);
    assert.equal(savedDocuments[1]?.regions[0]?.type, "pinch");
    await app.flush(() => secondSave.resolve(boardFixture("board-a", savedDocuments[1]!)));
    assert.equal(app.text("#save-state"), "Saved");
  });
});

test("a successful save always reports Board saved after committing the saved document", async () => {
  const image = imageFixture();
  let saves = 0;
  await withApp(dependenciesFixture({
    runtime: image.runtime,
    client: {
      async saveBoard(boardId, document) {
        saves += 1;
        return boardFixture(boardId, document);
      },
    },
  }), async (app) => {
    await app.flush();
    await app.click("#board-list button");
    await app.flush(() => image.images.succeed());
    assert.equal(app.text("#editor-status"), "Board loaded.");

    await app.click("#save-button");

    assert.equal(saves, 1);
    assert.equal(app.text("#save-state"), "Saved");
    assert.equal(app.text("#editor-status"), "Board saved.");
  });
});

test("replacing dependencies starts current Git initialization when obsolete work never settles", async () => {
  const staleStatus = deferred<GitStatus>();
  let staleBoards = 0;
  let freshGitCalls = 0;
  let freshBoards = 0;
  const initialDependencies = dependenciesFixture({
    client: {
      async getAuthStatus() { return { ok: true, authenticated: true, username: "old-user" }; },
      getGitStatus() { return staleStatus.promise; },
      async listBoards() { staleBoards += 1; return []; },
    },
  });
  const replacementDependencies = dependenciesFixture({
    client: {
      async getAuthStatus() { return { ok: true, authenticated: true, username: "new-user" }; },
      async getGitStatus() {
        freshGitCalls += 1;
        return gitStatus({ currentBranch: "fresh", branches: ["fresh"] });
      },
      async listBoards() { freshBoards += 1; return []; },
    },
  });
  let replaceDependencies: ((dependencies: WorkbenchDependencies) => void) | undefined;

  function ReplacingApp(): ReactElement {
    const [dependencies, setDependencies] = useState(initialDependencies);
    replaceDependencies = (nextDependencies) => setDependencies(nextDependencies);
    return <WorkbenchApp dependencies={dependencies} />;
  }

  const app = await renderReact(<ReplacingApp />);
  try {
    await app.flush();
    assert.equal(app.disabled("#git-refresh-button"), true);
    await app.flush(() => replaceDependencies?.(replacementDependencies));
    await app.flush();

    assert.equal(app.text("#git-auth-status"), "Logged in as new-user");
    assert.equal(app.text("#git-status"), "fresh");
    assert.equal(staleBoards, 0);
    assert.equal(freshGitCalls, 1);
    assert.equal(freshBoards, 1);
    assert.equal(app.disabled("#git-refresh-button"), false);
  } finally {
    await app.cleanup();
  }
});

test("replacing dependencies releases a save abandoned by the old coordinator", async () => {
  const oldImage = imageFixture();
  const oldDependencies = dependenciesFixture({
    runtime: oldImage.runtime,
    client: { saveBoard() { return new Promise<Board>(() => {}); } },
  });
  let freshSaves = 0;
  const freshDependencies = dependenciesFixture({
    client: {
      async saveBoard(boardId, document) {
        freshSaves += 1;
        return boardFixture(boardId, document);
      },
    },
  });
  let replaceDependencies: ((dependencies: WorkbenchDependencies) => void) | undefined;

  function ReplacingApp(): ReactElement {
    const [dependencies, setDependencies] = useState(oldDependencies);
    replaceDependencies = (nextDependencies) => setDependencies(nextDependencies);
    return <WorkbenchApp dependencies={dependencies} />;
  }

  const app = await renderReact(<ReplacingApp />);
  try {
    await app.flush();
    await app.click("#board-list button");
    await app.flush(() => oldImage.images.succeed());
    await app.click("#save-button");
    assert.equal(app.disabled("#save-button"), true);

    await app.flush(() => replaceDependencies?.(freshDependencies));
    await app.flush();

    assert.equal(app.disabled("#save-button"), false);
    await app.click("#save-button");
    assert.equal(freshSaves, 1);
  } finally {
    await app.cleanup();
  }
});

test("detached HEAD differs from unavailable status and still permits New Branch", async () => {
  await withApp(dependenciesFixture({
    client: {
      async listBoards() { return []; },
      async getGitStatus() {
        return gitStatus({ currentBranch: null, branches: ["main"], dirty: true });
      },
    },
  }), async (app) => {
    await app.flush();
    assert.equal(app.text("#git-status"), "Detached HEAD (uncommitted changes)");
    assert.equal(app.text("#board-status"), "Detached HEAD");
    await app.input("#git-new-branch-name", "recovered");
    assert.equal(app.disabled("#git-new-branch-button"), false);
  });

  await withApp(dependenciesFixture({
    client: {
      async listBoards() { return []; },
      async getGitStatus() { throw new Error("status offline"); },
    },
  }), async (app) => {
    await app.flush();
    assert.equal(app.text("#git-status"), "Repository status unavailable");
    assert.equal(app.text("#board-status"), "No branch detected");
  });
});

test("hosted storage omits local commit controls while keeping Save and Open PR", async () => {
  await withApp(dependenciesFixture({
    client: {
      async listBoards() { return []; },
      async getAuthStatus() {
        return { ok: true, authenticated: true, username: "octocat", hostedStorage: true };
      },
    },
  }), async (app) => {
    await app.flush();
    for (const selector of ["#git-commit-message", "#git-commit-button", "#git-push-button"]) {
      assert.equal(app.document.querySelector(selector), null, `${selector} must be omitted`);
    }
    assert.ok(app.document.querySelector("#save-button"));
    assert.ok(app.document.querySelector("#git-open-pr-button"));
  });
});

test("dirty branch switch and create confirm once and honor cancellation while clean switch does not confirm", async () => {
  const confirms: string[] = [];
  const switched: string[] = [];
  const created: string[] = [];
  const image = imageFixture();
  await withHook(dependenciesFixture({
    runtime: image.runtime,
    dialogs: { confirm(message) { confirms.push(message); return false; } },
    client: {
      async switchBranch(branch) { switched.push(branch); return branch; },
      async createBranch(branch) { created.push(branch); return branch; },
    },
  }), async (result, harness) => {
    await harness.flush();
    await harness.flush(() => result().actions.switchBranch("feature"));
    await harness.flush(() => result().actions.createBranch("clean-branch"));
    assert.deepEqual(switched, ["feature"]);
    assert.deepEqual(created, ["clean-branch"]);
    assert.deepEqual(confirms, []);

    let load!: Promise<void>;
    await harness.flush(() => { load = result().actions.selectBoard("board-a"); });
    await harness.flush(async () => {
      image.images.succeed();
      await load;
    });
    await harness.flush(() => result().actions.updateDocument(editorDocument("M 4 4 L 24 4 L 24 24 Z"), "edit"));
    await harness.flush(() => result().actions.switchBranch("main"));
    await harness.flush(() => result().actions.createBranch("cancelled"));
    assert.deepEqual(switched, ["feature"]);
    assert.deepEqual(created, ["clean-branch"]);
    assert.equal(confirms.length, 2);
  });
});

test("successful switch and create retain success when status refresh fails and create clears input", async () => {
  let statusCalls = 0;
  await withApp(dependenciesFixture({
    client: {
      async listBoards() { return []; },
      async getGitStatus() {
        statusCalls += 1;
        if (statusCalls === 1) return gitStatus();
        throw new Error("status backend unavailable");
      },
    },
  }), async (app) => {
    await app.flush();
    await app.change("#git-branch-select", "feature");
    await app.click("#git-switch-button");
    assert.equal(app.text("#editor-status"), "Switched to feature. Repository status unavailable.");
    assert.match(app.text("#validation-list"), /status backend unavailable/);
  });

  let createStatusCalls = 0;
  await withApp(dependenciesFixture({
    client: {
      async listBoards() { return []; },
      async getGitStatus() {
        createStatusCalls += 1;
        if (createStatusCalls === 1) return gitStatus();
        throw new Error("create status backend unavailable");
      },
    },
  }), async (app) => {
    await app.flush();
    await app.input("#git-new-branch-name", "new-work");
    await app.click("#git-new-branch-button");
    assert.equal(app.documentValue("#git-new-branch-name"), "");
    assert.equal(app.text("#editor-status"), "Created new-work. Repository status unavailable.");
    assert.match(app.text("#validation-list"), /create status backend unavailable/);
  });
});

test("empty commit never calls the client and push status names the branch", async () => {
  let commits = 0;
  await withApp(dependenciesFixture({
    client: {
      async listBoards() { return []; },
      async commitBoardChanges(message) {
        commits += 1;
        return { ok: true, commit: "abcdef0", branch: "feature", message };
      },
    },
  }), async (app) => {
    await app.flush();
    await app.input("#git-commit-message", "   ");
    await app.click("#git-commit-button");
    assert.equal(commits, 0);
    assert.equal(app.text("#validation-list"), "Commit message is required.");
    await app.click("#git-push-button");
    assert.equal(app.text("#editor-status"), "Pushed main.");
  });
});

test("pull request prompts cancel safely and accepted values are trimmed with base main", async () => {
  let request: Parameters<WorkbenchClient["openPullRequest"]>[0] | undefined;
  const responses: Array<string | null> = [null, "  My title  ", "  My body  "];
  await withApp(dependenciesFixture({
    dialogs: { prompt() { return responses.shift() ?? null; } },
    client: {
      async listBoards() { return []; },
      async openPullRequest(options) {
        request = options;
        return { ok: true, branch: "main", url: "https://example.com/pr/1" };
      },
    },
  }), async (app) => {
    await app.flush();
    await app.click("#git-open-pr-button");
    assert.equal(request, undefined);
    await app.click("#git-open-pr-button");
    assert.deepEqual(request, { title: "My title", body: "My body", base: "main" });
  });
});
