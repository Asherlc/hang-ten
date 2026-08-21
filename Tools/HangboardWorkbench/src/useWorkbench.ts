import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type {
  BoardOperationCoordinator,
  EditorDocument,
  GitStatus,
  UseWorkbenchResult,
  WorkbenchActions,
  WorkbenchDependencies,
  WorkbenchState,
} from "./types.ts";
import { cloneEditorDocument } from "./editor-model.ts";

const INITIAL_STATE: WorkbenchState = {
  initialized: false,
  boards: [],
  board: null,
  document: null,
  selectedKey: null,
  selectedKeys: [],
  branches: [],
  currentBranch: null,
  selectedBranch: "",
  gitStatusKnown: false,
  hasUncommittedChanges: false,
  dirty: false,
  busyBoard: false,
  savingBoard: false,
  busyGit: false,
  authenticated: false,
  username: null,
  hostedStorage: false,
  newBranchName: "",
  commitMessage: "",
  rotationDegrees: "",
  validation: "",
  status: "Ready.",
  saveLoginUrl: null,
  boardsError: "",
};

const MAX_DOCUMENT_HISTORY = 100;
interface DocumentHistory {
  undo: EditorDocument[];
  redo: EditorDocument[];
}

function resetHistory(history: DocumentHistory): void {
  history.undo = [];
  history.redo = [];
}

function recordHistory(history: DocumentHistory, document: EditorDocument): void {
  history.undo.push(cloneEditorDocument(document));
  if (history.undo.length > MAX_DOCUMENT_HISTORY) history.undo.shift();
  history.redo = [];
}

type StateUpdate = (state: WorkbenchState) => WorkbenchState;
type ActivityGuard = () => boolean;
interface OperationCoordinators {
  readonly dependencies: WorkbenchDependencies;
  readonly generation: number;
  readonly board: BoardOperationCoordinator;
  readonly git: BoardOperationCoordinator;
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

function saveLoginUrl(error: unknown): string | null {
  return typeof error === "object"
    && error !== null
    && "loginUrl" in error
    && error.loginUrl === "/auth/login"
    ? error.loginUrl
    : null;
}

function selectedBranch(status: GitStatus): string {
  if (status.currentBranch && status.branches.includes(status.currentBranch)) {
    return status.currentBranch;
  }
  return [...status.branches].sort()[0] ?? "";
}

function validSelection(document: EditorDocument, keys: readonly string[], primary: string | null): {
  selectedKeys: string[];
  selectedKey: string | null;
} {
  const available = new Set(document.regions.map((region) => region.key));
  const selectedKeys = [...new Set(keys)].filter((key) => available.has(key));
  return {
    selectedKeys,
    selectedKey: primary && selectedKeys.includes(primary) ? primary : selectedKeys.at(-1) ?? null,
  };
}

export function useWorkbench(dependencies: WorkbenchDependencies): UseWorkbenchResult {
  const { client, controller, dialogs, runtime } = dependencies;
  const [state, setState] = useState<WorkbenchState>(INITIAL_STATE);
  const stateRef = useRef(state);
  const mountedRef = useRef(true);
  const initializationGenerationRef = useRef(0);
  const historyRef = useRef<DocumentHistory>({ undo: [], redo: [] });
  const boardIdleWaitersRef = useRef(new Set<() => void>());
  const gitIdleWaitersRef = useRef(new Set<() => void>());
  const saveGenerationRef = useRef<number | null>(null);

  const updateState = useCallback((update: StateUpdate): void => {
    if (!mountedRef.current) return;
    const next = update(stateRef.current);
    stateRef.current = next;
    setState(next);
  }, []);

  // Dependency identity intentionally controls coordinator replacement and initialization.
  // Callers that construct dependencies inline must memoize that object between renders.
  const operationsRef = useRef<OperationCoordinators | null>(null);
  if (operationsRef.current?.dependencies !== dependencies) {
    const generation = (operationsRef.current?.generation ?? 0) + 1;
    saveGenerationRef.current = null;
    const board = controller.createBoardOperationCoordinator({
      onBusyChange: (busy) => {
        if (operationsRef.current?.generation !== generation) return;
        if (!busy) {
          for (const resolve of boardIdleWaitersRef.current) resolve();
          boardIdleWaitersRef.current.clear();
        }
        updateState((current) => ({ ...current, busyBoard: busy }));
      },
    });
    const git = controller.createBoardOperationCoordinator({
      onBusyChange: (busy) => {
        if (operationsRef.current?.generation !== generation) return;
        if (!busy) {
          for (const resolve of gitIdleWaitersRef.current) resolve();
          gitIdleWaitersRef.current.clear();
        }
        updateState((current) => ({ ...current, busyGit: busy }));
      },
    });
    operationsRef.current = { dependencies, generation, board, git };
  }
  const { generation: operationGeneration, board: boardOperations, git: gitOperations } = operationsRef.current;

  const isBusy = useCallback((): boolean => (
    boardOperations.isBusy || gitOperations.isBusy
  ), [boardOperations, gitOperations]);

  const waitForBoardIdle = useCallback(async (isActive: ActivityGuard): Promise<void> => {
    while (boardOperations.isBusy && isActive()) {
      await new Promise<void>((resolve) => boardIdleWaitersRef.current.add(resolve));
    }
  }, [boardOperations]);

  const waitForGitIdle = useCallback(async (isActive: ActivityGuard): Promise<void> => {
    while (gitOperations.isBusy && isActive()) {
      await new Promise<void>((resolve) => gitIdleWaitersRef.current.add(resolve));
    }
  }, [gitOperations]);

  const loadImage = useCallback((href: string): Promise<HTMLImageElement> => (
    new Promise((resolve, reject) => {
      const image = runtime.createImage();
      image.onload = () => {
        image.onload = null;
        image.onerror = null;
        resolve(image);
      };
      image.onerror = () => {
        image.onload = null;
        image.onerror = null;
        reject(new Error("Board image is unavailable"));
      };
      image.src = href;
    })
  ), [runtime]);

  const reloadBoards = useCallback(async (
    isActive: ActivityGuard = () => mountedRef.current,
    waitForSlot = false,
  ): Promise<boolean> => {
    if (waitForSlot) await waitForBoardIdle(isActive);
    if (!isActive()) return false;
    let loaded = false;
    await boardOperations.perform(async ({ isCurrent }) => {
      try {
        const boards = await client.listBoards();
        if (!isActive() || !isCurrent()) return;
        updateState((current) => ({
          ...current,
          boards,
          boardsError: "",
          status: "Boards loaded.",
        }));
        loaded = true;
      } catch (error: unknown) {
        if (!isActive() || !isCurrent()) return;
        updateState((current) => ({
          ...current,
          boardsError: errorMessage(error, "Could not load boards."),
          status: "Could not load boards.",
        }));
      }
    });
    return loaded;
  }, [boardOperations, client, updateState, waitForBoardIdle]);

  const refreshBoards = useCallback(async (): Promise<void> => {
    if (isBusy()) return;
    await reloadBoards();
  }, [isBusy, reloadBoards]);

  const refreshGitState = useCallback(async (
    isActive: ActivityGuard = () => mountedRef.current,
  ): Promise<boolean> => {
    try {
      const status = await client.getGitStatus();
      if (!isActive()) return false;
      updateState((current) => ({
        ...current,
        branches: [...status.branches],
        currentBranch: status.currentBranch,
        selectedBranch: selectedBranch(status),
        gitStatusKnown: true,
        hasUncommittedChanges: status.dirty,
      }));
      return true;
    } catch (error: unknown) {
      if (!isActive()) return false;
      updateState((current) => ({
        ...current,
        branches: [],
        currentBranch: null,
        selectedBranch: "",
        gitStatusKnown: false,
        hasUncommittedChanges: false,
        validation: errorMessage(error, "Could not read repository status."),
        status: "Could not read repository status.",
      }));
      return false;
    }
  }, [client, updateState]);

  const refreshGit = useCallback(async (): Promise<void> => {
    if (isBusy()) return;
    await gitOperations.perform(async ({ isCurrent }) => {
      await refreshGitState(() => mountedRef.current && isCurrent());
    });
  }, [gitOperations, isBusy, refreshGitState]);

  const refreshAuthState = useCallback(async (isActive: ActivityGuard): Promise<void> => {
    try {
      const auth = await client.getAuthStatus();
      if (!isActive()) return;
      updateState((current) => ({
        ...current,
        authenticated: auth.authenticated,
        username: auth.username ?? null,
        hostedStorage: auth.hostedStorage ?? false,
      }));
    } catch {
      if (!isActive()) return;
      updateState((current) => ({
        ...current,
        authenticated: false,
        username: null,
        hostedStorage: false,
      }));
    }
  }, [client, updateState]);

  const refreshInitialGitState = useCallback(async (isActive: ActivityGuard): Promise<void> => {
    await waitForGitIdle(isActive);
    if (!isActive()) return;
    await gitOperations.perform(async ({ isCurrent }) => {
      await refreshGitState(() => isActive() && isCurrent());
    });
  }, [gitOperations, refreshGitState, waitForGitIdle]);

  const selectBoard = useCallback(async (boardId: string): Promise<void> => {
    if (!boardId || isBusy()) return;
    updateState((current) => ({ ...current, validation: "", saveLoginUrl: null }));
    await boardOperations.perform(async ({ isCurrent }) => {
      let committed = false;
      try {
        await controller.loadBoardAtomically({
          boardId,
          getBoard: client.getBoard,
          loadImage,
          commit: ({ board, document }) => {
            if (!isCurrent()) return;
            resetHistory(historyRef.current);
            updateState((current) => ({
              ...current,
              board,
              document: cloneEditorDocument(document),
              selectedKey: null,
              selectedKeys: [],
              dirty: false,
            }));
            committed = true;
          },
        });
        if (committed) {
          updateState((current) => ({ ...current, status: "Board loaded." }));
        }
      } catch (error: unknown) {
        if (!isCurrent()) return;
        updateState((current) => ({
          ...current,
          validation: errorMessage(error, "Could not load board."),
          status: "Could not load board. The current editor was kept.",
        }));
      }
    });
  }, [boardOperations, client, controller, isBusy, loadImage, updateState]);

  const selectPresentation = useCallback(async (presentationID: string): Promise<void> => {
    const current = stateRef.current;
    if (!current.board || !presentationID || isBusy()
      || current.board.selectedPresentationID === presentationID) return;
    if (current.dirty) {
      updateState((value) => ({
        ...value,
        validation: "Save or undo the current surface changes before switching surfaces.",
        status: "Surface not changed. Unsaved edits were kept.",
      }));
      return;
    }
    const boardId = current.board.boardId;
    updateState((value) => ({ ...value, validation: "", saveLoginUrl: null }));
    await boardOperations.perform(async ({ isCurrent }) => {
      let committed = false;
      try {
        await controller.loadBoardAtomically({
          boardId,
          getBoard: (requestedBoardID) => client.getBoard(requestedBoardID, presentationID),
          loadImage,
          commit: ({ board, document }) => {
            if (!isCurrent() || board.selectedPresentationID !== presentationID) return;
            resetHistory(historyRef.current);
            updateState((value) => ({
              ...value,
              board,
              document: cloneEditorDocument(document),
              selectedKey: null,
              selectedKeys: [],
              dirty: false,
            }));
            committed = true;
          },
        });
        if (committed) {
          updateState((value) => ({ ...value, status: "Board surface loaded." }));
        }
      } catch (error: unknown) {
        if (!isCurrent()) return;
        updateState((value) => ({
          ...value,
          validation: errorMessage(error, "Could not load board surface."),
          status: "Could not load board surface. The current editor was kept.",
        }));
      }
    });
  }, [boardOperations, client, controller, isBusy, loadImage, updateState]);

  const saveBoard = useCallback(async (): Promise<void> => {
    if (isBusy() || stateRef.current.savingBoard) return;
    const current = stateRef.current;
    if (!current.board || !current.document) return;
    try {
      controller.validateEditorDocument(current.document);
    } catch (error: unknown) {
      updateState((value) => ({
        ...value,
        validation: errorMessage(error, "Hold document is invalid."),
        saveLoginUrl: null,
      }));
      return;
    }
    const boardId = current.board.boardId;
    const documentIdentity = current.document;
    const saveGeneration = operationGeneration;
    saveGenerationRef.current = saveGeneration;
    updateState((value) => ({ ...value, saveLoginUrl: null, savingBoard: true }));
    try {
      await boardOperations.perform(async ({ isCurrent }) => {
        try {
          await controller.saveBoardAtomically({
            boardId,
            document: cloneEditorDocument(documentIdentity),
            save: client.saveBoard,
            commit: ({ board, document }) => {
              if (!isCurrent()
                || stateRef.current.board?.boardId !== boardId
                || stateRef.current.document !== documentIdentity) return;
              updateState((latest) => {
                if (latest.board?.boardId !== boardId || latest.document !== documentIdentity) {
                  return latest;
                }
                resetHistory(historyRef.current);
                const selection = validSelection(document, latest.selectedKeys, latest.selectedKey);
                return {
                  ...latest,
                  board,
                  document: cloneEditorDocument(document),
                  ...selection,
                  dirty: false,
                  validation: "",
                  status: "Board saved.",
                };
              });
            },
          });
        } catch (error: unknown) {
          if (!isCurrent()) return;
          const loginUrl = saveLoginUrl(error);
          updateState((latest) => loginUrl ? {
            ...latest,
            validation: "",
            status: "Could not save board. Reauthenticate in a new tab, then return here and save again. Your editor changes were kept.",
            saveLoginUrl: loginUrl,
          } : {
            ...latest,
            validation: errorMessage(error, "Could not save board."),
            status: "Could not save board. Your editor changes were kept.",
          });
        }
      });
    } finally {
      if (operationsRef.current?.generation !== saveGeneration
        || saveGenerationRef.current !== saveGeneration) return;
      saveGenerationRef.current = null;
      updateState((value) => ({ ...value, savingBoard: false }));
    }
  }, [boardOperations, client, controller, isBusy, operationGeneration, updateState]);

  const clearEditor = useCallback((): void => {
    resetHistory(historyRef.current);
    updateState((current) => ({
      ...current,
      board: null,
      document: null,
      selectedKey: null,
      selectedKeys: [],
      dirty: false,
      saveLoginUrl: null,
    }));
  }, [updateState]);

  const reloadBoardsAfterBranch = useCallback(async (
    failurePrefix: string,
  ): Promise<void> => {
    try {
      await boardOperations.perform(async () => {
        const boards = await client.listBoards();
        updateState((current) => ({ ...current, boards, boardsError: "" }));
      });
    } catch (error: unknown) {
      updateState((current) => ({
        ...current,
        boards: [],
        boardsError: errorMessage(error, "Could not reload boards for the new branch."),
        validation: errorMessage(error, "Could not reload boards for the new branch."),
        status: `${failurePrefix} Could not reload boards.`,
      }));
    }
  }, [boardOperations, client, updateState]);

  const switchBranch = useCallback(async (branchName?: string): Promise<void> => {
    const branch = (branchName ?? stateRef.current.selectedBranch).trim();
    if (!branch || isBusy()) return;
    await gitOperations.perform(async () => {
      if (stateRef.current.dirty && !dialogs.confirm(
        "You have unsaved hold edits. Switching branches will keep those edits in memory only. Continue?",
      )) return;
      try {
        await client.switchBranch(branch);
      } catch (error: unknown) {
        updateState((current) => ({
          ...current,
          validation: errorMessage(error, "Could not switch branch."),
          status: "Could not switch branch.",
        }));
        return;
      }
      clearEditor();
      const refreshed = await refreshGitState();
      updateState((current) => ({
        ...current,
        ...(refreshed ? { validation: "" } : {}),
        status: refreshed
          ? `Switched to ${branch}.`
          : `Switched to ${branch}. Repository status unavailable.`,
      }));
      await reloadBoardsAfterBranch(`Switched to ${branch}.`);
    });
  }, [clearEditor, client, dialogs, gitOperations, isBusy, refreshGitState, reloadBoardsAfterBranch, updateState]);

  const createBranch = useCallback(async (branchName?: string): Promise<void> => {
    const branch = (branchName ?? stateRef.current.newBranchName).trim();
    if (!branch || isBusy()) return;
    await gitOperations.perform(async () => {
      if (stateRef.current.dirty && !dialogs.confirm(
        "You have unsaved hold edits. Creating a branch will keep those edits in memory only. Continue?",
      )) return;
      try {
        await client.createBranch(branch);
      } catch (error: unknown) {
        updateState((current) => ({
          ...current,
          validation: errorMessage(error, "Could not create branch."),
          status: "Could not create branch.",
        }));
        return;
      }
      clearEditor();
      updateState((current) => ({ ...current, newBranchName: "" }));
      const refreshed = await refreshGitState();
      updateState((current) => ({
        ...current,
        ...(refreshed ? { validation: "" } : {}),
        status: refreshed
          ? `Created and switched to ${branch}.`
          : `Created ${branch}. Repository status unavailable.`,
      }));
      await reloadBoardsAfterBranch(`Created ${branch}.`);
    });
  }, [clearEditor, client, dialogs, gitOperations, isBusy, refreshGitState, reloadBoardsAfterBranch, updateState]);

  const commitChanges = useCallback(async (): Promise<void> => {
    const message = stateRef.current.commitMessage.trim();
    if (!message) {
      updateState((current) => ({ ...current, validation: "Commit message is required." }));
      return;
    }
    if (isBusy() || stateRef.current.hostedStorage) return;
    await gitOperations.perform(async () => {
      try {
        const result = await client.commitBoardChanges(message);
        updateState((current) => ({ ...current, commitMessage: "" }));
        const label = `Committed ${result.commit.slice(0, 7) || "changes"}.`;
        const refreshed = await refreshGitState();
        updateState((current) => ({
          ...current,
          ...(refreshed ? { validation: "" } : {}),
          status: refreshed ? label : `${label} Repository status unavailable.`,
        }));
      } catch (error: unknown) {
        updateState((current) => ({
          ...current,
          validation: errorMessage(error, "Could not commit changes."),
          status: "Could not commit changes.",
        }));
      }
    });
  }, [client, gitOperations, isBusy, refreshGitState, updateState]);

  const pushBranch = useCallback(async (): Promise<void> => {
    if (isBusy() || stateRef.current.hostedStorage) return;
    const branch = stateRef.current.currentBranch ?? "current branch";
    await gitOperations.perform(async () => {
      try {
        await client.pushBranch();
        const label = `Pushed ${branch}.`;
        const refreshed = await refreshGitState();
        updateState((current) => ({
          ...current,
          ...(refreshed ? { validation: "" } : {}),
          status: refreshed ? label : `${label} Repository status unavailable.`,
        }));
      } catch (error: unknown) {
        updateState((current) => ({
          ...current,
          validation: errorMessage(error, "Could not push branch."),
          status: "Could not push branch.",
        }));
      }
    });
  }, [client, gitOperations, isBusy, refreshGitState, updateState]);

  const openPullRequest = useCallback(async (): Promise<void> => {
    if (isBusy()) return;
    const title = dialogs.prompt(
      "Pull request title:",
      `Update ${stateRef.current.currentBranch ?? "branch"}`,
    );
    if (!title) return;
    const body = dialogs.prompt("Pull request description (optional):", "") ?? "";
    await gitOperations.perform(async () => {
      try {
        const result = await client.openPullRequest({
          title: title.trim(),
          body: body.trim(),
          base: "main",
        });
        updateState((current) => ({
          ...current,
          validation: "",
          status: `Opened PR: ${result.url || "created"}`,
        }));
      } catch (error: unknown) {
        updateState((current) => ({
          ...current,
          validation: errorMessage(error, "Could not open pull request."),
          status: "Could not open pull request.",
        }));
      }
    });
  }, [client, dialogs, gitOperations, isBusy, updateState]);

  const replaceDocument = useCallback<WorkbenchActions["replaceDocument"]>((document, options = {}) => {
    const nextDocument = cloneEditorDocument(document);
    if (options.historySnapshot) recordHistory(historyRef.current, options.historySnapshot);
    const current = stateRef.current;
    const selection = validSelection(
      nextDocument,
      Object.hasOwn(options, "selectedKeys") ? options.selectedKeys ?? [] : current.selectedKeys,
      Object.hasOwn(options, "selectedKey") ? options.selectedKey ?? null : current.selectedKey,
    );
    updateState((current) => ({
      ...current,
      document: nextDocument,
      dirty: options.dirty ?? true,
      ...selection,
      validation: options.validation ?? "",
      status: options.status ?? current.status,
    }));
    return nextDocument;
  }, [updateState]);

  const editDocument = useCallback<WorkbenchActions["editDocument"]>((edit, options = {}) => {
    const current = stateRef.current;
    if (!current.document) return false;
    const nextDocument = cloneEditorDocument(current.document);
    try {
      edit(nextDocument);
      controller.validateEditorDocument(nextDocument);
    } catch (error: unknown) {
      updateState((latest) => ({
        ...latest,
        validation: errorMessage(error, options.failureMessage ?? "Contour is invalid."),
        status: options.failureStatus ?? latest.status,
      }));
      return false;
    }
    if (stateRef.current.document !== current.document) return true;
    replaceDocument(nextDocument, {
      ...options,
      historySnapshot: current.document,
      status: options.status ?? "Hold document updated. Save when ready.",
    });
    return true;
  }, [controller, replaceDocument, updateState]);

  const undoDocument = useCallback<WorkbenchActions["undoDocument"]>(() => {
    const current = stateRef.current;
    const snapshot = historyRef.current.undo.pop();
    if (!current.board || !current.document || !snapshot) {
      if (snapshot) historyRef.current.undo.push(snapshot);
      return false;
    }
    historyRef.current.redo.push(cloneEditorDocument(current.document));
    const document = cloneEditorDocument(snapshot);
    const selection = validSelection(document, current.selectedKeys, current.selectedKey);
    updateState((latest) => ({
      ...latest,
      document,
      ...selection,
      dirty: true,
      validation: "",
      status: "Undo. Save when ready.",
    }));
    return true;
  }, [updateState]);

  const redoDocument = useCallback<WorkbenchActions["redoDocument"]>(() => {
    const current = stateRef.current;
    const snapshot = historyRef.current.redo.pop();
    if (!current.board || !current.document || !snapshot) {
      if (snapshot) historyRef.current.redo.push(snapshot);
      return false;
    }
    historyRef.current.undo.push(cloneEditorDocument(current.document));
    const document = cloneEditorDocument(snapshot);
    const selection = validSelection(document, current.selectedKeys, current.selectedKey);
    updateState((latest) => ({
      ...latest,
      document,
      ...selection,
      dirty: true,
      validation: "",
      status: "Redo. Save when ready.",
    }));
    return true;
  }, [updateState]);

  useEffect(() => {
    if (boardOperations.isBusy || saveGenerationRef.current === operationGeneration) return;
    updateState((current) => (
      current.busyBoard || current.savingBoard
        ? { ...current, busyBoard: false, savingBoard: false }
        : current
    ));
  }, [boardOperations, operationGeneration, updateState]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      initializationGenerationRef.current += 1;
      for (const resolve of boardIdleWaitersRef.current) resolve();
      boardIdleWaitersRef.current.clear();
      for (const resolve of gitIdleWaitersRef.current) resolve();
      gitIdleWaitersRef.current.clear();
    };
  }, []);

  useEffect(() => {
    const generation = initializationGenerationRef.current + 1;
    initializationGenerationRef.current = generation;
    updateState((current) => ({ ...current, initialized: false }));
    const isActive = (): boolean => (
      mountedRef.current && initializationGenerationRef.current === generation
    );
    void (async () => {
      await refreshAuthState(isActive);
      if (!isActive()) return;
      await refreshInitialGitState(isActive);
      if (!isActive()) return;
      await reloadBoards(isActive, true);
      if (!isActive()) return;
      updateState((current) => ({ ...current, initialized: true }));
    })();
    return () => {
      if (initializationGenerationRef.current === generation) {
        initializationGenerationRef.current += 1;
      }
    };
  }, [refreshAuthState, refreshInitialGitState, reloadBoards, updateState]);

  const actions = useMemo<WorkbenchActions>(() => ({
    refreshBoards,
    selectBoard,
    saveBoard,
    refreshGit,
    setSelectedBranch(branchName) {
      updateState((current) => ({ ...current, selectedBranch: branchName }));
    },
    switchBranch,
    setNewBranchName(branchName) {
      updateState((current) => ({ ...current, newBranchName: branchName }));
    },
    createBranch,
    setCommitMessage(message) {
      updateState((current) => ({ ...current, commitMessage: message }));
    },
    commitChanges,
    pushBranch,
    openPullRequest,
    selectPresentation,
    selectHold(key, toggle = false) {
      updateState((current) => {
        if (!key || !current.document?.regions.some((region) => region.key === key)) {
          return { ...current, selectedKey: null, selectedKeys: [] };
        }
        if (!toggle) return { ...current, selectedKey: key, selectedKeys: [key] };
        const selectedKeys = current.selectedKeys.includes(key)
          ? current.selectedKeys.filter((selected) => selected !== key)
          : [...current.selectedKeys, key];
        return {
          ...current,
          selectedKeys,
          selectedKey: selectedKeys.includes(key) ? key : selectedKeys.at(-1) ?? null,
        };
      });
    },
    setRotationDegrees(value) {
      updateState((current) => ({ ...current, rotationDegrees: value }));
    },
    replaceDocument,
    editDocument,
    undoDocument,
    redoDocument,
    updateDocument(document, status = "Hold document updated. Save when ready.") {
      replaceDocument(document, { status });
    },
  }), [
    commitChanges,
    createBranch,
    openPullRequest,
    pushBranch,
    refreshBoards,
    refreshGit,
    replaceDocument,
    editDocument,
    redoDocument,
    saveBoard,
    selectPresentation,
    selectBoard,
    switchBranch,
    undoDocument,
    updateState,
  ]);

  return { state, actions };
}
