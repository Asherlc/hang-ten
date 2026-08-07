const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const markup = fs.readFileSync(path.join(__dirname, "../index.html"), "utf8");

test("the guided opening screen offers repository and in-progress board pickers", () => {
  assert.match(markup, /id="repository-board-list"/);
  assert.match(markup, /id="in-progress-board-list"/);
  assert.match(markup, /id="create-board-form"/);
  assert.match(markup, /name="sourceKind" value="url"/);
  assert.match(markup, /name="sourceKind" value="upload"/);
  assert.doesNotMatch(markup, /name="sourceKind" value="import"/);
  assert.doesNotMatch(markup, /setup-import-path|Existing CLI run|Import run/);
});
