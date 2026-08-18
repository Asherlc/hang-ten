const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function response(payload, { ok = true, status = 200 } = {}) {
  return { ok, status, async json() { return payload; } };
}

function freshClient() {
  delete require.cache[require.resolve("../workbench-client.js")];
  return require("../workbench-client.js");
}

function settle() {
  return new Promise((resolve) => setImmediate(resolve));
}

class FakeClassList {
  constructor() { this.values = new Set(); }
  add(value) { this.values.add(value); }
  remove(value) { this.values.delete(value); }
  toggle(value, enabled) {
    if (enabled === undefined ? !this.values.has(value) : enabled) this.values.add(value);
    else this.values.delete(value);
  }
}

class FakeElement {
  constructor(tagName, ownerDocument) {
    this.tagName = tagName;
    this.ownerDocument = ownerDocument;
    this.children = [];
    this.parent = null;
    this.classList = new FakeClassList();
    this.listeners = new Map();
    this.attributes = new Map();
    this.dataset = {};
    this.disabled = false;
    this.textContent = "";
    this.value = "";
  }

  append(...children) {
    this.children.push(...children);
    for (const child of children) { if (child instanceof FakeElement) child.parent = this; }
  }
  appendChild(child) {
    this.children.push(child);
    if (child instanceof FakeElement) child.parent = this;
    return child;
  }
  replaceChildren(...children) {
    this.children = children;
    for (const child of children) { if (child instanceof FakeElement) child.parent = this; }
    this.textContent = "";
  }
  remove() {
    if (!this.parent) return;
    this.parent.children = this.parent.children.filter((child) => child !== this);
    this.parent = null;
  }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  removeAttribute(name) { this.attributes.delete(name); }
  addEventListener(name, listener) { this.listeners.set(name, listener); }
  querySelector(selector) {
    if (typeof selector !== "string" || !selector.startsWith(".")) return null;
    const className = selector.slice(1);
    const stack = [...this.children];
    while (stack.length) {
      const node = stack.shift();
      if (!(node instanceof FakeElement)) continue;
      if (node.classList.values.has(className)) return node;
      stack.push(...node.children);
    }
    return null;
  }
  click() {
    if (!this.disabled) this.listeners.get("click")?.({ currentTarget: this, target: this });
  }
  change() {
    this.listeners.get("change")?.({ currentTarget: this, target: this });
  }
  input() {
    this.listeners.get("input")?.({ currentTarget: this, target: this });
  }
}

function loadApp({ client, controller, imageLoader = () => Promise.resolve({}), dialogs }) {
  const ids = [
    "board-list", "boards-error", "refresh-boards-button", "save-button", "save-state", "board-status",
    "board-name", "editor-svg", "board-image", "hold-overlay", "empty-state", "editor-status",
    "validation-panel", "validation-list", "hold-heading", "hold-empty", "hold-form", "hold-key",
    "git-auth-status", "git-status", "git-branch-select", "git-refresh-button", "git-switch-button",
    "git-new-branch-name", "git-new-branch-button",
    "git-commit-message", "git-commit-button", "git-push-button", "git-open-pr-button",
    "delete-hold-button",
  ];
  const elements = {};
  const document = {
    getElementById(id) { return elements[id]; },
    createElement(tagName) { return new FakeElement(tagName, document); },
    createElementNS(_namespace, tagName) { return new FakeElement(tagName, document); },
    listeners: new Map(),
    addEventListener(name, listener) {
      if (!this.listeners.has(name)) this.listeners.set(name, []);
      this.listeners.get(name).push(listener);
    },
    dispatchEvent(event) {
      for (const listener of this.listeners.get(event.type) || []) listener(event);
    },
  };
  for (const id of ids) elements[id] = new FakeElement("div", document);
  const context = {
    HoldWorkbenchClient: client,
    HoldWorkbenchController: controller,
    HoldWorkbenchDialogs: dialogs || {
      confirm: () => { throw new Error("dialogs.confirm was not stubbed for this test"); },
      prompt: () => { throw new Error("dialogs.prompt was not stubbed for this test"); },
    },
    HoldPathEditor: require("../path-editor.js"),
    Image: class {
      set src(href) {
        imageLoader(href).then(
          (image) => { Object.assign(this, image); this.onload?.(); },
          () => this.onerror?.(),
        );
      }
    },
    document,
    setImmediate,
  };
  context.globalThis = context;
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8"), context);
  return { elements, document };
}

test("the browser client lists and opens direct boards", async () => {
  const calls = [];
  global.fetch = async (request) => {
    calls.push(request);
    if (request === "/api/boards") {
      return response({ ok: true, boards: [{ boardId: "compact", displayName: "Compact", holdCount: 10 }] });
    }
    return response({
      ok: true,
      board: {
        boardId: "compact",
        imageUrl: "/api/boards/compact/image",
        document: { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [] },
      },
    });
  };
  const client = freshClient();

  assert.deepEqual(await client.listBoards(), [{ boardId: "compact", displayName: "Compact", holdCount: 10 }]);
  assert.equal((await client.getBoard("compact")).boardId, "compact");
  assert.deepEqual(calls, ["/api/boards", "/api/boards/compact"]);
});

test("the browser client saves one direct editor document with PUT", async () => {
  const calls = [];
  global.fetch = async (request, options) => {
    calls.push([request, options]);
    return response({ ok: true, board: { boardId: "compact", document: { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [] } } });
  };
  const client = freshClient();
  const document = { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [] };

  await client.saveBoard("compact", document);

  assert.equal(calls[0][0], "/api/boards/compact");
  assert.equal(calls[0][1].method, "PUT");
  assert.deepEqual(JSON.parse(calls[0][1].body), document);
});

test("the browser client can read git status and run git operations", async () => {
  const calls = [];
  global.fetch = async (request, options) => {
    calls.push([request, options]);
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
      return response({ ok: true, commit: "a".repeat(40), branch: "main", message: "Update board" });
    }
    if (request === "/api/git/push") {
      return response({ ok: true, branch: "main", remote: "origin" });
    }
    if (request === "/api/git/open-pr") {
      return response({ ok: true, branch: "main", url: "https://example.com/pull/1" });
    }
    throw new Error(`unexpected endpoint ${request}`);
  };

  const client = freshClient();

  assert.deepEqual(await client.getGitStatus(), {
    ok: true,
    currentBranch: "main",
    branches: ["main", "feature"],
    dirty: false,
    statusLines: [],
  });
  assert.equal(await client.listBranches().then((payload) => payload.branches.join(",")), "main,feature");
  assert.equal(await client.switchBranch("feature"), "feature");
  assert.equal(await client.createBranch("feature"), "feature");
  assert.equal(JSON.parse(calls.at(-1)[1].body).create, true);
  const commit = await client.commitBoardChanges("Update board");
  assert.equal(commit.commit, "a".repeat(40));
  const pushed = await client.pushBranch();
  assert.equal(pushed.remote, "origin");
  const opened = await client.openPullRequest({ title: "Update board", body: "", base: "main" });
  assert.equal(opened.url, "https://example.com/pull/1");
  assert.equal(calls.length, 7);
});

test("getGitStatus falls back to an empty statusLines array for null or non-array values", async () => {
  let statusLines = null;
  global.fetch = async (request) => {
    if (request === "/api/git/status") {
      return response({ ok: true, currentBranch: "main", branches: ["main"], dirty: true, statusLines });
    }
    throw new Error(`unexpected endpoint ${request}`);
  };
  const client = freshClient();

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

test("direct board loading commits image and holds together and preserves the prior editor on failure", async () => {
  const { loadBoardAtomically } = require("../workbench-controller.js");
  const prior = { boardId: "prior", image: { href: "prior.png" }, document: { regions: [{ key: "prior" }] } };
  const candidate = {
    boardId: "compact",
    imageUrl: "/api/boards/compact/image",
    document: { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [{ key: "hold-1", displayPath: "M 1 1 L 2 1 L 2 2 Z" }] },
  };
  const committed = [];
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
      getBoard: async () => ({ ...candidate, boardId: "broken" }),
      loadImage: async () => { throw new Error("Image unavailable"); },
      commit: (value) => committed.push(value),
    }),
    /Image unavailable/,
  );
  assert.deepEqual(committed, [success]);
  assert.equal(prior.boardId, "prior");
});

test("the direct editor model rejects duplicate and open hold paths before saving", () => {
  const { validateEditorDocument } = require("../workbench-controller.js");
  const base = { schemaVersion: 1, canvas: { width: 100, height: 50 } };
  assert.throws(() => validateEditorDocument({ ...base, regions: [
    { key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20 Z" },
    { key: "hold-1", displayPath: "M 30 1 L 40 1 L 40 20 Z" },
  ] }), /unique hold key/);
  assert.throws(() => validateEditorDocument({ ...base, regions: [
    { key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20" },
  ] }), /one closed contour/);
});

test("a rejected save keeps the editor document untouched", async () => {
  const { saveBoardAtomically } = require("../workbench-controller.js");
  const document = {
    schemaVersion: 1,
    canvas: { width: 100, height: 50 },
    regions: [{ key: "hold-1", displayPath: "M 1 1 L 20 1 L 20 20 Z" }],
  };
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
  assert.equal(document.regions[0].displayPath, "M 1 1 L 20 1 L 20 20 Z");
});

test("board operations serialize out-of-order selections", async () => {
  const { createBoardOperationCoordinator } = require("../workbench-controller.js");
  const busyStates = [];
  const coordinator = createBoardOperationCoordinator({ onBusyChange: (busy) => busyStates.push(busy) });
  let resolveFirst;
  const commits = [];

  const first = coordinator.perform(async ({ isCurrent }) => {
    await new Promise((resolve) => { resolveFirst = resolve; });
    if (isCurrent()) commits.push("first");
  });
  const second = await coordinator.perform(async ({ isCurrent }) => {
    if (isCurrent()) commits.push("second");
  });

  assert.deepEqual(second, { started: false, value: undefined });
  assert.deepEqual(busyStates, [true]);
  resolveFirst();
  assert.deepEqual(await first, { started: true, value: undefined });
  assert.deepEqual(commits, ["first"]);
  assert.deepEqual(busyStates, [true, false]);
});

test("a pending save cannot overwrite a board selected after the operation changes", async () => {
  const { createBoardOperationCoordinator } = require("../workbench-controller.js");
  const coordinator = createBoardOperationCoordinator();
  const editor = { boardId: "board-a", document: { regions: [{ key: "a" }] } };
  let resolveSave;
  const pendingSave = coordinator.perform(async ({ isCurrent }) => {
    await new Promise((resolve) => { resolveSave = resolve; });
    if (isCurrent() && editor.boardId === "board-a") {
      editor.document = { regions: [{ key: "saved-a" }] };
    }
  });

  editor.boardId = "board-b";
  editor.document = { regions: [{ key: "edited-b" }] };
  resolveSave();
  await pendingSave;

  assert.equal(editor.boardId, "board-b");
  assert.deepEqual(editor.document, { regions: [{ key: "edited-b" }] });
});

test("the browser disables every board action while a board selection is pending", async () => {
  let resolveBoardA;
  const requestedBoards = [];
  const controller = require("../workbench-controller.js");
  const app = loadApp({
    client: {
      async listBoards() {
        return [
          { boardId: "board-a", displayName: "Board A", holdCount: 1 },
          { boardId: "board-b", displayName: "Board B", holdCount: 1 },
        ];
      },
      getBoard(boardId) {
        requestedBoards.push(boardId);
        if (boardId === "board-a") return new Promise((resolve) => { resolveBoardA = resolve; });
        throw new Error("The locked Board B action must not start");
      },
      async saveBoard() { throw new Error("Save is not part of this selection test"); },
    },
    controller,
  });
  await settle();

  app.elements["board-list"].children[0].click();
  await settle();
  assert.equal(app.elements["refresh-boards-button"].disabled, true);
  assert.equal(app.elements["save-button"].disabled, true);
  assert.equal(app.elements["board-list"].children[0].disabled, true);
  assert.equal(app.elements["board-list"].children[1].disabled, true);

  app.elements["board-list"].children[1].click();
  assert.deepEqual(requestedBoards, ["board-a"]);
  resolveBoardA({
    boardId: "board-a",
    displayName: "Board A",
    imageUrl: "/api/boards/board-a/image",
    document: { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [] },
  });
  await settle();
  await settle();
  assert.equal(app.elements["board-name"].textContent, "Board A");
});

test("a pending browser save cannot reset a newer board document", async () => {
  let resolveSave;
  const controller = require("../workbench-controller.js");
  const boardA = {
    boardId: "board-a",
    displayName: "Board A",
    imageUrl: "/api/boards/board-a/image",
    document: { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [{ key: "a", displayPath: "M 1 1 L 2 1 L 2 2 Z" }] },
  };
  const app = loadApp({
    client: {
      async listBoards() { return [{ boardId: "board-a", displayName: "Board A", holdCount: 1 }]; },
      async getBoard() { return boardA; },
      saveBoard() { return new Promise((resolve) => { resolveSave = resolve; }); },
    },
    controller,
  });
  await settle();
  app.elements["board-list"].children[0].click();
  await settle();
  await settle();

  app.elements["save-button"].click();
  await settle();
  assert.equal(app.elements["board-list"].children[0].disabled, true);
  resolveSave({ ...boardA, document: { ...boardA.document, regions: [{ key: "a", displayPath: "M 10 10 L 20 10 L 20 20 Z" }] } });
  await settle();
  await settle();
  assert.equal(app.elements["board-name"].textContent, "Board A");
});

test("selecting a hold repeatedly does not duplicate the path editor overlay", async () => {
  const controller = require("../workbench-controller.js");
  const board = {
    boardId: "board-a",
    displayName: "Board A",
    imageUrl: "/api/boards/board-a/image",
    document: { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [{ key: "a", displayPath: "M 1 1 L 20 1 L 20 20 Z" }] },
  };
  const app = loadApp({
    client: {
      async listBoards() { return [{ boardId: "board-a", displayName: "Board A", holdCount: 1 }]; },
      async getBoard() { return board; },
    },
    controller,
  });
  await settle();
  app.elements["board-list"].children[0].click();
  await settle();
  await settle();

  function overlayCount() {
    return app.elements["editor-svg"].children.filter((child) => child.classList.values.has("path-editor-overlay")).length;
  }

  app.elements["hold-overlay"].children[0].click();
  assert.equal(overlayCount(), 1);

  app.elements["hold-overlay"].children[0].click();
  assert.equal(overlayCount(), 1);
});

test("the browser shows detached HEAD instead of unavailable when the repository has no branch", async () => {
  const controller = require("../workbench-controller.js");
  const app = loadApp({
    client: {
      async listBoards() { return []; },
      async getAuthStatus() { return { authenticated: true, username: "octocat" }; },
      async getGitStatus() {
        return { ok: true, currentBranch: null, branches: ["main"], dirty: true, statusLines: ["?? note.txt"] };
      },
    },
    controller,
  });
  await settle();
  await settle();

  assert.equal(app.elements["git-status"].textContent, "Detached HEAD (uncommitted changes)");
  assert.equal(app.elements["board-status"].textContent, "Detached HEAD");
});

test("the browser reports repository status unavailable only when the status fetch itself fails", async () => {
  const controller = require("../workbench-controller.js");
  const app = loadApp({
    client: {
      async listBoards() { return []; },
      async getAuthStatus() { return { authenticated: true, username: "octocat" }; },
      async getGitStatus() { throw new Error("network error"); },
    },
    controller,
  });
  await settle();
  await settle();

  assert.equal(app.elements["git-status"].textContent, "Repository status unavailable");
  assert.equal(app.elements["board-status"].textContent, "No branch detected");
});

test("switching branches does not prompt for confirmation when there are no unsaved hold edits", async () => {
  const controller = require("../workbench-controller.js");
  const switchedTo = [];
  const app = loadApp({
    client: {
      async listBoards() { return []; },
      async getAuthStatus() { return { authenticated: true, username: "octocat" }; },
      async getGitStatus() { return { ok: true, currentBranch: "main", branches: ["main", "feature"], dirty: false }; },
      async switchBranch(branch) { switchedTo.push(branch); return { ok: true }; },
    },
    controller,
    dialogs: {
      confirm: () => { throw new Error("confirm must not be called without unsaved edits"); },
      prompt: () => { throw new Error("prompt was not stubbed for this test"); },
    },
  });
  await settle();
  await settle();

  app.elements["git-branch-select"].value = "feature";
  app.elements["git-branch-select"].change();
  app.elements["git-switch-button"].click();
  await settle();
  await settle();

  assert.deepEqual(switchedTo, ["feature"]);
});

test("switching branches reports success plus a status warning when the post-switch status refresh fails", async () => {
  const controller = require("../workbench-controller.js");
  let statusCalls = 0;
  const app = loadApp({
    client: {
      async listBoards() { return []; },
      async getAuthStatus() { return { authenticated: true, username: "octocat" }; },
      async getGitStatus() {
        statusCalls += 1;
        if (statusCalls === 1) return { ok: true, currentBranch: "main", branches: ["main", "feature"], dirty: false };
        throw new Error("status backend unavailable");
      },
      async switchBranch(branch) { return { ok: true }; },
    },
    controller,
    dialogs: {
      confirm: () => { throw new Error("confirm was not stubbed for this test"); },
      prompt: () => { throw new Error("prompt was not stubbed for this test"); },
    },
  });
  await settle();
  await settle();

  app.elements["git-branch-select"].value = "feature";
  app.elements["git-branch-select"].change();
  app.elements["git-switch-button"].click();
  await settle();
  await settle();

  assert.equal(app.elements["editor-status"].textContent, "Switched to feature. Repository status unavailable.");
  assert.equal(app.elements["validation-panel"].classList.values.has("hidden"), false);
});

test("creating a branch switches to it and clears the new-branch input", async () => {
  const controller = require("../workbench-controller.js");
  const created = [];
  const app = loadApp({
    client: {
      async listBoards() { return []; },
      async getAuthStatus() { return { authenticated: true, username: "octocat" }; },
      async getGitStatus() { return { ok: true, currentBranch: "feature", branches: ["main", "feature"], dirty: false }; },
      async createBranch(branch) { created.push(branch); return branch; },
    },
    controller,
    dialogs: {
      confirm: () => { throw new Error("confirm must not be called without unsaved edits"); },
      prompt: () => { throw new Error("prompt was not stubbed for this test"); },
    },
  });
  await settle();
  await settle();

  app.elements["git-new-branch-name"].value = "feature";
  app.elements["git-new-branch-name"].input();
  app.elements["git-new-branch-button"].click();
  await settle();
  await settle();

  assert.deepEqual(created, ["feature"]);
  assert.equal(app.elements["git-new-branch-name"].value, "");
  assert.equal(app.elements["editor-status"].textContent, "Created and switched to feature.");
});

test("creating a branch is available from detached HEAD", async () => {
  const controller = require("../workbench-controller.js");
  const created = [];
  const app = loadApp({
    client: {
      async listBoards() { return []; },
      async getAuthStatus() { return { authenticated: true, username: "octocat" }; },
      async getGitStatus() {
        return { ok: true, currentBranch: null, branches: ["main"], dirty: false };
      },
      async createBranch(branch) { created.push(branch); return branch; },
    },
    controller,
    dialogs: {
      confirm: () => { throw new Error("confirm must not be called without unsaved edits"); },
      prompt: () => { throw new Error("prompt was not stubbed for this test"); },
    },
  });
  await settle();
  await settle();

  app.elements["git-new-branch-name"].value = "recovered";
  app.elements["git-new-branch-name"].input();

  assert.equal(app.elements["git-new-branch-button"].disabled, false);

  app.elements["git-new-branch-button"].click();
  await settle();
  await settle();

  assert.deepEqual(created, ["recovered"]);
});

test("opening a pull request cancels when the title prompt is dismissed", async () => {
  const controller = require("../workbench-controller.js");
  let opened = false;
  const prompts = [];
  const app = loadApp({
    client: {
      async listBoards() { return []; },
      async getAuthStatus() { return { authenticated: true, username: "octocat" }; },
      async getGitStatus() { return { ok: true, currentBranch: "feature", branches: ["main", "feature"], dirty: false }; },
      async openPullRequest() { opened = true; return { url: "https://example.com/pr/1" }; },
    },
    controller,
    dialogs: {
      confirm: () => { throw new Error("confirm was not stubbed for this test"); },
      prompt: (message, defaultValue) => { prompts.push(message); return null; },
    },
  });
  await settle();
  await settle();

  app.elements["git-open-pr-button"].click();
  await settle();

  assert.equal(prompts.length, 1);
  assert.equal(opened, false);
});

test("opening a pull request sends the prompted title and body", async () => {
  const controller = require("../workbench-controller.js");
  const requests = [];
  const app = loadApp({
    client: {
      async listBoards() { return []; },
      async getAuthStatus() { return { authenticated: true, username: "octocat" }; },
      async getGitStatus() { return { ok: true, currentBranch: "feature", branches: ["main", "feature"], dirty: false }; },
      async openPullRequest(request) { requests.push(request); return { url: "https://example.com/pr/1" }; },
    },
    controller,
    dialogs: {
      confirm: () => { throw new Error("confirm was not stubbed for this test"); },
      prompt: (message) => (message.startsWith("Pull request title") ? "My title" : "My body"),
    },
  });
  await settle();
  await settle();

  app.elements["git-open-pr-button"].click();
  await settle();

  assert.equal(requests.length, 1);
  assert.equal(requests[0].title, "My title");
  assert.equal(requests[0].body, "My body");
  assert.equal(requests[0].base, "main");
});

test("arrow keys nudge the selected hold by 1px and 10px with shift", async () => {
  const controller = require("../workbench-controller.js");
  const board = {
    boardId: "board-a",
    displayName: "Board A",
    imageUrl: "/api/boards/board-a/image",
    document: { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [{ key: "a", displayPath: "M 10 10 L 20 10 L 20 20 Z" }] },
  };
  const app = loadApp({
    client: {
      async listBoards() { return [{ boardId: "board-a", displayName: "Board A", holdCount: 1 }]; },
      async getBoard() { return board; },
    },
    controller,
  });
  await settle();
  app.elements["board-list"].children[0].click();
  await settle();
  await settle();
  app.elements["hold-overlay"].children[0].click();

  app.document.dispatchEvent({ key: "ArrowRight", shiftKey: false, type: "keydown", preventDefault() {} });
  assert.equal(app.elements["hold-overlay"].children[0].attributes.get("d"), "M 11 10 L 21 10 L 21 20 Z");

  app.document.dispatchEvent({ key: "ArrowRight", shiftKey: true, type: "keydown", preventDefault() {} });
  assert.equal(app.elements["hold-overlay"].children[0].attributes.get("d"), "M 21 10 L 31 10 L 31 20 Z");
});

test("the delete button removes the selected hold from the document", async () => {
  const controller = require("../workbench-controller.js");
  const board = {
    boardId: "board-a",
    displayName: "Board A",
    imageUrl: "/api/boards/board-a/image",
    document: { schemaVersion: 1, canvas: { width: 100, height: 50 }, regions: [
      { key: "a", displayPath: "M 10 10 L 20 10 L 20 20 Z" },
      { key: "b", displayPath: "M 30 10 L 40 10 L 40 20 Z" },
    ] },
  };
  const app = loadApp({
    client: {
      async listBoards() { return [{ boardId: "board-a", displayName: "Board A", holdCount: 2 }]; },
      async getBoard() { return board; },
    },
    controller,
    dialogs: { confirm: () => true, prompt: () => { throw new Error("prompt should not be called"); } },
  });
  await settle();
  app.elements["board-list"].children[0].click();
  await settle();
  await settle();
  app.elements["hold-overlay"].children[0].click();

  app.elements["delete-hold-button"].click();
  assert.equal(app.elements["hold-overlay"].children.length, 1);
  assert.equal(app.elements["hold-overlay"].children[0].attributes.get("d"), "M 30 10 L 40 10 L 40 20 Z");
  assert.equal(app.elements["hold-heading"].textContent, "No selection");
});

test("browser source contains only direct board vocabulary", () => {
  const root = path.join(__dirname, "..");
  const files = ["app.js", "index.html", "workbench-client.js", "workbench-controller.js"];
  const forbidden = /recent runs|in progress|checkpoint|approval|promotion|static mode|\bpipeline\b|\bstage\b|\brevision\b|\bretry\b|final-save/iu;
  for (const file of files) {
    assert.doesNotMatch(fs.readFileSync(path.join(root, file), "utf8"), forbidden, file);
  }
});
