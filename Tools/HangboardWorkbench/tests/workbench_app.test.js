const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { restoreOpeningAfterJobRecovery } = require("../workbench-controller.js");

const markup = fs.readFileSync(path.join(__dirname, "../index.html"), "utf8");

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


test("clipboard write rejection reaches the existing status channel", () => {
  const appSource = fs.readFileSync(path.join(__dirname, "../app.js"), "utf8");
  const handler = appSource.slice(appSource.lastIndexOf('el["validation-copy-commands-button"]'), appSource.lastIndexOf("configureSvg();"));
  assert.match(handler, /await navigator\.clipboard\.writeText\(commands\)/);
  assert.match(handler, /catch \(error\)[\s\S]*setStatus\(error\?\.message/);
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
