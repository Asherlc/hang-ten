import type {
  Board,
  DirectTwoAnchorCordRig,
  EditorDocument,
  Point,
} from "./types.ts";

export interface CordStrand {
  start: Point;
  end: Point;
}

export interface CordRigPresentationGeometry {
  rig: DirectTwoAnchorCordRig;
  viewBox: { x: number; y: number; width: number; height: number };
  rotationDegrees: number;
  rotationAnchor: Point;
  pullPoint: Point;
  strands: [CordStrand, CordStrand];
  supportPaths: [string, string, string, string];
  eyeletForegroundCrescents: [string, string];
  eyeletRadius: number;
  cordUnitScale: number;
}

function rotateClockwise(point: Point, anchor: Point, degrees: number): Point {
  const normalizedDegrees = ((degrees % 360) + 360) % 360;
  const radians = normalizedDegrees * Math.PI / 180;
  const cosine = normalizedDegrees === 90 || normalizedDegrees === 270
    ? 0
    : normalizedDegrees === 180 ? -1 : normalizedDegrees === 0 ? 1 : Math.cos(radians);
  const sine = normalizedDegrees === 90
    ? 1
    : normalizedDegrees === 180 || normalizedDegrees === 0
      ? 0
      : normalizedDegrees === 270 ? -1 : Math.sin(radians);
  const deltaX = point.x - anchor.x;
  const deltaY = point.y - anchor.y;
  return {
    x: anchor.x + cosine * deltaX - sine * deltaY,
    y: anchor.y + sine * deltaX + cosine * deltaY,
  };
}

function pathNumber(value: number): string {
  const normalized = Math.abs(value) < 1e-12 ? 0 : value;
  return Number(normalized.toFixed(12)).toString();
}

function pointCommand(command: string, points: readonly Point[]): string {
  return `${command} ${points.flatMap((point) => [
    pathNumber(point.x),
    pathNumber(point.y),
  ]).join(" ")}`;
}

function eyeletForegroundCrescent(
  center: Point,
  toward: Point,
  radius: number,
  chordOffset: number,
): string {
  const deltaX = toward.x - center.x;
  const deltaY = toward.y - center.y;
  const length = Math.hypot(deltaX, deltaY);
  if (!Number.isFinite(length) || length <= 0 || radius < chordOffset) return "";

  const unitX = deltaX / length;
  const unitY = deltaY / length;
  const normalX = -unitY;
  const normalY = unitX;
  const halfChord = Math.sqrt(radius * radius - chordOffset * chordOffset);
  const start = {
    x: center.x + chordOffset * unitX + halfChord * normalX,
    y: center.y + chordOffset * unitY + halfChord * normalY,
  };
  const end = {
    x: center.x + chordOffset * unitX - halfChord * normalX,
    y: center.y + chordOffset * unitY - halfChord * normalY,
  };
  return [
    pointCommand("M", [start]),
    `A ${pathNumber(radius)} ${pathNumber(radius)} 0 1 1 ${pathNumber(end.x)} ${pathNumber(end.y)}`,
    "Z",
  ].join(" ");
}

export function resolveCordRigPresentationGeometry(
  board: Board | null,
  document: EditorDocument | null,
): CordRigPresentationGeometry | null {
  if (!board || !document || !board.presentations || !board.selectedPresentationID) return null;
  const presentation = board.presentations.find(
    (candidate) => candidate.presentationID === board.selectedPresentationID,
  );
  if (!presentation) return null;
  const canonical = presentation.sourcePresentationID
    ? board.presentations.find(
      (candidate) => candidate.presentationID === presentation.sourcePresentationID,
    )
    : presentation;
  const rig = canonical?.cordRig;
  if (!rig || document.canvas.width <= 0 || document.canvas.height <= 0) return null;

  const faceOrigin = {
    x: rig.sourceFrame.x + rig.innerFaceFrame.x,
    y: rig.sourceFrame.y + rig.innerFaceFrame.y,
  };
  const sceneUnitsPerFaceX = rig.innerFaceFrame.width / document.canvas.width;
  const sceneUnitsPerFaceY = rig.innerFaceFrame.height / document.canvas.height;
  if (!Number.isFinite(sceneUnitsPerFaceX)
    || !Number.isFinite(sceneUnitsPerFaceY)
    || sceneUnitsPerFaceX <= 0
    || sceneUnitsPerFaceY <= 0) return null;

  const sceneToFace = (point: Point): Point => ({
    x: (point.x - faceOrigin.x) / sceneUnitsPerFaceX,
    y: (point.y - faceOrigin.y) / sceneUnitsPerFaceY,
  });
  const sourceRelativeScenePoint = (point: Point): Point => ({
    x: rig.sourceFrame.x + point.x,
    y: rig.sourceFrame.y + point.y,
  });
  const rotationDegrees = presentation.rotationDegrees
    ?? (presentation.isInverted === true ? 180 : 0);
  const normalizedAnchor = presentation.geometryRotationAnchor ?? { x: 0.5, y: 0.5 };
  const sceneAnchor = {
    x: normalizedAnchor.x * rig.sceneSize.width,
    y: normalizedAnchor.y * rig.sceneSize.height,
  };
  const rotationAnchor = sceneToFace(sceneAnchor);
  const projectedAttachments = rig.attachmentPoints.map((point) => sceneToFace(
    rotateClockwise(sourceRelativeScenePoint(point), sceneAnchor, rotationDegrees),
  )).sort((left, right) => left.x - right.x || left.y - right.y);
  const scenePullPoint = sourceRelativeScenePoint(rig.pullPoint);
  const pullPoint = sceneToFace(scenePullPoint);
  const exits = [
    sceneToFace({ x: scenePullPoint.x - 22, y: scenePullPoint.y }),
    sceneToFace({ x: scenePullPoint.x + 22, y: scenePullPoint.y }),
  ] as const;
  const strands = [
    { start: exits[0], end: projectedAttachments[0]! },
    { start: exits[1], end: projectedAttachments[1]! },
  ] as const;
  const cordUnitScale = 1 / Math.sqrt(sceneUnitsPerFaceX * sceneUnitsPerFaceY);
  const eyeletRadius = rig.eyeletRadius * cordUnitScale;
  const eyeletForegroundCrescents = strands.map((strand) => (
    eyeletForegroundCrescent(
      strand.end,
      strand.start,
      eyeletRadius,
      7 * cordUnitScale,
    )
  )) as [string, string];

  const offsetPoint = (x: number, y: number): Point => sceneToFace({
    x: scenePullPoint.x + x,
    y: scenePullPoint.y + y,
  });
  const bight = [
    pointCommand("M", [offsetPoint(-12, -61)]),
    pointCommand("C", [offsetPoint(-26, -82), offsetPoint(-30, -115), offsetPoint(-21, -142)]),
    pointCommand("C", [offsetPoint(-14, -163), offsetPoint(-5, -174), offsetPoint(1, -177)]),
    pointCommand("C", [offsetPoint(9, -171), offsetPoint(18, -157), offsetPoint(24, -136)]),
    pointCommand("C", [offsetPoint(31, -109), offsetPoint(26, -81), offsetPoint(12, -61)]),
  ].join(" ");
  const knotAndExit = (mirror: number): string => [
    pointCommand("M", [offsetPoint(-12 * mirror, -63)]),
    pointCommand("C", [
      offsetPoint(1 * mirror, -52),
      offsetPoint(18 * mirror, -51),
      offsetPoint(21 * mirror, -39),
    ]),
    pointCommand("C", [
      offsetPoint(24 * mirror, -28),
      offsetPoint(16 * mirror, -19),
      offsetPoint(5 * mirror, -18),
    ]),
    pointCommand("C", [
      offsetPoint(-8 * mirror, -17),
      offsetPoint(-17 * mirror, -9),
      offsetPoint(-22 * mirror, 0),
    ]),
  ].join(" ");
  const overpass = [
    pointCommand("M", [offsetPoint(-18, -35)]),
    pointCommand("C", [offsetPoint(-10, -24), offsetPoint(9, -22), offsetPoint(18, -35)]),
  ].join(" ");

  return {
    rig,
    viewBox: {
      x: -faceOrigin.x / sceneUnitsPerFaceX,
      y: -faceOrigin.y / sceneUnitsPerFaceY,
      width: rig.sceneSize.width / sceneUnitsPerFaceX,
      height: rig.sceneSize.height / sceneUnitsPerFaceY,
    },
    rotationDegrees,
    rotationAnchor,
    pullPoint,
    strands: [strands[0], strands[1]],
    supportPaths: [bight, knotAndExit(1), knotAndExit(-1), overpass],
    eyeletForegroundCrescents,
    eyeletRadius,
    cordUnitScale,
  };
}

export function cordRigViewBox(
  geometry: CordRigPresentationGeometry,
): string {
  const { x, y, width, height } = geometry.viewBox;
  return [x, y, width, height].map(pathNumber).join(" ");
}
