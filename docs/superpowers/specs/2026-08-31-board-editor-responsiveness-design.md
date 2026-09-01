# Board Editor Responsiveness Design

## Problem

The board editor is slow when selecting or changing boards. The picker currently
constructs every row and synchronously decodes each presentation image in the
SwiftUI render path. Opening a selected board also copies and decodes its local
package synchronously while `BoardEditorScreen` is initialized. The catalog has
61 packages, and individual presentation images are as large as 2.4 MB.

## Goals

- Keep board-picker rendering independent of synchronous image decoding.
- Only request thumbnails for rows SwiftUI has made visible.
- Move selected-package preparation and loading off the main actor so navigation
  can present a responsive loading state.
- Preserve the existing editable package format, local-copy semantics, error
  message, and editor behavior once a board has loaded.
- Provide automated coverage for the loading-state behavior and retain package
  store validation coverage.

## Non-goals

- Change board package contents or remove non-default presentation assets.
- Change editing, persistence, GitHub sync, or geometry behavior.
- Add image generation, image analysis, or automatic geometry processing.

## Design

Replace the eager picker stack with a lazy stack and move thumbnail decoding
into a thumbnail view whose task is keyed by the asset URL. It displays the
existing neutral placeholder until decoding has completed.

Route board navigation through a loading screen. The screen starts package
copying and document/image preparation on a background queue, publishes a
loaded package or the existing failure state on the main actor, and creates
`BoardEditorScreen` only after loading finishes. This removes filesystem I/O,
JSON decoding, PNG validation, and image decoding from SwiftUI view-body and
destination initialization.
