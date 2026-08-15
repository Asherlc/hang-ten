(function exposeWorkbenchClient(root, factory) {
  const api = factory(root);
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldWorkbenchClient = api;
}(typeof globalThis === "object" ? globalThis : this, (root) => {
  "use strict";

  function reportRequestFailure(path, category, message, details = {}) {
    const diagnostic = {
      path: String(path).slice(0, 256),
      category: String(category).slice(0, 64),
      message: String(message).slice(0, 1024),
    };
    if (Number.isInteger(details.status) && details.status >= 100 && details.status <= 599) {
      diagnostic.status = details.status;
    }
    try {
      root.webkit?.messageHandlers?.workbenchDiagnostics?.postMessage(diagnostic);
    } catch (_error) {
      // Native diagnostics never replace the editor's useful error message.
    }
  }

  async function request(path, options = {}) {
    const requestOptions = { cache: "no-store", ...options };
    let response;
    try {
      response = await root.fetch(path, requestOptions);
    } catch (error) {
      const detail = error?.message ? `: ${error.message}` : "";
      const message = `Could not reach the Hangboard Workbench backend for ${path}${detail}`;
      reportRequestFailure(path, "transport", message);
      throw new Error(message, { cause: error });
    }
    let payload;
    try {
      payload = await response.json();
    } catch (_error) {
      const message = `Workbench request for ${path} returned an unreadable response`;
      reportRequestFailure(path, "unreadable-response", message, { status: response.status });
      throw new Error(message);
    }
    if (!response.ok || !payload.ok) {
      const message = payload.error || `Workbench request for ${path} failed (${String(response.status)})`;
      if (response.status >= 500) reportRequestFailure(path, "server", message, { status: response.status });
      throw new Error(message);
    }
    return payload;
  }

  async function listBoards() {
    const payload = await request("/api/boards");
    if (!Array.isArray(payload.boards)) throw new Error("Workbench returned an invalid board list");
    return payload.boards;
  }

  async function getBoard(boardId) {
    const payload = await request(`/api/boards/${encodeURIComponent(boardId)}`);
    if (!payload.board || typeof payload.board !== "object") throw new Error("Workbench returned an invalid board");
    return payload.board;
  }

  async function saveBoard(boardId, document) {
    const payload = await request(`/api/boards/${encodeURIComponent(boardId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(document),
    });
    if (!payload.board || typeof payload.board !== "object") throw new Error("Workbench returned an invalid saved board");
    return payload.board;
  }

  return Object.freeze({ getBoard, listBoards, saveBoard });
}));
