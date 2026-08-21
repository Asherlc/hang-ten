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

function isFingerCapacity(value: unknown): value is number {
  return Number.isInteger(value) && typeof value === "number" && value >= 1 && value <= 4;
}

function isMillimeterRange(value: unknown): value is { lowerBound: number; upperBound: number } {
  if (!isRecord(value)) return false;
  const { lowerBound, upperBound } = value;
  return Number.isInteger(lowerBound)
    && Number.isInteger(upperBound)
    && typeof lowerBound === "number"
    && typeof upperBound === "number"
    && lowerBound > 0
    && upperBound >= lowerBound;
}

function isHoldRegion(value: unknown): value is EditorDocument["regions"][number] {
  if (!isRecord(value)) return false;
  const metadata = value.metadata;
  return typeof value.key === "string"
    && typeof value.displayPath === "string"
    && (value.id === undefined || typeof value.id === "number")
    && isOptionalString(value.type)
    && (value.fingerCapacity === undefined || isFingerCapacity(value.fingerCapacity))
    && (value.depthRangeMillimeters === undefined || isMillimeterRange(value.depthRangeMillimeters))
    && (metadata === undefined
      || (isRecord(metadata)
        && typeof metadata.holdID === "string"
        && typeof metadata.pieceIndex === "number"));
}

function isBoardSummary(value: unknown): value is BoardSummary {
  return isRecord(value)
    && typeof value.boardId === "string"
    && typeof value.displayName === "string"
    && typeof value.holdCount === "number"
    && isOptionalString(value.href);
}

function isEditorDocumentPayload(value: unknown): value is EditorDocument {
  return isRecord(value)
    && typeof value.schemaVersion === "number"
    && isRecord(value.canvas)
    && typeof value.canvas.width === "number"
    && typeof value.canvas.height === "number"
    && Array.isArray(value.regions)
    && value.regions.every(isHoldRegion);
}

function isBoard(value: unknown): value is Board {
  return isRecord(value)
    && typeof value.boardId === "string"
    && typeof value.displayName === "string"
    && typeof value.holdCount === "number"
    && isOptionalString(value.href)
    && typeof value.imageUrl === "string"
    && isOptionalString(value.saveUrl)
    && isEditorDocumentPayload(value.document);
}

function parseBoardList(payload: unknown): BoardSummary[] {
  if (!isRecord(payload)
    || !Array.isArray(payload.boards)
    || !payload.boards.every(isBoardSummary)) {
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
  const currentBranch = typeof payload.currentBranch === "string" && payload.currentBranch
    ? payload.currentBranch
    : null;
  return {
    ok: true,
    currentBranch,
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
  if (!isRecord(payload) || typeof payload.branch !== "string") {
    throw new Error("Workbench returned an invalid branch");
  }
  return payload.branch;
}

function parseCommit(payload: unknown): CommitResult {
  if (!isRecord(payload)
    || typeof payload.commit !== "string"
    || typeof payload.branch !== "string"
    || typeof payload.message !== "string") {
    throw new Error("Workbench returned an invalid commit");
  }
  return {
    ok: true,
    commit: payload.commit,
    branch: payload.branch,
    message: payload.message,
  };
}

function parsePush(payload: unknown): PushResult {
  if (!isRecord(payload)
    || typeof payload.branch !== "string"
    || typeof payload.remote !== "string") {
    throw new Error("Workbench returned an invalid push result");
  }
  return { ok: true, branch: payload.branch, remote: payload.remote };
}

function parsePullRequest(payload: unknown): PullRequestResult {
  if (!isRecord(payload)
    || typeof payload.branch !== "string"
    || typeof payload.url !== "string") {
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
    if (Number.isInteger(details.status)
      && details.status !== undefined
      && details.status >= 100
      && details.status <= 599) {
      diagnostic.status = details.status;
    }
    try {
      runtime.postDiagnostic?.(diagnostic);
    } catch {
      // Native diagnostics never replace the editor's useful error message.
    }
  }

  async function request<T>(
    path: string,
    parser: PayloadParser<T>,
    options: RequestOptions = {},
  ): Promise<T> {
    const { redirectOnUnauthorized = true, ...fetchOptions } = options;
    const requestOptions: RequestInit = {
      cache: "no-store",
      ...fetchOptions,
      signal: fetchOptions.signal ?? AbortSignal.timeout(15_000),
    };
    let response: Response;
    try {
      response = await runtime.fetch(path, requestOptions);
    } catch (error: unknown) {
      const detailMessage = errorMessage(error);
      const detail = detailMessage ? `: ${detailMessage}` : "";
      const message = `Could not reach the Hangboard Workbench backend for ${path}${detail}`;
      reportRequestFailure(path, "transport", message);
      throw new Error(message, { cause: error });
    }

    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      const message = `Workbench request for ${path} returned an unreadable response`;
      reportRequestFailure(path, "unreadable-response", message, { status: response.status });
      throw new Error(message);
    }

    const succeeded = isRecord(payload) && payload.ok === true;
    if (!response.ok || !succeeded) {
      const loginUrl = response.status === 401
        && isRecord(payload)
        && payload.login_url === "/auth/login"
        ? payload.login_url
        : null;
      const message = isRecord(payload) && typeof payload.error === "string" && payload.error
        ? payload.error
        : `Workbench request for ${path} failed (${String(response.status)})`;
      if (response.status >= 500) {
        reportRequestFailure(path, "server", message, { status: response.status });
      }
      const error = new Error(message) as Error & { loginUrl?: string };
      if (loginUrl) {
        error.loginUrl = loginUrl;
        if (redirectOnUnauthorized) runtime.location.assign(loginUrl);
      }
      throw error;
    }
    return parser(payload);
  }

  async function listBoards(): Promise<BoardSummary[]> {
    return request("/api/boards", parseBoardList);
  }

  async function getBoard(boardId: string): Promise<Board> {
    return request(
      `/api/boards/${encodeURIComponent(boardId)}`,
      parseBoard("Workbench returned an invalid board"),
    );
  }

  async function saveBoard(boardId: string, document: EditorDocument): Promise<Board> {
    return request(
      `/api/boards/${encodeURIComponent(boardId)}`,
      parseBoard("Workbench returned an invalid saved board"),
      {
        redirectOnUnauthorized: false,
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(document),
      },
    );
  }

  async function getGitStatus(): Promise<GitStatus> {
    return request("/api/git/status", parseGitStatus);
  }

  async function getAuthStatus(): Promise<AuthStatus> {
    try {
      return await request("/api/auth/status", parseAuthStatus);
    } catch {
      return { ok: true, authenticated: false };
    }
  }

  async function listBranches(): Promise<GitStatus> {
    return getGitStatus();
  }

  async function switchBranch(branchName: string): Promise<string> {
    if (!branchName.trim()) throw new Error("A branch name is required");
    return request("/api/git/checkout", parseBranch, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ branch: branchName.trim() }),
    });
  }

  async function createBranch(branchName: string): Promise<string> {
    if (!branchName.trim()) throw new Error("A branch name is required");
    return request("/api/git/checkout", parseBranch, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ branch: branchName.trim(), create: true }),
    });
  }

  async function commitBoardChanges(message: string): Promise<CommitResult> {
    if (typeof message !== "string") throw new Error("A commit message is required");
    return request("/api/git/commit", parseCommit, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message.trim() }),
    });
  }

  async function pushBranch(options: { remote?: string } = {}): Promise<PushResult> {
    const remote = typeof options.remote === "string" ? options.remote.trim() : "origin";
    return request("/api/git/push", parsePush, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ remote }),
    });
  }

  async function openPullRequest({
    title,
    body = "",
    base = "main",
    branch = null,
  }: {
    title?: string;
    body?: string;
    base?: string;
    branch?: string | null;
  } = {}): Promise<PullRequestResult> {
    if (typeof title !== "string" || !title.trim()) {
      throw new Error("A pull request title is required");
    }
    return request("/api/git/open-pr", parsePullRequest, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title.trim(),
        body: typeof body === "string" ? body : "",
        base: typeof base === "string" ? base.trim() || "main" : "main",
        branch: branch === null ? undefined : String(branch),
      }),
    });
  }

  return Object.freeze({
    getBoard,
    listBoards,
    saveBoard,
    getGitStatus,
    listBranches,
    switchBranch,
    createBranch,
    commitBoardChanges,
    pushBranch,
    openPullRequest,
    getAuthStatus,
  });
}
