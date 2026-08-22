export interface Point {
  x: number;
  y: number;
}

export type PathCommandType = "M" | "L" | "Q" | "C" | "Z";

export interface PathCommand {
  type: PathCommandType;
  points: Point[];
  controls: Point[];
}

export type ShapeConstraintShape = "oval" | "circle" | "pill" | "roundedRectangle" | "rectangle";

export interface ShapeConstraint {
  shape: ShapeConstraintShape;
  rotationDegrees: number;
}

export interface MillimeterRange {
  lowerBound: number;
  upperBound: number;
}

export type OutlinePreset = Exclude<ShapeConstraintShape, "roundedRectangle"> | "rounded-rectangle";
export type ConstrainedHandle = "nw" | "n" | "ne" | "e" | "se" | "s" | "sw" | "w";

export interface Bounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

export interface ConstrainedOutlineModel {
  center: Point;
  rotationDegrees: number;
  intrinsicBounds: Bounds;
  handles: Record<ConstrainedHandle, Point>;
}

export interface ConstrainedResizeResult {
  displayPath: string;
  shapeConstraint: ShapeConstraint;
}

export interface HoldRegion {
  id?: number;
  key: string;
  type?: string;
  displayPath: string;
  metadata?: {
    holdID: string;
    pieceIndex: number;
  };
  fingerCapacity?: number;
  depthRangeMillimeters?: MillimeterRange;
  handCapacity?: number;
  shapeConstraint?: ShapeConstraint;
}

export interface EditorDocument {
  schemaVersion: number;
  canvas: {
    width: number;
    height: number;
  };
  regions: HoldRegion[];
}

export interface BoardSummary {
  boardId: string;
  displayName: string;
  holdCount: number;
  href?: string;
  imageUrl: string;
}

export interface Board extends BoardSummary {
  imageUrl: string;
  saveUrl?: string;
  document: EditorDocument;
}

export interface GitStatus {
  ok: true;
  currentBranch: string | null;
  branches: string[];
  dirty: boolean;
  statusLines: string[];
}

export interface AuthStatus {
  ok: true;
  authenticated: boolean;
  username?: string;
  hostedStorage?: boolean;
}

export interface CommitResult {
  ok: true;
  commit: string;
  branch: string;
  message: string;
}

export interface PushResult {
  ok: true;
  branch: string;
  remote: string;
}

export interface PullRequestResult {
  ok: true;
  branch: string;
  url: string;
}

export interface WorkbenchClient {
  listBoards(): Promise<BoardSummary[]>;
  getBoard(boardId: string): Promise<Board>;
  saveBoard(boardId: string, document: EditorDocument): Promise<Board>;
  getGitStatus(): Promise<GitStatus>;
  getAuthStatus(): Promise<AuthStatus>;
  listBranches(): Promise<GitStatus>;
  switchBranch(branchName: string): Promise<string>;
  createBranch(branchName: string): Promise<string>;
  commitBoardChanges(message: string): Promise<CommitResult>;
  pushBranch(options?: { remote?: string }): Promise<PushResult>;
  openPullRequest(options?: {
    title?: string;
    body?: string;
    base?: string;
    branch?: string | null;
  }): Promise<PullRequestResult>;
}

export interface BoardOperationContext {
  isCurrent(): boolean;
}

export interface BoardOperationResult<T> {
  started: boolean;
  value: T | undefined;
}

export interface BoardOperationCoordinator {
  readonly isBusy: boolean;
  perform<T>(operation: (context: BoardOperationContext) => Promise<T>): Promise<BoardOperationResult<T>>;
}

export interface LoadedBoard<ImageType = HTMLImageElement> {
  readonly board: Board;
  readonly image: ImageType;
  readonly document: EditorDocument;
}

export interface SavedBoard {
  readonly board: Board;
  readonly document: EditorDocument;
}

export interface WorkbenchController {
  validateEditorDocument(document: unknown): EditorDocument;
  loadBoardAtomically<ImageType>(options: {
    boardId: string;
    getBoard(boardId: string): Promise<Board>;
    loadImage(href: string): Promise<ImageType>;
    preloadedImage?: {
      href: string;
      promise: Promise<ImageType>;
    };
    commit(value: LoadedBoard<ImageType>): void;
  }): Promise<LoadedBoard<ImageType>>;
  saveBoardAtomically(options: {
    boardId: string;
    document: EditorDocument;
    save(boardId: string, document: EditorDocument): Promise<Board>;
    commit(value: SavedBoard): void;
  }): Promise<SavedBoard>;
  createBoardOperationCoordinator(options?: {
    onBusyChange?: (busy: boolean) => void;
  }): BoardOperationCoordinator;
}

export interface PathEditor {
  parsePath(pathString: string): PathCommand[];
  serializePath(commands: readonly PathCommand[]): string;
  pathBounds(commands: readonly PathCommand[]): Bounds;
  createOutlineShapePath(pathString: string, preset: OutlinePreset): string;
  constrainedOutlineModel(pathString: string, constraint: unknown): ConstrainedOutlineModel;
  resizeConstrainedOutline(
    pathString: string,
    constraint: unknown,
    handle: ConstrainedHandle,
    pointer: Point,
    minimumSize?: number,
  ): ConstrainedResizeResult;
  moveVertex(commands: PathCommand[], index: number, dx: number, dy: number): void;
  addVertex(commands: PathCommand[], afterIndex: number, x: number, y: number): void;
  addInflectionPoint(commands: PathCommand[], afterIndex: number, point: Point): boolean;
  deleteVertex(commands: PathCommand[], index: number): void;
  isInflectionVertex(commands: readonly PathCommand[], index: number): boolean;
  roundVertex(commands: PathCommand[], index: number): boolean;
  makeSegmentBendable(commands: PathCommand[], afterIndex: number): boolean;
  makeSegmentStraight(commands: PathCommand[], afterIndex: number): boolean;
  snapSegmentHorizontal(commands: PathCommand[], afterIndex: number): boolean;
  snapSegmentVertical(commands: PathCommand[], afterIndex: number): boolean;
  rotatePath(commands: PathCommand[], angleRadians: number, pivot: Point): void;
}

export interface RequestDiagnostic {
  path: string;
  category: string;
  message: string;
  status?: number;
}

export interface Dialogs {
  confirm(message: string): boolean;
  prompt(message: string, defaultValue?: string): string | null;
}

export interface BrowserStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export interface BrowserRuntime extends Dialogs {
  fetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response>;
  location: {
    assign(url: string): void;
  };
  storage?: BrowserStorage;
  postDiagnostic?(diagnostic: RequestDiagnostic): void;
  createImage(): HTMLImageElement;
}

export interface WorkbenchDependencies {
  client: WorkbenchClient;
  controller: WorkbenchController;
  pathEditor: PathEditor;
  runtime: BrowserRuntime;
  dialogs: Dialogs;
}

export interface WorkbenchState {
  initialized: boolean;
  boards: BoardSummary[];
  board: Board | null;
  document: EditorDocument | null;
  selectedKey: string | null;
  selectedKeys: string[];
  branches: string[];
  currentBranch: string | null;
  selectedBranch: string;
  gitStatusKnown: boolean;
  hasUncommittedChanges: boolean;
  dirty: boolean;
  autosaveEnabled: boolean;
  busyBoard: boolean;
  savingBoard: boolean;
  busyGit: boolean;
  authenticated: boolean;
  username: string | null;
  hostedStorage: boolean;
  newBranchName: string;
  commitMessage: string;
  rotationDegrees: string;
  validation: string;
  apiError: string;
  apiErrorOperation: string | null;
  status: string;
  saveLoginUrl: string | null;
  boardsError: string;
}

export interface DocumentUpdateOptions {
  dirty?: boolean;
  historySnapshot?: EditorDocument;
  selectedKey?: string | null;
  selectedKeys?: string[];
  validation?: string;
  status?: string;
  failureStatus?: string;
  failureMessage?: string;
}

export interface WorkbenchActions {
  refreshBoards(): Promise<void>;
  selectBoard(boardId: string): Promise<void>;
  saveBoard(): Promise<void>;
  setAutosaveEnabled(enabled: boolean): void;
  refreshGit(): Promise<void>;
  setSelectedBranch(branchName: string): void;
  switchBranch(branchName?: string): Promise<void>;
  setNewBranchName(branchName: string): void;
  createBranch(branchName?: string): Promise<void>;
  setCommitMessage(message: string): void;
  commitChanges(): Promise<void>;
  pushBranch(): Promise<void>;
  openPullRequest(): Promise<void>;
  selectHold(key: string | null, toggle?: boolean): void;
  setRotationDegrees(value: string): void;
  replaceDocument(document: EditorDocument, options?: DocumentUpdateOptions): EditorDocument;
  editDocument(edit: (document: EditorDocument) => void, options?: DocumentUpdateOptions): boolean;
  undoDocument(): boolean;
  redoDocument(): boolean;
  updateDocument(document: EditorDocument, status?: string): void;
}

export interface UseWorkbenchResult {
  state: WorkbenchState;
  actions: WorkbenchActions;
}
