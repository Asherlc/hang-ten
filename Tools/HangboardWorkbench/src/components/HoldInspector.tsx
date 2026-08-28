import React from "react";

import type { HoldRegion, MillimeterRange } from "../types.ts";

type DepthMeasurementMode = "unset" | "fixed" | "variable";

function depthMeasurementMode(hold: HoldRegion | null): DepthMeasurementMode {
  if (hold?.sizeMillimeters !== undefined) return "fixed";
  if (hold?.depthRangeMillimeters !== undefined) return "variable";
  return "unset";
}

const HOLD_TYPES = ["jug", "sloper", "edge", "pocket", "pinch", "gaston"] as const;
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
  gastonPairCandidates: readonly string[];
  onPairedHoldIDChange(pairedHoldID: string | undefined): void;
  onFingerCapacityChange(capacity: number | undefined): void;
  onDepthMeasurementChange(mode: DepthMeasurementMode): void;
  onSizeMillimetersChange(size: number | undefined): void;
  onDepthRangeChange(depthRange: MillimeterRange | undefined): void;
  onHandCapacityChange(capacity: number | undefined): void;
  onOutlineShapeChange(shape: string): void;
  onRotate(direction: -1 | 1, shiftKey: boolean): void;
  onApplyRotation(): void;
  onAddSegment(): void;
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
  gastonPairCandidates,
  onPairedHoldIDChange,
  onFingerCapacityChange,
  onDepthMeasurementChange,
  onSizeMillimetersChange,
  onDepthRangeChange,
  onHandCapacityChange,
  onOutlineShapeChange,
  onRotate,
  onApplyRotation,
  onAddSegment,
  onDuplicateAndMirror,
  onDelete,
  onMobileCollapse,
  className = "",
}: HoldInspectorProps) {
  const [selectedDepthMode, setSelectedDepthMode] = React.useState<DepthMeasurementMode>(() => depthMeasurementMode(hold));
  const depthInputRef = React.useRef<HTMLInputElement>(null);
  const lowerDepthInputRef = React.useRef<HTMLInputElement>(null);
  const upperDepthInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    setSelectedDepthMode(depthMeasurementMode(hold));
  }, [hold?.key]);

  React.useEffect(() => {
    depthInputRef.current?.setCustomValidity("");
    lowerDepthInputRef.current?.setCustomValidity("");
    upperDepthInputRef.current?.setCustomValidity("");
  }, [
    hold?.key,
    hold?.sizeMillimeters,
    hold?.depthRangeMillimeters?.lowerBound,
    hold?.depthRangeMillimeters?.upperBound,
  ]);

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
        {hold?.type === "gaston" && (hold.pairedHoldID
          ? <div>
              <span className="field-label">Paired gaston hold</span>
              <output id="gaston-pair-current" aria-label={`Paired gaston hold: ${hold.pairedHoldID}`}>{hold.pairedHoldID}</output>
            </div>
          : gastonPairCandidates.length > 0
            ? <label>Paired gaston hold
                <select
                  id="gaston-pair-select"
                  disabled={busy}
                  value=""
                  onChange={(event) => onPairedHoldIDChange(event.currentTarget.value)}
                >
                  {gastonPairCandidates.map((holdID) => <option key={holdID} value={holdID}>{holdID}</option>)}
                </select>
              </label>
            : <p id="gaston-pair-unavailable" role="status">No unpaired gaston holds are available.</p>
        )}
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
        <label>Depth measurement
          <select
            id="depth-measurement-select"
            disabled={busy}
            value={selectedDepthMode}
            onChange={(event) => {
              const mode = event.currentTarget.value as DepthMeasurementMode;
              setSelectedDepthMode(mode);
              onDepthMeasurementChange(mode);
            }}
          >
            <option value="unset">Unset</option>
            <option value="fixed">Fixed</option>
            <option value="variable">Variable</option>
          </select>
        </label>
        {selectedDepthMode === "fixed" && <label>Depth (mm)
          <input
            id="hold-depth-input"
            type="number"
            min={Number.MIN_VALUE}
            step="any"
            disabled={busy}
            ref={depthInputRef}
            value={hold?.sizeMillimeters ?? ""}
            onChange={(event) => {
              const value = event.currentTarget.value;
              if (!value) {
                event.currentTarget.setCustomValidity("");
                onSizeMillimetersChange(undefined);
                return;
              }
              const size = Number(value);
              if (!Number.isFinite(size) || size <= 0) {
                event.currentTarget.setCustomValidity("Depth must be greater than 0 mm.");
                event.currentTarget.reportValidity();
                return;
              }
              event.currentTarget.setCustomValidity("");
              onSizeMillimetersChange(size);
            }}
          />
        </label>}
        {selectedDepthMode === "variable" && <fieldset className="depth-range-inputs">
          <legend>Depth range (mm)</legend>
          <label>Minimum
            <input
              id="depth-range-lower-input"
              type="number"
              min={Number.MIN_VALUE}
              step="any"
              disabled={busy}
              ref={lowerDepthInputRef}
              value={hold?.depthRangeMillimeters?.lowerBound ?? ""}
              onChange={(event) => {
                const value = event.currentTarget.value;
                if (!value) {
                  event.currentTarget.setCustomValidity("");
                  onDepthRangeChange(undefined);
                  return;
                }
                const lowerBound = Number(value);
                if (!Number.isFinite(lowerBound) || lowerBound <= 0) {
                  event.currentTarget.setCustomValidity("Depth must be greater than 0 mm.");
                  event.currentTarget.reportValidity();
                  return;
                }
                event.currentTarget.setCustomValidity("");
                const upperBound = Math.max(hold?.depthRangeMillimeters?.upperBound ?? lowerBound, lowerBound);
                onDepthRangeChange({ lowerBound, upperBound });
              }}
            />
          </label>
          <label>Maximum
            <input
              id="depth-range-upper-input"
              type="number"
              min={Number.MIN_VALUE}
              step="any"
              disabled={busy}
              ref={upperDepthInputRef}
              value={hold?.depthRangeMillimeters?.upperBound ?? ""}
              onChange={(event) => {
                const value = event.currentTarget.value;
                if (!value) {
                  event.currentTarget.setCustomValidity("");
                  onDepthRangeChange(undefined);
                  return;
                }
                const upperBound = Number(value);
                if (!Number.isFinite(upperBound) || upperBound <= 0) {
                  event.currentTarget.setCustomValidity("Depth must be greater than 0 mm.");
                  event.currentTarget.reportValidity();
                  return;
                }
                event.currentTarget.setCustomValidity("");
                const lowerBound = Math.min(hold?.depthRangeMillimeters?.lowerBound ?? upperBound, upperBound);
                onDepthRangeChange({ lowerBound, upperBound });
              }}
            />
          </label>
        </fieldset>}
        <label>Hand capacity
          <select
            id="hand-capacity-select"
            disabled={busy}
            value={hold?.handCapacity?.toString() ?? ""}
            onChange={(event) => {
              const value = event.currentTarget.value;
              onHandCapacityChange(value ? Number(value) : undefined);
            }}
          >
            <option value="">Unset</option>
            {[1, 2].map((capacity) => <option key={capacity} value={capacity}>{capacity}</option>)}
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
        <button type="button" id="add-hold-segment-button" className="tool-button" disabled={busy || !hold?.metadata?.holdID} onClick={onAddSegment}>Add segment</button>
        <button type="button" id="duplicate-mirror-hold-button" className="tool-button" disabled={busy} onClick={onDuplicateAndMirror}>Duplicate & mirror</button>
        <button type="button" id="delete-hold-button" className="tool-button danger" disabled={busy} onClick={onDelete}>Delete hold</button>
      </form>
    </aside>
  );
}
