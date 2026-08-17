(() => {
  "use strict";

  const client = globalThis.HoldWorkbenchClient;
  const {
    createBoardOperationCoordinator,
    loadBoardAtomically,
    saveBoardAtomically,
    validateEditorDocument,
  } = globalThis.HoldWorkbenchController;
  const svgNS = "http://www.w3.org/2000/svg";
  const TYPE_COLORS = { jug: "#ff754f", sloper: "#32bbc1", edge: "#9a6cf2", pocket: "#ee4d97", pinch: "#f2c94c" };

  const state = {
    boards: [],
    board: null,
    document: null,
    image: null,
    selectedKey: null,
    branches: [],
    currentBranch: null,
    hasUncommittedChanges: false,
    dirty: false,
    busyBoard: false,
    busyGit: false,
    authenticated: false,
    username: null,
  };

  const el = Object.fromEntries([
    "board-list",
    "boards-error",
    "refresh-boards-button",
    "save-button",
    "save-state",
    "board-status",
    "board-name",
    "editor-svg",
    "board-image",
    "hold-overlay",
    "empty-state",
    "editor-status",
    "validation-panel",
    "validation-list",
    "hold-heading",
    "hold-empty",
    "hold-form",
    "hold-key",
    "hold-path",
    "apply-hold-button",
    "git-auth-status",
    "git-status",
    "git-branch-select",
    "git-refresh-button",
    "git-switch-button",
    "git-commit-message",
    "git-commit-button",
    "git-push-button",
    "git-open-pr-button",
  ].map((id) => [id, document.getElementById(id)]));

  const boardOperations = createBoardOperationCoordinator({
    onBusyChange: (busy) => {
      state.busyBoard = busy;
      render();
    },
  });

  const gitOperations = createBoardOperationCoordinator({
    onBusyChange: (busy) => {
      state.busyGit = busy;
      render();
    },
  });

  function isBusy() {
    return state.busyBoard || state.busyGit;
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function selectedHold() {
    return state.document?.regions.find((region) => region.key === state.selectedKey) || null;
  }

  function setStatus(message) {
    el["editor-status"].textContent = message;
  }

  function setValidation(error = "") {
    el["validation-list"].replaceChildren();
    el["validation-panel"].classList.toggle("hidden", !error);
    if (!error) return;
    const item = document.createElement("li");
    item.textContent = error;
    el["validation-list"].append(item);
  }

  function renderSaveState() {
    el["save-button"].disabled = !state.board || isBusy();
    el["refresh-boards-button"].disabled = isBusy();
    el["save-state"].textContent = !state.board
      ? "No board selected"
      : isBusy()
        ? "Working…"
        : state.dirty
          ? "Unsaved changes"
          : "Saved";

    el["git-status"].textContent = state.currentBranch
      ? `${state.currentBranch}${state.hasUncommittedChanges ? " (uncommitted changes)" : ""}`
      : "Repository status unavailable";

    el["git-refresh-button"].disabled = isBusy();
    el["git-branch-select"].disabled = isBusy() || state.branches.length === 0;
    el["git-switch-button"].disabled = isBusy() || !state.currentBranch || !el["git-branch-select"].value || el["git-branch-select"].value === state.currentBranch;
    el["git-commit-message"].disabled = isBusy();
    el["git-commit-button"].disabled = isBusy() || !state.currentBranch;
    el["git-push-button"].disabled = isBusy() || !state.currentBranch;
    el["git-open-pr-button"].disabled = isBusy() || !state.currentBranch;

    el["board-status"].textContent = state.currentBranch
      ? `Current branch: ${state.currentBranch}`
      : "No branch detected";
  }

  function syncBranches(activeBranch) {
    el["git-branch-select"].replaceChildren();
    const ordered = [...state.branches].sort();
    if (ordered.length === 0) {
      const fallback = document.createElement("option");
      fallback.value = "";
      fallback.textContent = "No branches detected";
      el["git-branch-select"].append(fallback);
      return;
    }
    for (const branch of ordered) {
      const option = document.createElement("option");
      option.value = branch;
      option.textContent = branch;
      option.selected = branch === activeBranch;
      el["git-branch-select"].append(option);
    }
    if (activeBranch && ordered.includes(activeBranch)) {
      el["git-branch-select"].value = activeBranch;
    }
  }

  function renderBoards() {
    el["board-list"].replaceChildren();
    for (const board of state.boards) {
      const button = document.createElement("button");
      const title = document.createElement("span");
      const detail = document.createElement("small");
      button.type = "button";
      button.className = `region-item${state.board?.boardId === board.boardId ? " selected" : ""}`;
      button.disabled = isBusy();
      title.className = "region-key";
      title.textContent = board.displayName;
      detail.className = "region-type";
      detail.textContent = `${board.holdCount} holds`;
      button.append(title, detail);
      button.addEventListener("click", () => {
        if (!isBusy()) void selectBoard(board.boardId);
      });
      el["board-list"].append(button);
    }
  }

  function renderEditor() {
    const documentValue = state.document;
    const selected = selectedHold();
    el["empty-state"].classList.toggle("hidden", Boolean(documentValue));
    el["hold-overlay"].replaceChildren();
    if (!documentValue) {
      el["board-name"].textContent = "No board selected";
      el["board-image"].removeAttribute("href");
      return;
    }
    const { width, height } = documentValue.canvas;
    el["board-name"].textContent = state.board.displayName;
    el["editor-svg"].setAttribute("viewBox", `0 0 ${width} ${height}`);
    el["editor-svg"].setAttribute("width", String(width));
    el["editor-svg"].setAttribute("height", String(height));
    el["board-image"].setAttribute("href", state.board.imageUrl);
    el["board-image"].setAttribute("width", String(width));
    el["board-image"].setAttribute("height", String(height));
    for (const hold of documentValue.regions) {
      const shape = document.createElementNS(svgNS, "path");
      shape.setAttribute("d", hold.displayPath);
      shape.setAttribute("fill", TYPE_COLORS[hold.type] || "#ff754f");
      shape.setAttribute("fill-opacity", hold.key === selected?.key ? "0.58" : "0.3");
      shape.setAttribute("stroke", hold.key === selected?.key ? "#fff7dc" : TYPE_COLORS[hold.type] || "#ff754f");
      shape.setAttribute("stroke-width", hold.key === selected?.key ? "2.2" : "1.4");
      shape.classList.add("region-shape");
      shape.addEventListener("click", () => {
        state.selectedKey = hold.key;
        render();
      });
      el["hold-overlay"].append(shape);
    }
  }

  function renderInspector() {
    const hold = selectedHold();
    el["apply-hold-button"].disabled = isBusy() || !hold;
    el["hold-path"].disabled = isBusy() || !hold;
    el["hold-empty"].classList.toggle("hidden", Boolean(hold));
    el["hold-form"].classList.toggle("hidden", !hold);
    el["hold-heading"].textContent = hold ? hold.key : "No selection";
    if (!hold) return;
    el["hold-key"].value = hold.key;
    el["hold-path"].value = hold.displayPath;
  }

  function render() {
    renderBoards();
    renderEditor();
    renderInspector();
    renderSaveState();
  }

  function loadImage(href) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error("Board image is unavailable"));
      image.src = href;
    });
  }

  async function refreshBoards() {
    if (state.busyBoard || state.busyGit) return;
    el["boards-error"].classList.add("hidden");
    await boardOperations.perform(async () => {
      try {
        state.boards = await client.listBoards();
        renderBoards();
        setStatus("Boards loaded.");
      } catch (error) {
        el["boards-error"].textContent = error.message || "Could not load boards.";
        el["boards-error"].classList.remove("hidden");
        setStatus("Could not load boards.");
      }
    });
  }

  async function refreshGitState() {
    try {
      const status = await client.getGitStatus();
      const branches = Array.isArray(status.branches) ? status.branches : [];
      state.currentBranch = status.currentBranch || null;
      state.branches = branches;
      state.hasUncommittedChanges = Boolean(status.dirty);
      syncBranches(state.currentBranch);
    } catch (error) {
      state.branches = [];
      state.currentBranch = null;
      state.hasUncommittedChanges = false;
      syncBranches(null);
      console.error(error);
    }
  }

  async function refreshAuthState() {
    try {
      const status = await client.getAuthStatus();
      state.authenticated = Boolean(status.authenticated);
      state.username = status.username || null;
    } catch {
      state.authenticated = false;
      state.username = null;
    }
    renderAuthState();
  }

  function renderAuthState() {
    if (state.authenticated && state.username) {
      el["git-auth-status"].textContent = `Logged in as ${state.username}`;
    } else {
      el["git-auth-status"].innerHTML = '<a href="/auth/login">Log in with GitHub</a>';
    }
  }

  async function selectBoard(boardId) {
    if (isBusy()) return;
    setValidation();
    await boardOperations.perform(async ({ isCurrent }) => {
      let committed = false;
      try {
        await loadBoardAtomically({
          boardId,
          getBoard: client.getBoard,
          loadImage,
          commit: ({ board, document: documentValue, image }) => {
            if (!isCurrent()) return;
            state.board = board;
            state.document = clone(documentValue);
            state.image = image;
            state.selectedKey = null;
            state.dirty = false;
            committed = true;
          },
        });
        if (!committed) return;
        setStatus("Board loaded.");
        render();
      } catch (error) {
        if (!isCurrent()) return;
        setValidation(error.message || "Could not load board.");
        setStatus("Could not load board. The current editor was kept.");
      }
    });
  }

  function applyHold(event) {
    event.preventDefault();
    if (isBusy()) return;
    const hold = selectedHold();
    if (!hold) return;
    const candidate = clone(state.document);
    candidate.regions.find((region) => region.key === hold.key).displayPath = el["hold-path"].value.trim();
    try {
      validateEditorDocument(candidate);
      state.document = candidate;
      state.dirty = true;
      setValidation();
      setStatus("Contour updated. Save when ready.");
      render();
    } catch (error) {
      setValidation(error.message || "Contour is invalid.");
    }
  }

  async function saveBoard() {
    if (isBusy() || !state.board || !state.document) return;
    try {
      validateEditorDocument(state.document);
    } catch (error) {
      setValidation(error.message || "Hold document is invalid.");
      return;
    }
    const boardId = state.board.boardId;
    const documentValue = state.document;
    await boardOperations.perform(async ({ isCurrent }) => {
      let committed = false;
      try {
        await saveBoardAtomically({
          boardId,
          document: clone(documentValue),
          save: client.saveBoard,
          commit: ({ board, document: savedDocument }) => {
            if (!isCurrent() || state.board?.boardId !== boardId || state.document !== documentValue) return;
            state.board = board;
            state.document = clone(savedDocument);
            state.dirty = false;
            committed = true;
          },
        });
        if (!committed) return;
        setValidation();
        setStatus("Board saved.");
        render();
      } catch (error) {
        if (!isCurrent()) return;
        setValidation(error.message || "Could not save board.");
        setStatus("Could not save board. Your editor changes were kept.");
      }
    });
  }

  async function switchBranch() {
    const branch = el["git-branch-select"].value;
    if (!branch || isBusy()) return;
    await gitOperations.perform(async () => {
      if (state.dirty) {
        const proceed = window.confirm("You have unsaved hold edits. Switching branches will keep those edits in memory only. Continue?");
        if (!proceed) return;
      }
      try {
        await client.switchBranch(branch);
        state.board = null;
        state.document = null;
        state.image = null;
        state.selectedKey = null;
        state.dirty = false;
        await boardOperations.perform(async () => {
          state.boards = await client.listBoards();
        });
        await refreshGitState();
        setValidation("");
        setStatus(`Switched to ${branch}.`);
        render();
      } catch (error) {
        setValidation(error.message || "Could not switch branch.");
        setStatus("Could not switch branch.");
      }
    });
  }

  async function commitChanges() {
    const message = el["git-commit-message"].value.trim();
    if (!message) {
      setValidation("Commit message is required.");
      return;
    }
    if (isBusy()) return;
    await gitOperations.perform(async () => {
      try {
        const result = await client.commitBoardChanges(message);
        el["git-commit-message"].value = "";
        await refreshGitState();
        setValidation("");
        setStatus(`Committed ${result.commit?.slice(0, 7) || "changes"}.`);
      } catch (error) {
        setValidation(error.message || "Could not commit changes.");
        setStatus("Could not commit changes.");
      }
    });
  }

  async function pushBranch() {
    if (isBusy()) return;
    await gitOperations.perform(async () => {
      try {
        await client.pushBranch();
        await refreshGitState();
        setValidation("");
        setStatus(`Pushed ${state.currentBranch || "current branch"}.`);
      } catch (error) {
        setValidation(error.message || "Could not push branch.");
        setStatus("Could not push branch.");
      }
    });
  }

  async function openPullRequest() {
    if (isBusy()) return;
    const defaultTitle = `Update ${state.currentBranch || "branch"}`;
    const title = window.prompt("Pull request title:", defaultTitle);
    if (!title) return;
    const bodyText = window.prompt("Pull request description (optional):", "") || "";
    await gitOperations.perform(async () => {
      try {
        const result = await client.openPullRequest({
          title: title.trim(),
          body: bodyText.trim(),
          base: "main",
        });
        setValidation("");
        setStatus(`Opened PR: ${result.url || "created"}`);
      } catch (error) {
        setValidation(error.message || "Could not open pull request.");
        setStatus("Could not open pull request.");
      }
    });
  }

  el["refresh-boards-button"].addEventListener("click", () => { void refreshBoards(); });
  el["hold-form"].addEventListener("submit", applyHold);
  el["save-button"].addEventListener("click", () => { void saveBoard(); });
  el["git-refresh-button"].addEventListener("click", () => {
    void gitOperations.perform(async () => {
      await refreshGitState();
    });
  });
  el["git-switch-button"].addEventListener("click", () => { void switchBranch(); });
  el["git-commit-button"].addEventListener("click", () => { void commitChanges(); });
  el["git-push-button"].addEventListener("click", () => { void pushBranch(); });
  el["git-open-pr-button"].addEventListener("click", () => { void openPullRequest(); });

  void (async () => {
    await refreshAuthState();
    await gitOperations.perform(async () => {
      await refreshGitState();
    });
    await refreshBoards();
  })();
})();
