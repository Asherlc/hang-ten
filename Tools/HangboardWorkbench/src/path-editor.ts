import type {
  Bounds,
  ConstrainedHandle,
  ConstrainedOutlineModel,
  ConstrainedResizeResult,
  OutlinePreset,
  PathCommand,
  PathCommandType,
  Point,
  ShapeConstraint,
  ShapeConstraintShape,
} from "./types.ts";
import {
  isConstrainedHandle,
  validateShapeConstraint,
} from "./shape-constraints.ts";

const COMMAND_ARITY: Record<PathCommandType, number> = {
  M: 1,
  L: 1,
  Q: 2,
  C: 3,
  Z: 0,
};
const MIN_STABLE_SUBDIVISION_AMOUNT = 1e-4;

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

export function createOutlineShapePath(pathString: string, preset: OutlinePreset): string {
  const bounds = validPathBounds(parsePath(pathString));
  const width = bounds.maxX - bounds.minX;
  const height = bounds.maxY - bounds.minY;
  const centerX = (bounds.minX + bounds.maxX) / 2;
  const centerY = (bounds.minY + bounds.maxY) / 2;
  if (preset === "oval") return serializePath(ellipseCommands(centerX, centerY, width / 2, height / 2));
  if (preset === "circle") {
    const radius = Math.min(width, height) / 2;
    return serializePath(ellipseCommands(centerX, centerY, radius, radius));
  }
  if (preset === "pill") return serializePath(pillCommands(bounds));
  if (preset === "rounded-rectangle") {
    return serializePath(roundedRectangleCommands(bounds, Math.min(width, height) / 5));
  }
  if (preset === "rectangle") return serializePath(rectangleCommands(bounds));
  throw new Error("Choose a valid outline preset");
}

export function constrainedOutlineModel(
  pathString: string,
  constraint: unknown,
): ConstrainedOutlineModel {
  const shapeConstraint = validateShapeConstraint(constraint);
  const commands = parsePath(pathString);
  const worldBounds = validPathBounds(commands);
  const center = {
    x: (worldBounds.minX + worldBounds.maxX) / 2,
    y: (worldBounds.minY + worldBounds.maxY) / 2,
  };
  const rotationRadians = shapeConstraint.rotationDegrees * Math.PI / 180;
  rotatePath(commands, -rotationRadians, center);
  const intrinsicBounds = validPathBounds(commands);
  const { minX, minY, maxX, maxY } = intrinsicBounds;
  const midX = (minX + maxX) / 2;
  const midY = (minY + maxY) / 2;
  const localHandles: Record<ConstrainedHandle, Point> = {
    nw: { x: minX, y: minY },
    n: { x: midX, y: minY },
    ne: { x: maxX, y: minY },
    e: { x: maxX, y: midY },
    se: { x: maxX, y: maxY },
    s: { x: midX, y: maxY },
    sw: { x: minX, y: maxY },
    w: { x: minX, y: midY },
  };
  const handles = Object.fromEntries(
    Object.entries(localHandles).map(([handle, point]) => [
      handle,
      rotatePoint(point, center, rotationRadians),
    ]),
  ) as Record<ConstrainedHandle, Point>;
  return { center, rotationDegrees: shapeConstraint.rotationDegrees, intrinsicBounds, handles };
}

export function resizeConstrainedOutline(
  pathString: string,
  constraint: unknown,
  handle: ConstrainedHandle,
  pointer: Point,
  minimumSize = 2,
): ConstrainedResizeResult {
  const shapeConstraint = validateShapeConstraint(constraint);
  if (!isConstrainedHandle(handle)) throw new Error("Choose a valid resize handle");
  assertFinitePoint(pointer, "Resize pointer must be finite");
  if (!Number.isFinite(minimumSize) || minimumSize <= 0) throw new Error("Minimum size must be positive");

  const model = constrainedOutlineModel(pathString, shapeConstraint);
  const rotationRadians = shapeConstraint.rotationDegrees * Math.PI / 180;
  const localPointer = rotatePoint(pointer, model.center, -rotationRadians);
  assertFinitePoint(localPointer, "Constrained resize local pointer must be finite");
  const bounds = { ...model.intrinsicBounds };
  const originalWidth = bounds.maxX - bounds.minX;
  const originalHeight = bounds.maxY - bounds.minY;

  if (handle.includes("w")) bounds.minX = Math.min(localPointer.x, bounds.maxX - minimumSize);
  if (handle.includes("e")) bounds.maxX = Math.max(localPointer.x, bounds.minX + minimumSize);
  if (handle.includes("n")) bounds.minY = Math.min(localPointer.y, bounds.maxY - minimumSize);
  if (handle.includes("s")) bounds.maxY = Math.max(localPointer.y, bounds.minY + minimumSize);

  if (shapeConstraint.shape === "circle") {
    lockCircleBounds(bounds, model.intrinsicBounds, handle, originalWidth, originalHeight, minimumSize);
  }
  assertFiniteResizeBounds(bounds);

  const commands = constrainedPrimitiveCommands(shapeConstraint.shape, bounds);
  assertFiniteCommands(commands);
  rotatePath(commands, rotationRadians, model.center);
  assertFiniteCommands(commands);
  return { displayPath: serializePath(commands), shapeConstraint };
}

function validPathBounds(commands: readonly PathCommand[]): Bounds {
  const bounds = pathBounds(commands);
  const width = bounds.maxX - bounds.minX;
  const height = bounds.maxY - bounds.minY;
  if (!Object.values(bounds).every(Number.isFinite)
    || !Number.isFinite(width)
    || !Number.isFinite(height)
    || width <= 0
    || height <= 0) {
    throw new Error("Outline needs non-zero width and height");
  }
  return bounds;
}

function assertFinitePoint(point: Point, message: string): void {
  if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) throw new Error(message);
}

function assertFiniteResizeBounds(bounds: Bounds): void {
  const width = bounds.maxX - bounds.minX;
  const height = bounds.maxY - bounds.minY;
  if (!Object.values(bounds).every(Number.isFinite)
    || !Number.isFinite(width)
    || !Number.isFinite(height)) {
    throw new Error("Constrained resize dimensions must be finite");
  }
}

function assertFiniteCommands(commands: readonly PathCommand[]): void {
  for (const command of commands) {
    for (const point of [...command.points, ...command.controls]) {
      assertFinitePoint(point, "Constrained resize coordinates must be finite");
    }
  }
}

function lockCircleBounds(
  bounds: Bounds,
  originalBounds: Bounds,
  handle: ConstrainedHandle,
  originalWidth: number,
  originalHeight: number,
  minimumSize: number,
): void {
  const changesX = handle.includes("e") || handle.includes("w");
  const changesY = handle.includes("n") || handle.includes("s");
  const width = bounds.maxX - bounds.minX;
  const height = bounds.maxY - bounds.minY;
  let diameter = changesX && changesY
    ? Math.abs(width - originalWidth) >= Math.abs(height - originalHeight) ? width : height
    : changesX ? width : height;
  diameter = Math.max(minimumSize, diameter);

  if (changesX) {
    if (handle.includes("w")) bounds.minX = bounds.maxX - diameter;
    else bounds.maxX = bounds.minX + diameter;
  } else {
    const centerX = (originalBounds.minX + originalBounds.maxX) / 2;
    bounds.minX = centerX - diameter / 2;
    bounds.maxX = centerX + diameter / 2;
  }
  if (changesY) {
    if (handle.includes("n")) bounds.minY = bounds.maxY - diameter;
    else bounds.maxY = bounds.minY + diameter;
  } else {
    const centerY = (originalBounds.minY + originalBounds.maxY) / 2;
    bounds.minY = centerY - diameter / 2;
    bounds.maxY = centerY + diameter / 2;
  }
}

function constrainedPrimitiveCommands(shape: ShapeConstraintShape, bounds: Bounds): PathCommand[] {
  const width = bounds.maxX - bounds.minX;
  const height = bounds.maxY - bounds.minY;
  const centerX = (bounds.minX + bounds.maxX) / 2;
  const centerY = (bounds.minY + bounds.maxY) / 2;
  if (shape === "oval" || shape === "circle") {
    return ellipseCommands(centerX, centerY, width / 2, height / 2);
  }
  if (shape === "pill") return pillCommands(bounds);
  if (shape === "roundedRectangle") {
    return roundedRectangleCommands(bounds, Math.min(width, height) / 5);
  }
  return rectangleCommands(bounds);
}

export function pathBounds(commands: readonly PathCommand[]): Bounds {
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  const include = (point: Point): void => {
    minX = Math.min(minX, point.x);
    minY = Math.min(minY, point.y);
    maxX = Math.max(maxX, point.x);
    maxY = Math.max(maxY, point.y);
  };
  let current: Point | null = null;
  let start: Point | null = null;
  for (const command of commands) {
    if (command.type === "M") {
      current = command.points[0]!;
      start = current;
      include(current);
    } else if (command.type === "L") {
      current = command.points[0]!;
      include(current);
    } else if (command.type === "Q" && current) {
      includeQuadraticExtrema(current, command.controls[0]!, command.points[0]!, include);
      current = command.points[0]!;
    } else if (command.type === "C" && current) {
      includeCubicExtrema(current, command.controls[0]!, command.controls[1]!, command.points[0]!, include);
      current = command.points[0]!;
    } else if (command.type === "Z" && start) {
      include(start);
      current = start;
    }
  }
  return { minX, minY, maxX, maxY };
}

function includeQuadraticExtrema(
  start: Point,
  control: Point,
  end: Point,
  include: (point: Point) => void,
): void {
  include(start);
  include(end);
  for (const axis of ["x", "y"] as const) {
    const denominator = start[axis] - 2 * control[axis] + end[axis];
    if (denominator === 0) continue;
    const amount = (start[axis] - control[axis]) / denominator;
    if (amount > 0 && amount < 1) include(quadraticPoint(start, control, end, amount));
  }
}

function includeCubicExtrema(
  start: Point,
  firstControl: Point,
  secondControl: Point,
  end: Point,
  include: (point: Point) => void,
): void {
  include(start);
  include(end);
  for (const axis of ["x", "y"] as const) {
    const a = -start[axis] + 3 * firstControl[axis] - 3 * secondControl[axis] + end[axis];
    const b = 2 * (start[axis] - 2 * firstControl[axis] + secondControl[axis]);
    const c = firstControl[axis] - start[axis];
    for (const amount of quadraticRoots(a, b, c)) {
      if (amount > 0 && amount < 1) include(cubicPoint(start, firstControl, secondControl, end, amount));
    }
  }
}

function quadraticRoots(a: number, b: number, c: number): number[] {
  if (Math.abs(a) < Number.EPSILON) return Math.abs(b) < Number.EPSILON ? [] : [-c / b];
  const discriminant = b * b - 4 * a * c;
  if (discriminant < 0) return [];
  const root = Math.sqrt(discriminant);
  return [(-b + root) / (2 * a), (-b - root) / (2 * a)];
}

function cubicPoint(start: Point, firstControl: Point, secondControl: Point, end: Point, amount: number): Point {
  const inverse = 1 - amount;
  return {
    x: inverse ** 3 * start.x + 3 * inverse ** 2 * amount * firstControl.x
      + 3 * inverse * amount ** 2 * secondControl.x + amount ** 3 * end.x,
    y: inverse ** 3 * start.y + 3 * inverse ** 2 * amount * firstControl.y
      + 3 * inverse * amount ** 2 * secondControl.y + amount ** 3 * end.y,
  };
}

function ellipseCommands(centerX: number, centerY: number, radiusX: number, radiusY: number): PathCommand[] {
  const kappa = 0.5522847498307936;
  return [
    { type: "M", points: [{ x: centerX, y: centerY - radiusY }], controls: [] },
    { type: "C", points: [{ x: centerX + radiusX, y: centerY }], controls: [{ x: centerX + kappa * radiusX, y: centerY - radiusY }, { x: centerX + radiusX, y: centerY - kappa * radiusY }] },
    { type: "C", points: [{ x: centerX, y: centerY + radiusY }], controls: [{ x: centerX + radiusX, y: centerY + kappa * radiusY }, { x: centerX + kappa * radiusX, y: centerY + radiusY }] },
    { type: "C", points: [{ x: centerX - radiusX, y: centerY }], controls: [{ x: centerX - kappa * radiusX, y: centerY + radiusY }, { x: centerX - radiusX, y: centerY + kappa * radiusY }] },
    { type: "C", points: [{ x: centerX, y: centerY - radiusY }], controls: [{ x: centerX - radiusX, y: centerY - kappa * radiusY }, { x: centerX - kappa * radiusX, y: centerY - radiusY }] },
    { type: "Z", points: [], controls: [] },
  ];
}

function rectangleCommands({ minX, minY, maxX, maxY }: Bounds): PathCommand[] {
  return [
    { type: "M", points: [{ x: minX, y: minY }], controls: [] },
    { type: "L", points: [{ x: maxX, y: minY }], controls: [] },
    { type: "L", points: [{ x: maxX, y: maxY }], controls: [] },
    { type: "L", points: [{ x: minX, y: maxY }], controls: [] },
    { type: "Z", points: [], controls: [] },
  ];
}

function roundedRectangleCommands(bounds: Bounds, radius: number): PathCommand[] {
  const { minX, minY, maxX, maxY } = bounds;
  const kappa = 0.5522847498307936;
  return [
    { type: "M", points: [{ x: minX + radius, y: minY }], controls: [] },
    { type: "L", points: [{ x: maxX - radius, y: minY }], controls: [] },
    { type: "C", points: [{ x: maxX, y: minY + radius }], controls: [{ x: maxX - radius + kappa * radius, y: minY }, { x: maxX, y: minY + radius - kappa * radius }] },
    { type: "L", points: [{ x: maxX, y: maxY - radius }], controls: [] },
    { type: "C", points: [{ x: maxX - radius, y: maxY }], controls: [{ x: maxX, y: maxY - radius + kappa * radius }, { x: maxX - radius + kappa * radius, y: maxY }] },
    { type: "L", points: [{ x: minX + radius, y: maxY }], controls: [] },
    { type: "C", points: [{ x: minX, y: maxY - radius }], controls: [{ x: minX + radius - kappa * radius, y: maxY }, { x: minX, y: maxY - radius + kappa * radius }] },
    { type: "L", points: [{ x: minX, y: minY + radius }], controls: [] },
    { type: "C", points: [{ x: minX + radius, y: minY }], controls: [{ x: minX, y: minY + radius - kappa * radius }, { x: minX + radius - kappa * radius, y: minY }] },
    { type: "Z", points: [], controls: [] },
  ];
}

function pillCommands(bounds: Bounds): PathCommand[] {
  const { minX, minY, maxX, maxY } = bounds;
  const width = maxX - minX;
  const height = maxY - minY;
  const kappa = 0.5522847498307936;
  if (width >= height) {
    const radius = height / 2;
    const centerY = minY + radius;
    return [
      { type: "M", points: [{ x: minX + radius, y: minY }], controls: [] },
      { type: "L", points: [{ x: maxX - radius, y: minY }], controls: [] },
      { type: "C", points: [{ x: maxX, y: centerY }], controls: [{ x: maxX - radius + kappa * radius, y: minY }, { x: maxX, y: centerY - kappa * radius }] },
      { type: "C", points: [{ x: maxX - radius, y: maxY }], controls: [{ x: maxX, y: centerY + kappa * radius }, { x: maxX - radius + kappa * radius, y: maxY }] },
      { type: "L", points: [{ x: minX + radius, y: maxY }], controls: [] },
      { type: "C", points: [{ x: minX, y: centerY }], controls: [{ x: minX + radius - kappa * radius, y: maxY }, { x: minX, y: centerY + kappa * radius }] },
      { type: "C", points: [{ x: minX + radius, y: minY }], controls: [{ x: minX, y: centerY - kappa * radius }, { x: minX + radius - kappa * radius, y: minY }] },
      { type: "Z", points: [], controls: [] },
    ];
  }
  const radius = width / 2;
  const centerX = minX + radius;
  return [
    { type: "M", points: [{ x: minX, y: minY + radius }], controls: [] },
    { type: "L", points: [{ x: minX, y: maxY - radius }], controls: [] },
    { type: "C", points: [{ x: centerX, y: maxY }], controls: [{ x: minX, y: maxY - radius + kappa * radius }, { x: centerX - kappa * radius, y: maxY }] },
    { type: "C", points: [{ x: maxX, y: maxY - radius }], controls: [{ x: centerX + kappa * radius, y: maxY }, { x: maxX, y: maxY - radius + kappa * radius }] },
    { type: "L", points: [{ x: maxX, y: minY + radius }], controls: [] },
    { type: "C", points: [{ x: centerX, y: minY }], controls: [{ x: maxX, y: minY + radius - kappa * radius }, { x: centerX + kappa * radius, y: minY }] },
    { type: "C", points: [{ x: minX, y: minY + radius }], controls: [{ x: centerX - kappa * radius, y: minY }, { x: minX, y: minY + radius - kappa * radius }] },
    { type: "Z", points: [], controls: [] },
  ];
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

export function addInflectionPoint(
  commands: PathCommand[],
  afterIndex: number,
  point: Point,
): boolean {
  const start = commands[afterIndex]?.points.at(-1);
  const curve = commands[afterIndex + 1];
  if (!start || (curve?.type !== "Q" && curve?.type !== "C")) return false;

  const amount = nearestCurveAmount(start, curve, point);
  if (amount <= 0 || amount >= 1) return false;
  const split = curve.type === "Q"
    ? subdivideQuadratic(start, curve.controls[0]!, curve.points[0]!, amount)
    : subdivideCubic(start, curve.controls[0]!, curve.controls[1]!, curve.points[0]!, amount);
  commands.splice(afterIndex + 1, 1, split.left, split.right);
  return true;
}

export function isInflectionVertex(commands: readonly PathCommand[], index: number): boolean {
  return mergedInflectionCurve(commands, index) !== null;
}

export function deleteVertex(commands: PathCommand[], index: number): void {
  const command = commands[index];
  const drawableVertexCount = commands.filter(
    (candidate) => candidate.type !== "Z" && candidate.points.length > 0,
  ).length;
  if (command === undefined
    || command.type === "Z"
    || (command.type === "M" && index !== 0)
    || drawableVertexCount <= 3) return;

  if (index === 0) {
    const next = commands[1];
    if (next === undefined || next.type === "Z") return;
    commands[0] = { type: "M", points: [next.points.at(-1)!], controls: [] };
    commands.splice(1, 1);
    return;
  }

  const mergedCurve = mergedInflectionCurve(commands, index);
  if (mergedCurve) {
    commands.splice(index, 2, mergedCurve);
    return;
  }

  const next = commands[(index + 1) % commands.length]!;

  commands.splice(index, 1);

  if (next.type === "Q" || next.type === "C") {
    const nextCommandIndex = index % commands.length;
    const endpoint = commands[nextCommandIndex]!.points.at(-1)!;
    commands[nextCommandIndex] = { type: "L", points: [endpoint], controls: [] };
  }
}

export function makeSegmentBendable(commands: PathCommand[], afterIndex: number): boolean {
  const start = commands[afterIndex]?.points.at(-1);
  const next = commands[afterIndex + 1];
  if (!start) return false;
  const closingEdge = next?.type === "Z" && afterIndex + 1 === commands.length - 1;
  const end = closingEdge
    ? commands[0]?.type === "M" ? commands[0].points[0] : undefined
    : next?.type === "L" ? next.points[0] : undefined;
  if (!end || pointsMatch(start, end)) return false;
  const curve: PathCommand = {
    type: "C",
    points: [{ ...end }],
    controls: [interpolate(start, end, 1 / 3), interpolate(start, end, 2 / 3)],
  };
  if (closingEdge) {
    commands.splice(afterIndex + 1, 1, curve, { type: "Z", points: [], controls: [] });
  } else {
    commands[afterIndex + 1] = curve;
  }
  return true;
}

export function makeSegmentStraight(commands: PathCommand[], afterIndex: number): boolean {
  const start = commands[afterIndex]?.points.at(-1);
  const curve = commands[afterIndex + 1];
  if (!start || (curve?.type !== "Q" && curve?.type !== "C")) return false;
  const end = curve.points[0];
  if (!end || pointsMatch(start, end)) return false;
  commands[afterIndex + 1] = { type: "L", points: [{ ...end }], controls: [] };
  return true;
}

export function snapSegmentHorizontal(commands: PathCommand[], afterIndex: number): boolean {
  return snapSegmentToAxis(commands, afterIndex, "horizontal");
}

export function snapSegmentVertical(commands: PathCommand[], afterIndex: number): boolean {
  return snapSegmentToAxis(commands, afterIndex, "vertical");
}

function snapSegmentToAxis(
  commands: PathCommand[],
  afterIndex: number,
  axis: "horizontal" | "vertical",
): boolean {
  const start = commands[afterIndex]?.points.at(-1);
  const next = commands[afterIndex + 1];
  const closingEdge = next?.type === "Z" && afterIndex + 1 === commands.length - 1;
  const end = closingEdge
    ? commands[0]?.type === "M" ? commands[0].points[0] : undefined
    : next?.type === "L" ? next.points[0] : undefined;
  if (!start || !end || (axis === "horizontal" ? start.y === end.y : start.x === end.x)) return false;

  const snappedEnd = axis === "horizontal"
    ? { x: end.x, y: start.y }
    : { x: start.x, y: end.y };
  if (closingEdge) {
    commands.splice(afterIndex + 1, 0, { type: "L", points: [snappedEnd], controls: [] });
  } else {
    commands[afterIndex + 1] = { type: "L", points: [snappedEnd], controls: [] };
  }
  return true;
}

export function roundVertex(commands: PathCommand[], index: number): boolean {
  if (index === 0) return roundStartVertex(commands);
  if (index === commands.length - 2) return roundLastVertex(commands);
  const previous = commands[index - 1];
  const vertex = commands[index];
  const next = commands[index + 1];
  if (!previous?.points.at(-1) || vertex?.type !== "L" || next?.type !== "L") return false;

  const start = previous.points.at(-1)!;
  const corner = vertex.points[0];
  const end = next.points[0];
  if (!corner || !end || pointsMatch(start, corner) || pointsMatch(corner, end) || areCollinear(start, corner, end)) {
    return false;
  }

  const trim = 0.2;
  const incoming = interpolate(corner, start, trim);
  const outgoing = interpolate(corner, end, trim);
  vertex.points = [incoming];
  commands.splice(
    index + 1,
    1,
    { type: "Q", points: [outgoing], controls: [{ ...corner }] },
    { type: "L", points: [{ ...end }], controls: [] },
  );
  return true;
}

function roundStartVertex(commands: PathCommand[]): boolean {
  const vertex = commands[0];
  const next = commands[1];
  const previous = commands.at(-2);
  if (vertex?.type !== "M" || next?.type !== "L" || previous?.type !== "L" || commands.at(-1)?.type !== "Z") {
    return false;
  }
  const start = previous.points.at(-1);
  const corner = vertex.points[0];
  const end = next.points[0];
  if (!start || !corner || !end || pointsMatch(start, corner) || pointsMatch(corner, end) || areCollinear(start, corner, end)) {
    return false;
  }

  const trim = 0.2;
  vertex.points = [interpolate(corner, start, trim)];
  commands.splice(
    1,
    1,
    { type: "Q", points: [interpolate(corner, end, trim)], controls: [{ ...corner }] },
    { type: "L", points: [{ ...end }], controls: [] },
  );
  return true;
}

function roundLastVertex(commands: PathCommand[]): boolean {
  const previous = commands[commands.length - 3];
  const vertex = commands[commands.length - 2];
  const close = commands.at(-1);
  const startCommand = commands[0];
  if (previous?.type !== "L" || vertex?.type !== "L" || close?.type !== "Z" || startCommand?.type !== "M") {
    return false;
  }
  const start = previous.points.at(-1);
  const corner = vertex.points[0];
  const end = startCommand.points[0];
  if (!start || !corner || !end || pointsMatch(start, corner) || pointsMatch(corner, end) || areCollinear(start, corner, end)) {
    return false;
  }

  const trim = 0.2;
  vertex.points = [interpolate(corner, start, trim)];
  commands.splice(
    commands.length - 1,
    1,
    { type: "Q", points: [interpolate(corner, end, trim)], controls: [{ ...corner }] },
    { type: "Z", points: [], controls: [] },
  );
  return true;
}

function pointsMatch(left: Point, right: Point): boolean {
  return left.x === right.x && left.y === right.y;
}

function areCollinear(start: Point, corner: Point, end: Point): boolean {
  const incomingX = corner.x - start.x;
  const incomingY = corner.y - start.y;
  const outgoingX = end.x - corner.x;
  const outgoingY = end.y - corner.y;
  return Math.abs(incomingX * outgoingY - incomingY * outgoingX) <= 1e-9;
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

function subdivideQuadratic(
  start: Point,
  control: Point,
  end: Point,
  amount: number,
): { left: PathCommand; right: PathCommand } {
  const firstControl = interpolate(start, control, amount);
  const secondControl = interpolate(control, end, amount);
  const midpoint = interpolate(firstControl, secondControl, amount);
  return {
    left: { type: "Q", points: [midpoint], controls: [firstControl] },
    right: { type: "Q", points: [end], controls: [secondControl] },
  };
}

function subdivideCubic(
  start: Point,
  firstControl: Point,
  secondControl: Point,
  end: Point,
  amount = 0.5,
): { left: PathCommand; right: PathCommand } {
  const firstMidpoint = interpolate(start, firstControl, amount);
  const controlMidpoint = interpolate(firstControl, secondControl, amount);
  const lastMidpoint = interpolate(secondControl, end, amount);
  const leftControl = interpolate(firstMidpoint, controlMidpoint, amount);
  const rightControl = interpolate(controlMidpoint, lastMidpoint, amount);
  const midpoint = interpolate(leftControl, rightControl, amount);
  return {
    left: { type: "C", points: [midpoint], controls: [firstMidpoint, leftControl] },
    right: { type: "C", points: [end], controls: [rightControl, lastMidpoint] },
  };
}

function nearestCurveAmount(start: Point, curve: PathCommand, point: Point): number {
  let bestAmount = 0;
  let bestDistanceSquared = Number.POSITIVE_INFINITY;
  const samples = 128;
  for (let index = 1; index < samples; index += 1) {
    const amount = index / samples;
    const candidate = curvePoint(start, curve, amount);
    const distanceSquared = squaredDistance(candidate, point);
    if (distanceSquared < bestDistanceSquared) {
      bestAmount = amount;
      bestDistanceSquared = distanceSquared;
    }
  }
  if (bestDistanceSquared < 1e-12) return bestAmount;

  let lower = Math.max(0, bestAmount - 1 / samples);
  let upper = Math.min(1, bestAmount + 1 / samples);
  for (let iteration = 0; iteration < 20; iteration += 1) {
    const first = lower + (upper - lower) / 3;
    const second = upper - (upper - lower) / 3;
    if (squaredDistance(curvePoint(start, curve, first), point)
      <= squaredDistance(curvePoint(start, curve, second), point)) {
      upper = second;
    } else {
      lower = first;
    }
  }
  return (lower + upper) / 2;
}

function curvePoint(start: Point, curve: PathCommand, amount: number): Point {
  if (curve.type === "Q") return quadraticPoint(start, curve.controls[0]!, curve.points[0]!, amount);
  return cubicPoint(start, curve.controls[0]!, curve.controls[1]!, curve.points[0]!, amount);
}

function squaredDistance(left: Point, right: Point): number {
  return (left.x - right.x) ** 2 + (left.y - right.y) ** 2;
}

function mergedInflectionCurve(commands: readonly PathCommand[], index: number): PathCommand | null {
  const previous = commands[index - 1];
  const left = commands[index];
  const right = commands[index + 1];
  if (!previous?.points.at(-1) || !left || !right
    || (left.type !== "Q" && left.type !== "C") || left.type !== right.type) return null;
  const start = previous.points.at(-1)!;
  const vertex = left.points[0];
  const end = right.points[0];
  const incomingControl = left.controls.at(-1);
  const outgoingControl = right.controls[0];
  if (!vertex || !end || !incomingControl || !outgoingControl) return null;
  const incomingLength = Math.hypot(vertex.x - incomingControl.x, vertex.y - incomingControl.y);
  const outgoingLength = Math.hypot(outgoingControl.x - vertex.x, outgoingControl.y - vertex.y);
  const amount = mergeAmount(start, vertex, end, incomingLength, outgoingLength);
  if (amount !== null && hasStableSubdivisionAmount(amount)) {
    const merged = left.type === "Q"
      ? mergeQuadratic(start, left, right, amount, subdivisionTolerance(amount))
      : mergeCubic(start, left, right, amount);
    if (merged) {
      const split = merged.type === "Q"
        ? subdivideQuadratic(start, merged.controls[0]!, end, amount)
        : subdivideCubic(start, merged.controls[0]!, merged.controls[1]!, end, amount);
      if (commandsMatch(split.left, left, subdivisionTolerance(amount))
        && commandsMatch(split.right, right, subdivisionTolerance(amount))) return merged;
    }
  }

  return left.type === "Q"
    ? fallbackQuadraticMerge(left, right)
    : fallbackCubicMerge(left, right);
}

function hasStableSubdivisionAmount(amount: number): boolean {
  return Number.isFinite(amount)
    && amount >= MIN_STABLE_SUBDIVISION_AMOUNT
    && amount <= 1 - MIN_STABLE_SUBDIVISION_AMOUNT;
}

function mergeAmount(
  start: Point,
  vertex: Point,
  end: Point,
  incomingLength: number,
  outgoingLength: number,
): number | null {
  const handleLength = incomingLength + outgoingLength;
  if (handleLength > 1e-9) return incomingLength / handleLength;

  const incomingChord = Math.hypot(vertex.x - start.x, vertex.y - start.y);
  const outgoingChord = Math.hypot(end.x - vertex.x, end.y - vertex.y);
  const chordLength = incomingChord + outgoingChord;
  return chordLength > 1e-9 ? incomingChord / chordLength : null;
}

function mergeQuadratic(
  start: Point,
  left: PathCommand,
  right: PathCommand,
  amount: number,
  tolerance: number,
): PathCommand | null {
  const first = left.controls[0];
  const second = right.controls[0];
  const end = right.points[0];
  if (!first || !second || !end) return null;
  const fromStart = extrapolate(start, first, amount);
  const fromEnd = extrapolate(end, second, 1 - amount);
  if (!pointsClose(fromStart, fromEnd, tolerance)) return null;
  return { type: "Q", points: [{ ...end }], controls: [fromStart] };
}

function fallbackQuadraticMerge(
  left: PathCommand,
  right: PathCommand,
): PathCommand | null {
  const first = left.controls[0];
  const second = right.controls[0];
  const end = right.points[0];
  if (!first || !second || !end) return null;
  return {
    type: "Q",
    points: [{ ...end }],
    controls: [stableMidpoint(first, second)],
  };
}

function stableMidpoint(first: Point, second: Point): Point {
  return {
    x: first.x / 2 + second.x / 2,
    y: first.y / 2 + second.y / 2,
  };
}

function mergeCubic(start: Point, left: PathCommand, right: PathCommand, amount: number): PathCommand | null {
  const first = left.controls[0];
  const second = right.controls[1];
  const end = right.points[0];
  if (!first || !second || !end) return null;
  return {
    type: "C",
    points: [{ ...end }],
    controls: [extrapolate(start, first, amount), extrapolate(end, second, 1 - amount)],
  };
}

function fallbackCubicMerge(left: PathCommand, right: PathCommand): PathCommand | null {
  const first = left.controls[0];
  const second = right.controls[1];
  const end = right.points[0];
  if (!first || !second || !end) return null;
  return {
    type: "C",
    points: [{ ...end }],
    controls: [{ ...first }, { ...second }],
  };
}

function extrapolate(start: Point, point: Point, amount: number): Point {
  return {
    x: start.x + (point.x - start.x) / amount,
    y: start.y + (point.y - start.y) / amount,
  };
}

function subdivisionTolerance(amount: number): number {
  return 4e-6 / Math.min(amount, 1 - amount);
}

function commandsMatch(left: PathCommand, right: PathCommand, tolerance: number): boolean {
  return left.type === right.type
    && left.points.length === right.points.length
    && left.controls.length === right.controls.length
    && left.points.every((point, index) => pointsClose(point, right.points[index]!, tolerance))
    && left.controls.every((point, index) => pointsClose(point, right.controls[index]!, tolerance));
}

function pointsClose(left: Point, right: Point, tolerance = 1e-6): boolean {
  return Math.abs(left.x - right.x) <= tolerance && Math.abs(left.y - right.y) <= tolerance;
}
