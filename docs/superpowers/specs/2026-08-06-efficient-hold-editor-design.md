# Efficient Hold Editor Design

## Goal

Reduce careful tracing of a complex commercial board such as the Metolius Simulator 3D from roughly 30–60 minutes to a practical target of 15–20 minutes, without product-specific geometry or changing the Stage 2 artifact contract.

## Approach

Use a hybrid editor. Object-level transforms handle most corrections quickly; sparse smooth contours handle irregular holds; symmetry tools eliminate repeated work; optional local edge snapping assists placement without becoming authoritative. A geometry-only approach would remain slow on photo boundaries, while automatic segmentation would repeat the pipeline uncertainty this editor exists to correct.

## Object controls

The selected region keeps its move, rotate, and bend controls and gains eight oriented resize handles. Corner handles scale both axes around the opposite corner. Side handles scale one axis around the opposite side. Holding Shift preserves aspect ratio. All transforms operate in the region's rotated local coordinate system and remain single-step undo operations.

## Sparse curves

Smooth regions use the existing closed Catmull–Rom path representation. Add a **Simplify curve** action that reduces redundant contour points using closed-shape Ramer–Douglas–Peucker simplification at a canvas-relative tolerance. The simplified points remain the editable spline controls while rendering and export continue to use the same contour array. Simplification is explicit, previewable through undo, and never runs during load or save.

## Symmetry and repetition

Add **Mirror copy** to duplicate the selected region across the canvas centerline, reverse winding, assign a new region ID/key, and select the result. Add **Mirror onto…** as a two-click operation: choose a source, activate the tool, then select the target region whose geometry should be replaced by the mirrored source while retaining the target's ID, key, type, and notes. Both operations are board-independent because the centerline derives from `canvas.width / 2`.

## Navigation

Add previous/next controls to the inspector and keyboard shortcuts `[` and `]`. Navigation follows numeric region order, keeps the selected hold visible in the list, and does not alter geometry. `M` performs Mirror copy, `S` toggles edge snapping, and `E` toggles detailed point editing when focus is not in a text control.

## Optional edge snapping

When enabled, dragging a contour point or resize handle searches a small radius in the Stage 1 image for the strongest luminance gradient and snaps only when the gradient exceeds a conservative threshold. The source image is sampled through an offscreen canvas. If image pixels are unavailable, snapping disables itself with a visible explanation. The operator can hold Option/Alt to bypass snapping for one drag.

Snapping affects only active drag operations, never moving whole regions, rotation, bending, loading, or saving. This keeps the assist predictable and avoids board-specific vision logic.

## Feedback and recovery

The status bar names each active mode and completed operation. Resize, simplify, mirror, mirror-replace, and snapped point changes enter existing undo/redo history. Save behavior and correction provenance remain unchanged. The original automatic proposal is never overwritten.

## Verification

- Unit-test local-coordinate scaling, closed-contour simplification, mirroring, target replacement metadata preservation, and edge candidate selection.
- Browser-test object resize, mirror copy, navigation, snap toggling, undo, and Save dirty state against a real onboarding run.
- Replay the same editor code against Beastmaker, Compact II, and Simulator 3D artifacts; no per-product editor data or branches are permitted.
