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
import {
  bendEditableSegmentToPoint,
  cloneEditablePath,
  createEditablePath,
  deleteEditableAnchor,
  editablePathAnchor,
  editablePathAnchorIsInflection,
  insertEditableInflectionPoint,
  insertEditableVertex,
  makeEditableSegmentBendable,
  makeEditableSegmentStraight,
  moveEditableAnchor,
  moveEditableControl,
  roundEditableAnchor,
  rotateEditablePath,
  serializeEditablePath,
  snapEditableSegmentHorizontal,
  snapEditableSegmentVertical,
  translateEditablePath,
} from "./editable-path.ts";
import { isConstrainedHandle, isConstrainedShape } from "./shape-constraints.ts";
import type {
  Dialogs,
  Bounds,
  ConstrainedHandle,
  EditorDocument,
  EditablePath,
  HoldRegion,
  MillimeterRange,
  PathCommand,
  PathEditor,
  Point,
  ShapeConstraint,
  ShapeConstraintShape,
  WorkbenchActions,
} from "./types.ts";

interface DragState {
  active: boolean;
  type: "vertex" | "control" | "path" | "bend" | "rotation" | "constrained-resize" | null;
  holdKey: string | null;
  segmentID: string | null;
  anchorID: string | null;
  controlID: string | null;
  startX: number;
  startY: number;
  editablePath: EditablePath | null;
  originalPath: string | null;
  originalPaths: Array<{
    key: string;
    path: string;
    pivot?: Point;
    shapeConstraint?: ShapeConstraint;
    bendableCommandIndexes?: number[];
  }> | null;
  originalConstraint: ShapeConstraint | null;
  originalDocument: EditorDocument | null;
  resizeHandle: ConstrainedHandle | null;
  originalDirty: boolean;
  changed: boolean;
  pivot: Point | null;
  lastAngle: number;
  totalAngle: number;
  pointerId: number | null;
  pathBounds: Bounds | null;
}

interface VertexSelection {
  holdKey: string;
  anchorID: string;
}

interface VertexMenuState {
  document: EditorDocument;
  holdKey: string;
  x: number;
  y: number;
  kind: "vertex" | "segment";
  segmentID: string | null;
  segmentPoint: Point | null;
  invoker: Element;
}

interface EditablePathState {
  document: EditorDocument;
  holdKey: string;
  displayPath: string;
  path: EditablePath;
}

const EMPTY_DRAG: DragState = {
  active: false,
  type: null,
  holdKey: null,
  segmentID: null,
  anchorID: null,
  controlID: null,
  startX: 0,
  startY: 0,
  editablePath: null,
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
  pathBounds: null,
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
  reservedHoldIDs?: readonly string[];
}

export interface HoldEditorActions {
  editablePath: EditablePath | null;
  selectedAnchorID: string | null;
  vertexMenu: { x: number; y: number; kind: "vertex" | "segment" } | null;
  canDeleteSelectedVertex: boolean;
  selectedVertexIsInflection: boolean;
  canRoundSelectedVertex: boolean;
  canAddInflectionPoint: boolean;
  canMakeSelectedSegmentBendable: boolean;
  canMakeSelectedSegmentStraight: boolean;
  canMakeSelectedSegmentHorizontal: boolean;
  canMakeSelectedSegmentVertical: boolean;
  addHold(): void;
  duplicateAndMirrorHold(): void;
  deleteHold(): void;
  selectAnchor(anchorID: string): void;
  deleteSelectedVertex(): void;
  roundSelectedVertex(): void;
  addInflectionPoint(): void;
  makeSelectedSegmentBendable(): void;
  makeSelectedSegmentStraight(): void;
  makeSelectedSegmentHorizontal(): void;
  makeSelectedSegmentVertical(): void;
  dismissVertexMenu(restoreFocus?: boolean): void;
  changeHoldType(type: string): void;
  changeFingerCapacity(capacity: number | undefined): void;
  changeHoldDepthMeasurement(mode: "unset" | "fixed" | "variable"): void;
  changeHoldSizeMillimeters(size: number | undefined): void;
  changeHoldDepthRange(depthRange: MillimeterRange | undefined): void;
  changeHandCapacity(capacity: number | undefined): void;
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

function translateCommands(commands: PathCommand[], deltaX: number, deltaY: number): void {
  for (const command of commands) {
    if (command.type === "Z") continue;
    for (const point of [...command.points, ...command.controls]) {
      point.x += deltaX;
      point.y += deltaY;
    }
  }
}

function writeBendableCommandIndexes(region: HoldRegion, commands: readonly PathCommand[]): void {
  const bendableCommandIndexes = commands.flatMap((command, index) => (
    command.type === "C" && command.bendable === true ? [index] : []
  ));
  if (bendableCommandIndexes.length > 0) region.bendableCommandIndexes = bendableCommandIndexes;
  else delete region.bendableCommandIndexes;
}

function pathCommandsForHold(region: HoldRegion, pathEditor: PathEditor): PathCommand[] {
  const commands = pathEditor.parsePath(region.displayPath);
  for (const index of region.bendableCommandIndexes ?? []) {
    const command = commands[index];
    if (command?.type === "C") command.bendable = true;
  }
  return commands;
}

function nearbyGuideCoordinate(coordinates: readonly number[], value: number): number | null {
  let closest: number | null = null;
  for (const coordinate of coordinates) {
    if (!Number.isFinite(coordinate) || Math.abs(coordinate - value) > GUIDE_SNAP_TOLERANCE) continue;
    if (closest === null || Math.abs(coordinate - value) < Math.abs(closest - value)) closest = coordinate;
  }
  return closest;
}

function nearbyGuideEdgeOffset(
  coordinates: readonly number[],
  minimum: number,
  maximum: number,
  delta: number,
): number {
  let closestOffset: number | null = null;
  for (const edge of [minimum, maximum]) {
    const coordinate = nearbyGuideCoordinate(coordinates, edge + delta);
    if (coordinate === null) continue;
    const offset = coordinate - (edge + delta);
    if (closestOffset === null || Math.abs(offset) < Math.abs(closestOffset)) closestOffset = offset;
  }
  return closestOffset ?? 0;
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

function canDeleteEditableAnchor(path: EditablePath, anchorID: string): boolean {
  return path.segments.length > 3 && editablePathAnchor(path, anchorID) !== undefined;
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

function mirrorHoldPath(
  source: HoldRegion,
  target: HoldRegion,
  canvasWidth: number,
  pathEditor: PathEditor,
): void {
  const commands = pathCommandsForHold(source, pathEditor);
  for (const command of commands) {
    for (const point of [...command.points, ...command.controls]) point.x = canvasWidth - point.x;
  }
  target.displayPath = pathEditor.serializePath(commands);
  writeBendableCommandIndexes(target, commands);
}

function uniqueRegionKey(document: EditorDocument, baseKey: string): string {
  if (!document.regions.some((region) => region.key === baseKey)) return baseKey;
  let suffix = 2;
  while (document.regions.some((region) => region.key === `${baseKey}-${suffix}`)) suffix += 1;
  return `${baseKey}-${suffix}`;
}

function closestEditableSegmentID(
  path: EditablePath,
  point: Point,
  maximumDistance = 15,
): string | null {
  let closestID: string | null = null;
  let closestDistance = maximumDistance;
  for (let index = 0; index < path.segments.length; index += 1) {
    const candidate = editableSegmentAfter(path, path.segments[index]!.id);
    if (!candidate) continue;
    const { start, command: segment } = candidate;
    const distance = closestDistanceOnSegment(start, segment, point);
    if (distance < closestDistance) {
      closestDistance = distance;
      closestID = path.segments[index]!.id;
    }
  }
  return closestID;
}

function editableSegmentAfter(
  path: EditablePath,
  segmentID: string,
): { start: Point; command: PathCommand } | null {
  const index = path.segments.findIndex((segment) => segment.id === segmentID);
  const start = path.segments[index]?.anchor;
  const next = path.segments[index + 1] ?? (path.closed ? path.segments[0] : undefined);
  if (!start || !next) return null;
  return {
    start,
    command: index + 1 === path.segments.length
      ? { type: "L", points: [{ ...next.anchor }], controls: [] }
      : {
        type: next.type === "M" ? "L" : next.type,
        ...(next.bendable === true ? { bendable: true } : {}),
        points: [{ ...next.anchor }],
        controls: next.controls.map((control) => ({ ...control })),
      },
  };
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
    reservedHoldIDs = [],
  } = options;
  const dragRef = useRef<DragState>({ ...EMPTY_DRAG });
  const previewDocumentRef = useRef<EditorDocument | null>(null);
  const pendingPreviewRef = useRef<EditorDocument | null>(null);
  const dragSvgRef = useRef<SVGSVGElement | null>(null);
  const editablePathRef = useRef<EditablePathState | null>(null);
  const locallyUpdatedEditablePathRef = useRef(false);
  const [vertexSelection, setVertexSelection] = useState<VertexSelection | null>(null);
  const [vertexMenuState, setVertexMenuState] = useState<VertexMenuState | null>(null);
  let editablePath: EditablePath | null = null;
  if (document && selectedHold && !selectedHold.shapeConstraint) {
    const current = editablePathRef.current;
    try {
      const matchesSelection = current?.holdKey === selectedHold.key
        && current.displayPath === selectedHold.displayPath;
      const localUpdate = locallyUpdatedEditablePathRef.current;
      if (matchesSelection && (current.document === document || localUpdate || dragRef.current.active)) {
        editablePath = current.path;
        if (localUpdate) {
          current.document = document;
          locallyUpdatedEditablePathRef.current = false;
        }
      } else {
        editablePath = createEditablePath(
          selectedHold.key,
          selectedHold.displayPath,
          pathEditor,
          selectedHold.bendableCommandIndexes,
        );
        editablePathRef.current = {
          document,
          holdKey: selectedHold.key,
          displayPath: selectedHold.displayPath,
          path: editablePath,
        };
        locallyUpdatedEditablePathRef.current = false;
      }
    } catch {
      editablePathRef.current = null;
      locallyUpdatedEditablePathRef.current = false;
    }
  } else {
    editablePathRef.current = null;
    locallyUpdatedEditablePathRef.current = false;
  }
  const reportInvalidPath = useCallback((error: unknown): void => {
    actions.editDocument(() => { throw error; }, {
      failureStatus: "Could not edit — selected hold has an invalid path.",
      failureMessage: errorMessage(error, "Selected hold path is invalid."),
    });
  }, [actions]);

  let selectionIsCurrent = false;
  let canDeleteSelectedVertex = false;
  let selectedVertexIsInflection = false;
  let canRoundSelectedVertex = false;
  let canAddInflectionPoint = false;
  let canMakeSelectedSegmentBendable = false;
  let canMakeSelectedSegmentStraight = false;
  let canMakeSelectedSegmentHorizontal = false;
  let canMakeSelectedSegmentVertical = false;
  if (!busy && document && selectedHold && !selectedHold.shapeConstraint && editablePath) {
    if (vertexSelection?.holdKey === selectedHold.key) {
      selectionIsCurrent = editablePathAnchor(editablePath, vertexSelection.anchorID) !== undefined;
      canDeleteSelectedVertex = selectionIsCurrent
        && canDeleteEditableAnchor(editablePath, vertexSelection.anchorID);
      selectedVertexIsInflection = selectionIsCurrent
        && editablePathAnchorIsInflection(editablePath, vertexSelection.anchorID, pathEditor);
    }
    if (selectionIsCurrent && vertexSelection) {
      const candidate = cloneEditablePath(editablePath);
      canRoundSelectedVertex = roundEditableAnchor(candidate, vertexSelection.anchorID, pathEditor);
    }
    if (vertexMenuState?.document === document
      && vertexMenuState.holdKey === selectedHold.key
      && vertexMenuState.segmentID !== null) {
      const { segmentID, segmentPoint } = vertexMenuState;
      const inflectionCandidate = cloneEditablePath(editablePath);
      canAddInflectionPoint = segmentPoint !== null
        && insertEditableInflectionPoint(inflectionCandidate, segmentID, segmentPoint, pathEditor);
      const bendableCandidate = cloneEditablePath(editablePath);
      canMakeSelectedSegmentBendable = makeEditableSegmentBendable(bendableCandidate, segmentID, pathEditor);
      const straightCandidate = cloneEditablePath(editablePath);
      canMakeSelectedSegmentStraight = makeEditableSegmentStraight(straightCandidate, segmentID, pathEditor);
      const horizontalCandidate = cloneEditablePath(editablePath);
      canMakeSelectedSegmentHorizontal = snapEditableSegmentHorizontal(horizontalCandidate, segmentID, pathEditor);
      const verticalCandidate = cloneEditablePath(editablePath);
      canMakeSelectedSegmentVertical = snapEditableSegmentVertical(verticalCandidate, segmentID, pathEditor);
    }
  }
  const selectedAnchorID = selectionIsCurrent ? vertexSelection!.anchorID : null;
  const menuIsCurrent = vertexMenuState?.document === document
    && vertexMenuState.holdKey === selectedHold?.key
    && (selectionIsCurrent || vertexMenuState.segmentID !== null);
  const vertexMenu = menuIsCurrent
    ? { x: vertexMenuState.x, y: vertexMenuState.y, kind: vertexMenuState.kind }
    : null;

  const selectAnchor = useCallback((anchorID: string): void => {
    if (busy || !selectedHold || selectedHold.shapeConstraint || !editablePath) return;
    if (editablePathAnchor(editablePath, anchorID) === undefined) return;
    setVertexSelection({ holdKey: selectedHold.key, anchorID });
    setVertexMenuState(null);
  }, [busy, editablePath, selectedHold]);

  const commitEditablePath = useCallback((path: EditablePath, displayPath: string, nextStatus: string): boolean => {
    if (!document || !selectedHold) return false;
    const edited = actions.editDocument((candidate) => {
      const hold = candidate.regions.find((region) => region.key === selectedHold.key);
      if (hold && !hold.shapeConstraint) {
        hold.displayPath = displayPath;
        const bendableCommandIndexes = path.segments.flatMap((segment, index) => (
          segment.bendable === true ? [index] : []
        ));
        if (bendableCommandIndexes.length > 0) hold.bendableCommandIndexes = bendableCommandIndexes;
        else delete hold.bendableCommandIndexes;
      }
    }, { status: nextStatus });
    if (!edited) return false;
    editablePathRef.current = { document, holdKey: selectedHold.key, displayPath, path };
    locallyUpdatedEditablePathRef.current = true;
    return true;
  }, [actions, document, selectedHold]);

  const deleteSelectedVertex = useCallback((): void => {
    if (!canDeleteSelectedVertex || !editablePath || selectedAnchorID === null) return;
    try {
      const candidate = cloneEditablePath(editablePath);
      if (!deleteEditableAnchor(candidate, selectedAnchorID, pathEditor)) return;
      const nextPath = serializeEditablePath(candidate, pathEditor);
      if (!commitEditablePath(candidate, nextPath, status)) return;
      setVertexSelection(null);
      setVertexMenuState(null);
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [
    canDeleteSelectedVertex,
    commitEditablePath,
    editablePath,
    pathEditor,
    reportInvalidPath,
    selectedAnchorID,
    status,
  ]);

  const roundSelectedVertex = useCallback((): void => {
    if (!canRoundSelectedVertex || !editablePath || selectedAnchorID === null || !selectedHold
      || vertexMenuState?.holdKey !== selectedHold.key || vertexMenuState.segmentID !== null) return;
    try {
      const candidate = cloneEditablePath(editablePath);
      if (!roundEditableAnchor(candidate, selectedAnchorID, pathEditor)) return;
      if (!commitEditablePath(candidate, serializeEditablePath(candidate, pathEditor), "Corner rounded. Save when ready.")) return;
      setVertexSelection(null);
      setVertexMenuState(null);
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [canRoundSelectedVertex, commitEditablePath, editablePath, pathEditor, reportInvalidPath, selectedAnchorID, selectedHold, vertexMenuState]);

  const addInflectionPoint = useCallback((): void => {
    const segmentID = vertexMenuState?.segmentID;
    const point = vertexMenuState?.segmentPoint;
    if (!canAddInflectionPoint || !editablePath || !selectedHold || !point
      || vertexMenuState?.holdKey !== selectedHold.key || segmentID === null || segmentID === undefined) return;
    try {
      const candidate = cloneEditablePath(editablePath);
      if (!insertEditableInflectionPoint(candidate, segmentID, point, pathEditor)) return;
      if (!commitEditablePath(candidate, serializeEditablePath(candidate, pathEditor), "Inflection point added. Save when ready.")) return;
      setVertexSelection(null);
      setVertexMenuState(null);
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [
    canAddInflectionPoint,
    commitEditablePath,
    editablePath,
    pathEditor,
    reportInvalidPath,
    selectedHold,
    vertexMenuState?.segmentID,
    vertexMenuState?.segmentPoint,
  ]);

  const makeSelectedSegmentBendable = useCallback((): void => {
    const segmentID = vertexMenuState?.segmentID;
    if (!canMakeSelectedSegmentBendable || !editablePath || !selectedHold
      || vertexMenuState?.holdKey !== selectedHold.key || segmentID === null || segmentID === undefined) return;
    try {
      const candidate = cloneEditablePath(editablePath);
      if (!makeEditableSegmentBendable(candidate, segmentID, pathEditor)) return;
      if (!commitEditablePath(candidate, serializeEditablePath(candidate, pathEditor), "Line converted to a bendable curve. Save when ready.")) return;
      setVertexSelection(null);
      setVertexMenuState(null);
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [
    canMakeSelectedSegmentBendable,
    commitEditablePath,
    editablePath,
    pathEditor,
    reportInvalidPath,
    selectedHold,
    vertexMenuState?.segmentID,
  ]);

  const makeSelectedSegmentStraight = useCallback((): void => {
    const segmentID = vertexMenuState?.segmentID;
    if (!canMakeSelectedSegmentStraight || !editablePath || !selectedHold
      || vertexMenuState?.holdKey !== selectedHold.key || segmentID === null || segmentID === undefined) return;
    try {
      const candidate = cloneEditablePath(editablePath);
      if (!makeEditableSegmentStraight(candidate, segmentID, pathEditor)) return;
      if (!commitEditablePath(candidate, serializeEditablePath(candidate, pathEditor), "Curve made straight. Save when ready.")) return;
      setVertexSelection(null);
      setVertexMenuState(null);
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [
    canMakeSelectedSegmentStraight,
    commitEditablePath,
    editablePath,
    pathEditor,
    reportInvalidPath,
    selectedHold,
    vertexMenuState?.segmentID,
  ]);

  const snapSelectedSegment = useCallback((axis: "horizontal" | "vertical"): void => {
    const segmentID = vertexMenuState?.segmentID;
    const canSnap = axis === "horizontal"
      ? canMakeSelectedSegmentHorizontal
      : canMakeSelectedSegmentVertical;
    if (!canSnap || !editablePath || !selectedHold
      || vertexMenuState?.holdKey !== selectedHold.key || segmentID === null || segmentID === undefined) return;
    try {
      const candidate = cloneEditablePath(editablePath);
      const snapped = axis === "horizontal"
        ? snapEditableSegmentHorizontal(candidate, segmentID, pathEditor)
        : snapEditableSegmentVertical(candidate, segmentID, pathEditor);
      if (!snapped) return;
      if (!commitEditablePath(candidate, serializeEditablePath(candidate, pathEditor), `Line made ${axis}. Save when ready.`)) return;
      setVertexSelection(null);
      setVertexMenuState(null);
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [
    canMakeSelectedSegmentHorizontal,
    canMakeSelectedSegmentVertical,
    commitEditablePath,
    editablePath,
    pathEditor,
    reportInvalidPath,
    selectedHold,
    vertexMenuState?.segmentID,
  ]);

  const makeSelectedSegmentHorizontal = useCallback((): void => {
    snapSelectedSegment("horizontal");
  }, [snapSelectedSegment]);

  const makeSelectedSegmentVertical = useCallback((): void => {
    snapSelectedSegment("vertical");
  }, [snapSelectedSegment]);

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
    const angleRadians = ((degrees % 360) * Math.PI) / 180;
    const selectedPhysicalHold = holds.find((hold) => (
      hold.some((region) => region.key === selectedHold.key)
    ));
    const rotatedEditablePath = editablePath && selectedPhysicalHold
      ? cloneEditablePath(editablePath)
      : null;
    if (rotatedEditablePath && selectedPhysicalHold) {
      rotateEditablePath(
        rotatedEditablePath,
        angleRadians,
        holdCentroid(selectedPhysicalHold, pathEditor),
        pathEditor,
      );
    }
    const rotatedDisplayPath = rotatedEditablePath
      ? serializeEditablePath(rotatedEditablePath, pathEditor)
      : null;
    const edited = actions.editDocument((candidate) => {
      for (const hold of holds) {
        const siblingKeys = new Set(hold.map((region) => region.key));
        const pivot = holdCentroid(hold, pathEditor);
        for (const region of candidate.regions) {
          if (!siblingKeys.has(region.key)) continue;
          if (region.key === selectedHold.key && rotatedDisplayPath !== null) {
            region.displayPath = rotatedDisplayPath;
          } else {
            const commands = pathEditor.parsePath(region.displayPath);
            pathEditor.rotatePath(commands, angleRadians, pivot);
            region.displayPath = pathEditor.serializePath(commands);
          }
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
    if (edited && rotatedEditablePath && rotatedDisplayPath !== null) {
      editablePathRef.current = {
        document,
        holdKey: selectedHold.key,
        displayPath: rotatedDisplayPath,
        path: rotatedEditablePath,
      };
      locallyUpdatedEditablePathRef.current = true;
    }
  }, [actions, busy, document, editablePath, pathEditor, selectedHold, selectedKeys]);

  const addHold = useCallback((): void => {
    if (busy || !document) return;
    const { width, height } = document.canvas;
    const size = Math.max(20, Math.min(60, width * 0.06, height * 0.06));
    const centerX = width / 2;
    const centerY = height / 2;
    const holdId = nextHoldId(document, reservedHoldIDs);
    const key = `${holdId}-piece-0`;
    actions.editDocument((candidate) => {
      candidate.regions.push({
        id: nextRegionId(candidate),
        key,
        type: "edge",
        displayPath: `M ${centerX - size} ${centerY - size} L ${centerX + size} ${centerY - size} L ${centerX + size} ${centerY + size} L ${centerX - size} ${centerY + size} Z`,
        metadata: {
          holdID: holdId,
          pieceIndex: 0,
          ...(document.presentationID ? { presentationID: document.presentationID } : {}),
        },
      });
    }, {
      selectedKey: key,
      selectedKeys: [key],
      status: "Hold added. Drag it into place and save when ready.",
      failureMessage: "Could not add hold.",
    });
  }, [actions, busy, document, reservedHoldIDs]);

  const duplicateAndMirrorHold = useCallback((): void => {
    if (busy || !document || !selectedHold) return;
    const holds = selectedPhysicalHolds(document, selectedKeys);
    const planningDocument = cloneEditorDocument(document);
    const duplicates: Array<{ source: HoldRegion; id: number; key: string; holdId: string; pieceIndex: number }> = [];
    const duplicateKeyBySourceKey = new Map<string, string>();
    for (const hold of holds) {
      const holdId = nextHoldId(planningDocument);
      for (let index = 0; index < hold.length; index += 1) {
        const source = hold[index]!;
        const pieceIndex = source.metadata?.pieceIndex ?? index;
        const key = uniqueRegionKey(planningDocument, `${holdId}-piece-${pieceIndex}`);
        const id = nextRegionId(planningDocument);
        planningDocument.regions.push({
          ...source,
          id,
          key,
          metadata: {
            holdID: holdId,
            pieceIndex,
            ...(document.presentationID ? { presentationID: document.presentationID } : {}),
          },
        });
        duplicates.push({ source, id, key, holdId, pieceIndex });
        duplicateKeyBySourceKey.set(source.key, key);
      }
    }
    const duplicateKeys = duplicates.map((duplicate) => duplicate.key);
    const edited = actions.editDocument((candidate) => {
      for (const duplicate of duplicates) {
        const { source, id, key, holdId, pieceIndex } = duplicate;
        const mirrored: HoldRegion = {
          ...source,
          id,
          key,
          metadata: {
            holdID: holdId,
            pieceIndex,
            ...(document.presentationID ? { presentationID: document.presentationID } : {}),
          },
          ...(source.shapeConstraint ? {
            shapeConstraint: {
              ...source.shapeConstraint,
              rotationDegrees: normalizedConstraintRotation(-source.shapeConstraint.rotationDegrees),
            },
          } : {}),
        };
        mirrorHoldPath(source, mirrored, candidate.canvas.width, pathEditor);
        candidate.regions.push(mirrored);
      }
    }, {
      selectedKey: duplicateKeyBySourceKey.get(selectedHold.key) ?? duplicateKeys[0] ?? null,
      selectedKeys: duplicateKeys,
      status: "Hold duplicated and mirrored. Save when ready.",
      failureStatus: "Duplicate reverted — contour is invalid.",
    });
    if (!edited) return;
    setVertexSelection(null);
    setVertexMenuState(null);
  }, [actions, busy, document, pathEditor, selectedHold, selectedKeys]);

  const deleteHold = useCallback((): void => {
    if (busy || !document || !selectedHold) return;
    const holds = selectedPhysicalHolds(document, selectedKeys);
    const confirmation = holds.length === 1
      ? `Delete hold "${selectedHold.key}"?`
      : `Delete ${holds.length} selected holds and all of their pieces?`;
    if (!dialogs.confirm(confirmation)) return;
    const siblingKeys = new Set(holds.flatMap((hold) => hold.map((region) => region.key)));
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
        if (!siblingKeys.has(region.key)) continue;
        region.type = type;
        if (type !== "sloper") delete region.sloper;
      }
    }, {
      status: "Hold recategorized. Save when ready.",
      failureMessage: "Hold type is invalid.",
    });
  }, [actions, busy, document, selectedHold, selectedKeys]);

  const changeFingerCapacity = useCallback((capacity: number | undefined): void => {
    if (busy || !document || !selectedHold || (capacity !== undefined && (!Number.isInteger(capacity) || capacity < 1 || capacity > 4))) return;
    const siblingKeys = new Set(selectedPhysicalHolds(document, selectedKeys).flatMap((hold) => hold.map((region) => region.key)));
    actions.editDocument((candidate) => {
      for (const region of candidate.regions) {
        if (!siblingKeys.has(region.key)) continue;
        if (capacity === undefined) delete region.fingerCapacity;
        else region.fingerCapacity = capacity;
      }
    }, {
      status: "Finger capacity changed. Save when ready.",
      failureMessage: "Finger capacity is invalid.",
    });
  }, [actions, busy, document, selectedHold, selectedKeys]);

  const changeHoldDepthMeasurement = useCallback((mode: "unset" | "fixed" | "variable"): void => {
    if (busy || !document || !selectedHold) return;
    const siblingKeys = new Set(selectedPhysicalHolds(document, selectedKeys).flatMap((hold) => hold.map((region) => region.key)));
    actions.editDocument((candidate) => {
      for (const region of candidate.regions) {
        if (!siblingKeys.has(region.key)) continue;
        if (mode !== "fixed") delete region.sizeMillimeters;
        if (mode !== "variable") delete region.depthRangeMillimeters;
      }
    }, {
      status: "Depth measurement changed. Save when ready.",
      failureMessage: "Depth measurement is invalid.",
    });
  }, [actions, busy, document, selectedHold, selectedKeys]);

  const changeHoldSizeMillimeters = useCallback((size: number | undefined): void => {
    if (busy || !document || !selectedHold
      || (size !== undefined && (!Number.isFinite(size) || size <= 0))) return;
    const siblingKeys = new Set(selectedPhysicalHolds(document, selectedKeys).flatMap((hold) => hold.map((region) => region.key)));
    actions.editDocument((candidate) => {
      for (const region of candidate.regions) {
        if (!siblingKeys.has(region.key)) continue;
        delete region.depthRangeMillimeters;
        if (size === undefined) delete region.sizeMillimeters;
        else region.sizeMillimeters = size;
      }
    }, {
      status: "Hold depth changed. Save when ready.",
      failureMessage: "Hold depth is invalid.",
    });
  }, [actions, busy, document, selectedHold, selectedKeys]);

  const changeHoldDepthRange = useCallback((depthRange: MillimeterRange | undefined): void => {
    if (busy || !document || !selectedHold
      || (depthRange !== undefined
        && (!Number.isFinite(depthRange.lowerBound)
          || !Number.isFinite(depthRange.upperBound)
          || depthRange.lowerBound <= 0
          || depthRange.upperBound < depthRange.lowerBound))) return;
    const siblingKeys = new Set(selectedPhysicalHolds(document, selectedKeys).flatMap((hold) => hold.map((region) => region.key)));
    actions.editDocument((candidate) => {
      for (const region of candidate.regions) {
        if (!siblingKeys.has(region.key)) continue;
        delete region.sizeMillimeters;
        if (depthRange === undefined) delete region.depthRangeMillimeters;
        else region.depthRangeMillimeters = { ...depthRange };
      }
    }, {
      status: "Depth range changed. Save when ready.",
      failureMessage: "Depth range is invalid.",
    });
  }, [actions, busy, document, selectedHold, selectedKeys]);

  const changeHandCapacity = useCallback((capacity: number | undefined): void => {
    if (busy || !document || !selectedHold || (capacity !== undefined && (!Number.isInteger(capacity) || capacity < 1 || capacity > 2))) return;
    const siblingKeys = new Set(selectedPhysicalHolds(document, selectedKeys).flatMap((hold) => hold.map((region) => region.key)));
    actions.editDocument((candidate) => {
      for (const region of candidate.regions) {
        if (!siblingKeys.has(region.key)) continue;
        if (capacity === undefined) delete region.handCapacity;
        else region.handCapacity = capacity;
      }
    }, {
      status: "Hand capacity changed. Save when ready.",
      failureMessage: "Hand capacity is invalid.",
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
          delete hold.bendableCommandIndexes;
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
          if (original.bendableCommandIndexes) {
            region.bendableCommandIndexes = [...original.bendableCommandIndexes];
          } else {
            delete region.bendableCommandIndexes;
          }
          if (original.shapeConstraint) region.shapeConstraint = { ...original.shapeConstraint };
          else delete region.shapeConstraint;
        }
      }
    } else {
      const region = restored.regions.find((candidate) => candidate.key === drag.holdKey);
      if (region && drag.originalPath !== null) {
        const originalRegion = drag.originalDocument?.regions.find((candidate) => candidate.key === drag.holdKey);
        region.displayPath = drag.originalPath;
        if (originalRegion?.bendableCommandIndexes) {
          region.bendableCommandIndexes = [...originalRegion.bendableCommandIndexes];
        } else {
          delete region.bendableCommandIndexes;
        }
        if (drag.originalConstraint) region.shapeConstraint = { ...drag.originalConstraint };
        else delete region.shapeConstraint;
      }
    }
    editablePathRef.current = null;
    locallyUpdatedEditablePathRef.current = false;
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
    editablePathRef.current = null;
    locallyUpdatedEditablePathRef.current = false;
    previewDocumentRef.current = document;
    pendingPreviewRef.current = null;
  }, [document, releasePointer]);

  const onPointerDown = useCallback((event: ReactPointerEvent<SVGSVGElement>): void => {
    const drag = dragRef.current;
    if (busy || drag.active || !document || !selectedHold) return;
    const target = targetElement(event);
    if (!target) return;
    if (event.button !== 0) return;
    if (!selectedHold.shapeConstraint) {
      try {
        createEditablePath(selectedHold.key, selectedHold.displayPath, pathEditor);
      } catch (error: unknown) {
        reportInvalidPath(error);
        return;
      }
    }
    if (target.classList.contains("path-editor-vertex") && !selectedHold.shapeConstraint) {
      const anchorID = target.getAttribute("data-anchor-id");
      if (!anchorID) return;
      selectAnchor(anchorID);
    }
    const point = svgPoint(event.currentTarget, event);
    let next: DragState | null = null;
    if (target.classList.contains("path-editor-rotation-handle")) {
      const siblings = holdSiblings(document, selectedHold);
      const pivot = holdCentroid(siblings, pathEditor);
      const holds = selectedPhysicalHolds(document, selectedKeys);
      next = {
        ...EMPTY_DRAG,
        active: true,
        type: "rotation",
        holdKey: selectedHold.key,
        originalPaths: holds.flatMap((hold) => {
          const holdPivot = holdCentroid(hold, pathEditor);
          return hold.map((region) => ({
            key: region.key,
            path: region.displayPath,
            pivot: holdPivot,
            ...(region.shapeConstraint ? { shapeConstraint: { ...region.shapeConstraint } } : {}),
            ...(region.bendableCommandIndexes ? {
              bendableCommandIndexes: [...region.bendableCommandIndexes],
            } : {}),
          }));
        }),
        editablePath: editablePath ? cloneEditablePath(editablePath) : null,
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
      let dragEditablePath = editablePath;
      if (!dragEditablePath) {
        try {
          dragEditablePath = createEditablePath(
            selectedHold.key,
            selectedHold.displayPath,
            pathEditor,
            selectedHold.bendableCommandIndexes,
          );
        } catch (error: unknown) {
          reportInvalidPath(error);
          return;
        }
      }
      if (!dragEditablePath) return;
      const anchorID = target.getAttribute("data-anchor-id");
      const controlID = target.getAttribute("data-control-id");
      if (target.classList.contains("path-editor-vertex") && !anchorID) return;
      if (target.classList.contains("path-editor-control") && !controlID) return;
      const originalEditablePath = cloneEditablePath(dragEditablePath);
      const bendableSegmentID = !selectedHold.shapeConstraint && target.classList.contains("region-shape")
        ? closestEditableSegmentID(dragEditablePath, point)
        : null;
      const bendsSegment = bendableSegmentID !== null
        && editableSegmentAfter(dragEditablePath, bendableSegmentID)?.command.bendable === true;
      next = {
        ...EMPTY_DRAG,
        active: true,
        type: target.classList.contains("path-editor-vertex")
          ? "vertex"
          : target.classList.contains("path-editor-control") ? "control" : bendsSegment ? "bend" : "path",
        holdKey: selectedHold.key,
        anchorID,
        controlID,
        ...(bendsSegment ? { segmentID: bendableSegmentID } : {}),
        startX: point.x,
        startY: point.y,
        editablePath: originalEditablePath,
        originalPath: selectedHold.displayPath,
        originalConstraint: cloneConstraint(selectedHold.shapeConstraint) ?? null,
        originalDirty: dirty,
        pointerId: event.pointerId,
        pathBounds: target.classList.contains("region-shape")
          ? pathEditor.pathBounds(pathEditor.parsePath(serializeEditablePath(originalEditablePath, pathEditor)))
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
  }, [busy, dirty, document, editablePath, pathEditor, reportInvalidPath, selectAnchor, selectedHold, selectedKeys]);

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
        if (original.key === drag.holdKey && drag.editablePath && !original.shapeConstraint) {
          const rotatedEditablePath = cloneEditablePath(drag.editablePath);
          rotateEditablePath(
            rotatedEditablePath,
            drag.totalAngle,
            original.pivot ?? drag.pivot,
            pathEditor,
          );
          region.displayPath = serializeEditablePath(rotatedEditablePath, pathEditor);
          writeBendableCommandIndexes(region, rotatedEditablePath.segments.map((segment) => ({
            type: segment.type,
            ...(segment.bendable === true ? { bendable: true } : {}),
            points: [{ x: segment.anchor.x, y: segment.anchor.y }],
            controls: segment.controls.map((control) => ({ x: control.x, y: control.y })),
          })));
          editablePathRef.current = {
            document: candidate,
            holdKey: original.key,
            displayPath: region.displayPath,
            path: rotatedEditablePath,
          };
          locallyUpdatedEditablePathRef.current = true;
        } else {
          const commands = pathEditor.parsePath(original.path);
          for (const index of original.bendableCommandIndexes ?? []) {
            const command = commands[index];
            if (command?.type === "C") command.bendable = true;
          }
          pathEditor.rotatePath(commands, drag.totalAngle, original.pivot ?? drag.pivot);
          region.displayPath = pathEditor.serializePath(commands);
          writeBendableCommandIndexes(region, commands);
        }
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
        delete hold.bendableCommandIndexes;
        hold.shapeConstraint = resized.shapeConstraint;
      } catch (error: unknown) {
        restoreDrag(
          "Edit reverted — contour is invalid.",
          errorMessage(error, "Contour is invalid."),
        );
        return;
      }
    } else if (drag.editablePath) {
      const editable = cloneEditablePath(drag.editablePath);
      let deltaX = point.x - drag.startX;
      let deltaY = point.y - drag.startY;
      if (drag.type === "vertex") {
        if (!drag.anchorID || !moveEditableAnchor(editable, drag.anchorID, deltaX, deltaY)) return;
      } else if (drag.type === "control") {
        if (!drag.controlID || !moveEditableControl(editable, drag.controlID, deltaX, deltaY)) return;
      } else if (drag.type === "bend") {
        if (!drag.segmentID || !bendEditableSegmentToPoint(editable, drag.segmentID, point, pathEditor)) return;
      } else if (drag.type === "path") {
        if (!event.altKey && drag.pathBounds) {
          deltaX += nearbyGuideEdgeOffset(
            verticalGuideXs,
            drag.pathBounds.minX,
            drag.pathBounds.maxX,
            deltaX,
          );
          deltaY += nearbyGuideEdgeOffset(
            horizontalGuideYs,
            drag.pathBounds.minY,
            drag.pathBounds.maxY,
            deltaY,
          );
        }
        translateEditablePath(editable, deltaX, deltaY);
      }
      hold.displayPath = serializeEditablePath(editable, pathEditor);
      writeBendableCommandIndexes(hold, editable.segments.map((segment) => ({
        type: segment.type,
        ...(segment.bendable === true ? { bendable: true } : {}),
        points: [{ x: segment.anchor.x, y: segment.anchor.y }],
        controls: segment.controls.map((control) => ({ x: control.x, y: control.y })),
      })));
      editablePathRef.current = {
        document: candidate,
        holdKey: drag.holdKey ?? selectedHold?.key ?? "",
        displayPath: hold.displayPath,
        path: editable,
      };
      locallyUpdatedEditablePathRef.current = true;
    }
    drag.changed = !dragMatchesOriginal(drag, candidate);
    if (draggedRegionsMatch(drag, preview, candidate)) return;
    previewDocumentRef.current = candidate;
    pendingPreviewRef.current = actions.replaceDocument(candidate, {
      dirty: drag.originalDirty || drag.changed,
    });
  }, [actions, document, horizontalGuideYs, pathEditor, releasePointer, restoreDrag, selectedHold, verticalGuideXs]);

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
      const committedDocument = actions.replaceDocument(candidate, {
        dirty: true,
        historySnapshot: drag.originalDocument ?? undefined,
        validation: "",
        status: drag.type === "rotation"
          ? "Hold rotated. Save when ready."
          : "Contour updated. Save when ready.",
      });
      const currentEditablePath = editablePathRef.current;
      const committedHold = committedDocument.regions.find((region) => region.key === drag.holdKey);
      if (currentEditablePath && committedHold
        && currentEditablePath.holdKey === committedHold.key
        && currentEditablePath.displayPath === committedHold.displayPath) {
        currentEditablePath.document = committedDocument;
        locallyUpdatedEditablePathRef.current = false;
      }
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
    if (busy || !document || !selectedHold || selectedHold.shapeConstraint || !target) return;
    try {
      createEditablePath(selectedHold.key, selectedHold.displayPath, pathEditor);
    } catch (error: unknown) {
      reportInvalidPath(error);
      return;
    }
    if (target.classList.contains("path-editor-vertex")
      || target.classList.contains("path-editor-control") || !editablePath) return;
    const point = svgPoint(event.currentTarget, event);
    const segmentID = closestEditableSegmentID(editablePath, point);
    if (!segmentID) return;
    const segment = editableSegmentAfter(editablePath, segmentID);
    if (!segment) return;
    try {
      const insert = segment.command.type === "L"
        ? closestPointOnLine(segment.start, segment.command.points[0]!, point)
        : point;
      const candidate = cloneEditablePath(editablePath);
      if (!insertEditableVertex(candidate, segmentID, insert, pathEditor)) return;
      if (!commitEditablePath(candidate, serializeEditablePath(candidate, pathEditor), status)) return;
      setVertexSelection(null);
      setVertexMenuState(null);
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [busy, commitEditablePath, document, editablePath, pathEditor, reportInvalidPath, selectedHold, status]);

  const onContextMenu = useCallback((event: ReactMouseEvent<SVGSVGElement>): void => {
    const target = targetElement(event);
    if (busy || !document || !selectedHold || selectedHold.shapeConstraint || !target) return;
    try {
      createEditablePath(selectedHold.key, selectedHold.displayPath, pathEditor);
    } catch (error: unknown) {
      reportInvalidPath(error);
      return;
    }
    if (!editablePath) {
      return;
    }
    if (target.classList.contains("path-editor-vertex")) {
      const anchorID = target.getAttribute("data-anchor-id");
      if (!anchorID) return;
      event.preventDefault();
      selectAnchor(anchorID);
      setVertexMenuState({
        document,
        holdKey: selectedHold.key,
        x: event.clientX,
        y: event.clientY,
        kind: "vertex",
        segmentID: null,
        segmentPoint: null,
        invoker: target,
      });
      return;
    }
    if (!target.classList.contains("region-shape") || target.getAttribute("data-hold-key") !== selectedHold.key) return;
    try {
      const point = svgPoint(event.currentTarget, event);
      const segmentID = closestEditableSegmentID(editablePath, point);
      if (segmentID === null) return;
      const inflectionCandidate = cloneEditablePath(editablePath);
      const bendableCandidate = cloneEditablePath(editablePath);
      const straightCandidate = cloneEditablePath(editablePath);
      const horizontalCandidate = cloneEditablePath(editablePath);
      const verticalCandidate = cloneEditablePath(editablePath);
      if (!insertEditableInflectionPoint(inflectionCandidate, segmentID, point, pathEditor)
        && !makeEditableSegmentBendable(bendableCandidate, segmentID, pathEditor)
        && !makeEditableSegmentStraight(straightCandidate, segmentID, pathEditor)
        && !snapEditableSegmentHorizontal(horizontalCandidate, segmentID, pathEditor)
        && !snapEditableSegmentVertical(verticalCandidate, segmentID, pathEditor)) return;
      event.preventDefault();
      setVertexSelection(null);
      setVertexMenuState({
        document,
        holdKey: selectedHold.key,
        x: event.clientX,
        y: event.clientY,
        kind: "segment",
        segmentID,
        segmentPoint: point,
        invoker: target,
      });
    } catch (error: unknown) {
      reportInvalidPath(error);
    }
  }, [busy, document, editablePath, pathEditor, reportInvalidPath, selectAnchor, selectedHold]);

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
      if ((event.key === "Delete" || event.key === "Backspace") && selectedAnchorID !== null) {
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
      if (editablePath) {
        const next = cloneEditablePath(editablePath);
        translateEditablePath(next, deltaX, deltaY);
        const nextPath = serializeEditablePath(next, pathEditor);
        const edited = actions.editDocument((candidate) => {
          const hold = candidate.regions.find((region) => region.key === selectedHold.key);
          if (hold) {
            hold.displayPath = nextPath;
            writeBendableCommandIndexes(hold, next.segments.map((segment) => ({
              type: segment.type,
              ...(segment.bendable === true ? { bendable: true } : {}),
              points: [{ x: segment.anchor.x, y: segment.anchor.y }],
              controls: segment.controls.map((control) => ({ x: control.x, y: control.y })),
            })));
          }
        }, {
          status: "Hold nudged. Save when ready.",
          failureStatus: "Nudge reverted — contour is invalid.",
        });
        if (edited) {
          editablePathRef.current = { document, holdKey: selectedHold.key, displayPath: nextPath, path: next };
          locallyUpdatedEditablePathRef.current = true;
        }
        return;
      }
      actions.editDocument((candidate) => {
        const hold = candidate.regions.find((region) => region.key === selectedHold.key);
        if (!hold) return;
        const commands = pathCommandsForHold(hold, pathEditor);
        translateCommands(commands, deltaX, deltaY);
        hold.displayPath = pathEditor.serializePath(commands);
        writeBendableCommandIndexes(hold, commands);
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
    editablePath,
    pathEditor,
    rotateHold,
    selectedHold,
    selectedAnchorID,
    vertexMenu,
  ]);

  return {
    editablePath,
    selectedAnchorID,
    vertexMenu,
    canDeleteSelectedVertex,
    selectedVertexIsInflection,
    canRoundSelectedVertex,
    canAddInflectionPoint,
    canMakeSelectedSegmentBendable,
    canMakeSelectedSegmentStraight,
    canMakeSelectedSegmentHorizontal,
    canMakeSelectedSegmentVertical,
    addHold,
    duplicateAndMirrorHold,
    deleteHold,
    selectAnchor,
    deleteSelectedVertex,
    roundSelectedVertex,
    addInflectionPoint,
    makeSelectedSegmentBendable,
    makeSelectedSegmentStraight,
    makeSelectedSegmentHorizontal,
    makeSelectedSegmentVertical,
    dismissVertexMenu,
    changeHoldType,
    changeFingerCapacity,
    changeHoldDepthMeasurement,
    changeHoldSizeMillimeters,
    changeHoldDepthRange,
    changeHandCapacity,
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
