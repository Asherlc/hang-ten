const test = require("node:test");
const assert = require("node:assert/strict");

const {
  parseDisplayPath,
  serializeDisplayPath,
  transformPath,
  bendPath,
  mirrorPath,
  treatPathCorner,
  isExplicitClosingCommand,
  explicitClosingCommandChecker,
  movePathEndpoint,
} = require("../vector-path-model.js");

test("cubic display paths round-trip without flattening", () => {
  const source = "M 10 20 C 15 10 25 10 30 20 L 30 40 Z";
  assert.equal(serializeDisplayPath(parseDisplayPath(source)), source);
});

test("mirrorPath reflects endpoints and control handles", () => {
  const mirrored = mirrorPath(parseDisplayPath("M 10 20 C 15 10 25 10 30 20 Z"), 50);
  assert.equal(serializeDisplayPath(mirrored), "M 90 20 C 85 10 75 10 70 20 Z");
});

test("transformPath retains quadratic and cubic commands while applying an affine matrix", () => {
  const transformed = transformPath(
    parseDisplayPath("M 1 2 Q 3 4 5 6 C 7 8 9 10 11 12 Z"),
    [2, 0, 0, 3, 10, 20],
  );

  assert.equal(serializeDisplayPath(transformed), "M 12 26 Q 16 32 20 38 C 24 44 28 50 32 56 Z");
});

test("bendPath offsets endpoints and control handles without changing commands", () => {
  const bent = bendPath(
    parseDisplayPath("M 0 10 Q 50 10 100 10 C 25 10 75 10 100 10 Z"),
    20,
    [0, 0, 100, 100],
  );

  assert.equal(serializeDisplayPath(bent), "M 0 10 Q 50 30 100 10 C 25 25 75 25 100 10 Z");
});

test("rounded Stage 3 junction aligns adjacent cubic handles without moving endpoints", () => {
  const source = parseDisplayPath("M 0 0 L 10 0 L 20 0 L 20 10 Z");
  const rounded = treatPathCorner(source, 1, "rounded", 2);

  assert.equal(
    serializeDisplayPath(rounded),
    "M 0 0 C 0 0 8 0 10 0 C 12 0 20 0 20 0 L 20 10 Z",
  );
  assert.deepEqual(rounded.filter((command) => command.type !== "Z").map(({ x, y }) => [x, y]), [[0, 0], [10, 0], [20, 0], [20, 10]]);
  assert.equal(serializeDisplayPath(source), "M 0 0 L 10 0 L 20 0 L 20 10 Z");
});

test("sharp Stage 3 junction collapses incoming and outgoing handles to the endpoint", () => {
  const source = parseDisplayPath("M 0 0 C 3 0 7 0 10 0 C 13 3 17 3 20 0 Z");
  const sharp = treatPathCorner(source, 1, "sharp", 3);

  assert.equal(
    serializeDisplayPath(sharp),
    "M 0 0 C 3 0 10 0 10 0 C 10 0 17 3 20 0 Z",
  );
});

test("Stage 3 treatment supports the closing M corner", () => {
  const source = parseDisplayPath("M 0 0 L 10 0 L 10 10 L 0 10 Z");
  const rounded = treatPathCorner(source, 0, "rounded", Math.SQRT2);

  assert.equal(
    serializeDisplayPath(rounded),
    "M 0 0 C 1 -1 10 0 10 0 L 10 10 L 0 10 C 0 10 -1 1 0 0 Z",
  );
});

test("closing M treatment can be changed without adding duplicate closure segments", () => {
  const source = parseDisplayPath("M 0 0 L 10 0 L 10 10 L 0 10 Z");
  const rounded = treatPathCorner(source, 0, "rounded", Math.SQRT2);
  const sharp = treatPathCorner(rounded, 0, "sharp", 4);

  assert.equal(
    serializeDisplayPath(sharp),
    "M 0 0 C 0 0 10 0 10 0 L 10 10 L 0 10 C 0 10 0 0 0 0 Z",
  );
});

test("rounded closing M treatment converts explicit closure segments in place", () => {
  const cases = [
    {
      source: "M 0 0 L 10 0 L 10 10 L 0 0 Z",
      expected: "M 0 0 C 0 -2 10 0 10 0 L 10 10 C 10 10 0 2 0 0 Z",
    },
    {
      source: "M 0 0 L 10 0 L 10 10 Q 3 7 0 0 Z",
      expected: "M 0 0 C 0 -2 10 0 10 0 L 10 10 C 5.333333333333333 8 0 2 0 0 Z",
    },
  ];

  for (const { source: path, expected } of cases) {
    const source = parseDisplayPath(path);
    const original = structuredClone(source);
    const closingIndex = source.length - 2;
    const rounded = treatPathCorner(source, 0, "rounded", 2);

    assert.equal(serializeDisplayPath(rounded), expected);
    assert.equal(rounded[closingIndex].type, "C");
    assert.equal(rounded.length, source.length);
    assert.deepEqual(
      rounded.filter((command) => command.type !== "Z").map(({ x, y }) => [x, y]),
      source.filter((command) => command.type !== "Z").map(({ x, y }) => [x, y]),
    );
    assert.deepEqual(source, original);
  }
});

test("isExplicitClosingCommand identifies terminal closure segments in their own subpath", () => {
  const terminalClosures = [
    "M 0 0 L 10 0 L 0 0 Z",
    "M 0 0 L 10 0 Q 4 4 0 0 Z",
    "M 0 0 L 10 0 C 6 2 3 3 0 0 Z",
  ];

  for (const source of terminalClosures) {
    const commands = parseDisplayPath(source);
    assert.equal(isExplicitClosingCommand(commands, commands.length - 2), true);
  }

  assert.equal(isExplicitClosingCommand(parseDisplayPath("M 0 0 L 0 0 L 10 0 Z"), 1), false);
  assert.equal(isExplicitClosingCommand(parseDisplayPath("M 0 0 L 10 0 L 5 5 Z"), 2), false);
  assert.equal(
    isExplicitClosingCommand(parseDisplayPath("M 100 100 L 110 100 Z M 0 0 L 10 0 L 0 0 Z"), 5),
    true,
  );
});

test("an explicit closing command checker validates once for repeated rendering checks", () => {
  const commands = parseDisplayPath("M 0 0 L 10 0 L 0 0 Z");
  const isExplicitClosureAt = explicitClosingCommandChecker(commands);

  assert.equal(isExplicitClosureAt(0), false);
  assert.equal(isExplicitClosureAt(1), false);
  assert.equal(isExplicitClosureAt(2), true);
  assert.equal(isExplicitClosureAt(3), false);
});

test("moving a subpath start keeps explicit L Q and C closures attached", () => {
  const cases = [
    {
      closing: "L 0 0",
      expected: "M 100 100 L 110 100 Z M 2 3 L 10 0 L 2 3 Z",
    },
    {
      closing: "Q 4 4 0 0",
      expected: "M 100 100 L 110 100 Z M 2 3 L 10 0 Q 4 4 2 3 Z",
    },
    {
      closing: "C 8 2 3 3 0 0",
      expected: "M 100 100 L 110 100 Z M 2 3 L 10 0 C 8 2 3 3 2 3 Z",
    },
  ];

  for (const { closing, expected } of cases) {
    const source = parseDisplayPath(`M 100 100 L 110 100 Z M 0 0 L 10 0 ${closing} Z`);
    const original = structuredClone(source);
    const moved = movePathEndpoint(source, 3, [2, 3]);

    assert.equal(serializeDisplayPath(moved), expected);
    assert.deepEqual(source, original);
  }
});

test("Stage 3 corner treatment rejects invalid inputs without mutation", () => {
  const source = parseDisplayPath("M 0 0 Q 5 0 10 0 L 10 10 Z");
  const original = structuredClone(source);

  assert.throws(() => treatPathCorner(source, 9, "rounded", 2), /index/i);
  assert.throws(() => treatPathCorner(source, 1, "soft", 2), /treatment/i);
  assert.throws(() => treatPathCorner(source, 1, "rounded", Number.NaN), /amount/i);
  assert.throws(() => treatPathCorner(source, 1, "rounded", 0), /amount/i);
  assert.throws(() => treatPathCorner([{ type: "M", x: 0, y: 0 }], 0, "sharp", 2), /closed/i);
  assert.deepEqual(source, original);
});

test("display path parsing rejects relative, unsupported, and non-finite coordinates", () => {
  assert.throws(() => parseDisplayPath("m 0 0"), /unsupported/i);
  assert.throws(() => parseDisplayPath("M 0 0 A 1 1 0 0 1 2 2"), /unsupported/i);
  assert.throws(() => parseDisplayPath("M Infinity 0"), /finite/i);
});

test("display path parsing requires complete closed subpaths", () => {
  for (const source of ["", "Z", "L 1 2", "M 1 2", "M 1 2 M 3 4 Z", "M 1 2 Z L 3 4"]) {
    assert.throws(() => parseDisplayPath(source), /closed|start|empty/i);
  }
  assert.equal(
    serializeDisplayPath(parseDisplayPath("M 0 0 L 1 0 Z M 2 2 Q 3 3 4 2 Z")),
    "M 0 0 L 1 0 Z M 2 2 Q 3 3 4 2 Z",
  );
});

test("transformPath rejects sparse matrices and non-finite computed coordinates", () => {
  const commands = parseDisplayPath("M 1.7976931348623157e+308 1 Z");

  assert.throws(() => transformPath(commands, Array(6)), /finite/i);
  assert.throws(
    () => transformPath(commands, [2, 0, 0, 1, 0, 0]),
    /finite/i,
  );
});

test("transformPath accepts complete keyed matrices without mutating inputs", () => {
  const commands = parseDisplayPath("M 1 2 Q 3 4 5 6 Z");
  const originalCommands = structuredClone(commands);
  const matrix = { a: 1, b: 0, c: 0, d: 1, e: 10, f: 20 };
  const transformed = transformPath(commands, matrix);

  assert.equal(serializeDisplayPath(transformed), "M 11 22 Q 13 24 15 26 Z");
  assert.deepEqual(commands, originalCommands);
  assert.deepEqual(matrix, { a: 1, b: 0, c: 0, d: 1, e: 10, f: 20 });
  assert.notStrictEqual(transformed, commands);
  assert.notStrictEqual(transformed[0], commands[0]);
  assert.throws(() => transformPath(commands, { a: 1, b: 0, c: 0, d: 1, e: 0 }), /finite/i);
});

test("bendPath rejects non-finite computed coordinates without mutating inputs", () => {
  const commands = parseDisplayPath("M 0 0 Q 0.5 1.7976931348623157e+308 1 0 Z");
  const originalCommands = structuredClone(commands);
  const bounds = [0, 0, 1, 1];

  assert.throws(() => bendPath(commands, Number.MAX_VALUE, bounds), /finite/i);
  assert.deepEqual(commands, originalCommands);
  assert.deepEqual(bounds, [0, 0, 1, 1]);
});

test("bendPath validates every supplied bound and derived width", () => {
  const commands = parseDisplayPath("M 0 0 L 1 0 Z");

  assert.throws(() => bendPath(commands, 1, [0, Number.POSITIVE_INFINITY, 1, 1]), /finite/i);
  assert.throws(
    () => bendPath(commands, 1, { x: 0, y: 0, width: 1, height: Number.NaN }),
    /finite/i,
  );
  assert.throws(
    () => bendPath(commands, 1, [-Number.MAX_VALUE, 0, Number.MAX_VALUE, 1]),
    /finite/i,
  );
});

test("bendPath validates non-finite aliases even when finite primary bounds are present", () => {
  const commands = parseDisplayPath("M 0 0 L 1 0 Z");
  const invalidBounds = [
    { minX: 0, maxX: 1, left: Number.POSITIVE_INFINITY },
    { minX: 0, maxX: 1, right: Number.NaN },
    { minX: 0, maxX: 1, minY: 0, maxY: 1, top: Number.POSITIVE_INFINITY },
    { minX: 0, maxX: 1, minY: 0, maxY: 1, bottom: Number.NaN },
  ];

  for (const bounds of invalidBounds) assert.throws(() => bendPath(commands, 1, bounds), /finite/i);
});

test("bendPath validates aliases mixed into rectangle bounds and preserves valid keyed forms", () => {
  const commands = parseDisplayPath("M 0 0 L 1 0 Z");
  for (const alias of ["minX", "maxX", "minY", "maxY", "left", "right", "top", "bottom"]) {
    const bounds = { x: 0, y: 0, width: 1, height: 1, [alias]: Number.POSITIVE_INFINITY };
    assert.throws(() => bendPath(commands, 1, bounds), /finite/i);
  }

  assert.equal(serializeDisplayPath(bendPath(commands, 1, { x: 0, y: 0, width: 1, height: 1 })), "M 0 0 L 1 0 Z");
  assert.equal(serializeDisplayPath(bendPath(commands, 1, { left: 0, right: 1, top: 0, bottom: 1 })), "M 0 0 L 1 0 Z");
});
