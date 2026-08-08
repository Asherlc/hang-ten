# Local Hangboard Workbench Design

**Date:** 2026-08-06

## Summary

Build a local browser workbench that guides one hangboard through the existing onboarding pipeline. The workbench runs automatically to each visual checkpoint, pauses for human review or refinement, and continues after approval. It uses the same orchestration and artifact contracts as the CLI, saves approved work to the local filesystem-backed pipeline store, and leaves synchronization to Hang Ten to a separate future command.

## Goals

- Let a user start onboarding with a commercial product name and either an image URL or a local image upload.
- Present one active board as a guided sequence of visual checkpoints.
- Support manual refinement of coarse hold contours before smoothing and exact vector paths after smoothing.
- Make rotation, bending, resizing, per-corner treatment, control-point editing, mirroring, undo, and redo efficient enough to trace complex boards.
- Preserve generated inputs, attempts, edits, approvals, and revision history without destructive overwrites.
- Let the UI and CLI start or resume the same runs.
- Apply one product-neutral workflow to materially different commercial hangboards.

## Non-goals

- Syncing or publishing boards to Hang Ten.
- Reimplementing detection, cleanup, smoothing, or rendering in the browser.
- Adding product-specific templates, coordinates, masks, hold inventories, or tuning paths.
- Introducing a database or remote service.
- Supporting simultaneous mutation of the same board by multiple clients.

## User Experience

The workbench focuses on one active board and provides a compact recent-runs picker. The main layout has:

- A left stage timeline and recent-runs list.
- A central visual review or editing canvas.
- A contextual inspector for the selected region.
- Persistent undo, comparison, draft status, and approval controls.

The stages are:

1. Input
2. Source review
3. Cleanup review
4. Hold-contour refinement
5. Smoothing
6. Vector refinement
7. Save

Creating a run requires a commercial product name plus either an image URL or a local upload. The workbench runs automatically until the next visual checkpoint. Selecting **Approve & continue** seals the current revision and immediately starts work toward the next checkpoint. Browser refreshes and closures do not cancel pipeline jobs.

## Architecture

### Loopback server

The existing local editor server becomes a thin workbench server. It owns filesystem access, job lifecycle, catalog queries, draft writes, approval transitions, and status delivery to the browser. It invokes shared Python orchestration APIs rather than reproducing pipeline behavior or parsing shell output.

Only one mutating job may operate on a board at a time. Independent boards may run concurrently. The browser receives current job state through a lightweight status endpoint or server-sent event stream and can reconnect after a refresh.

### Shared orchestration

The current CLI behavior remains the canonical compatibility contract. Pipeline operations move behind or continue to use a shared Python API that both the CLI and workbench call. Runs created by either interface must be discoverable and resumable by the other.

### Browser application

The browser renders pipeline artifacts and provides stage-specific editing tools. It does not perform authoritative detection, smoothing, or final rendering. Draft edits are sent to the server and written alongside, never over, generated artifacts.

### Filesystem-backed store

Each run retains its immutable source, stage attempts, draft edits, approvals, and manifest. The manifest identifies:

- The board and source identity.
- The current lineage and active stage attempt.
- Approval status at each checkpoint.
- Which downstream attempts are current or stale.
- The currently saved board revision, if any.

The store remains inspectable without the UI. No database is introduced.

## Editing Modes

### Contour refinement

The contour editor changes Stage 2 logical hold geometry and inventory. It is used to add, remove, classify, align, and roughly shape every usable grip before smoothing.

### Vector refinement

The vector editor changes the exact Stage 3 display paths that appear in the final illustration. It is the WYSIWYG polish step for correcting small alignment, curvature, corner, and edge discrepancies after automated smoothing.

Both modes share selection, transform, shape, curve, mirror, undo, redo, comparison, and visibility controls. Their writes remain distinct so an exact visual correction cannot be mistaken for a new detection contour.

## Data and Revision Flow

1. The server records the product name, caches an immutable source image, and creates a run manifest.
2. Shared orchestration advances the run until it creates the next review artifact.
3. The browser displays the artifact and stage-appropriate editor.
4. Manual changes autosave as a draft revision separate from generated files.
5. Approval validates and seals that revision, updates the manifest, and launches the next pipeline work.
6. Editing an approved upstream stage forks a new lineage. Prior downstream attempts remain available but are marked stale and cannot become the current saved version accidentally.
7. Final **Save** validates a complete lineage and records it as the board's current approved local version.

Save is not an export or publish action. A later, separate command will read saved board versions and synchronize them to Hang Ten.

## Geometry Validation

Approval is blocked when a region violates its stage's geometry contract. Errors identify and select the affected region. Validation includes required stable IDs, valid closed paths where required, usable bounds, finite coordinates, and prohibited self-intersections. The editor should not silently normalize geometry in a way that changes the approved shape.

## Failure and Recovery

- A failed stage stops at that stage and leaves all earlier approvals intact.
- Retry creates a new attempt using the same inputs; it does not overwrite the failed attempt.
- The cached source permits resumption if an original URL later becomes unavailable.
- Reopening a run reconnects to current job status and restores the latest draft.
- A manifest or artifact changed outside the UI triggers a reload/conflict state instead of a blind overwrite.
- The UI explains actionable errors beside the review canvas and retains detailed logs for diagnosis.
- Save is atomic: the manifest either points to the newly approved lineage or continues pointing to the prior saved version.

## Verification

### Unit checks

Cover manifests, revision lineage, stale-descendant propagation, atomic save behavior, geometry validation, and job-state transitions.

### API checks

Cover creating runs from URL and upload sources; starting, reconnecting to, retrying, and resuming stages; autosaving drafts; approving checkpoints; reopening runs; and saving final lineages.

### Editor checks

Cover selection, movement, resizing, rotation, bending, per-corner treatment, control-point editing, mirroring, add/remove operations, comparison, visibility, undo/redo, and the separation between contour and vector editing.

### End-to-end checks

Replay the same workflow and code paths against Beastmaker 1000, Metolius Wood Grips Compact II, and Metolius Simulator 3D. These are validation fixtures, not product-specific production branches. Existing CLI workflows must continue to work and must resume runs created in the UI.

Schema and deterministic-render snapshots catch mechanical regressions. Human visual review remains authoritative for subjective hold accuracy and illustration quality.

## Acceptance Criteria

- A user can create a run from a named product and URL or uploaded image.
- The run advances automatically to every visual checkpoint and pauses there.
- A user can efficiently correct all logical holds, approve smoothing, and polish exact final vectors.
- Refreshing or closing the browser loses neither running work nor saved drafts.
- Revising an earlier stage preserves history and prevents stale descendants from being saved as current.
- Final Save records a complete approved lineage locally without exporting or syncing it.
- The CLI can discover and resume UI-created runs, and the UI can discover and resume CLI-created runs.
- The same production implementation handles all three validation boards without product-specific logic or data embedded in code.
