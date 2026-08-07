const test = require("node:test");
const assert = require("node:assert/strict");

const {
  createLatestLoadCoordinator,
  createAutosaveCoordinator,
  createDraftStore,
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
  const view = { boardId: "board-a", revisionId: "revision-1", stage: 2 };
  const entry = {
    ...view,
    key: store.keyFor(view),
    generation: 7,
    document: { stage: 2, regions: [{ id: 1, contour: [[1, 1], [2, 1], [1, 2]] }] },
  };

  store.writeDirty(entry);

  assert.deepEqual(store.read(view), { ...entry, dirty: true });
});

test("an older save completion cannot clear a newer local draft and mismatched pruning preserves other boards", () => {
  const storage = memoryStorage();
  const store = createDraftStore(storage);
  const firstView = { boardId: "board-a", revisionId: "revision-1", stage: 2 };
  const currentView = { boardId: "board-a", revisionId: "revision-2", stage: 3 };
  const otherView = { boardId: "board-b", revisionId: "revision-1", stage: 2 };
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
