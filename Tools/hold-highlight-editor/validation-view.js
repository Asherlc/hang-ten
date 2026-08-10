(function exposeValidationView(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldValidationView = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const CHECKS = Object.freeze([
    Object.freeze({ checkId: "package-readiness", label: "Package integrity", fallback: "Package readiness has not run." }),
    Object.freeze({ checkId: "hold-id-parity", label: "Hold-ID parity", fallback: "Hold-ID parity has not run." }),
    Object.freeze({ checkId: "semantic-routine-resolution", label: "Semantic routine resolution", fallback: "Semantic routine resolution has not run." }),
    Object.freeze({ checkId: "plan-library", label: "Plan library freshness", fallback: "Plan library freshness has not run." }),
    Object.freeze({ checkId: "promotion-status", label: "Promotion status", fallback: "No local iOS promotion has been saved for this revision." }),
  ]);
  const STATUS_LABELS = Object.freeze({
    passed: "Passed",
    failed: "Failed",
    stale: "Stale",
    not_run: "Not run",
  });

  function checkStatus(status) {
    return STATUS_LABELS[status] ? status : "not_run";
  }

  function promotionCheck(promotion, revisionId) {
    if (promotion?.revisionId && promotion.revisionId !== revisionId) {
      return { checkId: "promotion-status", status: "stale", message: "The promotion result belongs to a different board revision.", details: [] };
    }
    if (promotion?.saved === true) {
      return { checkId: "promotion-status", status: "passed", message: "The reviewed iOS changes were saved locally.", details: [] };
    }
    if (Array.isArray(promotion?.issues) && promotion.issues.length) {
      return { checkId: "promotion-status", status: "failed", message: "Promotion has unresolved local validation or conflict issues.", details: [] };
    }
    return { checkId: "promotion-status", status: "not_run", message: "No local iOS promotion has been saved for this revision.", details: [] };
  }

  function validationChecks(report = null, promotion = null) {
    const revisionId = report?.revisionId || promotion?.revisionId || null;
    const reported = new Map(
      Array.isArray(report?.checks)
        ? report.checks.filter((check) => check && typeof check.checkId === "string").map((check) => [check.checkId, check])
        : [],
    );
    reported.set("promotion-status", promotionCheck(promotion, revisionId));
    return CHECKS.map(({ checkId, label, fallback }) => {
      const check = reported.get(checkId);
      return {
        checkId,
        label,
        status: checkStatus(check?.status),
        message: typeof check?.message === "string" && check.message ? check.message : fallback,
        details: Array.isArray(check?.details) ? check.details.filter((detail) => typeof detail === "string" && detail) : [],
      };
    });
  }

  function appendText(parent, tagName, value, className = "") {
    const node = parent.ownerDocument.createElement(tagName);
    if (className) node.className = className;
    node.textContent = value;
    parent.appendChild(node);
    return node;
  }

  function renderValidationReport(container, report = null, promotion = null) {
    if (!container) return;
    container.replaceChildren();
    validationChecks(report, promotion).forEach((check) => {
      const card = container.ownerDocument.createElement("article");
      card.className = `validation-check ${check.status}`;
      const heading = container.ownerDocument.createElement("div");
      heading.className = "validation-check-heading";
      appendText(heading, "h3", check.label);
      appendText(heading, "span", STATUS_LABELS[check.status], `validation-check-status ${check.status}`);
      card.appendChild(heading);
      appendText(card, "p", check.message);
      if (check.details.length) {
        const details = container.ownerDocument.createElement("ul");
        check.details.forEach((detail) => appendText(details, "li", detail));
        card.appendChild(details);
      }
      container.appendChild(card);
    });
  }

  function simulatorCommand(simulatorUUID) {
    const uuid = typeof simulatorUUID === "string" ? simulatorUUID.trim() : "";
    if (!uuid || /\s/.test(uuid) || /^(booted|unknown|default|all)$/i.test(uuid)) {
      throw new RangeError("An explicit simulator UUID is required; booted or unknown simulator status is not allowed.");
    }
    return `platform=iOS Simulator,id=${uuid}`;
  }

  function simulatorCommands(simulatorUUID) {
    const uuid = typeof simulatorUUID === "string" ? simulatorUUID.trim() : "";
    const destination = simulatorCommand(uuid);
    return [
      `xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination '${destination}' -derivedDataPath .context/DerivedData build`,
      `xcrun simctl install ${uuid} .context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app`,
      `SIMCTL_CHILD_HANGTEN_REVIEW_WORKOUT=1 SIMCTL_CHILD_HANGTEN_REVIEW_PORTRAIT=1 xcrun simctl launch ${uuid} com.hangten.training`,
      `SIMCTL_CHILD_HANGTEN_REVIEW_WORKOUT=1 SIMCTL_CHILD_HANGTEN_REVIEW_LANDSCAPE=1 xcrun simctl launch ${uuid} com.hangten.training`,
      `xcrun simctl io ${uuid} screenshot .context/workout-raw.png`,
    ].join("\n");
  }

  function activeContext(getSuiteState) {
    const suite = getSuiteState?.() || {};
    const board = suite.activeBoard || null;
    const revisionId = suite.activeRevision || board?.revisionId || null;
    return { board, revisionId };
  }

  function contextKey({ board, revisionId }) {
    return board?.boardId && revisionId ? JSON.stringify([board.boardId, revisionId]) : null;
  }

  function bindReport(report, context) {
    if (!report || typeof report !== "object") return null;
    return {
      ...report,
      boardId: report.boardId || context.board?.boardId,
      revisionId: report.revisionId || context.revisionId,
    };
  }

  function createValidationController({ client, getSuiteState, onValidation = () => {}, render = () => {} } = {}) {
    if (!client || typeof client.getValidationReport !== "function" || typeof client.runValidation !== "function") {
      throw new TypeError("validation client methods are required");
    }
    if (typeof getSuiteState !== "function") throw new TypeError("getSuiteState must be a function");

    let operation = 0;
    let state = {
      contextKey: contextKey(activeContext(getSuiteState)),
      report: null,
      busy: false,
      error: "",
      simulatorUUID: "",
    };

    function synchronizeContext() {
      const context = activeContext(getSuiteState);
      if (state.contextKey !== contextKey(context)) {
        operation += 1;
        state = { ...state, contextKey: contextKey(context), report: null, busy: false, error: "" };
      }
      return context;
    }

    function getState() {
      synchronizeContext();
      return Object.freeze({ ...state, report: state.report ? { ...state.report } : null });
    }

    function emit() { render(getState()); }

    function contextIsCurrent(context, token) {
      const current = activeContext(getSuiteState);
      return token === operation && state.contextKey === contextKey(context) && contextKey(current) === contextKey(context);
    }

    function setError(message) {
      synchronizeContext();
      state = { ...state, busy: false, error: message };
      emit();
      return getState();
    }

    async function loadCachedReport() {
      const context = synchronizeContext();
      if (!context.board || !context.revisionId) return setError("Choose an active board revision before loading validation.");
      const token = ++operation;
      state = { ...state, busy: true, error: "" };
      emit();
      try {
        const report = bindReport(await client.getValidationReport(context.board.boardId, context.revisionId), context);
        if (!contextIsCurrent(context, token)) return getState();
        state = { ...state, report, busy: false, error: "" };
        if (report) onValidation(report);
        emit();
        return getState();
      } catch (error) {
        if (!contextIsCurrent(context, token)) return getState();
        return setError(error?.message || "Could not load the cached validation report.");
      }
    }

    async function runReport() {
      const context = synchronizeContext();
      if (!context.board || !context.revisionId) return setError("Choose an active board revision before running validation.");
      const token = ++operation;
      state = { ...state, busy: true, error: "" };
      emit();
      try {
        const report = bindReport(await client.runValidation(context.board.boardId, context.revisionId), context);
        if (!contextIsCurrent(context, token)) return getState();
        state = { ...state, report, busy: false, error: "" };
        if (report) onValidation(report);
        emit();
        return getState();
      } catch (error) {
        if (!contextIsCurrent(context, token)) return getState();
        return setError(error?.message || "Could not run validation.");
      }
    }

    function setSimulatorUUID(simulatorUUID) {
      synchronizeContext();
      state = { ...state, simulatorUUID: typeof simulatorUUID === "string" ? simulatorUUID : "" };
      emit();
      return getState();
    }

    return Object.freeze({
      getState,
      loadCachedReport,
      runReport,
      setSimulatorUUID,
    });
  }

  function renderValidationView(root, { suite, validation } = {}) {
    if (!root) return;
    const board = suite?.activeBoard || null;
    const revisionId = suite?.activeRevision || board?.revisionId || null;
    const view = validation || {};
    const report = view.report?.revisionId === revisionId ? view.report : null;
    const identity = root.querySelector("#validation-identity");
    const status = root.querySelector("#validation-status");
    const error = root.querySelector("#validation-error");
    const refreshButton = root.querySelector("#validation-refresh-button");
    const runButton = root.querySelector("#validation-run-button");
    const uuidInput = root.querySelector("#validation-simulator-uuid");
    const commandOutput = root.querySelector("#validation-simulator-commands");
    const commandError = root.querySelector("#validation-simulator-error");
    const copyButton = root.querySelector("#validation-copy-commands-button");
    const checks = root.querySelector("#validation-checks");

    if (identity) identity.textContent = board ? `${board.productName || board.boardId} · Revision ${revisionId}` : "Choose one active board revision to begin validation.";
    if (status) {
      const overallStatus = checkStatus(report?.overallStatus);
      status.textContent = report ? STATUS_LABELS[overallStatus] : "Not run";
      status.className = `validation-status ${overallStatus}`;
    }
    if (error) {
      error.textContent = view.error || "";
      error.classList.toggle("hidden", !view.error);
    }
    if (refreshButton) refreshButton.disabled = Boolean(view.busy) || !board || !revisionId;
    if (runButton) {
      runButton.disabled = Boolean(view.busy) || !board || !revisionId;
      runButton.textContent = view.busy ? "Working…" : "Run validation";
    }
    if (uuidInput && root.ownerDocument.activeElement !== uuidInput) uuidInput.value = view.simulatorUUID || "";

    let commands = "";
    let simulatorError = "";
    if (view.simulatorUUID) {
      try {
        commands = simulatorCommands(view.simulatorUUID);
      } catch (issue) {
        simulatorError = issue.message;
      }
    }
    if (uuidInput) {
      uuidInput.setAttribute("aria-invalid", simulatorError ? "true" : "false");
      uuidInput.title = simulatorError;
    }
    if (commandOutput) commandOutput.value = commands;
    if (commandError) {
      commandError.textContent = simulatorError || "Enter the UUID of a dedicated simulator that has already been created and made ready under the ownership contract.";
      commandError.classList.toggle("error", Boolean(simulatorError));
    }
    if (copyButton) copyButton.disabled = !commands;
    renderValidationReport(checks, report, suite?.promotion || null);
  }

  return Object.freeze({
    CHECKS,
    validationChecks,
    renderValidationReport,
    simulatorCommand,
    simulatorCommands,
    createValidationController,
    renderValidationView,
  });
}));
