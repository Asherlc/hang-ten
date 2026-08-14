const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {
  renderRepositoryDiagnostics,
  restoreOpeningAfterJobRecovery,
} = require("../workbench-controller.js");
const { formatFocusedEditorDiagnostic } = require("../editor-ui-model.js");
const { normalizePipelineDocument } = require("../editor-model.js");

const markup = fs.readFileSync(path.join(__dirname, "../index.html"), "utf8");
const readme = fs.readFileSync(path.join(__dirname, "../README.md"), "utf8");
const appSource = fs.readFileSync(path.join(__dirname, "../app.js"), "utf8");

function actualElementIds(html) {
  const withoutComments = html.replace(/<!--[\s\S]*?-->/g, "");
  const ids = new Set();
  for (const tag of withoutComments.matchAll(/<[A-Za-z][^>]*>/g)) {
    const id = tag[0].match(/\sid=(?:"([^"]+)"|'([^']+)')/);
    if (id) ids.add(id[1] || id[2]);
  }
  return ids;
}

function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `expected ${name}() to be present`);
  const bodyStart = source.indexOf("{", start);
  let depth = 0;
  for (let index = bodyStart; index < source.length; index += 1) {
    if (source[index] === "{") depth += 1;
    if (source[index] === "}") depth -= 1;
    if (depth === 0) return source.slice(start, index + 1);
  }
  assert.fail(`could not extract ${name}()`);
}

function literalCallArguments(source, callee, argumentIndex) {
  const marker = `${callee}(`;
  const values = [];
  let searchFrom = 0;
  while (searchFrom < source.length) {
    const callStart = source.indexOf(marker, searchFrom);
    if (callStart < 0) break;
    const openParen = callStart + marker.length - 1;
    const argumentsList = [];
    let argumentStart = openParen + 1;
    let depth = 1;
    let quote = null;
    let escaped = false;
    let index = openParen + 1;
    for (; index < source.length; index += 1) {
      const character = source[index];
      if (quote) {
        if (escaped) escaped = false;
        else if (character === "\\") escaped = true;
        else if (character === quote) quote = null;
        continue;
      }
      if (character === '"' || character === "'" || character === "`") {
        quote = character;
      } else if (character === "(") {
        depth += 1;
      } else if (character === ")") {
        depth -= 1;
        if (depth === 0) {
          argumentsList.push(source.slice(argumentStart, index));
          break;
        }
      } else if (character === "," && depth === 1) {
        argumentsList.push(source.slice(argumentStart, index));
        argumentStart = index + 1;
      }
    }
    const value = argumentsList[argumentIndex]?.trim();
    if (value && /^["'`]/.test(value)) values.push(value);
    searchFrom = Math.max(index + 1, callStart + marker.length);
  }
  return values;
}

function propertyMessageLiterals(source) {
  const literal = String.raw`(?:\`(?:\\.|[^\`])*\`|"(?:\\.|[^"])*"|'(?:\\.|[^'])*')`;
  return [...source.matchAll(new RegExp(`message\\s*:\\s*(${literal})`, "g"))]
    .map((match) => match[1]);
}

test("the guided opening screen offers repository and in-progress board pickers", () => {
  const ids = actualElementIds(markup);
  for (const id of [
    "repository-board-list",
    "repository-diagnostics",
    "in-progress-board-list",
    "create-board-form",
  ]) assert.equal(ids.has(id), true, `${id} must resolve to an element`);
  assert.match(markup, /name="sourceKind" value="url"/);
  assert.match(markup, /name="sourceKind" value="upload"/);
  assert.doesNotMatch(markup, /name="sourceKind" value="import"/);
  assert.doesNotMatch(markup, /setup-import-path|Existing CLI run|Import run/);
});

test("loads a completed board from its explicit editor document URL", async () => {
  const source = extractFunction(appSource, "loadCheckpoint");
  assert.match(source, /view\.editorDocumentUrl/);
  assert.doesNotMatch(source, /checkpointDocumentUrl\(/);
});

test("a new image-only board loads without requesting a hold document", async () => {
  const state = {
    board: { boardId: "previous-board" },
    regions: [{ id: 9, key: "previous" }],
    baselineRegions: [{ id: 9, key: "previous" }],
    imageHref: "previous.png",
    checkpointDocument: { regions: [{ id: 9 }] },
    autosaveTimer: null,
  };
  let fetchCount = 0;
  let setRegionsCount = 0;
  const loadCheckpoint = new Function(
    "loadCoordinator",
    "state",
    "renderSaveState",
    "checkpointImageUrl",
    "loadImageAsset",
    "fetch",
    "validateEditableImageAlignment",
    "stageCheckpointDocument",
    "checkpointComparisonUrl",
    "clearTimeout",
    "clone",
    "el",
    "applyImageAsset",
    "applyAnnotatedReviewAsset",
    "EDITOR_STAGES",
    "readStoredDraft",
    "discardStaleDrafts",
    "setRegions",
    "resetHistory",
    "renderEditorShell",
    "render",
    `return (async ${extractFunction(appSource, "loadCheckpoint")});`,
  )(
    { begin() { throw new Error("the supplied load should be used"); } },
    state,
    () => {},
    (view) => view.editorImageUrl,
    async (href) => ({ href, name: "Board image", image: { naturalWidth: 120, naturalHeight: 60 } }),
    async () => { fetchCount += 1; throw new Error("hold document must not be requested"); },
    () => {},
    () => { throw new Error("image-only boards have no hold document to stage"); },
    () => null,
    () => {},
    structuredClone,
    {
      "board-image": { removeAttribute() {} },
      "annotated-review-image": { removeAttribute() {}, alt: "" },
    },
    (asset) => { state.imageHref = asset.href; state.canvas = { width: 120, height: 60 }; },
    () => {},
    new Set([2, 3]),
    () => null,
    () => {},
    () => { setRegionsCount += 1; },
    () => {},
    () => {},
    () => {},
  );

  const loaded = await loadCheckpoint(
    {
      boardId: "new-board",
      revisionId: "revision-1",
      stage: 0,
      state: "awaiting_review",
      editorImageUrl: "/stage-0-review.png",
      editorDocumentUrl: null,
    },
    null,
    { isCurrent: () => true, commit(callback) { callback(); return true; } },
  );

  assert.equal(loaded, true);
  assert.equal(fetchCount, 0);
  assert.equal(setRegionsCount, 0);
  assert.equal(state.board.boardId, "new-board");
  assert.equal(state.imageHref, "/stage-0-review.png");
  assert.deepEqual(state.regions, []);
});

test("opening a completed board first creates an editable Stage 3 revision", async () => {
  const source = extractFunction(appSource, "prepareEditableBoard");
  const calls = [];
  const prepareEditableBoard = new Function(
    "runTrackedJob",
    "workbenchClient",
    `return (async ${source});`,
  )(
    async (operation) => operation({ onAccepted() {} }),
    {
      async revise(view, stage) {
        calls.push([view.revisionId, stage]);
        return { ...view, revisionId: "revision-2", parentRevisionId: view.revisionId, stage: 3, state: "awaiting_review" };
      },
    },
  );
  const complete = {
    boardId: "published-board",
    revisionId: "revision-1",
    stage: 4,
    state: "complete",
    editorDocumentUrl: "/holds.json",
  };

  const editable = await prepareEditableBoard(complete);

  assert.deepEqual(calls, [["revision-1", 3]]);
  assert.equal(editable.revisionId, "revision-2");
  assert.equal(editable.parentRevisionId, "revision-1");
  assert.equal(editable.stage, 3);
  assert.match(extractFunction(appSource, "selectLibraryBoard"), /prepareEditableBoard/);
  const guidedSelection = extractFunction(appSource, "selectGuidedBoard");
  assert.match(guidedSelection, /prepareEditableBoard/);
  assert.ok(
    guidedSelection.indexOf("prepareEditableBoard")
      < guidedSelection.indexOf("refreshBoards")
      && guidedSelection.indexOf("refreshBoards")
        < guidedSelection.indexOf("loadCheckpoint"),
    "the board rail must refresh after the completed revision is forked",
  );
});

test("failed checkpoint preparation does not prune the visible board recovery draft", async () => {
  let pruneCount = 0;
  const draftHelpers = new Function(
    "draftStore",
    "console",
    `${extractFunction(appSource, "discardStaleDrafts")}
${extractFunction(appSource, "readStoredDraft")}
return { discardStaleDrafts, readStoredDraft };`,
  )(
    {
      discardMismatched() { pruneCount += 1; },
      read() { return { document: { canvas: { width: 100, height: 50 }, regions: [] } }; },
    },
    { warn() {} },
  );
  const state = {
    board: { boardId: "visible-board" },
    regions: [{ id: 9, key: "visible" }],
    baselineRegions: [{ id: 9, key: "visible" }],
    imageHref: "visible.png",
    checkpointDocument: { regions: [{ id: 9 }] },
  };
  const before = structuredClone(state);
  const loadCheckpoint = new Function(
    "loadCoordinator",
    "state",
    "renderSaveState",
    "checkpointImageUrl",
    "loadImageAsset",
    "fetch",
    "validateEditableImageAlignment",
    "stageCheckpointDocument",
    "checkpointComparisonUrl",
    "clearTimeout",
    "clone",
    "el",
    "applyImageAsset",
    "applyAnnotatedReviewAsset",
    "EDITOR_STAGES",
    "readStoredDraft",
    "discardStaleDrafts",
    "setRegions",
    "renderEditorShell",
    "render",
    `return (async ${extractFunction(appSource, "loadCheckpoint")});`,
  )(
    { begin() { throw new Error("the supplied load should be used"); } },
    state,
    () => {},
    (view) => view.editorImageUrl,
    async (href) => {
      if (href === "/comparison.png") throw new Error("comparison unavailable");
      return { href, image: { naturalWidth: 100, naturalHeight: 50 } };
    },
    async () => ({ ok: true, async json() { return { canvas: { width: 100, height: 50 }, regions: [] }; } }),
    () => {},
    (_view, _image, baseline, restored) => ({ baseline, document: restored || baseline, editorMode: "contour" }),
    () => "/comparison.png",
    () => {},
    structuredClone,
    {},
    () => {},
    () => {},
    new Set([2, 3]),
    draftHelpers.readStoredDraft,
    draftHelpers.discardStaleDrafts,
    () => {},
    () => {},
    () => {},
  );

  await assert.rejects(
    loadCheckpoint(
      { boardId: "next-board", revisionId: "revision-2", stage: 2, editorImageUrl: "/board.png", editorDocumentUrl: "/holds.json" },
      null,
      { isCurrent: () => true, commit(callback) { callback(); return true; } },
    ),
    /comparison unavailable/,
  );
  assert.equal(pruneCount, 0);
  assert.deepEqual(state, before);
});

test("checkpoint loading stages vector documents and rejects malformed data before commit", async () => {
  const helpers = new Function(
    "normalizePipelineDocument",
    `${extractFunction(appSource, "editorModeForDocument")}
${extractFunction(appSource, "stageCheckpointDocument")}
return { editorModeForDocument, stageCheckpointDocument };`,
  )(normalizePipelineDocument);
  const vectorDocument = {
    canvas: { width: 100, height: 50 },
    regions: [{ id: 1, key: "hold-1", type: "edge", displayPath: "M 10 10 L 20 10 L 20 20 Z" }],
  };
  const vectorStage = helpers.stageCheckpointDocument(
    { stage: 4, editorMode: null },
    { image: { naturalWidth: 100, naturalHeight: 50 } },
    vectorDocument,
  );
  assert.equal(vectorStage.editorMode, "vector");
  assert.equal(vectorStage.document.regions[0].displayPath, vectorDocument.regions[0].displayPath);
  const validContourDocument = {
    canvas: { width: 100, height: 50 },
    regions: [{ id: 2, key: "hold-2", type: "edge", contour: [[0, 0], [10, 0], [10, 10]] }],
  };
  const malformedDraft = {
    ...validContourDocument,
    regions: [{
      ...validContourDocument.regions[0],
      metadata: { editableContour: [[0, 0], [10, Infinity], [10, 10]] },
    }],
  };
  assert.throws(
    () => helpers.stageCheckpointDocument(
      { stage: 2, editorMode: "contour" },
      { image: { naturalWidth: 100, naturalHeight: 50 } },
      validContourDocument,
      malformedDraft,
    ),
    /Editable contour point 1 must contain two finite coordinates/,
  );

  const source = extractFunction(appSource, "loadCheckpoint");
  assert.ok(
    source.indexOf("stageCheckpointDocument") < source.indexOf("return load.commit"),
    "the document must be staged before editor state is committed",
  );
  const state = {
    board: { boardId: "previous-board" },
    regions: [{ id: 9, key: "previous" }],
    baselineRegions: [{ id: 9, key: "previous" }],
    imageHref: "previous.png",
    checkpointDocument: { regions: [{ id: 9 }] },
  };
  const before = structuredClone(state);
  let committed = false;
  const loadCheckpoint = new Function(
    "loadCoordinator",
    "state",
    "renderSaveState",
    "checkpointImageUrl",
    "loadImageAsset",
    "fetch",
    "validateEditableImageAlignment",
    "stageCheckpointDocument",
    "checkpointComparisonUrl",
    "clearTimeout",
    "clone",
    "el",
    "applyImageAsset",
    "applyAnnotatedReviewAsset",
    "EDITOR_STAGES",
    "readStoredDraft",
    "discardStaleDrafts",
    "setRegions",
    "renderEditorShell",
    "render",
    "requestAnimationFrame",
    "fitCanvas",
    `return (async ${source});`,
  )(
    { begin() { throw new Error("the supplied load should be used"); } },
    state,
    () => {},
    (view) => view.editorImageUrl,
    async () => ({ image: { naturalWidth: 100, naturalHeight: 50 } }),
    async () => ({ ok: true, async json() {
      return {
        canvas: { width: 100, height: 50 },
        regions: [{
          id: 1,
          key: "invalid",
          type: "edge",
          contour: [[0, 0], [10, 0], [10, 10]],
          metadata: { editableContour: [[0, 0], [10, Infinity], [10, 10]] },
        }],
      };
    } }),
    () => {},
    helpers.stageCheckpointDocument,
    () => null,
    () => {},
    structuredClone,
    {},
    () => {},
    () => {},
    new Set([2, 3]),
    () => null,
    () => {},
    () => { throw new Error("setRegions must not run for malformed data"); },
    () => {},
    () => {},
    () => {},
  );

  await assert.rejects(
    loadCheckpoint(
      { stage: 4, editorImageUrl: "/board.png", editorDocumentUrl: "/holds.json", editorMode: null },
      null,
      { isCurrent: () => true, commit(callback) { committed = true; callback(); return true; } },
    ),
    /Editable contour point 1 must contain two finite coordinates/,
  );
  assert.equal(committed, false);
  assert.deepEqual(state, before);
});

test("the board rail has no user-facing run terminology", () => {
  assert.doesNotMatch(markup, />Recent runs</);
  assert.doesNotMatch(markup, /Checking for recent runs/);
  assert.doesNotMatch(appSource, /function renderRecentRuns\(/);
});

test("the workbench is a single focused hold-outline editor", () => {
  const ids = actualElementIds(markup);
  for (const id of [
    "board-select", "undo-button", "redo-button", "save-state", "save-button",
    "region-list", "canvas-viewport", "inspector-panel", "advanced-tools-toggle",
    "advanced-outline-tools", "advanced-transform-tools", "advanced-assist-tools",
    "advanced-details-tools", "more-actions", "board-details",
  ]) assert.equal(ids.has(id), true, `${id} must resolve to an element`);
  assert.doesNotMatch(markup, /tool-suite-sidebar|tool-onboard|tool-inspect|tool-promote|tool-validate/);
  assert.doesNotMatch(markup, />Promote to iOS<|>Validate</);
});

test("the main editor copy and operator docs explain direct outlining without pipeline terminology", () => {
  const workspace = markup.match(/<section class="workspace-grid"[\s\S]*?<\/section>\s*<\/main>/);
  assert.ok(workspace, "expected the focused editor workspace");

  assert.match(workspace[0], /Edit holds/);
  assert.doesNotMatch(
    workspace[0],
    /(?:>[^<]*(?:Stage [0-9]|checkpoint|Promote to iOS|Validate)[^<]*<|\b(?:aria-label|aria-labelledby|title|alt|placeholder)=["'][^"']*(?:Stage [0-9]|checkpoint|Promote to iOS|Validate)[^"']*["'])/,
  );
  assert.match(readme, /## Correct hold outlines/);
  assert.match(readme, /Open \*\*Advanced tools\*\* only for shape, curve, transform, edge snap, mirror, and metadata work\./);
  assert.match(readme, /Selecting a hold highlight exposes its canvas handles/);
  assert.match(
    readme,
    /Open \*\*Advanced tools\*\* for the corresponding shape, curve, and transform actions in the inspector, plus \*\*Snap edges\*\*/,
  );
  assert.doesNotMatch(readme, /open \*\*Advanced tools\*\*[^.]*handles/i);
  assert.match(readme, /Press `E` to open or close \*\*Advanced tools\*\*/);
  assert.match(readme, /drag an edge handle to bow that segment without moving its vertices/);
  assert.match(readme, /hold Alt during the drag to bypass snapping/);
  assert.match(readme, /undo the gesture to restore the prior edge in one step/);
  assert.doesNotMatch(readme, /\*\*Edit points\*\*|toggle detailed point editing/i);
  assert.match(readme, /Use \*\*More\*\* for comparison or artifact exports\./);
  assert.match(readme, /Save locally; saving does not commit, push, or synchronize changes\./);
});

test("persistent secondary actions are contextual rather than toolbar controls", () => {
  const moreActions = markup.match(/<details id="more-actions"[\s\S]*?<\/details>/);
  const advancedTools = markup.match(/<div id="advanced-tools"[\s\S]*?<\/div>\s*<\/form>/);

  assert.ok(moreActions, "expected the More actions popover");
  assert.ok(advancedTools, "expected the Advanced tools region");
  for (const id of ["compare-button", "export-button", "corrections-button"]) {
    assert.match(moreActions[0], new RegExp(`id="${id}"`), `${id} must be under More actions`);
  }
  assert.match(advancedTools[0], /id="snap-button"/, "snap-button must be under Advanced tools");
  const toolbarWithoutDetails = markup
    .match(/<div class="toolbar"[\s\S]*?<\/div>\s*<\/header>/)[0]
    .replace(/<details\b[\s\S]*?<\/details>/g, "");
  for (const id of ["snap-button", "compare-button", "export-button", "corrections-button"]) {
    assert.doesNotMatch(toolbarWithoutDetails, new RegExp(`id="${id}"`));
  }
});

test("every retained inspector action is a non-submitting form button", () => {
  const inspectorForm = markup.match(/<form class="inspector-form[\s\S]*?<\/form>/);
  assert.ok(inspectorForm, "expected the selected-hold inspector form");

  const buttons = [...inspectorForm[0].matchAll(/<button\b[^>]*>/g)].map((match) => match[0]);
  assert.ok(buttons.some((button) => /\bid="snap-button"/.test(button)), "expected Snap edges in the inspector");
  for (const button of buttons) {
    assert.match(button, /\btype=(?:"button"|'button')/, `${button} must not submit the inspector form`);
  }
});

test("main editor runtime feedback uses hold-task language without banning data-contract terms", () => {
  const validateGeometrySource = extractFunction(appSource, "validateGeometry");
  const loadCheckpointSource = extractFunction(appSource, "loadCheckpoint");
  const reviewAssetSource = loadCheckpointSource.match(/const reviewAsset =[\s\S]*?(?=\n\s*if \(!load\.isCurrent\(\)\))/);
  assert.ok(reviewAssetSource, "expected the comparison-image loading pathway");

  const runtimeCopy = [
    ...propertyMessageLiterals(validateGeometrySource),
    ...literalCallArguments(loadCheckpointSource, "Error", 0),
    ...literalCallArguments(reviewAssetSource[0], "loadImageAsset", 1),
    ...literalCallArguments(appSource, "setStatus", 0),
    ...literalCallArguments(appSource, "runGuidedMutation", 1),
    ...literalCallArguments(appSource, "commitHistory", 0),
    ...[...appSource.matchAll(/state\.saveError\s*=\s*error\.message\s*\|\|\s*(["'`][^\n;]+["'`])/g)]
      .map((match) => match[1]),
  ];

  assert.ok(runtimeCopy.length >= 20, "expected to audit the main editor's runtime copy sinks");
  assert.doesNotMatch(
    runtimeCopy.join("\n"),
    /\b(?:Stage(?:\s+\d|\s*\$\{)|checkpoint|promotion|validation|approval)\b/i,
  );
});

test("focused editor error sinks format external messages before rendering", () => {
  for (const functionName of [
    "renderValidation",
    "handleAutosaveError",
    "selectLibraryBoard",
    "selectGuidedBoard",
    "createGuidedBoard",
    "approveCurrent",
    "runGuidedMutation",
    "loadGuidedWorkbench",
    "loadServerSession",
    "saveToRun",
  ]) {
    assert.match(
      extractFunction(appSource, functionName),
      /formatFocusedEditorError|focusedEditorErrorMessage/,
      `${functionName}() must format external errors at its UI boundary`,
    );
  }
  assert.doesNotMatch(
    appSource,
    /(?:state\.saveError|\.textContent)\s*=\s*(?:error|failure)\.message\b/,
    "external messages must not be assigned directly to visible editor state",
  );
});

test("opening repository diagnostics are translated at the app boundary before visible rendering", async () => {
  const state = {};
  const refreshBoards = new Function(
    "openingBoardController",
    "state",
    "formatFocusedEditorDiagnostic",
    "formatFocusedEditorError",
    "renderOpenBoards",
    "renderOpeningSections",
    `return (async ${extractFunction(appSource, "refreshBoards")});`,
  )(
    { async refresh() {
      return {
        library: [{ boardId: "alpha" }],
        diagnostics: [{
          path: "broken-board/stage-2-regions.json",
          code: "invalid_run",
          holdId: "hold-17",
          reason: "contour overlaps itself",
          message: "Stage 2 region 17 failed validation: contour overlaps itself",
        }, {
          path: "broken-board/metadata.json",
          code: "missing_message",
          message: {},
        }],
        runtime: [],
        errors: {},
      };
    } },
    state,
    formatFocusedEditorDiagnostic,
    require("../editor-ui-model.js").formatFocusedEditorError,
    () => {},
    () => {},
  );

  await refreshBoards();

  const makeNode = (tagName) => ({
    tagName,
    children: [],
    textContent: "",
    className: "",
    classList: { toggle() {} },
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = [...children]; },
  });
  const container = { ...makeNode("div"), ownerDocument: { createElement: makeNode } };
  renderRepositoryDiagnostics(container, state.libraryDiagnostics);

  assert.equal(
    container.children[1].children[0].children[1].textContent,
    "Hold 17 failed outline check: outline overlaps itself",
  );
  assert.equal(
    container.children[1].children[1].children[1].textContent,
    "Repository package is invalid",
  );
  assert.equal(state.libraryDiagnostics[0].path, "broken-board/stage-2-regions.json");
  assert.equal(state.libraryDiagnostics[0].holdId, "hold-17");
  assert.equal(state.libraryDiagnostics[0].reason, "contour overlaps itself");
  assert.equal(state.libraryDiagnostics[1].message, "Repository package is invalid");
});

test("the workbench uses one accessible inspector panel and drawer controls", () => {
  const count = (id) => (markup.match(new RegExp(`\\bid=["']${id}["']`, "g")) ?? []).length;
  for (const id of [
    "inspector-panel",
    "inspector-drawer-toggle",
    "inspector-drawer-close",
    "inspector-drawer-backdrop",
  ]) assert.equal(count(id), 1, `${id} must appear exactly once`);

  assert.match(markup, /<aside[^>]*id="inspector-panel"[^>]*aria-labelledby="inspector-title"/);
  assert.doesNotMatch(markup, /<aside[^>]*id="inspector-panel"[^>]*\brole=/);
  assert.doesNotMatch(markup, /<aside[^>]*id="inspector-panel"[^>]*aria-modal=/);
  assert.match(markup, /<button[^>]*id="inspector-drawer-toggle"[^>]*aria-expanded="false"[^>]*aria-controls="inspector-panel"/);
});


test("editor bootstrap does not reference the removed suite controls", () => {
  for (const obsoleteReference of [
    "inspect-next-action", "tool-onboard", "tool-inspect", "tool-promote", "tool-validate",
    "promotion-preview-button", "promotion-refresh-button", "promotion-save-button",
    "validation-refresh-button", "validation-run-button", "validation-simulator-uuid", "validation-copy-commands-button",
  ]) assert.doesNotMatch(appSource, new RegExp(obsoleteReference));
  assert.doesNotMatch(appSource, /createToolSuiteController|createPromotionController|createValidationController|renderSuite|renderInspectView/);
});

test("the focused app no longer initializes suite, promotion, or validation views", () => {
  const app = fs.readFileSync(path.join(__dirname, "../app.js"), "utf8");

  assert.doesNotMatch(app, /createToolSuiteController|createPromotionController|createValidationController/);
  assert.doesNotMatch(app, /renderSuite\(|renderPromotionView|renderValidationView/);
});

test("setup preserves a recovered terminal job error after refreshing boards", async () => {
  const classes = new Set(["hidden"]);
  const setupError = {
    textContent: "",
    classList: {
      toggle(name, force) {
        if (force) classes.add(name);
        else classes.delete(name);
      },
    },
  };
  const calls = [];
  const failure = new Error("Repository package is invalid");

  const message = await restoreOpeningAfterJobRecovery({
    failure,
    async refreshBoards() { calls.push("refresh"); },
    showSetup() { calls.push("setup"); },
    setupError,
    setStatus(status) { calls.push(["status", status]); },
  });

  assert.equal(message, failure.message);
  assert.deepEqual(calls, [
    "refresh",
    "setup",
    ["status", failure.message],
  ]);
  assert.equal(setupError.textContent, failure.message);
  assert.equal(classes.has("hidden"), false);
});
