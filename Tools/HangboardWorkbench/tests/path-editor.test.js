const test = require("node:test");
const assert = require("node:assert/strict");
const { parsePath, serializePath, moveVertex, addVertex, deleteVertex, rotatePath } = require("../path-editor.js");

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

test("parsePath rejects incomplete or non-finite coordinate pairs", () => {
  assert.throws(() => parsePath("M 0"), /finite coordinate/);
  assert.throws(() => parsePath("M 0 10px"), /finite coordinate/);
  assert.throws(() => parsePath("M NaN 0"), /finite coordinate/);
});

test("moveVertex translates an anchor point and its dependent controls", () => {
  const commands = parsePath("M 0 0 L 50 50 Q 60 60 100 100 Z");
  moveVertex(commands, 1, 10, 10);
  assert.deepEqual(commands[1].points, [{ x: 60, y: 60 }]);
});

test("moveVertex on a Q endpoint shifts the curve", () => {
  const commands = parsePath("M 0 0 L 10 10 Q 20 20 50 50 Z");
  moveVertex(commands, 2, 5, -5);
  assert.deepEqual(commands[2].points, [{ x: 55, y: 45 }]);
  assert.deepEqual(commands[2].controls, [{ x: 25, y: 15 }]);
});

test("moveVertex on a C endpoint shifts both control points equally", () => {
  const commands = parsePath("M 0 0 L 10 10 C 20 20 30 30 50 50 Z");
  moveVertex(commands, 2, 5, 5);
  assert.deepEqual(commands[2].points, [{ x: 55, y: 55 }]);
  assert.deepEqual(commands[2].controls, [{ x: 25, y: 25 }, { x: 35, y: 35 }]);
});

test("moveVertex on M shifts the start point", () => {
  const commands = parsePath("M 10 10 L 50 50 Z");
  moveVertex(commands, 0, 5, 5);
  assert.deepEqual(commands[0].points, [{ x: 15, y: 15 }]);
});

test("addVertex on an L segment inserts a new L at the midpoint", () => {
  const commands = parsePath("M 0 0 L 100 0 L 100 100 Z");
  addVertex(commands, 0, 50, 0);
  assert.equal(commands.length, 5);
  assert.equal(commands[1].type, "L");
  assert.deepEqual(commands[1].points, [{ x: 50, y: 0 }]);
  assert.equal(commands[2].type, "L");
  assert.deepEqual(commands[2].points, [{ x: 100, y: 0 }]);
});

test("addVertex on a Q segment subdivides the bezier", () => {
  const commands = parsePath("M 0 0 Q 50 100 100 0 Z");
  addVertex(commands, 0, 50, 50);
  assert.equal(commands.length, 4);
  assert.equal(commands[0].type, "M");
  assert.equal(commands[1].type, "Q");
  assert.equal(commands[2].type, "Q");
  assert.equal(commands[3].type, "Z");
  assert.deepEqual(commands[1].points, [{ x: 50, y: 50 }]);
  assert.deepEqual(commands[2].points, [{ x: 100, y: 0 }]);
});

test("addVertex on a C segment subdivides the cubic bezier", () => {
  const commands = parsePath("M 0 0 C 25 100 75 100 100 0 Z");
  addVertex(commands, 0, 50, 50);
  assert.equal(commands.length, 4);
  assert.equal(commands[1].type, "C");
  assert.equal(commands[2].type, "C");
});

test("addVertex inserts on the segment after afterIndex, not before it", () => {
  const commands = parsePath("M 0 0 L 50 0 L 100 0 L 100 100 Z");
  addVertex(commands, 1, 75, 0);
  assert.equal(commands.length, 6);
  assert.equal(commands[1].type, "L");
  assert.deepEqual(commands[1].points, [{ x: 50, y: 0 }]);
  assert.equal(commands[2].type, "L");
  assert.deepEqual(commands[2].points, [{ x: 75, y: 0 }]);
  assert.equal(commands[3].type, "L");
  assert.deepEqual(commands[3].points, [{ x: 100, y: 0 }]);
});

test("addVertex subdivides a Q segment after a non-M command, leaving the preceding segment unchanged", () => {
  const commands = parsePath("M 0 0 L 20 0 Q 60 100 100 0 Z");
  addVertex(commands, 1, 60, 50);
  assert.equal(commands.length, 5);
  assert.equal(commands[1].type, "L");
  assert.deepEqual(commands[1].points, [{ x: 20, y: 0 }]);
  assert.equal(commands[2].type, "Q");
  assert.equal(commands[3].type, "Q");
  assert.deepEqual(commands[3].points, [{ x: 100, y: 0 }]);
});

test("addVertex subdivides a C segment after a non-M command, leaving the preceding segment unchanged", () => {
  const commands = parsePath("M 0 0 L 20 0 C 40 100 80 100 100 0 Z");
  addVertex(commands, 1, 60, 50);
  assert.equal(commands.length, 5);
  assert.equal(commands[1].type, "L");
  assert.deepEqual(commands[1].points, [{ x: 20, y: 0 }]);
  assert.equal(commands[2].type, "C");
  assert.equal(commands[3].type, "C");
  assert.deepEqual(commands[3].points, [{ x: 100, y: 0 }]);
});

test("deleteVertex removes a vertex and converts adjacent curves to lines", () => {
  const commands = parsePath("M 0 0 L 25 50 L 50 0 L 75 50 Z");
  deleteVertex(commands, 2);
  assert.equal(commands.length, 4);
  assert.equal(commands[2].type, "L");
  assert.deepEqual(commands[2].points, [{ x: 75, y: 50 }]);
});

test("deleteVertex on an L between Q segments leaves the preceding curve untouched", () => {
  const commands = parsePath("M 0 0 Q 25 50 50 0 L 75 50 Q 100 100 125 0 Z");
  deleteVertex(commands, 2);
  assert.equal(commands.length, 4);
  assert.equal(commands[1].type, "Q");
  assert.deepEqual(commands[1].points, [{ x: 50, y: 0 }]);
  assert.equal(commands[2].type, "L");
  assert.deepEqual(commands[2].points, [{ x: 125, y: 0 }]);
});

test("deleteVertex refuses to delete the M vertex", () => {
  const commands = parsePath("M 0 0 L 50 0 Z");
  deleteVertex(commands, 0);
  assert.equal(commands.length, 3);
  assert.equal(commands[0].type, "M");
});

test("deleteVertex on the vertex before Z wraps correctly", () => {
  const commands = parsePath("M 0 0 L 50 0 L 100 50 Z");
  deleteVertex(commands, 2);
  assert.equal(commands.length, 3);
  assert.equal(commands[0].type, "M");
  assert.equal(commands[1].type, "L");
  assert.equal(commands[2].type, "Z");
});

test("deleteVertex on the vertex before Z leaves a curved prev segment untouched", () => {
  const commands = parsePath("M 0 0 Q 40 80 80 0 L 120 40 Z");
  deleteVertex(commands, 2);
  assert.equal(commands.length, 3);
  assert.equal(commands[0].type, "M");
  assert.equal(commands[1].type, "Q");
  assert.deepEqual(commands[1].points, [{ x: 80, y: 0 }]);
  assert.deepEqual(commands[1].controls, [{ x: 40, y: 80 }]);
  assert.equal(commands[2].type, "Z");
});

test("rotatePath rotates every anchor point 90 degrees clockwise around the pivot", () => {
  const commands = parsePath("M 20 10 L 20 20 L 10 20 Z");
  rotatePath(commands, Math.PI / 2, { x: 10, y: 10 });
  assert.equal(serializePath(commands), "M 10 20 L 0 20 L 0 10 Z");
});

test("rotatePath carries control points along with a curve's rotation", () => {
  const commands = parsePath("M 10 10 Q 20 10 20 20 Z");
  rotatePath(commands, Math.PI / 2, { x: 10, y: 10 });
  assert.deepEqual(commands[1].controls, [{ x: 10, y: 20 }]);
  assert.deepEqual(commands[1].points, [{ x: 0, y: 20 }]);
});

test("rotatePath leaves a point already on the pivot unchanged", () => {
  const commands = parsePath("M 10 10 L 30 10 Z");
  rotatePath(commands, Math.PI / 4, { x: 10, y: 10 });
  assert.deepEqual(commands[0].points, [{ x: 10, y: 10 }]);
});
