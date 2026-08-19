import type { Board, EditorDocument } from "../types.ts";

export interface HoldCanvasProps {
  board: Board | null;
  document: EditorDocument | null;
  selectedKey: string | null;
  onSelectHold(key: string): void;
}

export function HoldCanvas({ board, document, selectedKey, onSelectHold }: HoldCanvasProps) {
  return (
    <div className="editor-views">
      <div className="canvas-viewport" id="canvas-viewport">
        <svg
          id="editor-svg"
          xmlns="http://www.w3.org/2000/svg"
          aria-label="Hangboard hold editor"
          viewBox={document ? `0 0 ${document.canvas.width} ${document.canvas.height}` : undefined}
          width={document?.canvas.width}
          height={document?.canvas.height}
        >
          <image
            id="board-image"
            x="0"
            y="0"
            preserveAspectRatio="none"
            href={board?.imageUrl}
            width={document?.canvas.width}
            height={document?.canvas.height}
          />
          <g id="hold-overlay">
            {document?.regions.map((hold) => (
              <path
                key={hold.key}
                className="region-shape"
                data-hold-key={hold.key}
                d={hold.displayPath}
                fill="#ff754f"
                fillOpacity={hold.key === selectedKey ? "0.58" : "0.3"}
                stroke={hold.key === selectedKey ? "#fff7dc" : "#ff754f"}
                strokeWidth={hold.key === selectedKey ? "2.2" : "1.4"}
                onClick={() => onSelectHold(hold.key)}
              />
            ))}
          </g>
        </svg>
        <div className={`empty-state${document ? " hidden" : ""}`} id="empty-state">
          <strong>Select a board</strong>
          <span>Its image and holds load together.</span>
        </div>
      </div>
    </div>
  );
}
