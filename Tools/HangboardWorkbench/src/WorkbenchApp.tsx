import React from "react";

import { holdCentroid } from "./editor-model.ts";
import type { HoldRegion, WorkbenchDependencies } from "./types.ts";
import { useWorkbench } from "./useWorkbench.ts";
import { useHoldEditor } from "./useHoldEditor.ts";
import { BoardLibrary } from "./components/BoardLibrary.tsx";
import { HoldCanvas, type Guide, type GuideAxis } from "./components/HoldCanvas.tsx";
import { HoldInspector } from "./components/HoldInspector.tsx";
import { RepositoryToolbar } from "./components/RepositoryToolbar.tsx";
import { ValidationPanel } from "./components/ValidationPanel.tsx";

export interface WorkbenchAppProps {
  dependencies: WorkbenchDependencies;
}

const MIN_CANVAS_ZOOM = 50;
const MAX_CANVAS_ZOOM = 300;
const CANVAS_ZOOM_STEP = 25;

export function WorkbenchApp({ dependencies }: WorkbenchAppProps) {
  const { state, actions } = useWorkbench(dependencies);
  const [canvasZoom, setCanvasZoom] = React.useState(100);
  const canvasZoomRef = React.useRef(canvasZoom);
  const [guides, setGuides] = React.useState<Guide[]>([]);
  const [mobileBoardsOpen, setMobileBoardsOpen] = React.useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [mobileHoldSheetOpen, setMobileHoldSheetOpen] = React.useState(false);
  const nextGuideId = React.useRef(1);
  const canZoomChange = React.useCallback((direction: number): boolean => {
    const step = Math.sign(direction) * CANVAS_ZOOM_STEP;
    const nextZoom = canvasZoomRef.current + step;
    return nextZoom >= MIN_CANVAS_ZOOM && nextZoom <= MAX_CANVAS_ZOOM;
  }, []);
  const changeCanvasZoom = React.useCallback((direction: number): boolean => {
    const step = Math.sign(direction) * CANVAS_ZOOM_STEP;
    const nextZoom = canvasZoomRef.current + step;
    if (!canZoomChange(direction)) return false;
    canvasZoomRef.current = nextZoom;
    setCanvasZoom(nextZoom);
    return true;
  }, [canZoomChange]);
  const busy = state.busyBoard || state.busyGit;
  const editorBusy = state.busyGit || (state.busyBoard && !state.savingBoard);
  const selectedHold: HoldRegion | null = state.document?.regions.find(
    (region) => region.key === state.selectedKey,
  ) ?? null;
  const selectedHoldCenter = state.document && selectedHold
    ? holdCentroid([selectedHold], dependencies.pathEditor)
    : null;
  React.useEffect(() => {
    setGuides([]);
  }, [state.board?.boardId]);
  React.useEffect(() => {
    setMobileHoldSheetOpen(false);
  }, [state.board?.boardId]);
  const addGuide = React.useCallback((axis: GuideAxis): void => {
    if (!selectedHoldCenter) return;
    setGuides((current) => [...current, {
      id: `guide-${nextGuideId.current++}`,
      axis,
      coordinate: axis === "horizontal" ? selectedHoldCenter.y : selectedHoldCenter.x,
    }]);
  }, [selectedHoldCenter]);
  const moveGuide = React.useCallback((id: string, coordinate: number): void => {
    setGuides((current) => current.map((guide) => (
      guide.id === id ? { ...guide, coordinate } : guide
    )));
  }, []);
  const editor = useHoldEditor({
    document: state.document,
    selectedHold,
    selectedKeys: state.selectedKeys,
    dirty: state.dirty,
    status: state.status,
    busy: editorBusy,
    rotationDegrees: state.rotationDegrees,
    actions,
    pathEditor: dependencies.pathEditor,
    validateEditorDocument: dependencies.controller.validateEditorDocument,
    dialogs: dependencies.dialogs,
    horizontalGuideYs: guides.filter((guide) => guide.axis === "horizontal").map((guide) => guide.coordinate),
    verticalGuideXs: guides.filter((guide) => guide.axis === "vertical").map((guide) => guide.coordinate),
  });
  const saveFromShortcut = React.useCallback(() => {
    if (busy || !state.board) return;
    editor.cancelActiveEdit();
    void actions.saveBoard();
  }, [actions, busy, editor, state.board]);
  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      const target = event.target instanceof Element ? event.target : null;
      const tag = target?.tagName.toLowerCase();
      const editable = (target instanceof HTMLElement && target.isContentEditable)
        || target?.getAttribute("contenteditable") === "true"
        || tag === "input" || tag === "select" || tag === "textarea";
      if (editable) return;
      if (event.metaKey && (event.key === "+" || event.key === "-")) {
        if (!state.document || busy) return;
        if (changeCanvasZoom(event.key === "+" ? 1 : -1)) event.preventDefault();
        return;
      }
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "s") return;
      if (busy || !state.board) return;
      event.preventDefault();
      saveFromShortcut();
    };
    window.document.addEventListener("keydown", onKeyDown);
    return () => window.document.removeEventListener("keydown", onKeyDown);
  }, [busy, changeCanvasZoom, saveFromShortcut, state.board, state.document]);
  const branchStatus = !state.initialized && !state.gitStatusKnown
    ? "Choose a board to edit its holds."
    : state.currentBranch
    ? `Current branch: ${state.currentBranch}`
    : state.gitStatusKnown
      ? "Detached HEAD"
      : "No branch detected";
  const saveState = !state.board
    ? "No board selected"
    : busy
      ? "Working…"
      : state.dirty
        ? "Unsaved changes"
        : "Saved";

  return (
    <main className="app-shell direct-workbench">
      <header className={`topbar${mobileMenuOpen ? " mobile-menu-open" : ""}`}>
        <div className="brand-block">
          <div className="brand-mark">H</div>
          <div>
            <h1>Hangboard Workbench</h1>
            <p id="board-status">{branchStatus}</p>
          </div>
        </div>
        <div className="toolbar" aria-label="Board tools">
          <button className="tool-button" id="refresh-boards-button" type="button" disabled={busy} onClick={() => void actions.refreshBoards()}>Boards</button>
          <span className="save-state" id="save-state" aria-live="polite">{saveState}</span>
          <button className="tool-button accent" id="save-button" type="button" disabled={!state.board || busy} onClick={saveFromShortcut}>Save</button>
          <label className="tool-button" htmlFor="autosave-toggle">
            <input
              id="autosave-toggle"
              type="checkbox"
              checked={state.autosaveEnabled}
              onChange={(event) => actions.setAutosaveEnabled(event.currentTarget.checked)}
            />
            Autosave
          </label>
          <span className="save-state" id="autosave-state" aria-live="polite">
            {state.autosaveEnabled ? "Autosave on" : "Autosave off"}
          </span>
        </div>
        <div className="mobile-toolbar" aria-label="Mobile board tools">
          <button className="tool-button" id="mobile-boards-button" type="button" aria-expanded={mobileBoardsOpen} onClick={() => setMobileBoardsOpen((open) => !open)}>Boards</button>
          <button className="tool-button" id="mobile-menu-button" type="button" aria-expanded={mobileMenuOpen} onClick={() => setMobileMenuOpen((open) => !open)}>Menu</button>
          <button className="tool-button accent" id="mobile-save-button" type="button" disabled={!state.board || busy} onClick={saveFromShortcut}>Save</button>
        </div>
        <RepositoryToolbar state={state} actions={actions} />
      </header>

      <section className={`workspace-grid${mobileBoardsOpen ? " mobile-boards-open" : ""}`}>
        <BoardLibrary
          boards={state.boards}
          selectedBoardId={state.board?.boardId ?? null}
          busy={busy}
          error={state.boardsError}
          onSelectBoard={(boardId) => {
            setMobileBoardsOpen(false);
            void actions.selectBoard(boardId);
          }}
        />

        <section className="canvas-column" aria-label="Hold editor">
          <div className="canvas-header">
            <div className="editor-heading">
              <span className="eyebrow">Board</span>
              <strong id="board-name">{state.board?.displayName ?? "No board selected"}</strong>
            </div>
            <div className="canvas-controls" aria-label="Canvas controls">
              <button
                className="tool-button"
                id="zoom-out-button"
                type="button"
                aria-label="Zoom out"
                disabled={!state.document || canvasZoom <= MIN_CANVAS_ZOOM}
                onClick={() => changeCanvasZoom(-1)}
              >−</button>
              <output id="canvas-zoom-level" aria-live="polite">{canvasZoom}%</output>
              <button
                className="tool-button"
                id="zoom-in-button"
                type="button"
                aria-label="Zoom in"
                disabled={!state.document || canvasZoom >= MAX_CANVAS_ZOOM}
                onClick={() => changeCanvasZoom(1)}
              >+</button>
              <button className="tool-button accent" id="add-hold-button" type="button" disabled={!state.document || editorBusy} onClick={editor.addHold}>Add hold</button>
              <button className="tool-button" id="add-horizontal-guide-button" type="button" disabled={!selectedHold || editorBusy} onClick={() => addGuide("horizontal")}>Horizontal guide</button>
              <button className="tool-button" id="add-vertical-guide-button" type="button" disabled={!selectedHold || editorBusy} onClick={() => addGuide("vertical")}>Vertical guide</button>
              <button className="tool-button" id="clear-guides-button" type="button" disabled={guides.length === 0 || editorBusy} onClick={() => setGuides([])}>Clear guides</button>
            </div>
          </div>
          <HoldCanvas
            board={state.board}
            document={state.document}
            selectedKey={state.selectedKey}
            selectedKeys={state.selectedKeys}
            busy={editorBusy}
            onSelectHold={(key, toggle) => {
              actions.selectHold(key, toggle);
            }}
            pathEditor={dependencies.pathEditor}
            editor={editor}
            zoomPercent={canvasZoom}
            onZoomChange={changeCanvasZoom}
            canZoomChange={canZoomChange}
            guides={guides}
            onMoveGuide={moveGuide}
          />
          <ValidationPanel validation={state.validation} />
          <footer className="statusbar">
            <span id="editor-status">
              {state.status}
              {state.saveLoginUrl && <>{" "}<a href={state.saveLoginUrl} target="_blank" rel="noopener noreferrer">Reauthenticate</a></>}
            </span>
          </footer>
          <div className="mobile-canvas-controls" aria-label="Mobile canvas controls">
            <button className="tool-button" id="mobile-zoom-out-button" type="button" aria-label="Zoom out" disabled={!state.document || canvasZoom <= MIN_CANVAS_ZOOM} onClick={() => changeCanvasZoom(-1)}>−</button>
            <button className="tool-button" id="mobile-zoom-in-button" type="button" aria-label="Zoom in" disabled={!state.document || canvasZoom >= MAX_CANVAS_ZOOM} onClick={() => changeCanvasZoom(1)}>+</button>
            <button className="tool-button" id="mobile-open-hold-sheet-button" type="button" disabled={!selectedHold} onClick={() => setMobileHoldSheetOpen(true)}>Edit hold</button>
            <button className="tool-button accent" id="mobile-add-hold-button" type="button" disabled={!state.document || editorBusy} onClick={editor.addHold}>Add hold</button>
          </div>
        </section>

        <HoldInspector
          className={selectedHold && mobileHoldSheetOpen ? "mobile-sheet-open" : ""}
          hold={selectedHold}
          selectedCount={state.selectedKeys.length}
          busy={editorBusy}
          rotationDegrees={state.rotationDegrees}
          onRotationDegreesChange={actions.setRotationDegrees}
          onTypeChange={editor.changeHoldType}
          onFingerCapacityChange={editor.changeFingerCapacity}
          onOutlineShapeChange={editor.changeOutlineShape}
          onRotate={(direction, shiftKey) => editor.rotateHold(direction * (shiftKey ? 45 : 15))}
          onApplyRotation={editor.applyRotation}
          onDelete={editor.deleteHold}
          onMobileCollapse={() => setMobileHoldSheetOpen(false)}
        />
      </section>
    </main>
  );
}
