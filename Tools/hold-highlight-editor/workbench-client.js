(function exposeWorkbenchClient(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldWorkbenchClient = api;
}(typeof globalThis === "object" ? globalThis : this, (root) => {
  "use strict";

  const ACTIVE_JOB_STATES = new Set(["queued", "running"]);

  async function request(path, options = {}) {
    const response = await root.fetch(path, { cache: "no-store", ...options });
    let payload;
    try {
      payload = await response.json();
    } catch (_error) {
      throw new Error(`Workbench request failed (${String(response.status)})`);
    }
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || `Workbench request failed (${String(response.status)})`);
    }
    return payload;
  }

  async function getJob(jobId) {
    return (await request(`/api/jobs/${encodeURIComponent(jobId)}`)).job;
  }

  function uncertainJobError(jobId, message, cause = null) {
    const error = cause instanceof Error ? cause : new Error(message);
    error.jobId = jobId;
    error.terminal = false;
    return error;
  }

  function validJobPayload(job, jobId) {
    if (!job || typeof job !== "object" || Array.isArray(job)) return false;
    if (job.id !== jobId || typeof job.boardId !== "string" || !job.boardId) return false;
    if (typeof job.state !== "string") return false;
    if (!Object.prototype.hasOwnProperty.call(job, "result")) return false;
    if (!Object.prototype.hasOwnProperty.call(job, "error")) return false;
    if (job.error !== null && typeof job.error !== "string") return false;
    if (job.state === "succeeded" && (!job.result || typeof job.result !== "object")) return false;
    if (job.state === "failed" && (
      job.result !== null || typeof job.error !== "string" || !job.error
    )) return false;
    return true;
  }

  async function pollJob(jobId, { interval = 350, maxTransientFailures = 3 } = {}) {
    let transientFailures = 0;
    while (true) {
      let job;
      try {
        job = await getJob(jobId);
        transientFailures = 0;
      } catch (error) {
        if (transientFailures >= maxTransientFailures) {
          throw uncertainJobError(jobId, "Workbench polling failed", error);
        }
        transientFailures += 1;
        await new Promise((resolve) => root.setTimeout(resolve, interval));
        continue;
      }
      if (!validJobPayload(job, jobId)) {
        throw uncertainJobError(jobId, "Workbench returned an uncertain job response");
      }
      if (job.state === "succeeded") return job.result;
      if (job.state === "failed") {
        const error = new Error(job.error || "Workbench job failed");
        error.jobId = jobId;
        error.terminal = true;
        throw error;
      }
      if (!ACTIVE_JOB_STATES.has(job.state)) {
        throw uncertainJobError(jobId, `Workbench returned unknown job state: ${job.state}`);
      }
      await new Promise((resolve) => root.setTimeout(resolve, interval));
    }
  }

  async function postJob(path, body, {
    headers = { "Content-Type": "application/json" },
    onAccepted = () => {},
  } = {}) {
    const payload = await request(path, {
      method: "POST",
      headers,
      body: headers["Content-Type"] === "application/json" ? JSON.stringify(body) : body,
    });
    onAccepted({
      jobId: payload.jobId,
      boardId: payload.boardId || body?.boardId || null,
    });
    return pollJob(payload.jobId);
  }

  async function listBoards() {
    return (await request("/api/boards")).boards;
  }

  async function listLibraryBoards() {
    const payload = await request("/api/library");
    return {
      boards: Array.isArray(payload.boards) ? payload.boards : [],
      diagnostics: Array.isArray(payload.diagnostics) ? payload.diagnostics : [],
    };
  }

  async function createFromUrl(productName, source, options = {}) {
    return postJob("/api/boards", { productName, source }, options);
  }

  async function createFromUpload(productName, image, options = {}) {
    const query = new URLSearchParams({ productName });
    return postJob(`/api/boards/upload?${query.toString()}`, image, {
      ...options,
      headers: {
        "Content-Type": image.type || "application/octet-stream",
      },
    });
  }

  async function importRun(runRoot, options = {}) {
    return postJob("/api/boards/import", { runRoot }, options);
  }

  async function openLibraryBoard(boardId, options = {}) {
    return postJob(`/api/library/${encodeURIComponent(boardId)}/open`, {}, options);
  }

  async function getBoard(boardId, revisionId = null) {
    const query = revisionId ? `?${new URLSearchParams({ revisionId }).toString()}` : "";
    return (await request(`/api/boards/${encodeURIComponent(boardId)}${query}`)).board;
  }

  function optimisticPayload(view) {
    return {
      boardId: view.boardId,
      expectedRevisionId: view.revisionId,
      expectedStage: view.stage,
      expectedCheckpointToken: view.checkpointToken,
    };
  }

  async function saveDraft(view, document, options = {}) {
    return postJob("/api/drafts", { ...optimisticPayload(view), document }, options);
  }

  async function approve(view, options = {}) {
    return postJob("/api/approve", optimisticPayload(view), options);
  }

  async function revise(view, stage, options = {}) {
    return postJob("/api/revise", {
      boardId: view.boardId,
      expectedRevisionId: view.revisionId,
      expectedStage: stage,
    }, options);
  }

  async function retry(view, options = {}) {
    return postJob("/api/retry", optimisticPayload(view), options);
  }

  async function finalSave(view, options = {}) {
    return postJob(`/api/boards/${encodeURIComponent(view.boardId)}/save`, {
      boardId: view.boardId,
      expectedRevisionId: view.revisionId,
    }, options);
  }

  return {
    listBoards,
    listLibraryBoards,
    createFromUrl,
    createFromUpload,
    importRun,
    openLibraryBoard,
    getBoard,
    getJob,
    pollJob,
    saveDraft,
    approve,
    revise,
    retry,
    finalSave,
  };
}));
