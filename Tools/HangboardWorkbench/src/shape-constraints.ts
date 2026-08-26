import type {
  ConstrainedHandle,
  ShapeConstraint,
  ShapeConstraintShape,
} from "./types.ts";

export const CONSTRAINED_SHAPES: readonly ShapeConstraintShape[] = [
  "oval",
  "circle",
  "pill",
  "roundedRectangle",
  "rectangle",
];

export const CONSTRAINED_HANDLES: readonly ConstrainedHandle[] = [
  "nw",
  "n",
  "ne",
  "e",
  "se",
  "s",
  "sw",
  "w",
];

export function isConstrainedShape(value: unknown): value is ShapeConstraintShape {
  return typeof value === "string" && CONSTRAINED_SHAPES.includes(value as ShapeConstraintShape);
}

export function isConstrainedHandle(value: unknown): value is ConstrainedHandle {
  return typeof value === "string" && CONSTRAINED_HANDLES.includes(value as ConstrainedHandle);
}

export function validateShapeConstraint(
  value: unknown,
  subject = "Shape constraint",
): ShapeConstraint {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`${subject} is invalid`);
  }
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record);
  if (keys.length !== 2 || !Object.hasOwn(record, "shape") || !Object.hasOwn(record, "rotationDegrees")) {
    throw new Error(`${subject} must contain exactly shape and rotationDegrees`);
  }
  if (!isConstrainedShape(record.shape)) {
    throw new Error(`${subject} has an invalid shape`);
  }
  if (typeof record.rotationDegrees !== "number" || !Number.isFinite(record.rotationDegrees)) {
    throw new Error(`${subject} rotation must be finite`);
  }
  if (record.rotationDegrees < -180 || record.rotationDegrees >= 180) {
    throw new Error(`${subject} rotation must be normalized to [-180, 180)`);
  }
  return { shape: record.shape, rotationDegrees: record.rotationDegrees };
}

export function isShapeConstraint(value: unknown): value is ShapeConstraint {
  try {
    validateShapeConstraint(value);
    return true;
  } catch {
    return false;
  }
}
