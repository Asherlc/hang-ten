import type { EditorDocument, HoldRegion, PathEditor, Point } from "./types.ts";

export const ROTATION_HANDLE_RADIUS = 6;
export const ROTATION_HANDLE_OFFSET = 24;

interface CanvasSize {
  width: number;
  height: number;
}

interface SvgCoordinateSpace {
  getAttribute(name: string): string | null;
  getBoundingClientRect(): Pick<DOMRect, "left" | "top" | "width" | "height">;
  getScreenCTM?(): { inverse(): Pick<DOMMatrix, "a" | "b" | "c" | "d" | "e" | "f"> } | null;
}

interface ClientPoint {
  clientX: number;
  clientY: number;
}

export function cloneEditorDocument(document: EditorDocument): EditorDocument {
  return {
    schemaVersion: document.schemaVersion,
    canvas: { ...document.canvas },
    regions: document.regions.map((region) => ({
      ...region,
      ...(region.metadata ? { metadata: { ...region.metadata } } : {}),
      ...(region.depthRangeMillimeters ? { depthRangeMillimeters: { ...region.depthRangeMillimeters } } : {}),
      ...(region.shapeConstraint ? { shapeConstraint: { ...region.shapeConstraint } } : {}),
    })),
  };
}

export function normalizedConstraintRotation(degrees: number): number {
  const normalized = ((degrees + 180) % 360 + 360) % 360 - 180;
  return Object.is(normalized, -0) ? 0 : normalized;
}

export function holdSiblings(document: EditorDocument, hold: HoldRegion): HoldRegion[] {
  const holdId = hold.metadata?.holdID;
  return holdId === undefined
    ? [hold]
    : document.regions.filter((region) => region.metadata?.holdID === holdId);
}

export function holdCentroid(regions: readonly HoldRegion[], pathEditor: PathEditor): Point {
  let sumX = 0;
  let sumY = 0;
  let count = 0;
  for (const region of regions) {
    try {
      for (const command of pathEditor.parsePath(region.displayPath)) {
        if (command.type === "Z") continue;
        const point = command.points.at(-1);
        if (!point) continue;
        sumX += point.x;
        sumY += point.y;
        count += 1;
      }
    } catch {
      continue;
    }
  }
  return count === 0 ? { x: 0, y: 0 } : { x: sumX / count, y: sumY / count };
}

export function rotationHandlePosition(pivot: Point, canvas: CanvasSize): Point {
  const minX = Math.min(ROTATION_HANDLE_RADIUS, canvas.width / 2);
  const maxX = Math.max(canvas.width - ROTATION_HANDLE_RADIUS, canvas.width / 2);
  const minY = Math.min(ROTATION_HANDLE_RADIUS, canvas.height / 2);
  const maxY = Math.max(canvas.height - ROTATION_HANDLE_RADIUS, canvas.height / 2);
  const clamp = (value: number, min: number, max: number): number => Math.min(Math.max(value, min), max);
  const centeredX = clamp(pivot.x, minX, maxX);
  const centeredY = clamp(pivot.y, minY, maxY);
  const horizontalOffset = Math.sqrt(Math.max(
    0,
    ROTATION_HANDLE_OFFSET ** 2 - (centeredY - pivot.y) ** 2,
  ));
  const candidates: Point[] = [
    { x: centeredX, y: pivot.y - ROTATION_HANDLE_OFFSET },
    { x: pivot.x + horizontalOffset, y: centeredY },
    { x: pivot.x - horizontalOffset, y: centeredY },
    { x: centeredX, y: pivot.y + ROTATION_HANDLE_OFFSET },
  ];
  const inBounds = ({ x, y }: Point): boolean => x >= minX && x <= maxX && y >= minY && y <= maxY;
  const candidate = candidates.find(inBounds);
  if (candidate) return candidate;
  return [
    { x: minX, y: minY },
    { x: minX, y: maxY },
    { x: maxX, y: minY },
    { x: maxX, y: maxY },
  ].reduce((furthest, point) => (
    Math.hypot(point.x - pivot.x, point.y - pivot.y)
      > Math.hypot(furthest.x - pivot.x, furthest.y - pivot.y)
      ? point
      : furthest
  ));
}

export function normalizedRotationDegrees(input: string): number | null {
  const trimmed = input.trim();
  const degrees = Number(trimmed);
  return !trimmed || !Number.isFinite(degrees) || degrees === 0 ? null : degrees % 360;
}

export function svgPoint(svg: SvgCoordinateSpace, event: ClientPoint): Point {
  const ctm = svg.getScreenCTM?.();
  if (ctm) {
    try {
      const inverse = ctm.inverse();
      return {
        x: inverse.a * event.clientX + inverse.c * event.clientY + inverse.e,
        y: inverse.b * event.clientX + inverse.d * event.clientY + inverse.f,
      };
    } catch {
      // Fall through to viewBox conversion when the screen matrix is singular.
    }
  }
  const viewBox = (svg.getAttribute("viewBox") ?? "0 0 0 0").trim().split(/[\s,]+/u).map(Number);
  const [viewX = 0, viewY = 0, viewWidth = 0, viewHeight = 0] = viewBox;
  const rect = svg.getBoundingClientRect();
  const pointerOffset = { x: event.clientX - rect.left, y: event.clientY - rect.top };
  if (viewWidth <= 0 || viewHeight <= 0 || rect.width <= 0 || rect.height <= 0) {
    return pointerOffset;
  }
  const preserveAspectRatio = svg.getAttribute("preserveAspectRatio") ?? "xMidYMid meet";
  if (preserveAspectRatio.includes("none")) {
    return {
      x: viewX + (event.clientX - rect.left) * (viewWidth / rect.width),
      y: viewY + (event.clientY - rect.top) * (viewHeight / rect.height),
    };
  }
  const scale = Math.min(rect.width / viewWidth, rect.height / viewHeight);
  if (!Number.isFinite(scale) || scale <= 0) return pointerOffset;
  const offsetX = rect.left + (rect.width - viewWidth * scale) / 2;
  const offsetY = rect.top + (rect.height - viewHeight * scale) / 2;
  return {
    x: viewX + (event.clientX - offsetX) / scale,
    y: viewY + (event.clientY - offsetY) / scale,
  };
}

export function nextHoldId(document: EditorDocument): string {
  const ids = new Set(document.regions.map((region) => region.metadata?.holdID));
  let number = ids.size + 1;
  while (ids.has(`hold-${number}`)) number += 1;
  return `hold-${number}`;
}

export function nextRegionId(document: EditorDocument): number {
  const ids = document.regions.flatMap((region) => (
    typeof region.id === "number" && Number.isFinite(region.id) ? [region.id] : []
  ));
  return ids.length === 0 ? 1 : Math.max(...ids) + 1;
}
