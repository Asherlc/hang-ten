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
  branches: [],
  currentBranch: null,
  selectedBranch: "",
  gitStatusKnown: false,
  hasUncommittedChanges: false,
  dirty: false,
  busyBoard: false,
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

export function useWorkbench(dependencies: WorkbenchDependencies): UseWorkbenchResult {
  const { client, controller, dialogs, runtime } = dependencies;
  const [state, setState] = useState<WorkbenchState>(INITIAL_STATE);
  const stateRef = useRef(state);
  const mountedRef = useRef(true);
  const initializationGenerationRef = useRef(0);
  const boardIdleWaitersRef = useRef(new Set<() => void>());
  const gitIdleWaitersRef = useRef(new Set<() => void>());

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
  const { board: boardOperations, git: gitOperations } = operationsRef.current;

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
    updateState((current) => ({ ...current, validation: "" }));
    await boardOperations.perform(async ({ isCurrent }) => {
      let committed = false;
      try {
        await controller.loadBoardAtomically({
          boardId,
          getBoard: client.getBoard,
          loadImage,
          commit: ({ board, document }) => {
            if (!isCurrent()) return;
            updateState((current) => ({
              ...current,
              board,
              document: cloneEditorDocument(document),
              selectedKey: null,
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

  const saveBoard = useCallback(async (): Promise<void> => {
    if (isBusy()) return;
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
    updateState((value) => ({ ...value, saveLoginUrl: null }));
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
              return {
                ...latest,
                board,
                document: cloneEditorDocument(document),
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
  }, [boardOperations, client, controller, isBusy, updateState]);

  const clearEditor = useCallback((): void => {
    updateState((current) => ({
      ...current,
      board: null,
      document: null,
      selectedKey: null,
      dirty: false,
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
    updateState((current) => ({
      ...current,
      document: nextDocument,
      dirty: options.dirty ?? true,
      ...(Object.hasOwn(options, "selectedKey") ? { selectedKey: options.selectedKey ?? null } : {}),
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
    updateState((latest) => {
      if (latest.document !== current.document) return latest;
      return {
        ...latest,
        document: nextDocument,
        dirty: options.dirty ?? true,
        ...(Object.hasOwn(options, "selectedKey") ? { selectedKey: options.selectedKey ?? null } : {}),
        validation: options.validation ?? "",
        status: options.status ?? "Hold document updated. Save when ready.",
      };
    });
    return true;
  }, [controller, updateState]);

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
    selectHold(key) {
      updateState((current) => ({ ...current, selectedKey: key }));
    },
    setRotationDegrees(value) {
      updateState((current) => ({ ...current, rotationDegrees: value }));
    },
    replaceDocument,
    editDocument,
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
    saveBoard,
    selectBoard,
    switchBranch,
    updateState,
  ]);

  return { state, actions };
}
