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

test("the workbench has a persistent single-board tool suite shell", () => {
  const ids = actualElementIds(markup);
  for (const id of [
    "tool-suite-sidebar",
    "active-board-card",
    "tool-onboard",
    "tool-inspect",
    "tool-promote",
    "tool-validate",
    "inspect-view",
    "inspect-board-preview",
    "inspect-artifact-links",
    "inspect-hold-inventory",
    "inspect-readiness",
    "inspect-next-action",
    "promote-view",
    "validate-view",
  ]) assert.equal(ids.has(id), true, `${id} must resolve to an element`);
  assert.match(markup, /data-tool="onboard"/);
  assert.match(markup, /data-tool="inspect"/);
  assert.match(markup, /data-tool="promote"/);
  assert.match(markup, /data-tool="validate"/);
  assert.match(markup, /workbench-suite-model\.js/);
  assert.match(markup, /workbench-suite-controller\.js/);
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
