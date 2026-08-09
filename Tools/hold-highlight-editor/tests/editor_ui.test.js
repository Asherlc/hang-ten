const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");

test("app imports normalizeRegion from HoldEditorModel", () => {
  assert.match(app, /normalizeRegion,/);
  assert.match(app, /const region = normalizeRegion\(/);
});
