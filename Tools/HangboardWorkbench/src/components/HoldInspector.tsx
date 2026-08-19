import type { HoldRegion } from "../types.ts";

const HOLD_TYPES = ["jug", "sloper", "edge", "pocket", "pinch"] as const;

export interface HoldInspectorProps {
  hold: HoldRegion | null;
  rotationDegrees: string;
  onRotationDegreesChange(value: string): void;
  onTypeChange(type: string): void;
  onRotate(degrees: number): void;
  onApplyRotation(): void;
  onDelete(): void;
}

export function HoldInspector({
  hold,
  rotationDegrees,
  onRotationDegreesChange,
  onTypeChange,
  onRotate,
  onApplyRotation,
  onDelete,
}: HoldInspectorProps) {
  return (
    <aside className="panel inspector-panel" aria-labelledby="hold-heading">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Hold</span>
          <h2 id="hold-heading">{hold?.key ?? "No selection"}</h2>
        </div>
      </div>
      <div className={`inspector-empty${hold ? " hidden" : ""}`} id="hold-empty">Select a hold to edit its closed contour.</div>
      <form className={`inspector-form${hold ? "" : " hidden"}`} id="hold-form">
        <label>Hold key <input id="hold-key" type="text" readOnly value={hold?.key ?? ""} /></label>
        <label>Hold type
          <select id="hold-type-select" value={hold?.type ?? ""} onChange={(event) => onTypeChange(event.currentTarget.value)}>
            {!hold?.type && <option value="" />}
            {HOLD_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
          </select>
        </label>
        <div className="rotate-controls">
          <span className="eyebrow">Rotate hold (Shift for 45°)</span>
          <div className="button-row">
            <button type="button" id="rotate-ccw-button" className="tool-button" title="Rotate counterclockwise" onClick={() => onRotate(-15)}>⟲ CCW</button>
            <button type="button" id="rotate-cw-button" className="tool-button" title="Rotate clockwise" onClick={() => onRotate(15)}>⟳ CW</button>
          </div>
          <label htmlFor="rotate-by-input">Rotate by</label>
          <span className="rotate-by-input-row">
            <input id="rotate-by-input" type="number" step="any" placeholder="Degrees" value={rotationDegrees} onInput={(event) => onRotationDegreesChange(event.currentTarget.value)} />
            <button type="button" id="rotate-by-apply-button" className="tool-button" onClick={onApplyRotation}>Apply</button>
          </span>
        </div>
        <button type="button" id="delete-hold-button" className="tool-button danger" onClick={onDelete}>Delete hold</button>
      </form>
    </aside>
  );
}
