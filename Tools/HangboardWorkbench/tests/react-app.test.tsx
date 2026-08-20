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
