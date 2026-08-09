const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "app.js"), "utf8");
const readme = fs.readFileSync(path.join(root, "README.md"), "utf8");
const server = fs.readFileSync(path.join(root, "server.py"), "utf8");

test("renders the guided Hangboard Workbench shell instead of the old static title", () => {
  assert.match(index, /<title>Hangboard Workbench<\/title>/);
  assert.match(index, /<h1 id="setup-title">Start a hangboard<\/h1>/);
  assert.match(index, /<h1 id="board-title">Hangboard Workbench<\/h1>/);
  assert.match(index, /Review each checkpoint, then continue the pipeline\./);
  assert.doesNotMatch(index, /<title>Hold Editor<\/title>/);
  assert.doesNotMatch(index, /<h1>Hold Editor<\/h1>/);
  assert.doesNotMatch(index, /Hold Region Editor/);
});

test("shows the guided pipeline and region-review controls", () => {
  assert.match(index, /<h2>Pipeline<\/h2>/);
  assert.match(index, /<h2>Grip regions<\/h2>/);
  assert.match(index, /aria-label="Grip regions"/);
  assert.match(index, /id="new-shape-select"/);
  assert.match(index, /value="curved-freeform"/);
  assert.match(index, /id="add-region-button"/);
  assert.match(index, /No checkpoint selected/);
  assert.match(index, /Why was this region changed\?/);
});

test("keeps legacy file-loading controls inside the workbench toolbar", () => {
  assert.match(index, /id="legacy-controls"/);
  assert.match(index, /id="load-image-button">Load image</);
  assert.match(index, /id="load-regions-button">Load regions</);
  assert.match(index, /id="export-button">Export edited regions</);
  assert.match(index, /id="corrections-button">Export corrections</);
  assert.doesNotMatch(index, /id="static-load-controls"/);
});

test("app switches between guided workbench labels and legacy static mode", () => {
  assert.match(app, /el\["board-title"\]\.textContent = view\?\.productName \|\| "Hangboard Workbench"/);
  assert.match(app, /el\["board-state"\]\.textContent = view[\s\S]*"Create or choose a board to begin\.";/);
  assert.match(app, /el\["checkpoint-title"\]\.textContent = view[\s\S]*"Waiting for a board";/);
  assert.match(app, /el\["setup-submit-button"\]\.textContent = "Create board";/);
  assert.match(app, /el\["legacy-controls"\]\.classList\.add\("hidden"\)/);
  assert.match(app, /el\["legacy-controls"\]\.classList\.remove\("hidden"\)/);
  assert.match(app, /el\["save-state"\]\.textContent = "Static mode"/);
});

test("app uses guided approval and local-save wording for current revisions", () => {
  assert.match(app, /"Approve & continue"/);
  assert.match(app, /"Save locally"/);
  assert.match(app, /"Saved locally"/);
  assert.doesNotMatch(app, /save hold highlights/i);
  assert.doesNotMatch(app, /edited hold highlights/i);
  assert.match(app, /detail: \(board\) => board\.saved \? "Saved locally" : `Stage \$\{String\(board\.stage \?\? 0\)\} · Unsaved`,/);
  assert.match(app, /runGuidedMutation\(\(options\) => workbenchClient\.finalSave\(state\.board, options\), "Saved to this repository\."\)/);
});

test("server still exposes the legacy Hold Editor CLI entrypoint", () => {
  assert.match(server, /ArgumentParser\(description="Serve the Hold Editor for pipeline-generated onboarding runs"\)/);
  assert.match(server, /help="Persistent workbench workspace; may be combined with legacy run inputs"/);
  assert.match(server, /print\(f"Hold Editor: http:\/\/\{server\.server_address\[0\]\}:\{server\.server_port\}"\)/);
});

test("README documents both the guided workbench flow and the legacy static editor modes", () => {
  assert.match(readme, /^# Hold Editor/m);
  assert.match(readme, /## Run the guided local workbench/);
  assert.match(readme, /select \*\*Create board\*\*/);
  assert.match(readme, /## Edit and save one existing Stage 2 run/);
  assert.match(readme, /## Static mode/);
  assert.match(readme, /legacy\/static mode, unsaved browser edits are lost/);
  assert.match(readme, /Both export buttons remain available in server and static modes as recovery/);
  assert.doesNotMatch(readme, /# Hold Region Editor/);
});
