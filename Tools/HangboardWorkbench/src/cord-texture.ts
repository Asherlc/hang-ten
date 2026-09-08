import { parsePath } from "./path-editor.ts";
import type { PathCommand, Point } from "./types.ts";

export interface CordFiberMark {
  color: "dark" | 0 | 1;
  start: Point;
  end: Point;
  opacity: number;
  width: number;
}

interface PolylinePoint extends Point {
  distance: number;
}

function distance(first: Point, second: Point): number {
  return Math.hypot(second.x - first.x, second.y - first.y);
}

function quadraticPoint(start: Point, control: Point, end: Point, amount: number): Point {
  const inverse = 1 - amount;
  return {
    x: inverse * inverse * start.x + 2 * inverse * amount * control.x + amount * amount * end.x,
    y: inverse * inverse * start.y + 2 * inverse * amount * control.y + amount * amount * end.y,
  };
}

function cubicPoint(
  start: Point,
  firstControl: Point,
  secondControl: Point,
  end: Point,
  amount: number,
): Point {
  const inverse = 1 - amount;
  return {
    x: inverse ** 3 * start.x
      + 3 * inverse * inverse * amount * firstControl.x
      + 3 * inverse * amount * amount * secondControl.x
      + amount ** 3 * end.x,
    y: inverse ** 3 * start.y
      + 3 * inverse * inverse * amount * firstControl.y
      + 3 * inverse * amount * amount * secondControl.y
      + amount ** 3 * end.y,
  };
}

function appendSegment(
  points: Point[],
  command: PathCommand,
  start: Point,
  curveStep: number,
): Point {
  if (command.type === "M") return command.points[0]!;
  if (command.type === "L") {
    const end = command.points[0]!;
    points.push(end);
    return end;
  }
  if (command.type === "Q") {
    const control = command.controls[0]!;
    const end = command.points[0]!;
    const estimatedLength = distance(start, control) + distance(control, end);
    const steps = Math.max(2, Math.ceil(estimatedLength / curveStep));
    for (let index = 1; index <= steps; index += 1) {
      points.push(quadraticPoint(start, control, end, index / steps));
    }
    return end;
  }
  if (command.type === "C") {
    const firstControl = command.controls[0]!;
    const secondControl = command.controls[1]!;
    const end = command.points[0]!;
    const estimatedLength = distance(start, firstControl)
      + distance(firstControl, secondControl)
      + distance(secondControl, end);
    const steps = Math.max(3, Math.ceil(estimatedLength / curveStep));
    for (let index = 1; index <= steps; index += 1) {
      points.push(cubicPoint(start, firstControl, secondControl, end, index / steps));
    }
    return end;
  }
  return start;
}

function pathPolyline(path: string, curveStep: number): PolylinePoint[] {
  const points: Point[] = [];
  let current: Point | null = null;
  let subpathStart: Point | null = null;
  for (const command of parsePath(path)) {
    if (command.type === "M") {
      current = command.points[0]!;
      subpathStart = current;
      points.push(current);
      continue;
    }
    if (!current) continue;
    if (command.type === "Z") {
      if (subpathStart && distance(current, subpathStart) > 0) points.push(subpathStart);
      current = subpathStart;
      continue;
    }
    current = appendSegment(points, command, current, curveStep);
  }

  let traveled = 0;
  return points.map((point, index) => {
    if (index > 0) traveled += distance(points[index - 1]!, point);
    return { ...point, distance: traveled };
  });
}

function pointAndTangentAt(
  polyline: readonly PolylinePoint[],
  targetDistance: number,
): { point: Point; tangent: Point } | null {
  for (let index = 1; index < polyline.length; index += 1) {
    const start = polyline[index - 1]!;
    const end = polyline[index]!;
    if (end.distance < targetDistance) continue;
    const segmentLength = end.distance - start.distance;
    if (segmentLength <= 0) continue;
    const amount = Math.max(0, Math.min(1, (targetDistance - start.distance) / segmentLength));
    return {
      point: {
        x: start.x + (end.x - start.x) * amount,
        y: start.y + (end.y - start.y) * amount,
      },
      tangent: {
        x: (end.x - start.x) / segmentLength,
        y: (end.y - start.y) / segmentLength,
      },
    };
  }
  return null;
}

function fiberMark(
  sample: { point: Point; tangent: Point },
  diameter: number,
  color: CordFiberMark["color"],
): CordFiberMark {
  const normal = { x: -sample.tangent.y, y: sample.tangent.x };
  const light = color === 1;
  const dark = color === "dark";
  const alongStart = dark ? -0.15 : light ? -0.17 : -0.19;
  const alongEnd = dark ? 0.17 : light ? 0.17 : 0.19;
  const acrossStart = dark ? -0.25 : light ? 0.31 : -0.34;
  const acrossEnd = dark ? 0.13 : light ? -0.28 : 0.29;
  const translated = (along: number, across: number): Point => ({
    x: sample.point.x + diameter * (sample.tangent.x * along + normal.x * across),
    y: sample.point.y + diameter * (sample.tangent.y * along + normal.y * across),
  });
  return {
    color,
    start: translated(alongStart, acrossStart),
    end: translated(alongEnd, acrossEnd),
    opacity: dark ? 0.36 : light ? 0.46 : 0.58,
    width: diameter * (dark ? 0.026 : light ? 0.045 : 0.055),
  };
}

export function cordFiberMarks(path: string, diameter: number): CordFiberMark[] {
  const spacing = diameter * 0.46;
  const polyline = pathPolyline(path, Math.max(diameter * 0.22, 0.25));
  const pathLength = polyline.at(-1)?.distance ?? 0;
  if (pathLength <= diameter) return [];

  const marks: CordFiberMark[] = [];
  for (let distanceAlong = diameter * 0.34; distanceAlong < pathLength - diameter * 0.24; distanceAlong += spacing) {
    const yellowSample = pointAndTangentAt(polyline, distanceAlong);
    if (yellowSample) marks.push(fiberMark(yellowSample, diameter, 0));
    const lightSample = pointAndTangentAt(polyline, distanceAlong + spacing * 0.52);
    if (lightSample && distanceAlong + spacing * 0.52 < pathLength - diameter * 0.3) {
      marks.push(fiberMark(lightSample, diameter, 1));
    }
    const darkSample = pointAndTangentAt(polyline, distanceAlong + spacing * 0.26);
    if (darkSample && distanceAlong + spacing * 0.26 < pathLength - diameter * 0.3) {
      marks.push(fiberMark(darkSample, diameter, "dark"));
    }
  }
  return marks;
}
