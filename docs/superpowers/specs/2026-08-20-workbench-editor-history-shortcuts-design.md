# Workbench Editor History and Shortcuts Design

## Goal

Add local undo and redo for Hangboard Workbench document edits and provide standard cross-platform editor shortcuts without changing the saved board format or server API.

## Scope

The editor will support `Command/Ctrl+Z` for undo, `Command/Ctrl+Shift+Z` and `Ctrl+Y` for redo, `Command/Ctrl+S` for saving, and `Escape` for cancelling an active pointer drag. Document revisions are local to the currently opened board and are discarded when a board is loaded or saved.

The feature applies to committed geometry and metadata edits: add/delete, hold-type changes, outline changes, rotations, arrow nudges, vertex edits, and completed pointer drags. Multiple preview updates during one pointer drag are represented by one undo step. No history data is persisted in `board.json` or sent to the server.

## Architecture

`useWorkbench` will own a bounded in-memory history adjacent to the editable document. It records immutable snapshots before successful document changes and exposes undo and redo actions. Applying either action replaces the active document, retains the current selected hold when it still exists, marks the board dirty, clears stale validation messages, and reports an editor status. A new document change after undo clears the redo stack.

`useHoldEditor` remains responsible for document-level editing keyboard handling. It will call the Workbench undo/redo actions for the revision shortcuts and continue to leave native keyboard behavior untouched inside inputs, selects, textareas, and content-editable elements. Escape restores an active drag using the existing pointer-drag snapshot; it has no effect when no drag is active.

`WorkbenchApp` will own the save shortcut because it coordinates the active drag cancellation with the asynchronous save action. It will register and clean up a document-level keyboard listener that ignores editable targets and does nothing while an operation is busy or no board is selected.

## Error Handling

Undo and redo are no-ops when their corresponding stack is empty. Keyboard handlers only call `preventDefault` when they perform an editor action, so the browser and form controls retain their standard behavior otherwise. Save failures retain the unsaved document and local history. History resets on successful board load and save, preventing revisions from crossing a durable save boundary or board identity.

## Testing

React editor tests will first assert each shortcut's observable behavior:

1. Undo and redo reverse/reapply a document edit via macOS and Windows/Linux shortcut variants.
2. A new edit after undo invalidates redo.
3. A drag becomes a single undoable operation rather than one revision per pointer move, and Escape restores its pointer-down geometry.
4. Keyboard shortcuts leave text-entry targets untouched.
5. Command/Ctrl+S invokes save once, cancels an active drag first, and does not act with no selected board or while busy.

The existing typecheck, module tests, React tests, and bundle freshness check remain the verification suite.

## Acceptance Criteria

- Standard undo, redo, save, and Escape shortcuts work across supported desktop platforms.
- Every finished document edit can be undone and redone exactly once per action, including pointer drags.
- History is document-local, bounded, and never serialized.
- Existing native typing and form-control keyboard behavior remains intact.
- The Workbench frontend typecheck, test suite, and bundle check pass.
