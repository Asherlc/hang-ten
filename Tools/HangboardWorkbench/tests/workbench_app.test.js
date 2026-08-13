const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {
  renderRepositoryDiagnostics,
  restoreOpeningAfterJobRecovery,
} = require("../workbench-controller.js");
const { formatFocusedEditorDiagnostic } = require("../editor-ui-model.js");

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
  assert.match(readme, /Select a hold highlight, then open \*\*Advanced tools\*\*/);
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
    "renderRecentRuns",
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
