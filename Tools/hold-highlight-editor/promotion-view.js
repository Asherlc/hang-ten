(function exposePromotionView(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldPromotionView = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const PROFILE_FIELDS = Object.freeze([
    Object.freeze({ key: "boardID", label: "iOS board ID", note: "Canonical iOS identifier; confirm it against the approved board package.", type: "text" }),
    Object.freeze({ key: "manufacturer", label: "Manufacturer", note: "Use the manufacturer product page or packaging as evidence.", type: "text" }),
    Object.freeze({ key: "name", label: "Display name", note: "Use the exact product name from the evidence source.", type: "text" }),
    Object.freeze({ key: "subtitle", label: "Subtitle", note: "Write only evidence-backed product context; do not infer features from the photo.", type: "text" }),
    Object.freeze({ key: "dimensions", label: "Dimensions", note: "Transcribe the manufacturer’s published dimensions.", type: "text" }),
    Object.freeze({ key: "aspectRatio", label: "Aspect ratio", note: "Use the measured or published board aspect ratio.", type: "number" }),
    Object.freeze({ key: "productURL", label: "Product URL", note: "Link the manufacturer evidence used for this profile.", type: "url" }),
  ]);
  const GROUPS = Object.freeze([
    Object.freeze({ heading: "Metadata", match: (path) => path === "HangTen/Models/TrainingModels.swift" }),
    Object.freeze({ heading: "Geometry", match: (path) => path.startsWith("HangTen/Views/") }),
    Object.freeze({ heading: "Plans", match: (path) => path === "HangTen/Models/PlanStorage.swift" || path.startsWith("HangTen/Resources/") }),
  ]);

  function blankProfile() {
    return {
      schemaVersion: 1,
      boardID: "",
      manufacturer: "",
      name: "",
      subtitle: "",
      dimensions: "",
      aspectRatio: "",
      productURL: "",
    };
  }

  function normalizedProfile(profile) {
    const next = { ...blankProfile(), ...(profile || {}) };
    next.schemaVersion = 1;
    for (const { key } of PROFILE_FIELDS) {
      if (key === "aspectRatio") continue;
      next[key] = typeof next[key] === "string" ? next[key].trim() : "";
    }
    const ratio = typeof next.aspectRatio === "string" ? next.aspectRatio.trim() : next.aspectRatio;
    if (ratio === "") next.aspectRatio = "";
    else {
      const numericRatio = Number(ratio);
      next.aspectRatio = Number.isFinite(numericRatio) ? numericRatio : ratio;
    }
    return next;
  }

  function isPromotionProfileComplete(profile) {
    const value = normalizedProfile(profile);
    return PROFILE_FIELDS.every(({ key }) => (
      key === "aspectRatio"
        ? Number.isFinite(value.aspectRatio) && value.aspectRatio > 0
        : typeof value[key] === "string" && value[key].length > 0
    ));
  }

  function profileSignature(profile) {
    return JSON.stringify(normalizedProfile(profile));
  }

  function fileGroup(path) {
    return GROUPS.find((group) => group.match(path)) || GROUPS[0];
  }

  function groupPromotionFiles(files = [], issues = []) {
    const groups = GROUPS.map(({ heading }) => ({ heading, files: [] }));
    const filesByPath = new Map();
    for (const file of Array.isArray(files) ? files : []) {
      if (!file || typeof file.path !== "string") continue;
      const copy = { ...file, issues: [] };
      const group = groups.find(({ heading }) => heading === fileGroup(file.path).heading);
      group.files.push(copy);
      filesByPath.set(file.path, copy);
    }
    const unassignedIssues = [];
    for (const issue of Array.isArray(issues) ? issues : []) {
      const copy = { ...issue };
      const target = typeof copy.path === "string" ? filesByPath.get(copy.path) : null;
      if (target) target.issues.push(copy);
      else unassignedIssues.push(copy);
    }
    Object.defineProperty(groups, "unassignedIssues", { value: unassignedIssues, enumerable: false });
    return groups;
  }

  function promotionStatus(preview, { expectedRevisionId = null } = {}) {
    if (!preview) return { status: "empty", label: "No preview", message: "Generate a preview before saving local native files." };
    if (expectedRevisionId && preview.revisionId !== expectedRevisionId) {
      return { status: "stale", label: "Preview is stale", message: "The active board revision changed after this preview." };
    }
    if (typeof preview.previewToken !== "string" || !preview.previewToken) {
      return { status: "stale", label: "Preview is stale", message: "This preview is missing its required save token." };
    }
    if (Array.isArray(preview.issues) && preview.issues.length) {
      return { status: "blocked", label: "Blocked by issues", message: "Resolve each validation or target-file issue before saving." };
    }
    return { status: "ready", label: "Ready to save locally", message: "The displayed diff is bound to the active revision and main baseline." };
  }

  function saveActionState({
    preview = null,
    busy = false,
    expectedRevisionId = null,
    profileReady = true,
    boardReady = true,
    profileChanged = false,
  } = {}) {
    if (busy) return { disabled: true, reason: "A promotion job is already active." };
    if (!boardReady) return { disabled: true, reason: "The active board must be complete and approved before promotion." };
    if (!profileReady) return { disabled: true, reason: "Complete the explicit iOS promotion profile before saving." };
    if (profileChanged) return { disabled: true, reason: "The promotion profile changed; generate a new preview." };
    const status = promotionStatus(preview, { expectedRevisionId });
    return status.status === "ready"
      ? { disabled: false, reason: "" }
      : { disabled: true, reason: status.message };
  }

  function activeContext(getSuiteState) {
    const suite = getSuiteState?.() || {};
    const board = suite.activeBoard || null;
    const revisionId = suite.activeRevision || board?.revisionId || null;
    return { suite, board, revisionId };
  }

  function contextKey({ board, revisionId }) {
    return board?.boardId && revisionId ? JSON.stringify([board.boardId, revisionId]) : null;
  }

  function boardIsReady(board) {
    return board?.state === "complete" && board?.staleFromStage == null;
  }

  function boundPreview(value, context) {
    if (!value || typeof value !== "object") return null;
    return {
      ...value,
      boardID: value.boardID || value.boardId,
      boardId: context.board?.boardId,
      revisionId: value.revisionId || context.revisionId,
    };
  }

  function createPromotionController({ client, getSuiteState, onPromotion = () => {}, render = () => {} } = {}) {
    if (!client || typeof client.getPromotionPreview !== "function" || typeof client.previewPromotion !== "function" || typeof client.savePromotion !== "function") {
      throw new TypeError("promotion client methods are required");
    }
    if (typeof getSuiteState !== "function") throw new TypeError("getSuiteState must be a function");

    let operation = 0;
    let state = {
      contextKey: contextKey(activeContext(getSuiteState)),
      profile: blankProfile(),
      preview: null,
      previewProfileSignature: null,
      busy: false,
      saved: false,
      error: "",
    };

    function emit() { render(getState()); }

    function resetContext(context) {
      operation += 1;
      state = {
        contextKey: contextKey(context),
        profile: blankProfile(),
        preview: null,
        previewProfileSignature: null,
        busy: false,
        saved: false,
        error: "",
      };
    }

    function synchronizeContext() {
      const context = activeContext(getSuiteState);
      if (state.contextKey !== contextKey(context)) resetContext(context);
      return context;
    }

    function getState() {
      synchronizeContext();
      return Object.freeze({ ...state, profile: { ...state.profile } });
    }

    function contextIsCurrent(context, token) {
      const current = activeContext(getSuiteState);
      return token === operation
        && contextKey(current) === contextKey(context)
        && state.contextKey === contextKey(context);
    }

    function saveState() {
      const { board, revisionId } = synchronizeContext();
      return saveActionState({
        preview: state.preview,
        busy: state.busy,
        expectedRevisionId: revisionId,
        profileReady: isPromotionProfileComplete(state.profile),
        boardReady: boardIsReady(board),
        profileChanged: state.previewProfileSignature != null && state.previewProfileSignature !== profileSignature(state.profile),
      });
    }

    function setProfile(profile) {
      synchronizeContext();
      state = { ...state, profile: normalizedProfile(profile), saved: false, error: "" };
      emit();
      return getState();
    }

    function setProfileField(field, value) {
      if (!PROFILE_FIELDS.some(({ key }) => key === field)) throw new RangeError(`Unknown promotion profile field: ${String(field)}`);
      synchronizeContext();
      return setProfile({ ...state.profile, [field]: value });
    }

    function replacePreview(value) {
      const context = synchronizeContext();
      const preview = boundPreview(value, context);
      state = {
        ...state,
        preview,
        previewProfileSignature: preview ? profileSignature(state.profile) : null,
        saved: Boolean(preview?.saved),
        error: "",
      };
      emit();
      return getState();
    }

    function setError(message) {
      synchronizeContext();
      state = { ...state, error: message, busy: false };
      emit();
      return getState();
    }

    async function refreshPreview() {
      const context = synchronizeContext();
      if (!context.board || !context.revisionId) return setError("Choose an active board revision before refreshing promotion preview.");
      const token = ++operation;
      state = { ...state, busy: true, error: "" };
      emit();
      try {
        const refreshed = boundPreview(await client.getPromotionPreview(context.board.boardId, context.revisionId), context);
        if (!contextIsCurrent(context, token)) return getState();
        if (!refreshed) {
          state = { ...state, busy: false, error: "No saved preview exists for this active revision." };
          emit();
          return getState();
        }
        state = {
          ...state,
          busy: false,
          preview: refreshed,
          previewProfileSignature: profileSignature(state.profile),
          saved: Boolean(refreshed.saved),
          error: "",
        };
        onPromotion(refreshed);
        emit();
        return getState();
      } catch (error) {
        if (!contextIsCurrent(context, token)) return getState();
        return setError(error?.message || "Could not refresh promotion preview.");
      }
    }

    async function generatePreview() {
      const context = synchronizeContext();
      if (!boardIsReady(context.board)) return setError("The active board must be complete and approved before promotion.");
      if (!isPromotionProfileComplete(state.profile)) return setError("Complete the explicit iOS promotion profile before generating a preview.");
      const token = ++operation;
      const profile = normalizedProfile(state.profile);
      state = { ...state, busy: true, error: "", saved: false };
      emit();
      try {
        const preview = boundPreview(
          await client.previewPromotion(context.board.boardId, context.revisionId, profile, "main"),
          context,
        );
        if (!contextIsCurrent(context, token)) return getState();
        state = {
          ...state,
          busy: false,
          preview,
          previewProfileSignature: profileSignature(profile),
          saved: false,
          error: "",
        };
        onPromotion(preview);
        emit();
        return getState();
      } catch (error) {
        if (!contextIsCurrent(context, token)) return getState();
        return setError(error?.message || "Could not generate promotion preview.");
      }
    }

    async function saveLocally() {
      const action = saveState();
      if (action.disabled) return setError(action.reason);
      const context = synchronizeContext();
      const token = ++operation;
      const profile = normalizedProfile(state.profile);
      state = { ...state, busy: true, error: "" };
      emit();
      try {
        const refreshed = boundPreview(await client.getPromotionPreview(context.board.boardId, context.revisionId), context);
        if (!contextIsCurrent(context, token)) return getState();
        if (refreshed?.previewToken !== state.preview?.previewToken) {
          state = {
            ...state,
            busy: false,
            preview: refreshed || state.preview,
            previewProfileSignature: profileSignature(profile),
            saved: false,
            error: "The promotion preview changed; review the refreshed diff before saving.",
          };
          emit();
          return getState();
        }
        const refreshedState = saveActionState({
          preview: refreshed,
          expectedRevisionId: context.revisionId,
          profileReady: isPromotionProfileComplete(profile),
          boardReady: boardIsReady(context.board),
          profileChanged: state.previewProfileSignature !== profileSignature(profile),
        });
        if (refreshedState.disabled) {
          state = { ...state, busy: false, preview: refreshed || state.preview, error: refreshedState.reason };
          emit();
          return getState();
        }
        state = { ...state, preview: refreshed, busy: true };
        emit();
        const result = await client.savePromotion(context.board.boardId, context.revisionId, profile, refreshed.previewToken);
        if (!contextIsCurrent(context, token)) return getState();
        const saved = result?.saved === true;
        const promoted = saved ? { ...refreshed, saved: true } : refreshed;
        state = { ...state, preview: promoted, busy: false, saved, error: saved ? "" : "The server did not confirm the local save." };
        if (saved) onPromotion(promoted);
        emit();
        return getState();
      } catch (error) {
        if (!contextIsCurrent(context, token)) return getState();
        state = { ...state, busy: false, error: error?.message || "Could not save promotion locally." };
        emit();
        return getState();
      }
    }

    return Object.freeze({
      getState,
      setProfile,
      setProfileField,
      replacePreview,
      saveState,
      refreshPreview,
      generatePreview,
      saveLocally,
    });
  }

  function appendText(parent, tag, text, className = "") {
    const node = parent.ownerDocument.createElement(tag);
    if (className) node.className = className;
    node.textContent = text;
    parent.appendChild(node);
    return node;
  }

  function renderPromotionView(root, { suite, promotion } = {}) {
    if (!root) return;
    const board = suite?.activeBoard || null;
    const expectedRevisionId = suite?.activeRevision || board?.revisionId || null;
    const view = promotion || {};
    const matchesContext = view.contextKey === contextKey({ board, revisionId: expectedRevisionId });
    const preview = matchesContext
      && view.preview?.boardId === board?.boardId
      && view.preview?.revisionId === expectedRevisionId
      ? view.preview
      : null;
    const saved = matchesContext && preview && view.saved;
    const profile = normalizedProfile(view.profile);
    const ready = boardIsReady(board);
    const profileReady = isPromotionProfileComplete(profile);
    const profileChanged = view.previewProfileSignature != null && view.previewProfileSignature !== profileSignature(profile);
    const action = saveActionState({ preview, busy: view.busy, expectedRevisionId, profileReady, boardReady: ready, profileChanged });
    const status = promotionStatus(preview, { expectedRevisionId });

    const identity = root.querySelector("#promotion-identity");
    const readiness = root.querySelector("#promotion-readiness");
    const statusNode = root.querySelector("#promotion-status");
    const error = root.querySelector("#promotion-error");
    if (identity) identity.textContent = board ? `${board.productName || board.boardId} · Revision ${expectedRevisionId} · baseline main` : "Choose one active board revision to begin promotion.";
    if (readiness) readiness.textContent = ready ? "Ready: Stage 4 is complete and approved." : "Blocked: complete and approve Stage 4 in Onboard before promotion.";
    if (statusNode) {
      statusNode.textContent = saved ? "Saved locally" : status.label;
      statusNode.className = `promotion-status ${saved ? "saved" : status.status}`;
    }
    if (error) {
      error.textContent = view.error || "";
      error.classList.toggle("hidden", !view.error);
    }
    PROFILE_FIELDS.forEach(({ key }) => {
      const input = root.querySelector(`[data-promotion-field="${key}"]`);
      if (!input) return;
      if (root.ownerDocument.activeElement !== input) input.value = String(profile[key] ?? "");
      input.disabled = Boolean(view.busy);
    });
    const previewButton = root.querySelector("#promotion-preview-button");
    const refreshButton = root.querySelector("#promotion-refresh-button");
    const saveButton = root.querySelector("#promotion-save-button");
    if (previewButton) previewButton.disabled = Boolean(view.busy) || !ready || !profileReady;
    if (refreshButton) refreshButton.disabled = Boolean(view.busy) || !board || !expectedRevisionId;
    if (saveButton) {
      saveButton.disabled = action.disabled;
      saveButton.title = action.reason;
      saveButton.textContent = view.busy ? "Working…" : saved ? "Saved locally" : "Save locally";
    }

    const issueList = root.querySelector("#promotion-issues");
    if (issueList) {
      issueList.replaceChildren();
      const issues = preview?.issues || [];
      if (!issues.length) appendText(issueList, "p", preview ? "No conflict or validation issues were reported." : "Preview issues will appear here.");
      issues.forEach((issue) => {
        const line = appendText(issueList, "p", "", "promotion-issue");
        appendText(line, "strong", issue.path || "Package");
        line.appendChild(root.ownerDocument.createTextNode(` · ${issue.message || issue.code || "Promotion issue"}`));
      });
    }

    const diffGroups = root.querySelector("#promotion-diff-groups");
    if (diffGroups) {
      diffGroups.replaceChildren();
      if (!preview) appendText(diffGroups, "p", "Generate a preview to review the exact local Swift and plan changes.", "promotion-empty");
      else groupPromotionFiles(preview.files, preview.issues).forEach((group) => {
        const section = root.ownerDocument.createElement("section");
        section.className = "promotion-diff-group";
        appendText(section, "h3", group.heading);
        if (!group.files.length) appendText(section, "p", "No changes in this group.");
        group.files.forEach((file) => {
          const card = root.ownerDocument.createElement("article");
          card.className = "promotion-file-diff";
          appendText(card, "h4", file.path);
          file.issues.forEach((issue) => appendText(card, "p", issue.message || issue.code || "Promotion issue", "promotion-issue"));
          appendText(card, "pre", file.unifiedDiff || "No textual changes.");
          section.appendChild(card);
        });
        diffGroups.appendChild(section);
      });
    }
  }

  return Object.freeze({
    PROFILE_FIELDS,
    groupPromotionFiles,
    promotionStatus,
    saveActionState,
    isPromotionProfileComplete,
    createPromotionController,
    renderPromotionView,
  });
}));
