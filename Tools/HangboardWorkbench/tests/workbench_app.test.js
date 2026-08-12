const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { restoreOpeningAfterJobRecovery } = require("../workbench-controller.js");

const markup = fs.readFileSync(path.join(__dirname, "../index.html"), "utf8");
const readme = fs.readFileSync(path.join(__dirname, "../README.md"), "utf8");

function actualElementIds(html) {
  const withoutComments = html.replace(/<!--[\s\S]*?-->/g, "");
  const ids = new Set();
  for (const tag of withoutComments.matchAll(/<[A-Za-z][^>]*>/g)) {
    const id = tag[0].match(/\sid=(?:"([^"]+)"|'([^']+)')/);
    if (id) ids.add(id[1] || id[2]);
  }
  return ids;
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
  const visibleWorkspaceCopy = workspace[0].replace(/<[^>]*>/g, " ");

  assert.match(visibleWorkspaceCopy, /Edit holds/);
  assert.doesNotMatch(visibleWorkspaceCopy, /Stage [0-9]|checkpoint|Promote to iOS|Validate/);
  assert.match(readme, /## Correct hold outlines/);
  assert.match(readme, /Open \*\*Advanced tools\*\* only for shape, curve, transform, edge snap, mirror, and metadata work\./);
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
  const appSource = fs.readFileSync(path.join(__dirname, "../app.js"), "utf8");
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
