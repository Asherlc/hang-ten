const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "app.js"), "utf8");
const readme = fs.readFileSync(path.join(root, "README.md"), "utf8");
const server = fs.readFileSync(path.join(root, "server.py"), "utf8");

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
  assert.match(index, />\s*<span>＋<\/span>\s*Add highlight\s*</);
  assert.match(index, /id="delete-button"/);
});

test("documents the direct hold-highlight workflow", () => {
  assert.match(readme, /^# Hold Editor/m);
  assert.match(readme, /choose a board.*edit.*add.*delete.*save/is);
  assert.match(readme, /hold type/i);
  assert.doesNotMatch(readme, /# Hold Region Editor/);
});

test("uses hold editor wording in server labels", () => {
  assert.match(server, /Hold Editor: http:\/\//);
  assert.doesNotMatch(server, /Hold Region Editor: http:\/\//);
});

test("marks manual file loading as a static fallback", () => {
  assert.match(index, /id="static-load-controls"/);
  assert.match(index, /id="load-image-button"/);
  assert.match(index, /id="load-regions-button"/);
});

test("switches between server-first and static fallback entry states", () => {
  assert.match(app, /function showStaticLoadControls\(visible\)/);
  assert.match(app, /static-load-controls/);
  assert.match(app, /showStaticLoadControls\(false\)/);
  assert.match(app, /showStaticLoadControls\(true\)/);
});

test("uses hold language for selection and editing status", () => {
  assert.match(app, /Hold \$\{region\.id\}/);
  assert.match(app, /Added \$\{region\.key\}/);
  assert.match(app, /Deleted \$\{region\.key\}/);
  assert.doesNotMatch(app, /Select a region to edit its shape and metadata/);
});

test("describes static save mode with hold-editor wording", () => {
  assert.match(app, /save hold highlights in this Hold Editor/i);
  assert.doesNotMatch(app, /onboarding run/);
});

test("uses hold-highlight terminology in visible editor controls", () => {
  assert.match(index, />Load highlights</);
  assert.match(index, />Export edited highlights</);
  assert.match(index, />All highlights</);
  assert.match(index, /Drop a board image and hold-highlight JSON here/);
  assert.match(index, /Why was this hold highlight changed\?/);
  assert.doesNotMatch(index, />Load regions</);
  assert.doesNotMatch(index, />All regions</);
});

test("uses hold-highlight terminology in runtime messages", () => {
  assert.match(app, /Rotated hold highlight/);
  assert.match(app, /Exported .* edited hold highlights/);
  assert.doesNotMatch(app, /"(?:Rotated|Bent|Resized|Moved|Renamed) region"/);
  assert.doesNotMatch(app, /edited regions\.`/);
});

test("documents hold-highlight operations without generic region prose", () => {
  assert.match(readme, /Hold highlights can be drawn/);
  assert.match(readme, /previous or next hold highlight/);
  assert.doesNotMatch(readme, /Regions can be drawn/);
  assert.doesNotMatch(readme, /symmetric region/);
});
