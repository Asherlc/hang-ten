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
  shiftCornerTreatmentsForInsertion,
  mirrorCornerTreatments,
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
