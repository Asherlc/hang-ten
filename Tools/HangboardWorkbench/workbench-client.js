(function exposeWorkbenchClient(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldWorkbenchClient = api;
}(typeof globalThis === "object" ? globalThis : this, (root) => {
  "use strict";

  const ACTIVE_JOB_STATES = new Set(["queued", "running"]);
  const READ_ATTEMPTS = 3;
  const READ_RETRY_DELAY = 100;

  function wait(duration) {
    return new Promise((resolve) => root.setTimeout(resolve, duration));
  }

  function reportRequestFailure(path, category, message, details = {}) {
    const diagnostic = {
      path: String(path).slice(0, 256),
      category: String(category).slice(0, 64),
      message: String(message).slice(0, 1024),
    };
    if (Number.isInteger(details.status) && details.status >= 100 && details.status <= 599) {
      diagnostic.status = details.status;
    }
    if (Number.isInteger(details.attempts) && details.attempts >= 1 && details.attempts <= READ_ATTEMPTS) {
      diagnostic.attempts = details.attempts;
    }
    try {
      root.webkit?.messageHandlers?.workbenchDiagnostics?.postMessage(diagnostic);
    } catch (_error) {
      // Diagnostics must never replace the request failure the editor handles.
    }
  }

  function requestFailure(path, category, message, details = {}) {
    reportRequestFailure(path, category, message, details);
    return new Error(message);
  }

  async function request(path, options = {}, { retryTransportFailures = true } = {}) {
    const requestOptions = { cache: "no-store", ...options };
    const method = String(requestOptions.method || "GET").toUpperCase();
    let response;
    for (let attempt = 1; attempt <= READ_ATTEMPTS; attempt += 1) {
      try {
        response = await root.fetch(path, requestOptions);
        break;
      } catch (error) {
        if (method !== "GET" || !retryTransportFailures) {
          const detail = error?.message ? `: ${error.message}` : "";
          const message = `Could not reach the Hangboard Workbench backend for ${path}${detail}`;
          reportRequestFailure(path, "transport", message, { attempts: attempt });
          throw error;
        }
        if (attempt === READ_ATTEMPTS) {
          const detail = error?.message ? `: ${error.message}` : "";
          const message = `Could not reach the Hangboard Workbench backend for ${path} after ${attempt} attempt${attempt === 1 ? "" : "s"}${detail}`;
          const failure = requestFailure(path, "transport", message, { attempts: attempt });
          failure.cause = error;
          throw failure;
        }
        await wait(READ_RETRY_DELAY);
      }
    }
    let payload;
    try {
      payload = await response.json();
    } catch (_error) {
      const message = `Workbench request for ${path} returned an unreadable response (${String(response.status)})`;
      if (response.ok || response.status >= 500) {
        throw requestFailure(path, "unreadable-response", message, { status: response.status });
      }
      throw new Error(message);
    }
    if (!response.ok || !payload.ok) {
      const message = payload.error || `Workbench request for ${path} failed (${String(response.status)})`;
      if (response.status >= 500) {
        throw requestFailure(path, "server", message, { status: response.status });
      }
      throw new Error(message);
    }
    return payload;
  }

  async function getJob(jobId) {
    return (await request(
      `/api/jobs/${encodeURIComponent(jobId)}`,
      {},
      { retryTransportFailures: false },
    )).job;
  }

  function uncertainJobError(jobId, message, cause = null) {
    const error = cause instanceof Error ? cause : new Error(message);
    error.jobId = jobId;
    error.terminal = false;
    return error;
  }

  function pollingDeadlineError(jobId) {
    const error = uncertainJobError(jobId, "Workbench polling deadline expired");
    error.pollingDeadline = true;
    return error;
  }

  async function getJobBeforeDeadline(jobId, remainingDuration) {
    let timeoutId;
    const deadline = new Promise((_resolve, reject) => {
      timeoutId = root.setTimeout(
        () => reject(pollingDeadlineError(jobId)),
        Math.max(0, remainingDuration),
      );
    });
    try {
      return await Promise.race([getJob(jobId), deadline]);
    } finally {
      if (typeof root.clearTimeout === "function") root.clearTimeout(timeoutId);
    }
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

  async function pollJob(jobId, {
    interval = 350,
    maxTransientFailures = 3,
    maxDuration = 300_000,
  } = {}) {
    if (!Number.isFinite(maxDuration) || maxDuration < 0) {
      throw new RangeError("Polling duration must be finite and non-negative");
    }
    const deadline = Date.now() + maxDuration;
    let transientFailures = 0;
    while (true) {
      let job;
      try {
        job = await getJobBeforeDeadline(jobId, deadline - Date.now());
        transientFailures = 0;
      } catch (error) {
        if (error?.pollingDeadline) throw error;
        if (Date.now() >= deadline) {
          throw pollingDeadlineError(jobId);
        }
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
      if (Date.now() >= deadline) {
        throw pollingDeadlineError(jobId);
      }
      await new Promise((resolve) => root.setTimeout(resolve, interval));
    }
  }

  async function postJob(path, body, {
    headers = { "Content-Type": "application/json" },
    onAccepted = () => {},
    method = "POST",
  } = {}) {
    const payload = await request(path, {
      method,
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
    const payload = await request("/api/boards");
    const boards = Array.isArray(payload.boards) ? payload.boards : [];
    return {
      repositoryBoards: boards.filter((board) => board.inProgress !== true),
      inProgressBoards: boards.filter((board) => board.inProgress === true),
      diagnostics: Array.isArray(payload.diagnostics) ? payload.diagnostics : [],
    };
  }

  async function createFromUrl(productName, source, options = {}) {
    return postJob("/api/boards", { type: "url", productName, source }, options);
  }

  async function createFromUpload(productName, image, options = {}) {
    const query = new URLSearchParams({ type: "upload", productName });
    return postJob(`/api/boards?${query.toString()}`, image, {
      ...options,
      headers: {
        "Content-Type": image.type || "application/octet-stream",
      },
    });
  }

  async function importRun(runRoot, options = {}) {
    return postJob("/api/boards", { type: "import", runRoot }, options);
  }

  async function openRepositoryBoard(boardId, options = {}) {
    return postJob("/api/boards", { type: "repository", boardId }, options);
  }

  async function getBoard(boardId, revisionId = null) {
    const query = revisionId ? `?${new URLSearchParams({ revisionId }).toString()}` : "";
    return (await request(`/api/boards/${encodeURIComponent(boardId)}${query}`)).board;
  }

  function revisionQuery(revisionId) {
    return new URLSearchParams({ revisionId }).toString();
  }

  async function getValidationReport(boardId, revisionId) {
    const payload = await request(
      `/api/boards/${encodeURIComponent(boardId)}/validation?${revisionQuery(revisionId)}`,
    );
    return payload.report || null;
  }

  async function runValidation(boardId, revisionId, options = {}) {
    return postJob(`/api/boards/${encodeURIComponent(boardId)}/validation`, {
      boardId,
      expectedRevisionId: revisionId,
    }, options);
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
    return postJob(`/api/boards/${encodeURIComponent(view.boardId)}`, {
      boardId: view.boardId,
      expectedRevisionId: view.revisionId,
    }, { ...options, method: "PATCH" });
  }

  return {
    listBoards,
    createFromUrl,
    createFromUpload,
    importRun,
    openRepositoryBoard,
    getBoard,
    getValidationReport,
    runValidation,
    getJob,
    pollJob,
    saveDraft,
    approve,
    revise,
    retry,
    finalSave,
  };
}));
