import React from "react";

import type { ContactRegion, PhysicalContact } from "../types.ts";

const CONTACT_KINDS = ["jug", "sloper", "edge", "pocket", "pinch", "gaston"] as const;
const OUTLINE_SHAPES = [
  ["custom", "Custom"], ["oval", "Oval"], ["circle", "Circle"],
  ["pill", "Pill"], ["roundedRectangle", "Rounded rectangle"],
  ["rectangle", "Rectangle"],
] as const;

export interface ContactInspectorProps {
  region: ContactRegion | null;
  contact: PhysicalContact | null;
  selectedCount: number;
  busy: boolean;
  rotationDegrees: string;
  onRotationDegreesChange(value: string): void;
  onContactChange(contact: PhysicalContact): void;
  onDisplayPathChange(value: string): void;
  onTreatmentChange(treatment: ContactRegion["treatment"]): void;
  gastonPairCandidates: readonly string[];
  onOutlineShapeChange(shape: string): void;
  onRotate(direction: -1 | 1, shiftKey: boolean): void;
  onApplyRotation(): void;
  onAddSegment(): void;
  onDuplicateAndMirror(): void;
  onDelete(): void;
  onMobileCollapse(): void;
  className?: string;
}

function commaSeparated(value: string): string[] {
  return [...new Set(value.split(",").map((item) => item.trim()).filter(Boolean))];
}

export function ContactInspector({
  region,
  contact,
  selectedCount,
  busy,
  rotationDegrees,
  onRotationDegreesChange,
  onContactChange,
  onDisplayPathChange,
  onTreatmentChange,
  gastonPairCandidates,
  onOutlineShapeChange,
  onRotate,
  onApplyRotation,
  onAddSegment,
  onDuplicateAndMirror,
  onDelete,
  onMobileCollapse,
  className = "",
}: ContactInspectorProps) {
  const update = (patch: Partial<PhysicalContact>): void => {
    if (contact) onContactChange({ ...contact, ...patch });
  };
  return (
    <aside className={`panel inspector-panel ${className}`.trim()} aria-labelledby="contact-heading">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Contact</span>
          <h2 id="contact-heading">{contact?.name ?? "No selection"}</h2>
          {selectedCount > 1 && <span id="selected-contact-count">{selectedCount} selected</span>}
        </div>
        <button className="tool-button mobile-sheet-collapse" type="button" onClick={onMobileCollapse}>Collapse</button>
      </div>
      <div className={`inspector-empty${region && contact ? " hidden" : ""}`}>Select a contact to edit its facts and contour.</div>
      <form className={`inspector-form${region && contact ? "" : " hidden"}`}>
        <label>Contact ID <input type="text" readOnly value={contact?.id ?? ""} /></label>
        <label>Canonical SVG path <textarea disabled={busy} value={region?.displayPath ?? ""} onChange={(event) => onDisplayPathChange(event.currentTarget.value)} /></label>
        <label>Name <input id="contact-name" type="text" disabled={busy} value={contact?.name ?? ""} onChange={(event) => update({ name: event.currentTarget.value })} /></label>
        <label>Kind
          <select disabled={busy} value={contact?.kind ?? ""} onChange={(event) => {
            const kind = event.currentTarget.value;
            if (kind === "gaston") update({ kind });
            else if (contact) {
              const { pairedContactID: _removed, ...unpaired } = contact;
              onContactChange({ ...unpaired, kind });
            }
          }}>
            {CONTACT_KINDS.map((kind) => <option key={kind} value={kind}>{kind}</option>)}
          </select>
        </label>
        <label>Equipment object <input type="text" disabled={busy} value={contact?.equipmentObjectID ?? ""} onChange={(event) => update({ equipmentObjectID: event.currentTarget.value })} /></label>
        {contact?.kind === "gaston" && <label>Paired gaston contact
          <select disabled={busy} value={contact.pairedContactID ?? ""} onChange={(event) => update({ pairedContactID: event.currentTarget.value })}>
            <option value="">Choose a contact</option>
            {gastonPairCandidates.map((contactID) => <option key={contactID} value={contactID}>{contactID}</option>)}
          </select>
        </label>}
        <label>Features <input type="text" disabled={busy} value={contact?.features.join(", ") ?? ""} onChange={(event) => update({ features: commaSeparated(event.currentTarget.value) })} /></label>
        <label>Grip types <input type="text" disabled={busy} value={contact?.gripTypes.join(", ") ?? ""} onChange={(event) => update({ gripTypes: commaSeparated(event.currentTarget.value) })} /></label>
        <label>Finger capacity
          <select disabled={busy} value={contact?.fingerCapacity?.toString() ?? ""} onChange={(event) => {
            if (!contact) return;
            const value = event.currentTarget.value;
            const next = { ...contact };
            if (value) next.fingerCapacity = Number(value); else delete next.fingerCapacity;
            onContactChange(next);
          }}><option value="">Unset</option>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}</select>
        </label>
        <label>Hand capacity
          <select disabled={busy} value={contact?.handCapacity?.toString() ?? ""} onChange={(event) => {
            if (!contact) return;
            const value = event.currentTarget.value;
            const next = { ...contact };
            if (value) next.handCapacity = Number(value); else delete next.handCapacity;
            onContactChange(next);
          }}><option value="">Unset</option>{[1, 2].map((value) => <option key={value}>{value}</option>)}</select>
        </label>
        <label>Side
          <select disabled={busy} value={contact?.side ?? ""} onChange={(event) => {
            if (!contact) return;
            const next = { ...contact };
            if (event.currentTarget.value) next.side = event.currentTarget.value as "left" | "right";
            else delete next.side;
            onContactChange(next);
          }}><option value="">Unset</option><option value="left">left</option><option value="right">right</option></select>
        </label>
        <fieldset className="depth-range-inputs">
          <legend>Depth range (mm)</legend>
          <label>Minimum <input type="number" min="0" step="any" disabled={busy} value={contact?.depthRangeMillimeters?.lowerBound ?? ""} onChange={(event) => {
            if (!contact) return;
            const lowerBound = Number(event.currentTarget.value);
            if (!lowerBound) { const next = { ...contact }; delete next.depthRangeMillimeters; onContactChange(next); return; }
            update({ depthRangeMillimeters: { lowerBound, upperBound: Math.max(lowerBound, contact.depthRangeMillimeters?.upperBound ?? lowerBound) } });
          }} /></label>
          <label>Maximum <input type="number" min="0" step="any" disabled={busy} value={contact?.depthRangeMillimeters?.upperBound ?? ""} onChange={(event) => {
            if (!contact) return;
            const upperBound = Number(event.currentTarget.value);
            if (!upperBound) { const next = { ...contact }; delete next.depthRangeMillimeters; onContactChange(next); return; }
            update({ depthRangeMillimeters: { lowerBound: Math.min(upperBound, contact.depthRangeMillimeters?.lowerBound ?? upperBound), upperBound } });
          }} /></label>
        </fieldset>
        <label>Outline shape
          <select disabled={busy} value={region?.shapeConstraint?.shape ?? "custom"} onChange={(event) => onOutlineShapeChange(event.currentTarget.value)}>
            {OUTLINE_SHAPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label>Geometry treatment
          <select id="contact-treatment" disabled={busy} value={region?.treatment?.type ?? "surface"} onChange={(event) => {
            const type = event.currentTarget.value;
            if (type === "surface") onTreatmentChange({ type });
            if (type === "shelf") onTreatmentChange({ type, rimInsetFraction: 0.15 });
            if (type === "recess") onTreatmentChange({ type, rimInsetFraction: 0.15, depth: "shallow" });
          }}>
            <option value="surface">Surface</option>
            <option value="shelf">Shelf</option>
            <option value="recess">Recess</option>
          </select>
        </label>
        {(region?.treatment?.type === "shelf" || region?.treatment?.type === "recess") && <label>Rim inset fraction
          <input type="number" min="0" max="0.5" step="0.01" disabled={busy} value={region.treatment.rimInsetFraction} onChange={(event) => {
            const rimInsetFraction = Number(event.currentTarget.value);
            if (!Number.isFinite(rimInsetFraction)) return;
            if (region.treatment?.type === "shelf") onTreatmentChange({ type: "shelf", rimInsetFraction });
            if (region.treatment?.type === "recess") onTreatmentChange({
              type: "recess", rimInsetFraction, depth: region.treatment.depth,
            });
          }} />
        </label>}
        {region?.treatment?.type === "recess" && <label>Recess depth
          <select disabled={busy} value={region.treatment.depth} onChange={(event) => onTreatmentChange({
            type: "recess",
            rimInsetFraction: region.treatment?.type === "recess" ? region.treatment.rimInsetFraction : 0.15,
            depth: event.currentTarget.value as "shallow" | "deep",
          })}>
            <option value="shallow">Shallow</option>
            <option value="deep">Deep</option>
          </select>
        </label>}
        <div className="rotate-controls">
          <div className="button-row">
            <button type="button" className="tool-button" disabled={busy} onClick={(event) => onRotate(-1, event.shiftKey)}>⟲ CCW</button>
            <button type="button" className="tool-button" disabled={busy} onClick={(event) => onRotate(1, event.shiftKey)}>⟳ CW</button>
          </div>
          <input type="number" step="any" placeholder="Degrees" disabled={busy} value={rotationDegrees} onInput={(event) => onRotationDegreesChange(event.currentTarget.value)} />
          <button type="button" className="tool-button" disabled={busy} onClick={onApplyRotation}>Apply rotation</button>
        </div>
        <button type="button" className="tool-button" disabled={busy || !region} onClick={onAddSegment}>Add piece</button>
        <button type="button" className="tool-button" disabled={busy || !region} onClick={onDuplicateAndMirror}>Duplicate &amp; mirror</button>
        <button type="button" className="tool-button danger" disabled={busy} onClick={onDelete}>Delete contact</button>
      </form>
    </aside>
  );
}
