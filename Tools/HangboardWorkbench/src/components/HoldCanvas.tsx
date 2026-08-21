import React, { useEffect, useLayoutEffect, useRef, useState } from "react";

import { holdCentroid, holdSiblings, rotationHandlePosition } from "../editor-model.ts";
import type { HoldEditorActions } from "../useHoldEditor.ts";
import type {
  Board,
  ConstrainedOutlineModel,
  EditorDocument,
  PathCommand,
  PathEditor,
} from "../types.ts";

const TYPE_COLORS: Readonly<Record<string, string>> = {
  jug: "#ff754f",
  sloper: "#32bbc1",
  edge: "#9a6cf2",
  pocket: "#ee4d97",
  pinch: "#f2c94c",
};

interface VertexMenuPosition {
  anchorX: number;
  anchorY: number;
  x: number;
  y: number;
}

function fixedMenuCoordinate(anchor: number, size: number, viewportSize: number): number {
  const flipped = anchor + size > viewportSize ? anchor - size : anchor;
  return Math.max(0, Math.min(flipped, Math.max(0, viewportSize - size)));
}

export interface HoldCanvasProps {
  board: Board | null;
  document: EditorDocument | null;
  selectedKey: string | null;
  busy: boolean;
  onSelectHold(key: string): void;
  pathEditor: PathEditor;
  editor: HoldEditorActions;
  zoomPercent: number;
  onZoomChange(direction: number): void;
}

export function HoldCanvas({
  board,
  document,
  selectedKey,
  busy,
  onSelectHold,
  pathEditor,
  editor,
  zoomPercent,
  onZoomChange,
}: HoldCanvasProps) {
  const vertexMenuRef = useRef<HTMLDivElement>(null);
  const [vertexMenuPosition, setVertexMenuPosition] = useState<VertexMenuPosition | null>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const handleWheel = (event: WheelEvent): void => {
      if (!event.altKey || !document) return;
      const delta = event.deltaY === 0 ? event.deltaX : event.deltaY;
      if (delta === 0) return;
      event.preventDefault();
      onZoomChange(delta < 0 ? 1 : -1);
    };
    viewport.addEventListener("wheel", handleWheel, { passive: false });
    return () => viewport.removeEventListener("wheel", handleWheel);
  }, [document, onZoomChange]);
  const selectedHold = document?.regions.find((region) => region.key === selectedKey) ?? null;
  let selectedCommands: PathCommand[] | null = null;
  if (selectedHold) {
    try {
      selectedCommands = pathEditor.parsePath(selectedHold.displayPath);
    } catch {
      selectedCommands = null;
    }
  }
  const pivot = document && selectedHold && selectedCommands
    ? holdCentroid(holdSiblings(document, selectedHold), pathEditor)
    : null;
  const rotationHandle = document && pivot ? rotationHandlePosition(pivot, document.canvas) : null;
  const selectedColor = selectedHold ? TYPE_COLORS[selectedHold.type ?? ""] ?? "#ff754f" : "#ff754f";
  let constrainedModel: ConstrainedOutlineModel | null = null;
  if (selectedHold?.shapeConstraint) {
    try {
      constrainedModel = pathEditor.constrainedOutlineModel(
        selectedHold.displayPath,
        selectedHold.shapeConstraint,
      );
    } catch {
      constrainedModel = null;
    }
  }
  useLayoutEffect(() => {
    const menu = vertexMenuRef.current;
    if (!editor.vertexMenu || !menu) return;
    const bounds = menu.getBoundingClientRect();
    const nextPosition = {
      anchorX: editor.vertexMenu.x,
      anchorY: editor.vertexMenu.y,
      x: fixedMenuCoordinate(editor.vertexMenu.x, bounds.width, window.innerWidth),
      y: fixedMenuCoordinate(editor.vertexMenu.y, bounds.height, window.innerHeight),
    };
    setVertexMenuPosition((current) => (
      current?.anchorX === nextPosition.anchorX
        && current.anchorY === nextPosition.anchorY
        && current.x === nextPosition.x
        && current.y === nextPosition.y
        ? current
        : nextPosition
    ));
    const firstEnabledItem = [...menu.querySelectorAll<HTMLButtonElement>('[role="menuitem"]')]
      .find((item) => !item.disabled);
    (firstEnabledItem ?? menu).focus();
  }, [
    editor.canDeleteSelectedVertex,
    editor.canMakeSelectedSegmentBendable,
    editor.canRoundSelectedVertex,
    editor.vertexMenu?.x,
    editor.vertexMenu?.y,
  ]);
  const displayedVertexMenuPosition = editor.vertexMenu
    && vertexMenuPosition?.anchorX === editor.vertexMenu.x
    && vertexMenuPosition.anchorY === editor.vertexMenu.y
    ? vertexMenuPosition
    : editor.vertexMenu;
  return (
    <div className="editor-views">
      <div
        className="canvas-viewport"
        id="canvas-viewport"
        ref={viewportRef}
      >
        <svg
          id="editor-svg"
          xmlns="http://www.w3.org/2000/svg"
          aria-label="Hangboard hold editor"
          viewBox={document ? `0 0 ${document.canvas.width} ${document.canvas.height}` : undefined}
          width={document?.canvas.width}
          height={document?.canvas.height}
          style={{
            width: `${zoomPercent}%`,
            height: `${zoomPercent}%`,
            minHeight: `${3.6 * zoomPercent}px`,
          }}
          onPointerDown={editor.onPointerDown}
          onPointerMove={editor.onPointerMove}
          onPointerUp={editor.onPointerUp}
          onPointerCancel={editor.onPointerCancel}
          onLostPointerCapture={editor.onLostPointerCapture}
          onDoubleClick={editor.onDoubleClick}
          onContextMenu={editor.onContextMenu}
        >
          <image
            id="board-image"
            x="0"
            y="0"
            preserveAspectRatio="none"
            href={board?.imageUrl}
            width={document?.canvas.width}
            height={document?.canvas.height}
          />
          <g id="hold-overlay">
            {document?.regions.map((hold) => (
              <path
                key={hold.key}
                className="region-shape"
                data-hold-key={hold.key}
                d={hold.displayPath}
                fill={TYPE_COLORS[hold.type ?? ""] ?? "#ff754f"}
                fillOpacity={hold.key === selectedKey ? "0.58" : "0.3"}
                stroke={hold.key === selectedKey ? "#fff7dc" : TYPE_COLORS[hold.type ?? ""] ?? "#ff754f"}
                strokeWidth={hold.key === selectedKey ? "2.2" : "1.4"}
                role="button"
                tabIndex={0}
                aria-label={`Select hold ${hold.key}`}
                onClick={() => { if (!busy) onSelectHold(hold.key); }}
                onKeyDown={(event) => {
                  if (busy || (event.key !== "Enter" && event.key !== " ")) return;
                  if (event.key === " ") event.preventDefault();
                  onSelectHold(hold.key);
                }}
              />
            ))}
          </g>
          {selectedCommands && pivot && rotationHandle && (
            <g className={`path-editor-overlay${busy ? " busy" : ""}`}>
              <line
                className="path-editor-rotation-connector"
                x1={pivot.x}
                y1={pivot.y}
                x2={rotationHandle.x}
                y2={rotationHandle.y}
                stroke="#fff7dc"
                strokeWidth="1.5"
                strokeDasharray="4 3"
              />
              <circle
                className="path-editor-rotation-handle"
                cx={rotationHandle.x}
                cy={rotationHandle.y}
                r="6"
                fill="#fff7dc"
                stroke={selectedColor}
                strokeWidth="2"
              />
              {constrainedModel ? <>
                <polygon
                  className="path-editor-constrained-box"
                  points={["nw", "ne", "se", "sw"].map((handle) => {
                    const point = constrainedModel.handles[handle as "nw" | "ne" | "se" | "sw"];
                    return `${point.x},${point.y}`;
                  }).join(" ")}
                  fill="none"
                  stroke="#fff7dc"
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                />
                {Object.entries(constrainedModel.handles).map(([handle, point]) => (
                  <circle
                    key={handle}
                    className="path-editor-resize-handle"
                    data-handle={handle}
                    cx={point.x}
                    cy={point.y}
                    r="5"
                    fill={selectedColor}
                    stroke="#fff7dc"
                    strokeWidth="1.5"
                  />
                ))}
              </> : selectedCommands.map((command, commandIndex) => {
                if (command.type === "Z") return null;
                const endpoint = command.points.at(-1);
                if (!endpoint) return null;
                const previous = commandIndex > 0 ? selectedCommands[commandIndex - 1] : null;
                return (
                  <g key={`${selectedHold?.key ?? "selected"}-${commandIndex}`}>
                    <circle
                      className={`path-editor-vertex${editor.selectedVertexIndex === commandIndex ? " selected" : ""}`}
                      data-index={commandIndex}
                      cx={endpoint.x}
                      cy={endpoint.y}
                      r="6"
                      fill={selectedColor}
                      stroke="#fff7dc"
                      strokeWidth="1.5"
                      role="button"
                      tabIndex={busy ? -1 : 0}
                      aria-label={commandIndex === 0 ? "Start vertex" : `Vertex ${commandIndex + 1}`}
                      aria-pressed={editor.selectedVertexIndex === commandIndex}
                      onFocus={() => editor.selectVertex(commandIndex)}
                      onKeyDown={(event) => {
                        if (busy || (event.key !== "Enter" && event.key !== " ")) return;
                        if (event.key === " ") event.preventDefault();
                        editor.selectVertex(commandIndex);
                      }}
                    />
                    {command.controls.map((control, controlIndex) => {
                      const anchor = controlIndex === 0
                        ? previous && previous.type !== "Z" ? previous.points.at(-1) : command.points[0]
                        : command.points[0];
                      return (
                        <g key={`${commandIndex}-${controlIndex}`}>
                          {anchor && <line
                            className="path-editor-line"
                            x1={anchor.x}
                            y1={anchor.y}
                            x2={control.x}
                            y2={control.y}
                            stroke="#888"
                            strokeWidth="1"
                            strokeDasharray="4 2"
                          />}
                          <circle
                            className="path-editor-control"
                            data-index={commandIndex}
                            data-control={controlIndex}
                            cx={control.x}
                            cy={control.y}
                            r="3"
                            fill="#888"
                            stroke="#fff"
                            strokeWidth="1"
                          />
                        </g>
                      );
                    })}
                  </g>
                );
              })}
            </g>
          )}
        </svg>
        {editor.vertexMenu && (
          <div
            ref={vertexMenuRef}
            className="path-editor-vertex-menu"
            role="menu"
            aria-label={editor.vertexMenu.kind === "vertex" ? "Vertex actions" : "Line actions"}
            tabIndex={-1}
            style={{ left: displayedVertexMenuPosition?.x, top: displayedVertexMenuPosition?.y }}
            onContextMenu={(event) => event.preventDefault()}
            onKeyDown={(event) => {
              const items = [...(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="menuitem"]'))]
                .filter((item) => !item.disabled);
              if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
                event.preventDefault();
                event.stopPropagation();
                if (items.length === 0) return;
                if (event.key === "Home") {
                  items[0]?.focus();
                  return;
                }
                if (event.key === "End") {
                  items.at(-1)?.focus();
                  return;
                }
                const currentIndex = items.indexOf(window.document.activeElement as HTMLButtonElement);
                const direction = event.key === "ArrowDown" || event.key === "ArrowRight" ? 1 : -1;
                items[(currentIndex + direction + items.length) % items.length]?.focus();
                return;
              }
              if (event.key !== "Escape") return;
              event.preventDefault();
              event.stopPropagation();
              editor.dismissVertexMenu(true);
            }}
          >
            {editor.selectedVertexIndex !== null && <button
              type="button"
              role="menuitem"
              disabled={!editor.canDeleteSelectedVertex}
              aria-disabled={!editor.canDeleteSelectedVertex}
              onClick={() => editor.deleteSelectedVertex()}
            >Delete</button>}
            {editor.canRoundSelectedVertex && <button
              id="round-corner-action"
              type="button"
              role="menuitem"
              onClick={() => editor.roundSelectedVertex()}
            >Round corner</button>}
            {editor.canMakeSelectedSegmentBendable && <button
              id="make-bendable-action"
              type="button"
              role="menuitem"
              onClick={() => editor.makeSelectedSegmentBendable()}
            >Make bendable</button>}
          </div>
        )}
        <div className={`empty-state${document ? " hidden" : ""}`} id="empty-state">
          <strong>Select a board</strong>
          <span>Its image and holds load together.</span>
        </div>
      </div>
    </div>
  );
}
