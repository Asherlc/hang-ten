const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { restoreOpeningAfterJobRecovery } = require("../workbench-controller.js");

const markup = fs.readFileSync(path.join(__dirname, "../index.html"), "utf8");

test("the guided opening screen offers repository and in-progress board pickers", () => {
  assert.match(markup, /id="repository-board-list"/);
  assert.match(markup, /id="repository-diagnostics"/);
  assert.match(markup, /id="in-progress-board-list"/);
  assert.match(markup, /id="create-board-form"/);
  assert.match(markup, /name="sourceKind" value="url"/);
  assert.match(markup, /name="sourceKind" value="upload"/);
  assert.doesNotMatch(markup, /name="sourceKind" value="import"/);
  assert.doesNotMatch(markup, /setup-import-path|Existing CLI run|Import run/);
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
