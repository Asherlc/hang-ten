(function exposeWorkbenchController(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldWorkbenchController = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const DRAFT_PREFIX = "hold-workbench-draft:";

  function createLatestLoadCoordinator() {
    let latestToken = 0;
    return {
      begin() {
        const token = ++latestToken;
        return Object.freeze({
          isCurrent: () => token === latestToken,
          commit(callback) {
            if (token !== latestToken) return false;
            callback();
            return true;
          },
        });
      },
      cancel() { latestToken += 1; },
    };
  }

  function createAutosaveCoordinator({ save, onStart = () => {}, onSuccess = () => {}, onError = () => {} }) {
    if (typeof save !== "function") throw new TypeError("save must be a function");
    let generation = 0;
    let savedGeneration = 0;
    let requestedGeneration = 0;
    let latestEntry = null;
    let activeSave = null;

    function update(entry) {
      latestEntry = Object.freeze({ ...entry, generation: ++generation });
      return latestEntry;
    }

    function hasPending() {
      return Boolean(latestEntry && savedGeneration < latestEntry.generation);
    }

    async function drain() {
      while (latestEntry && savedGeneration < requestedGeneration) {
        const target = latestEntry;
        onStart(target);
        try {
          const result = await save(target);
          savedGeneration = Math.max(savedGeneration, target.generation);
          await onSuccess(target, result);
        } catch (error) {
          onError(target, error);
          throw error;
        }
      }
      return latestEntry;
    }

    function ensureSave() {
      if (activeSave) return activeSave;
      const saving = drain();
      activeSave = saving;
      saving.then(
        () => { if (activeSave === saving) activeSave = null; },
        () => { if (activeSave === saving) activeSave = null; },
      );
      return saving;
    }

    function requestLatest() {
      if (!latestEntry) return Promise.resolve(null);
      requestedGeneration = Math.max(requestedGeneration, latestEntry.generation);
      return ensureSave();
    }

    function savePending() {
      return requestLatest().catch(() => null);
    }

    async function flush() {
      while (hasPending()) {
        requestedGeneration = Math.max(requestedGeneration, latestEntry.generation);
        await ensureSave();
      }
      return latestEntry;
    }

    return Object.freeze({ update, requestLatest, savePending, flush, hasPending });
  }

  function draftKey(view) {
    if (!view) return null;
    return `${DRAFT_PREFIX}${view.boardId}:${view.revisionId}:${String(view.stage)}`;
  }

  function createDraftStore(storage) {
    function parse(key) {
      try {
        return JSON.parse(storage.getItem(key) || "null");
      } catch (_error) {
        return null;
      }
    }

    function matches(record, view) {
      return record?.boardId === view.boardId
        && record?.revisionId === view.revisionId
        && record?.stage === view.stage
        && record.document;
    }

    function writeDirty(entry) {
      storage.setItem(entry.key, JSON.stringify({
        boardId: entry.boardId,
        revisionId: entry.revisionId,
        stage: entry.stage,
        key: entry.key,
        generation: entry.generation,
        document: entry.document,
        dirty: true,
      }));
    }

    function markSaved(entry) {
      const record = parse(entry.key);
      if (!record || record.generation !== entry.generation) return false;
      storage.setItem(entry.key, JSON.stringify({ ...record, dirty: false }));
      return true;
    }

    function read(view) {
      const key = draftKey(view);
      const record = parse(key);
      if (!record) return null;
      if (!matches(record, view)) {
        storage.removeItem(key);
        return null;
      }
      return record;
    }

    function discardMismatched(view) {
      const currentKey = draftKey(view);
      const boardPrefix = `${DRAFT_PREFIX}${view.boardId}:`;
      for (let index = storage.length - 1; index >= 0; index -= 1) {
        const key = storage.key(index);
        if (key?.startsWith(boardPrefix) && key !== currentKey) storage.removeItem(key);
      }
    }

    return Object.freeze({ keyFor: draftKey, writeDirty, markSaved, read, discardMismatched });
  }

  return { createLatestLoadCoordinator, createAutosaveCoordinator, createDraftStore };
}));
