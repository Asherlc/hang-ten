const test = require("node:test");
const assert = require("node:assert/strict");

const {
  createLatestLoadCoordinator,
  createAutosaveCoordinator,
  createDraftStore,
  checkpointImageUrl,
  checkpointComparisonUrl,
  validateEditableImageAlignment,
  createActiveJobStore,
  reconcileActiveJobs,
  clearMatchingAcceptedJob,
  clearConfirmedTerminalJob,
  isRecoverableJobError,
  regionIdFromError,
  geometryValidationError,
  runFrozenApproval,
  createOpeningBoardController,
  renderOpeningBoardList,
  openingScreenState,
  renderOpeningFormVisibility,
  renderRepositoryDiagnostics,
  handleOpeningSelectionFailure,
  openingActionsDisabled,
} = require("../workbench-controller.js");

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((onResolve, onReject) => {
    resolve = onResolve;
    reject = onReject;
  });
  return { promise, resolve, reject };
}

async function nextTurn() {
  await new Promise((resolve) => setImmediate(resolve));
}

function memoryStorage() {
  const values = new Map();
  return {
    get length() { return values.size; },
    key(index) { return [...values.keys()][index] ?? null; },
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, String(value)); },
    removeItem(key) { values.delete(key); },
  };
}

test("opening board controller fetches all boards once and opens the selected repository or runtime board", async () => {
  const calls = [];
  const controller = createOpeningBoardController({
    async listBoards() {
      calls.push("boards");
      return {
        repositoryBoards: [{ boardId: "alpha", displayName: "Alpha", revisionToken: "a".repeat(64) }],
        inProgressBoards: [{ boardId: "board-2", productName: "Beta", saved: false }],
        diagnostics: [{ path: "broken-board", code: "invalid_run", message: "Broken package" }],
      };
    },
    async openRepositoryBoard(boardId) {
      calls.push(["open", boardId]);
      return { boardId: "board-1", productName: "Alpha" };
    },
    async getBoard(boardId) {
      calls.push(["get", boardId]);
      return { boardId, productName: "Beta" };
    },
  });

  assert.deepEqual(await controller.refresh(), {
    repositoryBoards: [{ boardId: "alpha", displayName: "Alpha", revisionToken: "a".repeat(64) }],
    diagnostics: [{ path: "broken-board", code: "invalid_run", message: "Broken package" }],
    inProgressBoards: [{ boardId: "board-2", productName: "Beta", saved: false }],
    error: "",
  });
  assert.deepEqual(await controller.openRepositoryBoard("alpha"), { boardId: "board-1", productName: "Alpha" });
  assert.deepEqual(await controller.openRuntimeBoard("board-2"), { boardId: "board-2", productName: "Beta" });
  assert.deepEqual(calls, ["boards", ["open", "alpha"], ["get", "board-2"]]);
});

test("opening board rows pass the selected repository and runtime identifiers", () => {
  const selected = [];
  const makeContainer = () => ({
    children: [],
    ownerDocument: {
      createElement() {
        return {
          listeners: {},
          append(...children) { this.children = children; },
          addEventListener(name, callback) { this.listeners[name] = callback; },
        };
      },
    },
    replaceChildren(...children) { this.children = children; },
    appendChild(child) { this.children.push(child); },
  });
  const repository = makeContainer();
  const inProgress = makeContainer();

  renderOpeningBoardList(repository, {
    state: "boards",
    boards: [
      { boardId: "metolius-compact-ii", displayName: "Wood Grips Compact II", status: "published" },
      { boardId: "beastmaker-1000", displayName: "beastmaker-1000", status: "draft" },
    ],
  }, {
    label: (board) => board.displayName,
    detail: () => "Ready to open",
    onSelect: (boardId) => selected.push(["openRepositoryBoard", boardId]),
  });
  renderOpeningBoardList(inProgress, {
    state: "boards",
    boards: [{ boardId: "runtime-board-17", productName: "Draft board" }],
  }, {
    label: (board) => board.productName,
    detail: () => "Stage 2",
    onSelect: (boardId) => selected.push(["getBoard", boardId]),
  });

  repository.children[0].listeners.click();
  repository.children[1].listeners.click();
  inProgress.children[0].listeners.click();

  assert.deepEqual(selected, [
    ["openRepositoryBoard", "metolius-compact-ii"],
    ["openRepositoryBoard", "beastmaker-1000"],
    ["getBoard", "runtime-board-17"],
  ]);
});

test("opening board controller reports one failure when the boards request fails", async () => {
  const controller = createOpeningBoardController({
    async listBoards() { throw new Error("Boards unavailable"); },
    async openRepositoryBoard() { throw new Error("not used"); },
    async getBoard() { throw new Error("not used"); },
  });

  assert.deepEqual(await controller.refresh(), {
    repositoryBoards: [],
    diagnostics: [],
    inProgressBoards: [],
    error: "Boards unavailable",
  });
});

test("opening screen renders empty board sections while leaving Create board visible", () => {
  assert.deepEqual(openingScreenState({ repositoryBoards: [], inProgressBoards: [] }), {
    repository: { state: "empty", boards: [], message: "No repository boards yet." },
    inProgress: { state: "empty", boards: [], message: "No boards in progress." },
    repositoryDiagnostics: [],
    createFormVisible: true,
  });
});

test("opening screen retains Create board when the repository list reports an error", () => {
  assert.deepEqual(openingScreenState({
    repositoryBoards: [],
    inProgressBoards: [{ boardId: "board-2", productName: "Beta", saved: false }],
    error: "Repository unavailable",
  }), {
    repository: { state: "error", boards: [], message: "Repository unavailable" },
    inProgress: {
      state: "error",
      boards: [{ boardId: "board-2", productName: "Beta", saved: false }],
      message: "Repository unavailable",
    },
    repositoryDiagnostics: [],
    createFormVisible: true,
  });
});

test("opening screen keeps valid repository boards selectable while exposing package diagnostics", () => {
  const diagnostics = [{
    path: "broken-board",
    code: "invalid_run",
    message: "broken-board: run is not Stage 4 complete",
  }];
  const screen = openingScreenState({
    repositoryBoards: [{ boardId: "alpha", displayName: "Alpha", revisionToken: "a".repeat(64) }],
    diagnostics,
  });

  assert.equal(screen.repository.state, "boards");
  assert.equal(screen.repository.boards[0].boardId, "alpha");
  assert.deepEqual(screen.repositoryDiagnostics, diagnostics);
});

test("opening screen with only package diagnostics omits the misleading empty-library message", () => {
  const screen = openingScreenState({
    repositoryBoards: [],
    diagnostics: [{ path: "broken-board", code: "invalid_run", message: "Broken package" }],
  });

  assert.deepEqual(screen.repository, { state: "diagnostics", boards: [], message: "" });
  assert.notEqual(screen.repository.message, "No published boards yet.");
});

test("repository diagnostics render their relative path and message", () => {
  const makeNode = (tagName) => ({
    tagName,
    children: [],
    textContent: "",
    className: "",
    classList: { toggle() {} },
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = [...children]; },
  });
  const ownerDocument = { createElement: makeNode };
  const container = { ...makeNode("div"), ownerDocument };

  renderRepositoryDiagnostics(container, [{
    path: "broken-board",
    code: "invalid_run",
    message: "broken-board: run is not Stage 4 complete",
  }]);

  assert.equal(container.children[0].textContent, "Repository warnings");
  assert.equal(container.children[1].children[0].children[0].textContent, "broken-board");
  assert.equal(
    container.children[1].children[0].children[1].textContent,
    "broken-board: run is not Stage 4 complete",
  );
});

test("opening screen keeps the Create board form visible for empty and repository-error states", () => {
  const classes = new Set(["hidden"]);
  const form = {
    classList: {
      toggle(name, force) {
        if (force) classes.add(name);
        else classes.delete(name);
      },
    },
  };

  renderOpeningFormVisibility(form, openingScreenState({ repositoryBoards: [], inProgressBoards: [] }));
  assert.equal(classes.has("hidden"), false);

  classes.add("hidden");
  renderOpeningFormVisibility(form, openingScreenState({
    repositoryBoards: [],
    inProgressBoards: [],
    error: "Repository unavailable",
  }));
  assert.equal(classes.has("hidden"), false);
});

test("recoverable repository-open polling failure preserves the frozen workbench", () => {
  const calls = [];
  const error = Object.assign(new Error("connection reset"), {
    jobId: "job-open-1",
    terminal: false,
  });

  const preserved = handleOpeningSelectionFailure({
    error,
    editingFrozen: true,
    setLibraryError(message) { calls.push(["error", message]); },
    showSetup() { calls.push(["setup"]); },
  });

  assert.equal(preserved, true);
  assert.deepEqual(calls, []);
  assert.equal(openingActionsDisabled({ busy: true, editingFrozen: true }), true);
});

test("terminal repository-open failure returns to setup with an actionable error", () => {
  const calls = [];

  const preserved = handleOpeningSelectionFailure({
    error: new Error("catalog entry is invalid"),
    editingFrozen: false,
    setLibraryError(message) { calls.push(["error", message]); },
    showSetup() { calls.push(["setup"]); },
  });

  assert.equal(preserved, false);
  assert.deepEqual(calls, [
    ["error", "catalog entry is invalid"],
    ["setup"],
  ]);
  assert.equal(openingActionsDisabled({ busy: false, editingFrozen: false }), false);
});

test("only the latest interleaved checkpoint load may commit identity, geometry, and autosave state", async () => {
  const coordinator = createLatestLoadCoordinator();
  const aGeometry = deferred();
  const bGeometry = deferred();
  const state = { boardId: null, regions: [], autosaveKey: null };

  async function load(boardId, pendingGeometry) {
    const load = coordinator.begin();
    const regions = await pendingGeometry.promise;
    return load.commit(() => {
      state.boardId = boardId;
      state.regions = regions;
      state.autosaveKey = `draft:${boardId}`;
    });
  }

  const loadingA = load("board-a", aGeometry);
  const loadingB = load("board-b", bGeometry);
  bGeometry.resolve([{ id: 2 }]);
  assert.equal(await loadingB, true);
  aGeometry.resolve([{ id: 1 }]);
  assert.equal(await loadingA, false);

  assert.deepEqual(state, {
    boardId: "board-b",
    regions: [{ id: 2 }],
    autosaveKey: "draft:board-b",
  });
});

test("cancelling an in-flight checkpoint load prevents its commit", async () => {
  const coordinator = createLatestLoadCoordinator();
  const geometry = deferred();
  const state = { boardId: null, regions: [] };
  const load = coordinator.begin();
  const loading = geometry.promise.then((regions) => load.commit(() => {
    state.boardId = "board-a";
    state.regions = regions;
  }));

  coordinator.cancel();
  geometry.resolve([{ id: 1 }]);

  assert.equal(await loading, false);
  assert.deepEqual(state, { boardId: null, regions: [] });
});

test("a reentrant autosave request reuses the save already being started", async () => {
  const calls = [];
  let reentered = false;
  let reentrantSave;
  let coordinator;
  coordinator = createAutosaveCoordinator({
    async save(entry) {
      calls.push(entry.document.version);
      if (!reentered) {
        reentered = true;
        reentrantSave = coordinator.requestLatest();
      }
      return { revisionId: "revision" };
    },
  });
  coordinator.update({ key: "board:revision:2", document: { version: 1 } });

  await coordinator.requestLatest();
  await reentrantSave;

  assert.deepEqual(calls, [1]);
  assert.equal(coordinator.hasPending(), false);
});

test("an edit during an active autosave produces one serialized latest follow-up", async () => {
  const firstSave = deferred();
  const secondSave = deferred();
  const calls = [];
  const saved = [];
  const coordinator = createAutosaveCoordinator({
    save(entry) {
      calls.push(entry.document.version);
      return calls.length === 1 ? firstSave.promise : secondSave.promise;
    },
    onSuccess(entry) { saved.push(entry.document.version); },
  });

  coordinator.update({ key: "board:revision:2", document: { version: 1 } });
  const background = coordinator.savePending();
  await nextTurn();
  coordinator.update({ key: "board:revision:2", document: { version: 2 } });
  coordinator.update({ key: "board:revision:2", document: { version: 3 } });
  coordinator.requestLatest();

  firstSave.resolve({ revisionId: "revision" });
  await nextTurn();
  assert.deepEqual(calls, [1, 3]);
  secondSave.resolve({ revisionId: "revision" });
  await background;

  assert.deepEqual(saved, [1, 3]);
  assert.equal(coordinator.hasPending(), false);
});

test("flush during an active save waits until the newest draft generation succeeds", async () => {
  const firstSave = deferred();
  const secondSave = deferred();
  const calls = [];
  const coordinator = createAutosaveCoordinator({
    save(entry) {
      calls.push(entry.document.version);
      return calls.length === 1 ? firstSave.promise : secondSave.promise;
    },
  });

  coordinator.update({ key: "board:revision:3", document: { version: 1 } });
  coordinator.savePending();
  await nextTurn();
  coordinator.update({ key: "board:revision:3", document: { version: 2 } });
  let flushed = false;
  const flushing = coordinator.flush().then(() => { flushed = true; });

  firstSave.resolve({ revisionId: "revision" });
  await nextTurn();
  assert.deepEqual(calls, [1, 2]);
  assert.equal(flushed, false);
  secondSave.resolve({ revisionId: "revision" });
  await flushing;

  assert.equal(flushed, true);
  assert.equal(coordinator.hasPending(), false);
});

test("a background autosave failure is reported without rejecting the timer-facing promise", async () => {
  const failures = [];
  const coordinator = createAutosaveCoordinator({
    save: async () => { throw new Error("save unavailable"); },
    onError(entry, error) { failures.push([entry.document.version, error.message]); },
  });
  coordinator.update({ key: "board:revision:2", document: { version: 4 } });

  assert.equal(await coordinator.savePending(), null);
  assert.deepEqual(failures, [[4, "save unavailable"]]);
  assert.equal(coordinator.hasPending(), true);
});

test("dirty recovery is available synchronously before a slow or failing server save", () => {
  const store = createDraftStore(memoryStorage());
  const view = {
    boardId: "board-a",
    revisionId: "revision-1",
    stage: 2,
    checkpointToken: "checkpoint-attempt-1",
  };
  const entry = {
    ...view,
    key: store.keyFor(view),
    generation: 7,
    document: { stage: 2, regions: [{ id: 1, contour: [[1, 1], [2, 1], [1, 2]] }] },
  };

  store.writeDirty(entry);

  assert.deepEqual(store.read(view), { ...entry, dirty: true });
});

test("draft recovery rejects a stale checkpoint attempt within the same revision and stage", () => {
  const storage = memoryStorage();
  const store = createDraftStore(storage);
  const firstAttempt = {
    boardId: "board-a",
    revisionId: "revision-1",
    stage: 2,
    checkpointToken: "checkpoint-attempt-1",
  };
  const retriedAttempt = {
    ...firstAttempt,
    checkpointToken: "checkpoint-attempt-2",
  };
  const entry = {
    ...firstAttempt,
    key: store.keyFor(firstAttempt),
    generation: 1,
    document: { version: "attempt-1-draft" },
  };

  store.writeDirty(entry);

  assert.equal(store.read(retriedAttempt), null);
  store.discardMismatched(retriedAttempt);
  assert.equal(store.read(firstAttempt), null);
});

test("an older save completion cannot clear a newer local draft and mismatched pruning preserves other boards", () => {
  const storage = memoryStorage();
  const store = createDraftStore(storage);
  const firstView = { boardId: "board-a", revisionId: "revision-1", stage: 2, checkpointToken: "checkpoint-a1" };
  const currentView = { boardId: "board-a", revisionId: "revision-2", stage: 3, checkpointToken: "checkpoint-a2" };
  const otherView = { boardId: "board-b", revisionId: "revision-1", stage: 2, checkpointToken: "checkpoint-b1" };
  const oldEntry = { ...firstView, key: store.keyFor(firstView), generation: 1, document: { version: 1 } };
  const currentEntry = { ...currentView, key: store.keyFor(currentView), generation: 3, document: { version: 3 } };
  const otherEntry = { ...otherView, key: store.keyFor(otherView), generation: 2, document: { version: 2 } };

  store.writeDirty(oldEntry);
  store.writeDirty(currentEntry);
  store.writeDirty(otherEntry);
  store.markSaved({ ...currentEntry, generation: 2 });
  assert.equal(store.read(currentView).dirty, true);

  store.discardMismatched(currentView);
  assert.equal(store.read(firstView), null);
  assert.deepEqual(store.read(currentView), { ...currentEntry, dirty: true });
  assert.deepEqual(store.read(otherView), { ...otherEntry, dirty: true });
});

test("editable checkpoints use the clean editor image while preserving annotated review access", () => {
  const view = {
    stage: 3,
    editorImageUrl: "/api/artifact?path=clean.png",
    editorDocumentUrl: "/api/artifact?path=regions.json",
    reviewUrl: "/api/artifact?path=annotated.png",
  };

  assert.equal(checkpointImageUrl(view), view.editorImageUrl);
  assert.equal(view.reviewUrl, "/api/artifact?path=annotated.png");
  assert.equal(checkpointImageUrl({ stage: 1, reviewUrl: view.reviewUrl }), view.reviewUrl);
});

test("checkpoint image selection uses the completed board normal artifact when no editor or review image exists", () => {
  assert.equal(
    checkpointImageUrl({
      editorImageUrl: null,
      reviewUrl: null,
      normalArtifactUrl: "/api/artifact?path=stage-4-normal.png",
    }),
    "/api/artifact?path=stage-4-normal.png",
  );
});

test("editable checkpoint comparison selects the review separately from the editor image", () => {
  const view = {
    stage: 2,
    editorImageUrl: "/api/artifact?path=clean.png",
    reviewUrl: "/api/artifact?path=annotated.png",
  };

  assert.equal(checkpointImageUrl(view), "/api/artifact?path=clean.png");
  assert.equal(checkpointComparisonUrl(view), "/api/artifact?path=annotated.png");
  assert.notEqual(checkpointComparisonUrl(view), checkpointImageUrl(view));
  assert.equal(checkpointComparisonUrl({ stage: 1, reviewUrl: view.reviewUrl }), null);
});

test("editable checkpoint image dimensions must match the geometry canvas", () => {
  const view = {
    stage: 3,
    editorImageUrl: "/api/artifact?path=clean.png",
    editorDocumentUrl: "/api/artifact?path=regions.json",
    reviewUrl: "/api/artifact?path=annotated.png",
  };
  const imageAsset = { image: { naturalWidth: 1000, naturalHeight: 159 } };
  const geometry = { canvas: { width: 1000, height: 160 }, regions: [] };

  assert.throws(
    () => validateEditableImageAlignment(view, imageAsset, geometry),
    /image dimensions do not match geometry canvas/,
  );
});

test("completed board editor geometry must align with its explicit editor image", () => {
  const view = {
    stage: 4,
    editorImageUrl: "/api/artifact?path=clean.png",
    editorDocumentUrl: "/api/artifact?path=regions.json",
  };
  const imageAsset = { image: { naturalWidth: 1000, naturalHeight: 159 } };
  const geometry = { canvas: { width: 1000, height: 160 }, regions: [] };

  assert.throws(
    () => validateEditableImageAlignment(view, imageAsset, geometry),
    /image dimensions do not match geometry canvas/,
  );
});

test("accepted job identity survives controller recreation for refresh recovery", () => {
  const storage = memoryStorage();
  createActiveJobStore(storage).write({ jobId: "job-17", boardId: "board-2" });

  assert.deepEqual(createActiveJobStore(storage).read(), {
    jobId: "job-17",
    boardId: "board-2",
  });
  assert.equal(createActiveJobStore(storage).clear("job-stale"), false);
  assert.deepEqual(createActiveJobStore(storage).read(), {
    jobId: "job-17",
    boardId: "board-2",
  });
  createActiveJobStore(storage).clear("job-17");
  assert.equal(createActiveJobStore(storage).read(), null);
});

test("two tabs preserve and reconcile independent board and creation jobs after restart", async () => {
  const storage = memoryStorage();
  const firstTab = createActiveJobStore(storage);
  const secondTab = createActiveJobStore(storage);
  const boardJob = { jobId: "job-board-a", boardId: "board-a" };
  const creationJob = { jobId: "job-create-b", boardId: null };
  firstTab.write(boardJob);
  secondTab.write(creationJob);

  const restartedFirstTab = createActiveJobStore(storage);
  const restartedSecondTab = createActiveJobStore(storage);
  assert.deepEqual(restartedFirstTab.readAll(), [boardJob, creationJob]);
  assert.deepEqual(restartedSecondTab.readAll(), [boardJob, creationJob]);

  const pollsByTab = [[], []];
  const pollFrom = (tabIndex) => async (jobId) => {
    pollsByTab[tabIndex].push(jobId);
    return jobId === boardJob.jobId
      ? { boardId: "board-a", productName: "Board A" }
      : { boardId: "board-b", productName: "Board B" };
  };
  const reconciliations = await Promise.all([
    reconcileActiveJobs(restartedFirstTab, pollFrom(0)),
    reconcileActiveJobs(restartedSecondTab, pollFrom(1)),
  ]);

  assert.deepEqual(pollsByTab.map((jobs) => jobs.sort()), [
    ["job-board-a", "job-create-b"],
    ["job-board-a", "job-create-b"],
  ]);
  for (const reconciliation of reconciliations) {
    assert.deepEqual(
      reconciliation.succeeded.map(({ acceptedJob, result }) => [acceptedJob, result.boardId]),
      [[boardJob, "board-a"], [creationJob, "board-b"]],
    );
    assert.deepEqual(reconciliation.failed, []);
    assert.deepEqual(reconciliation.unknown, []);
  }
  assert.deepEqual(restartedSecondTab.readAll(), []);
});

test("restart reconciliation retains genuinely unknown jobs while releasing only matching terminal jobs", async () => {
  const storage = memoryStorage();
  const store = createActiveJobStore(storage);
  const failedJob = { jobId: "job-failed", boardId: "board-a" };
  const unknownJob = { jobId: "job-unknown", boardId: "board-b" };
  store.write(failedJob);
  store.write(unknownJob);

  const reconciliation = await reconcileActiveJobs(store, async (jobId) => {
    if (jobId === failedJob.jobId) {
      throw Object.assign(new Error("rejected"), { jobId, terminal: true });
    }
    throw Object.assign(new Error("network unavailable"), { jobId, terminal: false });
  });

  assert.deepEqual(reconciliation.succeeded, []);
  assert.equal(reconciliation.failed.length, 1);
  assert.equal(reconciliation.failed[0].acceptedJob.jobId, failedJob.jobId);
  assert.equal(reconciliation.unknown.length, 1);
  assert.equal(reconciliation.unknown[0].acceptedJob.jobId, unknownJob.jobId);
  assert.deepEqual(store.readAll(), [unknownJob]);
});

test("geometry error parsing identifies the region the UI must focus", () => {
  assert.equal(regionIdFromError("Stage 2 region 17: contour is invalid"), 17);
  assert.equal(regionIdFromError("job failed"), null);
});

test("guided-action failures enter geometry validation only for public geometry errors", () => {
  assert.equal(typeof geometryValidationError, "function");
  assert.equal(geometryValidationError("job failed"), null);
  assert.deepEqual(
    geometryValidationError("Stage 2 region 17: contour is invalid"),
    { regionId: 17, message: "Stage 2 region 17: contour is invalid" },
  );
  assert.deepEqual(
    geometryValidationError("Stage 3 region 4: malformed displayPath"),
    { regionId: 4, message: "Stage 3 region 4: malformed displayPath" },
  );
  assert.deepEqual(
    geometryValidationError("review geometry is invalid"),
    { regionId: null, message: "review geometry is invalid" },
  );
});

test("only an accepted job without terminal confirmation remains recoverable", () => {
  assert.equal(isRecoverableJobError(new Error("request rejected")), false);
  assert.equal(isRecoverableJobError({ jobId: "job-17", terminal: true }), false);
  assert.equal(isRecoverableJobError({ jobId: "job-17", terminal: false }), true);
  assert.equal(isRecoverableJobError({ jobId: "job-17" }), true);
});

test("active job storage clears only for its matching confirmed terminal failure", () => {
  const storage = memoryStorage();
  const store = createActiveJobStore(storage);
  const acceptedJob = { jobId: "job-17", boardId: "board-2" };
  store.write(acceptedJob);

  assert.equal(clearConfirmedTerminalJob(store, acceptedJob, new Error("request failed")), false);
  assert.equal(clearConfirmedTerminalJob(store, acceptedJob, { jobId: "job-other", terminal: true }), false);
  assert.equal(clearConfirmedTerminalJob(store, acceptedJob, { jobId: "job-17", terminal: false }), false);
  assert.deepEqual(store.read(), acceptedJob);
  assert.equal(clearConfirmedTerminalJob(store, acceptedJob, { jobId: "job-17", terminal: true }), true);
  assert.equal(store.read(), null);

  store.write({ jobId: "job-current", boardId: "board-3" });
  assert.equal(clearConfirmedTerminalJob(store, acceptedJob, { jobId: "job-17", terminal: true }), false);
  assert.deepEqual(store.read(), { jobId: "job-current", boardId: "board-3" });
});

test("successful job release requires clearing the same persisted accepted job", () => {
  const storage = memoryStorage();
  const store = createActiveJobStore(storage);
  const creationJob = { jobId: "job-create", boardId: null };
  store.write(creationJob);

  assert.deepEqual(createActiveJobStore(storage).read(), creationJob);
  assert.equal(clearMatchingAcceptedJob(store, creationJob), true);

  const acceptedJob = { jobId: "job-17", boardId: "board-2" };
  store.write(acceptedJob);

  assert.equal(clearMatchingAcceptedJob(store, acceptedJob), true);
  assert.equal(store.read(), null);

  store.write({ jobId: "job-current", boardId: "board-3" });
  assert.equal(clearMatchingAcceptedJob(store, acceptedJob), false);
  assert.deepEqual(store.read(), { jobId: "job-current", boardId: "board-3" });
});

test("approval freezes and cancels editing before flushing the draft", async () => {
  const calls = [];
  const result = await runFrozenApproval({
    setFrozen(value) { calls.push(["frozen", value]); },
    cancelPointerSessions() { calls.push(["cancel"]); },
    async flushDraft() { calls.push(["flush"]); },
    async approve() { calls.push(["approve"]); return "advanced"; },
  });

  assert.equal(result, "advanced");
  assert.deepEqual(calls, [
    ["frozen", true],
    ["cancel"],
    ["flush"],
    ["approve"],
    ["frozen", false],
  ]);
});

test("approval restores editing after a pre-acceptance failure", async () => {
  const frozen = [];

  await assert.rejects(runFrozenApproval({
    setFrozen(value) { frozen.push(value); },
    cancelPointerSessions() {},
    async flushDraft() {},
    async approve() { throw new Error("approval rejected"); },
  }), /approval rejected/);

  assert.deepEqual(frozen, [true, false]);
});

test("approval restores editing after the server confirms the accepted job failed", async () => {
  const frozen = [];
  const failure = Object.assign(new Error("approval rejected"), {
    jobId: "job-17",
    terminal: true,
  });

  await assert.rejects(runFrozenApproval({
    setFrozen(value) { frozen.push(value); },
    cancelPointerSessions() {},
    async flushDraft() {},
    async approve() { throw failure; },
  }), failure);

  assert.deepEqual(frozen, [true, false]);
});

test("approval stays frozen while an accepted job has no confirmed terminal outcome", async () => {
  const frozen = [];
  const uncertainty = Object.assign(new Error("network unavailable"), {
    jobId: "job-17",
    terminal: false,
  });

  await assert.rejects(runFrozenApproval({
    setFrozen(value) { frozen.push(value); },
    cancelPointerSessions() {},
    async flushDraft() {},
    async approve() { throw uncertainty; },
  }), uncertainty);

  assert.deepEqual(frozen, [true]);
});
