import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type {
  KeyboardEvent as ReactKeyboardEvent,
  MouseEvent as ReactMouseEvent,
  PointerEvent as ReactPointerEvent,
} from "react";

import {
  cloneEditorDocument,
  holdCentroid,
  holdSiblings,
  nextHoldId,
  nextRegionId,
  normalizedConstraintRotation,
  normalizedRotationDegrees,
  svgPoint,
} from "./editor-model.ts";
import { isConstrainedHandle, isConstrainedShape } from "./shape-constraints.ts";
import type {
  Dialogs,
  ConstrainedHandle,
  EditorDocument,
  HoldRegion,
  PathCommand,
  PathEditor,
  Point,
  ShapeConstraint,
  ShapeConstraintShape,
  WorkbenchActions,
} from "./types.ts";

interface DragState {
  active: boolean;
  type: "vertex" | "control" | "path" | "rotation" | "constrained-resize" | null;
  holdKey: string | null;
  commandIndex: number;
  controlIndex: number;
  startX: number;
  startY: number;
  commands: PathCommand[] | null;
  originalPath: string | null;
  originalPaths: Array<{ key: string; path: string; shapeConstraint?: ShapeConstraint }> | null;
  originalConstraint: ShapeConstraint | null;
  originalDocument: EditorDocument | null;
  resizeHandle: ConstrainedHandle | null;
  originalDirty: boolean;
  changed: boolean;
  pivot: Point | null;
  lastAngle: number;
  totalAngle: number;
  pointerId: number | null;
  pathCenter: Point | null;
}

interface VertexSelection {
  holdKey: string;
  commandIndex: number;
}

interface VertexMenuState {
  document: EditorDocument;
  holdKey: string;
  x: number;
  y: number;
  kind: "vertex" | "segment";
  segmentAfterIndex: number | null;
  invoker: Element;
}

const EMPTY_DRAG: DragState = {
  active: false,
  type: null,
  holdKey: null,
  commandIndex: -1,
  controlIndex: -1,
  startX: 0,
  startY: 0,
  commands: null,
  originalPath: null,
  originalPaths: null,
  originalConstraint: null,
  originalDocument: null,
  resizeHandle: null,
  originalDirty: false,
  changed: false,
  pivot: null,
  lastAngle: 0,
  totalAngle: 0,
  pointerId: null,
  pathCenter: null,
};

const GUIDE_SNAP_TOLERANCE = 6;

export interface UseHoldEditorOptions {
  document: EditorDocument | null;
  selectedHold: HoldRegion | null;
  selectedKeys: readonly string[];
  dirty: boolean;
  status: string;
  busy: boolean;
  rotationDegrees: string;
  actions: WorkbenchActions;
  pathEditor: PathEditor;
  validateEditorDocument(document: unknown): EditorDocument;
  dialogs: Dialogs;
  horizontalGuideYs: readonly number[];
  verticalGuideXs: readonly number[];
}

export interface HoldEditorActions {
  selectedVertexIndex: number | null;
  vertexMenu: { x: number; y: number; kind: "vertex" | "segment" } | null;
  canDeleteSelectedVertex: boolean;
  canRoundSelectedVertex: boolean;
  canMakeSelectedSegmentBendable: boolean;
  addHold(): void;
  deleteHold(): void;
  selectVertex(index: number): void;
  deleteSelectedVertex(): void;
  roundSelectedVertex(): void;
  makeSelectedSegmentBendable(): void;
  dismissVertexMenu(restoreFocus?: boolean): void;
  changeHoldType(type: string): void;
  changeOutlineShape(shape: string): void;
  rotateHold(degrees: number): void;
  applyRotation(): void;
  cancelActiveEdit(): boolean;
  onPointerDown(event: ReactPointerEvent<SVGSVGElement>): void;
  onPointerMove(event: ReactPointerEvent<SVGSVGElement>): void;
  onPointerUp(event: ReactPointerEvent<SVGSVGElement>): void;
  onPointerCancel(event: ReactPointerEvent<SVGSVGElement>): void;
  onLostPointerCapture(event: ReactPointerEvent<SVGSVGElement>): void;
  onDoubleClick(event: ReactMouseEvent<SVGSVGElement>): void;
  onContextMenu(event: ReactMouseEvent<SVGSVGElement>): void;
}

function cloneCommands(commands: readonly PathCommand[]): PathCommand[] {
  return commands.map((command) => ({
    ...command,
    points: command.points.map((point) => ({ ...point })),
    controls: command.controls.map((point) => ({ ...point })),
  }));
}

function translateCommands(commands: PathCommand[], deltaX: number, deltaY: number): void {
  for (const command of commands) {
    if (command.type === "Z") continue;
    for (const point of [...command.points, ...command.controls]) {
      point.x += deltaX;
      point.y += deltaY;
    }
  }
}

function nearbyGuideCoordinate(coordinates: readonly number[], value: number): number | null {
  let closest: number | null = null;
  for (const coordinate of coordinates) {
    if (!Number.isFinite(coordinate) || Math.abs(coordinate - value) > GUIDE_SNAP_TOLERANCE) continue;
    if (closest === null || Math.abs(coordinate - value) < Math.abs(closest - value)) closest = coordinate;
  }
  return closest;
}

function closestPointOnLine(start: Point, end: Point, point: Point): Point {
  const deltaX = end.x - start.x;
  const deltaY = end.y - start.y;
  const lengthSquared = deltaX * deltaX + deltaY * deltaY;
  if (lengthSquared === 0) return { ...start };
  const amount = Math.max(0, Math.min(
    1,
    ((point.x - start.x) * deltaX + (point.y - start.y) * deltaY) / lengthSquared,
  ));
  return { x: start.x + amount * deltaX, y: start.y + amount * deltaY };
}

function bezierPointAt(start: Point, command: PathCommand, amount: number): Point {
  const inverse = 1 - amount;
  if (command.type === "Q") {
    const control = command.controls[0]!;
    const end = command.points[0]!;
    return {
      x: inverse ** 2 * start.x + 2 * inverse * amount * control.x + amount ** 2 * end.x,
      y: inverse ** 2 * start.y + 2 * inverse * amount * control.y + amount ** 2 * end.y,
    };
  }
  if (command.type === "C") {
    const first = command.controls[0]!;
    const second = command.controls[1]!;
    const end = command.points[0]!;
    return {
      x: inverse ** 3 * start.x + 3 * inverse ** 2 * amount * first.x
        + 3 * inverse * amount ** 2 * second.x + amount ** 3 * end.x,
      y: inverse ** 3 * start.y + 3 * inverse ** 2 * amount * first.y
        + 3 * inverse * amount ** 2 * second.y + amount ** 3 * end.y,
    };
  }
  const end = command.points[0]!;
  return { x: start.x + (end.x - start.x) * amount, y: start.y + (end.y - start.y) * amount };
}

function closestDistanceOnSegment(start: Point, command: PathCommand, point: Point): number {
  let distance = Number.POSITIVE_INFINITY;
  let previous = start;
  for (let sample = 1; sample <= 20; sample += 1) {
    const current = bezierPointAt(start, command, sample / 20);
    const projected = closestPointOnLine(previous, current, point);
    distance = Math.min(distance, Math.hypot(point.x - projected.x, point.y - projected.y));
    previous = current;
  }
  return distance;
}

function targetElement(event: ReactPointerEvent<SVGSVGElement> | ReactMouseEvent<SVGSVGElement>): Element | null {
  return event.target instanceof Element ? event.target : null;
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

function cloneConstraint(constraint: ShapeConstraint | undefined): ShapeConstraint | undefined {
  return constraint ? { ...constraint } : undefined;
}

function constraintsMatch(
  left: ShapeConstraint | null | undefined,
  right: ShapeConstraint | null | undefined,
): boolean {
  if (!left || !right) return !left && !right;
  return left.shape === right.shape && left.rotationDegrees === right.rotationDegrees;
}

function draggedRegionsMatch(
  drag: DragState,
  left: EditorDocument,
  right: EditorDocument,
): boolean {
  const keys = drag.type === "rotation"
    ? (drag.originalPaths ?? []).map((original) => original.key)
    : drag.holdKey ? [drag.holdKey] : [];
  return keys.every((key) => {
    const leftRegion = left.regions.find((region) => region.key === key);
    const rightRegion = right.regions.find((region) => region.key === key);
    return !!leftRegion && !!rightRegion
      && leftRegion.displayPath === rightRegion.displayPath
      && constraintsMatch(leftRegion.shapeConstraint, rightRegion.shapeConstraint);
  });
}

function dragMatchesOriginal(drag: DragState, document: EditorDocument): boolean {
  if (drag.type === "rotation") {
    return (drag.originalPaths ?? []).every((original) => {
      const region = document.regions.find((candidate) => candidate.key === original.key);
      return !!region
        && region.displayPath === original.path
        && constraintsMatch(region.shapeConstraint, original.shapeConstraint);
    });
  }
  const region = document.regions.find((candidate) => candidate.key === drag.holdKey);
  return !!region
    && region.displayPath === drag.originalPath
    && constraintsMatch(region.shapeConstraint, drag.originalConstraint);
}

function isShapeConstraintShape(value: string): value is ShapeConstraintShape {
  return isConstrainedShape(value);
}

function outlinePreset(shape: ShapeConstraintShape): "oval" | "circle" | "pill" | "rounded-rectangle" | "rectangle" {
  return shape === "roundedRectangle" ? "rounded-rectangle" : shape;
}

function canDeleteVertex(commands: readonly PathCommand[], index: number): boolean {
  const command = commands[index];
  if (!command || command.type === "Z" || (command.type === "M" && index !== 0)) return false;
  return commands.filter((candidate) => candidate.type !== "Z" && candidate.points.length > 0).length > 3;
}

function selectedPhysicalHolds(document: EditorDocument, selectedKeys: readonly string[]): HoldRegion[][] {
  const selected = new Set(selectedKeys);
  const groups = new Map<string, HoldRegion[]>();
  for (const region of document.regions) {
    if (!selected.has(region.key)) continue;
    const siblings = holdSiblings(document, region);
    groups.set(siblings.map((sibling) => sibling.key).join("\u0000"), siblings);
  }
  return [...groups.values()];
}

function hasVertex(commands: readonly PathCommand[], index: number): boolean {
  const command = commands[index];
  return !!command && command.type !== "Z" && command.points.length > 0;
}

function closestStraightSegmentIndex(
  commands: readonly PathCommand[],
  point: Point,
  maximumDistance = 15,
): number | null {
  let closestIndex: number | null = null;
  let closestDistance = maximumDistance;
  for (let index = 0; index + 1 < commands.length; index += 1) {
    const start = commands[index]?.points.at(-1);
    const next = commands[index + 1];
    const end = next?.type === "L"
      ? next.points[0]
      : next?.type === "Z" && index + 1 === commands.length - 1 && commands[0]?.type === "M"
        ? commands[0].points[0]
        : undefined;
    if (!start || !end) continue;
    const closest = closestPointOnLine(start, end, point);
    const distance = Math.hypot(point.x - closest.x, point.y - closest.y);
    if (distance < closestDistance) {
      closestDistance = distance;
      closestIndex = index;
    }
  }
  return closestIndex;
}

export function useHoldEditor(options: UseHoldEditorOptions): HoldEditorActions {
  const {
    document,
    selectedHold,
    selectedKeys,
    dirty,
    status,
    busy,
    rotationDegrees,
    actions,
    pathEditor,
    validateEditorDocument,
    dialogs,
    horizontalGuideYs,
    verticalGuideXs,
  } = options;
  const dragRef = useRef<DragState>({ ...EMPTY_DRAG });
  const previewDocumentRef = useRef<EditorDocument | null>(null);
  const pendingPreviewRef = useRef<EditorDocument | null>(null);
  const dragSvgRef = useRef<SVGSVGElement | null>(null);
  const [vertexSelection, setVertexSelection] = useState<VertexSelection | null>(null);
  const [vertexMenuState, setVertexMenuState] = useState<VertexMenuState | null>(null);
  const reportInvalidPath = useCallback((error: unknown): void => {
    actions.editDocument(() => { throw error; }, {
      failureStatus: "Could not edit — selected hold has an invalid path.",
      failureMessage: errorMessage(error, "Selected hold path is invalid."),
    });
  }, [actions]);

  let selectionIsCurrent = false;
  let canDeleteSelectedVertex = false;
  let canRoundSelectedVertex = false;
  let canMakeSelectedSegmentBendable = false;
  if (!busy && document && selectedHold && !selectedHold.shapeConstraint) {
    try {
      const commands = pathEditor.parsePath(selectedHold.displayPath);
      if (vertexSelection?.holdKey === selectedHold.key) {
        selectionIsCurrent = hasVertex(commands, vertexSelection.commandIndex);
        canDeleteSelectedVertex = selectionIsCurrent
          && canDeleteVertex(commands, vertexSelection.commandIndex);
      }
      if (selectionIsCurrent && vertexSelection) {
        const candidate = cloneCommands(commands);
        canRoundSelectedVertex = pathEditor.roundVertex(candidate, vertexSelection.commandIndex);
      }
      if (vertexMenuState?.document === document
        && vertexMenuState.holdKey === selectedHold.key
        && vertexMenuState.segmentAfterIndex !== null) {
        const candidate = cloneCommands(commands);
        canMakeSelectedSegmentBendable = pathEditor.makeSegmentBendable(
          candidate,
          vertexMenuState.segmentAfterIndex,
        );
      }
    } catch {
      selectionIsCurrent = false;
      canDeleteSelectedVertex = false;
      canRoundSelectedVertex = false;
      canMakeSelectedSegmentBendable = false;
    }
  }
  const selectedVertexIndex = selectionIsCurrent ? vertexSelection!.commandIndex : null;
  const menuIsCurrent = vertexMenuState?.document === document
    && vertexMenuState.holdKey === selectedHold?.key
    && (selectionIsCurrent || vertexMenuState.segmentAfterIndex !== null);
  const vertexMenu = menuIsCurrent
    ? { x: vertexMenuState.x, y: vertexMenuState.y, kind: vertexMenuState.kind }
    : null;

  const selectVertex = useCallback((index: number): void => {
    if (busy || !selectedHold || selectedHold.shapeConstraint || !Number.isInteger(index) || index < 0) return;
    try {
      if (!hasVertex(pathEditor.parsePath(selectedHold.displayPath), index)) return;
      setVertexSelection({ holdKey: selectedHold.key, commandIndex: index });
      setVertexMenuState(null);
    } catch {
      // Invalid paths do not render selectable vertices.
    }
  }, [busy, pathEditor, selectedHold]);

  const deleteSelectedVertex = useCallback((): void => {
    if (!canDeleteSelectedVertex || !document || !selectedHold || selectedVertexIndex === null) return;
    try {
      const commands = pathEditor.parsePath(selectedHold.displayPath);
      if (!canDeleteVertex(commands, selectedVertexIndex)) return;
      pathEditor.deleteVertex(commands, selectedVertexIndex);
      const nextPath = pathEditor.serializePath(commands);
      if (nextPath === selectedHold.displayPath) return;
      const edited = actions.editDocument((candidate) => {
        const hold = candidate.regions.find((region) => region.key === selectedHold.key);
        if (hold && !hold.shapeConstraint) hold.displayPath = nextPath;
      }, { status });
      if (!edited) return;
      setVertexSelection(null);
      setVertexMenuState(null);
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [
    actions,
    canDeleteSelectedVertex,
    document,
    pathEditor,
    reportInvalidPath,
    selectedHold,
    selectedVertexIndex,
    status,
  ]);

  const roundSelectedVertex = useCallback((): void => {
    if (!canRoundSelectedVertex || !document || !selectedHold || selectedVertexIndex === null
      || vertexMenuState?.holdKey !== selectedHold.key || vertexMenuState.segmentAfterIndex !== null) return;
    try {
      const commands = pathEditor.parsePath(selectedHold.displayPath);
      if (!pathEditor.roundVertex(commands, selectedVertexIndex)) return;
      const nextPath = pathEditor.serializePath(commands);
      const edited = actions.editDocument((candidate) => {
        const hold = candidate.regions.find((region) => region.key === selectedHold.key);
        if (hold && !hold.shapeConstraint) hold.displayPath = nextPath;
      }, { status: "Corner rounded. Save when ready." });
      if (!edited) return;
      setVertexSelection(null);
      setVertexMenuState(null);
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [actions, canRoundSelectedVertex, document, pathEditor, reportInvalidPath, selectedHold, selectedVertexIndex, vertexMenuState]);

  const makeSelectedSegmentBendable = useCallback((): void => {
    const afterIndex = vertexMenuState?.segmentAfterIndex;
    if (!canMakeSelectedSegmentBendable || !document || !selectedHold
      || vertexMenuState?.holdKey !== selectedHold.key || afterIndex === null || afterIndex === undefined) return;
    try {
      const commands = pathEditor.parsePath(selectedHold.displayPath);
      if (!pathEditor.makeSegmentBendable(commands, afterIndex)) return;
      const nextPath = pathEditor.serializePath(commands);
      const edited = actions.editDocument((candidate) => {
        const hold = candidate.regions.find((region) => region.key === selectedHold.key);
        if (hold && !hold.shapeConstraint) hold.displayPath = nextPath;
      }, { status: "Line converted to a bendable curve. Save when ready." });
      if (!edited) return;
      setVertexSelection(null);
      setVertexMenuState(null);
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [
    actions,
    canMakeSelectedSegmentBendable,
    document,
    pathEditor,
    reportInvalidPath,
    selectedHold,
    vertexMenuState?.segmentAfterIndex,
  ]);

  const dismissVertexMenu = useCallback((restoreFocus = false): void => {
    setVertexMenuState((current) => {
      if (!current) return current;
      if (restoreFocus && (current.invoker instanceof HTMLElement || current.invoker instanceof SVGElement)) {
        current.invoker.focus();
      }
      return null;
    });
  }, []);

  const rotateHold = useCallback((degrees: number): void => {
    if (busy || !document || !selectedHold) return;
    const holds = selectedPhysicalHolds(document, selectedKeys);
    actions.editDocument((candidate) => {
      for (const hold of holds) {
        const siblingKeys = new Set(hold.map((region) => region.key));
        const pivot = holdCentroid(hold, pathEditor);
        for (const region of candidate.regions) {
          if (!siblingKeys.has(region.key)) continue;
          const commands = pathEditor.parsePath(region.displayPath);
          pathEditor.rotatePath(commands, ((degrees % 360) * Math.PI) / 180, pivot);
          region.displayPath = pathEditor.serializePath(commands);
          if (region.shapeConstraint) {
            region.shapeConstraint = {
              ...region.shapeConstraint,
              rotationDegrees: normalizedConstraintRotation(region.shapeConstraint.rotationDegrees + degrees),
            };
          }
        }
      }
    }, {
      status: "Hold rotated. Save when ready.",
      failureStatus: "Rotation reverted — contour is invalid.",
    });
  }, [actions, busy, document, pathEditor, selectedHold, selectedKeys]);

  const addHold = useCallback((): void => {
    if (busy || !document) return;
    const { width, height } = document.canvas;
    const size = Math.max(20, Math.min(60, width * 0.06, height * 0.06));
    const centerX = width / 2;
    const centerY = height / 2;
    const holdId = nextHoldId(document);
    const key = `${holdId}-piece-0`;
    actions.editDocument((candidate) => {
      candidate.regions.push({
        id: nextRegionId(candidate),
        key,
        type: "edge",
        displayPath: `M ${centerX - size} ${centerY - size} L ${centerX + size} ${centerY - size} L ${centerX + size} ${centerY + size} L ${centerX - size} ${centerY + size} Z`,
        metadata: { holdID: holdId, pieceIndex: 0 },
      });
    }, {
      selectedKey: key,
      selectedKeys: [key],
      status: "Hold added. Drag it into place and save when ready.",
      failureMessage: "Could not add hold.",
    });
  }, [actions, busy, document]);

  const deleteHold = useCallback((): void => {
    if (busy || !document || !selectedHold || !dialogs.confirm(`Delete hold "${selectedHold.key}"?`)) return;
    const siblingKeys = new Set(selectedPhysicalHolds(document, selectedKeys).flatMap((hold) => hold.map((region) => region.key)));
    actions.editDocument((candidate) => {
      candidate.regions = candidate.regions.filter((region) => !siblingKeys.has(region.key));
    }, {
      selectedKey: null,
      selectedKeys: [],
      status: "Hold deleted. Save when ready.",
      failureMessage: "Document is invalid after deletion.",
    });
  }, [actions, busy, dialogs, document, selectedHold, selectedKeys]);

  const changeHoldType = useCallback((type: string): void => {
    if (busy || !document || !selectedHold) return;
    const siblingKeys = new Set(selectedPhysicalHolds(document, selectedKeys).flatMap((hold) => hold.map((region) => region.key)));
    actions.editDocument((candidate) => {
      for (const region of candidate.regions) {
        if (siblingKeys.has(region.key)) region.type = type;
      }
    }, {
      status: "Hold recategorized. Save when ready.",
      failureMessage: "Hold type is invalid.",
    });
  }, [actions, busy, document, selectedHold, selectedKeys]);

  const changeOutlineShape = useCallback((shape: string): void => {
    if (busy || !document || !selectedHold || (shape !== "custom" && !isShapeConstraintShape(shape))) return;
    const label = shape === "roundedRectangle" ? "rounded rectangle" : shape;
    const siblingKeys = new Set(selectedPhysicalHolds(document, selectedKeys).flatMap((hold) => hold.map((region) => region.key)));
    actions.editDocument((candidate) => {
      for (const hold of candidate.regions) {
        if (!siblingKeys.has(hold.key)) continue;
        if (shape === "custom") {
          delete hold.shapeConstraint;
        } else {
          hold.displayPath = pathEditor.createOutlineShapePath(hold.displayPath, outlinePreset(shape));
          hold.shapeConstraint = { shape, rotationDegrees: 0 };
        }
      }
    }, {
      status: shape === "custom"
        ? "Outline unlocked for custom editing. Save when ready."
        : `Outline changed to ${label}. Save when ready.`,
      failureStatus: "Outline change reverted — contour is invalid.",
    });
  }, [actions, busy, document, pathEditor, selectedHold, selectedKeys]);

  const applyRotation = useCallback((): void => {
    if (busy) return;
    const degrees = normalizedRotationDegrees(rotationDegrees);
    if (degrees === null) {
      if (document) actions.replaceDocument(document, {
        dirty,
        validation: "Enter a finite, non-zero rotation in degrees.",
        status: "Enter a finite, non-zero rotation in degrees.",
      });
      return;
    }
    rotateHold(degrees);
  }, [actions, busy, dirty, document, rotateHold, rotationDegrees]);

  const restoreDrag = useCallback((status: string, validation = ""): void => {
    const drag = dragRef.current;
    const current = previewDocumentRef.current ?? document;
    if (!current) return;
    const restored = cloneEditorDocument(current);
    if (drag.type === "rotation") {
      for (const original of drag.originalPaths ?? []) {
        const region = restored.regions.find((candidate) => candidate.key === original.key);
        if (region) {
          region.displayPath = original.path;
          if (original.shapeConstraint) region.shapeConstraint = { ...original.shapeConstraint };
          else delete region.shapeConstraint;
        }
      }
    } else {
      const region = restored.regions.find((candidate) => candidate.key === drag.holdKey);
      if (region && drag.originalPath !== null) {
        region.displayPath = drag.originalPath;
        if (drag.originalConstraint) region.shapeConstraint = { ...drag.originalConstraint };
        else delete region.shapeConstraint;
      }
    }
    previewDocumentRef.current = restored;
    actions.replaceDocument(restored, { dirty: drag.originalDirty, validation, status });
  }, [actions, document]);

  const releasePointer = useCallback((svg: SVGSVGElement): void => {
    const pointerId = dragRef.current.pointerId;
    dragRef.current.pointerId = null;
    if (pointerId === null) return;
    try {
      svg.releasePointerCapture?.(pointerId);
    } catch {
      // Pointer capture can already be gone when the browser reports cancellation.
    }
    dragSvgRef.current = null;
  }, []);

  const cancelActiveEdit = useCallback((): boolean => {
    const drag = dragRef.current;
    if (!drag.active) return false;
    restoreDrag("Edit cancelled because another operation started.");
    drag.active = false;
    const svg = dragSvgRef.current;
    if (svg) releasePointer(svg);
    else drag.pointerId = null;
    return true;
  }, [releasePointer, restoreDrag]);

  useEffect(() => {
    if (busy) cancelActiveEdit();
  }, [busy, cancelActiveEdit]);

  useEffect(() => {
    if (!vertexSelection || selectionIsCurrent) return;
    setVertexSelection(null);
    setVertexMenuState(null);
  }, [selectionIsCurrent, vertexSelection]);

  useEffect(() => {
    if (!vertexMenuState || menuIsCurrent) return;
    setVertexMenuState(null);
  }, [menuIsCurrent, vertexMenuState]);

  useEffect(() => {
    if (!vertexMenu) return undefined;
    const closeOnOutsidePointerDown = (event: PointerEvent): void => {
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest(".path-editor-vertex-menu")) return;
      dismissVertexMenu();
    };
    window.document.addEventListener("pointerdown", closeOnOutsidePointerDown);
    return () => window.document.removeEventListener("pointerdown", closeOnOutsidePointerDown);
  }, [dismissVertexMenu, vertexMenu]);

  useLayoutEffect(() => {
    const drag = dragRef.current;
    if (!drag.active) {
      previewDocumentRef.current = document;
      pendingPreviewRef.current = null;
      return;
    }
    if (document === pendingPreviewRef.current) {
      previewDocumentRef.current = document;
      pendingPreviewRef.current = null;
      return;
    }
    if (document === previewDocumentRef.current) return;
    const svg = dragSvgRef.current;
    drag.active = false;
    if (svg) releasePointer(svg);
    else drag.pointerId = null;
    dragRef.current = { ...EMPTY_DRAG };
    dragSvgRef.current = null;
    previewDocumentRef.current = document;
    pendingPreviewRef.current = null;
  }, [document, releasePointer]);

  const onPointerDown = useCallback((event: ReactPointerEvent<SVGSVGElement>): void => {
    const drag = dragRef.current;
    if (busy || drag.active || !document || !selectedHold) return;
    const target = targetElement(event);
    if (!target) return;
    if (event.button !== 0) return;
    if (target.classList.contains("path-editor-vertex") && !selectedHold.shapeConstraint) {
      const index = Number(target.getAttribute("data-index"));
      selectVertex(index);
    }
    const point = svgPoint(event.currentTarget, event);
    let next: DragState | null = null;
    if (target.classList.contains("path-editor-rotation-handle")) {
      const siblings = holdSiblings(document, selectedHold);
      const pivot = holdCentroid(siblings, pathEditor);
      next = {
        ...EMPTY_DRAG,
        active: true,
        type: "rotation",
        holdKey: selectedHold.key,
        originalPaths: siblings.map((region) => ({
          key: region.key,
          path: region.displayPath,
          ...(region.shapeConstraint ? { shapeConstraint: { ...region.shapeConstraint } } : {}),
        })),
        originalDirty: dirty,
        pivot,
        lastAngle: Math.atan2(point.y - pivot.y, point.x - pivot.x),
        pointerId: event.pointerId,
      };
    } else if (target.classList.contains("path-editor-resize-handle") && selectedHold.shapeConstraint) {
      const resizeHandle = target.getAttribute("data-handle");
      if (!isConstrainedHandle(resizeHandle)) return;
      next = {
        ...EMPTY_DRAG,
        active: true,
        type: "constrained-resize",
        holdKey: selectedHold.key,
        originalPath: selectedHold.displayPath,
        originalConstraint: { ...selectedHold.shapeConstraint },
        resizeHandle,
        originalDirty: dirty,
        pointerId: event.pointerId,
      };
    } else if (target.classList.contains("path-editor-vertex")
      || target.classList.contains("path-editor-control")
      || (target.classList.contains("region-shape") && target.getAttribute("data-hold-key") === selectedHold.key)) {
      let commands: PathCommand[];
      try {
        commands = pathEditor.parsePath(selectedHold.displayPath);
      } catch (error: unknown) {
        reportInvalidPath(error);
        return;
      }
      next = {
        ...EMPTY_DRAG,
        active: true,
        type: target.classList.contains("path-editor-vertex")
          ? "vertex"
          : target.classList.contains("path-editor-control") ? "control" : "path",
        holdKey: selectedHold.key,
        commandIndex: Number(target.getAttribute("data-index") ?? -1),
        controlIndex: Number(target.getAttribute("data-control") ?? -1),
        startX: point.x,
        startY: point.y,
        commands,
        originalPath: selectedHold.displayPath,
        originalConstraint: cloneConstraint(selectedHold.shapeConstraint) ?? null,
        originalDirty: dirty,
        pointerId: event.pointerId,
        pathCenter: target.classList.contains("region-shape")
          ? holdCentroid([selectedHold], pathEditor)
          : null,
      };
    }
    if (!next) return;
    next.originalDocument = cloneEditorDocument(document);
    event.preventDefault();
    dragRef.current = next;
    previewDocumentRef.current = document;
    pendingPreviewRef.current = null;
    dragSvgRef.current = event.currentTarget;
    try {
      event.currentTarget.setPointerCapture?.(event.pointerId);
    } catch {
      // Tests and older browsers may not implement pointer capture.
    }
  }, [busy, dirty, document, pathEditor, reportInvalidPath, selectVertex, selectedHold]);

  const onPointerMove = useCallback((event: ReactPointerEvent<SVGSVGElement>): void => {
    const drag = dragRef.current;
    if (!drag.active || event.pointerId !== drag.pointerId || !document) return;
    event.preventDefault();
    const point = svgPoint(event.currentTarget, event);
    const preview = previewDocumentRef.current ?? document;
    const candidate = cloneEditorDocument(preview);
    const hold = candidate.regions.find((region) => region.key === drag.holdKey);
    if (!hold) {
      restoreDrag("Edit cancelled because the selected hold is no longer available.");
      drag.active = false;
      releasePointer(event.currentTarget);
      return;
    }
    if (drag.type === "rotation" && drag.pivot && drag.originalPaths) {
      const angle = Math.atan2(point.y - drag.pivot.y, point.x - drag.pivot.x);
      let delta = angle - drag.lastAngle;
      if (delta > Math.PI) delta -= 2 * Math.PI;
      if (delta < -Math.PI) delta += 2 * Math.PI;
      drag.lastAngle = angle;
      drag.totalAngle += delta;
      for (const original of drag.originalPaths) {
        const region = candidate.regions.find((value) => value.key === original.key);
        if (!region) continue;
        const commands = pathEditor.parsePath(original.path);
        pathEditor.rotatePath(commands, drag.totalAngle, drag.pivot);
        region.displayPath = pathEditor.serializePath(commands);
        if (original.shapeConstraint) {
          region.shapeConstraint = {
            ...original.shapeConstraint,
            rotationDegrees: normalizedConstraintRotation(
              original.shapeConstraint.rotationDegrees + drag.totalAngle * 180 / Math.PI,
            ),
          };
        }
      }
    } else if (drag.type === "constrained-resize"
      && drag.originalPath
      && drag.originalConstraint
      && drag.resizeHandle) {
      try {
        const resized = pathEditor.resizeConstrainedOutline(
          drag.originalPath,
          drag.originalConstraint,
          drag.resizeHandle,
          point,
        );
        hold.displayPath = resized.displayPath;
        hold.shapeConstraint = resized.shapeConstraint;
      } catch (error: unknown) {
        restoreDrag(
          "Edit reverted — contour is invalid.",
          errorMessage(error, "Contour is invalid."),
        );
        return;
      }
    } else if (drag.commands) {
      const commands = cloneCommands(drag.commands);
      let deltaX = point.x - drag.startX;
      let deltaY = point.y - drag.startY;
      if (drag.type === "vertex") {
        pathEditor.moveVertex(commands, drag.commandIndex, deltaX, deltaY);
      } else if (drag.type === "control") {
        const control = commands[drag.commandIndex]?.controls[drag.controlIndex];
        if (control) {
          control.x += deltaX;
          control.y += deltaY;
        }
      } else if (drag.type === "path") {
        if (!event.altKey && drag.pathCenter) {
          const snappedX = nearbyGuideCoordinate(verticalGuideXs, drag.pathCenter.x + deltaX);
          const snappedY = nearbyGuideCoordinate(horizontalGuideYs, drag.pathCenter.y + deltaY);
          if (snappedX !== null) deltaX += snappedX - (drag.pathCenter.x + deltaX);
          if (snappedY !== null) deltaY += snappedY - (drag.pathCenter.y + deltaY);
        }
        translateCommands(commands, deltaX, deltaY);
      }
      hold.displayPath = pathEditor.serializePath(commands);
    }
    drag.changed = !dragMatchesOriginal(drag, candidate);
    if (draggedRegionsMatch(drag, preview, candidate)) return;
    previewDocumentRef.current = candidate;
    pendingPreviewRef.current = actions.replaceDocument(candidate, {
      dirty: drag.originalDirty || drag.changed,
    });
  }, [actions, document, horizontalGuideYs, pathEditor, releasePointer, restoreDrag, verticalGuideXs]);

  const completeDrag = useCallback((event: ReactPointerEvent<SVGSVGElement>): void => {
    const drag = dragRef.current;
    if (!drag.active || event.pointerId !== drag.pointerId) return;
    drag.active = false;
    releasePointer(event.currentTarget);
    const candidate = previewDocumentRef.current ?? document;
    if (!candidate) return;
    drag.changed = !dragMatchesOriginal(drag, candidate);
    if (!drag.changed) return;
    try {
      if (drag.type === "constrained-resize") {
        const hold = candidate.regions.find((region) => region.key === drag.holdKey);
        if (!hold?.shapeConstraint) throw new Error("Constrained outline is unavailable.");
        const model = pathEditor.constrainedOutlineModel(hold.displayPath, hold.shapeConstraint);
        if (!Object.values(model.handles).every(({ x, y }) => (
          Number.isFinite(x) && Number.isFinite(y)
        ))) {
          throw new Error("Constrained outline coordinates must be finite.");
        }
      }
      validateEditorDocument(candidate);
      actions.replaceDocument(candidate, {
        dirty: true,
        historySnapshot: drag.originalDocument ?? undefined,
        validation: "",
        status: drag.type === "rotation"
          ? "Hold rotated. Save when ready."
          : "Contour updated. Save when ready.",
      });
    } catch (error: unknown) {
      restoreDrag(
        drag.type === "rotation"
          ? "Rotation reverted — contour is invalid."
          : "Edit reverted — contour is invalid.",
        errorMessage(error, "Contour is invalid."),
      );
    }
  }, [actions, document, pathEditor, releasePointer, restoreDrag, validateEditorDocument]);

  const cancelDrag = useCallback((event: ReactPointerEvent<SVGSVGElement>): void => {
    const drag = dragRef.current;
    if (!drag.active || event.pointerId !== drag.pointerId) return;
    restoreDrag(drag.type === "rotation"
      ? "Rotation cancelled. Changes reverted."
      : "Edit cancelled. Changes reverted.");
    drag.active = false;
    releasePointer(event.currentTarget);
  }, [releasePointer, restoreDrag]);

  const onLostPointerCapture = useCallback((event: ReactPointerEvent<SVGSVGElement>): void => {
    const drag = dragRef.current;
    if (!drag.active || event.pointerId !== drag.pointerId) return;
    restoreDrag(drag.type === "rotation"
      ? "Rotation cancelled. Changes reverted."
      : "Edit cancelled. Changes reverted.");
    drag.active = false;
    drag.pointerId = null;
    dragSvgRef.current = null;
  }, [restoreDrag]);

  const onDoubleClick = useCallback((event: ReactMouseEvent<SVGSVGElement>): void => {
    const target = targetElement(event);
    if (busy || !document || !selectedHold || selectedHold.shapeConstraint || !target
      || target.classList.contains("path-editor-vertex")
      || target.classList.contains("path-editor-control")) return;
    const point = svgPoint(event.currentTarget, event);
    let commands: PathCommand[];
    try {
      commands = pathEditor.parsePath(selectedHold.displayPath);
    } catch (error: unknown) {
      reportInvalidPath(error);
      return;
    }
    for (let index = 0; index < commands.length; index += 1) {
      const command = commands[index]!;
      if (command.type === "Z") continue;
      const nextIndex = (index + 1) % commands.length;
      const next = commands[nextIndex]!;
      if (next.type === "Z" && command.type === "M") continue;
      const start = command.points.at(-1)!;
      const segment: PathCommand = next.type === "Z"
        ? { type: "L", points: [{ ...commands[0]!.points[0]! }], controls: [] }
        : next;
      if (closestDistanceOnSegment(start, segment, point) >= 15) continue;
      const insert = segment.type === "L" ? closestPointOnLine(start, segment.points[0]!, point) : point;
      const edited = actions.editDocument((candidate) => {
        const hold = candidate.regions.find((region) => region.key === selectedHold.key);
        if (!hold) return;
        const edited = pathEditor.parsePath(hold.displayPath);
        pathEditor.addVertex(edited, index, insert.x, insert.y);
        hold.displayPath = pathEditor.serializePath(edited);
      }, { status });
      if (edited) {
        setVertexSelection(null);
        setVertexMenuState(null);
      }
      return;
    }
  }, [actions, busy, document, pathEditor, reportInvalidPath, selectedHold, status]);

  const onContextMenu = useCallback((event: ReactMouseEvent<SVGSVGElement>): void => {
    const target = targetElement(event);
    if (busy || !document || !selectedHold || selectedHold.shapeConstraint || !target) return;
    if (target.classList.contains("path-editor-vertex")) {
      const index = Number(target.getAttribute("data-index"));
      if (!Number.isInteger(index) || index < 0) return;
      event.preventDefault();
      selectVertex(index);
      setVertexMenuState({
        document,
        holdKey: selectedHold.key,
        x: event.clientX,
        y: event.clientY,
        kind: "vertex",
        segmentAfterIndex: null,
        invoker: target,
      });
      return;
    }
    if (!target.classList.contains("region-shape") || target.getAttribute("data-hold-key") !== selectedHold.key) return;
    try {
      const commands = pathEditor.parsePath(selectedHold.displayPath);
      const afterIndex = closestStraightSegmentIndex(commands, svgPoint(event.currentTarget, event));
      if (afterIndex === null) return;
      const candidate = cloneCommands(commands);
      if (!pathEditor.makeSegmentBendable(candidate, afterIndex)) return;
      event.preventDefault();
      setVertexSelection(null);
      setVertexMenuState({
        document,
        holdKey: selectedHold.key,
        x: event.clientX,
        y: event.clientY,
        kind: "segment",
        segmentAfterIndex: afterIndex,
        invoker: target,
      });
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [busy, document, pathEditor, reportInvalidPath, selectVertex, selectedHold]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      const target = event.target instanceof Element ? event.target : null;
      const tagName = target?.tagName.toLowerCase();
      if ((target instanceof HTMLElement && target.isContentEditable)
        || target?.getAttribute("contenteditable") === "true"
        || tagName === "input" || tagName === "select" || tagName === "textarea") return;
      if (busy) return;
      const modifier = event.metaKey || event.ctrlKey;
      if (modifier && event.key.toLowerCase() === "z") {
        const cancelled = cancelActiveEdit();
        const changed = event.shiftKey ? actions.redoDocument() : actions.undoDocument();
        if (cancelled || changed) event.preventDefault();
        return;
      }
      if (event.ctrlKey && !event.metaKey && event.key.toLowerCase() === "y") {
        const cancelled = cancelActiveEdit();
        if (cancelled || actions.redoDocument()) event.preventDefault();
        return;
      }
      if (event.key === "Escape" && cancelActiveEdit()) {
        event.preventDefault();
        return;
      }
      if (event.key === "Escape" && vertexMenu) {
        event.preventDefault();
        dismissVertexMenu(true);
        return;
      }
      if ((event.key === "Delete" || event.key === "Backspace") && selectedVertexIndex !== null) {
        if (!canDeleteSelectedVertex) return;
        event.preventDefault();
        deleteSelectedVertex();
        return;
      }
      if (event.key === "[" || event.key === "]") {
        if (!selectedHold) return;
        event.preventDefault();
        rotateHold(event.key === "]" ? (event.shiftKey ? 45 : 15) : (event.shiftKey ? -45 : -15));
        return;
      }
      if (!document || !selectedHold
        || !["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const step = event.shiftKey ? 10 : 1;
      const deltaX = event.key === "ArrowRight" ? step : event.key === "ArrowLeft" ? -step : 0;
      const deltaY = event.key === "ArrowDown" ? step : event.key === "ArrowUp" ? -step : 0;
      actions.editDocument((candidate) => {
        const hold = candidate.regions.find((region) => region.key === selectedHold.key);
        if (!hold) return;
        const commands = pathEditor.parsePath(hold.displayPath);
        translateCommands(commands, deltaX, deltaY);
        hold.displayPath = pathEditor.serializePath(commands);
      }, {
        status: "Hold nudged. Save when ready.",
        failureStatus: "Nudge reverted — contour is invalid.",
      });
    };
    window.document.addEventListener("keydown", onKeyDown);
    return () => window.document.removeEventListener("keydown", onKeyDown);
  }, [
    actions,
    busy,
    cancelActiveEdit,
    canDeleteSelectedVertex,
    deleteSelectedVertex,
    dismissVertexMenu,
    document,
    pathEditor,
    rotateHold,
    selectedHold,
    selectedVertexIndex,
    vertexMenu,
  ]);

  return {
    selectedVertexIndex,
    vertexMenu,
    canDeleteSelectedVertex,
    canRoundSelectedVertex,
    canMakeSelectedSegmentBendable,
    addHold,
    deleteHold,
    selectVertex,
    deleteSelectedVertex,
    roundSelectedVertex,
    makeSelectedSegmentBendable,
    dismissVertexMenu,
    changeHoldType,
    changeOutlineShape,
    rotateHold,
    applyRotation,
    cancelActiveEdit,
    onPointerDown,
    onPointerMove,
    onPointerUp: completeDrag,
    onPointerCancel: cancelDrag,
    onLostPointerCapture,
    onDoubleClick,
    onContextMenu,
  };
}
