import type {
  EditableAnchor,
  EditableControl,
  EditablePath,
  EditableSegment,
  PathCommand,
  PathEditor,
  Point,
} from "./types.ts";

export type {
  EditableAnchor,
  EditableControl,
  EditablePath,
  EditableSegment,
} from "./types.ts";

interface IdentityAllocator {
  nextOrdinal: number;
}

const allocators = new WeakMap<EditablePath, IdentityAllocator>();

function editableSegments(commands: readonly PathCommand[]): PathCommand[] {
  return commands.filter((command) => command.type !== "Z");
}

function controlID(regionKey: string, ordinal: number, controlIndex: number): string {
  return `${regionKey}:control:${ordinal}:${controlIndex}`;
}

function createSegment(regionKey: string, command: PathCommand, ordinal: number): EditableSegment {
  if (command.type === "Z") throw new Error("Close commands do not have editable segments.");
  const endpoint = command.points[0];
  if (!endpoint) throw new Error("Editable path commands require an endpoint.");
  return {
    id: `${regionKey}:segment:${ordinal}`,
    type: command.type,
    anchor: {
      id: `${regionKey}:anchor:${ordinal}`,
      ordinal,
      isStart: command.type === "M",
      x: endpoint.x,
      y: endpoint.y,
    },
    controls: command.controls.map((control, controlIndex) => ({
      id: controlID(regionKey, ordinal, controlIndex),
      x: control.x,
      y: control.y,
    })),
  };
}

function allocatedOrdinal(regionKey: string, id: string, kind: "segment" | "anchor" | "control"): number | null {
  const prefix = `${regionKey}:${kind}:`;
  if (!id.startsWith(prefix)) return null;
  const ordinal = Number(id.slice(prefix.length).split(":", 1)[0]);
  return Number.isInteger(ordinal) && ordinal >= 0 ? ordinal : null;
}

function allocatorFor(path: EditablePath): IdentityAllocator {
  const existing = allocators.get(path);
  if (existing) return existing;
  const highestOrdinal = path.segments.reduce((highest, segment) => {
    const segmentOrdinal = allocatedOrdinal(path.regionKey, segment.id, "segment");
    const anchorOrdinal = allocatedOrdinal(path.regionKey, segment.anchor.id, "anchor");
    return segment.controls.reduce((controlHighest, control) => {
      const controlOrdinal = allocatedOrdinal(path.regionKey, control.id, "control");
      return Math.max(controlHighest, controlOrdinal ?? -1);
    }, Math.max(highest, segment.anchor.ordinal, segmentOrdinal ?? -1, anchorOrdinal ?? -1));
  }, -1);
  const nextOrdinal = highestOrdinal + 1;
  const allocator = { nextOrdinal };
  allocators.set(path, allocator);
  return allocator;
}

function allocateSegment(path: EditablePath, command: PathCommand): EditableSegment {
  const allocator = allocatorFor(path);
  const ordinal = allocator.nextOrdinal;
  allocator.nextOrdinal += 1;
  return createSegment(path.regionKey, command, ordinal);
}

function allocateControl(path: EditablePath, control: Point, controlIndex: number): EditableControl {
  const allocator = allocatorFor(path);
  const ordinal = allocator.nextOrdinal;
  allocator.nextOrdinal += 1;
  return {
    id: controlID(path.regionKey, ordinal, controlIndex),
    x: control.x,
    y: control.y,
  };
}

function retainSegment(path: EditablePath, command: PathCommand, prior: EditableSegment): EditableSegment {
  if (command.type === "Z") throw new Error("Close commands do not have editable segments.");
  const endpoint = command.points[0];
  if (!endpoint) throw new Error("Editable path commands require an endpoint.");
  return {
    id: prior.id,
    type: command.type,
    anchor: {
      ...prior.anchor,
      isStart: command.type === "M",
      x: endpoint.x,
      y: endpoint.y,
    },
    controls: command.controls.map((control, controlIndex) => {
      const existing = prior.controls[controlIndex];
      return existing
        ? { ...existing, x: control.x, y: control.y }
        : allocateControl(path, control, controlIndex);
    }),
  };
}

function toPathCommands(path: EditablePath): PathCommand[] {
  const commands: PathCommand[] = path.segments.map((segment) => ({
    type: segment.type,
    points: [{ x: segment.anchor.x, y: segment.anchor.y }],
    controls: segment.controls.map((control) => ({ x: control.x, y: control.y })),
  }));
  if (path.closed) commands.push({ type: "Z", points: [], controls: [] });
  return commands;
}

function replaceFromCommands(
  path: EditablePath,
  commands: readonly PathCommand[],
  priorAtResultIndex: (resultIndex: number) => EditableSegment | undefined,
): void {
  const next = editableSegments(commands).map((command, index) => {
    const prior = priorAtResultIndex(index);
    return prior ? retainSegment(path, command, prior) : allocateSegment(path, command);
  });
  path.segments.splice(0, path.segments.length, ...next);
}

function mutateCommands(
  path: EditablePath,
  pathEditor: PathEditor,
  mutate: (commands: PathCommand[]) => void,
  priorAtResultIndex: (resultIndex: number) => EditableSegment | undefined,
): boolean {
  const commands = toPathCommands(path);
  const before = pathEditor.serializePath(commands);
  mutate(commands);
  if (pathEditor.serializePath(commands) === before) return false;
  replaceFromCommands(path, commands, priorAtResultIndex);
  return true;
}

function segmentIndex(path: EditablePath, segmentID: string): number | null {
  const index = path.segments.findIndex((segment) => segment.id === segmentID);
  return index === -1 ? null : index;
}

function anchorIndex(path: EditablePath, anchorID: string): number | null {
  const index = path.segments.findIndex((segment) => segment.anchor.id === anchorID);
  return index === -1 ? null : index;
}

export function createEditablePath(
  regionKey: string,
  pathString: string,
  pathEditor: PathEditor,
): EditablePath {
  const commands = pathEditor.parsePath(pathString);
  const segments = editableSegments(commands).map((command, index) => createSegment(regionKey, command, index));
  const path: EditablePath = {
    regionKey,
    segments,
    closed: commands.at(-1)?.type === "Z",
  };
  allocators.set(path, { nextOrdinal: segments.length });
  return path;
}

export function serializeEditablePath(path: EditablePath, pathEditor: PathEditor): string {
  return pathEditor.serializePath(toPathCommands(path));
}

export function editablePathAnchor(path: EditablePath, anchorID: string): EditableAnchor | undefined {
  return path.segments.find((segment) => segment.anchor.id === anchorID)?.anchor;
}

export function editablePathControl(path: EditablePath, controlID: string): EditableControl | undefined {
  return path.segments.flatMap((segment) => segment.controls).find((control) => control.id === controlID);
}

export function editablePathSegment(path: EditablePath, segmentID: string): EditableSegment | undefined {
  return path.segments.find((segment) => segment.id === segmentID);
}

export function moveEditableAnchor(path: EditablePath, anchorID: string, deltaX: number, deltaY: number): boolean {
  const segment = path.segments.find((candidate) => candidate.anchor.id === anchorID);
  if (!segment) return false;
  segment.anchor.x += deltaX;
  segment.anchor.y += deltaY;
  for (const control of segment.controls) {
    control.x += deltaX;
    control.y += deltaY;
  }
  return true;
}

export function moveEditableControl(path: EditablePath, controlID: string, deltaX: number, deltaY: number): boolean {
  const control = editablePathControl(path, controlID);
  if (!control) return false;
  control.x += deltaX;
  control.y += deltaY;
  return true;
}

export function translateEditablePath(path: EditablePath, deltaX: number, deltaY: number): void {
  for (const segment of path.segments) {
    segment.anchor.x += deltaX;
    segment.anchor.y += deltaY;
    for (const control of segment.controls) {
      control.x += deltaX;
      control.y += deltaY;
    }
  }
}

export function insertEditableVertex(
  path: EditablePath,
  afterSegmentID: string,
  point: Point,
  pathEditor: PathEditor,
): boolean {
  const afterIndex = segmentIndex(path, afterSegmentID);
  if (afterIndex === null) return false;
  const original = [...path.segments];
  return mutateCommands(
    path,
    pathEditor,
    (commands) => pathEditor.addVertex(commands, afterIndex, point.x, point.y),
    (resultIndex) => resultIndex <= afterIndex
      ? original[resultIndex]
      : resultIndex === afterIndex + 1 ? undefined : original[resultIndex - 1],
  );
}

export function insertEditableInflectionPoint(
  path: EditablePath,
  afterSegmentID: string,
  point: Point,
  pathEditor: PathEditor,
): boolean {
  const afterIndex = segmentIndex(path, afterSegmentID);
  if (afterIndex === null) return false;
  const original = [...path.segments];
  return mutateCommands(
    path,
    pathEditor,
    (commands) => {
      pathEditor.addInflectionPoint(commands, afterIndex, point);
    },
    (resultIndex) => resultIndex <= afterIndex
      ? original[resultIndex]
      : resultIndex === afterIndex + 1 ? undefined : original[resultIndex - 1],
  );
}

export function deleteEditableAnchor(path: EditablePath, anchorID: string, pathEditor: PathEditor): boolean {
  const deletedIndex = anchorIndex(path, anchorID);
  if (deletedIndex === null) return false;
  const original = [...path.segments];
  return mutateCommands(
    path,
    pathEditor,
    (commands) => pathEditor.deleteVertex(commands, deletedIndex),
    (resultIndex) => deletedIndex === 0
      ? original[resultIndex + 1]
      : resultIndex < deletedIndex ? original[resultIndex] : original[resultIndex + 1],
  );
}

export function editablePathAnchorIsInflection(
  path: EditablePath,
  anchorID: string,
  pathEditor: PathEditor,
): boolean {
  const index = anchorIndex(path, anchorID);
  return index !== null && pathEditor.isInflectionVertex(toPathCommands(path), index);
}

export function roundEditableAnchor(path: EditablePath, anchorID: string, pathEditor: PathEditor): boolean {
  const roundedIndex = anchorIndex(path, anchorID);
  if (roundedIndex === null) return false;
  const original = [...path.segments];
  const lastIndex = original.length - 1;
  return mutateCommands(
    path,
    pathEditor,
    (commands) => {
      pathEditor.roundVertex(commands, roundedIndex);
    },
    (resultIndex) => {
      if (roundedIndex === 0) return resultIndex === 1
        ? undefined
        : resultIndex === 0 ? original[0] : original[resultIndex - 1];
      if (roundedIndex === lastIndex) return resultIndex <= lastIndex ? original[resultIndex] : undefined;
      if (resultIndex <= roundedIndex) return original[resultIndex];
      if (resultIndex === roundedIndex + 1) return undefined;
      return original[resultIndex - 1];
    },
  );
}

export function makeEditableSegmentBendable(
  path: EditablePath,
  afterSegmentID: string,
  pathEditor: PathEditor,
): boolean {
  const afterIndex = segmentIndex(path, afterSegmentID);
  if (afterIndex === null) return false;
  const original = [...path.segments];
  const closesPath = path.closed && afterIndex === original.length - 1;
  return mutateCommands(
    path,
    pathEditor,
    (commands) => {
      pathEditor.makeSegmentBendable(commands, afterIndex);
    },
    (resultIndex) => closesPath && resultIndex === original.length ? undefined : original[resultIndex],
  );
}

export function makeEditableSegmentStraight(
  path: EditablePath,
  afterSegmentID: string,
  pathEditor: PathEditor,
): boolean {
  const afterIndex = segmentIndex(path, afterSegmentID);
  if (afterIndex === null) return false;
  const original = [...path.segments];
  return mutateCommands(
    path,
    pathEditor,
    (commands) => {
      pathEditor.makeSegmentStraight(commands, afterIndex);
    },
    (resultIndex) => original[resultIndex],
  );
}

function snapEditableSegment(
  path: EditablePath,
  afterSegmentID: string,
  pathEditor: PathEditor,
  axis: "horizontal" | "vertical",
): boolean {
  const afterIndex = segmentIndex(path, afterSegmentID);
  if (afterIndex === null) return false;
  const original = [...path.segments];
  const closesPath = path.closed && afterIndex === original.length - 1;
  return mutateCommands(
    path,
    pathEditor,
    (commands) => {
      if (axis === "horizontal") pathEditor.snapSegmentHorizontal(commands, afterIndex);
      else pathEditor.snapSegmentVertical(commands, afterIndex);
    },
    (resultIndex) => closesPath && resultIndex === original.length ? undefined : original[resultIndex],
  );
}

export function snapEditableSegmentHorizontal(
  path: EditablePath,
  afterSegmentID: string,
  pathEditor: PathEditor,
): boolean {
  return snapEditableSegment(path, afterSegmentID, pathEditor, "horizontal");
}

export function snapEditableSegmentVertical(
  path: EditablePath,
  afterSegmentID: string,
  pathEditor: PathEditor,
): boolean {
  return snapEditableSegment(path, afterSegmentID, pathEditor, "vertical");
}

export function rotateEditablePath(
  path: EditablePath,
  angleRadians: number,
  pivot: Point,
  pathEditor: PathEditor,
): boolean {
  const original = [...path.segments];
  return mutateCommands(
    path,
    pathEditor,
    (commands) => pathEditor.rotatePath(commands, angleRadians, pivot),
    (resultIndex) => original[resultIndex],
  );
}
