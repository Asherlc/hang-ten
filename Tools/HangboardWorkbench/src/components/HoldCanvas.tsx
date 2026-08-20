import React from "react";

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

export interface HoldCanvasProps {
  board: Board | null;
  document: EditorDocument | null;
  selectedKey: string | null;
  busy: boolean;
  onSelectHold(key: string): void;
  pathEditor: PathEditor;
  editor: HoldEditorActions;
}

export function HoldCanvas({
  board,
  document,
  selectedKey,
  busy,
  onSelectHold,
  pathEditor,
  editor,
}: HoldCanvasProps) {
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
  return (
    <div className="editor-views">
      <div className="canvas-viewport" id="canvas-viewport">
        <svg
          id="editor-svg"
          xmlns="http://www.w3.org/2000/svg"
          aria-label="Hangboard hold editor"
          viewBox={document ? `0 0 ${document.canvas.width} ${document.canvas.height}` : undefined}
          width={document?.canvas.width}
          height={document?.canvas.height}
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
                      className="path-editor-vertex"
                      data-index={commandIndex}
                      cx={endpoint.x}
                      cy={endpoint.y}
                      r="6"
                      fill={selectedColor}
                      stroke="#fff7dc"
                      strokeWidth="1.5"
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
        <div className={`empty-state${document ? " hidden" : ""}`} id="empty-state">
          <strong>Select a board</strong>
          <span>Its image and holds load together.</span>
        </div>
      </div>
    </div>
  );
}
