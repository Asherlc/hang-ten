import assert from "node:assert/strict";
import test from "node:test";

import {
  addInflectionPoint,
  addVertex,
  constrainedOutlineModel,
  createOutlineShapePath,
  deleteVertex,
  isInflectionVertex,
  makeSegmentBendable,
  makeSegmentStraight,
  moveVertex,
  parsePath,
  roundVertex,
  resizeConstrainedOutline,
  rotatePath,
  serializePath,
  snapSegmentHorizontal,
  snapSegmentVertical,
} from "../src/path-editor.ts";
import { validateEditorDocument } from "../src/workbench-controller.ts";
import type {
  Bounds,
  ConstrainedHandle,
  OutlinePreset,
  PathCommand,
  Point,
  ShapeConstraint,
} from "../src/types.ts";

function assertPoint(actual: Point, expected: Point): void {
  assert.ok(Math.abs(actual.x - expected.x) < 1e-6, `expected x=${expected.x}, got ${actual.x}`);
  assert.ok(Math.abs(actual.y - expected.y) < 1e-6, `expected y=${expected.y}, got ${actual.y}`);
}

function assertBounds(actual: Bounds, expected: Bounds): void {
  for (const key of ["minX", "minY", "maxX", "maxY"] as const) {
    assert.ok(Math.abs(actual[key] - expected[key]) < 1e-6, `expected ${key}=${expected[key]}, got ${actual[key]}`);
  }
}

test("parsePath splits an SVG path string into commands", () => {
  const commands = parsePath("M 10 20 L 30 40 Q 50 60 70 80 C 10 20 30 40 50 60 Z");
  assert.equal(commands.length, 5);
  assert.equal(commands[0]?.type, "M");
  assert.deepEqual(commands[0]?.points, [{ x: 10, y: 20 }]);
  assert.equal(commands[1]?.type, "L");
  assert.deepEqual(commands[1]?.points, [{ x: 30, y: 40 }]);
  assert.equal(commands[2]?.type, "Q");
  assert.deepEqual(commands[2]?.points, [{ x: 70, y: 80 }]);
  assert.deepEqual(commands[2]?.controls, [{ x: 50, y: 60 }]);
  assert.equal(commands[3]?.type, "C");
  assert.deepEqual(commands[3]?.points, [{ x: 50, y: 60 }]);
  assert.deepEqual(commands[3]?.controls, [{ x: 10, y: 20 }, { x: 30, y: 40 }]);
  assert.equal(commands[4]?.type, "Z");
});

test("parsePath handles a simple triangle", () => {
  const commands = parsePath("M 0 0 L 100 0 L 50 80 Z");
  assert.equal(commands.length, 4);
  assert.equal(commands[0]?.type, "M");
  assert.equal(commands[3]?.type, "Z");
});

test("serializePath reconstructs an SVG path string", () => {
  const input = "M 10 20 L 30 40 Q 50 60 70 80 C 10 20 30 40 50 60 Z";
  assert.equal(serializePath(parsePath(input)), input);
});

test("serializePath handles integer coordinates cleanly", () => {
  const commands: PathCommand[] = [
    { type: "M", points: [{ x: 0, y: 0 }], controls: [] },
    { type: "L", points: [{ x: 100, y: 0 }], controls: [] },
    { type: "L", points: [{ x: 50, y: 80 }], controls: [] },
    { type: "Z", points: [], controls: [] },
  ];
  assert.equal(serializePath(commands), "M 0 0 L 100 0 L 50 80 Z");
});

test("makeSegmentBendable replaces a straight segment with a geometrically identical cubic", () => {
  const commands = parsePath("M 0 0 L 10 0 L 10 10 Z");

  assert.equal(makeSegmentBendable(commands, 0), true);
  assert.equal(serializePath(commands), "M 0 0 C 3.333333 0 6.666667 0 10 0 L 10 10 Z");
  assert.equal(makeSegmentBendable(commands, 0), false, "curves cannot be converted twice");
});

test("makeSegmentBendable converts a closing edge while retaining one final close command", () => {
  const commands = parsePath("M 0 0 L 10 0 L 10 10 Z");

  assert.equal(makeSegmentBendable(commands, 2), true);
  assert.equal(serializePath(commands), "M 0 0 L 10 0 L 10 10 C 6.666667 6.666667 3.333333 3.333333 0 0 Z");
  assert.equal(commands.filter((command) => command.type === "M").length, 1);
  assert.equal(commands.filter((command) => command.type === "Z").length, 1);
  assert.equal(commands.at(-1)?.type, "Z");
});

test("makeSegmentStraight replaces quadratic and cubic segments with lines to their existing endpoints", () => {
  for (const [path, expected] of [
    ["M 0 0 Q 5 10 10 0 L 10 10 Z", "M 0 0 L 10 0 L 10 10 Z"],
    ["M 0 0 C 2 10 8 10 10 0 L 10 10 Z", "M 0 0 L 10 0 L 10 10 Z"],
  ] as const) {
    const commands = parsePath(path);

    assert.equal(makeSegmentStraight(commands, 0), true, path);
    assert.equal(serializePath(commands), expected, path);
    assert.equal(makeSegmentStraight(commands, 0), false, "straight segments cannot be converted twice");
  }
});

test("makeSegmentStraight replaces a closing curve while retaining one final close command", () => {
  const commands = parsePath("M 0 0 L 10 0 L 10 10 Q 4 14 0 0 Z");

  assert.equal(makeSegmentStraight(commands, 2), true);
  assert.equal(serializePath(commands), "M 0 0 L 10 0 L 10 10 L 0 0 Z");
  assert.equal(commands.filter((command) => command.type === "M").length, 1);
  assert.equal(commands.filter((command) => command.type === "Z").length, 1);
  assert.equal(commands.at(-1)?.type, "Z");
});

test("snapSegmentHorizontal preserves a straight segment start while aligning its endpoint", () => {
  const commands = parsePath("M 0 0 L 10 5 L 20 10 Z");

  assert.equal(snapSegmentHorizontal(commands, 0), true);
  assert.equal(serializePath(commands), "M 0 0 L 10 0 L 20 10 Z");
});

test("snapSegmentVertical preserves a straight segment start while aligning its endpoint", () => {
  const commands = parsePath("M 0 0 L 10 5 L 20 10 Z");

  assert.equal(snapSegmentVertical(commands, 0), true);
  assert.equal(serializePath(commands), "M 0 0 L 0 5 L 20 10 Z");
});

test("axis snapping materializes an aligned closing edge while retaining one final close command", () => {
  for (const [snap, expected] of [
    [snapSegmentHorizontal, "M 0 0 L 10 0 L 10 10 L 2 8 L 0 8 Z"],
    [snapSegmentVertical, "M 0 0 L 10 0 L 10 10 L 2 8 L 2 0 Z"],
  ] as const) {
    const commands = parsePath("M 0 0 L 10 0 L 10 10 L 2 8 Z");

    assert.equal(snap(commands, 3), true, expected);
    assert.equal(serializePath(commands), expected);
    assert.equal(commands.filter((command) => command.type === "M").length, 1);
    assert.equal(commands.filter((command) => command.type === "Z").length, 1);
    assert.equal(commands.at(-1)?.type, "Z");
  }
});

test("axis snapping leaves curves and already aligned straight segments unchanged", () => {
  for (const [snap, path, afterIndex] of [
    [snapSegmentHorizontal, "M 0 0 L 10 0 L 10 10 Z", 0],
    [snapSegmentVertical, "M 0 0 L 0 10 L 10 10 Z", 0],
    [snapSegmentHorizontal, "M 0 0 Q 5 10 10 0 L 10 10 Z", 0],
    [snapSegmentVertical, "M 0 0 Q 5 10 10 0 L 10 10 Z", 0],
  ] as const) {
    const commands = parsePath(path);

    assert.equal(snap(commands, afterIndex), false, path);
    assert.equal(serializePath(commands), path);
  }
});

test("roundVertex trims adjacent straight segments and retains the sharp point as the quadratic control", () => {
  const commands = parsePath("M 0 0 L 10 0 L 10 10 L 0 10 Z");

  assert.equal(roundVertex(commands, 1), true);
  assert.equal(serializePath(commands), "M 0 0 L 8 0 Q 10 0 10 2 L 10 10 L 0 10 Z");
});

test("roundVertex rounds the first vertex through the closing edge without changing closure structure", () => {
  const commands = parsePath("M 0 0 L 10 0 L 10 10 L 0 10 Z");

  assert.equal(roundVertex(commands, 0), true);
  assert.equal(serializePath(commands), "M 0 2 Q 0 0 2 0 L 10 0 L 10 10 L 0 10 Z");
  assert.equal(commands.filter((command) => command.type === "M").length, 1);
  assert.equal(commands.filter((command) => command.type === "Z").length, 1);
  assert.equal(commands.at(-1)?.type, "Z");
});

test("roundVertex rounds the last vertex through the closing edge without changing closure structure", () => {
  const commands = parsePath("M 0 0 L 10 0 L 10 10 L 0 10 Z");

  assert.equal(roundVertex(commands, 3), true);
  assert.equal(serializePath(commands), "M 0 0 L 10 0 L 10 10 L 2 10 Q 0 10 0 8 Z");
  assert.equal(commands.filter((command) => command.type === "M").length, 1);
  assert.equal(commands.filter((command) => command.type === "Z").length, 1);
  assert.equal(commands.at(-1)?.type, "Z");
});

test("roundVertex leaves degenerate and curved vertices unchanged", () => {
  for (const [path, index] of [
    ["M 0 0 L 10 0 L 20 0 Z", 1],
    ["M 0 0 Q 5 0 10 0 L 10 10 Z", 1],
  ] as const) {
    const commands = parsePath(path);
    assert.equal(roundVertex(commands, index), false, path);
    assert.equal(serializePath(commands), path);
  }
});

test("createOutlineShapePath replaces an outline with an oval inside the same bounding box", () => {
  assert.equal(
    createOutlineShapePath("M 10 20 L 50 20 L 50 40 L 10 40 Z", "oval"),
    "M 30 20 C 41.045695 20 50 24.477153 50 30 C 50 35.522847 41.045695 40 30 40 C 18.954305 40 10 35.522847 10 30 C 10 24.477153 18.954305 20 30 20 Z",
  );
});

test("createOutlineShapePath centers a circle and constrains its diameter to the shorter source dimension", () => {
  assert.equal(
    createOutlineShapePath("M 10 20 L 50 20 L 50 40 L 10 40 Z", "circle"),
    "M 30 20 C 35.522847 20 40 24.477153 40 30 C 40 35.522847 35.522847 40 30 40 C 24.477153 40 20 35.522847 20 30 C 20 24.477153 24.477153 20 30 20 Z",
  );
});

test("createOutlineShapePath generates every preset as a valid closed contour", () => {
  const source = "M 10 20 L 50 20 L 50 40 L 10 40 Z";
  const expectedPaths = {
    oval: "M 30 20 C 41.045695 20 50 24.477153 50 30 C 50 35.522847 41.045695 40 30 40 C 18.954305 40 10 35.522847 10 30 C 10 24.477153 18.954305 20 30 20 Z",
    circle: "M 30 20 C 35.522847 20 40 24.477153 40 30 C 40 35.522847 35.522847 40 30 40 C 24.477153 40 20 35.522847 20 30 C 20 24.477153 24.477153 20 30 20 Z",
    pill: "M 20 20 L 40 20 C 45.522847 20 50 24.477153 50 30 C 50 35.522847 45.522847 40 40 40 L 20 40 C 14.477153 40 10 35.522847 10 30 C 10 24.477153 14.477153 20 20 20 Z",
    "rounded-rectangle": "M 14 20 L 46 20 C 48.209139 20 50 21.790861 50 24 L 50 36 C 50 38.209139 48.209139 40 46 40 L 14 40 C 11.790861 40 10 38.209139 10 36 L 10 24 C 10 21.790861 11.790861 20 14 20 Z",
    rectangle: "M 10 20 L 50 20 L 50 40 L 10 40 Z",
  } satisfies Record<OutlinePreset, string>;

  for (const [preset, expectedPath] of Object.entries(expectedPaths) as Array<[OutlinePreset, string]>) {
    const displayPath = createOutlineShapePath(source, preset);
    assert.equal(displayPath, expectedPath, preset);
    assert.equal(parsePath(displayPath).at(-1)?.type, "Z", preset);
    assert.doesNotThrow(() => validateEditorDocument({
      schemaVersion: 1,
      canvas: { width: 100, height: 50 },
      regions: [{ key: "hold-1", displayPath }],
    }), preset);
  }
});

test("createOutlineShapePath creates a vertical pill inside the source bounds", () => {
  assert.equal(
    createOutlineShapePath("M 10 10 L 30 10 L 30 70 L 10 70 Z", "pill"),
    "M 10 20 L 10 60 C 10 65.522847 14.477153 70 20 70 C 25.522847 70 30 65.522847 30 60 L 30 20 C 30 14.477153 25.522847 10 20 10 C 14.477153 10 10 14.477153 10 20 Z",
  );
});

test("createOutlineShapePath uses a quadratic curve's true extrema instead of its control point", () => {
  assert.equal(
    createOutlineShapePath("M 0 0 Q 100 100 200 0 L 200 40 L 0 40 Z", "oval"),
    "M 100 0 C 155.228475 0 200 11.192881 200 25 C 200 38.807119 155.228475 50 100 50 C 44.771525 50 0 38.807119 0 25 C 0 11.192881 44.771525 0 100 0 Z",
  );
});

test("createOutlineShapePath uses a cubic curve's true extrema instead of its control points", () => {
  assert.equal(
    createOutlineShapePath("M 0 0 C 0 120 200 120 200 0 L 200 60 L 0 60 Z", "oval"),
    "M 100 0 C 155.228475 0 200 20.147186 200 45 C 200 69.852814 155.228475 90 100 90 C 44.771525 90 0 69.852814 0 45 C 0 20.147186 44.771525 0 100 0 Z",
  );
});

test("constrainedOutlineModel exposes an unrotated rectangle's intrinsic bounds and all eight handles", () => {
  const model = constrainedOutlineModel(
    "M 10 20 L 50 20 L 50 40 L 10 40 Z",
    { shape: "rectangle", rotationDegrees: 0 },
  );

  assertPoint(model.center, { x: 30, y: 30 });
  assert.equal(model.rotationDegrees, 0);
  assertBounds(model.intrinsicBounds, { minX: 10, minY: 20, maxX: 50, maxY: 40 });
  assert.deepEqual(model.handles, {
    nw: { x: 10, y: 20 },
    n: { x: 30, y: 20 },
    ne: { x: 50, y: 20 },
    e: { x: 50, y: 30 },
    se: { x: 50, y: 40 },
    s: { x: 30, y: 40 },
    sw: { x: 10, y: 40 },
    w: { x: 10, y: 30 },
  });
});

test("constrainedOutlineModel inverse-rotates a rectangle and maps its handles back to world space", () => {
  const model = constrainedOutlineModel(
    "M 40 10 L 40 50 L 20 50 L 20 10 Z",
    { shape: "rectangle", rotationDegrees: 90 },
  );

  assertPoint(model.center, { x: 30, y: 30 });
  assert.equal(model.rotationDegrees, 90);
  assertBounds(model.intrinsicBounds, { minX: 10, minY: 20, maxX: 50, maxY: 40 });
  for (const [handle, expected] of Object.entries({
    nw: { x: 40, y: 10 },
    n: { x: 40, y: 30 },
    ne: { x: 40, y: 50 },
    e: { x: 30, y: 50 },
    se: { x: 20, y: 50 },
    s: { x: 20, y: 30 },
    sw: { x: 20, y: 10 },
    w: { x: 30, y: 10 },
  })) assertPoint(model.handles[handle as ConstrainedHandle], expected);
});

test("constrainedOutlineModel rejects rotations outside the normalized range", () => {
  const path = "M 10 20 L 50 20 L 50 40 L 10 40 Z";

  for (const rotationDegrees of [-181, 180, 450]) {
    assert.throws(
      () => constrainedOutlineModel(path, { shape: "rectangle", rotationDegrees }),
      /normalized to \[-180, 180\)/,
      String(rotationDegrees),
    );
  }
});

test("constrainedOutlineModel rejects constraint metadata with unexpected fields", () => {
  assert.throws(
    () => constrainedOutlineModel(
      "M 10 20 L 50 20 L 50 40 L 10 40 Z",
      { shape: "rectangle", rotationDegrees: 0, legacyShape: "oval" },
    ),
    /exactly shape and rotationDegrees/,
  );
});

test("constrainedOutlineModel uses true quadratic and cubic extrema", () => {
  const quadratic = constrainedOutlineModel(
    "M 0 0 Q 100 100 200 0 L 200 40 L 0 40 Z",
    { shape: "rectangle", rotationDegrees: 0 },
  );
  const cubic = constrainedOutlineModel(
    "M 0 0 C 0 120 200 120 200 0 L 200 60 L 0 60 Z",
    { shape: "rectangle", rotationDegrees: 0 },
  );

  assertPoint(quadratic.center, { x: 100, y: 25 });
  assertBounds(quadratic.intrinsicBounds, { minX: 0, minY: 0, maxX: 200, maxY: 50 });
  assertPoint(cubic.center, { x: 100, y: 45 });
  assertBounds(cubic.intrinsicBounds, { minX: 0, minY: 0, maxX: 200, maxY: 90 });
});

test("resizeConstrainedOutline supports every rectangle handle while fixing its opposite edge or corner", () => {
  const source = "M 0 0 L 10 0 L 10 8 L 0 8 Z";
  const constraint = { shape: "rectangle", rotationDegrees: 0 } satisfies ShapeConstraint;
  const cases: Array<[ConstrainedHandle, Point, string]> = [
    ["nw", { x: -2, y: -3 }, "M -2 -3 L 10 -3 L 10 8 L -2 8 Z"],
    ["n", { x: 999, y: -3 }, "M 0 -3 L 10 -3 L 10 8 L 0 8 Z"],
    ["ne", { x: 12, y: -3 }, "M 0 -3 L 12 -3 L 12 8 L 0 8 Z"],
    ["e", { x: 12, y: 999 }, "M 0 0 L 12 0 L 12 8 L 0 8 Z"],
    ["se", { x: 12, y: 11 }, "M 0 0 L 12 0 L 12 11 L 0 11 Z"],
    ["s", { x: 999, y: 11 }, "M 0 0 L 10 0 L 10 11 L 0 11 Z"],
    ["sw", { x: -2, y: 11 }, "M -2 0 L 10 0 L 10 11 L -2 11 Z"],
    ["w", { x: -2, y: 999 }, "M -2 0 L 10 0 L 10 8 L -2 8 Z"],
  ];

  for (const [handle, pointer, expectedPath] of cases) {
    const resized = resizeConstrainedOutline(source, constraint, handle, pointer);
    assert.equal(resized.displayPath, expectedPath, handle);
    assert.deepEqual(resized.shapeConstraint, constraint, handle);
  }
});

test("resizeConstrainedOutline clamps dragged rectangle axes to two pixels without flipping", () => {
  const source = "M 0 0 L 10 0 L 10 8 L 0 8 Z";
  const constraint = { shape: "rectangle", rotationDegrees: 0 };

  assert.equal(
    resizeConstrainedOutline(source, constraint, "se", { x: -10, y: -10 }).displayPath,
    "M 0 0 L 2 0 L 2 2 L 0 2 Z",
  );
  assert.equal(
    resizeConstrainedOutline(source, constraint, "w", { x: 20, y: 999 }).displayPath,
    "M 8 0 L 10 0 L 10 8 L 8 8 Z",
  );
});

test("resizeConstrainedOutline regenerates an oval when a side changes one intrinsic dimension", () => {
  const resized = resizeConstrainedOutline(
    "M 5 0 C 7.761424 0 10 1.790861 10 4 C 10 6.209139 7.761424 8 5 8 C 2.238576 8 0 6.209139 0 4 C 0 1.790861 2.238576 0 5 0 Z",
    { shape: "oval", rotationDegrees: 0 },
    "e",
    { x: 14, y: 999 },
  );

  assert.equal(
    resized.displayPath,
    "M 7 0 C 10.865993 0 14 1.790861 14 4 C 14 6.209139 10.865993 8 7 8 C 3.134007 8 0 6.209139 0 4 C 0 1.790861 3.134007 0 7 0 Z",
  );
});

test("resizeConstrainedOutline resizes a rotated oval in its local axes and rotates every control back", () => {
  const resized = resizeConstrainedOutline(
    "M 9 4 C 9 6.761424 7.209139 9 5 9 C 2.790861 9 1 6.761424 1 4 C 1 1.238576 2.790861 -1 5 -1 C 7.209139 -1 9 1.238576 9 4 Z",
    { shape: "oval", rotationDegrees: 90 },
    "e",
    { x: 5, y: 13 },
  );

  assert.equal(
    resized.displayPath,
    "M 9 6 C 9 9.865993 7.209139 13 5 13 C 2.790861 13 1 9.865993 1 6 C 1 2.134007 2.790861 -1 5 -1 C 7.209139 -1 9 2.134007 9 6 Z",
  );
  assert.deepEqual(resized.shapeConstraint, { shape: "oval", rotationDegrees: 90 });
});

test("resizeConstrainedOutline rejects a finite pointer when inverse rotation overflows", () => {
  assert.throws(
    () => resizeConstrainedOutline(
      "M 5 -2.071068 L 12.071068 5 L 5 12.071068 L -2.071068 5 Z",
      { shape: "rectangle", rotationDegrees: 45 },
      "e",
      { x: Number.MAX_VALUE, y: Number.MAX_VALUE },
    ),
    /finite/,
  );
});

test("resizeConstrainedOutline rejects finite local bounds whose derived dimensions overflow", () => {
  const halfMaximum = Number.MAX_VALUE / 2;
  assert.throws(
    () => resizeConstrainedOutline(
      `M ${-halfMaximum} 0 L ${halfMaximum} 0 L ${halfMaximum} 10 L ${-halfMaximum} 10 Z`,
      { shape: "rectangle", rotationDegrees: 0 },
      "e",
      { x: Number.MAX_VALUE, y: 5 },
    ),
    /finite/,
  );
});

test("resizeConstrainedOutline rejects regenerated coordinates that overflow during world rotation", () => {
  assert.throws(
    () => resizeConstrainedOutline(
      "M 6.010407569374976e307 -6.010407710796332e307 L 6.010407710796332e307 -6.010407569374976e307 L -6.010407569374976e307 6.010407710796332e307 L -6.010407710796332e307 6.010407569374976e307 Z",
      { shape: "rectangle", rotationDegrees: 45 },
      "e",
      { x: 1.2020815280171308e308, y: 1.2020815280171308e308 },
    ),
    /finite/,
  );
});

test("resizeConstrainedOutline keeps circle corner drags square around the opposite corner", () => {
  const resized = resizeConstrainedOutline(
    "M 5 0 C 7.761424 0 10 2.238576 10 5 C 10 7.761424 7.761424 10 5 10 C 2.238576 10 0 7.761424 0 5 C 0 2.238576 2.238576 0 5 0 Z",
    { shape: "circle", rotationDegrees: 0 },
    "se",
    { x: 14, y: 12 },
  );

  assert.equal(
    resized.displayPath,
    "M 7 0 C 10.865993 0 14 3.134007 14 7 C 14 10.865993 10.865993 14 7 14 C 3.134007 14 0 10.865993 0 7 C 0 3.134007 3.134007 0 7 0 Z",
  );
});

test("resizeConstrainedOutline keeps a circle centered on the perpendicular axis during an edge drag", () => {
  const resized = resizeConstrainedOutline(
    "M 5 0 C 7.761424 0 10 2.238576 10 5 C 10 7.761424 7.761424 10 5 10 C 2.238576 10 0 7.761424 0 5 C 0 2.238576 2.238576 0 5 0 Z",
    { shape: "circle", rotationDegrees: 0 },
    "e",
    { x: 14, y: 999 },
  );

  assert.equal(
    resized.displayPath,
    "M 7 -2 C 10.865993 -2 14 1.134007 14 5 C 14 8.865993 10.865993 12 7 12 C 3.134007 12 0 8.865993 0 5 C 0 1.134007 3.134007 -2 7 -2 Z",
  );
});

test("resizeConstrainedOutline clamps circle corner and edge drags before they can invert", () => {
  const source = "M 5 0 C 7.761424 0 10 2.238576 10 5 C 10 7.761424 7.761424 10 5 10 C 2.238576 10 0 7.761424 0 5 C 0 2.238576 2.238576 0 5 0 Z";
  const constraint = { shape: "circle", rotationDegrees: 0 };

  assert.equal(
    resizeConstrainedOutline(source, constraint, "nw", { x: 9, y: 8 }).displayPath,
    "M 9 8 C 9.552285 8 10 8.447715 10 9 C 10 9.552285 9.552285 10 9 10 C 8.447715 10 8 9.552285 8 9 C 8 8.447715 8.447715 8 9 8 Z",
  );
  assert.equal(
    resizeConstrainedOutline(source, constraint, "w", { x: 20, y: 999 }).displayPath,
    "M 9 4 C 9.552285 4 10 4.447715 10 5 C 10 5.552285 9.552285 6 9 6 C 8.447715 6 8 5.552285 8 5 C 8 4.447715 8.447715 4 9 4 Z",
  );
});

test("resizeConstrainedOutline regenerates horizontal and vertical pills from the shorter dimension", () => {
  const horizontal = resizeConstrainedOutline(
    "M 2 0 L 8 0 C 9.104569 0 10 0.895431 10 2 C 10 3.104569 9.104569 4 8 4 L 2 4 C 0.895431 4 0 3.104569 0 2 C 0 0.895431 0.895431 0 2 0 Z",
    { shape: "pill", rotationDegrees: 0 },
    "e",
    { x: 14, y: 999 },
  );
  const vertical = resizeConstrainedOutline(
    "M 0 2 L 0 8 C 0 9.104569 0.895431 10 2 10 C 3.104569 10 4 9.104569 4 8 L 4 2 C 4 0.895431 3.104569 0 2 0 C 0.895431 0 0 0.895431 0 2 Z",
    { shape: "pill", rotationDegrees: 0 },
    "s",
    { x: 999, y: 14 },
  );

  assert.equal(horizontal.displayPath, "M 2 0 L 12 0 C 13.104569 0 14 0.895431 14 2 C 14 3.104569 13.104569 4 12 4 L 2 4 C 0.895431 4 0 3.104569 0 2 C 0 0.895431 0.895431 0 2 0 Z");
  assert.equal(vertical.displayPath, "M 0 2 L 0 12 C 0 13.104569 0.895431 14 2 14 C 3.104569 14 4 13.104569 4 12 L 4 2 C 4 0.895431 3.104569 0 2 0 C 0.895431 0 0 0.895431 0 2 Z");
});

test("parsePath throws on malformed input", () => {
  assert.throws(() => parsePath(""), /non-empty/);
  assert.throws(() => parsePath("not a path"), /command/);
});

test("parsePath rejects incomplete or non-finite coordinate pairs", () => {
  assert.throws(() => parsePath("M 0"), /finite coordinate/);
  assert.throws(() => parsePath("M 0 10px"), /finite coordinate/);
  assert.throws(() => parsePath("M NaN 0"), /finite coordinate/);
});

test("moveVertex translates an anchor point and its dependent controls", () => {
  const commands = parsePath("M 0 0 L 50 50 Q 60 60 100 100 Z");
  moveVertex(commands, 1, 10, 10);
  assert.deepEqual(commands[1]?.points, [{ x: 60, y: 60 }]);
});

test("moveVertex on a Q endpoint shifts the curve", () => {
  const commands = parsePath("M 0 0 L 10 10 Q 20 20 50 50 Z");
  moveVertex(commands, 2, 5, -5);
  assert.deepEqual(commands[2]?.points, [{ x: 55, y: 45 }]);
  assert.deepEqual(commands[2]?.controls, [{ x: 25, y: 15 }]);
});

test("moveVertex on a C endpoint shifts both control points equally", () => {
  const commands = parsePath("M 0 0 L 10 10 C 20 20 30 30 50 50 Z");
  moveVertex(commands, 2, 5, 5);
  assert.deepEqual(commands[2]?.points, [{ x: 55, y: 55 }]);
  assert.deepEqual(commands[2]?.controls, [{ x: 25, y: 25 }, { x: 35, y: 35 }]);
});

test("moveVertex on M shifts the start point", () => {
  const commands = parsePath("M 10 10 L 50 50 Z");
  moveVertex(commands, 0, 5, 5);
  assert.deepEqual(commands[0]?.points, [{ x: 15, y: 15 }]);
});

test("addVertex on an L segment inserts a new L at the midpoint", () => {
  const commands = parsePath("M 0 0 L 100 0 L 100 100 Z");
  addVertex(commands, 0, 50, 0);
  assert.equal(commands.length, 5);
  assert.equal(commands[1]?.type, "L");
  assert.deepEqual(commands[1]?.points, [{ x: 50, y: 0 }]);
  assert.equal(commands[2]?.type, "L");
  assert.deepEqual(commands[2]?.points, [{ x: 100, y: 0 }]);
});

test("addVertex on a Q segment subdivides the bezier", () => {
  const commands = parsePath("M 0 0 Q 50 100 100 0 Z");
  addVertex(commands, 0, 50, 50);
  assert.equal(commands.length, 4);
  assert.equal(commands[0]?.type, "M");
  assert.equal(commands[1]?.type, "Q");
  assert.equal(commands[2]?.type, "Q");
  assert.equal(commands[3]?.type, "Z");
  assert.deepEqual(commands[1]?.points, [{ x: 50, y: 50 }]);
  assert.deepEqual(commands[2]?.points, [{ x: 100, y: 0 }]);
});

test("addVertex on a C segment subdivides the cubic bezier", () => {
  const commands = parsePath("M 0 0 C 25 100 75 100 100 0 Z");
  addVertex(commands, 0, 50, 50);
  assert.equal(commands.length, 4);
  assert.equal(commands[1]?.type, "C");
  assert.equal(commands[2]?.type, "C");
});

test("addInflectionPoint subdivides a quadratic at the selected non-midpoint location and delete restores it", () => {
  const originalPath = "M 0 0 Q 100 100 100 0 L 0 100 Z";
  const commands = parsePath(originalPath);

  assert.equal(addInflectionPoint(commands, 0, { x: 43.75, y: 37.5 }), true);
  assert.equal(commands[1]?.type, "Q");
  assert.equal(commands[2]?.type, "Q");
  assertPoint(commands[1]?.points[0]!, { x: 43.75, y: 37.5 });
  assertPoint(commands[1]?.controls[0]!, { x: 25, y: 25 });
  assertPoint(commands[2]?.controls[0]!, { x: 100, y: 75 });
  assert.equal(isInflectionVertex(commands, 1), true);

  deleteVertex(commands, 1);
  assert.equal(serializePath(commands), originalPath);
});

test("addInflectionPoint subdivides a cubic at the selected location without changing its curve", () => {
  const commands = parsePath("M 0 0 C 0 100 100 100 100 0 L 0 100 Z");

  assert.equal(addInflectionPoint(commands, 0, { x: 15.625, y: 56.25 }), true);
  assert.equal(commands[1]?.type, "C");
  assert.equal(commands[2]?.type, "C");
  assertPoint(commands[1]?.points[0]!, { x: 15.625, y: 56.25 });
  assertPoint(commands[1]?.controls[0]!, { x: 0, y: 25 });
  assertPoint(commands[1]?.controls[1]!, { x: 6.25, y: 43.75 });
  assertPoint(commands[2]?.controls[0]!, { x: 43.75, y: 93.75 });
  assertPoint(commands[2]?.controls[1]!, { x: 100, y: 75 });
  assert.equal(isInflectionVertex(commands, 1), true);
});

test("serialized inflection points remain removable curve vertices", () => {
  const cases = [
    ["M 0 0 Q 37.1234567 98.7654321 123.4567891 4.5678912 L 0 100 Z", "Q"],
    ["M 0 0 C 19.8765432 123.4567891 99.1234567 87.654321 123.4567891 4.5678912 L 0 100 Z", "C"],
  ] as const;

  for (const [path, type] of cases) {
    const commands = parsePath(path);
    assert.equal(addInflectionPoint(commands, 0, { x: 6.456789, y: 17.654321 }), true);
    const roundTripped = parsePath(serializePath(commands));

    assert.equal(isInflectionVertex(roundTripped, 1), true, `${type} inflection point is removable after serialization`);
    deleteVertex(roundTripped, 1);
    assert.equal(roundTripped[1]?.type, type, `${type} deletion keeps the segment bendable`);
  }
});

test("dragged inflection points remain removable curve vertices", () => {
  const cases = [
    ["M 0 0 Q 100 100 100 0 L 0 100 Z", "Q"],
    ["M 0 0 C 0 100 100 100 100 0 L 0 100 Z", "C"],
  ] as const;

  for (const [path, type] of cases) {
    const commands = parsePath(path);
    assert.equal(addInflectionPoint(commands, 0, { x: 43.75, y: 37.5 }), true);
    moveVertex(commands, 1, 8, -5);

    assert.equal(isInflectionVertex(commands, 1), true, `${type} inflection point is removable after dragging`);
    deleteVertex(commands, 1);
    assert.equal(commands[1]?.type, type, `${type} deletion keeps the segment bendable`);
  }
});

test("removing a quadratic inflection point remains finite when its drag reaches the outgoing control", () => {
  const commands = parsePath("M 0 0 Q 100 100 100 0 L 0 100 Z");

  assert.equal(addInflectionPoint(commands, 0, { x: 75, y: 50 }), true);
  moveVertex(commands, 1, 25, 0);
  assert.equal(isInflectionVertex(commands, 1), true);
  deleteVertex(commands, 1);

  assert.equal(commands[1]?.type, "Q");
  assert.ok(commands[1]?.controls.every((point) => Number.isFinite(point.x) && Number.isFinite(point.y)));
  assert.doesNotThrow(() => validateEditorDocument({
    schemaVersion: 1,
    canvas: { width: 100, height: 100 },
    regions: [{ key: "hold-1", displayPath: serializePath(commands) }],
  }));
});

test("removing a cubic inflection point remains finite when its drag nearly reaches the outgoing control", () => {
  const commands = parsePath("M 0 0 C 0 100 100 100 100 0 L 0 100 Z");

  assert.equal(addInflectionPoint(commands, 0, { x: 50, y: 75 }), true);
  moveVertex(commands, 1, 24.999999999, 0);
  assert.equal(isInflectionVertex(commands, 1), true);
  deleteVertex(commands, 1);

  assert.equal(commands[1]?.type, "C");
  assert.ok(commands[1]?.controls.every((point) => Number.isFinite(point.x) && Number.isFinite(point.y)));
  assert.ok(
    commands[1]?.controls.every((point) => Math.max(Math.abs(point.x), Math.abs(point.y)) <= 1_000),
    "near-overlap removal must not amplify controls far beyond the surrounding geometry",
  );
  assert.doesNotThrow(() => validateEditorDocument({
    schemaVersion: 1,
    canvas: { width: 100, height: 100 },
    regions: [{ key: "hold-1", displayPath: serializePath(commands) }],
  }));
});

test("addVertex inserts on the segment after afterIndex, not before it", () => {
  const commands = parsePath("M 0 0 L 50 0 L 100 0 L 100 100 Z");
  addVertex(commands, 1, 75, 0);
  assert.equal(commands.length, 6);
  assert.equal(commands[1]?.type, "L");
  assert.deepEqual(commands[1]?.points, [{ x: 50, y: 0 }]);
  assert.equal(commands[2]?.type, "L");
  assert.deepEqual(commands[2]?.points, [{ x: 75, y: 0 }]);
  assert.equal(commands[3]?.type, "L");
  assert.deepEqual(commands[3]?.points, [{ x: 100, y: 0 }]);
});

test("addVertex subdivides a Q segment after a non-M command, leaving the preceding segment unchanged", () => {
  const commands = parsePath("M 0 0 L 20 0 Q 60 100 100 0 Z");
  addVertex(commands, 1, 60, 50);
  assert.equal(commands.length, 5);
  assert.equal(commands[1]?.type, "L");
  assert.deepEqual(commands[1]?.points, [{ x: 20, y: 0 }]);
  assert.equal(commands[2]?.type, "Q");
  assert.equal(commands[3]?.type, "Q");
  assert.deepEqual(commands[3]?.points, [{ x: 100, y: 0 }]);
});

test("addVertex subdivides a C segment after a non-M command, leaving the preceding segment unchanged", () => {
  const commands = parsePath("M 0 0 L 20 0 C 40 100 80 100 100 0 Z");
  addVertex(commands, 1, 60, 50);
  assert.equal(commands.length, 5);
  assert.equal(commands[1]?.type, "L");
  assert.deepEqual(commands[1]?.points, [{ x: 20, y: 0 }]);
  assert.equal(commands[2]?.type, "C");
  assert.equal(commands[3]?.type, "C");
  assert.deepEqual(commands[3]?.points, [{ x: 100, y: 0 }]);
});

test("deleteVertex removes a vertex from a four-vertex contour and converts adjacent curves to lines", () => {
  const commands = parsePath("M 0 0 L 25 50 L 50 0 L 75 50 Z");
  deleteVertex(commands, 2);
  assert.equal(commands.length, 4);
  assert.equal(commands[2]?.type, "L");
  assert.deepEqual(commands[2]?.points, [{ x: 75, y: 50 }]);
});

test("deleteVertex reduces an open four-vertex path to three vertices", () => {
  const commands = parsePath("M 0 0 L 25 50 L 50 0 L 75 50");
  deleteVertex(commands, 2);
  assert.equal(serializePath(commands), "M 0 0 L 25 50 L 75 50");
});

test("deleteVertex refuses to delete a noninitial M command", () => {
  const commands = parsePath("M 0 0 L 25 0 L 25 25 Z M 50 50 L 75 50 L 75 75 Z");
  const originalPath = serializePath(commands);

  deleteVertex(commands, 4);

  assert.equal(serializePath(commands), originalPath);
});

test("deleteVertex on an L between Q segments leaves the preceding curve untouched", () => {
  const commands = parsePath("M 0 0 Q 25 50 50 0 L 75 50 Q 100 100 125 0 Z");
  deleteVertex(commands, 2);
  assert.equal(commands.length, 4);
  assert.equal(commands[1]?.type, "Q");
  assert.deepEqual(commands[1]?.points, [{ x: 50, y: 0 }]);
  assert.equal(commands[2]?.type, "L");
  assert.deepEqual(commands[2]?.points, [{ x: 125, y: 0 }]);
});

test("deleteVertex promotes the next vertex to M when deleting the start vertex", () => {
  const commands = parsePath("M 0 0 L 50 0 L 100 50 L 0 50 Z");
  deleteVertex(commands, 0);
  assert.equal(serializePath(commands), "M 50 0 L 100 50 L 0 50 Z");
  assert.deepEqual(commands.map((command) => command.type), ["M", "L", "L", "Z"]);
});

test("deleteVertex promotes a Q endpoint to M when deleting the start vertex", () => {
  const commands = parsePath("M 0 0 Q 25 50 50 0 L 100 50 L 0 50 Z");
  deleteVertex(commands, 0);
  assert.equal(serializePath(commands), "M 50 0 L 100 50 L 0 50 Z");
  assert.deepEqual(commands.map((command) => command.type), ["M", "L", "L", "Z"]);
});

test("deleteVertex promotes a C endpoint to M when deleting the start vertex", () => {
  const commands = parsePath("M 0 0 C 10 50 40 50 50 0 L 100 50 L 0 50 Z");
  deleteVertex(commands, 0);
  assert.equal(serializePath(commands), "M 50 0 L 100 50 L 0 50 Z");
  assert.deepEqual(commands.map((command) => command.type), ["M", "L", "L", "Z"]);
});

test("deleteVertex refuses to delete the start vertex when fewer than three vertices remain", () => {
  const commands = parsePath("M 0 0 L 50 0 Z");
  deleteVertex(commands, 0);
  assert.equal(commands.length, 3);
  assert.equal(commands[0]?.type, "M");
});

test("deleteVertex refuses to reduce a triangle below three vertices", () => {
  const commands = parsePath("M 0 0 L 50 0 L 100 50 Z");
  deleteVertex(commands, 2);
  assert.equal(commands.length, 4);
  assert.equal(serializePath(commands), "M 0 0 L 50 0 L 100 50 Z");
});

test("deleteVertex on the vertex before Z leaves a curved prev segment untouched", () => {
  const commands = parsePath("M 0 0 L 20 20 Q 40 80 80 0 L 120 40 Z");
  deleteVertex(commands, 3);
  assert.equal(commands.length, 4);
  assert.equal(commands[0]?.type, "M");
  assert.equal(commands[2]?.type, "Q");
  assert.deepEqual(commands[2]?.points, [{ x: 80, y: 0 }]);
  assert.deepEqual(commands[2]?.controls, [{ x: 40, y: 80 }]);
  assert.equal(commands[3]?.type, "Z");
});

test("rotatePath rotates every anchor point 90 degrees clockwise around the pivot", () => {
  const commands = parsePath("M 20 10 L 20 20 L 10 20 Z");
  rotatePath(commands, Math.PI / 2, { x: 10, y: 10 });
  assert.equal(serializePath(commands), "M 10 20 L 0 20 L 0 10 Z");
});

test("rotatePath carries control points along with a curve's rotation", () => {
  const commands = parsePath("M 10 10 Q 20 10 20 20 Z");
  rotatePath(commands, Math.PI / 2, { x: 10, y: 10 });
  assert.deepEqual(commands[1]?.controls, [{ x: 10, y: 20 }]);
  assert.deepEqual(commands[1]?.points, [{ x: 0, y: 20 }]);
});

test("rotatePath leaves a point already on the pivot unchanged", () => {
  const commands = parsePath("M 10 10 L 30 10 Z");
  rotatePath(commands, Math.PI / 4, { x: 10, y: 10 });
  assert.deepEqual(commands[0]?.points, [{ x: 10, y: 10 }]);
});
