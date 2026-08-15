# Direct Board Editor Design

## Goal

Make every selected hangboard immediately editable with its packaged hold geometry. The Workbench must not present boards as pipeline runs or show an empty hold editor for a completed board.

## Root Cause

The repository-library adapter materializes published packages as completed Stage 4 workspace revisions. `loadCheckpoint` only populates editor regions for editable Stages 2 and 3, so a completed package reaches the editor with an image but an empty hold collection.

The installed native app can also be built from a different commit than its selected checkout. The old runtime and newer checkout can disagree about board HTTP resources, leaving the opening screen with the unhelpful `Could not load boards` message.

## Design

### Direct package-backed board documents

Repository boards will expose a canonical editor document derived from the package's source-backed `board.json` and `artwork.json`: canvas, image, and one display-path hold per packaged hold piece. The board API will return a dedicated document URL rather than requiring the client to infer a pipeline artifact path from a review image.

Opening a repository board will return that direct editor view. The Workbench will load the returned document regardless of whether the board has been previously saved. Existing workspace boards remain readable and preserve their current draft/save behavior.

### Focused board language

The visible editor and opening screen will refer only to boards, holds, and saved work. `Recent runs`, session/run IDs, and generated-run status text will be removed from the guided editor. Legacy command-line import/catalog support may retain internal compatibility names, but those names will not surface in the product UI or its primary board-loading path.

### Failure handling

The native shell will check its embedded backend identity against the selected checkout before opening the web editor. If they differ, it will show a specific update/rebuild message rather than launching a backend whose API contract may not match the checkout. Board-document fetch failures will retain the loaded board state and show a clear, board-specific error; they will never be represented as an empty collection.

## Data Flow

1. The opening screen requests the repository board collection.
2. Selecting a board returns a public board view with an editor image URL and an explicit editor-document URL.
3. The editor fetches that document, verifies image/canvas alignment, and installs its holds.
4. Save writes a revision or package-backed draft according to the existing workspace ownership rules.

## Testing

- An API test proves a published package exposes a direct editor document with the package hold count.
- A browser-model test proves document loading uses the explicit URL and does not replace a populated editor with zero holds on a fetch failure.
- UI tests assert that guided editor copy has no user-visible run terminology.
- Native-shell tests cover checkout/runtime identity mismatch handling.
