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

function isPositiveFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

function isSloperMetadata(value: unknown): boolean {
  if (!isRecord(value) || (value.type !== "flat" && value.type !== "round")) return false;
  const allowedKeys = value.type === "flat" ? ["type", "angleDegrees"] : ["type"];
  if (!Object.keys(value).every((key) => allowedKeys.includes(key))) return false;
  if (value.type === "round") return true;
  return value.angleDegrees === undefined
    || (typeof value.angleDegrees === "number"
      && Number.isFinite(value.angleDegrees)
      && value.angleDegrees >= 0
      && value.angleDegrees <= 90);
}

function sameSloperMetadata(left: unknown, right: unknown): boolean {
  if (left === undefined || right === undefined) return left === right;
  if (!isRecord(left) || !isRecord(right)) return false;
  return left.type === right.type && left.angleDegrees === right.angleDegrees;
}

function isMillimeterRange(value: unknown): value is { lowerBound: number; upperBound: number } {
  if (!isRecord(value)) return false;
  const { lowerBound, upperBound } = value;
  return typeof lowerBound === "number"
    && typeof upperBound === "number"
    && Number.isFinite(lowerBound)
    && Number.isFinite(upperBound)
    && lowerBound > 0
    && upperBound >= lowerBound;
}

function isHandCapacity(value: unknown): value is number {
  return Number.isInteger(value) && typeof value === "number" && value >= 1 && value <= 2;
}

function isBendableCommandIndexes(value: unknown): value is number[] {
  return Array.isArray(value)
    && value.every((index) => typeof index === "number" && Number.isInteger(index) && index >= 0)
    && new Set(value).size === value.length;
}

function isHoldRegion(value: unknown): value is EditorDocument["regions"][number] {
  if (!isRecord(value)) return false;
  const metadata = value.metadata;
  return typeof value.key === "string"
    && typeof value.displayPath === "string"
    && (value.id === undefined || typeof value.id === "number")
    && isOptionalString(value.type)
    && isOptionalString(value.equipmentObjectID)
    && (value.sloper === undefined
      || (value.type === "sloper" && isSloperMetadata(value.sloper)))
    && (value.fingerCapacity === undefined || isFingerCapacity(value.fingerCapacity))
    && (value.sizeMillimeters === undefined || isPositiveFiniteNumber(value.sizeMillimeters))
    && (value.depthRangeMillimeters === undefined || isMillimeterRange(value.depthRangeMillimeters))
    && !(value.sizeMillimeters !== undefined && value.depthRangeMillimeters !== undefined)
    && (value.handCapacity === undefined || isHandCapacity(value.handCapacity))
    && (value.bendableCommandIndexes === undefined
      || isBendableCommandIndexes(value.bendableCommandIndexes))
    && (metadata === undefined
      || (isRecord(metadata)
        && typeof metadata.holdID === "string"
        && typeof metadata.pieceIndex === "number"
        && isOptionalString(metadata.presentationID)));
}

function isBoardPresentation(value: unknown): boolean {
  return isRecord(value)
    && typeof value.presentationID === "string"
    && typeof value.displayName === "string"
    && typeof value.imageUrl === "string"
    && (value.holdIDs === undefined || isStringArray(value.holdIDs))
    && typeof value.default === "boolean";
}

function isBoardSummary(value: unknown): value is BoardSummary {
  return isRecord(value)
    && typeof value.boardId === "string"
    && typeof value.displayName === "string"
    && typeof value.holdCount === "number"
    && typeof value.needsAttention === "boolean"
    && isOptionalString(value.href)
    && typeof value.imageUrl === "string";
}

function isEditorDocumentPayload(value: unknown): value is EditorDocument {
  if (!(isRecord(value)
    && Object.keys(value).every((key) => key === "presentationID" || key === "equipmentObjects" || key === "canvas" || key === "regions")
    && (value.presentationID === undefined || typeof value.presentationID === "string")
    && (value.equipmentObjects === undefined
      || (isStringArray(value.equipmentObjects)
        && value.equipmentObjects.length > 0
        && new Set(value.equipmentObjects).size === value.equipmentObjects.length))
    && isRecord(value.canvas)
    && typeof value.canvas.width === "number"
    && typeof value.canvas.height === "number"
    && Array.isArray(value.regions)
    && value.regions.every(isHoldRegion))) return false;

  const equipmentObjectIDs = value.equipmentObjects ? new Set(value.equipmentObjects) : null;
  if (equipmentObjectIDs && value.regions.some((region) => (
    !region.equipmentObjectID || !equipmentObjectIDs.has(region.equipmentObjectID)
  ))) return false;

  const sizeMillimetersByHoldId = new Map<string, number | undefined>();
  const sloperByHoldId = new Map<string, unknown>();
  const depthRangeByHoldId = new Map<string, { lowerBound: number; upperBound: number } | undefined>();
  const depthRepresentationByHoldId = new Map<string, "fixed" | "variable" | "unset">();
  const equipmentObjectByHoldId = new Map<string, string | undefined>();
  for (const region of value.regions) {
    if (!region.metadata) continue;
    const { holdID } = region.metadata;
    if (equipmentObjectByHoldId.has(holdID)
      && equipmentObjectByHoldId.get(holdID) !== region.equipmentObjectID) return false;
    equipmentObjectByHoldId.set(holdID, region.equipmentObjectID);
    if (sloperByHoldId.has(holdID)
      && !sameSloperMetadata(sloperByHoldId.get(holdID), region.sloper)) return false;
    sloperByHoldId.set(holdID, region.sloper);
    const depthRepresentation = region.sizeMillimeters !== undefined
      ? "fixed"
      : region.depthRangeMillimeters !== undefined ? "variable" : "unset";
    if (depthRepresentationByHoldId.has(holdID)
      && depthRepresentationByHoldId.get(holdID) !== depthRepresentation) return false;
    depthRepresentationByHoldId.set(holdID, depthRepresentation);
    if (sizeMillimetersByHoldId.has(holdID)
      && sizeMillimetersByHoldId.get(holdID) !== region.sizeMillimeters) return false;
    sizeMillimetersByHoldId.set(holdID, region.sizeMillimeters);
    const depthRange = region.depthRangeMillimeters;
    const existingDepthRange = depthRangeByHoldId.get(holdID);
    if (depthRangeByHoldId.has(holdID)
      && (existingDepthRange?.lowerBound !== depthRange?.lowerBound
        || existingDepthRange?.upperBound !== depthRange?.upperBound)) return false;
    depthRangeByHoldId.set(holdID, depthRange);
  }
  return true;
}

function isBoard(value: unknown): value is Board {
  return isRecord(value)
    && typeof value.boardId === "string"
    && typeof value.displayName === "string"
    && typeof value.holdCount === "number"
    && isOptionalString(value.href)
    && typeof value.imageUrl === "string"
    && isOptionalString(value.saveUrl)
    && isOptionalString(value.selectedPresentationID)
    && (value.presentations === undefined
      || (Array.isArray(value.presentations) && value.presentations.every(isBoardPresentation)))
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

  async function getBoard(boardId: string, presentationID?: string): Promise<Board> {
    const query = presentationID
      ? `?presentationID=${encodeURIComponent(presentationID)}`
      : "";
    return request(
      `/api/boards/${encodeURIComponent(boardId)}${query}`,
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

  async function deletePresentation(boardId: string, presentationID: string): Promise<Board> {
    if (!presentationID) throw new Error("A board surface is required");
    return request(
      `/api/boards/${encodeURIComponent(boardId)}/presentations/${encodeURIComponent(presentationID)}`,
      parseBoard("Workbench returned an invalid deleted board"),
      {
        redirectOnUnauthorized: false,
        method: "DELETE",
      },
    );
  }

  async function getGitStatus(): Promise<GitStatus> {
    return request("/api/git/status", parseGitStatus);
  }

  async function getAuthStatus(): Promise<AuthStatus> {
    return request("/api/auth/status", parseAuthStatus);
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
    deletePresentation,
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
