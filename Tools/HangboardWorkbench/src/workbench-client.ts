import type {
  AuthStatus,
  Board,
  BoardSummary,
  BrowserRuntime,
  CommitResult,
  EditorDocument,
  GitStatus,
  PullRequestResult,
  PushResult,
  RequestDiagnostic,
  WorkbenchClient,
} from "./types.ts";
import { validateEditorDocument } from "./workbench-controller.ts";

type PayloadParser<T> = (payload: unknown) => T;
type RequestOptions = RequestInit & { redirectOnUnauthorized?: boolean };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isOptionalString(value: unknown): value is string | undefined {
  return value === undefined || typeof value === "string";
}

function isBoardPresentation(value: unknown): boolean {
  return isRecord(value)
    && typeof value.presentationID === "string"
    && typeof value.displayName === "string"
    && typeof value.imageUrl === "string"
    && typeof value.default === "boolean"
    && isOptionalString(value.sourcePresentationID)
    && (value.contactIDs === undefined || isStringArray(value.contactIDs));
}

function isBoardSummary(value: unknown): value is BoardSummary {
  return isRecord(value)
    && typeof value.boardId === "string"
    && typeof value.displayName === "string"
    && typeof value.contactCount === "number"
    && typeof value.needsAttention === "boolean"
    && isOptionalString(value.href)
    && isOptionalString(value.imageUrl)
    && (value.editorAvailable === undefined || typeof value.editorAvailable === "boolean")
    && isOptionalString(value.unavailableReason)
    && (value.editorAvailable !== false || value.imageUrl === undefined);
}

function isBoard(value: unknown): value is Board {
  if (!isRecord(value)
    || typeof value.boardId !== "string"
    || typeof value.displayName !== "string"
    || typeof value.contactCount !== "number"
    || !isOptionalString(value.href)
    || typeof value.imageUrl !== "string"
    || !isOptionalString(value.saveUrl)
    || !isOptionalString(value.selectedPresentationID)
    || (value.contactIDs !== undefined && !isStringArray(value.contactIDs))
    || (value.presentations !== undefined
      && (!Array.isArray(value.presentations) || !value.presentations.every(isBoardPresentation)))) {
    return false;
  }
  try {
    validateEditorDocument(value.document);
    return true;
  } catch {
    return false;
  }
}

function parseBoardList(payload: unknown): BoardSummary[] {
  if (!isRecord(payload) || !Array.isArray(payload.boards) || !payload.boards.every(isBoardSummary)) {
    throw new Error("Workbench returned an invalid board list");
  }
  return payload.boards;
}

function parseBoard(message: string): PayloadParser<Board> {
  return (payload) => {
    if (!isRecord(payload) || !isBoard(payload.board)) throw new Error(message);
    return payload.board;
  };
}

function parseGitStatus(payload: unknown): GitStatus {
  if (!isRecord(payload) || !isStringArray(payload.branches)) {
    throw new Error("Workbench returned an invalid branch list");
  }
  return {
    ok: true,
    currentBranch: typeof payload.currentBranch === "string" && payload.currentBranch
      ? payload.currentBranch : null,
    branches: payload.branches,
    dirty: Boolean(payload.dirty),
    statusLines: isStringArray(payload.statusLines) ? payload.statusLines : [],
  };
}

function parseAuthStatus(payload: unknown): AuthStatus {
  if (!isRecord(payload) || typeof payload.authenticated !== "boolean") {
    throw new Error("Workbench returned an invalid authentication status");
  }
  return {
    ok: true,
    authenticated: payload.authenticated,
    ...(typeof payload.username === "string" ? { username: payload.username } : {}),
    ...(typeof payload.hostedStorage === "boolean" ? { hostedStorage: payload.hostedStorage } : {}),
  };
}

function parseBranch(payload: unknown): string {
  if (!isRecord(payload) || typeof payload.branch !== "string") throw new Error("Workbench returned an invalid branch");
  return payload.branch;
}

function parseCommit(payload: unknown): CommitResult {
  if (!isRecord(payload) || typeof payload.commit !== "string"
    || typeof payload.branch !== "string" || typeof payload.message !== "string") {
    throw new Error("Workbench returned an invalid commit");
  }
  return { ok: true, commit: payload.commit, branch: payload.branch, message: payload.message };
}

function parsePush(payload: unknown): PushResult {
  if (!isRecord(payload) || typeof payload.branch !== "string" || typeof payload.remote !== "string") {
    throw new Error("Workbench returned an invalid push result");
  }
  return { ok: true, branch: payload.branch, remote: payload.remote };
}

function parsePullRequest(payload: unknown): PullRequestResult {
  if (!isRecord(payload) || typeof payload.branch !== "string" || typeof payload.url !== "string") {
    throw new Error("Workbench returned an invalid pull request");
  }
  return { ok: true, branch: payload.branch, url: payload.url };
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (isRecord(error) && typeof error.message === "string") return error.message;
  return "";
}

export function createWorkbenchClient(runtime: BrowserRuntime): WorkbenchClient {
  function reportRequestFailure(
    path: string,
    category: string,
    message: string,
    details: { status?: number } = {},
  ): void {
    const diagnostic: RequestDiagnostic = {
      path: String(path).slice(0, 256),
      category: String(category).slice(0, 64),
      message: String(message).slice(0, 1024),
    };
    if (Number.isInteger(details.status) && details.status !== undefined
      && details.status >= 100 && details.status <= 599) diagnostic.status = details.status;
    try { runtime.postDiagnostic?.(diagnostic); } catch { /* diagnostics are best-effort */ }
  }

  async function request<T>(
    path: string,
    parser: PayloadParser<T>,
    options: RequestOptions = {},
  ): Promise<T> {
    const { redirectOnUnauthorized = true, ...fetchOptions } = options;
    let response: Response;
    try {
      response = await runtime.fetch(path, {
        cache: "no-store",
        ...fetchOptions,
        signal: fetchOptions.signal ?? AbortSignal.timeout(15_000),
      });
    } catch (error: unknown) {
      const detail = errorMessage(error);
      const message = `Could not reach the Hangboard Workbench backend for ${path}${detail ? `: ${detail}` : ""}`;
      reportRequestFailure(path, "transport", message);
      throw new Error(message, { cause: error });
    }
    let payload: unknown;
    try { payload = await response.json(); }
    catch {
      const message = `Workbench request for ${path} returned an unreadable response`;
      reportRequestFailure(path, "unreadable-response", message, { status: response.status });
      throw new Error(message);
    }
    if (!response.ok || !isRecord(payload) || payload.ok !== true) {
      const loginUrl = response.status === 401 && isRecord(payload)
        && payload.login_url === "/auth/login" ? payload.login_url : null;
      const message = isRecord(payload) && typeof payload.error === "string" && payload.error
        ? payload.error : `Workbench request for ${path} failed (${String(response.status)})`;
      if (response.status >= 500) reportRequestFailure(path, "server", message, { status: response.status });
      const error = new Error(message) as Error & { loginUrl?: string };
      if (loginUrl) {
        error.loginUrl = loginUrl;
        if (redirectOnUnauthorized) runtime.location.assign(loginUrl);
      }
      throw error;
    }
    return parser(payload);
  }

  const listBoards = (): Promise<BoardSummary[]> => request("/api/boards", parseBoardList);
  const getBoard = (boardId: string, presentationID?: string): Promise<Board> => request(
    `/api/boards/${encodeURIComponent(boardId)}${presentationID ? `?presentationID=${encodeURIComponent(presentationID)}` : ""}`,
    parseBoard("Workbench returned an invalid board"),
  );
  const saveBoard = (boardId: string, document: EditorDocument): Promise<Board> => request(
    `/api/boards/${encodeURIComponent(boardId)}`,
    parseBoard("Workbench returned an invalid saved board"),
    { redirectOnUnauthorized: false, method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(document) },
  );
  const deletePresentation = (boardId: string, presentationID: string): Promise<Board> => {
    if (!presentationID) throw new Error("A board surface is required");
    return request(
      `/api/boards/${encodeURIComponent(boardId)}/presentations/${encodeURIComponent(presentationID)}`,
      parseBoard("Workbench returned an invalid deleted board"),
      { redirectOnUnauthorized: false, method: "DELETE" },
    );
  };
  const getGitStatus = (): Promise<GitStatus> => request("/api/git/status", parseGitStatus);
  const getAuthStatus = (): Promise<AuthStatus> => request("/api/auth/status", parseAuthStatus);
  const switchBranch = (branchName: string): Promise<string> => request(
    "/api/git/checkout", parseBranch,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ branch: branchName.trim() }) },
  );
  const createBranch = (branchName: string): Promise<string> => request(
    "/api/git/checkout", parseBranch,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ branch: branchName.trim(), create: true }) },
  );
  const commitBoardChanges = (message: string): Promise<CommitResult> => request(
    "/api/git/commit", parseCommit,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: message.trim() }) },
  );
  const pushBranch = ({ remote = "origin" }: { remote?: string } = {}): Promise<PushResult> => request(
    "/api/git/push", parsePush,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ remote }) },
  );
  const openPullRequest = ({ title, body = "", base = "main", branch = null }: {
    title?: string; body?: string; base?: string; branch?: string | null;
  } = {}): Promise<PullRequestResult> => {
    if (typeof title !== "string" || !title.trim()) throw new Error("A pull request title is required");
    return request(
      "/api/git/open-pr", parsePullRequest,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: title.trim(), body, base, branch: branch ?? undefined }) },
    );
  };
  return Object.freeze({
    getBoard, listBoards, saveBoard, deletePresentation, getGitStatus,
    listBranches: getGitStatus, switchBranch, createBranch, commitBoardChanges,
    pushBranch, openPullRequest, getAuthStatus,
  });
}
