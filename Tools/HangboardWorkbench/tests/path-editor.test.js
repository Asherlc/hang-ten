const test = require("node:test");
const assert = require("node:assert/strict");
const { parsePath, serializePath } = require("../path-editor.js");

test("parsePath splits an SVG path string into commands", () => {
  const commands = parsePath("M 10 20 L 30 40 Q 50 60 70 80 C 10 20 30 40 50 60 Z");
  assert.equal(commands.length, 5);
  assert.equal(commands[0].type, "M");
  assert.deepEqual(commands[0].points, [{ x: 10, y: 20 }]);
  assert.equal(commands[1].type, "L");
  assert.deepEqual(commands[1].points, [{ x: 30, y: 40 }]);
  assert.equal(commands[2].type, "Q");
  assert.deepEqual(commands[2].points, [{ x: 70, y: 80 }]);
  assert.deepEqual(commands[2].controls, [{ x: 50, y: 60 }]);
  assert.equal(commands[3].type, "C");
  assert.deepEqual(commands[3].points, [{ x: 50, y: 60 }]);
  assert.deepEqual(commands[3].controls, [{ x: 10, y: 20 }, { x: 30, y: 40 }]);
  assert.equal(commands[4].type, "Z");
});

test("parsePath handles a simple triangle", () => {
  const commands = parsePath("M 0 0 L 100 0 L 50 80 Z");
  assert.equal(commands.length, 4);
  assert.equal(commands[0].type, "M");
  assert.equal(commands[3].type, "Z");
});

test("serializePath reconstructs an SVG path string", () => {
  const input = "M 10 20 L 30 40 Q 50 60 70 80 C 10 20 30 40 50 60 Z";
  const commands = parsePath(input);
  const output = serializePath(commands);
  assert.equal(output, input);
});

test("serializePath handles integer coordinates cleanly", () => {
  const commands = [{ type: "M", points: [{ x: 0, y: 0 }] }, { type: "L", points: [{ x: 100, y: 0 }] }, { type: "L", points: [{ x: 50, y: 80 }] }, { type: "Z", points: [] }];
  assert.equal(serializePath(commands), "M 0 0 L 100 0 L 50 80 Z");
});

test("parsePath throws on malformed input", () => {
  assert.throws(() => parsePath(""), /non-empty/);
  assert.throws(() => parsePath("not a path"), /command/);
});
