import type {
  Board,
  DirectTwoAnchorCordRig,
  EditorDocument,
  ExternalSlidingLoopCordRig,
  Point,
  RoutedCordLayer,
  RoutedCordPathCommand,
  RoutedCordRig,
  RoutedCordSpace,
} from "./types.ts";

export interface CordStrand {
  start: Point;
  end: Point;
}

interface CommonCordRigPresentationGeometry {
  viewBox: { x: number; y: number; width: number; height: number };
  rotationDegrees: number;
  geometryScale: number;
  rotationAnchor: Point;
  cordUnitScale: number;
}

export interface DirectCordRigPresentationGeometry extends CommonCordRigPresentationGeometry {
  type: "directTwoAnchor";
  rig: DirectTwoAnchorCordRig;
  pullPoint: Point;
  strands: [CordStrand, CordStrand];
  tensionPath: string;
  eyeletForegroundCrescents: [string, string];
  eyeletRadius: number;
}

export interface RoutedCordDrawPath {
  kind: "span" | "path";
  id: string;
  d: string;
  bodyPortID?: string;
  worldPortID?: string;
}

export interface RoutedCordOcclusionPath {
  type: "radialLip" | "facePatch";
  d: string;
}

export interface RoutedCordRigPresentationGeometry extends CommonCordRigPresentationGeometry {
  type: "routed";
  rig: RoutedCordRig;
  layers: Record<RoutedCordLayer, RoutedCordDrawPath[]>;
  renderLayers: Record<RoutedCordLayer, RoutedCordDrawPath[]>;
  occlusions: RoutedCordOcclusionPath[];
}

export interface ExternalSlidingLoopPresentationGeometry extends CommonCordRigPresentationGeometry {
  type: "externalSlidingLoop";
  rig: ExternalSlidingLoopCordRig;
  pullPoint: Point;
  contactPoints: [Point, Point];
  returnPoints: Point[];
  tensionPath: string;
  returnPath: string;
  renderLayers: Record<RoutedCordLayer, RoutedCordDrawPath[]>;
}

export type CordRigPresentationGeometry =
  | DirectCordRigPresentationGeometry
  | RoutedCordRigPresentationGeometry
  | ExternalSlidingLoopPresentationGeometry;

function transformBodyPoint(
  point: Point,
  anchor: Point,
  degrees: number,
  geometryScale: number,
): Point {
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
  const deltaX = (point.x - anchor.x) * geometryScale;
  const deltaY = (point.y - anchor.y) * geometryScale;
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

function routedCommandPath(
  commands: readonly RoutedCordPathCommand[],
  transform: (point: Point) => Point,
): string {
  return commands.map((command) => {
    switch (command.command) {
      case "close":
        return "Z";
      case "move":
        return pointCommand("M", [transform({ x: command.to[0], y: command.to[1] })]);
      case "line":
        return pointCommand("L", [transform({ x: command.to[0], y: command.to[1] })]);
      case "quad": {
        const control = transform({ x: command.control[0], y: command.control[1] });
        const destination = transform({ x: command.to[0], y: command.to[1] });
        return pointCommand("Q", [control, destination]);
      }
      case "curve": {
        const control1 = transform({ x: command.control1[0], y: command.control1[1] });
        const control2 = transform({ x: command.control2[0], y: command.control2[1] });
        const destination = transform({ x: command.to[0], y: command.to[1] });
        return pointCommand("C", [control1, control2, destination]);
      }
    }
  }).join(" ");
}

const SLIDING_LOOP_CORNER_STEPS = 24;

function roundedRectangleBoundary(
  center: Point,
  halfWidth: number,
  halfHeight: number,
  radius: number,
  rotationDegrees: number,
): Point[] {
  const coreHalfWidth = Math.max(0, halfWidth - radius);
  const coreHalfHeight = Math.max(0, halfHeight - radius);
  const corners = [
    { x: coreHalfWidth, y: -coreHalfHeight, start: -Math.PI / 2 },
    { x: coreHalfWidth, y: coreHalfHeight, start: 0 },
    { x: -coreHalfWidth, y: coreHalfHeight, start: Math.PI / 2 },
    { x: -coreHalfWidth, y: -coreHalfHeight, start: Math.PI },
  ];
  const points: Point[] = [];
  for (const corner of corners) {
    for (let step = 0; step <= SLIDING_LOOP_CORNER_STEPS; step += 1) {
      const angle = corner.start + step * Math.PI / (2 * SLIDING_LOOP_CORNER_STEPS);
      const local = {
        x: center.x + corner.x + radius * Math.cos(angle),
        y: center.y + corner.y + radius * Math.sin(angle),
      };
      const transformed = transformBodyPoint(local, center, rotationDegrees, 1);
      const previous = points.at(-1);
      if (!previous || Math.hypot(previous.x - transformed.x, previous.y - transformed.y) > 1e-9) {
        points.push(transformed);
      }
    }
  }
  const first = points[0];
  const last = points.at(-1);
  if (first && last && Math.hypot(first.x - last.x, first.y - last.y) <= 1e-9) {
    points.pop();
  }
  return points;
}

function normalizedAngleDifference(angle: number, reference: number): number {
  const fullTurn = 2 * Math.PI;
  return ((angle - reference + Math.PI) % fullTurn + fullTurn) % fullTurn - Math.PI;
}

function cyclicBoundaryArc(
  boundary: readonly Point[],
  startIndex: number,
  endIndex: number,
  step: 1 | -1,
): Point[] {
  const points = [boundary[startIndex]!];
  let index = startIndex;
  for (let count = 0; count < boundary.length; count += 1) {
    if (index === endIndex) return points;
    index = (index + step + boundary.length) % boundary.length;
    points.push(boundary[index]!);
  }
  return [];
}

function pathThroughPoints(points: readonly Point[]): string {
  if (points.length === 0) return "";
  return [
    pointCommand("M", [points[0]!]),
    ...points.slice(1).map((point) => pointCommand("L", [point])),
  ].join(" ");
}

function resolveExternalSlidingLoop(
  rig: ExternalSlidingLoopCordRig,
  rotationDegrees: number,
  geometryScale: number,
  sceneAnchor: Point,
  sceneToFace: (point: Point) => Point,
  sourceRelativeScenePoint: (point: Point) => Point,
): {
  pullPoint: Point;
  contactPoints: [Point, Point];
  returnPoints: Point[];
  tensionPath: string;
  returnPath: string;
  renderLayers: Record<RoutedCordLayer, RoutedCordDrawPath[]>;
} | null {
  const frame = rig.bodyContactFrame;
  const bodyCenter = sourceRelativeScenePoint({
    x: frame.x + frame.width / 2,
    y: frame.y + frame.height / 2,
  });
  const center = transformBodyPoint(bodyCenter, sceneAnchor, rotationDegrees, geometryScale);
  const centerlineOffset = rig.style.diameter / 2 + rig.clearance;
  const halfWidth = frame.width * geometryScale / 2 + centerlineOffset;
  const halfHeight = frame.height * geometryScale / 2 + centerlineOffset;
  const radius = rig.cornerRadius * geometryScale + centerlineOffset;
  const scenePullPoint = sourceRelativeScenePoint(rig.pullPoint);
  if (![center.x, center.y, halfWidth, halfHeight, radius, scenePullPoint.x, scenePullPoint.y]
    .every(Number.isFinite)
    || halfWidth <= 0
    || halfHeight <= 0
    || radius < 0
    || radius > Math.min(halfWidth, halfHeight)) return null;

  const pullInBodyOrientation = transformBodyPoint(
    scenePullPoint,
    center,
    -rotationDegrees,
    1,
  );
  const coreHalfWidth = halfWidth - radius;
  const coreHalfHeight = halfHeight - radius;
  const rotationRadians = rotationDegrees * Math.PI / 180;
  const extentY = Math.abs(Math.sin(rotationRadians)) * coreHalfWidth
    + Math.abs(Math.cos(rotationRadians)) * coreHalfHeight
    + radius;
  if (!Number.isFinite(extentY) || scenePullPoint.y >= center.y - extentY) return null;
  const contactDeltaX = Math.abs(pullInBodyOrientation.x - center.x) - coreHalfWidth;
  const contactDeltaY = Math.abs(pullInBodyOrientation.y - center.y) - coreHalfHeight;
  const distanceFromRoundedCore = Math.hypot(
    Math.max(0, contactDeltaX),
    Math.max(0, contactDeltaY),
  );
  if (distanceFromRoundedCore <= radius) return null;

  const boundary = roundedRectangleBoundary(
    center,
    halfWidth,
    halfHeight,
    radius,
    rotationDegrees,
  );
  if (boundary.length < 4) return null;
  const centerDirection = Math.atan2(
    center.y - scenePullPoint.y,
    center.x - scenePullPoint.x,
  );
  const angularOffsets = boundary.map((point) => normalizedAngleDifference(
    Math.atan2(point.y - scenePullPoint.y, point.x - scenePullPoint.x),
    centerDirection,
  ));
  let firstTangentIndex = 0;
  let secondTangentIndex = 0;
  for (let index = 1; index < boundary.length; index += 1) {
    if (angularOffsets[index]! < angularOffsets[firstTangentIndex]!) firstTangentIndex = index;
    if (angularOffsets[index]! > angularOffsets[secondTangentIndex]!) secondTangentIndex = index;
  }
  if (firstTangentIndex === secondTangentIndex
    || angularOffsets[secondTangentIndex]! - angularOffsets[firstTangentIndex]! >= Math.PI) {
    return null;
  }

  const tangentIndexes = [firstTangentIndex, secondTangentIndex].sort((left, right) => (
    boundary[left]!.x - boundary[right]!.x || boundary[left]!.y - boundary[right]!.y
  ));
  const [leftIndex, rightIndex] = tangentIndexes as [number, number];
  const forwardArc = cyclicBoundaryArc(boundary, leftIndex, rightIndex, 1);
  const backwardArc = cyclicBoundaryArc(boundary, leftIndex, rightIndex, -1);
  const arcScore = (points: readonly Point[]): [number, number] => [
    Math.max(...points.map((point) => point.y)),
    points.reduce((sum, point) => sum + point.y, 0) / points.length,
  ];
  const forwardScore = arcScore(forwardArc);
  const backwardScore = arcScore(backwardArc);
  const sceneReturnPoints = forwardScore[0] > backwardScore[0]
    || (forwardScore[0] === backwardScore[0] && forwardScore[1] >= backwardScore[1])
    ? forwardArc
    : backwardArc;
  if (sceneReturnPoints.length < 2) return null;

  const pullPoint = sceneToFace(scenePullPoint);
  const contactPoints = [
    sceneToFace(boundary[leftIndex]!),
    sceneToFace(boundary[rightIndex]!),
  ] as [Point, Point];
  const returnPoints = sceneReturnPoints.map(sceneToFace);
  const tensionPath = pathThroughPoints([contactPoints[0], pullPoint, contactPoints[1]]);
  const returnPath = pathThroughPoints(returnPoints);
  return {
    pullPoint,
    contactPoints,
    returnPoints,
    tensionPath,
    returnPath,
    renderLayers: {
      behindFace: [
        { kind: "path", id: "external-loop-tension", d: tensionPath },
        { kind: "path", id: "external-loop-return", d: returnPath },
      ],
      aboveFace: [],
      overpass: [],
    },
  };
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
  const geometryScale = presentation.geometryScale ?? 1;
  const normalizedAnchor = presentation.geometryRotationAnchor ?? { x: 0.5, y: 0.5 };
  const sceneAnchor = {
    x: normalizedAnchor.x * rig.sceneSize.width,
    y: normalizedAnchor.y * rig.sceneSize.height,
  };
  const rotationAnchor = sceneToFace(sceneAnchor);
  const cordUnitScale = 1 / Math.sqrt(sceneUnitsPerFaceX * sceneUnitsPerFaceY);
  const viewBox = {
    x: -faceOrigin.x / sceneUnitsPerFaceX,
    y: -faceOrigin.y / sceneUnitsPerFaceY,
    width: rig.sceneSize.width / sceneUnitsPerFaceX,
    height: rig.sceneSize.height / sceneUnitsPerFaceY,
  };

  if (rig.type === "externalSlidingLoop") {
    const externalGeometry = resolveExternalSlidingLoop(
      rig,
      rotationDegrees,
      geometryScale,
      sceneAnchor,
      sceneToFace,
      sourceRelativeScenePoint,
    );
    if (!externalGeometry) return null;
    return {
      type: "externalSlidingLoop",
      rig,
      viewBox,
      rotationDegrees,
      geometryScale,
      rotationAnchor,
      cordUnitScale,
      ...externalGeometry,
    };
  }

  if (rig.type === "routed") {
    const transformedPorts = new Map(rig.ports.map((port) => {
      const scenePoint = sourceRelativeScenePoint(port.point);
      return [port.id, sceneToFace(port.space === "body"
        ? transformBodyPoint(scenePoint, sceneAnchor, rotationDegrees, geometryScale)
        : scenePoint)] as const;
    }));
    const layers: RoutedCordRigPresentationGeometry["layers"] = {
      behindFace: [],
      aboveFace: [],
      overpass: [],
    };
    const spanRecords: Array<{
      groupID: string;
      layer: RoutedCordLayer;
      bodyPoint: Point;
      worldPoint: Point;
      drawPath: RoutedCordDrawPath;
    }> = [];
    const incidentWorldPoint = new Map<string, Point>();

    for (const group of rig.tensionGroups) {
      const bodyPorts = group.bodyPortIDs.map((id, declarationIndex) => ({
        id,
        declarationIndex,
        point: transformedPorts.get(id),
      }));
      const worldPorts = group.worldPortIDs.map((id, declarationIndex) => ({
        id,
        declarationIndex,
        point: transformedPorts.get(id),
      }));
      if (bodyPorts.some((port) => !port.point) || worldPorts.some((port) => !port.point)) {
        return null;
      }
      const screenOrder = (
        left: { point: Point | undefined; declarationIndex: number },
        right: { point: Point | undefined; declarationIndex: number },
      ): number => (
        left.point!.x - right.point!.x
        || left.point!.y - right.point!.y
        || left.declarationIndex - right.declarationIndex
      );
      if (group.pairing === "screenOrder") {
        bodyPorts.sort(screenOrder);
        worldPorts.sort(screenOrder);
      }
      for (let index = 0; index < bodyPorts.length; index += 1) {
        const body = bodyPorts[index]!;
        const world = worldPorts[index]!;
        incidentWorldPoint.set(body.id, world.point!);
        const drawPath: RoutedCordDrawPath = {
          kind: "span",
          id: `${group.id}:${index}`,
          bodyPortID: body.id,
          worldPortID: world.id,
          d: [pointCommand("M", [world.point!]), pointCommand("L", [body.point!])].join(" "),
        };
        layers[group.layer].push(drawPath);
        spanRecords.push({
          groupID: group.id,
          layer: group.layer,
          bodyPoint: body.point!,
          worldPoint: world.point!,
          drawPath,
        });
      }
    }

    const transformRoutedPoint = (point: Point, space: RoutedCordSpace): Point => {
      const scenePoint = sourceRelativeScenePoint(point);
      return sceneToFace(space === "body"
        ? transformBodyPoint(scenePoint, sceneAnchor, rotationDegrees, geometryScale)
        : scenePoint);
    };
    for (const path of rig.paths) {
      layers[path.layer].push({
        kind: "path",
        id: path.id,
        d: routedCommandPath(
          path.commands,
          (point) => transformRoutedPoint(point, path.space),
        ),
      });
    }

    const renderLayers: RoutedCordRigPresentationGeometry["renderLayers"] = {
      behindFace: [],
      aboveFace: [],
      overpass: [],
    };
    const coincidentPointTolerance = Math.max(viewBox.width, viewBox.height) * 1e-9;
    for (const layer of ["behindFace", "aboveFace", "overpass"] as const) {
      const clusters: Array<{
        groupID: string;
        worldPoint: Point;
        records: typeof spanRecords;
      }> = [];

      for (const record of spanRecords.filter((candidate) => candidate.layer === layer)) {
        const cluster = clusters.find((candidate) => (
          candidate.groupID === record.groupID
          && Math.hypot(
            candidate.worldPoint.x - record.worldPoint.x,
            candidate.worldPoint.y - record.worldPoint.y,
          ) <= coincidentPointTolerance
        ));
        if (cluster) {
          cluster.records.push(record);
        } else {
          clusters.push({
            groupID: record.groupID,
            worldPoint: record.worldPoint,
            records: [record],
          });
        }
      }

      for (const [clusterIndex, cluster] of clusters.entries()) {
        if (cluster.records.length === 1) {
          renderLayers[layer].push(cluster.records[0]!.drawPath);
          continue;
        }
        const apex = cluster.records.reduce<Point>((sum, record) => ({
          x: sum.x + record.worldPoint.x,
          y: sum.y + record.worldPoint.y,
        }), { x: 0, y: 0 });
        apex.x /= cluster.records.length;
        apex.y /= cluster.records.length;

        const points = [cluster.records[0]!.bodyPoint, apex];
        for (const [recordIndex, record] of cluster.records.slice(1).entries()) {
          points.push(record.bodyPoint);
          if (recordIndex < cluster.records.length - 2) points.push(apex);
        }
        renderLayers[layer].push({
          kind: "span",
          id: `${cluster.groupID}:apex:${clusterIndex}`,
          d: [
            pointCommand("M", [points[0]!]),
            ...points.slice(1).map((point) => pointCommand("L", [point])),
          ].join(" "),
        });
      }
      renderLayers[layer].push(...layers[layer].filter((path) => path.kind === "path"));
    }

    const occlusions: RoutedCordOcclusionPath[] = [];
    for (const occlusion of rig.occlusions) {
      if (occlusion.type === "facePatch") {
        occlusions.push({
          type: "facePatch",
          d: routedCommandPath(
            occlusion.commands,
            (point) => transformRoutedPoint(point, "body"),
          ),
        });
        continue;
      }
      const center = transformedPorts.get(occlusion.bodyPortID);
      const toward = incidentWorldPoint.get(occlusion.bodyPortID);
      if (!center || !toward) return null;
      occlusions.push({
        type: "radialLip",
        d: eyeletForegroundCrescent(
          center,
          toward,
          occlusion.radius * geometryScale * cordUnitScale,
          occlusion.chordOffset * geometryScale * cordUnitScale,
        ),
      });
    }

    return {
      type: "routed",
      rig,
      viewBox,
      rotationDegrees,
      geometryScale,
      rotationAnchor,
      cordUnitScale,
      layers,
      renderLayers,
      occlusions,
    };
  }

  const projectedAttachments = rig.attachmentPoints.map((point) => sceneToFace(
    transformBodyPoint(
      sourceRelativeScenePoint(point),
      sceneAnchor,
      rotationDegrees,
      geometryScale,
    ),
  )).sort((left, right) => left.x - right.x || left.y - right.y);
  const scenePullPoint = sourceRelativeScenePoint(rig.pullPoint);
  const pullPoint = sceneToFace(scenePullPoint);
  const strands = [
    { start: pullPoint, end: projectedAttachments[0]! },
    { start: pullPoint, end: projectedAttachments[1]! },
  ] as const;
  const eyeletRadius = rig.eyeletRadius * geometryScale * cordUnitScale;
  const eyeletForegroundCrescents = strands.map((strand) => (
    eyeletForegroundCrescent(
      strand.end,
      strand.start,
      eyeletRadius,
      7 * geometryScale * cordUnitScale,
    )
  )) as [string, string];

  const tensionPath = [
    pointCommand("M", [projectedAttachments[0]!]),
    pointCommand("L", [pullPoint]),
    pointCommand("L", [projectedAttachments[1]!]),
  ].join(" ");

  return {
    type: "directTwoAnchor",
    rig,
    viewBox,
    rotationDegrees,
    geometryScale,
    rotationAnchor,
    pullPoint,
    strands: [strands[0], strands[1]],
    tensionPath,
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
