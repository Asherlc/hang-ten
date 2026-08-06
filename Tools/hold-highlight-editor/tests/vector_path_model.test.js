const test = require("node:test");
const assert = require("node:assert/strict");

const {
  parseDisplayPath,
  serializeDisplayPath,
  transformPath,
  bendPath,
  mirrorPath,
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

test("display path parsing rejects relative, unsupported, and non-finite coordinates", () => {
  assert.throws(() => parseDisplayPath("m 0 0"), /unsupported/i);
  assert.throws(() => parseDisplayPath("M 0 0 A 1 1 0 0 1 2 2"), /unsupported/i);
  assert.throws(() => parseDisplayPath("M Infinity 0"), /finite/i);
});
