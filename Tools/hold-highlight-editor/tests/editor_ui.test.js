const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "app.js"), "utf8");
const readme = fs.readFileSync(path.join(root, "README.md"), "utf8");

void app;
void readme;

test("brands the workspace as a Hold Editor", () => {
  assert.match(index, /<title>Hold Editor<\/title>/);
  assert.match(index, /<h1>Hold Editor<\/h1>/);
  assert.doesNotMatch(index, /Hold Region Editor/);
  assert.match(index, /Edit and save hold highlights/);
});

test("keeps full hold editing controls", () => {
  assert.match(index, /id="new-shape-select"/);
  assert.match(index, /id="region-type-select"/);
  assert.match(index, /value="jug"/);
  assert.match(index, /value="sloper"/);
  assert.match(index, /value="edge"/);
  assert.match(index, /value="pocket"/);
  assert.match(index, /id="add-region-button"/);
  assert.match(index, /id="delete-button"/);
});

test("marks manual file loading as a static fallback", () => {
  assert.match(index, /id="static-load-controls"/);
  assert.match(index, /id="load-image-button"/);
  assert.match(index, /id="load-regions-button"/);
});
