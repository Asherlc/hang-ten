const test = require("node:test");
const assert = require("node:assert/strict");

const {
  buildEditedDocument,
  buildCorrectionsDocument,
  resizeTransform,
  resizeContour,
  simplifyClosedContour,
  mirrorContour,
  findStrongestEdge,
  resolveHistorySelection,
  normalizePipelineDocument,
  nextStage2RegionId,
  contourPath,
  isExportableContour,
  shiftCornerTreatmentsForInsertion,
  mirrorCornerTreatments,
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

test("buildEditedDocument rejects regions without an exportable contour", () => {
  for (const contour of [[], undefined]) {
    assert.throws(
      () => buildEditedDocument({
        canvas: { width: 100, height: 50 },
        regions: [{ ...baseline, contour }],
        imageName: "stage-1-auto-rgba.png",
        regionsName: "stage-2-regions.json",
      }),
      /Contour must contain at least three points/,
    );
  }
});

test("isExportableContour rejects malformed and non-finite points", () => {
  assert.equal(isExportableContour([[0, 0], [10, 0], [10, 10]]), true);
  assert.equal(isExportableContour([["oops", 0], [10, 0], [10, 10]]), false);
  assert.equal(isExportableContour([[Number.NaN, 0], [10, 0], [10, 10]]), false);
  assert.equal(isExportableContour([[0, 0], [10, 0]]), false);
});

test("buildEditedDocument preserves a valid anchor inside a concave contour", () => {
  const concave = {
    ...baseline,
    anchor: [1, 6],
    contour: [[0, 0], [10, 0], [10, 10], [7, 10], [7, 3], [3, 3], [3, 10], [0, 10]],
  };

  const result = buildEditedDocument({
    canvas: { width: 20, height: 20 },
    regions: [concave],
    imageName: "stage-1-auto-rgba.png",
    regionsName: "stage-2-regions.json",
  });

  assert.deepEqual(result.regions[0].anchor, [1, 6]);
});

test("buildEditedDocument replaces an invalid concave anchor with a deterministic interior pixel", () => {
  const concave = {
    ...baseline,
    anchor: [5, 6],
    contour: [[0, 0], [10, 0], [10, 10], [7, 10], [7, 3], [3, 3], [3, 10], [0, 10]],
  };

  const result = buildEditedDocument({
    canvas: { width: 20, height: 20 },
    regions: [concave],
    imageName: "stage-1-auto-rgba.png",
    regionsName: "stage-2-regions.json",
  });

  assert.deepEqual(result.regions[0].anchor, [5, 2]);
});

test("buildEditedDocument replaces a treated anchor cut away by a rounded corner", () => {
  const rounded = {
    ...baseline,
    anchor: [0, 0],
    contour: [[0, 0], [10, 0], [10, 10], [0, 10]],
    metadata: {
      ...baseline.metadata,
      pathStyle: "straight",
      curveTension: 0.8,
      cornerTreatments: { 0: { treatment: "rounded", amount: 4 } },
    },
  };
  const original = structuredClone(rounded);
  const input = {
    canvas: { width: 20, height: 20 },
    regions: [rounded],
    imageName: "stage-1-auto-rgba.png",
    regionsName: "stage-2-regions.json",
  };

  const first = buildEditedDocument(input);
  const second = buildEditedDocument(input);

  assert.notDeepEqual(first.regions[0].anchor, [0, 0]);
  assert.deepEqual(first.regions[0].anchor, [5, 4]);
  assert.deepEqual(second.regions[0].anchor, [5, 4]);
  assert.deepEqual(rounded, original);
});

test("buildEditedDocument uses Python pixel rounding for a fractional treated anchor", () => {
  const rounded = {
    ...baseline,
    anchor: [2.5, 2],
    contour: [[0, 0], [2.4, 0], [2.4, 5], [0, 5]],
    metadata: {
      ...baseline.metadata,
      pathStyle: "straight",
      curveTension: 0.8,
      cornerTreatments: { 0: { treatment: "rounded", amount: 0.5 } },
    },
  };

  const result = buildEditedDocument({
    canvas: { width: 20, height: 20 },
    regions: [rounded],
    imageName: "stage-1-auto-rgba.png",
    regionsName: "stage-2-regions.json",
  });

  assert.deepEqual(result.regions[0].anchor, [2.5, 2]);
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

test("canSaveEditorState rejects a save already in progress", () => {
  assert.equal(canSaveEditorState({
    serverSession: { id: "board-a" },
    dirty: true,
    saving: true,
    loadingSession: false,
  }), false);
});

test("canSaveEditorState rejects a session still loading", () => {
  assert.equal(canSaveEditorState({
    serverSession: { id: "board-a" },
    dirty: true,
    saving: false,
    loadingSession: true,
  }), false);
});

test("canSaveEditorState rejects a clean editor", () => {
  assert.equal(canSaveEditorState({
    serverSession: { id: "board-a" },
    dirty: false,
    saving: false,
    loadingSession: false,
  }), false);
});

test("canSaveEditorState rejects an editor without a server session", () => {
  assert.equal(canSaveEditorState({
    serverSession: null,
    dirty: true,
    saving: false,
    loadingSession: false,
  }), false);
});

test("a loadSession failure preserves the original snapshot and error", async () => {
  const current = {
    editor: { regions: [baseline], selectedId: 1 },
    visible: { boardValue: "board-a", status: "Selected hold grip-001." },
  };
  const before = structuredClone(current);
  const error = new Error("Could not load the selected board session");

  const result = await runSessionLoadTransaction(current, {
    loadSession: async () => { throw error; },
    loadRegions: async () => { throw new Error("loadRegions should not run"); },
    normalizeRegions: (document) => document,
    loadImage: async () => { throw new Error("loadImage should not run"); },
  });

  assert.equal(result.ok, false);
  assert.strictEqual(result.value, current);
  assert.deepEqual(current, before);
  assert.strictEqual(result.error, error);
});

test("a loadRegions failure preserves the original snapshot and error", async () => {
  const current = {
    editor: { regions: [baseline], selectedId: 1 },
    visible: { boardValue: "board-a", status: "Selected hold grip-001." },
  };
  const before = structuredClone(current);
  const error = new Error("Could not load hold highlights from the run");

  const result = await runSessionLoadTransaction(current, {
    loadSession: async () => ({ id: "board-b", label: "Board B", imageUrl: "/board-b.png", regionsUrl: "/board-b.json" }),
    loadRegions: async () => { throw error; },
    normalizeRegions: (document) => document,
    loadImage: async () => { throw new Error("loadImage should not run"); },
  });

  assert.equal(result.ok, false);
  assert.strictEqual(result.value, current);
  assert.deepEqual(current, before);
  assert.strictEqual(result.error, error);
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

test("mixed Stage 2 corner treatments route only rounded vertices and clamp to adjacent edges", () => {
  const points = [[0, 0], [10, 0], [10, 10], [0, 10]];
  const treatments = {
    0: { treatment: "sharp", amount: 3 },
    1: { treatment: "rounded", amount: 100 },
  };

  assert.equal(
    contourPath(points, "straight", 0.8, treatments),
    "M 0 0 L 5 0 Q 10 0 10 5 L 10 10 L 0 10 L 0 0 Z",
  );
});

test("Stage 2 corner metadata shifts on insertion and remaps to mirrored winding", () => {
  const treatments = {
    1: { treatment: "rounded", amount: 4 },
    3: { treatment: "sharp", amount: 2 },
  };

  const shifted = shiftCornerTreatmentsForInsertion(treatments, 2, 4);
  assert.deepEqual(shifted, {
    1: { treatment: "rounded", amount: 4 },
    4: { treatment: "sharp", amount: 2 },
  });
  assert.deepEqual(mirrorCornerTreatments(shifted, 5), {
    3: { treatment: "rounded", amount: 4 },
    0: { treatment: "sharp", amount: 2 },
  });
  assert.deepEqual(treatments, {
    1: { treatment: "rounded", amount: 4 },
    3: { treatment: "sharp", amount: 2 },
  });
});

test("correction comparison detects a per-corner treatment-only change", () => {
  const changed = structuredClone(baseline);
  changed.metadata.cornerTreatments = { 1: { treatment: "rounded", amount: 4 } };

  const result = buildCorrectionsDocument({ baselineRegions: [baseline], regions: [changed] });

  assert.equal(result.summary.modified, 1);
});

test("Stage 2 corner helpers reject malformed data without mutating inputs", () => {
  const points = [[0, 0], [10, 0], [10, 10]];
  const treatments = { 1: { treatment: "rounded", amount: 2 } };
  const originalPoints = structuredClone(points);
  const originalTreatments = structuredClone(treatments);

  assert.throws(() => contourPath(points, "straight", 0.8, { 3: treatments[1] }), /index/i);
  assert.throws(() => contourPath(points, "straight", 0.8, { 1: { treatment: "soft", amount: 2 } }), /treatment/i);
  assert.throws(() => contourPath(points, "straight", 0.8, { 1: { treatment: "rounded", amount: 0 } }), /amount/i);
  assert.throws(() => shiftCornerTreatmentsForInsertion(treatments, -1, points.length), /index/i);
  assert.deepEqual(points, originalPoints);
  assert.deepEqual(treatments, originalTreatments);
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

test("resizeContour uses the dominant horizontal corner scale when preserving aspect ratio", () => {
  const result = resizeContour({
    points: [[0, 0], [10, 0], [10, 10], [0, 10]],
    rotation: 0,
    handle: "se",
    pointer: [30, 15],
    preserveAspect: true,
  });

  assert.deepEqual(result, [[0, 0], [30, 0], [30, 30], [0, 30]]);
});

test("resizeTransform remains finite for a zero-width point set", () => {
  const points = [[2, 0], [2, 10], [2, 5]];
  const matrix = resizeTransform({
    points,
    rotation: 0,
    handle: "e",
    pointer: [5, 5],
  });

  assert.equal(matrix.every(Number.isFinite), true);
  assert.deepEqual(resizeContour({ points, handle: "e", pointer: [5, 5] }), points);
});

test("resizeContour clamps a handle dragged past its anchor without flipping", () => {
  const result = resizeContour({
    points: [[0, 0], [10, 0], [10, 10], [0, 10]],
    rotation: 0,
    handle: "e",
    pointer: [-10, 5],
  });

  assert.deepEqual(result, [[0, 0], [6, 0], [6, 10], [0, 10]]);
});

test("resizeContour uses signed local deltas for every side and corner handle", () => {
  const points = [[0, 0], [10, 0], [10, 10], [0, 10]];
  const cases = [
    ["n", [5, -10], [0, -10, 10, 10]],
    ["s", [5, 20], [0, 0, 10, 20]],
    ["w", [-10, 5], [-10, 0, 10, 10]],
    ["e", [20, 5], [0, 0, 20, 10]],
    ["nw", [-10, -20], [-10, -20, 10, 10]],
    ["ne", [20, -20], [0, -20, 20, 10]],
    ["sw", [-10, 20], [-10, 0, 10, 20]],
    ["se", [20, 20], [0, 0, 20, 20]],
  ];

  for (const [handle, pointer, expectedBounds] of cases) {
    const resized = resizeContour({ points, handle, pointer });
    const xs = resized.map(([x]) => x);
    const ys = resized.map(([, y]) => y);
    assert.deepEqual(
      [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)],
      expectedBounds,
      handle,
    );
  }
});

test("resizeTransform scales rotated vector geometry in its local frame", () => {
  const points = [[10, 0], [10, 10], [0, 10], [0, 0]];
  const matrix = resizeTransform({
    points,
    rotation: Math.PI / 2,
    handle: "e",
    pointer: [5, 15],
  });
  const transformed = points.map(([x, y]) => [
    Math.round((matrix[0] * x + matrix[2] * y + matrix[4]) * 1e8) / 1e8,
    Math.round((matrix[1] * x + matrix[3] * y + matrix[5]) * 1e8) / 1e8,
  ]);

  assert.deepEqual(transformed, [[10, 0], [10, 15], [0, 15], [0, 0]]);
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

test("normalizePipelineDocument keeps Stage 3 display paths exact", () => {
  const source = { width: 1000, height: 300, regions: [{ id: 13, key: "hold-13", type: "edge", displayPath: "M 10 20 C 15 10 25 10 30 20 Z" }] };
  const result = normalizePipelineDocument(source, { width: 10, height: 10 }, "vector");
  assert.equal(result.regions[0].displayPath, source.regions[0].displayPath);
  assert.equal(result.editorMode, "vector");
});

test("nextStage2RegionId never reuses deleted generated or allocated IDs", () => {
  const baselineRegions = [{ id: 1 }, { id: 2 }, { id: 7 }];
  const regions = [{ id: 2 }, { id: 8 }];

  assert.equal(nextStage2RegionId({ baselineRegions, regions, nextRegionId: 9 }), 9);
  assert.equal(nextStage2RegionId({ baselineRegions, regions, nextRegionId: 6 }), 9);
});
