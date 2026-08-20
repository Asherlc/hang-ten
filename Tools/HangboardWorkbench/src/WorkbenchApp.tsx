import React from "react";

import type { HoldRegion, WorkbenchDependencies } from "./types.ts";
import { useWorkbench } from "./useWorkbench.ts";
import { useHoldEditor } from "./useHoldEditor.ts";
import { BoardLibrary } from "./components/BoardLibrary.tsx";
import { HoldCanvas } from "./components/HoldCanvas.tsx";
import { HoldInspector } from "./components/HoldInspector.tsx";
import { RepositoryToolbar } from "./components/RepositoryToolbar.tsx";
import { ValidationPanel } from "./components/ValidationPanel.tsx";

export interface WorkbenchAppProps {
  dependencies: WorkbenchDependencies;
}

export function WorkbenchApp({ dependencies }: WorkbenchAppProps) {
  const { state, actions } = useWorkbench(dependencies);
  const busy = state.busyBoard || state.busyGit;
  const selectedHold: HoldRegion | null = state.document?.regions.find(
    (region) => region.key === state.selectedKey,
  ) ?? null;
  const editor = useHoldEditor({
    document: state.document,
    selectedHold,
    dirty: state.dirty,
    status: state.status,
    rotationDegrees: state.rotationDegrees,
    actions,
    pathEditor: dependencies.pathEditor,
    validateEditorDocument: dependencies.controller.validateEditorDocument,
    dialogs: dependencies.dialogs,
  });
  const branchStatus = state.status === "Ready." && !state.gitStatusKnown
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
      <header className="topbar">
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
          <button className="tool-button accent" id="save-button" type="button" disabled={!state.board || busy} onClick={() => void actions.saveBoard()}>Save</button>
        </div>
        <RepositoryToolbar state={state} actions={actions} />
      </header>

      <section className="workspace-grid">
        <BoardLibrary
          boards={state.boards}
          selectedBoardId={state.board?.boardId ?? null}
          busy={busy}
          error={state.boardsError}
          onSelectBoard={(boardId) => void actions.selectBoard(boardId)}
        />

        <section className="canvas-column" aria-label="Hold editor">
          <div className="canvas-header">
            <div className="editor-heading">
              <span className="eyebrow">Board</span>
              <strong id="board-name">{state.board?.displayName ?? "No board selected"}</strong>
            </div>
            <button className="tool-button accent" id="add-hold-button" type="button" disabled={!state.document || busy} onClick={editor.addHold}>Add hold</button>
          </div>
          <HoldCanvas
            board={state.board}
            document={state.document}
            selectedKey={state.selectedKey}
            onSelectHold={actions.selectHold}
            pathEditor={dependencies.pathEditor}
            editor={editor}
          />
          <ValidationPanel validation={state.validation} />
          <footer className="statusbar"><span id="editor-status">{state.status}</span></footer>
        </section>

        <HoldInspector
          hold={selectedHold}
          rotationDegrees={state.rotationDegrees}
          onRotationDegreesChange={actions.setRotationDegrees}
          onTypeChange={editor.changeHoldType}
          onRotate={(direction, shiftKey) => editor.rotateHold(direction * (shiftKey ? 45 : 15))}
          onApplyRotation={editor.applyRotation}
          onDelete={editor.deleteHold}
        />
      </section>
    </main>
  );
}
