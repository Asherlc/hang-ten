import React from "react";

import { contactCentroid } from "./editor-model.ts";
import type { ContactRegion, WorkbenchDependencies } from "./types.ts";
import { useWorkbench } from "./useWorkbench.ts";
import { useContactEditor } from "./useContactEditor.ts";
import { BoardLibrary } from "./components/BoardLibrary.tsx";
import { ContactCanvas, type Guide, type GuideAxis } from "./components/ContactCanvas.tsx";
import { ContactInspector } from "./components/ContactInspector.tsx";
import { RepositoryToolbar } from "./components/RepositoryToolbar.tsx";
import { ValidationPanel } from "./components/ValidationPanel.tsx";
import { ApiErrorAlert } from "./components/ApiErrorAlert.tsx";

export interface WorkbenchAppProps {
  dependencies: WorkbenchDependencies;
}

const MIN_CANVAS_ZOOM = 50;
const MAX_CANVAS_ZOOM = 300;
const CANVAS_ZOOM_STEP = 25;
const CANVAS_PINCH_ZOOM_STEP = 10;
const CANVAS_BACKGROUNDS = [
  { label: "Cream", value: "#d6d7d3" },
  { label: "White", value: "#ffffff" },
  { label: "Charcoal", value: "#292b2e" },
] as const;

export function WorkbenchApp({ dependencies }: WorkbenchAppProps) {
  const { state, actions } = useWorkbench(dependencies);
  const [canvasZoom, setCanvasZoom] = React.useState(100);
  const [canvasBackground, setCanvasBackground] = React.useState("#d6d7d3");
  const canvasZoomRef = React.useRef(canvasZoom);
  const [guides, setGuides] = React.useState<Guide[]>([]);
  const [mobileBoardsOpen, setMobileBoardsOpen] = React.useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [mobileContactSheetOpen, setMobileContactSheetOpen] = React.useState(false);
  const nextGuideId = React.useRef(1);
  const nextCanvasZoom = React.useCallback((direction: number, stepSize: number): number => {
    const step = Math.sign(direction) * stepSize;
    return Math.max(MIN_CANVAS_ZOOM, Math.min(MAX_CANVAS_ZOOM, canvasZoomRef.current + step));
  }, []);
  const canCanvasZoomChange = React.useCallback((direction: number, stepSize: number): boolean => {
    return nextCanvasZoom(direction, stepSize) !== canvasZoomRef.current;
  }, [nextCanvasZoom]);
  const changeCanvasZoomBy = React.useCallback((direction: number, stepSize: number): boolean => {
    const nextZoom = nextCanvasZoom(direction, stepSize);
    if (!canCanvasZoomChange(direction, stepSize)) return false;
    canvasZoomRef.current = nextZoom;
    setCanvasZoom(nextZoom);
    return true;
  }, [canCanvasZoomChange, nextCanvasZoom]);
  const canZoomChange = React.useCallback((direction: number): boolean => (
    canCanvasZoomChange(direction, CANVAS_ZOOM_STEP)
  ), [canCanvasZoomChange]);
  const changeCanvasZoom = React.useCallback((direction: number): boolean => (
    changeCanvasZoomBy(direction, CANVAS_ZOOM_STEP)
  ), [changeCanvasZoomBy]);
  const canPinchZoomChange = React.useCallback((direction: number): boolean => (
    canCanvasZoomChange(direction, CANVAS_PINCH_ZOOM_STEP)
  ), [canCanvasZoomChange]);
  const changeCanvasPinchZoom = React.useCallback((direction: number): boolean => (
    changeCanvasZoomBy(direction, CANVAS_PINCH_ZOOM_STEP)
  ), [changeCanvasZoomBy]);
  const busy = state.busyBoard || state.busyGit;
  const editorBusy = state.busyGit || (state.busyBoard && !state.savingBoard);
  const selectedPresentation = state.board?.presentations?.find(
    (presentation) => presentation.presentationID === state.board?.selectedPresentationID,
  );
  const selectedRegion: ContactRegion | null = state.document?.regions.find(
    (region) => region.key === state.selectedKey,
  ) ?? null;
  const selectedContact = state.document && selectedRegion
    ? state.document.contacts.find((contact) => contact.id === selectedRegion.metadata.contactID) ?? null
    : null;
  const gastonPairCandidates = state.document && selectedContact
    ? state.document.contacts
      .filter((contact) => (
        contact.kind === "gaston"
        && contact.id !== selectedContact.id
        && contact.pairedContactID === undefined
      ))
      .map((contact) => contact.id)
    : [];
  const selectedContactCenter = state.document && selectedRegion
    ? contactCentroid([selectedRegion], dependencies.pathEditor)
    : null;
  React.useEffect(() => {
    setGuides([]);
  }, [state.board?.boardId, state.board?.selectedPresentationID]);
  React.useEffect(() => {
    setMobileContactSheetOpen(false);
  }, [state.board?.boardId, state.board?.selectedPresentationID]);
  const addGuide = React.useCallback((axis: GuideAxis): void => {
    if (!selectedContactCenter) return;
    setGuides((current) => [...current, {
      id: `guide-${nextGuideId.current++}`,
      axis,
      coordinate: axis === "horizontal" ? selectedContactCenter.y : selectedContactCenter.x,
    }]);
  }, [selectedContactCenter]);
  const moveGuide = React.useCallback((id: string, coordinate: number): void => {
    setGuides((current) => current.map((guide) => (
      guide.id === id ? { ...guide, coordinate } : guide
    )));
  }, []);
  const editor = useContactEditor({
    document: state.document,
    selectedRegion: selectedRegion,
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
    ? "Choose a board to edit its contacts."
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

        <section className="canvas-column" aria-label="Contact editor">
          <div className="canvas-header">
            <div className="editor-heading">
              <span className="eyebrow">Board</span>
              <strong id="board-name">{state.board?.displayName ?? "No board selected"}</strong>
            </div>
            <div className="canvas-controls" aria-label="Canvas controls">
              <label className="canvas-background-selector" htmlFor="canvas-background-select">
                <span>Background</span>
                <select
                  id="canvas-background-select"
                  value={canvasBackground}
                  onChange={(event) => setCanvasBackground(event.target.value)}
                >
                  {CANVAS_BACKGROUNDS.map((background) => (
                    <option key={background.value} value={background.value}>{background.label}</option>
                  ))}
                </select>
              </label>
              {(state.board?.presentations?.length ?? 0) > 1 && (
                <div className="surface-controls">
                  <label className="surface-selector" htmlFor="presentation-select">
                    <span>Surface</span>
                    <select
                      id="presentation-select"
                      aria-label="Board surface"
                      value={state.board?.selectedPresentationID ?? ""}
                      disabled={busy}
                      onChange={(event) => void actions.selectPresentation(event.target.value)}
                    >
                      {state.board?.presentations?.map((presentation) => (
                        <option
                          key={presentation.presentationID}
                          value={presentation.presentationID}
                        >{presentation.displayName}</option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="tool-button danger"
                    id="delete-presentation-button"
                    type="button"
                    disabled={busy || Boolean(selectedPresentation?.sourcePresentationID)}
                    aria-describedby={selectedPresentation?.sourcePresentationID
                      ? "delete-presentation-alias-hint"
                      : undefined}
                    onClick={() => void actions.deletePresentation()}
                  >Delete surface</button>
                  {selectedPresentation?.sourcePresentationID && (
                    <small id="delete-presentation-alias-hint" className="region-type">
                      Alias surfaces are deleted with their canonical source.
                    </small>
                  )}
                </div>
              )}
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
              <button className="tool-button" id="add-horizontal-guide-button" type="button" disabled={!selectedRegion || editorBusy} onClick={() => addGuide("horizontal")}>Horizontal guide</button>
              <button className="tool-button" id="add-vertical-guide-button" type="button" disabled={!selectedRegion || editorBusy} onClick={() => addGuide("vertical")}>Vertical guide</button>
              <button className="tool-button" id="clear-guides-button" type="button" disabled={guides.length === 0 || editorBusy} onClick={() => setGuides([])}>Clear guides</button>
              <button className="tool-button accent" id="add-contact-button" type="button" disabled={!state.document || editorBusy} onClick={editor.addContact}>Add contact</button>
            </div>
          </div>
          <ContactCanvas
            board={state.board}
            document={state.document}
            selectedKey={state.selectedKey}
            selectedKeys={state.selectedKeys}
            busy={editorBusy}
            onSelectContact={(key, toggle) => {
              actions.selectContact(key, toggle);
            }}
            pathEditor={dependencies.pathEditor}
            editor={editor}
            zoomPercent={canvasZoom}
            backgroundColor={canvasBackground}
            onZoomChange={changeCanvasZoom}
            canZoomChange={canZoomChange}
            onPinchZoomChange={changeCanvasPinchZoom}
            canPinchZoomChange={canPinchZoomChange}
            guides={guides}
            onMoveGuide={moveGuide}
          />
          <ApiErrorAlert error={state.apiError} />
          <ValidationPanel validation={state.validation} />
          <footer className="statusbar">
            <span id="editor-status">
              {state.status}
              {state.saveLoginUrl && <>{" "}<a href={state.saveLoginUrl} target="_blank" rel="noopener noreferrer">Reauthenticate</a></>}
            </span>
          </footer>
          <div className="mobile-canvas-controls" aria-label="Mobile canvas controls">
            <label className="canvas-background-selector" htmlFor="mobile-canvas-background-select">
              <span>Background</span>
              <select
                id="mobile-canvas-background-select"
                value={canvasBackground}
                onChange={(event) => setCanvasBackground(event.target.value)}
              >
                {CANVAS_BACKGROUNDS.map((background) => (
                  <option key={background.value} value={background.value}>{background.label}</option>
                ))}
              </select>
            </label>
            <button className="tool-button" id="mobile-zoom-out-button" type="button" aria-label="Zoom out" disabled={!state.document || canvasZoom <= MIN_CANVAS_ZOOM} onClick={() => changeCanvasZoom(-1)}>−</button>
            <button className="tool-button" id="mobile-zoom-in-button" type="button" aria-label="Zoom in" disabled={!state.document || canvasZoom >= MAX_CANVAS_ZOOM} onClick={() => changeCanvasZoom(1)}>+</button>
            <button className="tool-button accent" id="mobile-add-contact-button" type="button" disabled={!state.document || editorBusy} onClick={editor.addContact}>Add contact</button>
            <button className="tool-button" id="mobile-open-contact-sheet-button" type="button" disabled={!selectedRegion} onClick={() => setMobileContactSheetOpen(true)}>Edit contact</button>
          </div>
        </section>

        <ContactInspector
          className={selectedRegion && mobileContactSheetOpen ? "mobile-sheet-open" : ""}
          region={selectedRegion}
          contact={selectedContact}
          selectedCount={state.selectedKeys.length}
          busy={editorBusy}
          rotationDegrees={state.rotationDegrees}
          onRotationDegreesChange={actions.setRotationDegrees}
          onContactChange={(updated) => {
            if (!state.document) return;
            const previous = state.document.contacts.find((contact) => contact.id === updated.id);
            if (!previous) return;
            if (previous.kind !== updated.kind) {
              const selectedContactIDs = [...new Set(state.selectedKeys.flatMap((key) => {
                const region = state.document?.regions.find((candidate) => candidate.key === key);
                return region ? [region.metadata.contactID] : [];
              }))];
              if (updated.kind === "gaston") {
                if (selectedContactIDs.length !== 2) {
                  actions.replaceDocument(state.document, {
                    dirty: state.dirty,
                    validation: "Select exactly two physical contacts with two distinct contact IDs to create a Gaston pair.",
                    status: "Gaston conversion needs two distinct contact IDs.",
                  });
                  return;
                }
                const selected = new Set(selectedContactIDs);
                const displaced = state.document.contacts.find((contact) => (
                  !selected.has(contact.id)
                  && contact.pairedContactID !== undefined
                  && selected.has(contact.pairedContactID)
                ));
                if (displaced) {
                  actions.replaceDocument(state.document, {
                    dirty: state.dirty,
                    validation: `Creating this Gaston pair would orphan paired Gaston contact ${displaced.id}. Select it instead or recategorize it first.`,
                    status: "Gaston conversion would orphan an existing pair.",
                  });
                  return;
                }
                actions.editDocument((candidate) => {
                  const [firstID, secondID] = selectedContactIDs as [string, string];
                  for (const contact of candidate.contacts) {
                    if (contact.id === firstID) Object.assign(contact, { kind: "gaston", pairedContactID: secondID });
                    if (contact.id === secondID) Object.assign(contact, { kind: "gaston", pairedContactID: firstID });
                  }
                }, { status: "Contacts recategorized. Save when ready." });
                return;
              }
              const selected = new Set(selectedContactIDs);
              actions.editDocument((candidate) => {
                for (const contact of candidate.contacts) {
                  if (selected.has(contact.id)) {
                    contact.kind = updated.kind;
                    delete contact.pairedContactID;
                  } else if (contact.pairedContactID && selected.has(contact.pairedContactID)) {
                    delete contact.pairedContactID;
                  }
                }
              }, { status: "Contacts recategorized. Save when ready." });
              return;
            }
            actions.editDocument((candidate) => {
              const index = candidate.contacts.findIndex((contact) => contact.id === updated.id);
              if (index < 0) return;
              const previous = candidate.contacts[index]!;
              candidate.contacts[index] = updated;
              if (previous.pairedContactID && previous.pairedContactID !== updated.pairedContactID) {
                const previousPair = candidate.contacts.find((contact) => contact.id === previous.pairedContactID);
                if (previousPair?.pairedContactID === updated.id) delete previousPair.pairedContactID;
              }
              if (updated.pairedContactID) {
                const pair = candidate.contacts.find((contact) => contact.id === updated.pairedContactID);
                if (pair) pair.pairedContactID = updated.id;
              }
            }, { status: "Contact facts changed. Save when ready." });
          }}
          gastonPairCandidates={gastonPairCandidates}
          onDisplayPathChange={editor.changeDisplayPath}
          onTreatmentChange={editor.changeTreatment}
          onOutlineShapeChange={editor.changeOutlineShape}
          onRotate={(direction, shiftKey) => editor.rotateContact(direction * (shiftKey ? 45 : 15))}
          onApplyRotation={editor.applyRotation}
          onAddSegment={editor.addContactPiece}
          onDuplicateAndMirror={editor.duplicateAndMirrorContact}
          onDelete={editor.deleteContact}
          onMobileCollapse={() => setMobileContactSheetOpen(false)}
        />
      </section>
    </main>
  );
}
