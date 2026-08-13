const test = require("node:test");
const assert = require("node:assert/strict");

const {
  advancedToolVisibility,
  formatFocusedEditorDiagnostic,
  formatFocusedEditorError,
} = require("../editor-ui-model.js");

test("freeform contour holds expose outline, assists, and details", () => {
  assert.deepEqual(advancedToolVisibility({
    region: { metadata: { shapeKind: "freeform" } },
    editorMode: "contour", editable: true, hasImagePixels: true,
  }), {
    outline: true, transform: true, assists: true, details: true, edgeSnap: true,
  });
});

test("primitive contour holds expose all editable contour tools", () => {
  assert.deepEqual(advancedToolVisibility({
    region: { metadata: { shapeKind: "rectangle" } },
    editorMode: "contour", editable: true, hasImagePixels: true,
  }), {
    outline: true, transform: true, assists: true, details: true, edgeSnap: true,
  });
});

test("vector and no-selection states expose no contour expert controls", () => {
  assert.deepEqual(advancedToolVisibility({
    region: null, editorMode: "contour", editable: true, hasImagePixels: true,
  }), { outline: false, transform: false, assists: false, details: false, edgeSnap: false });
  assert.deepEqual(advancedToolVisibility({
    region: { metadata: { shapeKind: "freeform" } },
    editorMode: "vector", editable: true, hasImagePixels: true,
  }), { outline: false, transform: false, assists: false, details: true, edgeSnap: false });
});

test("Stage 2 hold errors use outline language while retaining the hold and reason", () => {
  const message = formatFocusedEditorError(
    "Stage 2 region 17: contour is invalid because two points overlap",
    "Could not save outline changes",
  );

  assert.equal(message, "Hold 17: outline is invalid because two points overlap");
  assert.doesNotMatch(message, /\b(?:stage|checkpoint|promotion|approval|validation)\b/i);
  assert.match(message, /\b17\b/);
  assert.match(message, /two points overlap/);
});

test("Stage 3 hold errors use task language while retaining exact diagnostic details", () => {
  const message = formatFocusedEditorError(
    "Stage 3 region 4: malformed displayPath at command Q7",
    "Could not load board",
  );

  assert.equal(message, "Hold 4: malformed displayPath at command Q7");
  assert.doesNotMatch(message, /\b(?:stage|checkpoint|promotion|approval|validation)\b/i);
  assert.match(message, /\b4\b/);
  assert.match(message, /displayPath at command Q7/);
});

test("other pipeline terms are translated without discarding diagnostic identifiers", () => {
  const message = formatFocusedEditorError(
    "Stage 4 approval validation failed at checkpoint board-abc; promotion blocked for checkpointToken",
    "Workbench action failed",
  );

  assert.equal(
    message,
    "Board data outline save outline check failed at saved board version board-abc; repository update blocked for checkpointToken",
  );
  assert.doesNotMatch(
    message.replace("checkpointToken", ""),
    /\b(?:stage|checkpoint|promotion|approval|validation)\b/i,
  );
  assert.match(message, /board-abc/);
  assert.match(message, /checkpointToken/);
});

test("technical filenames, routes, and field identifiers survive surrounding workflow translation", () => {
  const message = formatFocusedEditorError(
    "Stage 2 validation failed for stage-2-regions.json at /promotion because checkpointToken was rejected",
    "Could not load board",
  );

  assert.equal(
    message,
    "Detected hold outlines outline check failed for stage-2-regions.json at /promotion because checkpointToken was rejected",
  );
  const surroundingSentence = message
    .replace("stage-2-regions.json", "")
    .replace("/promotion", "")
    .replace("checkpointToken", "");
  assert.doesNotMatch(
    surroundingSentence,
    /\b(?:stage|checkpoint|promotion|approval|validation)\b/i,
  );
});

test("repository diagnostic formatting changes only the visible message", () => {
  const diagnostic = {
    path: "boards/stage-2-regions.json",
    code: "invalid_run",
    severity: "warning",
    holdId: "hold-17",
    reason: "contour overlaps itself at checkpointToken",
    message: "Stage 2 region 17 failed validation: contour overlaps itself",
  };

  const formatted = formatFocusedEditorDiagnostic(diagnostic);

  assert.deepEqual(formatted, {
    ...diagnostic,
    message: "Hold 17 failed outline check: outline overlaps itself",
  });
  assert.notEqual(formatted, diagnostic);
  assert.equal(formatted.holdId, "hold-17");
  assert.equal(formatted.reason, "contour overlaps itself at checkpointToken");
});

test("empty external errors retain the action-specific fallback", () => {
  assert.equal(formatFocusedEditorError("", "Could not load board"), "Could not load board");
});
