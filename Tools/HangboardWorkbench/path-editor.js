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
      const x = parseFloat(tokens[i++]);
      const y = parseFloat(tokens[i++]);
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

module.exports = { parsePath, serializePath, moveVertex };
