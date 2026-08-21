import React from "react";

import type { HoldRegion } from "../types.ts";

const HOLD_TYPES = ["jug", "sloper", "edge", "pocket", "pinch"] as const;
const OUTLINE_SHAPES = [
  ["custom", "Custom"],
  ["oval", "Oval"],
  ["circle", "Circle"],
  ["pill", "Pill"],
  ["roundedRectangle", "Rounded rectangle"],
  ["rectangle", "Rectangle"],
] as const;

export interface HoldInspectorProps {
  hold: HoldRegion | null;
  selectedCount: number;
  busy: boolean;
  rotationDegrees: string;
  onRotationDegreesChange(value: string): void;
  onTypeChange(type: string): void;
  onFingerCapacityChange(capacity: number | undefined): void;
  onOutlineShapeChange(shape: string): void;
  onRotate(direction: -1 | 1, shiftKey: boolean): void;
  onApplyRotation(): void;
  onDuplicateAndMirror(): void;
  onDelete(): void;
  onMobileCollapse(): void;
  className?: string;
}

export function HoldInspector({
  hold,
  selectedCount,
  busy,
  rotationDegrees,
  onRotationDegreesChange,
  onTypeChange,
  onFingerCapacityChange,
  onOutlineShapeChange,
  onRotate,
  onApplyRotation,
  onDuplicateAndMirror,
  onDelete,
  onMobileCollapse,
  className = "",
}: HoldInspectorProps) {
  return (
    <aside className={`panel inspector-panel ${className}`.trim()} aria-labelledby="hold-heading">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Hold</span>
          <h2 id="hold-heading">{hold?.key ?? "No selection"}</h2>
          {selectedCount > 1 && <span id="selected-hold-count">{selectedCount} selected</span>}
        </div>
        <button
          className="tool-button mobile-sheet-collapse"
          id="mobile-collapse-hold-sheet-button"
          type="button"
          aria-label="Collapse hold editor"
          onClick={onMobileCollapse}
        >Collapse</button>
      </div>
      <div className={`inspector-empty${hold ? " hidden" : ""}`} id="hold-empty">Select a hold to edit its closed contour.</div>
      <form className={`inspector-form${hold ? "" : " hidden"}`} id="hold-form">
        <label>Hold key <input id="hold-key" type="text" readOnly value={hold?.key ?? ""} /></label>
        <label>Hold type
          <select id="hold-type-select" disabled={busy} value={hold?.type ?? ""} onChange={(event) => onTypeChange(event.currentTarget.value)}>
            {!hold?.type && <option value="" />}
            {hold?.type && !HOLD_TYPES.includes(hold.type as typeof HOLD_TYPES[number])
              && <option value={hold.type}>{hold.type}</option>}
            {HOLD_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
          </select>
        </label>
        <label>Finger capacity
          <select
            id="finger-capacity-select"
            disabled={busy}
            value={hold?.fingerCapacity?.toString() ?? ""}
            onChange={(event) => {
              const value = event.currentTarget.value;
              onFingerCapacityChange(value ? Number(value) : undefined);
            }}
          >
            <option value="">Unset</option>
            {[1, 2, 3, 4].map((capacity) => <option key={capacity} value={capacity}>{capacity}</option>)}
          </select>
        </label>
        <label>Outline shape
          <select
            id="outline-shape-select"
            disabled={busy}
            value={hold?.shapeConstraint?.shape ?? "custom"}
            onChange={(event) => onOutlineShapeChange(event.currentTarget.value)}
          >
            {OUTLINE_SHAPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <div className="rotate-controls">
          <span className="eyebrow">Rotate hold (Shift for 45°)</span>
          <div className="button-row">
            <button type="button" id="rotate-ccw-button" className="tool-button" title="Rotate counterclockwise" disabled={busy} onClick={(event) => onRotate(-1, event.shiftKey)}>⟲ CCW</button>
            <button type="button" id="rotate-cw-button" className="tool-button" title="Rotate clockwise" disabled={busy} onClick={(event) => onRotate(1, event.shiftKey)}>⟳ CW</button>
          </div>
          <label htmlFor="rotate-by-input">Rotate by</label>
          <span className="rotate-by-input-row">
            <input id="rotate-by-input" type="number" step="any" placeholder="Degrees" disabled={busy} value={rotationDegrees} onInput={(event) => onRotationDegreesChange(event.currentTarget.value)} />
            <button type="button" id="rotate-by-apply-button" className="tool-button" disabled={busy} onClick={onApplyRotation}>Apply</button>
          </span>
        </div>
        <button type="button" id="duplicate-mirror-hold-button" className="tool-button" disabled={busy} onClick={onDuplicateAndMirror}>Duplicate & mirror</button>
        <button type="button" id="delete-hold-button" className="tool-button danger" disabled={busy} onClick={onDelete}>Delete hold</button>
      </form>
    </aside>
  );
}
