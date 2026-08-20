export interface ValidationPanelProps {
  validation: string;
}

export function ValidationPanel({ validation }: ValidationPanelProps) {
  return (
    <div className={`validation-panel${validation ? "" : " hidden"}`} id="validation-panel" role="alert">
      <strong>Fix geometry before saving</strong>
      <ul id="validation-list">{validation && <li>{validation}</li>}</ul>
    </div>
  );
}
import React from "react";
