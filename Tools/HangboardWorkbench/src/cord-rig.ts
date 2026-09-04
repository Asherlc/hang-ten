import type {
  Board,
  DirectTwoAnchorCordRig,
  EditorDocument,
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

export type CordRigPresentationGeometry =
  | DirectCordRigPresentationGeometry
  | RoutedCordRigPresentationGeometry;

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
  const cordUnitScale = 1 / Math.sqrt(sceneUnitsPerFaceX * sceneUnitsPerFaceY);
  const viewBox = {
    x: -faceOrigin.x / sceneUnitsPerFaceX,
    y: -faceOrigin.y / sceneUnitsPerFaceY,
    width: rig.sceneSize.width / sceneUnitsPerFaceX,
    height: rig.sceneSize.height / sceneUnitsPerFaceY,
  };

  if (rig.type === "routed") {
    const transformedPorts = new Map(rig.ports.map((port) => {
      const scenePoint = sourceRelativeScenePoint(port.point);
      return [port.id, sceneToFace(port.space === "body"
        ? rotateClockwise(scenePoint, sceneAnchor, rotationDegrees)
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
        ? rotateClockwise(scenePoint, sceneAnchor, rotationDegrees)
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
          occlusion.radius * cordUnitScale,
          occlusion.chordOffset * cordUnitScale,
        ),
      });
    }

    return {
      type: "routed",
      rig,
      viewBox,
      rotationDegrees,
      rotationAnchor,
      cordUnitScale,
      layers,
      renderLayers,
      occlusions,
    };
  }

  const projectedAttachments = rig.attachmentPoints.map((point) => sceneToFace(
    rotateClockwise(sourceRelativeScenePoint(point), sceneAnchor, rotationDegrees),
  )).sort((left, right) => left.x - right.x || left.y - right.y);
  const scenePullPoint = sourceRelativeScenePoint(rig.pullPoint);
  const pullPoint = sceneToFace(scenePullPoint);
  const strands = [
    { start: pullPoint, end: projectedAttachments[0]! },
    { start: pullPoint, end: projectedAttachments[1]! },
  ] as const;
  const eyeletRadius = rig.eyeletRadius * cordUnitScale;
  const eyeletForegroundCrescents = strands.map((strand) => (
    eyeletForegroundCrescent(
      strand.end,
      strand.start,
      eyeletRadius,
      7 * cordUnitScale,
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
