import type { PathCommand, PathCommandType, Point } from "./types.ts";

const COMMAND_ARITY: Record<PathCommandType, number> = {
  M: 1,
  L: 1,
  Q: 2,
  C: 3,
  Z: 0,
};

function isPathCommandType(value: string): value is PathCommandType {
  return Object.hasOwn(COMMAND_ARITY, value);
}

export function parsePath(pathString: string): PathCommand[] {
  if (!pathString.trim()) {
    throw new Error("path must be a non-empty string");
  }
  const tokens = pathString.trim().split(/[\s,]+/);
  const commands: PathCommand[] = [];
  let index = 0;

  while (index < tokens.length) {
    const type = tokens[index];
    if (type === undefined || !isPathCommandType(type)) {
      throw new Error(`expected a command, got "${String(type)}"`);
    }
    index += 1;
    const coordinatePoints: Point[] = [];
    for (let pointIndex = 0; pointIndex < COMMAND_ARITY[type]; pointIndex += 1) {
      const x = Number(tokens[index]);
      const y = Number(tokens[index + 1]);
      index += 2;
      if (!Number.isFinite(x) || !Number.isFinite(y)) {
        throw new Error("expected a finite coordinate pair");
      }
      coordinatePoints.push({ x, y });
    }

    const controls = type === "Q"
      ? [coordinatePoints[0]!]
      : type === "C"
        ? [coordinatePoints[0]!, coordinatePoints[1]!]
        : [];
    const points = type === "Z"
      ? []
      : type === "Q"
        ? [coordinatePoints[1]!]
        : type === "C"
          ? [coordinatePoints[2]!]
          : coordinatePoints;
    commands.push({ type, points, controls });
  }

  return commands;
}

export function serializePath(commands: readonly PathCommand[]): string {
  const parts: string[] = [];
  for (const command of commands) {
    if (command.type === "Z") {
      parts.push("Z");
      continue;
    }
    if (command.type === "M" || command.type === "L") {
      const point = command.points[0]!;
      parts.push(command.type, formatCoordinate(point.x), formatCoordinate(point.y));
    } else if (command.type === "Q") {
      const control = command.controls[0]!;
      const point = command.points[0]!;
      parts.push(
        "Q",
        formatCoordinate(control.x),
        formatCoordinate(control.y),
        formatCoordinate(point.x),
        formatCoordinate(point.y),
      );
    } else {
      const firstControl = command.controls[0]!;
      const secondControl = command.controls[1]!;
      const point = command.points[0]!;
      parts.push(
        "C",
        formatCoordinate(firstControl.x),
        formatCoordinate(firstControl.y),
        formatCoordinate(secondControl.x),
        formatCoordinate(secondControl.y),
        formatCoordinate(point.x),
        formatCoordinate(point.y),
      );
    }
  }
  return parts.join(" ");
}

function formatCoordinate(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Math.round(value * 1e6) / 1e6);
}

export function moveVertex(
  commands: PathCommand[],
  index: number,
  deltaX: number,
  deltaY: number,
): void {
  const command = commands[index];
  if (command === undefined || command.type === "Z") return;
  for (const point of command.points) {
    point.x += deltaX;
    point.y += deltaY;
  }
  if (command.type === "Q" || command.type === "C") {
    for (const control of command.controls) {
      control.x += deltaX;
      control.y += deltaY;
    }
  }
}

export function addVertex(
  commands: PathCommand[],
  afterIndex: number,
  x: number,
  y: number,
): void {
  const command = commands[afterIndex];
  if (command === undefined || command.type === "Z") return;
  const nextIndex = (afterIndex + 1) % commands.length;
  const next = commands[nextIndex];
  if (next === undefined || next.type === "M") return;
  const start = command.points.at(-1)!;

  if (next.type === "Q") {
    const control = next.controls[0]!;
    const endpoint = next.points[0]!;
    const midpoint = quadraticPoint(start, control, endpoint, 0.5);
    commands.splice(
      nextIndex,
      1,
      { type: "Q", points: [midpoint], controls: [interpolate(start, control, 0.5)] },
      { type: "Q", points: [endpoint], controls: [interpolate(control, endpoint, 0.5)] },
    );
    return;
  }

  if (next.type === "C") {
    const { left, right } = subdivideCubic(
      start,
      next.controls[0]!,
      next.controls[1]!,
      next.points[0]!,
    );
    commands.splice(nextIndex, 1, left, right);
    return;
  }

  commands.splice(nextIndex, 0, {
    type: "L",
    points: [{ x, y }],
    controls: [],
  });
}

export function deleteVertex(commands: PathCommand[], index: number): void {
  const command = commands[index];
  if (index === 0 || command === undefined || command.type === "Z" || commands.length <= 3) return;
  const next = commands[(index + 1) % commands.length]!;

  commands.splice(index, 1);

  if (next.type === "Q" || next.type === "C") {
    const nextCommandIndex = index % commands.length;
    const endpoint = commands[nextCommandIndex]!.points.at(-1)!;
    commands[nextCommandIndex] = { type: "L", points: [endpoint], controls: [] };
  }
}

function rotatePoint(point: Point, pivot: Point, angleRadians: number): Point {
  const cosine = Math.cos(angleRadians);
  const sine = Math.sin(angleRadians);
  const deltaX = point.x - pivot.x;
  const deltaY = point.y - pivot.y;
  return {
    x: pivot.x + deltaX * cosine - deltaY * sine,
    y: pivot.y + deltaX * sine + deltaY * cosine,
  };
}

export function rotatePath(
  commands: PathCommand[],
  angleRadians: number,
  pivot: Point,
): void {
  for (const command of commands) {
    if (command.type === "Z") continue;
    for (const point of command.points) Object.assign(point, rotatePoint(point, pivot, angleRadians));
    for (const control of command.controls) Object.assign(control, rotatePoint(control, pivot, angleRadians));
  }
}

function interpolate(start: Point, end: Point, amount: number): Point {
  return {
    x: start.x + (end.x - start.x) * amount,
    y: start.y + (end.y - start.y) * amount,
  };
}

function quadraticPoint(start: Point, control: Point, end: Point, amount: number): Point {
  const inverse = 1 - amount;
  return {
    x: inverse * inverse * start.x + 2 * inverse * amount * control.x + amount * amount * end.x,
    y: inverse * inverse * start.y + 2 * inverse * amount * control.y + amount * amount * end.y,
  };
}

function subdivideCubic(
  start: Point,
  firstControl: Point,
  secondControl: Point,
  end: Point,
): { left: PathCommand; right: PathCommand } {
  const firstMidpoint = interpolate(start, firstControl, 0.5);
  const controlMidpoint = interpolate(firstControl, secondControl, 0.5);
  const lastMidpoint = interpolate(secondControl, end, 0.5);
  const leftControl = interpolate(firstMidpoint, controlMidpoint, 0.5);
  const rightControl = interpolate(controlMidpoint, lastMidpoint, 0.5);
  const midpoint = interpolate(leftControl, rightControl, 0.5);
  return {
    left: { type: "C", points: [midpoint], controls: [firstMidpoint, leftControl] },
    right: { type: "C", points: [end], controls: [rightControl, lastMidpoint] },
  };
}
