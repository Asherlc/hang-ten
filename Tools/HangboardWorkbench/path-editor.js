"use strict";

function parsePath(pathString) {
  if (typeof pathString !== "string" || !pathString.trim()) {
    throw new Error("path must be a non-empty string");
  }
  const tokens = pathString.trim().split(/[\s,]+/);
  const commands = [];
  let i = 0;
  const ARITY = { M: 1, L: 1, Q: 2, C: 3, Z: 0 };

  while (i < tokens.length) {
    const cmd = tokens[i];
    if (!ARITY.hasOwnProperty(cmd)) throw new Error(`expected a command, got "${cmd}"`);
    i++;
    const arity = ARITY[cmd];
    const points = [];
    for (let j = 0; j < arity; j++) {
      const x = Number(tokens[i++]);
      const y = Number(tokens[i++]);
      if (!Number.isFinite(x) || !Number.isFinite(y)) {
        throw new Error("expected a finite coordinate pair");
      }
      points.push({ x, y });
    }
    const controls = cmd === "Q" ? [points[0]] : cmd === "C" ? [points[0], points[1]] : [];
    const endpoint = cmd === "Z" ? [] : cmd === "Q" ? [points[1]] : cmd === "C" ? [points[2]] : points;
    commands.push({ type: cmd, points: endpoint, controls });
  }
  return commands;
}

function serializePath(commands) {
  const parts = [];
  for (const cmd of commands) {
    if (cmd.type === "Z") { parts.push("Z"); continue; }
    if (cmd.type === "M" || cmd.type === "L") {
      parts.push(cmd.type, fmt(cmd.points[0].x), fmt(cmd.points[0].y));
    } else if (cmd.type === "Q") {
      parts.push("Q", fmt(cmd.controls[0].x), fmt(cmd.controls[0].y), fmt(cmd.points[0].x), fmt(cmd.points[0].y));
    } else if (cmd.type === "C") {
      parts.push("C", fmt(cmd.controls[0].x), fmt(cmd.controls[0].y), fmt(cmd.controls[1].x), fmt(cmd.controls[1].y), fmt(cmd.points[0].x), fmt(cmd.points[0].y));
    }
  }
  return parts.join(" ");
}

function fmt(n) { return Number.isInteger(n) ? String(n) : String(Math.round(n * 1e6) / 1e6); }

function createOutlineShapePath(pathString, preset) {
  const bounds = pathBounds(parsePath(pathString));
  const width = bounds.maxX - bounds.minX;
  const height = bounds.maxY - bounds.minY;
  if (width <= 0 || height <= 0) throw new Error("Outline needs non-zero width and height");
  const cx = (bounds.minX + bounds.maxX) / 2;
  const cy = (bounds.minY + bounds.maxY) / 2;

  if (preset === "oval") return serializePath(ellipseCommands(cx, cy, width / 2, height / 2));
  if (preset === "circle") {
    const radius = Math.min(width, height) / 2;
    return serializePath(ellipseCommands(cx, cy, radius, radius));
  }
  if (preset === "pill") return serializePath(pillCommands(bounds));
  if (preset === "rounded-rectangle") return serializePath(roundedRectangleCommands(bounds, Math.min(width, height) / 5));
  if (preset === "rectangle") return serializePath(rectangleCommands(bounds));
  throw new Error("Choose a valid outline preset");
}

function pathBounds(commands) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  const include = (point) => {
    minX = Math.min(minX, point.x);
    minY = Math.min(minY, point.y);
    maxX = Math.max(maxX, point.x);
    maxY = Math.max(maxY, point.y);
  };
  let current = null;
  let start = null;
  for (const command of commands) {
    if (command.type === "M") {
      current = command.points[0];
      start = current;
      include(current);
    } else if (command.type === "L") {
      include(command.points[0]);
      current = command.points[0];
    } else if (command.type === "Q") {
      includeQuadraticExtrema(current, command.controls[0], command.points[0], include);
      current = command.points[0];
    } else if (command.type === "C") {
      includeCubicExtrema(current, command.controls[0], command.controls[1], command.points[0], include);
      current = command.points[0];
    } else if (command.type === "Z" && start) {
      include(start);
      current = start;
    }
  }
  return { minX, minY, maxX, maxY };
}

function includeQuadraticExtrema(p0, p1, p2, include) {
  include(p0);
  include(p2);
  for (const axis of ["x", "y"]) {
    const denominator = p0[axis] - 2 * p1[axis] + p2[axis];
    if (denominator === 0) continue;
    const t = (p0[axis] - p1[axis]) / denominator;
    if (t > 0 && t < 1) include(bezierQuad(p0, p1, p2, t));
  }
}

function includeCubicExtrema(p0, p1, p2, p3, include) {
  include(p0);
  include(p3);
  for (const axis of ["x", "y"]) {
    const a = -p0[axis] + 3 * p1[axis] - 3 * p2[axis] + p3[axis];
    const b = 2 * (p0[axis] - 2 * p1[axis] + p2[axis]);
    const c = p1[axis] - p0[axis];
    for (const t of quadraticRoots(a, b, c)) {
      if (t > 0 && t < 1) include(bezierCubic(p0, p1, p2, p3, t));
    }
  }
}

function quadraticRoots(a, b, c) {
  if (Math.abs(a) < Number.EPSILON) return Math.abs(b) < Number.EPSILON ? [] : [-c / b];
  const discriminant = b * b - 4 * a * c;
  if (discriminant < 0) return [];
  const root = Math.sqrt(discriminant);
  return [(-b + root) / (2 * a), (-b - root) / (2 * a)];
}

function bezierCubic(p0, p1, p2, p3, t) {
  const u = 1 - t;
  return {
    x: u ** 3 * p0.x + 3 * u ** 2 * t * p1.x + 3 * u * t ** 2 * p2.x + t ** 3 * p3.x,
    y: u ** 3 * p0.y + 3 * u ** 2 * t * p1.y + 3 * u * t ** 2 * p2.y + t ** 3 * p3.y,
  };
}

function ellipseCommands(cx, cy, rx, ry) {
  const k = 0.5522847498307936;
  return [
    { type: "M", points: [{ x: cx, y: cy - ry }], controls: [] },
    { type: "C", points: [{ x: cx + rx, y: cy }], controls: [{ x: cx + k * rx, y: cy - ry }, { x: cx + rx, y: cy - k * ry }] },
    { type: "C", points: [{ x: cx, y: cy + ry }], controls: [{ x: cx + rx, y: cy + k * ry }, { x: cx + k * rx, y: cy + ry }] },
    { type: "C", points: [{ x: cx - rx, y: cy }], controls: [{ x: cx - k * rx, y: cy + ry }, { x: cx - rx, y: cy + k * ry }] },
    { type: "C", points: [{ x: cx, y: cy - ry }], controls: [{ x: cx - rx, y: cy - k * ry }, { x: cx - k * rx, y: cy - ry }] },
    { type: "Z", points: [], controls: [] },
  ];
}

function rectangleCommands({ minX, minY, maxX, maxY }) {
  return [
    { type: "M", points: [{ x: minX, y: minY }], controls: [] },
    { type: "L", points: [{ x: maxX, y: minY }], controls: [] },
    { type: "L", points: [{ x: maxX, y: maxY }], controls: [] },
    { type: "L", points: [{ x: minX, y: maxY }], controls: [] },
    { type: "Z", points: [], controls: [] },
  ];
}

function roundedRectangleCommands({ minX, minY, maxX, maxY }, radius) {
  const k = 0.5522847498307936;
  return [
    { type: "M", points: [{ x: minX + radius, y: minY }], controls: [] },
    { type: "L", points: [{ x: maxX - radius, y: minY }], controls: [] },
    { type: "C", points: [{ x: maxX, y: minY + radius }], controls: [{ x: maxX - radius + k * radius, y: minY }, { x: maxX, y: minY + radius - k * radius }] },
    { type: "L", points: [{ x: maxX, y: maxY - radius }], controls: [] },
    { type: "C", points: [{ x: maxX - radius, y: maxY }], controls: [{ x: maxX, y: maxY - radius + k * radius }, { x: maxX - radius + k * radius, y: maxY }] },
    { type: "L", points: [{ x: minX + radius, y: maxY }], controls: [] },
    { type: "C", points: [{ x: minX, y: maxY - radius }], controls: [{ x: minX + radius - k * radius, y: maxY }, { x: minX, y: maxY - radius + k * radius }] },
    { type: "L", points: [{ x: minX, y: minY + radius }], controls: [] },
    { type: "C", points: [{ x: minX + radius, y: minY }], controls: [{ x: minX, y: minY + radius - k * radius }, { x: minX + radius - k * radius, y: minY }] },
    { type: "Z", points: [], controls: [] },
  ];
}

function pillCommands(bounds) {
  const { minX, minY, maxX, maxY } = bounds;
  const width = maxX - minX;
  const height = maxY - minY;
  const k = 0.5522847498307936;
  if (width >= height) {
    const radius = height / 2;
    const cy = minY + radius;
    return [
      { type: "M", points: [{ x: minX + radius, y: minY }], controls: [] },
      { type: "L", points: [{ x: maxX - radius, y: minY }], controls: [] },
      { type: "C", points: [{ x: maxX, y: cy }], controls: [{ x: maxX - radius + k * radius, y: minY }, { x: maxX, y: cy - k * radius }] },
      { type: "C", points: [{ x: maxX - radius, y: maxY }], controls: [{ x: maxX, y: cy + k * radius }, { x: maxX - radius + k * radius, y: maxY }] },
      { type: "L", points: [{ x: minX + radius, y: maxY }], controls: [] },
      { type: "C", points: [{ x: minX, y: cy }], controls: [{ x: minX + radius - k * radius, y: maxY }, { x: minX, y: cy + k * radius }] },
      { type: "C", points: [{ x: minX + radius, y: minY }], controls: [{ x: minX, y: cy - k * radius }, { x: minX + radius - k * radius, y: minY }] },
      { type: "Z", points: [], controls: [] },
    ];
  }
  const radius = width / 2;
  const cx = minX + radius;
  return [
    { type: "M", points: [{ x: minX, y: minY + radius }], controls: [] },
    { type: "L", points: [{ x: minX, y: maxY - radius }], controls: [] },
    { type: "C", points: [{ x: cx, y: maxY }], controls: [{ x: minX, y: maxY - radius + k * radius }, { x: cx - k * radius, y: maxY }] },
    { type: "C", points: [{ x: maxX, y: maxY - radius }], controls: [{ x: cx + k * radius, y: maxY }, { x: maxX, y: maxY - radius + k * radius }] },
    { type: "L", points: [{ x: maxX, y: minY + radius }], controls: [] },
    { type: "C", points: [{ x: cx, y: minY }], controls: [{ x: maxX, y: minY + radius - k * radius }, { x: cx + k * radius, y: minY }] },
    { type: "C", points: [{ x: minX, y: minY + radius }], controls: [{ x: cx - k * radius, y: minY }, { x: minX, y: minY + radius - k * radius }] },
    { type: "Z", points: [], controls: [] },
  ];
}

function moveVertex(commands, index, dx, dy) {
  const cmd = commands[index];
  if (!cmd || cmd.type === "Z") return;
  for (const p of cmd.points) { p.x += dx; p.y += dy; }
  if (cmd.type === "Q" || cmd.type === "C") {
    for (const c of cmd.controls) { c.x += dx; c.y += dy; }
  }
}

function addVertex(commands, afterIndex, x, y) {
  const cmd = commands[afterIndex];
  if (!cmd || cmd.type === "Z") return;
  const nextIndex = (afterIndex + 1) % commands.length;
  const next = commands[nextIndex];
  if (!next || next.type === "M") return;
  const p0 = cmd.points[cmd.points.length - 1];

  if (next.type === "Q") {
    const c = next.controls[0];
    const p1 = next.points[0];
    const mid = bezierQuad(p0, c, p1, 0.5);
    const newCmd1 = { type: "Q", points: [mid], controls: [lerp2(p0, c, 0.5)] };
    const newCmd2 = { type: "Q", points: [p1], controls: [lerp2(c, p1, 0.5)] };
    commands.splice(nextIndex, 1, newCmd1, newCmd2);
    return;
  }

  if (next.type === "C") {
    const c1 = next.controls[0];
    const c2 = next.controls[1];
    const p1 = next.points[0];
    const { left, right } = subdivideCubic(p0, c1, c2, p1);
    commands.splice(nextIndex, 1, left, right);
    return;
  }

  commands.splice(nextIndex, 0, { type: "L", points: [{ x, y }], controls: [] });
}

function deleteVertex(commands, index) {
  if (index === 0 || commands[index].type === "Z" || commands.length <= 3) return;
  const next = commands[(index + 1) % commands.length];

  commands.splice(index, 1);

  const nextIsCurve = next.type === "Q" || next.type === "C";
  if (nextIsCurve) {
    const idx = index % commands.length;
    const p = commands[idx].points[commands[idx].points.length - 1];
    commands[idx] = { type: "L", points: [p], controls: [] };
  }
}

function rotatePoint(point, pivot, angleRadians) {
  const cos = Math.cos(angleRadians);
  const sin = Math.sin(angleRadians);
  const dx = point.x - pivot.x;
  const dy = point.y - pivot.y;
  return { x: pivot.x + dx * cos - dy * sin, y: pivot.y + dx * sin + dy * cos };
}

function rotatePath(commands, angleRadians, pivot) {
  for (const cmd of commands) {
    if (cmd.type === "Z") continue;
    for (const p of cmd.points) Object.assign(p, rotatePoint(p, pivot, angleRadians));
    for (const c of cmd.controls) Object.assign(c, rotatePoint(c, pivot, angleRadians));
  }
}

function lerp2(a, b, t) { return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }; }

function bezierQuad(p0, c, p1, t) {
  const u = 1 - t;
  return {
    x: u * u * p0.x + 2 * u * t * c.x + t * t * p1.x,
    y: u * u * p0.y + 2 * u * t * c.y + t * t * p1.y,
  };
}

function subdivideCubic(p0, c1, c2, p3) {
  const m01 = lerp2(p0, c1, 0.5);
  const m12 = lerp2(c1, c2, 0.5);
  const m23 = lerp2(c2, p3, 0.5);
  const m012 = lerp2(m01, m12, 0.5);
  const m123 = lerp2(m12, m23, 0.5);
  const mid = lerp2(m012, m123, 0.5);
  return {
    left: { type: "C", points: [mid], controls: [m01, m012] },
    right: { type: "C", points: [p3], controls: [m123, m23] },
  };
}

const pathEditorExports = { parsePath, serializePath, createOutlineShapePath, moveVertex, addVertex, deleteVertex, rotatePath };
if (typeof module !== "undefined") module.exports = pathEditorExports;
if (typeof globalThis !== "undefined") globalThis.HoldPathEditor = pathEditorExports;
