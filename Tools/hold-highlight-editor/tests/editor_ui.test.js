const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "app.js"), "utf8");

test("brands the workspace as a Hold Editor", () => {
  assert.match(index, /<title>Hold Editor<\/title>/);
  assert.match(index, /<h1>Hold Editor<\/h1>/);
  assert.match(index, /Edit and save hold highlights/);
  assert.doesNotMatch(index, /Hold Region Editor/);
  assert.doesNotMatch(index, /Grip regions/);
});

test("keeps internal region controls while presenting hold highlights", () => {
  assert.match(index, /id="region-list"[^>]*aria-label="Hold highlights"/);
  assert.match(index, /id="new-shape-select"[^>]*aria-label="New highlight shape"/);
  assert.match(index, /id="add-region-button"[\s\S]*?Add highlight/);
  assert.match(index, /id="delete-button">Delete highlight<\/button>/);
  assert.match(index, /id="region-mode-select"/);
  assert.match(index, /id="region-key-input"/);
  assert.match(index, /Select a hold highlight to edit its shape and details\./);
  assert.doesNotMatch(index, /Select a region to edit its shape and metadata/);
});

test("explains how to trace recessed and raised holds", () => {
  assert.match(index, /id="region-mode-select"[^>]*aria-describedby="region-mode-help"/);
  assert.match(index, /id="region-mode-help"[^>]*>Recessed cavity: trace the inner usable boundary\. Raised hold: trace the outer silhouette\. Exclude board faces, shelves, rails, and supports\.<\/small>/);
});

test("uses hold-highlight language in visible editor status", () => {
  assert.match(app, /el\["inspector-title"\]\.textContent = region \? `Hold \$\{region\.id\}`/);
  assert.match(app, /setStatus\(`Added \$\{region\.key\} highlight\.??`\)/);
  assert.match(app, /setStatus\(`Deleted \$\{region\.key\} highlight\. Undo is available\.`\)/);
  assert.doesNotMatch(app, /Select a region to edit its shape and metadata/);
});

test("handles drawing Enter and Escape before the focused-control guard", () => {
  const drawingShortcut = app.indexOf('event.key === "Enter" && state.drawing');
  const focusedControlGuard = app.indexOf('if (editingText) return;');

  assert.notEqual(drawingShortcut, -1);
  assert.notEqual(focusedControlGuard, -1);
  assert.ok(drawingShortcut < focusedControlGuard);
  assert.match(app, /event\.key === "Escape" && state\.drawing/);
});

test("preserves the selected primitive shape when adding a highlight", () => {
  assert.match(app, /shapeKind: state\.drawShape === "curved-freeform" \? "freeform" : state\.drawShape/);
});
