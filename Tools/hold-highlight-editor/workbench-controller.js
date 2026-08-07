(function exposeWorkbenchController(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldWorkbenchController = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const DRAFT_PREFIX = "hold-workbench-draft:";
  const ACTIVE_JOB_KEY = "hold-workbench-active-job";
  const ACTIVE_JOB_PREFIX = `${ACTIVE_JOB_KEY}:`;
  const EDITABLE_STAGES = new Set([2, 3]);

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

  function createOpeningBoardController({
    listLibraryBoards,
    listBoards,
    openLibraryBoard,
    getBoard,
  }) {
    for (const [name, callback] of Object.entries({
      listLibraryBoards,
      listBoards,
      openLibraryBoard,
      getBoard,
    })) {
      if (typeof callback !== "function") throw new TypeError(`${name} must be a function`);
    }

    const collect = (list) => Promise.resolve()
      .then(list)
      .then(
        (boards) => ({ boards: Array.isArray(boards) ? boards : [], error: "" }),
        (error) => ({ boards: [], error: error?.message || "Could not load boards." }),
      );

    async function refresh() {
      const [library, runtime] = await Promise.all([
        collect(listLibraryBoards),
        collect(listBoards),
      ]);
      return Object.freeze({
        library: library.boards,
        runtime: runtime.boards,
        errors: Object.freeze({ library: library.error, runtime: runtime.error }),
      });
    }

    return Object.freeze({
      refresh,
      openRepositoryBoard: (boardId) => openLibraryBoard(boardId),
      openRuntimeBoard: (boardId) => getBoard(boardId),
    });
  }

  function openingScreenState({ library = [], runtime = [], errors = {} } = {}) {
    const section = (boards, error, emptyMessage) => ({
      state: error ? "error" : boards.length ? "boards" : "empty",
      boards,
      message: error || (boards.length ? "" : emptyMessage),
    });
    return {
      repository: section(library, errors.library || "", "No published boards yet."),
      inProgress: section(runtime, errors.runtime || "", "No boards in progress."),
      createFormVisible: true,
    };
  }

  function renderOpeningFormVisibility(form, screen) {
    if (typeof form?.classList?.toggle !== "function") {
      throw new TypeError("create board form must support classList.toggle");
    }
    form.classList.toggle("hidden", !screen?.createFormVisible);
  }

  function openingActionsDisabled({ busy = false, editingFrozen = false } = {}) {
    return Boolean(busy || editingFrozen);
  }

  function handleOpeningSelectionFailure({
    error,
    editingFrozen,
    setLibraryError,
    showSetup,
  }) {
    if (editingFrozen) return true;
    if (typeof setLibraryError !== "function" || typeof showSetup !== "function") {
      throw new TypeError("opening failure handlers are required");
    }
    setLibraryError(error?.message || "Could not open repository board.");
    showSetup();
    return false;
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
    if (!view || typeof view.checkpointToken !== "string" || !view.checkpointToken) return null;
    return `${DRAFT_PREFIX}${view.boardId}:${view.revisionId}:${String(view.stage)}:${view.checkpointToken}`;
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
        && record?.checkpointToken === view.checkpointToken
        && record.document;
    }

    function writeDirty(entry) {
      if (typeof entry?.key !== "string" || !entry.key) {
        throw new TypeError("checkpoint-bound draft key is required");
      }
      storage.setItem(entry.key, JSON.stringify({
        boardId: entry.boardId,
        revisionId: entry.revisionId,
        stage: entry.stage,
        checkpointToken: entry.checkpointToken,
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
      if (!key) return null;
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

  function checkpointImageUrl(view) {
    if (!view) return null;
    return view.editorImageUrl || view.reviewUrl || null;
  }

  function checkpointComparisonUrl(view) {
    if (!view || !EDITABLE_STAGES.has(view.stage) || !view.editorImageUrl) return null;
    if (!view.reviewUrl || view.reviewUrl === view.editorImageUrl) return null;
    return view.reviewUrl;
  }

  function validateEditableImageAlignment(view, imageAsset, geometryDocument) {
    if (!view || !EDITABLE_STAGES.has(view.stage)) return imageAsset;
    const image = imageAsset?.image || imageAsset;
    const canvas = geometryDocument?.canvas;
    const validCanvas = Number.isInteger(canvas?.width) && canvas.width > 0
      && Number.isInteger(canvas?.height) && canvas.height > 0;
    if (!validCanvas) throw new Error("Editable geometry canvas is invalid");
    if (image?.naturalWidth !== canvas.width || image?.naturalHeight !== canvas.height) {
      throw new Error("Editable image dimensions do not match geometry canvas");
    }
    return imageAsset;
  }

  function createActiveJobStore(storage) {
    function normalize(value) {
      if (!value || typeof value.jobId !== "string" || !value.jobId) return null;
      if (value.boardId != null && (typeof value.boardId !== "string" || !value.boardId)) return null;
      return { jobId: value.jobId, boardId: value.boardId ?? null };
    }

    function parse(key) {
      try {
        return normalize(JSON.parse(storage.getItem(key) || "null"));
      } catch (_error) {
        return null;
      }
    }

    function keyFor(jobId) {
      return `${ACTIVE_JOB_PREFIX}${encodeURIComponent(jobId)}`;
    }

    function readAll() {
      const records = new Map();
      const legacy = parse(ACTIVE_JOB_KEY);
      if (legacy) records.set(legacy.jobId, legacy);
      for (let index = 0; index < storage.length; index += 1) {
        const key = storage.key(index);
        if (!key?.startsWith(ACTIVE_JOB_PREFIX)) continue;
        const record = parse(key);
        if (record) records.set(record.jobId, record);
      }
      return [...records.values()].sort((left, right) => left.jobId.localeCompare(right.jobId));
    }

    function read(jobId = null) {
      const records = readAll();
      if (jobId == null) return records[0] || null;
      return records.find((record) => record.jobId === jobId) || null;
    }

    function write(job) {
      if (!job || typeof job.jobId !== "string" || !job.jobId) {
        throw new TypeError("accepted job ID is required");
      }
      if (job.boardId != null && (typeof job.boardId !== "string" || !job.boardId)) {
        throw new TypeError("accepted board ID must be a non-empty string or null");
      }
      const record = {
        jobId: job.jobId,
        boardId: job.boardId ?? null,
      };
      storage.setItem(keyFor(record.jobId), JSON.stringify(record));
      if (parse(ACTIVE_JOB_KEY)?.jobId === record.jobId) storage.removeItem(ACTIVE_JOB_KEY);
    }

    function clear(jobId) {
      let cleared = false;
      const key = keyFor(jobId);
      if (parse(key)?.jobId === jobId) {
        storage.removeItem(key);
        cleared = true;
      }
      if (parse(ACTIVE_JOB_KEY)?.jobId === jobId) {
        storage.removeItem(ACTIVE_JOB_KEY);
        cleared = true;
      }
      return cleared;
    }

    return Object.freeze({ read, readAll, write, clear });
  }

  function regionIdFromError(message) {
    const match = String(message).match(/region\s+(\d+)/i);
    return match ? Number(match[1]) : null;
  }

  function isRecoverableJobError(error) {
    return Boolean(error?.jobId && error.terminal !== true);
  }

  function clearMatchingAcceptedJob(store, acceptedJob) {
    if (typeof acceptedJob?.jobId !== "string" || !acceptedJob.jobId) return false;
    return store.clear(acceptedJob.jobId);
  }

  function clearConfirmedTerminalJob(store, acceptedJob, error) {
    if (error?.terminal !== true || error.jobId !== acceptedJob?.jobId) return false;
    return clearMatchingAcceptedJob(store, acceptedJob);
  }

  async function reconcileActiveJobs(store, pollJob) {
    if (typeof store?.readAll !== "function" || typeof pollJob !== "function") {
      throw new TypeError("active job store and poll function are required");
    }
    const outcomes = await Promise.all(store.readAll().map(async (acceptedJob) => {
      try {
        const result = await pollJob(acceptedJob.jobId);
        clearMatchingAcceptedJob(store, acceptedJob);
        return { state: "succeeded", acceptedJob, result };
      } catch (error) {
        if (error?.terminal === true && error.jobId === acceptedJob.jobId) {
          clearConfirmedTerminalJob(store, acceptedJob, error);
          return { state: "failed", acceptedJob, error };
        }
        return { state: "unknown", acceptedJob, error };
      }
    }));
    return Object.freeze({
      succeeded: outcomes.filter((outcome) => outcome.state === "succeeded"),
      failed: outcomes.filter((outcome) => outcome.state === "failed"),
      unknown: outcomes.filter((outcome) => outcome.state === "unknown"),
    });
  }

  async function restoreOpeningAfterJobRecovery({
    failure,
    refreshBoards,
    showSetup,
    setupError,
    setStatus,
  }) {
    for (const [name, callback] of Object.entries({
      refreshBoards,
      showSetup,
      setStatus,
    })) {
      if (typeof callback !== "function") throw new TypeError(`${name} must be a function`);
    }
    if (typeof setupError?.classList?.toggle !== "function") {
      throw new TypeError("setup error element must support classList.toggle");
    }
    const message = failure
      ? failure.message || "Could not reconnect to an active job"
      : "";
    await refreshBoards();
    showSetup();
    setupError.textContent = message;
    setupError.classList.toggle("hidden", !message);
    setStatus(message || "Open a board or create one to begin.");
    return message;
  }

  async function runFrozenApproval({
    setFrozen,
    cancelPointerSessions,
    flushDraft,
    approve,
  }) {
    for (const [name, callback] of Object.entries({
      setFrozen,
      cancelPointerSessions,
      flushDraft,
      approve,
    })) {
      if (typeof callback !== "function") throw new TypeError(`${name} must be a function`);
    }
    setFrozen(true);
    let result;
    try {
      cancelPointerSessions();
      await flushDraft();
      result = await approve();
    } catch (error) {
      if (!isRecoverableJobError(error)) setFrozen(false);
      throw error;
    }
    setFrozen(false);
    return result;
  }

  return {
    createLatestLoadCoordinator,
    createOpeningBoardController,
    openingScreenState,
    renderOpeningFormVisibility,
    openingActionsDisabled,
    handleOpeningSelectionFailure,
    createAutosaveCoordinator,
    createDraftStore,
    checkpointImageUrl,
    checkpointComparisonUrl,
    validateEditableImageAlignment,
    createActiveJobStore,
    reconcileActiveJobs,
    restoreOpeningAfterJobRecovery,
    clearMatchingAcceptedJob,
    clearConfirmedTerminalJob,
    isRecoverableJobError,
    regionIdFromError,
    runFrozenApproval,
  };
}));
