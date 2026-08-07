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

  async function pollJob(jobId, { interval = 350 } = {}) {
    let job = await getJob(jobId);
    while (ACTIVE_JOB_STATES.has(job.state)) {
      await new Promise((resolve) => root.setTimeout(resolve, interval));
      job = await getJob(jobId);
    }
    if (job.state === "succeeded") return job.result;
    const error = new Error(job.error || "Workbench job failed");
    error.jobId = jobId;
    error.terminal = true;
    throw error;
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

  async function getBoard(boardId, revisionId = null) {
    const query = revisionId ? `?${new URLSearchParams({ revisionId }).toString()}` : "";
    return (await request(`/api/boards/${encodeURIComponent(boardId)}${query}`)).board;
  }

  function optimisticPayload(view) {
    return {
      boardId: view.boardId,
      expectedRevisionId: view.revisionId,
      expectedStage: view.stage,
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
    return postJob("/api/final-save", {
      boardId: view.boardId,
      expectedRevisionId: view.revisionId,
    }, options);
  }

  return {
    listBoards,
    createFromUrl,
    createFromUpload,
    importRun,
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
