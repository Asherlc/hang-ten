import { useCallback, useEffect, useLayoutEffect, useRef } from "react";
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
  normalizedRotationDegrees,
  svgPoint,
} from "./editor-model.ts";
import type {
  Dialogs,
  EditorDocument,
  HoldRegion,
  PathCommand,
  PathEditor,
  Point,
  WorkbenchActions,
} from "./types.ts";

interface DragState {
  active: boolean;
  type: "vertex" | "control" | "path" | "rotation" | null;
  holdKey: string | null;
  commandIndex: number;
  controlIndex: number;
  startX: number;
  startY: number;
  commands: PathCommand[] | null;
  originalPath: string | null;
  originalPaths: Array<{ key: string; path: string }> | null;
  originalDirty: boolean;
  pivot: Point | null;
  lastAngle: number;
  totalAngle: number;
  pointerId: number | null;
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
  originalDirty: false,
  pivot: null,
  lastAngle: 0,
  totalAngle: 0,
  pointerId: null,
};

export interface UseHoldEditorOptions {
  document: EditorDocument | null;
  selectedHold: HoldRegion | null;
  dirty: boolean;
  status: string;
  rotationDegrees: string;
  actions: WorkbenchActions;
  pathEditor: PathEditor;
  validateEditorDocument(document: unknown): EditorDocument;
  dialogs: Dialogs;
}

export interface HoldEditorActions {
  addHold(): void;
  deleteHold(): void;
  changeHoldType(type: string): void;
  rotateHold(degrees: number): void;
  applyRotation(): void;
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

export function useHoldEditor(options: UseHoldEditorOptions): HoldEditorActions {
  const {
    document,
    selectedHold,
    dirty,
    status,
    rotationDegrees,
    actions,
    pathEditor,
    validateEditorDocument,
    dialogs,
  } = options;
  const dragRef = useRef<DragState>({ ...EMPTY_DRAG });
  const previewDocumentRef = useRef<EditorDocument | null>(null);
  const pendingPreviewRef = useRef<EditorDocument | null>(null);
  const dragSvgRef = useRef<SVGSVGElement | null>(null);

  const rotateHold = useCallback((degrees: number): void => {
    if (!document || !selectedHold) return;
    const siblingKeys = new Set(holdSiblings(document, selectedHold).map((region) => region.key));
    const pivot = holdCentroid(holdSiblings(document, selectedHold), pathEditor);
    actions.editDocument((candidate) => {
      for (const region of candidate.regions) {
        if (!siblingKeys.has(region.key)) continue;
        const commands = pathEditor.parsePath(region.displayPath);
        pathEditor.rotatePath(commands, ((degrees % 360) * Math.PI) / 180, pivot);
        region.displayPath = pathEditor.serializePath(commands);
      }
    }, {
      status: "Hold rotated. Save when ready.",
      failureStatus: "Rotation reverted — contour is invalid.",
    });
  }, [actions, document, pathEditor, selectedHold]);

  const addHold = useCallback((): void => {
    if (!document) return;
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
      status: "Hold added. Drag it into place and save when ready.",
      failureMessage: "Could not add hold.",
    });
  }, [actions, document]);

  const deleteHold = useCallback((): void => {
    if (!document || !selectedHold || !dialogs.confirm(`Delete hold "${selectedHold.key}"?`)) return;
    const siblingKeys = new Set(holdSiblings(document, selectedHold).map((region) => region.key));
    actions.editDocument((candidate) => {
      candidate.regions = candidate.regions.filter((region) => !siblingKeys.has(region.key));
    }, {
      selectedKey: null,
      status: "Hold deleted. Save when ready.",
      failureMessage: "Document is invalid after deletion.",
    });
  }, [actions, dialogs, document, selectedHold]);

  const changeHoldType = useCallback((type: string): void => {
    if (!document || !selectedHold) return;
    const siblingKeys = new Set(holdSiblings(document, selectedHold).map((region) => region.key));
    actions.editDocument((candidate) => {
      for (const region of candidate.regions) {
        if (siblingKeys.has(region.key)) region.type = type;
      }
    }, {
      status: "Hold recategorized. Save when ready.",
      failureMessage: "Hold type is invalid.",
    });
  }, [actions, document, selectedHold]);

  const applyRotation = useCallback((): void => {
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
  }, [actions, dirty, document, rotateHold, rotationDegrees]);

  const restoreDrag = useCallback((status: string, validation = ""): void => {
    const drag = dragRef.current;
    const current = previewDocumentRef.current ?? document;
    if (!current) return;
    const restored = cloneEditorDocument(current);
    if (drag.type === "rotation") {
      for (const original of drag.originalPaths ?? []) {
        const region = restored.regions.find((candidate) => candidate.key === original.key);
        if (region) region.displayPath = original.path;
      }
    } else {
      const region = restored.regions.find((candidate) => candidate.key === drag.holdKey);
      if (region && drag.originalPath !== null) region.displayPath = drag.originalPath;
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
    if (drag.active || !document || !selectedHold) return;
    const target = targetElement(event);
    if (!target) return;
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
        originalPaths: siblings.map((region) => ({ key: region.key, path: region.displayPath })),
        originalDirty: dirty,
        pivot,
        lastAngle: Math.atan2(point.y - pivot.y, point.x - pivot.x),
        pointerId: event.pointerId,
      };
    } else if (target.classList.contains("path-editor-vertex")
      || target.classList.contains("path-editor-control")
      || (target.classList.contains("region-shape") && target.getAttribute("data-hold-key") === selectedHold.key)) {
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
        commands: pathEditor.parsePath(selectedHold.displayPath),
        originalPath: selectedHold.displayPath,
        originalDirty: dirty,
        pointerId: event.pointerId,
      };
    }
    if (!next) return;
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
  }, [dirty, document, pathEditor, selectedHold]);

  const onPointerMove = useCallback((event: ReactPointerEvent<SVGSVGElement>): void => {
    const drag = dragRef.current;
    if (!drag.active || event.pointerId !== drag.pointerId || !document) return;
    event.preventDefault();
    const point = svgPoint(event.currentTarget, event);
    const candidate = cloneEditorDocument(previewDocumentRef.current ?? document);
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
      }
    } else if (drag.commands) {
      const commands = cloneCommands(drag.commands);
      const deltaX = point.x - drag.startX;
      const deltaY = point.y - drag.startY;
      if (drag.type === "vertex") {
        pathEditor.moveVertex(commands, drag.commandIndex, deltaX, deltaY);
      } else if (drag.type === "control") {
        const control = commands[drag.commandIndex]?.controls[drag.controlIndex];
        if (control) {
          control.x += deltaX;
          control.y += deltaY;
        }
      } else if (drag.type === "path") {
        translateCommands(commands, deltaX, deltaY);
      }
      hold.displayPath = pathEditor.serializePath(commands);
    }
    previewDocumentRef.current = candidate;
    pendingPreviewRef.current = actions.replaceDocument(candidate, { dirty: true });
  }, [actions, document, pathEditor, releasePointer, restoreDrag]);

  const completeDrag = useCallback((event: ReactPointerEvent<SVGSVGElement>): void => {
    const drag = dragRef.current;
    if (!drag.active || event.pointerId !== drag.pointerId) return;
    drag.active = false;
    releasePointer(event.currentTarget);
    const candidate = previewDocumentRef.current ?? document;
    if (!candidate) return;
    try {
      validateEditorDocument(candidate);
      actions.replaceDocument(candidate, {
        dirty: true,
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
  }, [actions, document, releasePointer, restoreDrag, validateEditorDocument]);

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
    if (!document || !selectedHold || !target
      || target.classList.contains("path-editor-vertex")
      || target.classList.contains("path-editor-control")) return;
    const point = svgPoint(event.currentTarget, event);
    const commands = pathEditor.parsePath(selectedHold.displayPath);
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
      actions.editDocument((candidate) => {
        const hold = candidate.regions.find((region) => region.key === selectedHold.key);
        if (!hold) return;
        const edited = pathEditor.parsePath(hold.displayPath);
        pathEditor.addVertex(edited, index, insert.x, insert.y);
        hold.displayPath = pathEditor.serializePath(edited);
      }, { status });
      return;
    }
  }, [actions, document, pathEditor, selectedHold, status]);

  const onContextMenu = useCallback((event: ReactMouseEvent<SVGSVGElement>): void => {
    const target = targetElement(event);
    if (!selectedHold || !target?.classList.contains("path-editor-vertex")) return;
    event.preventDefault();
    const index = Number(target.getAttribute("data-index"));
    if (index === 0) return;
    actions.editDocument((candidate) => {
      const hold = candidate.regions.find((region) => region.key === selectedHold.key);
      if (!hold) return;
      const commands = pathEditor.parsePath(hold.displayPath);
      pathEditor.deleteVertex(commands, index);
      hold.displayPath = pathEditor.serializePath(commands);
    }, { status });
  }, [actions, pathEditor, selectedHold, status]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      const target = event.target instanceof Element ? event.target : null;
      const tagName = target?.tagName.toLowerCase();
      if ((target instanceof HTMLElement && target.isContentEditable)
        || target?.getAttribute("contenteditable") === "true"
        || tagName === "input" || tagName === "select" || tagName === "textarea") return;
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
  }, [actions, document, pathEditor, rotateHold, selectedHold]);

  return {
    addHold,
    deleteHold,
    changeHoldType,
    rotateHold,
    applyRotation,
    onPointerDown,
    onPointerMove,
    onPointerUp: completeDrag,
    onPointerCancel: cancelDrag,
    onLostPointerCapture,
    onDoubleClick,
    onContextMenu,
  };
}
