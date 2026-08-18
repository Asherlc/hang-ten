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

const pathEditorExports = { parsePath, serializePath, moveVertex, addVertex, deleteVertex };
if (typeof module !== "undefined") module.exports = pathEditorExports;
if (typeof globalThis !== "undefined") globalThis.HoldPathEditor = pathEditorExports;
