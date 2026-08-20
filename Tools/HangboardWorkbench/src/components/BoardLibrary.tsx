import type { BoardSummary } from "../types.ts";

export interface BoardLibraryProps {
  boards: BoardSummary[];
  selectedBoardId: string | null;
  busy: boolean;
  error: string;
  onSelectBoard(boardId: string): void;
}

export function BoardLibrary({ boards, selectedBoardId, busy, error, onSelectBoard }: BoardLibraryProps) {
  return (
    <aside className="panel region-panel" aria-labelledby="boards-heading">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Library</span>
          <h2 id="boards-heading">Boards</h2>
        </div>
      </div>
      <p className={`opening-list-message${error ? "" : " hidden"}`} id="boards-error" role="alert">{error}</p>
      <div className="region-list" id="board-list" aria-live="polite">
        {boards.map((board) => (
          <button
            key={board.boardId}
            type="button"
            className={`region-item${selectedBoardId === board.boardId ? " selected" : ""}`}
            disabled={busy}
            onClick={() => onSelectBoard(board.boardId)}
          >
            <span className="region-key">{board.displayName}</span>
            <small className="region-type">{board.holdCount} holds</small>
          </button>
        ))}
      </div>
    </aside>
  );
}
import React from "react";
