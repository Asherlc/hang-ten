const test = require("node:test");
const assert = require("node:assert/strict");

const {
  buildEditedDocument,
  buildCorrectionsDocument,
  resizeContour,
  simplifyClosedContour,
  mirrorContour,
  findStrongestEdge,
  resolveHistorySelection,
  normalizePipelineDocument,
  canSaveEditorState,
  runSessionLoadTransaction,
  formatSessionLoadError,
} = require("../editor-model.js");

const baseline = {
  id: 1,
  key: "grip-001",
  type: "edge",
  contour: [[0, 0], [10, 0], [10, 10]],
  metadata: { mode: "surface", shapeKind: "freeform" },
};

test("buildEditedDocument returns a detached complete artifact", () => {
  const regions = [baseline];
  const result = buildEditedDocument({
    canvas: { width: 100, height: 50 },
    regions,
    imageName: "stage-1-auto-rgba.png",
    regionsName: "stage-2-regions.json",
  });

  assert.deepEqual(result.canvas, { width: 100, height: 50 });
  assert.deepEqual(result.regions[0].contour, regions[0].contour);
  assert.equal(result.regions[0].metadata.editedBy, "hold-highlight-editor");
  assert.equal(result.editor.name, "hold-highlight-editor");
  result.regions[0].key = "changed";
  assert.equal(regions[0].key, "grip-001");
});

test("buildCorrectionsDocument identifies added modified and deleted regions", () => {
  const modified = { ...baseline, contour: [[1, 0], [10, 0], [10, 10]] };
  const added = { ...baseline, id: 3, key: "grip-003" };
  const deleted = { ...baseline, id: 2, key: "grip-002" };

  const result = buildCorrectionsDocument({
    baselineRegions: [baseline, deleted],
    regions: [modified, added],
  });

  assert.deepEqual(result.summary, { added: 1, modified: 1, deleted: 1 });
  assert.deepEqual(result.added.map((region) => region.id), [3]);
  assert.deepEqual(result.modified.map((change) => change.after.id), [1]);
  assert.deepEqual(result.deleted, [{ id: 2, key: "grip-002" }]);
});

test("deleting the final highlight stays saveable and emits its deletion correction", () => {
  assert.equal(canSaveEditorState({
    serverSession: { id: "board-a" },
    regions: [],
    dirty: true,
    saving: false,
    loadingSession: false,
  }), true);

  const edited = buildEditedDocument({
    canvas: { width: 100, height: 50 },
    regions: [],
    imageName: "stage-1-auto-rgba.png",
    regionsName: "stage-2-regions.json",
  });
  const corrections = buildCorrectionsDocument({
    baselineRegions: [baseline],
    regions: [],
    imageName: "stage-1-auto-rgba.png",
    regionsName: "stage-2-regions.json",
  });

  assert.deepEqual(edited.regions, []);
  assert.deepEqual(corrections.summary, { added: 0, modified: 0, deleted: 1 });
  assert.deepEqual(corrections.deleted, [{ id: 1, key: "grip-001" }]);
});

test("a failed session transaction preserves the complete editing document and visible state", async () => {
  const current = {
    editor: {
      canvas: { width: 100, height: 50 },
      imageHref: "/api/artifact/image?run=board-a",
      imageName: "board-a.png",
      regionsName: "board-a-regions.json",
      regions: [baseline],
      baselineRegions: [baseline],
      selectedId: 1,
      history: [{ snapshot: JSON.stringify([baseline]), label: "Loaded hold highlights", selectedId: 1 }],
      historyIndex: 0,
      savedSnapshot: JSON.stringify([baseline]),
      dirty: true,
      serverSession: { id: "board-a" },
    },
    visible: {
      boardValue: "board-a",
      status: "Selected hold grip-001.",
      imageHref: "/api/artifact/image?run=board-a",
      staticControlsHidden: true,
    },
  };
  const before = structuredClone(current);

  const result = await runSessionLoadTransaction(current, {
    loadSession: async () => ({ id: "board-b", label: "Board B", imageUrl: "/board-b.png", regionsUrl: "/board-b.json" }),
    loadRegions: async () => ({ canvas: { width: 200, height: 80 }, regions: [] }),
    normalizeRegions: (document) => document,
    loadImage: async () => {
      throw new Error("Board image failed to load");
    },
  });

  assert.equal(result.ok, false);
  assert.strictEqual(result.value, current);
  assert.deepEqual(current, before);
  assert.equal(result.error.message, "Board image failed to load");
});

test("a successful session transaction returns the fully staged replacement", async () => {
  const current = { editor: { regions: [baseline] }, visible: { boardValue: "board-a" } };
  const session = { id: "board-b", label: "Board B", imageUrl: "/board-b.png", regionsUrl: "/board-b.json" };
  const normalized = { canvas: { width: 200, height: 80 }, regions: [] };
  const imageAsset = { image: { naturalWidth: 200, naturalHeight: 80 }, imagePixels: null };

  const result = await runSessionLoadTransaction(current, {
    loadSession: async () => session,
    loadRegions: async () => ({ width: 200, height: 80, regions: [] }),
    normalizeRegions: () => normalized,
    loadImage: async () => imageAsset,
  });

  assert.equal(result.ok, true);
  assert.deepEqual(result.value, { session, normalized, imageAsset });
  assert.equal(result.error, null);
});

test("a successful session transaction gives normalization the incoming image dimensions", async () => {
  const result = await runSessionLoadTransaction({ editor: {}, visible: {} }, {
    loadSession: async () => ({ id: "board-b" }),
    loadRegions: async () => ({ regions: [] }),
    normalizeRegions: (document, fallbackCanvas) => normalizePipelineDocument(document, fallbackCanvas),
    loadImage: async () => ({ image: { naturalWidth: 240, naturalHeight: 120 }, imagePixels: null }),
  });

  assert.deepEqual(result.value.normalized.canvas, { width: 240, height: 120 });
});

test("session load errors become specific user-facing status without exposing unexpected values", () => {
  assert.equal(
    formatSessionLoadError(new Error("Board image failed to load")),
    "Could not load the selected board. Please try again.",
  );
  assert.equal(
    formatSessionLoadError(new Error("Could not load hold highlights from the run")),
    "Could not load the selected board: Could not load hold highlights from the run",
  );
});

test("curve and transform metadata count as modifications", () => {
  const changed = JSON.parse(JSON.stringify(baseline));
  changed.metadata.rotation = 0.25;
  changed.metadata.bend = 12;

  const result = buildCorrectionsDocument({ baselineRegions: [baseline], regions: [changed] });

  assert.equal(result.summary.modified, 1);
});

test("resizeContour scales a corner around its opposite corner", () => {
  const result = resizeContour({
    points: [[0, 0], [10, 0], [10, 10], [0, 10]],
    rotation: 0,
    handle: "se",
    pointer: [20, 30],
    preserveAspect: false,
  });

  assert.deepEqual(result, [[0, 0], [20, 0], [20, 30], [0, 30]]);
});

test("resizeContour limits a side handle to one local axis", () => {
  const result = resizeContour({
    points: [[0, 0], [10, 0], [10, 10], [0, 10]],
    rotation: 0,
    handle: "e",
    pointer: [20, 30],
    preserveAspect: false,
  });

  assert.deepEqual(result, [[0, 0], [20, 0], [20, 10], [0, 10]]);
});

test("resizeContour preserves aspect ratio from corner handles", () => {
  const result = resizeContour({
    points: [[0, 0], [10, 0], [10, 10], [0, 10]],
    rotation: 0,
    handle: "se",
    pointer: [20, 30],
    preserveAspect: true,
  });

  assert.deepEqual(result, [[0, 0], [30, 0], [30, 30], [0, 30]]);
});

test("mirrorContour reflects across the canvas center and reverses winding", () => {
  assert.deepEqual(
    mirrorContour([[10, 5], [20, 5], [20, 10]], 100),
    [[80, 10], [80, 5], [90, 5]],
  );
});

test("simplifyClosedContour removes redundant controls from a closed outline", () => {
  const denseRectangle = [
    [0, 0], [5, 0], [10, 0], [10, 5], [10, 10], [5, 10], [0, 10], [0, 5],
  ];

  const result = simplifyClosedContour(denseRectangle, 0.1);

  assert.equal(result.length, 4);
  assert.deepEqual(new Set(result.map((point) => point.join(","))), new Set(["0,0", "10,0", "10,10", "0,10"]));
});

test("findStrongestEdge snaps to a nearby high-contrast boundary", () => {
  const width = 20;
  const height = 10;
  const rgba = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const value = x < 10 ? 0 : 255;
      const offset = (y * width + x) * 4;
      rgba.set([value, value, value, 255], offset);
    }
  }

  assert.deepEqual(findStrongestEdge({ rgba, width, height, point: [8, 5], radius: 5, threshold: 20 }), [9, 5]);
  assert.equal(findStrongestEdge({ rgba, width, height, point: [2, 5], radius: 2, threshold: 20 }), null);
});

test("resolveHistorySelection restores the selection stored with an undo snapshot", () => {
  const regions = [{ id: 1 }, { id: 2 }];

  assert.equal(resolveHistorySelection({ selectedId: 1 }, regions, 20), 1);
  assert.equal(resolveHistorySelection({}, regions, 2), 2);
  assert.equal(resolveHistorySelection({ selectedId: 9 }, regions, 20), null);
});

test("normalizePipelineDocument adapts historical generated region artifacts", () => {
  const result = normalizePipelineDocument({
    width: 1000,
    height: 259,
    regions: [{
      id: "piece-01-hold-01",
      type: "sloper",
      visualMode: "surface",
      contour: [[1, 2], [3, 4], [5, 6]],
    }],
  }, { width: 10, height: 10 });

  assert.deepEqual(result.canvas, { width: 1000, height: 259 });
  assert.equal(result.regions[0].id, 1);
  assert.equal(result.regions[0].key, "piece-01-hold-01");
  assert.equal(result.regions[0].metadata.mode, "surface");
  assert.equal(result.regions[0].metadata.sourceRegionId, "piece-01-hold-01");
});
